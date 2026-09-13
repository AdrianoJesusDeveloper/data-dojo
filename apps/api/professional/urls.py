from rest_framework.routers import DefaultRouter

from .views import OpportunityViewSet, ProfessionalModalityViewSet

router = DefaultRouter()
router.register("opportunities", OpportunityViewSet, basename="opportunity")
router.register("modalities", ProfessionalModalityViewSet, basename="professional-modality")

urlpatterns = router.urls
