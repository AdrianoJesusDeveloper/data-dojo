from rest_framework import serializers

from .agent_registry import AGENT_REGISTRY


class AIChatSerializer(serializers.Serializer):
    mentor = serializers.ChoiceField(choices=list(AGENT_REGISTRY.keys()) + ["chatgpt", "gemini", "deepseek", "copilot"])
    message = serializers.CharField(required=True, allow_blank=False)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
