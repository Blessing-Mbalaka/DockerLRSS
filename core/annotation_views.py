"""
annotation_views.py
───────────────────
Role-isolated annotation management and editable grade views.

Annotation rules
────────────────
• Only roles  assessor_marker | internal_mod | external_mod  may annotate.
• Each annotation is owned by one user; only that user may delete it.
• No "delete all" operation exists – every deletion is per-annotation.

Grade-edit rules
────────────────
• Assessor Marker  → may edit  marks / total_marks / feedback
• Internal Moderator → may edit  internal_*  fields
• External Moderator → may edit  external_*  fields
• Every change is logged in GradeChangeLog (who, when, old value, new value).
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST, require_http_methods

from .models import ExamSubmission, GradeChangeLog, PdfAnnotation

# ─── helpers ────────────────────────────────────────────────────────────────

ANNOTATION_ROLES = {"assessor_marker", "internal_mod", "external_mod"}


def _require_annotation_role(request):
    """Return None if OK, or a 403 JsonResponse."""
    if request.user.role not in ANNOTATION_ROLES:
        return JsonResponse({"success": False, "message": "Permission denied – annotation roles only."}, status=403)
    return None


# ════════════════════════════════════════════════════════════════════════════
#  ANNOTATION ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════


@login_required
@require_GET
def list_annotations(request, submission_id):
    """
    GET /annotations/<submission_id>/
    Returns all annotations for a submission, each tagged with whether
    the current user is the owner.
    """
    err = _require_annotation_role(request)
    if err:
        return err

    submission = get_object_or_404(ExamSubmission, id=submission_id)
    annotations = PdfAnnotation.objects.filter(submission=submission).select_related("created_by")

    data = [
        {
            "id":        ann.id,
            "type":      ann.ann_type,
            "page":      ann.page,
            "x":         ann.x,
            "y":         ann.y,
            "text":      ann.text,
            "colour":    ann.colour,
            "role":      ann.role,
            "owner_name": ann.created_by.get_full_name() or ann.created_by.username,
            "is_mine":   ann.created_by_id == request.user.id,
            "created_at": ann.created_at.strftime("%Y-%m-%d %H:%M"),
        }
        for ann in annotations
    ]
    return JsonResponse({"success": True, "annotations": data})


@login_required
@require_POST
def add_annotation(request, submission_id):
    """
    POST /annotations/<submission_id>/add/
    Body (JSON): { type, page, x, y, text? }
    """
    err = _require_annotation_role(request)
    if err:
        return err

    submission = get_object_or_404(ExamSubmission, id=submission_id)

    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "message": "Invalid JSON"}, status=400)

    ann_type = body.get("type", "")
    if ann_type not in {"tick", "cross", "comment"}:
        return JsonResponse({"success": False, "message": "Invalid annotation type"}, status=400)

    try:
        page = int(body["page"])
        x    = float(body["x"])
        y    = float(body["y"])
    except (KeyError, ValueError, TypeError):
        return JsonResponse({"success": False, "message": "page, x, y are required numbers"}, status=400)

    text = body.get("text", "").strip()
    if ann_type == "comment" and not text:
        return JsonResponse({"success": False, "message": "Comment text is required"}, status=400)

    ann = PdfAnnotation.objects.create(
        submission=submission,
        created_by=request.user,
        role=request.user.role,
        ann_type=ann_type,
        page=page,
        x=x,
        y=y,
        text=text,
    )

    return JsonResponse({
        "success": True,
        "annotation": {
            "id":         ann.id,
            "type":       ann.ann_type,
            "page":       ann.page,
            "x":          ann.x,
            "y":          ann.y,
            "text":       ann.text,
            "colour":     ann.colour,
            "role":       ann.role,
            "owner_name": request.user.get_full_name() or request.user.username,
            "is_mine":    True,
            "created_at": ann.created_at.strftime("%Y-%m-%d %H:%M"),
        },
    })


@login_required
@require_http_methods(["DELETE"])
def delete_annotation(request, annotation_id):
    """
    DELETE /annotations/delete/<annotation_id>/
    Only the creator may delete their own annotation.
    """
    err = _require_annotation_role(request)
    if err:
        return err

    ann = get_object_or_404(PdfAnnotation, id=annotation_id)

    if ann.created_by_id != request.user.id:
        return JsonResponse(
            {"success": False, "message": "You can only delete your own annotations."},
            status=403,
        )

    ann.delete()
    return JsonResponse({"success": True, "message": "Annotation deleted."})


@login_required
@require_POST
def delete_annotations_bulk(request):
    """
    POST /annotations/delete-bulk/
    Body (JSON): { ids: [1, 2, 3] }
    Deletes only the annotations in `ids` that belong to the current user.
    Returns counts of deleted vs skipped.
    """
    err = _require_annotation_role(request)
    if err:
        return err

    try:
        body = json.loads(request.body)
        ids = [int(i) for i in body.get("ids", [])]
    except (json.JSONDecodeError, ValueError, TypeError):
        return JsonResponse({"success": False, "message": "Invalid payload"}, status=400)

    if not ids:
        return JsonResponse({"success": False, "message": "No ids provided"}, status=400)

    # Only delete annotations owned by this user
    owned_qs = PdfAnnotation.objects.filter(id__in=ids, created_by=request.user)
    deleted_count = owned_qs.count()
    owned_qs.delete()

    skipped = len(ids) - deleted_count
    return JsonResponse({
        "success":       True,
        "deleted_count": deleted_count,
        "skipped_count": skipped,
        "message":       f"Deleted {deleted_count} annotation(s). {skipped} skipped (not yours).",
    })


# ════════════════════════════════════════════════════════════════════════════
#  GRADE EDIT ENDPOINTS (with audit trail)
# ════════════════════════════════════════════════════════════════════════════


def _log_grade_change(submission, tier, user, old_marks, new_marks, old_feedback, new_feedback, note=""):
    GradeChangeLog.objects.create(
        submission=submission,
        tier=tier,
        changed_by=user,
        old_marks=old_marks,
        new_marks=new_marks,
        old_feedback=old_feedback,
        new_feedback=new_feedback,
        note=note,
    )


@login_required
@require_POST
def edit_marker_grade(request, submission_id):
    """
    POST /grade/marker/<submission_id>/edit/
    Assessor Marker may update marks / total_marks / feedback for their tier.
    """
    if request.user.role != "assessor_marker":
        return JsonResponse({"success": False, "message": "Permission denied"}, status=403)

    submission = get_object_or_404(ExamSubmission, id=submission_id)

    try:
        marks       = Decimal(request.POST.get("marks", ""))
        total_marks = Decimal(request.POST.get("total_marks", "100"))
    except InvalidOperation:
        return JsonResponse({"success": False, "message": "Invalid marks values"}, status=400)

    feedback = request.POST.get("feedback", "").strip()
    note     = request.POST.get("note", "").strip()
    marked_paper = request.FILES.get("marked_paper")

    if marked_paper and not marked_paper.name.lower().endswith(".pdf"):
        return JsonResponse({"success": False, "message": "Only PDF files are allowed"}, status=400)

    # Log before overwriting
    _log_grade_change(
        submission=submission,
        tier="marker",
        user=request.user,
        old_marks=submission.marks,
        new_marks=marks,
        old_feedback=submission.feedback,
        new_feedback=feedback,
        note=note,
    )

    submission.marks       = marks
    submission.total_marks = total_marks
    submission.feedback    = feedback
    submission.graded_by   = request.user
    submission.graded_at   = timezone.now()
    if marked_paper:
        submission.marked_paper = marked_paper
    submission.save()

    return JsonResponse({
        "success":    True,
        "message":    "Grade updated.",
        "marks":      float(marks),
        "total_marks": float(total_marks),
        "graded_by":  request.user.get_full_name() or request.user.username,
        "graded_at":  submission.graded_at.strftime("%b %d, %Y %H:%M"),
        "status":     submission.status,
        "has_marked_paper": bool(submission.marked_paper),
    })


@login_required
@require_POST
def edit_internal_grade(request, submission_id):
    """
    POST /grade/internal/<submission_id>/edit/
    Internal Moderator may update internal_* fields.
    """
    if request.user.role != "internal_mod":
        return JsonResponse({"success": False, "message": "Permission denied"}, status=403)

    submission = get_object_or_404(ExamSubmission, id=submission_id)

    try:
        marks       = Decimal(request.POST.get("marks", ""))
        total_marks = Decimal(request.POST.get("total_marks", "100"))
    except InvalidOperation:
        return JsonResponse({"success": False, "message": "Invalid marks values"}, status=400)

    feedback = request.POST.get("feedback", "").strip()
    note     = request.POST.get("note", "").strip()

    _log_grade_change(
        submission=submission,
        tier="internal",
        user=request.user,
        old_marks=submission.internal_marks,
        new_marks=marks,
        old_feedback=submission.internal_feedback,
        new_feedback=feedback,
        note=note,
    )

    submission.internal_marks       = marks
    submission.internal_total_marks = total_marks
    submission.internal_feedback    = feedback
    submission.internal_graded_by   = request.user
    submission.internal_graded_at   = timezone.now()
    submission.save()

    return JsonResponse({
        "success":    True,
        "message":    "Internal grade updated.",
        "marks":      float(marks),
        "total_marks": float(total_marks),
        "graded_by":  request.user.get_full_name() or request.user.username,
        "graded_at":  submission.internal_graded_at.strftime("%b %d, %Y %H:%M"),
        "status":     submission.status,
    })


@login_required
@require_POST
def edit_external_grade(request, submission_id):
    """
    POST /grade/external/<submission_id>/edit/
    External Moderator may update external_* fields.
    """
    if request.user.role != "external_mod":
        return JsonResponse({"success": False, "message": "Permission denied"}, status=403)

    submission = get_object_or_404(ExamSubmission, id=submission_id)

    try:
        marks       = Decimal(request.POST.get("marks", ""))
        total_marks = Decimal(request.POST.get("total_marks", "100"))
    except InvalidOperation:
        return JsonResponse({"success": False, "message": "Invalid marks values"}, status=400)

    feedback = request.POST.get("feedback", "").strip()
    note     = request.POST.get("note", "").strip()

    _log_grade_change(
        submission=submission,
        tier="external",
        user=request.user,
        old_marks=submission.external_marks,
        new_marks=marks,
        old_feedback=submission.external_feedback,
        new_feedback=feedback,
        note=note,
    )

    submission.external_marks       = marks
    submission.external_total_marks = total_marks
    submission.external_feedback    = feedback
    submission.external_graded_by   = request.user
    submission.external_graded_at   = timezone.now()
    submission.save()

    return JsonResponse({
        "success":    True,
        "message":    "External grade updated.",
        "marks":      float(marks),
        "total_marks": float(total_marks),
        "graded_by":  request.user.get_full_name() or request.user.username,
        "graded_at":  submission.external_graded_at.strftime("%b %d, %Y %H:%M"),
        "status":     submission.status,
    })


@login_required
@require_GET
def grade_change_log(request, submission_id):
    """
    GET /grade/<submission_id>/log/
    Returns the full grade-change audit trail for a submission.
    Accessible by all three annotation roles.
    """
    err = _require_annotation_role(request)
    if err:
        return err

    submission = get_object_or_404(ExamSubmission, id=submission_id)
    logs = GradeChangeLog.objects.filter(submission=submission).select_related("changed_by")

    data = [
        {
            "id":          log.id,
            "tier":        log.get_tier_display(),
            "changed_by":  log.changed_by.get_full_name() if log.changed_by else "Unknown",
            "old_marks":   str(log.old_marks) if log.old_marks is not None else None,
            "new_marks":   str(log.new_marks) if log.new_marks is not None else None,
            "old_feedback": log.old_feedback,
            "new_feedback": log.new_feedback,
            "note":        log.note,
            "changed_at":  log.changed_at.strftime("%Y-%m-%d %H:%M"),
        }
        for log in logs
    ]
    return JsonResponse({"success": True, "logs": data})
