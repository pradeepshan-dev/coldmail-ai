import re

FREE_EMAIL_DOMAINS = [
    'gmail.com', 'yahoo.com', 'outlook.com', 'hotmail.com',
    'aol.com', 'icloud.com', 'protonmail.com', 'mail.com',
]

URGENCY_PHRASES = [
    'act now', 'urgent', 'immediately', 'limited slots', 'apply today',
    'expires today', 'act fast', 'don\'t miss', 'hurry', 'last chance',
]

PAYMENT_PHRASES = [
    'processing fee', 'registration fee', 'send money', 'wire transfer',
    'bank details', 'account number', 'gift card', 'bitcoin', 'crypto',
    'western union', 'pay upfront', 'deposit required', 'training fee',
]

SUSPICIOUS_CONTACT_PHRASES = [
    'whatsapp only', 'telegram only', 'contact us on whatsapp',
    'message me on telegram', 'text only',
]

VAGUE_PHRASES = [
    'work from home', 'no experience needed', 'earn $', 'earn up to',
    'guaranteed income', 'be your own boss',
]


def analyze_scam_risk_manual(sender_email, email_content):
    """
    Fallback scam detector using rule-based pattern matching, combined with
    domains AI has previously confirmed as safe or risky (KnownDomain).
    Used only when ALL AI providers fail.
    Returns the same dict shape as analyze_scam_risk().
    """
    from .models import KnownDomain

    content_lower = email_content.lower()
    red_flags = []
    risk_score = 0
    known_safe = False

    # Check sender domain
    if sender_email:
        domain = sender_email.split('@')[-1].lower().strip()

        if domain in FREE_EMAIL_DOMAINS:
            red_flags.append(f"Sender uses a free email domain ({domain}) instead of a company domain")
            risk_score += 2

        # Check against domains AI has previously confirmed as safe or risky
        known = KnownDomain.objects.filter(domain=domain).first()
        if known:
            if known.risk_level == 'risky':
                red_flags.append(
                    f"This domain ({domain}) has been confirmed risky {known.confirmed_count} time(s) before"
                )
                risk_score += 4
            elif known.risk_level == 'safe':
                known_safe = True

    # Check urgency language
    for phrase in URGENCY_PHRASES:
        if phrase in content_lower:
            red_flags.append(f"Contains urgency language: \"{phrase}\"")
            risk_score += 1
            break

    # Check payment/money requests
    for phrase in PAYMENT_PHRASES:
        if phrase in content_lower:
            red_flags.append(f"Mentions payment or financial info: \"{phrase}\"")
            risk_score += 3
            break

    # Check suspicious contact methods
    for phrase in SUSPICIOUS_CONTACT_PHRASES:
        if phrase in content_lower:
            red_flags.append(f"Requests contact via unofficial channel: \"{phrase}\"")
            risk_score += 2
            break

    # Check vague/too-good-to-be-true phrases
    for phrase in VAGUE_PHRASES:
        if phrase in content_lower:
            red_flags.append(f"Contains vague or unrealistic claim: \"{phrase}\"")
            risk_score += 1
            break

    # Check for excessive urgency via punctuation (e.g. "!!!" or ALL CAPS spam)
    if len(re.findall(r'!{2,}', email_content)) > 0:
        red_flags.append("Excessive exclamation marks detected")
        risk_score += 1

    # Determine risk level from score
    if known_safe and risk_score == 0:
        # AI has previously confirmed this exact domain as safe, and this
        # email also triggered zero other red flags — trust that confirmation
        risk_level = 'safe'
        summary = "This sender's domain has been previously confirmed as safe, and no scam patterns were found."
        red_flags = ["None detected"]
    elif risk_score >= 4:
        risk_level = 'risky'
        summary = "This email shows multiple strong scam indicators — proceed with caution."
    elif risk_score >= 1:
        risk_level = 'caution'
        summary = "This email has some suspicious patterns worth double-checking."
    else:
        risk_level = 'safe'
        summary = "No common scam patterns were detected in this email."
        red_flags = ["None detected"]

    return {
        'risk_level': risk_level,
        'summary': summary,
        'red_flags': red_flags,
    }