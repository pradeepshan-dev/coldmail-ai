import os
from dotenv import load_dotenv
import google.generativeai as genai
from openai import OpenAI
from emailgen.email_templates import generate_template_email
from emailgen.scam_rules import analyze_scam_risk_manual

load_dotenv()

# ---- Gemini setup ----
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = "gemini-3.6-flash"

# ---- OpenAI-compatible clients (Groq, OpenRouter, Mistral) ----
groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)

openrouter_client = OpenAI(
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

mistral_client = OpenAI(
    api_key=os.getenv("MISTRAL_API_KEY"),
    base_url="https://api.mistral.ai/v1",
)


def _call_gemini(prompt):
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt)
    return response.text.strip()


def _call_groq(prompt):
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def _call_openrouter(prompt):
    response = openrouter_client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct:free",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def _call_mistral(prompt):
    response = mistral_client.chat.completions.create(
        model="mistral-small-latest",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


PROVIDERS = [
    ("Gemini", _call_gemini),
    ("Groq", _call_groq),
    ("OpenRouter", _call_openrouter),
    ("Mistral", _call_mistral),
]


def _try_all_providers(prompt):
    """Returns raw text from the first provider that succeeds, or None if all fail."""
    for name, call_func in PROVIDERS:
        try:
            return call_func(prompt)
        except Exception:
            continue
    return None


def _save_generic_template(role_title, tone, company_name, subject, body):
    """
    Strips the specific company name out of a successful AI-generated email
    and saves it as a reusable template for this role + tone combination.
    Used later as a smarter fallback than the generic hardcoded templates.
    """
    from .models import SavedTemplate

    generic_subject = subject.replace(company_name, "{company}")
    generic_body = body.replace(company_name, "{company}")

    SavedTemplate.objects.create(
        role_title=role_title.strip().lower(),
        tone=tone,
        subject_line=generic_subject,
        generated_body=generic_body,
    )


def _get_fallback_email(role_title, tone, company_name, resume_text, job_description):
    """
    Fallback order when all AI providers fail:
    1) A saved AI-generated template matching this role + tone (if one exists)
    2) The hand-written hardcoded template as a last resort
    """
    from .models import SavedTemplate

    if role_title:
        saved = SavedTemplate.objects.filter(
            role_title=role_title.strip().lower(), tone=tone
        ).first()

        if saved:
            subject = saved.subject_line.replace("{company}", company_name)
            body = saved.generated_body.replace("{company}", company_name)
            return subject, body

    return generate_template_email(company_name, resume_text, job_description, tone)


def _save_known_domain(sender_email, risk_level):
    """
    Remembers AI's confirmed verdict (safe or risky) for a sender's domain,
    so the rule-based fallback can reuse this if AI becomes unavailable later.
    """
    from .models import KnownDomain

    domain = sender_email.split('@')[-1].strip().lower()
    obj, created = KnownDomain.objects.get_or_create(
        domain=domain,
        defaults={'risk_level': risk_level}
    )

    if not created:
        if obj.risk_level == risk_level:
            obj.confirmed_count += 1
            obj.save()
        else:
            # AI's verdict changed since last time — trust the latest judgment
            obj.risk_level = risk_level
            obj.confirmed_count = 1
            obj.save()


def generate_cold_email(company_name, resume_text, job_description, tone, role_title=None):
    """
    Calls AI providers in order (Gemini -> Groq -> OpenRouter -> Mistral).
    On success, saves a sanitized (company-name-stripped) version tagged by
    role + tone for future fallback reuse.
    On total AI failure, checks for a saved AI-generated template for this
    role + tone before falling back to the hand-written hardcoded template.
    Returns (subject_line, generated_body).
    """
    prompt = f"""
You are an expert cold email writer helping a job seeker reach out to a company.

Company: {company_name}
Tone: {tone}

Candidate's resume/background:
{resume_text}

Job description they're applying to:
{job_description}

Write a SHORT, punchy cold email (STRICTLY 60-90 words for the body, not more).
Recruiters scan emails for about 10 seconds, so every sentence must earn its place.

Requirements:
- One sharp opening line hooking into the company/role — no throat-clearing
- ONE key strength from the resume that matches the job description (not multiple, pick the single strongest one)
- One clear, low-friction call to action (e.g. "open to a quick 10-min call?")
- Match the tone: {tone}
- No generic filler phrases like "I hope this email finds you well"
- No long paragraphs — 2-3 short paragraphs maximum

Respond ONLY in this exact format, nothing else:
SUBJECT: <subject line here, under 8 words>
BODY:
<email body here>
"""

    text = _try_all_providers(prompt)

    if text is None:
        return _get_fallback_email(role_title, tone, company_name, resume_text, job_description)

    if "SUBJECT:" not in text or "BODY:" not in text:
        return _get_fallback_email(role_title, tone, company_name, resume_text, job_description)

    subject_part = text.split("SUBJECT:")[1].split("BODY:")[0].strip()
    body_part = text.split("BODY:")[1].strip()

    if role_title:
        _save_generic_template(role_title, tone, company_name, subject_part, body_part)

    return subject_part, body_part


def chat_about_email(current_subject, current_body, tone, company_name, user_message):
    """
    Handles edit requests, questions about the email/job search, and light chat.
    Politely redirects fully unrelated topics.
    If all AI providers fail, returns a graceful "unavailable" message instead
    of crashing — the chat UI stays usable even with zero AI capacity.
    """
    prompt = f"""
You are a friendly AI assistant helping a job seeker with a cold email they're sending to {company_name}.
You are scoped specifically to this email and general job-search/career topics — 
not a general-purpose assistant.

Current subject line: {current_subject}

Current email body:
{current_body}

Tone: {tone}

The user just said:
"{user_message}"

Decide what they want, choosing exactly ONE of these three categories:

1. EDIT — ONLY if they are clearly asking you to change, rewrite, shorten, lengthen, 
   or otherwise modify the email itself (e.g. "make it shorter", "add more confidence", 
   "remove the second paragraph", "make it more formal").

2. ANSWER — if they are asking a genuine question about this email, cold emailing, 
   job searching, interviews, or career advice (e.g. "why did you pick this subject?", 
   "is this too pushy?", "should I mention my GPA?", "how do I follow up after this?").

3. CHAT — for greetings, small talk, or thanks (e.g. "hi", "thanks", "lol") — respond 
   naturally and briefly. For topics UNRELATED to this email, job searching, or careers 
   (general trivia, coding help, unrelated tasks, random facts), politely decline and 
   redirect: briefly mention you're focused on helping with this cold email and job 
   search, and ask if there's anything in that area you can help with. Keep it warm, 
   not robotic.

IMPORTANT: Only choose EDIT if the user explicitly wants the email changed. When in 
doubt, choose ANSWER or CHAT instead of EDIT — never modify the email unless clearly asked to.

Respond ONLY in ONE of these three exact formats, nothing else:

If editing:
ACTION: EDIT
SUBJECT: <updated subject line, under 8 words>
BODY:
<updated email body, 60-90 words>

If answering a question:
ACTION: ANSWER
TEXT: <your helpful, concise answer, 2-4 sentences>

If general chat or redirecting an unrelated topic:
ACTION: CHAT
TEXT: <a brief, friendly reply, 1-3 sentences>
"""

    text = _try_all_providers(prompt)

    if text is None:
        return {
            'action': 'answer',
            'text': "The AI assistant is temporarily unavailable due to high demand. "
                    "You can still copy, edit manually, or send this email as-is. "
                    "Please try chatting again in a little while."
        }

    if text.startswith("ACTION: EDIT"):
        try:
            subject_part = text.split("SUBJECT:")[1].split("BODY:")[0].strip()
            body_part = text.split("BODY:")[1].strip()
            return {'action': 'edit', 'subject': subject_part, 'body': body_part}
        except IndexError:
            return {'action': 'answer', 'text': "Sorry, I had trouble processing that. Could you rephrase?"}

    elif text.startswith("ACTION: ANSWER") or text.startswith("ACTION: CHAT"):
        try:
            answer_text = text.split("TEXT:")[1].strip()
        except IndexError:
            answer_text = text.replace("ACTION: ANSWER", "").replace("ACTION: CHAT", "").strip()
        return {'action': 'answer', 'text': answer_text}

    else:
        return {'action': 'answer', 'text': text.strip()}


def analyze_scam_risk(sender_email, email_content):
    """
    Returns {'risk_level': ..., 'summary': ..., 'red_flags': [...]}.
    Tries all providers in order; falls back to rule-based detection
    (analyze_scam_risk_manual) if all AI providers fail or return a
    malformed response. On a confident AI verdict (safe or risky), saves
    the sender's domain to KnownDomain for future fallback reuse.
    """
    prompt = f"""
You are a scam-detection assistant helping a job seeker evaluate a recruiting/company email for fraud risk.

Sender email address: {sender_email or "Not provided"}

Full email content:
{email_content}

Analyze this for common recruitment/company email scam patterns, such as:
- Free/personal email domains (Gmail, Yahoo, Outlook) claiming to represent a real company
- Urgency or pressure tactics ("apply today", "limited slots")
- Requests for money, bank details, ID/passport, or payment before any formal process
- Requests to communicate only via WhatsApp/Telegram instead of official channels
- Vague job descriptions, unrealistic salary, poor grammar, generic greetings
- Any other classic phishing/scam indicators

Respond ONLY in this exact format, nothing else:
RISK: <safe OR caution OR risky>
SUMMARY: <one sentence overall verdict>
FLAGS:
- <red flag 1, or "None detected" if safe>
- <red flag 2 if any>
- <red flag 3 if any>
"""

    text = _try_all_providers(prompt)

    if text is None:
        return analyze_scam_risk_manual(sender_email, email_content)

    if "RISK:" not in text or "SUMMARY:" not in text or "FLAGS:" not in text:
        return analyze_scam_risk_manual(sender_email, email_content)

    risk_part = text.split("RISK:")[1].split("SUMMARY:")[0].strip().lower()
    summary_part = text.split("SUMMARY:")[1].split("FLAGS:")[0].strip()
    flags_part = text.split("FLAGS:")[1].strip()

    flags_list = [
        line.strip("- ").strip()
        for line in flags_part.split("\n")
        if line.strip().startswith("-")
    ]

    if risk_part not in ('safe', 'caution', 'risky'):
        risk_part = 'caution'

    if sender_email and '@' in sender_email and risk_part in ('safe', 'risky'):
        _save_known_domain(sender_email, risk_part)

    return {
        'risk_level': risk_part,
        'summary': summary_part,
        'red_flags': flags_list,
    }