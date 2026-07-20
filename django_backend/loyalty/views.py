"""
Loyalty & Reward Points views for Warungio Marketplace.
Complete CRUD with Flutter-ready JSON responses.
"""

from django.db import transaction
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
from rest_framework import status, generics, permissions, views
from rest_framework.response import Response

from .models import (
    LoyaltyTier, LoyaltyAccount, LoyaltyTransaction,
    LoyaltyReward, LoyaltyRedemption, LoyaltyReferral
)
from .serializers import (
    LoyaltyTierSerializer, LoyaltyAccountSerializer, LoyaltyTransactionSerializer,
    LoyaltyRewardSerializer, LoyaltyRedemptionSerializer, LoyaltyReferralSerializer,
    FlutterLoyaltyDashboardDTO, FlutterPointsEarnDTO, FlutterRewardRedemptionDTO,
)
from accounts.permissions import IsBuyer, IsAdmin
from drf_spectacular.utils import extend_schema


# =============================================================================
# LOYALTY ACCOUNT
# =============================================================================

def get_or_create_account(user):
    """Get or create loyalty account for user."""
    account, created = LoyaltyAccount.objects.get_or_create(
        user=user,
        defaults={
            'tier': LoyaltyTier.objects.filter(is_active=True, sort_order=0).first(),
        }
    )
    if not account.tier:
        default_tier = LoyaltyTier.objects.filter(is_active=True).order_by('sort_order').first()
        if default_tier:
            account.tier = default_tier
            account.save(update_fields=['tier'])
    return account


@extend_schema(exclude=True)
class MyLoyaltyAccountView(views.APIView):
    """Get current user's loyalty account."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        account = get_or_create_account(request.user)
        serializer = LoyaltyAccountSerializer(account)
        return Response(serializer.data)


@extend_schema(exclude=True)
class CalculatePointsView(views.APIView):
    """Calculate how many points would be earned from an order."""
    permission_classes = (permissions.IsAuthenticated,)

    def post(self, request):
        order_total = float(request.data.get('order_total', 0))
        account = get_or_create_account(request.user)
        multiplier = float(account.tier.point_multiplier) if account.tier else 1.0
        
        # Base: 1 point per Rp 1000
        base_points = int(order_total / 1000)
        bonus_points = int(base_points * (multiplier - 1))
        total_points = base_points + bonus_points
        
        return Response({
            'order_total': order_total,
            'points_earned': total_points,
            'base_points': base_points,
            'bonus_points': bonus_points,
            'multiplier_applied': multiplier,
            'tier_name': account.tier.get_name_display() if account.tier else 'Bronze',
        })


@extend_schema(exclude=True)
class EarnPointsView(views.APIView):
    """Manually add points to account (for testing/admin)."""
    permission_classes = (permissions.IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        points = request.data.get('points', 0)
        description = request.data.get('description', '')
        
        if points <= 0:
            return Response({'error': 'Jumlah poin tidak valid.'}, status=status.HTTP_400_BAD_REQUEST)
        
        account = get_or_create_account(request.user)
        account.add_points(points, description)
        
        return Response({
            'message': f'{points} poin berhasil ditambahkan.',
            'points_balance': account.points_balance,
            'tier': account.tier.get_name_display() if account.tier else 'Bronze',
        })


@extend_schema(exclude=True)
class RedeemPointsView(views.APIView):
    """Redeem points for a custom amount (for admin)."""
    permission_classes = (permissions.IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        points = int(request.data.get('points', 0))
        description = request.data.get('description', '')
        
        if points <= 0:
            return Response({'error': 'Jumlah poin tidak valid.'}, status=status.HTTP_400_BAD_REQUEST)
        
        account = get_or_create_account(request.user)
        try:
            account.redeem_points(points, description)
            return Response({
                'message': f'{points} poin berhasil ditukarkan.',
                'points_balance': account.points_balance,
            })
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


# =============================================================================
# TRANSACTIONS
# =============================================================================

class LoyaltyTransactionListView(generics.ListAPIView):
    """List user's loyalty transactions."""
    serializer_class = LoyaltyTransactionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LoyaltyTransaction.objects.none()

        qs = LoyaltyTransaction.objects.filter(user=self.request.user)
        
        # Filters
        ttype = self.request.query_params.get('type')
        if ttype:
            qs = qs.filter(transaction_type=ttype)
        
        period = self.request.query_params.get('period')
        if period:
            from datetime import timedelta
            days = int(period)
            qs = qs.filter(created_at__gte=timezone.now() - timedelta(days=days))
        
        return qs[:100]


@extend_schema(exclude=True)
class RecentTransactionsView(generics.ListAPIView):
    """Get recent loyalty transactions."""
    serializer_class = LoyaltyTransactionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return LoyaltyTransaction.objects.filter(
            user=self.request.user
        )[:20]


# =============================================================================
# REWARDS
# =============================================================================

