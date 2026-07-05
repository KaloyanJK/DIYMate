from django.urls import path
from . import views

urlpatterns = [
    path('generate/<int:project_id>/', views.generate_plan, name='generate_plan'),
]