"""Reserve captured questions once per generated set, atomically."""
from contextvars import ContextVar
from functools import wraps
from django.db import IntegrityError, transaction

active_set = ContextVar('lms_randomization_set', default=None)
active_paper = ContextVar('lms_randomization_paper', default=None)


def normalize_set(value):
    value = str(value or '1').strip()
    if not value.isascii() or not value.isdigit() or len(value) > 50 or int(value) < 1:
        raise ValueError('Set number must be a positive whole number, up to 50 digits.')
    return str(int(value))


def reserve_questions(builder):
    @wraps(builder)
    def wrapped(*args, **kwargs):
        from .models import Paper, QuestionUse, ExtractorUserBox
        from .paper_utils import RandomizationPoolError
        import inspect
        bound = inspect.signature(builder).bind(*args, **kwargs)
        target = bound.arguments['target_paper']
        base = bound.arguments.get('base_extractor')
        meta = target.structure_json if isinstance(target.structure_json, dict) else {}
        set_number = normalize_set((meta.get('randomization') or {}).get('set_number') or getattr(base, 'paper_number', '') or '1')
        token = active_set.set(set_number)
        paper_token = active_paper.set(target.pk)
        try:
            with transaction.atomic():
                # Serialize changes to this output, and let the unique constraint arbitrate concurrent outputs.
                Paper.objects.select_for_update().get(pk=target.pk)
                result = builder(*args, **kwargs)
                ids = {entry.get('box_id') for entry in result.get('selected_boxes', []) if entry.get('box_id')}
                questions = ExtractorUserBox.objects.filter(pk__in=ids, qtype__in=['question', 'question_part'])
                for box in questions:
                    use, created = QuestionUse.objects.get_or_create(box=box, set_number=set_number,
                                                                    defaults={'paper': target})
                    if not created and use.paper_id != target.pk:
                        raise RandomizationPoolError(f'Question {box.question_number} was already used in set {set_number}.')
                return result
        except IntegrityError as exc:
            raise RandomizationPoolError('A selected question was just used in this set. Please retry with available questions.') from exc
        finally:
            active_set.reset(token)
            active_paper.reset(paper_token)
    return wrapped


def randomization_response(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        from django.db import OperationalError
        from django.http import JsonResponse
        try:
            return view(*args, **kwargs)
        except OperationalError:
            return JsonResponse({'ok': False, 'message': 'Another change is being saved. Please retry randomization in a moment.'}, status=409)
    return wrapped
