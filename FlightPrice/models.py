from django.db import models

# Create your models here.

class Signup(models.Model):
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    contact_no = models.CharField(max_length=12)
    email_id = models.CharField(max_length=50)
    address = models.CharField(max_length=50)
    
    class Meta:
        db_table = 'signup'
    
    def __str__(self):
        return self.username


class PredictionHistory(models.Model):
    username = models.CharField(max_length=50, blank=True, null=True)
    airline = models.CharField(max_length=100)
    source = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    travel_date = models.DateField()
    predicted_price = models.FloatField()
    historical_average = models.FloatField(blank=True, null=True)
    live_price = models.FloatField(blank=True, null=True)
    selected_model = models.CharField(max_length=100)
    difference = models.FloatField(blank=True, null=True)
    percentage_error = models.FloatField(blank=True, null=True)
    status = models.CharField(max_length=64, blank=True)
    currency = models.CharField(max_length=16, default='INR')
    booking_link = models.URLField(blank=True)
    flight_number = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'prediction_history'

    def __str__(self):
        return f"{self.airline} {self.source}->{self.destination} {self.travel_date}"


class RetrainingHistory(models.Model):
    model_name = models.CharField(max_length=100)
    model_version = models.CharField(max_length=100)
    dataset_version = models.CharField(max_length=100, blank=True)
    training_date = models.DateTimeField(auto_now_add=True)
    rmse = models.FloatField()
    mae = models.FloatField()
    training_time_seconds = models.FloatField(blank=True, null=True)
    model_path = models.CharField(max_length=255)
    is_production = models.BooleanField(default=False)

    class Meta:
        ordering = ['-training_date']
        db_table = 'retraining_history'

    def __str__(self):
        return f"{self.model_name} ({self.model_version})"