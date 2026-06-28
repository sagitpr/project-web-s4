"""
Accounts URL configuration for Warungio Marketplace.
"""

from django.urls import path
from . import views

from . import social as social_views

urlpatterns = [
    # Authentication
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('check-auth/', views.CheckAuthView.as_view(), name='check-auth'),
    path('token-refresh/', views.TokenRefreshView.as_view(), name='accounts-token-refresh'),
    
    # Profile
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    
    # OTP
    path('otp/request/', views.OTPRequestView.as_view(), name='otp-request'),
    path('otp/verify/', views.OTPVerifyView.as_view(), name='otp-verify'),
    path('otp/resend/', views.ResendOTPView.as_view(), name='otp-resend'),
    
    # Password Reset
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),
    
    # Social Authentication
    path('social/google/', social_views.GoogleLoginView.as_view(), name='social-google'),
    path('social/facebook/', social_views.FacebookLoginView.as_view(), name='social-facebook'),
    path('social/apple/', social_views.AppleLoginView.as_view(), name='social-apple'),
    path('social/accounts/', social_views.SocialAccountStatusView.as_view(), name='social-accounts'),
    path('social/config/google/', social_views.GoogleAuthConfigView.as_view(), name='social-config-google'),
    path('social/config/facebook/', social_views.FacebookAuthConfigView.as_view(), name='social-config-facebook'),
]
