from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render

from core.models import ExamSubmission


def _build_submission_result(submission):
    if submission.external_marks is not None:
        final_marks = submission.external_marks
        final_total = submission.external_total_marks
        status = "Finalized"
    elif submission.internal_marks is not None:
        final_marks = submission.internal_marks
        final_total = submission.internal_total_marks
        status = "Reviewed"
    elif submission.marks is not None:
        final_marks = submission.marks
        final_total = submission.total_marks
        status = "Graded by Marker"
    else:
        final_marks = None
        final_total = submission.total_marks
        status = "Pending"

    percentage = None
    if final_marks is not None and final_total:
        percentage = (final_marks / final_total) * Decimal("100")

    return {
        "submission": submission,
        "final_marks": final_marks,
        "final_total": final_total,
        "percentage": percentage,
        "status": status,
        "passed": percentage is not None and percentage >= Decimal("50"),
        "has_marked_paper": bool(
            submission.marked_paper
            or submission.internal_marked_paper
            or submission.external_marked_paper
        ),
    }


@login_required
def student_graded_assessments(request):
    graded_submissions = (
        ExamSubmission.objects.filter(student=request.user)
        .filter(
            Q(marks__isnull=False)
            | Q(internal_marks__isnull=False)
            | Q(external_marks__isnull=False)
            | Q(marked_paper__isnull=False)
            | Q(internal_marked_paper__isnull=False)
            | Q(external_marked_paper__isnull=False)
        )
        .select_related("paper", "assessment", "assessment__qualification")
        .order_by("-submitted_at")
    )

    graded_results = [_build_submission_result(submission) for submission in graded_submissions]

    percentages = [
        result["percentage"] for result in graded_results if result["percentage"] is not None
    ]
    average_percentage = (
        sum(percentages, Decimal("0")) / len(percentages) if percentages else None
    )

    context = {
        "graded_results": graded_results,
        "summary": {
            "graded_count": len(graded_results),
            "finalized_count": sum(1 for result in graded_results if result["status"] == "Finalized"),
            "with_marked_paper_count": sum(1 for result in graded_results if result["has_marked_paper"]),
            "average_percentage": average_percentage,
        },
    }
    return render(
        request,
        "core/Marking_Logic/student_graded_assessments.html",
        context,
    )