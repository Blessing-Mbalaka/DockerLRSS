from __future__ import annotations

import random
from collections import defaultdict
from typing import Dict, List, Tuple

from django.db.models import Count
from django.db import transaction
from core.models import QuestionUse
from core.question_usage import normalize_set

from core.models import ExtractorPaper as Paper, ExtractorUserBox as UserBox, ExtractorTestPaper as TestPaper, ExtractorTestItem as TestItem

try:  # optional integration with core app metadata
    from core.models import Qualification  # type: ignore
    from core.randomization_config import get_qualification_meta  # type: ignore
except Exception:  # pragma: no cover - core app not available in standalone extractor
    Qualification = None
    get_qualification_meta = None


def list_modules() -> List[str]:
    modules = set(
        Paper.objects.exclude(module_name="").values_list("module_name", flat=True)
    )

    if Qualification and get_qualification_meta:
        for qual_name in Qualification.objects.values_list('name', flat=True):
            meta = get_qualification_meta(qual_name)
            module_map = meta.get('modules', {}) if isinstance(meta, dict) else {}
            if isinstance(module_map, dict):
                modules.update(str(code) for code in module_map.keys())

    return sorted(filter(None, modules))


def bank_counts(module_name: str) -> Dict[str, int]:
    """Return counts of available question_number entries for a module (questions only)."""
    qs = (
        UserBox.objects
        .filter(paper__module_name=module_name, qtype="question")
        .values("question_number")
        .annotate(n=Count("id"))
    )
    return {row["question_number"] or "": row["n"] for row in qs}


def pick_random_for_qnums(module_name: str, qnums: List[str], set_number='1') -> List[UserBox]:
    """For each question_number, pick one random UserBox from that module.

    If none available for a qnum, skip it.
    """
    boxes_by_q: Dict[str, List[UserBox]] = defaultdict(list)
    qs = UserBox.objects.filter(paper__module_name=module_name, qtype="question", question_number__in=qnums)
    qs = qs.exclude(set_uses__set_number=normalize_set(set_number))
    for bx in qs:
        boxes_by_q[bx.question_number].append(bx)
    picked: List[UserBox] = []
    for q in qnums:
        lst = boxes_by_q.get(q) or []
        if not lst:
            continue
        picked.append(random.choice(lst))
    return picked


@transaction.atomic
def build_test_from_boxes(module_name: str, title: str, boxes, set_number='1'):
    set_number = normalize_set(set_number)
    test = TestPaper.objects.create(module_name=module_name, title=title)
    seen = set()
    for idx, bx in enumerate(boxes, start=1):
        if bx.pk in seen:
            raise ValueError('A question cannot appear twice in one test.')
        seen.add(bx.pk)
        if bx.qtype in {'question', 'question_part'}:
            _, created = QuestionUse.objects.get_or_create(box=bx, set_number=set_number)
            if not created:
                raise ValueError(f'Question {bx.question_number} was already used in set {set_number}.')
        TestItem.objects.create(test=test, order_index=idx, question_number=bx.question_number,
            marks=bx.marks, qtype=bx.qtype, content_type=bx.content_type, content=bx.content)
    return test


def boxes_for_ids_preserve_order(ids: List[int]) -> List[UserBox]:
    if not ids:
        return []
    id_to_pos = {bid: i for i, bid in enumerate(ids)}
    found = list(UserBox.objects.filter(id__in=ids))
    found.sort(key=lambda b: id_to_pos.get(b.id, 1_000_000))
    return found
