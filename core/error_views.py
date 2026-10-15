from django.conf import settings
from django.shortcuts import render

ERRORS = {
    400: ("Bad Request", "The request could not be understood. Please check and try again."),
    403: ("Access Denied", "You do not have permission to view this page."),
    404: ("Page Not Found", "The page or file you are looking for does not exist or has been moved."),
    500: ("Something Went Wrong", "An unexpected error occurred on our side. Our team has been notified."),
}


def render_error(request, status):
    title, message = ERRORS.get(status, ("Error", "An error occurred."))
    return render(
        request,
        "core/error.html",
        {"status_code": status, "title": title, "message": message},
        status=status,
    )


def bad_request(request, exception=None):
    return render_error(request, 400)


def permission_denied(request, exception=None):
    return render_error(request, 403)


def page_not_found(request, exception=None):
    return render_error(request, 404)


def server_error(request):
    return render_error(request, 500)


class BrandedErrorMiddleware:
    """Replace Django's technical debug pages with the branded error page.

    Needed because Django shows its yellow debug page for 404/500 whenever
    DEBUG is True. Disable with BRANDED_ERRORS=False to see raw tracebacks.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            settings.DEBUG
            and getattr(settings, "BRANDED_ERRORS", True)
            and response.status_code in (404, 500)
            and "text/html" in response.get("Content-Type", "")
            and not request.path.startswith(("/api/", settings.MEDIA_URL, settings.STATIC_URL))
            and (response.status_code == 500 or b"Django tried these URL patterns" in response.content
                 or b"Page not found" in response.content)
        ):
            return render_error(request, response.status_code)
        return response
