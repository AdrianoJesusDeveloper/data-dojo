from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Conversation, Message
from .serializers import AIChatSerializer
from .services import AGENTS, chat_ai


class AIChatView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AIChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mentor = serializer.validated_data["mentor"]
        message = serializer.validated_data["message"]
        conversation_id = serializer.validated_data.get("conversation_id")

        conversation = None
        if conversation_id:
            conversation = Conversation.objects.filter(
                id=conversation_id,
                user=request.user,
            ).first()
            if conversation is None:
                return Response(
                    {"detail": "Conversa não encontrada."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if conversation is None:
            conversation = Conversation.objects.create(
                user=request.user,
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
                user=request.user,
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
            },
            status=status.HTTP_200_OK,
        )
