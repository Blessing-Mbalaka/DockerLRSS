"""Explicit ETQA approval of learner results and workflow report access."""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import Assessment, ExamSubmission


def etqa_allowed(user):
    return user.is_superuser or user.role in {'admin', 'etqa'}


@login_required
def results_release(request):
    if not etqa_allowed(request.user):
        return HttpResponseForbidden('ETQA access required.')
    if request.method == 'POST':
        if not request.POST.get('submission_id', '').isdigit():
            messages.error(request, 'Select a submission.'); return redirect('etqa_results_release')
        with transaction.atomic():
            submission = get_object_or_404(ExamSubmission.objects.select_for_update(), pk=request.POST.get('submission_id'))
            if request.POST.get('action') == 'hold':
                submission.results_release_at = None
                submission.results_released_by = None
                submission.save(update_fields=['results_release_at', 'results_released_by'])
                messages.success(request, 'Results returned to hold.')
            elif any(value is None for value in (submission.marks, submission.internal_marks, submission.external_marks)):
                messages.error(request, 'Marking, internal moderation and external moderation must be completed first.')
            elif request.POST.get('offline_confirmed') != 'yes':
                messages.error(request, 'Confirm that the offline approvals and QCTO engagements are complete.')
            else:
                release_at = timezone.now()
                submission.results_release_at = release_at
                submission.results_released_by = request.user
                submission.save(update_fields=['results_release_at', 'results_released_by'])
                messages.success(request, 'Results release saved.')
        return redirect('etqa_results_release')
    submissions = ExamSubmission.objects.select_related('student', 'assessment', 'paper', 'results_released_by').order_by('-submitted_at')
    return render(request, 'core/etqa/results_release.html', {'submissions': submissions, 'release_timezone': timezone.get_current_timezone_name()})


REPORT_FIELDS = {'assessor': ('Assessor Developer', 'assessor_report'),
                 'moderator': ('Moderator Developer', 'moderator_report'),
                 'qdd': ('QDD Reviewer', 'qdd_report'), 'qcto': ('QCTO Validator', 'qcto_report')}


@login_required
def reports(request):
    if not etqa_allowed(request.user):
        return HttpResponseForbidden('ETQA access required.')
    rows = []
    for assessment in Assessment.objects.select_related('qualification').order_by('-created_at'):
        for kind, (label, field) in REPORT_FIELDS.items():
            file = getattr(assessment, field)
            if file:
                rows.append({'assessment': assessment, 'kind': kind, 'label': label, 'filename': file.name.rsplit('/', 1)[-1]})
    return render(request, 'core/etqa/reports.html', {'reports': rows})


@login_required
def report_download(request, assessment_id, kind):
    if kind not in REPORT_FIELDS:
        raise Http404
    assessment = get_object_or_404(Assessment, pk=assessment_id)
    user = request.user
    allowed = etqa_allowed(user) or user.role in {'moderator', 'qcto', 'qdd'} or assessment.created_by_id == user.id
    if not allowed:
        return HttpResponseForbidden('Report access denied.')
    file = getattr(assessment, REPORT_FIELDS[kind][1])
    if not file:
        raise Http404
    try:
        return FileResponse(file.open('rb'), as_attachment=True, filename=file.name.rsplit('/', 1)[-1])
    except FileNotFoundError:
        raise Http404('Report file unavailable.')


@login_required
def written(request):
    if not etqa_allowed(request.user):
        return HttpResponseForbidden('ETQA access required.')
    from django.core.paginator import Paginator
    submissions = ExamSubmission.objects.select_related('student', 'offline_student', 'assessment', 'paper').order_by('-submitted_at', '-pk')
    page = Paginator(submissions, 50).get_page(request.GET.get('page'))
    return render(request, 'core/etqa/written.html', {'page_obj': page})


@login_required
def written_download(request, submission_id, kind):
    if not etqa_allowed(request.user):
        return HttpResponseForbidden('ETQA access required.')
    fields = {'original': 'pdf_file', 'marker': 'marked_paper',
              'internal': 'internal_marked_paper', 'external': 'external_marked_paper'}
    if kind not in fields:
        raise Http404
    submission = get_object_or_404(ExamSubmission, pk=submission_id)
    file = getattr(submission, fields[kind])
    if not file:
        raise Http404('No paper uploaded for this stage.')
    try:
        response = FileResponse(file.open('rb'), as_attachment=True, filename=file.name.rsplit('/', 1)[-1])
    except FileNotFoundError:
        raise Http404('Paper file unavailable.')
    response['Cache-Control'] = 'private, no-store'
    return response
