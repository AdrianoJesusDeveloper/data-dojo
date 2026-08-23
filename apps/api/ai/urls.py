from django.urls import path

from .views import AIAgentsView, AIChatView

urlpatterns = [
    path("agents/", AIAgentsView.as_view(), name="ai-agents"),
    path("chat/", AIChatView.as_view(), name="ai-chat"),
]
