from django import forms
from .models import EmailRequest

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


class SignupForm(forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    repassword = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        repassword = cleaned_data.get('repassword')
        if password and repassword and password != repassword:
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data


class EmailRequestForm(forms.Form):
    company_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Google'})
    )
    role_title = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Software Engineer, Data Analyst'})
    )
    resume_text = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Paste your resume text here', 'rows': 8})
    )
    job_description = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Paste the job description here', 'rows': 8})
    )
    tone = forms.ChoiceField(choices=EmailRequest.TONE_CHOICES)

    def clean_resume_text(self):
        text = self.cleaned_data['resume_text'].strip()
        if len(text) < 30:
            raise forms.ValidationError("Resume text looks too short — please paste more detail.")
        return text

    def clean_job_description(self):
        text = self.cleaned_data['job_description'].strip()
        if len(text) < 30:
            raise forms.ValidationError("Job description looks too short — please paste more detail.")
        return text


class ScamCheckForm(forms.Form):
    sender_email = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. hr@company-hiring.com'})
    )
    email_content = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Paste the full email content here', 'rows': 10})
    )

    def clean_email_content(self):
        text = self.cleaned_data['email_content'].strip()
        if len(text) < 20:
            raise forms.ValidationError("Please paste more of the email content for an accurate check.")
        return text