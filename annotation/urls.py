from django.urls import path
from .views import (
    AnnotationProjectListView,
    AnnotationProjectCreateView,
    AnnotationTaskListView,
    AnnotationTaskDetailView, AnnotationView
)

urlpatterns = [
    # Project URLs
    path('projects/', AnnotationProjectListView.as_view(), name='project_list'),
    path('projects/create/', AnnotationProjectCreateView.as_view(), name='project_create'),

    # Task URLs
    path('projects/<uuid:project_id>/tasks/', AnnotationTaskListView.as_view(), name='task_list'),
    path('tasks/<uuid:pk>/', AnnotationTaskDetailView.as_view(), name='task_detail'),
    path('tasks/<uuid:task_id>/annotate/', AnnotationView.as_view(), name='task-annotate'),
]
