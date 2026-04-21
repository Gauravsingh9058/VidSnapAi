from flask import Blueprint, render_template


bp = Blueprint("marketing", __name__)


@bp.route("/")
def landing():
    testimonials = [
        {
            "name": "Aanya Kapoor",
            "role": "Creator coach",
            "quote": "VidSnapAI took our reel workflow from scattered to systemized in one dashboard.",
        },
        {
            "name": "Marcus Lee",
            "role": "Agency strategist",
            "quote": "The scheduling and caption stack feels like three tools combined into one premium product.",
        },
        {
            "name": "Riya Sharma",
            "role": "Personal brand consultant",
            "quote": "We ship more content, faster, and with way less context switching.",
        },
    ]
    faqs = [
        ("Can I connect real Instagram and Facebook accounts?", "Yes. VidSnapAI now uses a real Meta OAuth flow for eligible Instagram professional accounts and Facebook Pages, with account discovery and secure token storage."),
        ("Does VidSnapAI create captions too?", "Yes. Every generated video can ship with a main caption, short caption, CTA, hashtags, and an optional first comment."),
        ("Can I schedule posts?", "Yes. The lifetime plan includes scheduled post management and the service architecture needed for future direct publishing expansion."),
        ("Is it mobile friendly?", "Yes. The entire marketing site and app shell are responsive for desktop, tablet, and mobile workflows."),
    ]
    before_after = [
        {
            "before": "Loose photos, scattered notes, and no posting cadence.",
            "after": "A generated reel, AI caption pack, and one-click publish flow.",
        },
        {
            "before": "Manual exports with no payment or customer dashboard.",
            "after": "Logged-in SaaS workspace with billing, history, status, and project management.",
        },
    ]
    return render_template(
        "marketing/landing.html",
        title="Create Viral Reels in Minutes with AI",
        testimonials=testimonials,
        faqs=faqs,
        before_after=before_after,
    )


@bp.route("/pricing")
def pricing():
    plans = [
        {
            "slug": "free",
            "name": "Free Workspace",
            "price": "Rs 0",
            "subtitle": "Start building inside the dashboard before you upgrade",
            "features": [
                "Secure signup and login",
                "Create projects and track status",
                "Watermarked exports",
                "One connected social account",
                "Content history dashboard",
            ],
            "highlight": False,
        },
        {
            "slug": "lifetime",
            "name": "Lifetime Access",
            "price": "Rs 399",
            "subtitle": "One-time upgrade for creators and businesses",
            "features": [
                "Unlimited videos",
                "Watermark-free exports",
                "Premium templates",
                "Razorpay checkout + secure premium unlock",
                "Real Meta account connection architecture",
                "Direct posting flow ready for Meta Graph API expansion",
                "Scheduling and publishing pipeline",
                "Content history and delete controls",
                "Optional Cloudinary media storage",
                "Instagram professional + Facebook Page support",
                "Premium dashboard and workflow",
            ],
            "highlight": True,
        },
    ]
    return render_template("marketing/pricing.html", title="Pricing", plans=plans)


@bp.route("/privacy")
def privacy():
    return render_template("marketing/privacy.html", title="Privacy Policy")


@bp.route("/terms")
def terms():
    return render_template("marketing/terms.html", title="Terms & Conditions")
