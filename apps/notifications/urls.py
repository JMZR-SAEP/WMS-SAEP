from rest_framework.routers import SimpleRouter

from apps.notifications.views import NotificacaoViewSet

router = SimpleRouter()
router.register("notifications", NotificacaoViewSet, basename="notification")

urlpatterns = router.urls
