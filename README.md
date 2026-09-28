# ColdMail AI

**Live demo:** https://coldmail-ai-ogbx.onrender.com

> Hosted on a free plan, so the first load can take about a minute while the server wakes up.

An AI-powered cold email generator for job seekers. Paste your resume and a job description, pick a tone, and get a tailored cold email. Then send it straight from your Gmail, track the application, refine it with an AI chatbot, and check suspicious recruiter emails with a built-in scam checker.

## Features

- **Auth and profiles**: signup/login with Django's `User` plus a `UserDetail` profile (profile picture upload, avatar dropdown, Gmail connection status).
- **AI email generation**: company, role, resume, job description and tone in, subject line and email body out.
- **Resilient AI fallback chain**: Gemini -> Groq -> OpenRouter -> Mistral -> saved templates (AI outputs stored per role + tone, company name replaced with `{company}`) -> hand-written templates. The app keeps working when free-tier limits run out.
- **Email history and application tracker**: mark each email as sent, no response, replied, interview, rejected or offer.
- **AI chatbot**: classifies each message as EDIT (modify the email), ANSWER (email/job-search questions) or CHAT (small talk). Deliberately scoped to email and job-search topics. Shows a friendly message if every AI provider is unavailable.
- **Scam checker**: AI analysis with a rule-based fallback (`scam_rules.py`: suspicious keywords, free email domains, urgency phrases, payment requests) plus a `KnownDomain` model that remembers past safe/risky verdicts per sender domain.
- **Gmail integration (OAuth2)**: connect your account, send emails with an optional resume attachment, and scan your 10 most recent inbox emails through the scam checker.

## Tech Stack

- **Backend**: Python, Django
- **Database**: MySQL (local development), PostgreSQL on Neon (live demo)
- **Hosting**: Render (free plan)
- **Frontend**: HTML, CSS, vanilla JavaScript
- **AI providers**: Google Gemini, Groq, OpenRouter, Mistral
- **Email**: Gmail API via `google-auth-oauthlib`
- **Config**: `python-dotenv`

## Setup

### 1. Clone and install

```bash
git clone https://github.com/pradeepshan-dev/coldmail-ai.git
cd coldmail-ai
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env             # Windows: copy .env.example .env
```

Fill in `.env`. Refer to `.env.example` for the exact variable names; it covers the Django secret key, database credentials, the four AI provider API keys, and the Google OAuth client ID, client secret and redirect URI.

### 3. Create the database

Create an empty MySQL database named `coldmail_db`, then:

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run

```bash
python manage.py runserver
```

Open http://127.0.0.1:8000/.

### 5. Google OAuth setup (for Gmail features)

1. In Google Cloud Console, create a project and enable the **Gmail API**.
2. Create an **OAuth client ID** (Web application).
3. Add your redirect URI (for local dev, the callback URL your `GOOGLE_REDIRECT_URI` points to, e.g. `http://127.0.0.1:8000/...`).
4. Put the client ID, secret and redirect URI in `.env`.
5. Local HTTP testing requires `OAUTHLIB_INSECURE_TRANSPORT=1`. **Never enable this in production**; production must use HTTPS.

## Note on Google OAuth "Testing" mode

The Google OAuth app is currently in **Testing** mode. That means:

- Only Google accounts manually added as **test users** in Google Cloud Console can connect Gmail (up to 100).
- Test-user authorizations **expire after 7 days**, so you will need to reconnect Gmail periodically.
- Publishing is possible, but because `gmail.readonly` is a restricted scope, unverified apps show a warning screen and are capped at 100 users until Google verification is completed.

If you are running your own copy, create your own Google Cloud project and add yourself as a test user.

On the live demo, Gmail connect only works for accounts added as test users. Sign-up, email generation and the scam checker work without Gmail.

## AI provider limits

All four AI providers are used on free tiers with daily rate limits. This is why the fallback chain exists. If you enable billing on your primary provider (Gemini), limits are far less likely to matter.

## Privacy

Scanning your inbox sends email content to third-party AI providers for analysis. Only use this feature if you are comfortable with that. Gmail tokens are stored in the database; see the roadmap for planned encryption.

## Roadmap

- "Continue with Google" login and signup
- Encryption of stored Gmail tokens
- Opt-in notice and privacy policy page
- Per-user daily AI usage limits

## License

No license has been added yet.
