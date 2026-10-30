from django.urls import path
from .writing_sessions import writing_session, writing_monitor
urlpatterns = [path('session/<int:assessment_id>/', writing_session, name='writing_session'), path('monitor/', writing_monitor, name='writing_monitor')]
