"""
Comprehensive test suite for the Support / Help Center app.
Tests models, admin configuration, API endpoints, and WebSocket consumer.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.contrib.admin import site as admin_site
from rest_framework import status
from rest_framework.test import APIClient

from .models import (
    HelpCategory, HelpArticle, FAQ, BannerPromo,
    ContactInfo, SupportInfo, ChatQuickReply,
    SupportConversation, SupportMessage,
)
from .admin import (
    HelpCategoryAdmin, HelpArticleAdmin, FAQAdmin,
    BannerPromoAdmin, ContactInfoAdmin, SupportInfoAdmin,
    ChatQuickReplyAdmin,
)
from accounts.models import User


# =============================================================================
# HELPER / BASE
# =============================================================================

class BaseTestDataMixin:
    """Mixin to create seed data for tests."""

    def create_categories(self):
        self.cat_pesanan = HelpCategory.objects.create(
            name='Pesanan', slug='pesanan', icon='package',
            description='Info seputar pesanan dan pengiriman', sort_order=1
        )
        self.cat_akun = HelpCategory.objects.create(
            name='Akun', slug='akun', icon='user',
            description='Pengelolaan akun', sort_order=2
        )
        self.cat_inactive = HelpCategory.objects.create(
            name='Inactive', slug='inactive', icon='x',
            description='Hidden', sort_order=99, is_active=False
        )

    def create_articles(self):
        self.article1 = HelpArticle.objects.create(
            category=self.cat_pesanan,
            title='Cara Melacak Pesanan',
            slug='cara-melacak-pesanan',
            content='<p>Langkah melacak pesanan...</p>',
            excerpt='Panduan melacak pesanan.',
            is_featured=True,
            views_count=100,
        )
        self.article2 = HelpArticle.objects.create(
            category=self.cat_pesanan,
            title='Batalkan Pesanan',
            slug='batalkan-pesanan',
            content='<p>Cara membatalkan...</p>',
            excerpt='Panduan pembatalan.',
            is_featured=False,
            views_count=50,
        )
        self.article3 = HelpArticle.objects.create(
            category=self.cat_akun,
            title='Cara Mendaftar',
            slug='cara-mendaftar',
            content='<p>Langkah daftar...</p>',
            excerpt='Panduan pendaftaran.',
            is_featured=True,
            views_count=200,
        )
        self.article_unpublished = HelpArticle.objects.create(
            category=self.cat_akun,
            title='Draft Article',
            slug='draft-article',
            content='<p>Not published...</p>',
            is_published=False,
        )

    def create_faqs(self):
        self.faq1 = FAQ.objects.create(
            question='Apakah Warungio melayani seluruh Indonesia?',
            answer='Saat ini melayani kota-kota besar.',
            category=self.cat_pesanan,
            sort_order=1,
        )
        self.faq2 = FAQ.objects.create(
            question='Bagaimana cara reset password?',
            answer='Buka lupa password di halaman login.',
            category=self.cat_akun,
            sort_order=2,
        )
        self.faq_unpublished = FAQ.objects.create(
            question='Unpublished FAQ?',
            answer='Hidden FAQ.',
            is_published=False,
        )

    def create_contacts(self):
        self.contact_wa = ContactInfo.objects.create(
            contact_type='whatsapp', label='Chat WhatsApp',
            value='+6281234567890', sort_order=1,
            operating_hours='24 jam, 7 hari',
        )
        self.contact_email = ContactInfo.objects.create(
            contact_type='email', label='Email Support',
            value='support@warungio.com', sort_order=2,
        )
        self.contact_inactive = ContactInfo.objects.create(
            contact_type='phone', label='Telepon Inactive',
            value='+6212345', sort_order=99, is_active=False,
        )

    def create_banners(self):
        now = timezone.now()
        self.banner_active = BannerPromo.objects.create(
            title='Belanja Hemat',
            subtitle='Promo spesial!',
            link_url='/products/',
            position='help_bottom',
            is_active=True,
            start_date=now - timedelta(days=1),
            end_date=now + timedelta(days=30),
        )
        self.banner_expired = BannerPromo.objects.create(
            title='Expired Banner',
            subtitle='Already over.',
            position='help_bottom',
            is_active=True,
            start_date=now - timedelta(days=60),
            end_date=now - timedelta(days=1),
        )
        self.banner_inactive = BannerPromo.objects.create(
            title='Inactive Banner',
            subtitle='Not active.',
            position='help_hero',
            is_active=False,
        )
        self.banner_no_dates = BannerPromo.objects.create(
            title='Always Active',
            subtitle='No date limits.',
            position='sidebar',
            is_active=True,
        )

    def create_support_infos(self):
        self.info1 = SupportInfo.objects.create(
            key='fast_response', title='Respon Cepat',
            description='Tim kami merespon cepat.', sort_order=1,
        )
        self.info2 = SupportInfo.objects.create(
            key='24_7', title='24/7 Siap Membantu',
            description='Non-stop.', sort_order=2,
        )
        self.info_inactive = SupportInfo.objects.create(
            key='old_info', title='Old Info',
            description='Inactive.', sort_order=99, is_active=False,
        )

    def create_quick_replies(self):
        self.qr_order = ChatQuickReply.objects.create(
            category='order', label='Status Pesanan',
            message_template='Halo admin, cek status pesanan.',
            sort_order=1,
        )
        self.qr_payment = ChatQuickReply.objects.create(
            category='payment', label='Pembayaran',
            message_template='Halo admin, tanya pembayaran.',
            sort_order=2,
        )
        self.qr_inactive = ChatQuickReply.objects.create(
            category='other', label='Lainnya Inactive',
            message_template='Inactive.',
            sort_order=99, is_active=False,
        )

    def create_conversation_and_messages(self, user=None):
        conv = SupportConversation.objects.create(
            subject='Test Chat', user=user, is_active=True,
        )
        msg1 = SupportMessage.objects.create(
            conversation=conv, sender=user,
            content='Halo, ada yang bisa dibantu?', is_from_user=True,
        )
        msg2 = SupportMessage.objects.create(
            conversation=conv, sender=user,
            content='Saya ingin bertanya...', is_from_user=True, is_read=True,
        )
        return conv, [msg1, msg2]

    def create_all(self):
        self.create_categories()
        self.create_articles()
        self.create_faqs()
        self.create_contacts()
        self.create_banners()
        self.create_support_infos()
        self.create_quick_replies()


# =============================================================================
# MODEL TESTS
# =============================================================================

class HelpCategoryModelTests(TestCase, BaseTestDataMixin):
    """Tests for HelpCategory model."""

    def setUp(self):
        self.create_categories()

    def test_str(self):
        self.assertEqual(str(self.cat_pesanan), 'Pesanan')

    def test_ordering(self):
        cats = list(HelpCategory.objects.all())
        self.assertEqual(cats[0], self.cat_pesanan)
        self.assertEqual(cats[1], self.cat_akun)

    def test_active_filter(self):
        active = HelpCategory.objects.filter(is_active=True)
        self.assertEqual(active.count(), 2)

    def test_db_table(self):
        self.assertEqual(HelpCategory._meta.db_table, 'help_categories')

    def test_verbose_name(self):
        self.assertEqual(HelpCategory._meta.verbose_name, 'Kategori Bantuan')

    def test_fields(self):
        cat = self.cat_pesanan
        self.assertEqual(cat.name, 'Pesanan')
        self.assertEqual(cat.slug, 'pesanan')
        self.assertEqual(cat.icon, 'package')
        self.assertEqual(cat.sort_order, 1)
        self.assertTrue(cat.is_active)
        self.assertIsNotNone(cat.created_at)

    def test_slug_unique(self):
        with self.assertRaises(Exception):
            HelpCategory.objects.create(name='Duplicate', slug='pesanan')


class HelpArticleModelTests(TestCase, BaseTestDataMixin):
    """Tests for HelpArticle model."""

    def setUp(self):
        self.create_categories()
        self.create_articles()
        self.staff_user = User.objects.create_user(
            username='staffwriter', email='staff@test.com',
            password='Test123!', full_name='Staff Writer', is_staff=True,
        )

    def test_str(self):
        self.assertEqual(str(self.article1), 'Cara Melacak Pesanan')

    def test_increment_views(self):
        old = self.article1.views_count
        self.article1.increment_views()
        self.article1.refresh_from_db()
        self.assertEqual(self.article1.views_count, old + 1)

    def test_increment_views_updates_only_views(self):
        self.article1.increment_views()
        self.article1.refresh_from_db()
        self.assertEqual(self.article1.views_count, 101)

    def test_unpublished_excluded_by_default(self):
        published = HelpArticle.objects.filter(is_published=True)
        self.assertNotIn(self.article_unpublished, published)

    def test_foreign_key_relations(self):
        self.assertEqual(self.article1.category, self.cat_pesanan)
        self.assertIn(self.article1, self.cat_pesanan.articles.all())

    def test_author_nullable(self):
        self.assertIsNone(self.article1.author)

    def test_author_assignment(self):
        article = HelpArticle.objects.create(
            category=self.cat_pesanan, title='Staff Article',
            slug='staff-article', content='<p>Content</p>',
            author=self.staff_user,
        )
        self.assertEqual(article.author, self.staff_user)

    def test_db_table(self):
        self.assertEqual(HelpArticle._meta.db_table, 'help_articles')

    def test_tags_field(self):
        article = HelpArticle.objects.create(
            category=self.cat_pesanan, title='Tagged Article',
            slug='tagged-article', content='<p>Content</p>',
            tags='tag1,tag2,tag3',
        )
        self.assertEqual(article.tags, 'tag1,tag2,tag3')

    def test_default_published_at(self):
        self.assertIsNotNone(self.article1.published_at)


class FAQModelTests(TestCase, BaseTestDataMixin):
    """Tests for FAQ model."""

    def setUp(self):
        self.create_categories()
        self.create_faqs()

    def test_str(self):
        self.assertEqual(str(self.faq1), 'Apakah Warungio melayani seluruh Indonesia?')

    def test_ordering(self):
        faqs = list(FAQ.objects.filter(is_published=True))
        self.assertEqual(faqs[0], self.faq1)
        self.assertEqual(faqs[1], self.faq2)

    def test_published_filter(self):
        published = FAQ.objects.filter(is_published=True)
        self.assertEqual(published.count(), 2)

    def test_category_nullable(self):
        faq_no_cat = FAQ.objects.create(
            question='No category?', answer='Yes no category.',
        )
        self.assertIsNone(faq_no_cat.category)

    def test_db_table(self):
        self.assertEqual(FAQ._meta.db_table, 'faqs')


class BannerPromoModelTests(TestCase, BaseTestDataMixin):
    """Tests for BannerPromo model."""

    def setUp(self):
        self.create_banners()

    def test_str(self):
        self.assertEqual(str(self.banner_active), 'Belanja Hemat')

    def test_is_expired_true(self):
        self.assertTrue(self.banner_expired.is_expired())

    def test_is_expired_false(self):
        self.assertFalse(self.banner_active.is_expired())

    def test_is_expired_no_end_date(self):
        self.assertFalse(self.banner_no_dates.is_expired())

    def test_active_banners_exclude_expired_and_inactive(self):
        now = timezone.now()
        active = BannerPromo.objects.filter(
            is_active=True
        ).exclude(
            end_date__lt=now
        ).exclude(
            start_date__gt=now
        )
        self.assertIn(self.banner_active, active)
        self.assertIn(self.banner_no_dates, active)
        self.assertNotIn(self.banner_expired, active)
        self.assertNotIn(self.banner_inactive, active)

    def test_db_table(self):
        self.assertEqual(BannerPromo._meta.db_table, 'banner_promos')


class ContactInfoModelTests(TestCase, BaseTestDataMixin):
    """Tests for ContactInfo model."""

    def setUp(self):
        self.create_contacts()

    def test_str(self):
        self.assertEqual(str(self.contact_wa), 'WhatsApp: Chat WhatsApp')

    def test_contact_type_unique(self):
        with self.assertRaises(Exception):
            ContactInfo.objects.create(
                contact_type='whatsapp', label='Duplicate',
                value='+6200000000000',
            )

    def test_active_filter(self):
        active = ContactInfo.objects.filter(is_active=True)
        self.assertNotIn(self.contact_inactive, active)

    def test_db_table(self):
        self.assertEqual(ContactInfo._meta.db_table, 'contact_infos')

    def test_operating_hours(self):
        self.assertIsNotNone(self.contact_wa.operating_hours)


class SupportInfoModelTests(TestCase, BaseTestDataMixin):
    """Tests for SupportInfo model."""

    def setUp(self):
        self.create_support_infos()

    def test_str(self):
        self.assertEqual(str(self.info1), 'Respon Cepat')

    def test_key_unique(self):
        with self.assertRaises(Exception):
            SupportInfo.objects.create(
                key='fast_response', title='Duplicate', description='dup'
            )

    def test_active_filter(self):
        active = SupportInfo.objects.filter(is_active=True)
        self.assertEqual(active.count(), 2)

    def test_db_table(self):
        self.assertEqual(SupportInfo._meta.db_table, 'support_infos')


class ChatQuickReplyModelTests(TestCase, BaseTestDataMixin):
    """Tests for ChatQuickReply model."""

    def setUp(self):
        self.create_quick_replies()

    def test_str(self):
        expected = '[Status Pesanan] Status Pesanan'
        self.assertEqual(str(self.qr_order), expected)

    def test_active_filter(self):
        active = ChatQuickReply.objects.filter(is_active=True)
        self.assertEqual(active.count(), 2)

    def test_db_table(self):
        self.assertEqual(ChatQuickReply._meta.db_table, 'chat_quick_replies')


class SupportConversationModelTests(TestCase, BaseTestDataMixin):
    """Tests for SupportConversation model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='convuser', email='conv@test.com',
            password='Test123!', full_name='Conv User',
        )
        self.conv, self.msgs = self.create_conversation_and_messages(self.user)

    def test_str(self):
        expected = f'Test Chat ({self.conv.created_at.date()})'
        self.assertEqual(str(self.conv), expected)

    def test_defaults(self):
        conv = SupportConversation.objects.create(subject='New Chat')
        self.assertTrue(conv.is_active)
        self.assertFalse(conv.is_resolved)
        self.assertIsNone(conv.user)

    def test_message_relation(self):
        self.assertEqual(self.conv.messages.count(), 2)
        self.assertEqual(self.conv.messages.first(), self.msgs[0])

    def test_db_table(self):
        self.assertEqual(SupportConversation._meta.db_table, 'support_conversations')


