from .base import PaymentConfigurationError, PaymentGateway, PaymentIntent


class DisabledPaymentGateway(PaymentGateway):
    name = "disabled"

    @property
    def available(self) -> bool:
        return False

    def create_intent(self, *, order, requested_provider: str) -> PaymentIntent:
        raise PaymentConfigurationError("Nenhum provedor de pagamento está configurado.")
