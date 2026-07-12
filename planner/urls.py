from django.urls import path
from . import views

urlpatterns = [
    path('generate/<int:project_id>/', views.generate_plan, name='generate_plan'),
    path('generate/<int:project_id>/inspirations/', views.generate_plan_inspirations, name='generate_plan_inspirations'),
    path('generate/<int:project_id>/drawing/regenerate/', views.regenerate_plan_drawing, name='regenerate_plan_drawing'),
    path('generate/<int:project_id>/drawing/save/', views.save_plan_drawing, name='save_plan_drawing'),
]