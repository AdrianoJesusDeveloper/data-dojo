from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .serializers import AIChatSerializer
from .services import chat_ai


class AIChatView(APIView):

    permission_classes = [AllowAny]

    def post(self, request):
        ...