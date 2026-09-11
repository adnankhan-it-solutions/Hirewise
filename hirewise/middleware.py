import uuid
import json
import logging


class SecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.correlation_id = uuid.uuid4()
        response = self.get_response(request)
        response['X-Request-ID'] = str(request.correlation_id)
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if request.path.startswith(('/dashboard/', '/accounts/', '/portal/', '/applications/', '/documents/', '/interviews/')):
            response['X-Robots-Tag'] = 'noindex, nofollow'
            response['Cache-Control'] = 'no-store, private'
        route = getattr(getattr(request, 'resolver_match', None), 'url_name', None) or 'unmatched'
        logging.getLogger('hirewise.requests').info(json.dumps({
            'event': 'http.request', 'request_id': str(request.correlation_id),
            'route': route, 'method': request.method, 'status': response.status_code,
        }))
        return response