class SupportMessageModelTests(TestCase, BaseTestDataMixin):
    """Tests for SupportMessage model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='msgsender', email='sender@test.com',
            password='Test123!', full_name='Msg Sender',
        )
        self.conv, self.msgs = self.create_conversation_and_messages(self.user)

    def test_str(self):
        expected = f'Pesan #{self.msgs[0].id} ({self.msgs[0].created_at:%H:%M})'
        self.assertEqual(str(self.msgs[0]), expected)

    def test_is_from_user_default(self):
        self.assertTrue(self.msgs[0].is_from_user)

    def test_is_read_default(self):
        self.assertFalse(self.msgs[0].is_read)
        self.assertTrue(self.msgs[1].is_read)

    def test_sender_nullable(self):
        msg = SupportMessage.objects.create(
            conversation=self.conv, content='Guest message',
        )
        self.assertIsNone(msg.sender)

    def test_ordering(self):
        msgs = list(self.conv.messages.all())
        self.assertEqual(msgs[0], self.msgs[0])
        self.assertEqual(msgs[1], self.msgs[1])

    def test_db_table(self):
        self.assertEqual(SupportMessage._meta.db_table, 'support_messages')

    def test_conversation_cascade(self):
        msg_id = self.msgs[0].id
        self.conv.delete()
        self.assertFalse(SupportMessage.objects.filter(id=msg_id).exists())


# =============================================================================
# ADMIN CONFIGURATION TESTS
# =============================================================================

class AdminRegistrationTests(TestCase):
    """Test all admin classes are properly registered."""

    def test_help_category_admin_registered(self):
        self.assertIsInstance(admin_site._registry[HelpCategory], HelpCategoryAdmin)

    def test_help_article_admin_registered(self):
        self.assertIsInstance(admin_site._registry[HelpArticle], HelpArticleAdmin)

    def test_faq_admin_registered(self):
        self.assertIsInstance(admin_site._registry[FAQ], FAQAdmin)

    def test_banner_promo_admin_registered(self):
        self.assertIsInstance(admin_site._registry[BannerPromo], BannerPromoAdmin)

    def test_contact_info_admin_registered(self):
        self.assertIsInstance(admin_site._registry[ContactInfo], ContactInfoAdmin)

    def test_support_info_admin_registered(self):
        self.assertIsInstance(admin_site._registry[SupportInfo], SupportInfoAdmin)

    def test_chat_quick_reply_admin_registered(self):
        self.assertIsInstance(
            admin_site._registry[ChatQuickReply], ChatQuickReplyAdmin
        )


class HelpCategoryAdminTests(TestCase, BaseTestDataMixin):
    """Test HelpCategoryAdmin configuration."""

    def setUp(self):
        self.create_categories()
        self.admin = HelpCategoryAdmin(model=HelpCategory, admin_site=admin_site)

    def test_list_display(self):
        expected = ('name', 'slug', 'sort_order', 'is_active', 'article_count')
        self.assertEqual(self.admin.list_display, expected)

    def test_list_filter(self):
        self.assertIn('is_active', self.admin.list_filter)

    def test_search_fields(self):
        self.assertIn('name', self.admin.search_fields)
        self.assertIn('description', self.admin.search_fields)

    def test_prepopulated_fields(self):
        self.assertEqual(self.admin.prepopulated_fields, {'slug': ('name',)})

    def test_list_editable(self):
        self.assertIn('sort_order', self.admin.list_editable)
        self.assertIn('is_active', self.admin.list_editable)


class HelpArticleAdminTests(TestCase, BaseTestDataMixin):
    """Test HelpArticleAdmin configuration."""

    def setUp(self):
        self.create_categories()
        self.admin = HelpArticleAdmin(model=HelpArticle, admin_site=admin_site)

    def test_list_display(self):
        fields = self.admin.list_display
        self.assertIn('title', fields)
        self.assertIn('category', fields)
        self.assertIn('is_published', fields)
        self.assertIn('views_count', fields)

    def test_readonly_fields(self):
        self.assertIn('views_count', self.admin.readonly_fields)
        self.assertIn('helpful_count', self.admin.readonly_fields)
        self.assertIn('not_helpful_count', self.admin.readonly_fields)

    def test_prepopulated_fields(self):
        self.assertEqual(self.admin.prepopulated_fields, {'slug': ('title',)})


class FAQAdminTests(TestCase):
    """Test FAQAdmin configuration."""

    def setUp(self):
        self.admin = FAQAdmin(model=FAQ, admin_site=admin_site)

    def test_list_display(self):
        self.assertIn('question', self.admin.list_display)
        self.assertIn('is_published', self.admin.list_display)


class BannerPromoAdminTests(TestCase):
    """Test BannerPromoAdmin configuration."""

    def setUp(self):
        self.admin = BannerPromoAdmin(model=BannerPromo, admin_site=admin_site)

    def test_list_display_contains_banner_preview(self):
        self.assertIn('banner_preview', self.admin.list_display)


# =============================================================================
# API ENDPOINT TESTS
# =============================================================================

class SupportAPITestBase(TestCase, BaseTestDataMixin):
    """Base class for API tests with common setup."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='apiuser', email='api@test.com',
            password='Test123!', full_name='API User',
        )

    def setUp(self):
        self.client = APIClient()
        self.create_all()

    def get_url(self, view_name, *args, **kwargs):
        return reverse(view_name, *args, **kwargs)


