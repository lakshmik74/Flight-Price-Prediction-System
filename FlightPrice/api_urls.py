from django.urls import include, path
from rest_framework.routers import DefaultRouter
from .api_views import (
    ModelPerformanceView,
    ModelListView,
    PredictionView,
    RetrainingHistoryView,
    APIHealthView,
    RetrainAPIView,
)

router = DefaultRouter()
router.register(r'models', ModelListView, basename='models')
router.register(r'history', RetrainingHistoryView, basename='history')

urlpatterns = [
    path('', include(router.urls)),
    path('predict/', PredictionView.as_view(), name='api-predict'),
    path('model-performance/', ModelPerformanceView.as_view(), name='api-model-performance'),
    path('retrain/', RetrainAPIView.as_view(), name='api-retrain'),
    path('health/', APIHealthView.as_view(), name='api-health'),
]
