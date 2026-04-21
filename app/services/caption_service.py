from textwrap import shorten


LANGUAGE_SNIPPETS = {
    "english": {
        "hook": "Turn your idea into a scroll-stopping reel.",
        "follow": "Follow for more creator-ready content systems.",
    },
    "hindi": {
        "hook": "Apne idea ko engaging reel mein badlo.",
        "follow": "Aise aur content ideas ke liye follow karo.",
    },
    "hinglish": {
        "hook": "Apne idea ko ek viral-ready reel mein convert karo.",
        "follow": "Aise aur growth-ready content ke liye follow karo.",
    },
}


STYLE_ANGLES = {
    "viral": "high-retention hooks and punchy lines",
    "storytelling": "a narrative flow that feels personal",
    "business-promo": "clear value and buyer-ready positioning",
    "motivational": "momentum-building emotional energy",
    "educational": "simple teaching points with authority",
    "emotional": "heart-led storytelling and memorable phrasing",
}


TONE_PREFIXES = {
    "professional": "Built for brands that want to look sharp.",
    "viral": "This one is designed to stop the scroll.",
    "casual": "Keeping it natural, clear, and easy to relate to.",
    "emotional": "Made to feel personal and memorable.",
    "sales": "Optimized to move attention toward action.",
}


CTA_LIBRARY = {
    "soft": "Save this for your next content day.",
    "medium": "Comment your niche and I will help with the next angle.",
    "strong": "DM us today to turn your content pipeline into a growth engine.",
}


EMOJI_PACK = {
    "professional": "✨",
    "viral": "🔥",
    "casual": "🙌",
    "emotional": "💫",
    "sales": "🚀",
}


def generate_caption_bundle(topic, script, style, language, tone, length, emoji_enabled, cta_strength):
    topic_text = topic.strip()
    script_text = (script or "").strip()
    language_pack = LANGUAGE_SNIPPETS[language]
    emoji = f"{EMOJI_PACK[tone]} " if emoji_enabled else ""
    cta = CTA_LIBRARY[cta_strength]
    angle = STYLE_ANGLES[style]
    prefix = TONE_PREFIXES[tone]

    script_line = shorten(script_text or topic_text, width=150, placeholder="...")

    main_caption = (
        f"{emoji}{prefix} {language_pack['hook']} This {style.replace('-', ' ')} piece uses {angle} around "
        f"'{topic_text}'. {script_line} {cta}"
    )

    if length == "short":
        main_caption = shorten(main_caption, width=140, placeholder="...")
    elif length == "medium":
        main_caption = shorten(main_caption, width=220, placeholder="...")
    else:
        main_caption = f"{main_caption} {language_pack['follow']}"

    short_caption = shorten(f"{emoji}{topic_text} reel with {angle}. {cta}", width=100, placeholder="...")
    hashtags = build_hashtags(topic_text, style, language)
    first_comment = f"{emoji}Want the caption framework for this {style.replace('-', ' ')} reel? Reply with '{topic_text[:20]}'." if emoji_enabled else f"Want the caption framework for this reel? Reply with '{topic_text[:20]}'."

    return {
        "main_caption": main_caption,
        "short_caption": short_caption,
        "cta": cta,
        "hashtags": hashtags,
        "first_comment": first_comment,
    }


def build_hashtags(topic, style, language):
    cleaned = "".join(ch for ch in topic.title() if ch.isalnum())
    base = [
        "#VidSnapAI",
        "#CreateOncePublishEverywhere",
        f"#{cleaned}" if cleaned else "#ContentMarketing",
        f"#{style.replace('-', '').title()}",
    ]
    language_tags = {
        "english": ["#ReelsMarketing", "#CreatorTools", "#ContentGrowth"],
        "hindi": ["#HindiCreators", "#InstagramGrowth", "#SocialMediaHindi"],
        "hinglish": ["#HinglishContent", "#CreatorGrowth", "#ViralReels"],
    }
    return " ".join(base + language_tags[language])
