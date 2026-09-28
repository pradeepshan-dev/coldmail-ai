from django.contrib import admin
from .models import UserDetail, EmailRequest, ScamCheck, GmailAccount, SavedTemplate, KnownDomain

# Register your models here.

admin.site.register(UserDetail)
admin.site.register(GmailAccount)


@admin.register(EmailRequest)
class EmailRequestAdmin(admin.ModelAdmin):
    list_display = ('company_name', 'role_title', 'user', 'tone', 'status', 'created_at')
    list_filter = ('tone', 'status', 'created_at')
    search_fields = ('company_name', 'role_title', 'user__username', 'subject_line')
    readonly_fields = ('created_at',)


@admin.register(ScamCheck)
class ScamCheckAdmin(admin.ModelAdmin):
    list_display = ('sender_email', 'user', 'risk_level', 'created_at')
    list_filter = ('risk_level', 'created_at')
    search_fields = ('sender_email', 'user__username')


@admin.register(SavedTemplate)
class SavedTemplateAdmin(admin.ModelAdmin):
    list_display = ('role_title', 'tone', 'subject_line', 'created_at')
    list_filter = ('tone', 'created_at')
    search_fields = ('role_title', 'subject_line')


@admin.register(KnownDomain)
class KnownDomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'risk_level', 'confirmed_count', 'last_confirmed')
    list_filter = ('risk_level',)
    search_fields = ('domain',)