# -*- coding: utf-8 -*-
"""Adapter de pagamento Mercado Pago para a 3DStore.

Usa a API REST do Mercado Pago v1 diretamente via `requests` para evitar
dependência de SDKs opcionais.  Para ativar, defina no .env:

    PAYMENT_BACKEND=mercado_pago
    MERCADO_PAGO_ACCESS_TOKEN=APP_USR-...
    MERCADO_PAGO_PUBLIC_KEY=APP_USR-...   (opcional, exibido para o frontend)
    MERCADO_PAGO_NOTIFICATION_URL=https://sua-api.com/api/store/payments/webhook/mp/

Documentação: https://www.mercadopago.com.br/developers/pt/reference
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

import requests
from django.conf import settings

from .base import PaymentConfigurationError, PaymentGateway, PaymentIntent

logger = logging.getLogger(__name__)

MP_API_BASE = "https://api.mercadopago.com"
_REQUEST_TIMEOUT = 15  # segundos


class MercadoPagoGateway(PaymentGateway):
    """Gateway de produção integrado ao Mercado Pago Checkout Pro."""

    name = "mercado_pago"
    sandbox = False

    def __init__(self) -> None:
        self._access_token: str = getattr(settings, "MERCADO_PAGO_ACCESS_TOKEN", "").strip()
        if not self._access_token:
            raise PaymentConfigurationError(
                "MERCADO_PAGO_ACCESS_TOKEN não está configurado. "
                "Defina a variável de ambiente antes de ativar este backend."
            )

    @property
    def available(self) -> bool:
        return bool(self._access_token)

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(uuid.uuid4()),
        }

    def _build_items(self, order: Any) -> list[dict]:
        """Converte os itens do pedido para o formato esperado pelo MP."""
        items = []
        for item in order.items.select_related("product"):
            items.append(
                {
                    "id": str(item.product.pk),
                    "title": item.product.name[:256],
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price),
                    "currency_id": "BRL",
                }
            )
        return items

    def create_intent(self, *, order: Any, requested_provider: str) -> PaymentIntent:
        notification_url: str = getattr(settings, "MERCADO_PAGO_NOTIFICATION_URL", "").strip()
        back_urls: dict = getattr(
            settings,
            "MERCADO_PAGO_BACK_URLS",
            {
                "success": f"{settings.DOJO_APP_URL.rstrip('/')}/store?payment=success",
                "failure": f"{settings.DOJO_APP_URL.rstrip('/')}/store?payment=failure",
                "pending": f"{settings.DOJO_APP_URL.rstrip('/')}/store?payment=pending",
            },
        )

        payload: dict[str, Any] = {
            "external_reference": str(order.pk),
            "items": self._build_items(order),
            "payer": {
                "email": order.user.email,
            },
            "back_urls": back_urls,
            "auto_return": "approved",
            "binary_mode": False,
            "statement_descriptor": "DATA DRIVEN DOJO",
            "metadata": {
                "order_id": str(order.pk),
                "user_id": str(order.user_id),
            },
        }

        if notification_url:
            payload["notification_url"] = notification_url

        try:
            response = requests.post(
                f"{MP_API_BASE}/checkout/preferences",
                json=payload,
                headers=self._headers(),
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
        except requests.Timeout as exc:
            logger.error("Mercado Pago timeout ao criar preferência do pedido %s", order.pk)
            raise PaymentConfigurationError(
                "Serviço do Mercado Pago não respondeu a tempo. Tente novamente."
            ) from exc
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response is not None else 0
            logger.error(
                "Mercado Pago retornou HTTP %s para o pedido %s",
                status_code,
                order.pk,
            )
            if status_code == 401:
                raise PaymentConfigurationError(
                    "Access token do Mercado Pago inválido ou expirado."
                ) from exc
            raise PaymentConfigurationError(
                f"Erro do Mercado Pago ao processar o pedido (HTTP {status_code})."
            ) from exc
        except requests.RequestException as exc:
            logger.error(
                "Erro de rede ao criar preferência MP para o pedido %s: %s",
                order.pk,
                type(exc).__name__,
            )
            raise PaymentConfigurationError(
                "Não foi possível conectar ao Mercado Pago. Verifique a conexão."
            ) from exc

        data = response.json()
        preference_id: str = data.get("id", "")
        # Em produção usa init_point; em sandbox usa sandbox_init_point.
        checkout_url: str = data.get("init_point") or data.get("sandbox_init_point", "")

        return PaymentIntent(
            external_id=preference_id,
            status="pending",
            amount=order.total,
            checkout_url=checkout_url,
            metadata={
                "gateway": self.name,
                "preference_id": preference_id,
                "requested_provider": requested_provider,
                "mp_response": {
                    "id": preference_id,
                    "date_created": data.get("date_created"),
                },
            },
        )
