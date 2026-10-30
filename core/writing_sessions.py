import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import Assessment, AssessmentWritingSession, AssessmentWritingIncident, ExamSubmission


@login_required
@require_http_methods(['GET', 'POST'])
def writing_session(request, assessment_id):
    assessment = get_object_or_404(Assessment, pk=assessment_id)
    if request.user.role != 'learner' or not request.user.qualification_id or request.user.qualification_id != assessment.qualification_id:
        return HttpResponseForbidden()
    if assessment.status not in ['Released to students', 'active']:
        return HttpResponseForbidden()
    with transaction.atomic():
        session, _ = AssessmentWritingSession.objects.get_or_create(student=request.user, assessment=assessment)
        session = AssessmentWritingSession.objects.select_for_update().get(pk=session.pk)
        if ExamSubmission.objects.filter(student=request.user, assessment=assessment).exists():
            return JsonResponse({'error': 'Already submitted'}, status=409)
        if request.method == 'POST':
            if len(request.body) > 2000000:
                return JsonResponse({'error': 'Draft too large'}, status=400)
            try:
                data = json.loads(request.body)
                if not isinstance(data, dict):
                    raise ValueError()
                kind = data.get('incident')
                if kind:
                    if kind not in ['tab_hidden', 'navigation', 'offline', 'reconnected']:
                        raise ValueError()
                    # Bound repeated browser signals without trusting client timestamps.
                    recent = timezone.now() - timezone.timedelta(seconds=5)
                    if not session.incidents.filter(kind=kind, created_at__gte=recent).exists():
                        AssessmentWritingIncident.objects.create(session=session, kind=kind)
                else:
                    answers = data.get('answers')
                    if not isinstance(answers, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in answers.items()):
                        raise ValueError()
                    if data.get('revision') != session.revision:
                        return JsonResponse({'error': 'Another tab updated this attempt. Reload before continuing.'}, status=409)
                    session.answers = {k: v for k, v in answers.items() if k != 'csrfmiddlewaretoken'}
                    session.revision += 1
                    session.save()
            except (ValueError, TypeError):
                return JsonResponse({'error': 'Invalid request'}, status=400)
        return JsonResponse({'answers': session.answers, 'revision': session.revision, 'started_at': session.started_at.isoformat()})


@login_required
@require_http_methods(['GET', 'POST'])
def writing_monitor(request):
    if request.user.role != 'assessment_center' or not request.user.assessment_centre_id:
        return HttpResponseForbidden()
    incidents = AssessmentWritingIncident.objects.filter(session__student__assessment_centre_id=request.user.assessment_centre_id)
    if request.method == 'POST':
        incident = get_object_or_404(incidents, pk=request.POST.get('incident_id'))
        if incident.reviewed_at is None:
            incident.reviewed_by = request.user
            incident.reviewed_at = timezone.now()
            incident.save(update_fields=['reviewed_by', 'reviewed_at'])
        return redirect('writing_monitor')
    sessions = AssessmentWritingSession.objects.filter(student__assessment_centre_id=request.user.assessment_centre_id).select_related('student', 'assessment').order_by('-last_saved_at')[:100]
    return render(request, 'core/assessment-center/writing_monitor.html', {'incidents': incidents.select_related('session__student', 'session__assessment', 'reviewed_by').order_by('-created_at')[:200], 'sessions': sessions})
