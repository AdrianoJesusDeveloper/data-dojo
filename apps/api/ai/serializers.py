from rest_framework import serializers


class AIChatSerializer(serializers.Serializer):
    mentor = serializers.ChoiceField(
        choices=["dojo_ai", "ai_sales", "chatgpt", "gemini", "deepseek", "copilot"]
    )
    message = serializers.CharField(required=True, allow_blank=False)
    conversation_id = serializers.IntegerField(required=False, allow_null=True)
