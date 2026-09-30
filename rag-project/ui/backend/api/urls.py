from django.urls import path
from .views import chat, pdf, system_stats

urlpatterns = [
    path('chat/', chat, name='chat'),
    path('pdf/<str:doc_name>/', pdf, name='pdf'),
    path('stats/', system_stats, name='system-stats'),
]