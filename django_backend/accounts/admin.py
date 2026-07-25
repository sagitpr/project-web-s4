from django.contrib import admin
from .models import User, OTP, UserSession, SocialAccount, LoginAttempt, AdminRole, AdminAuditLog, AdminVerification


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'full_name', 'role', 'is_staff', 'is_superuser', 'is_verified', 'is_active']
    list_filter = ['role', 'is_staff', 'is_superuser', 'is_verified', 'is_active']
    search_fields = ['email', 'full_name', 'username']
    ordering = ['-date_joined']


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ['email', 'purpose', 'is_valid', 'is_used', 'created_at', 'expires_at']
    list_filter = ['purpose', 'is_valid', 'is_used']
    search_fields = ['email']
    readonly_fields = ['otp_code', 'otp_code_hash', 'created_at']


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['user', 'device_type', 'is_active', 'last_activity']
    list_filter = ['device_type', 'is_active']


@admin.register(SocialAccount)
class SocialAccountAdmin(admin.ModelAdmin):
    list_display = ['user', 'provider', 'created_at']
    list_filter = ['provider']


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ['email', 'ip_address', 'was_successful', 'attempted_at']
    list_filter = ['was_successful']


@admin.register(AdminRole)
class AdminRoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'level', 'is_active']
    list_filter = ['is_active']
    readonly_fields = ['created_at']


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ['admin_email', 'action', 'target_email', 'created_at']
    list_filter = ['action', 'created_at']
    search_fields = ['admin_email', 'target_email', 'description']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(AdminVerification)
class AdminVerificationAdmin(admin.ModelAdmin):
    list_display = ['email', 'status', 'attempts', 'created_at', 'expires_at']
    list_filter = ['status']
    search_fields = ['email']
    readonly_fields = ['otp_code', 'otp_code_hash', 'created_at']
