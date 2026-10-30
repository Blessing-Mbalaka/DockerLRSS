from django.http import HttpRequest

from .automated_notifications import build_user_notifications


def notifications_context(request: HttpRequest) -> dict:
    """
    Inject workflow notifications + filter metadata into every template.
    Falls back to empty payload for anonymous sessions.
    """
    if getattr(request, 'user', None) and request.user.is_authenticated:
        notifications, filters = build_user_notifications(request.user)
    else:
        notifications, filters = [], {'qualifications': [], 'statuses': []}

    writing_incident_count = 0
    user = getattr(request, 'user', None)
    if user and user.is_authenticated and user.role == 'assessment_center' and user.assessment_centre_id:
        from .models import AssessmentWritingIncident
        writing_incident_count = AssessmentWritingIncident.objects.filter(
            session__student__assessment_centre_id=user.assessment_centre_id,
            reviewed_at__isnull=True,
        ).count()

    return {
        'writing_incident_count': writing_incident_count,
        'dashboard_notifications': notifications,
        'dashboard_notification_filters': filters,
    }
