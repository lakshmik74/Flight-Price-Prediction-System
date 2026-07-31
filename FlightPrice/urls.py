from django.urls import include, path
from django.shortcuts import redirect

from . import views

def redirect_to_index(request):
    return redirect('index')

urlpatterns = [
    path("", redirect_to_index, name="root"),
    path("index.html", views.index, name="index"),
    path('UserLogin', views.UserLogin, name="UserLogin"),
    path('UserLoginAction', views.UserLoginAction, name="UserLoginAction"),	   
    path('Signup', views.Signup, name="Signup"),
    path('SignupAction', views.SignupAction, name="SignupAction"),
    path('DatasetCollection', views.DatasetCollection, name="DatasetCollection"),
    path('DatasetCleaning', views.DatasetCleaning, name="DatasetCleaning"),	      
    path('TrainRF', views.TrainRF, name='TrainRF'),
    path('TrainML', views.TrainML, name='TrainML'),
    path('ModelReport', views.ModelReport, name='ModelReport'),
    path('Dashboard', views.Dashboard, name='Dashboard'),
    path('AdminPanel', views.AdminPanel, name='AdminPanel'),
    path('AdminPromote/<str:artifact_name>', views.AdminPromoteArtifact, name='AdminPromoteArtifact'),
    path('AdminRollback/<str:artifact_name>', views.AdminRollbackArtifact, name='AdminRollbackArtifact'),
    path('ModelMonitoring', views.ModelMonitoring, name='ModelMonitoring'),
    path('AdminDownload/<str:artifact_name>', views.AdminDownloadArtifact, name='AdminDownloadArtifact'),
    path('AdminRetrain', views.AdminRetrain, name='AdminRetrain'),
    path('AdminUploadDataset', views.AdminUploadDataset, name='AdminUploadDataset'),
    path('AdminClearArtifacts', views.AdminClearArtifacts, name='AdminClearArtifacts'),
    path('AdminCleanRetraining', views.AdminCleanRetraining, name='AdminCleanRetraining'),
    path('AdminResetPredictionHistory', views.AdminResetPredictionHistory, name='AdminResetPredictionHistory'),
    path('Logout', views.Logout, name='Logout'),
    path('ForgotPassword', views.ForgotPassword, name='ForgotPassword'),
    path('PredictPrices', views.PredictPrices, name="PredictPrices"),
    path('PredictPricesAction', views.PredictPricesAction, name="PredictPricesAction"),
    path('api/', include('FlightPrice.api_urls')),
]
