def formal_template(company_name, resume_text, job_description, tone):
    subject = f"Application for Opportunities at {company_name}"
    body = f"""Dear Hiring Team at {company_name},

I am writing to express my interest in contributing to your organization. With a background that includes {_extract_snippet(resume_text)}, I believe I could bring meaningful value to your team.

I have reviewed the role you are hiring for and am confident that my skills align well with your requirements. I would welcome the opportunity to discuss how my experience could support {company_name}'s goals.

Thank you for considering my application. I look forward to the possibility of speaking further.

Best regards"""
    return subject, body


def friendly_template(company_name, resume_text, job_description, tone):
    subject = f"Excited about {company_name} — quick intro"
    body = f"""Hi there,

Hope you're doing well! I came across the opportunity at {company_name} and wanted to reach out directly, since I think there could be a great fit here.

A bit about me: {_extract_snippet(resume_text)}. I'd love the chance to chat about how I could contribute to your team.

Would you be open to a quick call sometime this week? Happy to work around your schedule.

Looking forward to hearing from you!"""
    return subject, body


def confident_template(company_name, resume_text, job_description, tone):
    subject = f"Ready to make an impact at {company_name}"
    body = f"""Hello,

I'll get straight to the point — I'm confident I'd be a strong addition to your team at {company_name}.

My background includes {_extract_snippet(resume_text)}, and I have a track record of delivering results. I understand what this role requires, and I'm ready to bring that same energy to your organization.

Let's set up a time to talk about how I can contribute from day one.

Best,"""
    return subject, body


def enthusiastic_template(company_name, resume_text, job_description, tone):
    subject = f"Thrilled at the chance to join {company_name}!"
    body = f"""Hello!

I am genuinely excited about the opportunity at {company_name} — this role immediately caught my attention!

With experience in {_extract_snippet(resume_text)}, I'd love to bring my energy and skills to your team. This feels like exactly the kind of challenge I've been looking for.

I'd be thrilled to discuss this further — please let me know a time that works for a quick chat!

Can't wait to hear from you!"""
    return subject, body


def _extract_snippet(resume_text, max_words=25):
    """Grabs the first meaningful chunk of the resume text as a fallback summary."""
    words = resume_text.strip().split()
    snippet = " ".join(words[:max_words])
    return snippet + ("..." if len(words) > max_words else "")


TEMPLATE_MAP = {
    'formal': formal_template,
    'friendly': friendly_template,
    'confident': confident_template,
    'enthusiastic': enthusiastic_template,
}


def generate_template_email(company_name, resume_text, job_description, tone):
    """
    Fallback when ALL AI providers fail. Returns (subject, body) using
    a hand-written template for the given tone.
    """
    template_func = TEMPLATE_MAP.get(tone, formal_template)
    return template_func(company_name, resume_text, job_description, tone)