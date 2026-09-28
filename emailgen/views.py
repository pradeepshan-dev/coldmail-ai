from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
import json
from datetime import timezone as py_timezone

from .forms import LoginForm, SignupForm, EmailRequestForm, ScamCheckForm
from .models import UserDetail, EmailRequest, ScamCheck, GmailAccount
from .ai_utils import generate_cold_email, chat_about_email, analyze_scam_risk
from .gmail_utils import get_authorization_url, exchange_code_for_tokens, send_email_via_gmail, fetch_recent_emails


def registration(request):
    login_form = LoginForm()
    signup_form = SignupForm()

    if request.method == 'POST':
        if 'login_submit' in request.POST:
            login_form = LoginForm(request.POST)
            if login_form.is_valid():
                username = login_form.cleaned_data['username']
                password = login_form.cleaned_data['password']
                user = authenticate(request, username=username, password=password)
                if user is not None:
                    auth_login(request, user)
                    return redirect('email_chatbot')
                else:
                    login_form.add_error(None, "Invalid username or password")

        elif 'signup_submit' in request.POST:
            signup_form = SignupForm(request.POST)
            if signup_form.is_valid():
                username = signup_form.cleaned_data['username']
                email = signup_form.cleaned_data['email']
                password = signup_form.cleaned_data['password']

                if User.objects.filter(username=username).exists():
                    signup_form.add_error('username', "Username already taken")
                elif User.objects.filter(email=email).exists():
                    signup_form.add_error('email', "Email already registered")
                else:
                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        password=password
                    )
                    UserDetail.objects.create(user=user, username=username, email=email)
                    auth_login(request, user)
                    return redirect('email_chatbot')

    return render(request, 'emailgen/registration.html', {
        'login_form': login_form,
        'signup_form': signup_form,
    })


@login_required(login_url='registration')
def home(request):
    emails = EmailRequest.objects.filter(user=request.user)
    scam_checks = ScamCheck.objects.filter(user=request.user)
    gmail_connected = GmailAccount.objects.filter(user=request.user).exists()
    recent_emails = emails[:3]

    return render(request, 'emailgen/home.html', {
        'user': request.user,
        'email_count': emails.count(),
        'scam_check_count': scam_checks.count(),
        'gmail_connected': gmail_connected,
        'recent_emails': recent_emails,
    })


def logout_view(request):
    auth_logout(request)
    return redirect('registration')


@login_required(login_url='registration')
def create_email(request):
    form = EmailRequestForm()

    if request.method == 'POST':
        form = EmailRequestForm(request.POST)
        if form.is_valid():
            company_name = form.cleaned_data['company_name']
            role_title = form.cleaned_data['role_title']
            resume_text = form.cleaned_data['resume_text']
            job_description = form.cleaned_data['job_description']
            tone = form.cleaned_data['tone']

            try:
                subject_line, generated_body = generate_cold_email(
                    company_name, resume_text, job_description, tone, role_title=role_title
                )
            except Exception as e:
                form.add_error(None, f"AI generation failed: {e}")
            else:
                email_request = EmailRequest.objects.create(
                    user=request.user,
                    company_name=company_name,
                    role_title=role_title,
                    resume_text=resume_text,
                    job_description=job_description,
                    tone=tone,
                    subject_line=subject_line,
                    generated_body=generated_body,
                )
                return redirect('email_result', pk=email_request.pk)

    return render(request, 'emailgen/create_email.html', {'form': form})


@login_required(login_url='registration')
def email_result(request, pk):
    email_request = get_object_or_404(EmailRequest, pk=pk, user=request.user)
    return render(request, 'emailgen/email_result.html', {
        'email_request': email_request,
    })


@login_required(login_url='registration')
def email_history(request):
    emails = EmailRequest.objects.filter(user=request.user)
    return render(request, 'emailgen/email_history.html', {
        'emails': emails,
    })


@login_required(login_url='registration')
def email_chatbot(request, pk=None):
    emails = EmailRequest.objects.filter(user=request.user)
    selected_email = None

    if pk:
        selected_email = get_object_or_404(EmailRequest, pk=pk, user=request.user)
    elif emails.exists():
        selected_email = emails.first()

    return render(request, 'emailgen/email_chatbot.html', {
        'emails': emails,
        'selected_email': selected_email,
    })


