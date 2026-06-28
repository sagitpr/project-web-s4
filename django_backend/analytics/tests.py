"""Tests for the analytics app."""

import pytest
from rest_framework import status
from django.urls import reverse
from django.utils import timezone

from .models import SalesAnalytics, DailyReport, UserActivity, DeviceAnalytics


class TestSalesAnalyticsModel:
    """Test SalesAnalytics model."""

    def test_create_analytics(self, db, test_store):
        analytics = SalesAnalytics.objects.create(
            store=test_store,
            date=timezone.now().date(),
            total_sales=1500000.00,
            total_orders=25,
            total_products_sold=60,
        )
        assert analytics.store == test_store
        assert analytics.date == timezone.now().date()
        assert analytics.total_sales == 1500000.00
        assert analytics.total_orders == 25
        assert analytics.total_products_sold == 60

    def test_analytics_str(self, db, test_store):
        today = timezone.now().date()
        analytics = SalesAnalytics.objects.create(
            store=test_store, date=today,
            total_sales=0, total_orders=0, total_products_sold=0,
        )
        assert str(analytics) == f"Sales {test_store.store_name} - {today}"


class TestDailyReportModel:
    """Test DailyReport model."""

    def test_create_report(self, db, test_store):
        report = DailyReport.objects.create(
            store=test_store,
            date=timezone.now().date(),
            total_revenue=500000,
            total_orders=10,
            total_products_sold=25,
            new_customers_count=3,
            total_visitors=50,
        )
        assert report.store == test_store
        assert report.total_orders == 10
        assert report.total_revenue == 500000
        assert report.new_customers_count == 3

    def test_report_str(self, db, test_store):
        today = timezone.now().date()
        report = DailyReport.objects.create(
            store=test_store, date=today,
            total_revenue=0, total_orders=0, total_products_sold=0,
        )
        assert str(report) == f"Report {test_store.store_name} - {today}"


class TestUserActivityModel:
    """Test UserActivity model."""

    def test_create_activity(self, db, verified_user):
        activity = UserActivity.objects.create(
            user=verified_user,
            activity_type="page_view",
            metadata={"page": "/home"},
        )
        assert activity.user == verified_user
        assert activity.activity_type == "page_view"
        assert activity.metadata == {"page": "/home"}
        assert activity.created_at is not None

    def test_activity_str(self, db, verified_user):
        activity = UserActivity.objects.create(
            user=verified_user, activity_type="search",
        )
        assert str(activity) == f"search - {activity.created_at}"


class TestDeviceAnalyticsModel:
    def test_create_device_analytics(self, db, test_store):
        da = DeviceAnalytics.objects.create(
            store=test_store, date=timezone.now().date(),
            device_type="mobile", visitors_count=100, page_views=300,
        )
        assert da.device_type == "mobile"
        assert da.visitors_count == 100


# ─── API Tests ──────────────────────────────────────────────────────────────

class TestDashboardAPI:
    DASHBOARD_URL = reverse("dashboard-summary")

    def test_dashboard_requires_auth(self, api_client):
        resp = api_client.get(self.DASHBOARD_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_dashboard_returns_data(self, seller_client, test_store):
        resp = seller_client.get(self.DASHBOARD_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert isinstance(resp.json(), dict)

    def test_dashboard_with_analytics(self, seller_client, test_store):
        SalesAnalytics.objects.create(
            store=test_store, date=timezone.now().date(),
            total_sales=2000000, total_orders=30, total_products_sold=75,
        )
        resp = seller_client.get(self.DASHBOARD_URL)
        assert resp.status_code == status.HTTP_200_OK

    def test_dashboard_buyer_forbidden(self, buyer_client):
        resp = buyer_client.get(self.DASHBOARD_URL)
        assert resp.status_code in (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND)


class TestSalesAnalyticsAPI:
    LIST_URL = reverse("sales-analytics")

    def test_list_requires_auth(self, api_client):
        resp = api_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_list_returns_data(self, seller_client, test_store):
        resp = seller_client.get(self.LIST_URL)
        assert resp.status_code == status.HTTP_200_OK
        assert "results" in resp.json()