class HelpCategoryAPITests(SupportAPITestBase):
    """Tests for HelpCategory API endpoint."""

    def test_list_categories(self):
        response = self.client.get(self.get_url('help-category-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)

    def test_retrieve_category_by_slug(self):
        url = self.get_url('help-category-detail', kwargs={'slug': 'pesanan'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Pesanan')

    def test_retrieve_nonexistent_slug_returns_404(self):
        url = self.get_url('help-category-detail', kwargs={'slug': 'nonexistent'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_inactive_category_not_listed(self):
        response = self.client.get(self.get_url('help-category-list'))
        slugs = [cat['slug'] for cat in response.data['results']]
        self.assertNotIn('inactive', slugs)

    def test_serializer_article_count(self):
        url = self.get_url('help-category-detail', kwargs={'slug': 'pesanan'})
        response = self.client.get(url)
        self.assertIn('article_count', response.data)
        self.assertEqual(response.data['article_count'], 2)


class HelpArticleAPITests(SupportAPITestBase):
    """Tests for HelpArticle API endpoint."""

    def setUp(self):
        super().setUp()
        self.client.force_authenticate(user=self.user)

    def test_list_returns_only_published(self):
        response = self.client.get(self.get_url('help-article-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slugs = [a['slug'] for a in response.data['results']]
        self.assertIn('cara-melacak-pesanan', slugs)
        self.assertNotIn('draft-article', slugs)

    def test_list_uses_list_serializer(self):
        response = self.client.get(self.get_url('help-article-list'))
        self.assertIn('category_name', response.data['results'][0])
        self.assertNotIn('content', response.data['results'][0])

    def test_retrieve_uses_detail_serializer(self):
        url = self.get_url('help-article-detail', kwargs={'slug': 'cara-melacak-pesanan'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('content', response.data)
        self.assertIn('helpful_count', response.data)

    def test_retrieve_increments_views(self):
        old_views = self.article1.views_count
        url = self.get_url('help-article-detail', kwargs={'slug': 'cara-melacak-pesanan'})
        self.client.get(url)
        self.article1.refresh_from_db()
        self.assertEqual(self.article1.views_count, old_views + 1)

    def test_filter_by_category(self):
        response = self.client.get(self.get_url('help-article-list'), {'category': 'akun'})
        slugs = [a['slug'] for a in response.data['results']]
        self.assertIn('cara-mendaftar', slugs)
        self.assertNotIn('cara-melacak-pesanan', slugs)

    def test_filter_by_search_title(self):
        response = self.client.get(self.get_url('help-article-list'), {'search': 'Melacak'})
        slugs = [a['slug'] for a in response.data['results']]
        self.assertIn('cara-melacak-pesanan', slugs)

    def test_filter_featured(self):
        response = self.client.get(self.get_url('help-article-list'), {'featured': 'true'})
        for article in response.data['results']:
            self.assertTrue(article['is_featured'])

    def test_mark_helpful(self):
        url = self.get_url('help-article-mark-helpful', kwargs={'slug': 'cara-melacak-pesanan'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['helpful_count'], 1)
        self.article1.refresh_from_db()
        self.assertEqual(self.article1.helpful_count, 1)

    def test_mark_not_helpful(self):
        url = self.get_url('help-article-mark-not-helpful', kwargs={'slug': 'cara-melacak-pesanan'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['not_helpful_count'], 1)

    def test_mark_helpful_twice_increments(self):
        url = self.get_url('help-article-mark-helpful', kwargs={'slug': 'cara-melacak-pesanan'})
        self.client.post(url)
        self.client.post(url)
        self.article1.refresh_from_db()
        self.assertEqual(self.article1.helpful_count, 2)

    def test_mark_helpful_unpublished_returns_404(self):
        url = self.get_url('help-article-mark-helpful', kwargs={'slug': 'draft-article'})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class FAQAPITests(SupportAPITestBase):
    """Tests for FAQ API endpoint."""

    def test_list_returns_only_published(self):
        response = self.client.get(self.get_url('faq-list'))
        questions = [f['question'] for f in response.data['results']]
        self.assertIn('Apakah Warungio melayani seluruh Indonesia?', questions)
        self.assertNotIn('Unpublished FAQ?', questions)

    def test_filter_by_category(self):
        response = self.client.get(self.get_url('faq-list'), {'category': 'pesanan'})
        for faq in response.data['results']:
            self.assertEqual(faq['category_name'], 'Pesanan')

    def test_filter_by_search_question(self):
        response = self.client.get(self.get_url('faq-list'), {'search': 'reset password'})
        questions = [f['question'] for f in response.data['results']]
        self.assertIn('Bagaimana cara reset password?', questions)

    def test_search_by_answer(self):
        response = self.client.get(self.get_url('faq-list'), {'search': 'kota-kota besar'})
        self.assertEqual(len(response.data['results']), 1)


class BannerPromoAPITests(SupportAPITestBase):
    """Tests for BannerPromo API endpoint."""

    def test_list_only_active_and_not_expired(self):
        response = self.client.get(self.get_url('banner-list'))
        titles = [b['title'] for b in response.data['results']]
        self.assertIn('Belanja Hemat', titles)
        self.assertIn('Always Active', titles)
        self.assertNotIn('Expired Banner', titles)
        self.assertNotIn('Inactive Banner', titles)

    def test_filter_by_position(self):
        response = self.client.get(self.get_url('banner-list'), {'position': 'help_bottom'})
        for banner in response.data['results']:
            self.assertEqual(banner['position'], 'help_bottom')


class ContactInfoAPITests(SupportAPITestBase):
    """Tests for ContactInfo API endpoint."""

    def test_list_only_active(self):
        response = self.client.get(self.get_url('contact-list'))
        labels = [c['label'] for c in response.data['results']]
        self.assertIn('Chat WhatsApp', labels)
        self.assertNotIn('Telepon Inactive', labels)

    def test_serializer_has_type_display(self):
        response = self.client.get(self.get_url('contact-list'))
        self.assertIn('type_display', response.data['results'][0])


class SupportInfoAPITests(SupportAPITestBase):
    """Tests for SupportInfo API endpoint."""

    def test_list_only_active(self):
        response = self.client.get(self.get_url('support-info-list'))
        titles = [s['title'] for s in response.data['results']]
        self.assertIn('Respon Cepat', titles)
        self.assertNotIn('Old Info', titles)

    def test_ordering(self):
        response = self.client.get(self.get_url('support-info-list'))
        results = response.data['results']
        self.assertEqual(results[0]['key'], 'fast_response')
        self.assertEqual(results[1]['key'], '24_7')


class ChatQuickReplyAPITests(SupportAPITestBase):
    """Tests for ChatQuickReply API endpoint."""

    def test_list_only_active(self):
        response = self.client.get(self.get_url('quick-reply-list'))
        labels = [q['label'] for q in response.data['results']]
        self.assertIn('Status Pesanan', labels)
        self.assertNotIn('Lainnya Inactive', labels)

    def test_filter_by_category(self):
        response = self.client.get(self.get_url('quick-reply-list'), {'category': 'order'})
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['label'], 'Status Pesanan')

    def test_filter_by_payment_category(self):
        response = self.client.get(self.get_url('quick-reply-list'), {'category': 'payment'})
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['label'], 'Pembayaran')


class HelpSearchAPITests(SupportAPITestBase):
    """Tests for combined help search endpoint."""

    def _pre_setup(self):
        super()._pre_setup()
        from django.core.cache import cache
        cache.clear()

    def test_search_articles_by_query(self):
        response = self.client.get(self.get_url('help-search'), {'q': 'Melacak'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        articles = response.data['articles']
        self.assertTrue(len(articles) > 0)
        self.assertEqual(articles[0]['slug'], 'cara-melacak-pesanan')

    def test_search_faqs_by_query(self):
        response = self.client.get(self.get_url('help-search'), {'q': 'reset password'})
        faqs = response.data['faqs']
        self.assertTrue(len(faqs) > 0)

    def test_search_returns_both_articles_and_faqs(self):
        response = self.client.get(self.get_url('help-search'), {'q': 'Warungio'})
        self.assertIn('articles', response.data)
        self.assertIn('faqs', response.data)

    def test_no_query_returns_empty(self):
        response = self.client.get(self.get_url('help-search'))
        self.assertEqual(len(response.data['articles']), 0)
        self.assertEqual(len(response.data['faqs']), 0)


