from flask_wtf import FlaskForm
from flask_wtf.file import FileField, MultipleFileField
from wtforms import BooleanField, DateTimeLocalField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional

from app.utils.choices import (
    ASPECT_RATIO_CHOICES,
    CTA_CHOICES,
    DURATION_CHOICES,
    LANGUAGE_CHOICES,
    LENGTH_CHOICES,
    CONTENT_STYLE_CHOICES,
    TEMPLATE_CHOICES,
    TONE_CHOICES,
)


class GenerateVideoForm(FlaskForm):
    title = StringField("Project title", validators=[DataRequired(), Length(max=180)])
    topic = StringField("Topic", validators=[DataRequired(), Length(max=255)])
    script = TextAreaField("Script", validators=[Optional(), Length(max=5000)])
    images = MultipleFileField("Upload images")
    video_file = FileField("Optional video")
    audio_file = FileField("Optional background audio")
    language = SelectField("Language", choices=LANGUAGE_CHOICES, validators=[DataRequired()])
    style = SelectField("Content style", choices=CONTENT_STYLE_CHOICES, validators=[DataRequired()])
    duration = SelectField("Duration", choices=DURATION_CHOICES, coerce=int, validators=[DataRequired()])
    aspect_ratio = SelectField("Aspect ratio", choices=ASPECT_RATIO_CHOICES, validators=[DataRequired()])
    template = SelectField("Template", choices=TEMPLATE_CHOICES, validators=[DataRequired()])
    tone = SelectField("Tone", choices=TONE_CHOICES, validators=[DataRequired()])
    caption_length = SelectField("Caption length", choices=LENGTH_CHOICES, validators=[DataRequired()])
    emoji_enabled = BooleanField("Use emojis", default=True)
    cta_strength = SelectField("CTA intensity", choices=CTA_CHOICES, validators=[DataRequired()])
    submit = SubmitField("Generate video")


class PostPreviewForm(FlaskForm):
    social_account_id = SelectField("Connected platform", choices=[], validators=[Optional()])
    caption_text = TextAreaField("Caption", validators=[DataRequired(), Length(max=5000)])
    hashtags_text = TextAreaField("Hashtags", validators=[Optional(), Length(max=2000)])
    scheduled_time = DateTimeLocalField("Schedule time", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    submit = SubmitField("Save")