@login_required(login_url='registration')
def refine_email(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    email_request = get_object_or_404(EmailRequest, pk=pk, user=request.user)
    instruction = request.POST.get('instruction', '').strip()

    if not instruction:
        return JsonResponse({'error': 'Please type a message'}, status=400)

    try:
        result = chat_about_email(
            email_request.subject_line,
            email_request.generated_body,
            email_request.tone,
            email_request.company_name,
            instruction
        )
    except Exception as e:
        return JsonResponse({'error': f'AI failed: {e}'}, status=500)

    if result['action'] == 'edit':
        new_email_request = EmailRequest.objects.create(
            user=request.user,
            company_name=email_request.company_name,
            role_title=email_request.role_title,
            resume_text=email_request.resume_text,
            job_description=email_request.job_description,
            tone=email_request.tone,
            subject_line=result['subject'],
            generated_body=result['body'],
        )
        return JsonResponse({
            'action': 'edit',
            'subject': result['subject'],
            'body': result['body'],
            'new_pk': new_email_request.pk,
        })
    else:
        return JsonResponse({
            'action': 'answer',
            'text': result['text'],
        })


@login_required(login_url='registration')
def scam_checker(request):
    form = ScamCheckForm()
    result = None

    if request.method == 'POST':
        form = ScamCheckForm(request.POST)
        if form.is_valid():
            sender_email = form.cleaned_data['sender_email']
            email_content = form.cleaned_data['email_content']

            try:
                analysis = analyze_scam_risk(sender_email, email_content)
            except Exception as e:
                form.add_error(None, f"Analysis failed: {e}")
            else:
                ScamCheck.objects.create(
                    user=request.user,
                    sender_email=sender_email,
                    email_content=email_content,
                    risk_level=analysis['risk_level'],
                    verdict_summary=analysis['summary'],
                    red_flags=json.dumps(analysis['red_flags']),
                )
                result = analysis

    return render(request, 'emailgen/scam_checker.html', {
        'form': form,
        'result': result,
    })


@login_required(login_url='registration')
def gmail_connect(request):
    auth_url, state, code_verifier = get_authorization_url()
    request.session['gmail_oauth_state'] = state
    request.session['gmail_code_verifier'] = code_verifier
    return redirect(auth_url)


@login_required(login_url='registration')
def gmail_callback(request):
    full_url = request.build_absolute_uri()
    code_verifier = request.session.get('gmail_code_verifier')

    if not code_verifier:
        return render(request, 'emailgen/gmail_error.html', {'error': 'Session expired, please try connecting again.'})

    try:
        creds = exchange_code_for_tokens(full_url, code_verifier)
    except Exception as e:
        return render(request, 'emailgen/gmail_error.html', {'error': str(e)})

    expiry = creds.expiry
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=py_timezone.utc)

    GmailAccount.objects.update_or_create(
        user=request.user,
        defaults={
            'access_token': creds.token,
            'refresh_token': creds.refresh_token,
            'token_expiry': expiry,
        }
    )

    del request.session['gmail_code_verifier']

    return redirect('home')


@login_required(login_url='registration')
def send_email_gmail(request, pk):
    email_request = get_object_or_404(EmailRequest, pk=pk, user=request.user)

    try:
        gmail_account = request.user.gmail_account
    except GmailAccount.DoesNotExist:
        return JsonResponse({'error': 'Gmail not connected. Please connect Gmail first.'}, status=400)

    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    recipient = request.POST.get('recipient_email', '').strip()
    if not recipient:
        return JsonResponse({'error': 'Please enter a recipient email address'}, status=400)

    attachment_path = None
    uploaded_file = request.FILES.get('resume_file')
    if uploaded_file:
        email_request.resume_file = uploaded_file
        email_request.save()
        attachment_path = email_request.resume_file.path
    elif email_request.resume_file:
        attachment_path = email_request.resume_file.path

    try:
        message_id = send_email_via_gmail(
            gmail_account,
            recipient,
            email_request.subject_line,
            email_request.generated_body,
            attachment_path=attachment_path,
        )
    except Exception as e:
        return JsonResponse({'error': f'Failed to send: {e}'}, status=500)

    email_request.recipient_email = recipient
    email_request.save()

    return JsonResponse({'success': True, 'message_id': message_id})


@login_required(login_url='registration')
def gmail_scan(request):
    try:
        gmail_account = request.user.gmail_account
    except GmailAccount.DoesNotExist:
        return render(request, 'emailgen/gmail_scan.html', {
            'not_connected': True,
        })

    scanned_results = []

    if request.method == 'POST':
        try:
            emails = fetch_recent_emails(gmail_account, max_results=10)
        except Exception as e:
            return render(request, 'emailgen/gmail_scan.html', {
                'error': f'Failed to fetch emails: {e}',
            })

        for email in emails:
            try:
                analysis = analyze_scam_risk(email['sender'], email['body'])
            except Exception:
                analysis = {'risk_level': 'caution', 'summary': 'Could not analyze this email.', 'red_flags': []}

            scanned_results.append({
                'sender': email['sender'],
                'subject': email['subject'],
                'risk_level': analysis['risk_level'],
                'summary': analysis['summary'],
                'red_flags': analysis['red_flags'],
            })

    return render(request, 'emailgen/gmail_scan.html', {
        'scanned_results': scanned_results,
    })


@login_required(login_url='registration')
def update_status(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    email_request = get_object_or_404(EmailRequest, pk=pk, user=request.user)
    new_status = request.POST.get('status', '').strip()

    valid_statuses = [choice[0] for choice in EmailRequest.STATUS_CHOICES]
    if new_status not in valid_statuses:
        return JsonResponse({'error': 'Invalid status'}, status=400)

    email_request.status = new_status
    email_request.save()

    return JsonResponse({'success': True, 'status': new_status, 'status_display': email_request.get_status_display()})

@login_required(login_url='registration')
def update_profile_picture(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=405)

    uploaded_file = request.FILES.get('profile_picture')
    if not uploaded_file:
        return JsonResponse({'error': 'No file provided'}, status=400)

    try:
        detail = request.user.detail
    except UserDetail.DoesNotExist:
        detail = UserDetail.objects.create(
            user=request.user,
            username=request.user.username,
            email=request.user.email,
        )

    detail.profile_picture = uploaded_file
    detail.save()

    return JsonResponse({'success': True, 'picture_url': detail.profile_picture.url})