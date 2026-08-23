from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import Conversation, Message
from .serializers import AIChatSerializer
from .services import AGENTS, chat_ai


class AIChatView(APIView):
    # O AI Sales é público para visitantes e futuros alunos.
    # Outros agentes continuam protegidos por autenticação.
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AIChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mentor = serializer.validated_data["mentor"]
        message = serializer.validated_data["message"]
        conversation_id = serializer.validated_data.get("conversation_id")

        if mentor != "ai_sales" and not request.user.is_authenticated:
            return Response(
                {"detail": "Autenticação necessária para este agente."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        conversation = None
        if conversation_id:
            conversation_query = Conversation.objects.filter(id=conversation_id)
            if request.user.is_authenticated:
                conversation_query = conversation_query.filter(user=request.user)
            else:
                conversation_query = conversation_query.filter(user__isnull=True)
            conversation = conversation_query.first()

            if conversation is None:
                return Response(
                    {"detail": "Conversa não encontrada."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if conversation is None:
            conversation = Conversation.objects.create(
                user=request.user if request.user.is_authenticated else None,
                mentor=mentor,
                title=message[:200],
            )

        history = list(
            conversation.messages.order_by("created_at").values("role", "content")
        )
        history = [
            {"role": item["role"], "content": item["content"]}
            for item in history
            if item["role"] in {"user", "assistant"}
        ]

        Message.objects.create(
            conversation=conversation,
            role="user",
            content=message,
        )

        try:
            answer = chat_ai(
                mentor,
                message,
                user=request.user if request.user.is_authenticated else None,
                history=history,
            )
        except Exception as exc:
            return Response(
                {"detail": "O agente de IA não pôde responder.", "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=answer,
        )

        return Response(
            {
                "agent": mentor,
                "agent_name": AGENTS.get(mentor, {}).get("name", mentor),
                "conversation_id": conversation.id,
                "message": answer,
                "whatsapp_url": "https://wa.me/5521972663791",
            },
            status=status.HTTP_200_OK,
        )
