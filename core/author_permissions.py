from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def assessor_author_required(view):
    """Authoring is reserved for assessor developers and system administrators."""
    @login_required
    @wraps(view)
    def guarded(request, *args, **kwargs):
        user = request.user
        if not (user.is_superuser or getattr(user, "role", "") in {"assessor_dev", "admin", "administrator"}):
            raise PermissionDenied("Only assessor developers may author assessment papers.")
        return view(request, *args, **kwargs)
    return guarded
