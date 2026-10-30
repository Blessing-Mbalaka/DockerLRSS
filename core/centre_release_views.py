from copy import copy
from io import BytesIO
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import transaction
from django.http import FileResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from .models import Batch, CustomUser
from .release_views import etqa_allowed
from .word_pdf import convert_word_to_pdf, ConversionUnavailable


def word_for_assessment(request, assessment):
    if assessment.paper_type == 'randomized' and assessment.paper_link_id:
        from .views import download_randomized_pdf
        export_request = copy(request)
        export_request.GET = request.GET.copy()
        export_request.GET['format'] = 'docx'
        export_request.GET['variant'] = 'paper'
        response = download_randomized_pdf(export_request, assessment.pk)
        if response.status_code != 200:
            raise ConversionUnavailable('The Word export is unavailable.')
        return response.content
    if assessment.file and assessment.file.name.lower().endswith('.docx'):
        with assessment.file.open('rb') as source:
            return source.read()
    raise ConversionUnavailable('A Word assessment file is required for this release.')


@login_required
def centre_release(request):
    if not etqa_allowed(request.user):
        return HttpResponseForbidden('ETQA access required.')
    if request.method == 'POST':
        if not request.POST.get('batch_id', '').isdigit():
            messages.error(request, 'Select an assessment batch.'); return redirect('etqa_centre_release')
        batch = get_object_or_404(Batch.objects.select_related('assessment', 'center'), pk=request.POST.get('batch_id'), submitted_to_center=True)
        release_at = timezone.now()
        recipients = list(CustomUser.objects.filter(role='assessment_center', assessment_centre=batch.center,
                            is_active=True).exclude(email='').values_list('email', flat=True))
        if not recipients:
            messages.error(request, 'Assign an active assessment centre user with an email address before release.')
            return redirect('etqa_centre_release')
        if request.POST.get('offline_confirmed') != 'yes':
            messages.error(request, 'Confirm offline approvals before releasing the paper.')
            return redirect('etqa_centre_release')
        try:
            pdf = convert_word_to_pdf(word_for_assessment(request, batch.assessment))
            with transaction.atomic():
                locked = Batch.objects.select_for_update().get(pk=batch.pk)
                if locked.paper_release_at:
                    messages.info(request, 'This batch already has a released paper.')
                    return redirect('etqa_centre_release')
                url = settings.SITE_URL.rstrip('/') + '/assessment-centre/released-papers/'
                delivered = send_mail('Released EISA paper: '+batch.assessment.eisa_id,
                    f'Centre: {batch.center.name}\nAssessment: {batch.assessment.eisa_id}\n'
                    f'Available from: {timezone.localtime(release_at):%Y-%m-%d %H:%M %Z}\n'
                    f'Download: {url}\nThe PDF opens without a password.',
                    settings.DEFAULT_FROM_EMAIL, recipients, fail_silently=False)
                if not delivered:
                    raise RuntimeError('Email delivery was not accepted.')
                locked.locked_paper_pdf = pdf
                locked.paper_release_at = release_at
                locked.paper_released_by = request.user
                locked.save(update_fields=['locked_paper_pdf', 'paper_release_at', 'paper_released_by'])
            messages.success(request, 'Paper released as a PDF without password protection. The centre has been notified.')
        except ConversionUnavailable as exc:
            messages.error(request, str(exc))
        except Exception:
            messages.error(request, 'Release failed. Check PDF conversion and SMTP configuration, then retry. The paper has not been released.')
        return redirect('etqa_centre_release')
    batches = Batch.objects.filter(submitted_to_center=True).select_related('assessment', 'center').defer('locked_paper_pdf').order_by('-created_at')
    return render(request, 'core/etqa/centre_release.html', {'batches': batches, 'release_timezone': timezone.get_current_timezone_name()})


@login_required
def released_papers(request):
    if request.user.role != 'assessment_center' or not request.user.assessment_centre_id:
        return HttpResponseForbidden('An assigned assessment centre account is required.')
    batches = Batch.objects.filter(center_id=request.user.assessment_centre_id, submitted_to_center=True,
        paper_release_at__lte=timezone.now()).select_related('assessment').defer('locked_paper_pdf').order_by('-paper_release_at')
    return render(request, 'core/etqa/released_papers.html', {'batches': batches})


@login_required
def protected_paper(request, batch_id):
    if request.user.role != 'assessment_center' or not request.user.assessment_centre_id:
        return HttpResponseForbidden('Assessment centre access required.')
    batch = get_object_or_404(Batch, pk=batch_id, center_id=request.user.assessment_centre_id,
        submitted_to_center=True, paper_release_at__lte=timezone.now())
    if not batch.locked_paper_pdf:
        return HttpResponseForbidden('Paper not released.')
    response = FileResponse(BytesIO(bytes(batch.locked_paper_pdf)), as_attachment=True,
        filename=f'{batch.assessment.eisa_id}-released.pdf', content_type='application/pdf')
    response['Cache-Control'] = 'private, no-store'
    return response
