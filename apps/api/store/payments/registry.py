from django.conf import settings

from .base import PaymentConfigurationError, PaymentGateway
from .disabled import DisabledPaymentGateway
from .sandbox import SandboxPaymentGateway


def get_payment_gateway() -> PaymentGateway:
    backend = getattr(settings, "PAYMENT_BACKEND", "disabled").strip().lower()
    gateways = {
        "disabled": DisabledPaymentGateway,
        "sandbox": SandboxPaymentGateway,
    }
    gateway_class = gateways.get(backend)
    if gateway_class is None:
        raise PaymentConfigurationError(f"Backend de pagamento desconhecido: {backend}")
    return gateway_class()
