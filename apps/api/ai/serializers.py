from rest_framework import serializers

from .agent_registry import AGENT_REGISTRY


class AIChatSerializer(serializers.Serializer):
    mentor = serializers.ChoiceField(choices=list(AGENT_REGISTRY.keys()) + ["chatgpt", "gemini", "deepseek", "copilot"])
    message = serializers.CharField(required=True, allow_blank=False, max_length=4000, trim_whitespace=True)
    conversation_id = serializers.CharField(required=False, allow_null=True, max_length=36)
    conversation_token = serializers.CharField(required=False, allow_blank=False, max_length=128, write_only=True)
