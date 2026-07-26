# apps/api/middleware.py
# Middleware vazio para evitar erro de importação

class OriginLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response