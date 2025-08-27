from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name='homepage'),                      # Homepage shown at /
    path("chatbot/", views.chatbot_ui, name="chatbot_ui"),      # Chatbot available at /chatbot/
    path("api/chat/", views.chatbot_response),
    path("api/feedback/", views.record_feedback),
    path("Checklist", views.checklist, name='Checklist'),
    path("moodtracker", views.moodtracker, name="moodtracker"),
    path("motivation", views.motivation, name="motivation"),
    path("Journal", views.Journal, name="Journal"),
    path("Resources", views.Resources, name="Resources"),
]
