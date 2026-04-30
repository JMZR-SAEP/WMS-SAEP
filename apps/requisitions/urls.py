from rest_framework.routers import SimpleRouter

from apps.requisitions.views import RequisicaoViewSet

router = SimpleRouter()
router.register("requisitions", RequisicaoViewSet, basename="requisicao")

urlpatterns = router.urls
