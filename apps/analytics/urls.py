from rest_framework.routers import SimpleRouter

from apps.analytics.views import FrontendAnalyticsViewSet

router = SimpleRouter()
router.register("analytics/events", FrontendAnalyticsViewSet, basename="analytics-event")

urlpatterns = router.urls
