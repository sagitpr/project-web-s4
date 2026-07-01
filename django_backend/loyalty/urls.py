"""
Loyalty URL configuration for Warungio Marketplace.
Flutter-ready API endpoints.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Account
    path('account/', views.MyLoyaltyAccountView.as_view(), name='my-loyalty-account'),
    path('account/earn/', views.EarnPointsView.as_view(), name='earn-points'),
    path('account/redeem/', views.RedeemPointsView.as_view(), name='redeem-points'),
    path('account/calculate/', views.CalculatePointsView.as_view(), name='calculate-points'),

    # Transactions
    path('transactions/', views.LoyaltyTransactionListView.as_view(), name='loyalty-transactions'),
    path('transactions/recent/', views.RecentTransactionsView.as_view(), name='recent-transactions'),

    # Rewards
    path('rewards/', views.LoyaltyRewardListView.as_view(), name='loyalty-rewards'),
    path('rewards/<int:pk>/', views.LoyaltyRewardDetailView.as_view(), name='loyalty-reward-detail'),
    path('rewards/<int:pk>/redeem/', views.RedeemRewardView.as_view(), name='redeem-reward'),

    # Redemptions
    path('redemptions/', views.MyRedemptionsView.as_view(), name='my-redemptions'),
    path('redemptions/<int:pk>/', views.RedemptionDetailView.as_view(), name='redemption-detail'),

    # Tiers
    path('tiers/', views.LoyaltyTierListView.as_view(), name='loyalty-tiers'),

    # Referral
    path('referral/', views.MyReferralView.as_view(), name='my-referral'),
    path('referral/claim/', views.ClaimReferralView.as_view(), name='claim-referral'),

    # Dashboard (Flutter-ready)
    path('dashboard/', views.LoyaltyDashboardView.as_view(), name='loyalty-dashboard'),

    # Admin
    path('admin/accounts/', views.AdminLoyaltyAccountListView.as_view(), name='admin-loyalty-accounts'),
    path('admin/rewards/create/', views.AdminRewardCreateView.as_view(), name='admin-reward-create'),
    path('admin/tiers/', views.AdminTierListView.as_view(), name='admin-loyalty-tiers'),
]
