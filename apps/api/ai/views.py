import hashlib
import secrets

from django.conf import settings
from django.utils.crypto import constant_time_compare
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .agent_registry import AGENT_REGISTRY
from .models import Conversation, Message
from .serializers import AIChatSerializer
from .services import WHATSAPP_URL, agent_runtime_status, ai_is_enabled, chat_ai
from .throttles import AIAnonRateThrottle, AIUserRateThrottle


class AIAgentsView(APIView):
    """Lista os agentes disponíveis para a interface do Dojô."""
    permission_classes = [AllowAny]

    def get(self, request):
        agents = []
        for key, config in AGENT_REGISTRY.items():
            if config["public"] or request.user.is_authenticated:
                runtime = agent_runtime_status(config)
                agents.append({
                    "key": key,
                    "name": config["name"],
                    "description": config["description"],
                    "specialty": config["specialty"],
                    "public": config["public"],
                    "provider": runtime["provider"],
                    "available": runtime["available"],
                })
        return Response({"agents": agents}, status=status.HTTP_200_OK)


class AIChatView(APIView):
    # O AI Sales é público para visitantes e futuros alunos.
    # Outros agentes continuam protegidos por autenticação.
    permission_classes = [AllowAny]

    def get_throttles(self):
        throttle_class = AIUserRateThrottle if self.request.user.is_authenticated else AIAnonRateThrottle
        return [throttle_class()]

    def post(self, request):
        if not ai_is_enabled():
            return Response(
                {"detail": "Os agentes de IA não estão disponíveis neste ambiente."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serializer = AIChatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        mentor = serializer.validated_data["mentor"]
        message = serializer.validated_data["message"]
        conversation_id = serializer.validated_data.get("conversation_id")
        conversation_token = serializer.validated_data.get("conversation_token")

        agent = AGENT_REGISTRY.get(mentor)
        if agent and not agent["public"] and not request.user.is_authenticated:
            return Response(
                {"detail": "Autenticação necessária para este agente."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        conversation = None
        if conversation_id:
            if request.user.is_authenticated:
                conversation_query = Conversation.objects.filter(
                    id=conversation_id, user=request.user, mentor=mentor
                )
            else:
                conversation_query = Conversation.objects.filter(
                    public_id=conversation_id, user__isnull=True, mentor=mentor
                )
            try:
                conversation = conversation_query.first()
            except (TypeError, ValueError):
                conversation = None

            if conversation is not None and not request.user.is_authenticated:
                supplied_hash = hashlib.sha256((conversation_token or "").encode()).hexdigest()
                if not conversation.anonymous_access_hash or not constant_time_compare(
                    supplied_hash, conversation.anonymous_access_hash
                ):
                    conversation = None

            if conversation is None:
                return Response(
                    {"detail": "Conversa não encontrada."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        issued_conversation_token = None
        if conversation is None:
            if not request.user.is_authenticated:
                issued_conversation_token = secrets.token_urlsafe(32)
            conversation = Conversation.objects.create(
                user=request.user if request.user.is_authenticated else None,
                mentor=mentor,
                title=message[:200],
                anonymous_access_hash=(
                    hashlib.sha256(issued_conversation_token.encode()).hexdigest()
                    if issued_conversation_token
                    else ""
                ),
            )

        history_limit = max(2, int(getattr(settings, "AI_HISTORY_MESSAGE_LIMIT", 20)))
        history = list(
            conversation.messages.order_by("-created_at").values("role", "content")[:history_limit]
        )
        history.reverse()
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
            payload = {"detail": "O agente de IA não pôde responder. Confira o provedor configurado."}
            if settings.DEBUG:
                payload["error"] = f"{type(exc).__name__}: {exc}"
            return Response(
                payload,
                status=status.HTTP_502_BAD_GATEWAY,
            )

        Message.objects.create(
            conversation=conversation,
            role="assistant",
            content=answer,
        )

        agent_name = agent["name"] if agent else mentor
        return Response(
            {
                "agent": mentor,
                "agent_name": agent_name,
                "conversation_id": (
                    conversation.id
                    if request.user.is_authenticated
                    else str(conversation.public_id)
                ),
                **(
                    {"conversation_token": issued_conversation_token}
                    if issued_conversation_token
                    else {}
                ),
                "message": answer,
                "whatsapp_url": WHATSAPP_URL,
            },
            status=status.HTTP_200_OK,
        )
