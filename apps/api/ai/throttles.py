from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AIAnonRateThrottle(AnonRateThrottle):
    """Limite específico para visitantes que usam o agente comercial."""

    scope = "ai_anon"


class AIUserRateThrottle(UserRateThrottle):
    """Limite específico para usuários autenticados dos agentes de IA."""

    scope = "ai_user"
