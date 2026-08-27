from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any


class PaymentConfigurationError(RuntimeError):
    """Raised when checkout is requested without a configured gateway."""


@dataclass(frozen=True)
class PaymentIntent:
    external_id: str
    status: str
    amount: Decimal
    checkout_url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class PaymentGateway(ABC):
    name: str
    sandbox: bool = False

    @property
    def available(self) -> bool:
        return True

    @abstractmethod
    def create_intent(self, *, order, requested_provider: str) -> PaymentIntent:
        raise NotImplementedError
