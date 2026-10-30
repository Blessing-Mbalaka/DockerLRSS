"""Enforce release controls on legacy media links served by Django."""
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.views.static import serve
from .models import Assessment, ExamSubmission, ExtractorPaper


def protected_media(request, path, document_root=None):
    user = request.user
    staff = user.is_authenticated and (user.is_superuser or user.role in {
        'admin', 'etqa', 'qcto', 'qdd', 'assessor_dev', 'moderator', 'assessor_marker', 'internal_mod', 'external_mod'})
    submission = ExamSubmission.objects.filter(Q(pdf_file=path) | Q(marked_paper=path) |
        Q(internal_marked_paper=path) | Q(external_marked_paper=path)).first()
    if submission and not staff:
        owner = user.is_authenticated and submission.student_id == user.pk
        original = submission.pdf_file.name == path
        # Centre staff must be able to reopen the original offline PDFs shown
        # in their upload register. ETQA source papers retain their release gate.
        centre_original = (user.is_authenticated and user.role == 'assessment_center'
                           and submission.is_offline and original)
        if not centre_original and (not owner or (not original and not submission.results_are_released)):
            return HttpResponseForbidden('This assessment document has not been released to you.')
    assessment = Assessment.objects.filter(Q(file=path) | Q(memo=path) | Q(memo_file=path) |
        Q(assessor_report=path) | Q(moderator_report=path) | Q(qdd_report=path) | Q(qcto_report=path)).exists()
    source = ExtractorPaper.objects.filter(original_file=path).exists()
    if (assessment or source) and not staff:
        return HttpResponseForbidden('Use your authorised released-paper download.')
    return serve(request, path, document_root=document_root)
