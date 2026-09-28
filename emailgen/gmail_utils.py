import os
if os.getenv('DEBUG') == 'True':
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

import base64
import re
from datetime import timezone
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

CLIENT_CONFIG = {
    "web": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": [REDIRECT_URI],
    }
}


def get_auth_flow():
    flow = Flow.from_client_config(CLIENT_CONFIG, scopes=SCOPES)
    flow.redirect_uri = REDIRECT_URI
    return flow


def get_authorization_url():
    flow = get_auth_flow()
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
    )
    return auth_url, state, flow.code_verifier


def exchange_code_for_tokens(authorization_response_url, code_verifier):
    flow = get_auth_flow()
    flow.code_verifier = code_verifier
    flow.fetch_token(authorization_response=authorization_response_url)
    creds = flow.credentials
    return creds


def credentials_from_gmail_account(gmail_account):
    creds = Credentials(
        token=gmail_account.access_token,
        refresh_token=gmail_account.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        scopes=SCOPES,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(GoogleRequest())
        gmail_account.access_token = creds.token
        gmail_account.token_expiry = creds.expiry.replace(tzinfo=timezone.utc)
        gmail_account.save()

    return creds


def get_gmail_service(gmail_account):
    creds = credentials_from_gmail_account(gmail_account)
    return build('gmail', 'v1', credentials=creds)


def send_email_via_gmail(gmail_account, to_email, subject, body, attachment_path=None):
    """
    Sends an email using the user's connected Gmail account.
    If attachment_path is provided, attaches that file to the email.
    Returns the sent message ID on success, raises Exception on failure.
    """
    service = get_gmail_service(gmail_account)

    if attachment_path:
        message = MIMEMultipart()
        message.attach(MIMEText(body))

        with open(attachment_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
        encoders.encode_base64(part)
        filename = os.path.basename(attachment_path)
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        message.attach(part)
    else:
        message = MIMEText(body)

    message['to'] = to_email
    message['subject'] = subject

    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

    sent_message = service.users().messages().send(
        userId='me',
        body={'raw': raw_message}
    ).execute()

    return sent_message['id']


def _extract_clean_email(raw_sender):
    """
    Gmail's 'From' header often looks like '"Google Careers" <noreply@google.com>'.
    This extracts just the clean email address for reliable domain matching.
    """
    match = re.search(r'[\w\.-]+@[\w\.-]+', raw_sender)
    return match.group(0) if match else raw_sender


def fetch_recent_emails(gmail_account, max_results=10):
    """
    Fetches recent emails from the user's Gmail inbox.
    Returns a list of dicts: [{'id', 'sender', 'subject', 'snippet', 'body'}]
    'sender' is a cleaned email address (display name stripped).
    """
    service = get_gmail_service(gmail_account)

    results = service.users().messages().list(
        userId='me',
        maxResults=max_results,
        labelIds=['INBOX'],
    ).execute()

    messages = results.get('messages', [])
    emails = []

    for msg_ref in messages:
        msg = service.users().messages().get(
            userId='me',
            id=msg_ref['id'],
            format='full',
        ).execute()

        headers = msg['payload'].get('headers', [])
        raw_sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        sender = _extract_clean_email(raw_sender)
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No subject)')
        snippet = msg.get('snippet', '')

        body_text = _extract_body(msg['payload'])

        emails.append({
            'id': msg_ref['id'],
            'sender': sender,
            'subject': subject,
            'snippet': snippet,
            'body': body_text or snippet,
        })

    return emails


def _extract_body(payload):
    """Recursively extracts plain text body from a Gmail message payload."""
    if payload.get('mimeType') == 'text/plain' and 'data' in payload.get('body', {}):
        data = payload['body']['data']
        return base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')

    for part in payload.get('parts', []):
        result = _extract_body(part)
        if result:
            return result

    return None