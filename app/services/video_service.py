import math
import shutil
import subprocess
from pathlib import Path

from flask import current_app

from app.services.upload_service import relative_upload_path


ASPECT_DIMENSIONS = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "16:9": (1920, 1080),
}


TEMPLATE_STYLES = {
    "clean-modern": {"bg": "0x0B1020", "fontcolor": "white", "box": "0x111827@0.55"},
    "bold-influencer": {"bg": "0x110B22", "fontcolor": "0xF9FAFB", "box": "0x7C3AED@0.55"},
    "business-promo": {"bg": "0x06131F", "fontcolor": "0xE0F2FE", "box": "0x0EA5E9@0.38"},
    "story-cinematic": {"bg": "0x05070D", "fontcolor": "0xF8FAFC", "box": "0x111827@0.42"},
    "motivational-reel": {"bg": "0x0F172A", "fontcolor": "0xFDE68A", "box": "0xF97316@0.25"},
}


def ffmpeg_available():
    return shutil.which("ffmpeg") is not None


def generate_video(
    workspace,
    image_paths,
    video_path,
    audio_path,
    title,
    topic,
    duration_seconds,
    aspect_ratio,
    template,
    add_watermark=False,
    watermark_text="VidSnapAI Free",
):
    if not ffmpeg_available():
        raise RuntimeError("FFmpeg is not available. Install FFmpeg and add it to PATH.")

    sources = []
    for image_path in image_paths:
        sources.append(("image", Path(image_path)))
    if video_path:
        sources.append(("video", Path(video_path)))

    if not sources:
        raise RuntimeError("Upload at least one image or a video asset.")

    width, height = ASPECT_DIMENSIONS[aspect_ratio]
    clip_duration = max(duration_seconds / len(sources), 2)
    total_duration = clip_duration * len(sources)
    style_config = TEMPLATE_STYLES[template]

    input_args = []
    clip_filters = []

    for index, (source_type, source_path) in enumerate(sources):
        if source_type == "image":
            input_args.extend(["-loop", "1", "-t", f"{clip_duration:.2f}", "-i", str(source_path)])
        else:
            input_args.extend(["-stream_loop", "-1", "-t", f"{clip_duration:.2f}", "-i", str(source_path)])

        fade_out_start = max(clip_duration - 0.35, 0)
        clip_filters.append(
            f"[{index}:v]"
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:{style_config['bg']},"
            f"setsar=1,format=yuv420p,"
            f"fade=t=in:st=0:d=0.30,"
            f"fade=t=out:st={fade_out_start:.2f}:d=0.30"
            f"[v{index}]"
        )

    audio_index = len(sources)
    if audio_path:
        input_args.extend(["-stream_loop", "-1", "-i", str(audio_path)])
    else:
        input_args.extend(["-f", "lavfi", "-t", f"{total_duration:.2f}", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"])

    concat_inputs = "".join(f"[v{index}]" for index in range(len(sources)))
    safe_title = _escape_drawtext(title or topic)
    safe_topic = _escape_drawtext(topic)
    font_clause = _font_clause()
    text_overlay = (
        f"[base]"
        f"drawtext={font_clause}text='{safe_title}':fontcolor={style_config['fontcolor']}:fontsize={int(width * 0.045)}:"
        f"x=(w-text_w)/2:y=h*0.10:box=1:boxcolor={style_config['box']}:boxborderw=20,"
        f"drawtext={font_clause}text='{safe_topic}':fontcolor={style_config['fontcolor']}:fontsize={int(width * 0.030)}:"
        f"x=(w-text_w)/2:y=h*0.18:box=1:boxcolor={style_config['box']}:boxborderw=16"
    )

    if add_watermark:
        text_overlay += (
            f",drawtext={font_clause}text='{_escape_drawtext(watermark_text)}':fontcolor=white:fontsize={int(width * 0.024)}:"
            f"x=w-text_w-42:y=h-text_h-48:box=1:boxcolor=0x111827@0.55:boxborderw=14"
        )

    filter_complex = ";".join(
        clip_filters
        + [
            f"{concat_inputs}concat=n={len(sources)}:v=1:a=0[base]",
            f"{text_overlay}[vout]",
        ]
    )

    output_dir = Path(workspace) / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "generated.mp4"
    thumbnail_file = output_dir / "thumbnail.jpg"

    command = [
        "ffmpeg",
        "-y",
        *input_args,
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-map",
        f"{audio_index}:a",
        "-t",
        f"{total_duration:.2f}",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_file),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        error_output = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise RuntimeError(f"FFmpeg failed while generating the video: {error_output}") from exc

    thumb_command = [
        "ffmpeg",
        "-y",
        "-ss",
        "1",
        "-i",
        str(output_file),
        "-frames:v",
        "1",
        str(thumbnail_file),
    ]
    try:
        subprocess.run(thumb_command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        error_output = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise RuntimeError(f"FFmpeg failed while creating the thumbnail: {error_output}") from exc

    return {
        "file_path": relative_upload_path(output_file),
        "thumbnail_path": relative_upload_path(thumbnail_file),
        "duration": math.ceil(total_duration),
    }


def _escape_drawtext(value):
    return (
        (value or "")
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace("\n", " ")
    )


def _font_clause():
    configured_font = current_app.config.get("FFMPEG_FONT_PATH", "").strip()
    candidate_paths = [
        Path(configured_font) if configured_font else None,
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    for font_path in candidate_paths:
        if font_path and font_path.exists():
            escaped = str(font_path).replace("\\", "/").replace(":", "\\:")
            return f"fontfile='{escaped}':"
    return ""
