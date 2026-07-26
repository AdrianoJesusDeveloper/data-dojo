# api/middleware.py
import logging

logger = logging.getLogger(__name__)

class OriginLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.META.get("HTTP_ORIGIN")
        logger.info(f"Requisição recebida: {request.method} {request.path} | Origin: {origin}")
        response = self.get_response(request)
        return response
