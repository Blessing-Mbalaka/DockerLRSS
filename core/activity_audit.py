import json
import logging
import re
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from django.utils import timezone
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.db.models import Q
from .models import ActivityEvent, ActivitySession

logger = logging.getLogger(__name__)

def record(request, kind, user=None, **fields):
    try:
        user = user or getattr(request, 'user', None)
        authenticated = user and user.is_authenticated
        return ActivityEvent.objects.create(
            user=user if authenticated else None,
            username=user.username if authenticated else '', kind=kind,
            path=request.path[:500] if request else '',
            ip=(request.META.get('REMOTE_ADDR', '')[:45] if request else ''),
            session_id=request.session.get('activity_session_id') if request else None,
            **fields)
    except Exception:
        logger.exception('Activity event could not be recorded')

@receiver(user_logged_in)
def login_event(sender, request, user, **kwargs):
    try:
        session = ActivitySession.objects.create(user=user, username=user.username,
            expires_at=request.session.get_expiry_date())
        request.session['activity_session_id'] = session.pk
        record(request, 'login', user)
    except Exception:
        logger.exception('Login audit could not be recorded')

@receiver(user_logged_out)
def logout_event(sender, request, user, **kwargs):
    record(request, 'logout', user)
    if request:
        ActivitySession.objects.filter(pk=request.session.get('activity_session_id')).update(
            ended_at=timezone.now(), last_seen=timezone.now())

@receiver(user_login_failed)
def failed_event(sender, credentials, request, **kwargs):
    # Never persist credentials, submitted forms, answers or query strings.
    if request:
        record(request, 'login_failed', method='POST')

class ActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated and user.role == 'it':
            if request.path not in ['/it/monitor/', '/activity/click/', '/logout/'] and not request.path.startswith('/static/'):
                record(request, 'access_denied', method=request.method, status=403)
                return HttpResponseForbidden('IT accounts can only access the activity monitor.')
        response = self.get_response(request)
        if request.path.startswith(('/static/', '/media/')) or request.path == '/activity/click/':
            return response
        try:
            if getattr(request, 'user', None) and request.user.is_authenticated:
                ActivitySession.objects.filter(pk=request.session.get('activity_session_id')).update(last_seen=timezone.now())
                action = request.POST.get('action', '') if request.method == 'POST' and not request.path == '/' else ''
                action = action if re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', action) else ''
                record(request, 'security' if response.status_code in (401,403,429) else 'request',
                       method=request.method, status=response.status_code, action=action)
                if (not response.streaming and 'text/html' in response.get('Content-Type', '')
                        and response.status_code == 200 and not response.get('Content-Encoding')):
                    script = b'''<script src="/static/core/js/activity-audit.js" defer></script>'''
                    response.content = response.content.replace(b'</body>', script+b'</body>')
                    if response.has_header('Content-Length'):
                        response['Content-Length'] = len(response.content)
        except Exception:
            logger.exception('Activity monitoring failed')
        return response

@require_POST
def click(request):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()
    if len(request.body) > 2048:
        return JsonResponse({'error':'Too large'}, status=400)
    try:
        data = json.loads(request.body)
        path = data.get('path', '')
        action = data.get('action', '')
        if not isinstance(path,str) or not path.startswith('/') or not isinstance(action,str):
            raise ValueError()
        # Browser click reports describe intent, not proof that a server operation succeeded.
        event = record(request, 'click', action=action[:120])
        if event:
            event.path = path.split('?')[0].split('#')[0][:500]
            event.save(update_fields=['path'])
    except (ValueError,TypeError,AttributeError):
        return JsonResponse({'error':'Invalid event'}, status=400)
    return JsonResponse({'ok':True})

def monitor(request):
    if not request.user.is_authenticated or request.user.role != 'it':
        return HttpResponseForbidden('IT monitoring access required.')
    events = ActivityEvent.objects.select_related('user')
    q = request.GET.get('q','')[:100]
    kind = request.GET.get('kind','')[:30]
    if q:
        events = events.filter(Q(username__icontains=q)|Q(path__icontains=q)|Q(action__icontains=q))
    if kind:
        events = events.filter(kind=kind)
    return render(request,'core/it/monitor.html',{
        'events':Paginator(events,50).get_page(request.GET.get('page')),
        'sessions':ActivitySession.objects.order_by('-started_at')[:50],
        'q':q,'kind':kind,
        'kinds':['login','logout','login_failed','request','click','security','access_denied'],
    })
