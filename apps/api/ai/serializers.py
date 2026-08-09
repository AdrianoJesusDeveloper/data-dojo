from rest_framework import serializers


class AIChatSerializer(serializers.Serializer):
    mentor = serializers.CharField()
    message = serializers.CharField()
    
class AIChatSerializer(serializers.Serializer):

    mentor = serializers.CharField(
        required=True
    )

    message = serializers.CharField(
        required=True
    )