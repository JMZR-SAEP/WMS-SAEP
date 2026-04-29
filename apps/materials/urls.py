from rest_framework.routers import SimpleRouter

from apps.materials.views import MaterialViewSet

router = SimpleRouter()
router.register("materials", MaterialViewSet, basename="material")

urlpatterns = router.urls
