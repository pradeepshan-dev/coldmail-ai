"""
URL configuration for coldmail_ai project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
"""
URL configuration for coldmail_ai project.
"""
from django.contrib import admin
from django.urls import path
from emailgen import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('registration/', views.registration, name='registration'),
    path('', views.home, name='home'),
    path('logout/', views.logout_view, name='logout'),
    path('create-email/', views.create_email, name='create_email'),
    path('email-result/<int:pk>/', views.email_result, name='email_result'),
    path('email-history/', views.email_history, name='email_history'),
    path('ai-chatbot/', views.email_chatbot, name='email_chatbot'),
    path('ai-chatbot/<int:pk>/', views.email_chatbot, name='email_chatbot_specific'),
    path('email-refine/<int:pk>/', views.refine_email, name='refine_email'),
    path('scam-checker/', views.scam_checker, name='scam_checker'),
    path('gmail/connect/', views.gmail_connect, name='gmail_connect'),
    path('gmail/callback/', views.gmail_callback, name='gmail_callback'),
    path('gmail/send/<int:pk>/', views.send_email_gmail, name='send_email_gmail'),
    path('gmail/scan/', views.gmail_scan, name='gmail_scan'),
    path('email-status/<int:pk>/', views.update_status, name='update_status'),
    path('profile/picture/', views.update_profile_picture, name='update_profile_picture'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)