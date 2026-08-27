import uuid

from django.urls import reverse

from .base import PaymentGateway, PaymentIntent


class SandboxPaymentGateway(PaymentGateway):
    """Deterministic local gateway. It never contacts or charges a real provider."""

    name = "sandbox"
    sandbox = True

    def create_intent(self, *, order, requested_provider: str) -> PaymentIntent:
        external_id = f"sandbox_{uuid.uuid4().hex}"
        return PaymentIntent(
            external_id=external_id,
            status="pending",
            amount=order.total,
            checkout_url=reverse("store-sandbox-payment-approve", kwargs={"pk": order.pk}),
            metadata={
                "gateway": self.name,
                "requested_provider": requested_provider,
                "real_charge": False,
            },
        )
