from rest_framework import serializers


class PredictionSerializer(serializers.Serializer):
    airline = serializers.CharField(required=False, allow_blank=True, default='')
    source = serializers.CharField(required=False, allow_blank=True, default='')
    destination = serializers.CharField(required=False, allow_blank=True, default='')
    day = serializers.IntegerField()
    month = serializers.IntegerField()
    year = serializers.IntegerField()


class RetrainingHistorySerializer(serializers.Serializer):
    model_name = serializers.CharField()
    model_version = serializers.CharField()
    dataset_version = serializers.CharField()
    training_date = serializers.DateTimeField()
    rmse = serializers.FloatField()
    mae = serializers.FloatField()
    training_time_seconds = serializers.FloatField()
    model_path = serializers.CharField()
    is_production = serializers.BooleanField()


class ModelInfoSerializer(serializers.Serializer):
    name = serializers.CharField()
    size_kb = serializers.FloatField()
    modified_at = serializers.FloatField()


class ModelPerformanceSerializer(serializers.Serializer):
    rows = serializers.IntegerField()
    features = serializers.ListField(child=serializers.CharField())
    models_evaluated = serializers.ListField(child=serializers.DictField())
    best_model = serializers.DictField()
    notes = serializers.CharField()
