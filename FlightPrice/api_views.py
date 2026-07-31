from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import PredictionHistory, RetrainingHistory
from .ml.model import predict_price, load_model, train_pipeline
from .serializers import (
    PredictionSerializer,
    RetrainingHistorySerializer,
    ModelInfoSerializer,
    ModelPerformanceSerializer,
)
from django.contrib.auth import authenticate
from django.conf import settings
from pathlib import Path
from .views import _load_model_report
import joblib
import os

class AuthenticatedAdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.session.get('username') is not None


class PredictionView(APIView):
    """POST /api/predict

    Request body:
    {
      "airline": "Air India",
      "source": "Delhi",
      "destination": "Mumbai",
      "day": 10,
      "month": 10,
      "year": 2025
    }

    Response:
    {
      "success": true,
      "data": {
        "prediction": 1234.56,
        "general_price": 1200.00,
        "selected_model": "random_forest",
        "model_version": "v3_random_forest"
      }
    }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PredictionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        prediction = predict_price(
            serializer.validated_data['airline'],
            serializer.validated_data['source'],
            serializer.validated_data['destination'],
            serializer.validated_data['day'],
            serializer.validated_data['month'],
            serializer.validated_data['year'],
        )
        return Response({
            'success': True,
            'data': prediction,
        }, status=status.HTTP_200_OK)


class ModelListView(viewsets.ViewSet):
    """GET /api/models

    Response:
    {
      "success": true,
      "models": [
        {"name": "v1_random_forest.joblib", "size_kb": 213.45, "modified_at": 1700000000.0}
      ]
    }
    """
    permission_classes = [permissions.AllowAny]

    def list(self, request):
        models_dir = Path(__file__).resolve().parents[2] / 'models'
        model_files = [
            {
                'name': path.name,
                'size_kb': round(path.stat().st_size / 1024, 2),
                'modified_at': path.stat().st_mtime,
            }
            for path in sorted(models_dir.glob('*.joblib'))
        ]
        serializer = ModelInfoSerializer(model_files, many=True)
        return Response({'success': True, 'models': serializer.data})


class RetrainingHistoryView(viewsets.ReadOnlyModelViewSet):
    """GET /api/history

    Returns retraining audit records.
    """
    permission_classes = [permissions.AllowAny]
    queryset = RetrainingHistory.objects.all().order_by('-training_date')
    serializer_class = RetrainingHistorySerializer

    def list(self, request):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({'success': True, 'results': serializer.data})


class ModelPerformanceView(APIView):
    """GET /api/model-performance

    Returns model comparison and best candidate metrics.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        report = _load_model_report()
        if report is None:
            return Response({'success': False, 'message': 'No model report available.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = ModelPerformanceSerializer(report)
        return Response({'success': True, 'performance': serializer.data})


class RetrainAPIView(APIView):
    """POST /api/retrain

    Admin-only retraining endpoint. Requires a valid authenticated session.
    """
    permission_classes = [AuthenticatedAdminPermission]

    def post(self, request):
        try:
            summary = train_pipeline()
            return Response({
                'success': True,
                'message': 'Retraining completed.',
                'data': summary,
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class APIHealthView(APIView):
    """GET /api/health

    Returns basic REST API health and artifact availability.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        status_payload = {
            'success': True,
            'status': 'healthy',
            'models_available': len(list((Path(__file__).resolve().parents[2] / 'models').glob('*.joblib'))),
            'report_available': (Path(__file__).resolve().parents[2] / 'reports' / 'model_comparison.json').exists(),
        }
        return Response(status_payload)