@extend_schema(exclude=True)
class LoyaltyRewardListView(generics.ListAPIView):
    """List available rewards for current user's tier."""
    serializer_class = LoyaltyRewardSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        account = get_or_create_account(self.request.user)
        qs = LoyaltyReward.objects.filter(is_active=True)
        
        # Filter by user's tier if applicable
        if account.tier:
            qs = qs.filter(
                Q(valid_for_tiers__isnull=True) |
                Q(valid_for_tiers=account.tier) |
                Q(valid_for_tiers__isnull=True)
            ).distinct()
        
        return qs.order_by('sort_order', 'points_required')


class LoyaltyRewardDetailView(generics.RetrieveAPIView):
    """Get reward detail."""
    queryset = LoyaltyReward.objects.filter(is_active=True)
    serializer_class = LoyaltyRewardSerializer
    permission_classes = (permissions.IsAuthenticated,)


@extend_schema(exclude=True)
class RedeemRewardView(views.APIView):
    """Redeem a reward using points."""
    permission_classes = (permissions.IsAuthenticated,)

    @transaction.atomic
    def post(self, request, pk):
        reward = LoyaltyReward.objects.filter(is_active=True, pk=pk).first()
        if not reward:
            return Response({'error': 'Reward tidak ditemukan.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check max usage
        if reward.max_usage > 0 and reward.usage_count >= reward.max_usage:
            return Response({'error': 'Reward sudah habis.'}, status=status.HTTP_400_BAD_REQUEST)
        
        account = get_or_create_account(request.user)
        
        # Check balance
        if account.points_balance < reward.points_required:
            return Response({
                'error': 'Poin tidak mencukupi.',
                'points_balance': account.points_balance,
                'points_required': reward.points_required,
                'points_short': reward.points_required - account.points_balance,
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            transaction = account.redeem_points(
                reward.points_required,
                f'Penukaran: {reward.name}'
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        
        # Generate voucher code
        import uuid
        voucher_code = f'LY-{uuid.uuid4().hex[:8].upper()}'
        
        redemption = LoyaltyRedemption.objects.create(
            user=request.user,
            reward=reward,
            transaction=transaction,
            points_spent=reward.points_required,
            status='approved',
            voucher_code=voucher_code,
            valid_until=timezone.now() + timedelta(days=reward.valid_days),
        )
        
        # Update reward usage count
        reward.usage_count += 1
        reward.save(update_fields=['usage_count'])
        
        return Response({
            'message': f'Reward {reward.name} berhasil ditukarkan!',
            'redemption_id': redemption.id,
            'reward_name': reward.name,
            'points_spent': reward.points_required,
            'points_balance_after': account.points_balance,
            'voucher_code': voucher_code,
            'valid_until': redemption.valid_until,
            'status': 'approved',
        })


# =============================================================================
# REDEMPTIONS
# =============================================================================

@extend_schema(exclude=True)
class MyRedemptionsView(generics.ListAPIView):
    """List user's redemptions."""
    serializer_class = LoyaltyRedemptionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return LoyaltyRedemption.objects.filter(user=self.request.user).select_related(
            'reward', 'transaction'
        ).order_by('-created_at')


class RedemptionDetailView(generics.RetrieveAPIView):
    """Get redemption detail."""
    serializer_class = LoyaltyRedemptionSerializer
    permission_classes = (permissions.IsAuthenticated,)

    def get_queryset(self):
        return LoyaltyRedemption.objects.filter(user=self.request.user)


# =============================================================================
# TIERS
# =============================================================================

class LoyaltyTierListView(generics.ListAPIView):
    """List all loyalty tiers."""
    queryset = LoyaltyTier.objects.filter(is_active=True)
    serializer_class = LoyaltyTierSerializer
    permission_classes = (permissions.AllowAny,)


# =============================================================================
# REFERRAL
# =============================================================================

@extend_schema(exclude=True)
class MyReferralView(views.APIView):
    """Get user's referral code and stats."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        import hashlib
        # Generate referral code from user ID
        referral_code = f'WRG{request.user.id:06d}'
        
        successful_referrals = LoyaltyReferral.objects.filter(
            referrer=request.user,
            first_purchase_made=True
        ).count()
        
        total_bonus = LoyaltyReferral.objects.filter(
            referrer=request.user,
            referrer_bonus_given=True
        ).aggregate(total=Sum('referrer_bonus'))['total'] or 0
        
        return Response({
            'referral_code': referral_code,
            'referral_url': f'/auth/register/?ref={referral_code}',
            'successful_referrals': successful_referrals,
            'total_bonus_earned': total_bonus,
            'bonus_per_referral': 5000,  # 5000 points per successful referral
        })


@extend_schema(exclude=True)
class ClaimReferralView(views.APIView):
    """Claim referral bonus when referred user registers."""
    permission_classes = (permissions.IsAuthenticated,)

    @transaction.atomic
    def post(self, request):
        code = request.data.get('referral_code', '')
        
        # Parse referral code
        try:
            if code.startswith('WRG'):
                referrer_id = int(code[3:])
            else:
                return Response({'error': 'Kode referral tidak valid.'}, status=status.HTTP_400_BAD_REQUEST)
        except (ValueError, IndexError):
            return Response({'error': 'Kode referral tidak valid.'}, status=status.HTTP_400_BAD_REQUEST)
        
        if referrer_id == request.user.id:
            return Response({'error': 'Tidak bisa menggunakan kode referral sendiri.'}, status=status.HTTP_400_BAD_REQUEST)
        
        from accounts.models import User
        referrer = User.objects.filter(id=referrer_id).first()
        if not referrer:
            return Response({'error': 'Kode referral tidak valid.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if already referred
        existing = LoyaltyReferral.objects.filter(
            referred=request.user
        ).first()
        if existing:
            return Response({'error': 'Kode referral sudah pernah digunakan.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create referral
        referral = LoyaltyReferral.objects.create(
            referrer=referrer,
            referred=request.user,
            referral_code=code,
            referrer_bonus=5000,
            referred_bonus=2000,
        )
        
        # Give bonus to referrer
        referrer_account = get_or_create_account(referrer)
        referrer_account.add_points(5000, f'Bonus referral: {request.user.full_name or request.user.email}')
        
        # Give bonus to new user
        user_account = get_or_create_account(request.user)
        user_account.add_points(2000, 'Bonus pendaftaran referral')
        
        return Response({
            'message': 'Kode referral berhasil diklaim! Bonus poin telah ditambahkan.',
            'your_bonus': 2000,
            'points_balance': user_account.points_balance,
        })


# =============================================================================
# DASHBOARD (Flutter-ready)
# =============================================================================

@extend_schema(exclude=True)
class LoyaltyDashboardView(views.APIView):
    """Complete loyalty dashboard for Flutter."""
    permission_classes = (permissions.IsAuthenticated,)

    def get(self, request):
        account = get_or_create_account(request.user)
        
        # Get recent transactions
        recent_transactions = LoyaltyTransaction.objects.filter(
            user=request.user
        )[:10]
        
        # Get available rewards
        available_rewards = LoyaltyReward.objects.filter(is_active=True)
        if account.tier:
            available_rewards = available_rewards.filter(
                Q(valid_for_tiers__isnull=True) |
                Q(valid_for_tiers=account.tier)
            ).distinct()
        
        # Get active redemptions
        active_redemptions = LoyaltyRedemption.objects.filter(
            user=request.user,
            status__in=['approved', 'pending']
        )
        
        # Get tiers
        tiers = LoyaltyTier.objects.filter(is_active=True).order_by('sort_order')
        
        # This month stats
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0)
        this_month_earned = LoyaltyTransaction.objects.filter(
            user=request.user,
            transaction_type__in=['earn', 'bonus', 'referral', 'birthday', 'review'],
            created_at__gte=month_start
        ).aggregate(total=Sum('points'))['total'] or 0
        
        this_month_redeemed = LoyaltyTransaction.objects.filter(
            user=request.user,
            transaction_type__in=['redeem'],
            created_at__gte=month_start
        ).aggregate(total=Sum('points'))['total'] or 0
        
        account_serializer = LoyaltyAccountSerializer(account)
        
        return Response({
            'account': account_serializer.data,
            'recent_transactions': LoyaltyTransactionSerializer(recent_transactions, many=True).data,
            'available_rewards': LoyaltyRewardSerializer(available_rewards, many=True).data,
            'active_redemptions': LoyaltyRedemptionSerializer(active_redemptions, many=True).data,
            'tiers': LoyaltyTierSerializer(tiers, many=True).data,
            'stats': {
                'total_points_earned': account.total_points_earned,
                'this_month_earned': this_month_earned,
                'this_month_redeemed': abs(this_month_redeemed),
                'points_to_next_tier': 0,
            },
        })


# =============================================================================
# ADMIN
# =============================================================================

class AdminLoyaltyAccountListView(generics.ListAPIView):
    """List all loyalty accounts (admin only)."""
    serializer_class = LoyaltyAccountSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)
    
    def get_queryset(self):
        return LoyaltyAccount.objects.all().select_related('user', 'tier').order_by('-points_balance')[:100]


class AdminRewardCreateView(generics.CreateAPIView):
    """Create new reward (admin only)."""
    serializer_class = LoyaltyRewardSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def perform_create(self, serializer):
        serializer.save()


class AdminTierListView(generics.ListAPIView):
    """List all tiers with member count (admin only)."""
    serializer_class = LoyaltyTierSerializer
    permission_classes = (permissions.IsAuthenticated, IsAdmin)

    def get_queryset(self):
        return LoyaltyTier.objects.all().order_by('sort_order')
