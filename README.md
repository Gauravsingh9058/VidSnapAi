# VidSnapAI

VidSnapAI is a production-style Flask SaaS MVP for creators and businesses who want to generate short-form videos, auto-write captions, connect social accounts, and publish or schedule content from one dashboard.

## Folder structure

```text
app/
  auth/
  dashboard/
  history/
  marketing/
  models/
  scheduler/
  services/
  settings/
  social/
  static/
    css/
    js/
  templates/
    auth/
    dashboard/
    history/
    marketing/
    partials/
    scheduler/
    settings/
    social/
    video/
  uploads/
  utils/
  video/
config.py
generate_process.py
main.py
requirements.txt
.env.example
```

## Features

- Authentication with signup, login, logout, and forgot password UI
- Free-to-paid SaaS flow with premium account state on each user
- Protected dashboard with overview metrics and quick actions
- Reel generation from uploaded images plus optional video/audio
- Background reel processing with queued, processing, uploading, ready, and failed states
- Auto-generated caption sets with CTA, hashtags, and first comment
- Payment-ready billing flow with Razorpay checkout, signature verification, and webhook support
- Media asset tracking plus optional Cloudinary storage for uploaded and generated files
- Real Meta OAuth architecture for Instagram professional accounts and Facebook Pages
- Post preview flow with draft, publish now, and schedule actions
- Scheduled post management and history tracking
- Project delete flow, download flow, and status polling on preview
- Marketing pages with pricing, demo, urgency, privacy policy, and terms
- Settings for profile, password, notifications, and account deletion

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and update values if needed.
4. Add your Meta app credentials to `.env` if you want the live Instagram/Facebook connection flow to work.
5. Add Razorpay keys if you want to test billing:

```text
RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
```

6. Add Cloudinary credentials if you want generated files stored outside the local filesystem:

```text
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
```

7. Make sure `ffmpeg` is installed and available on your system `PATH`.
8. Run the app:

```bash
python main.py
```

9. Open `http://127.0.0.1:5000`.

## Database

- Default database: SQLite at `instance/vidsnapai.db`
- To use PostgreSQL, set `DATABASE_URL` in `.env`
- A SQL migration file for the Meta social-account upgrade is included in `migrations/20260420_meta_social_upgrade.sql`
- Runtime schema upgrades also backfill new columns for premium access and project storage metadata

## Meta setup

1. Create a Meta app in the Meta App Dashboard.
2. Add Facebook Login for Business and configure the OAuth redirect URI:

```text
http://127.0.0.1:5000/app/social-accounts/callback/meta
```

For production SaaS deployments, replace `http://127.0.0.1:5000` with your public app URL. The redirect URI in Meta must exactly match the callback your app uses.

3. Request the permissions used by this build:

```text
pages_show_list
pages_read_engagement
pages_manage_posts
pages_manage_metadata
instagram_basic
instagram_content_publish
business_management
```

4. Connect at least one Facebook Page to the Meta user you log in with.
5. For Instagram, make sure the Instagram professional account is linked to a Facebook Page accessible by that Meta user.
6. Add `META_APP_ID`, `META_APP_SECRET`, and `SOCIAL_TOKEN_ENCRYPTION_SECRET` to `.env`.
7. Set `APP_BASE_URL` to your public app URL, or explicitly set `META_REDIRECT_URI` if you want to override the derived callback URL.

## Scheduler flow

- The MVP processes due scheduled jobs during authenticated requests.
- Reel generation now runs in a background thread so the UI can keep polling project status instead of blocking the request.
- You can also trigger the scheduler manually with:

```bash
python generate_process.py
```

## Deployment notes

- Put Flask behind Gunicorn, Waitress, or another production WSGI server.
- Use PostgreSQL in production.
- Use Cloudinary or S3-style storage for generated files in production.
- Wire the published post execution to the live Meta Graph API endpoints before calling the Instagram/Facebook autopost flow fully complete.
- Replace the background thread worker with Celery, RQ, or another queue for scale.
- Set a strong `SECRET_KEY` and production-safe cookie configuration.
- Update the legal pages with your business name, support email, refund policy, and jurisdiction before launch.
