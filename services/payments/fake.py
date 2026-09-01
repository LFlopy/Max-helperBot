from collections.abc import Mapping
from datetime import datetime

from database.models import PaymentStatus
from services.payments.models import (
    CreatedPayment,
    PaymentConfirmation,
    PaymentRequest,
)


class FakePaymentProvider:
    name = "fake"

    def __init__(self) -> None:
        self.requests: list[PaymentRequest] = []

    async def create_payment(self, request: PaymentRequest) -> CreatedPayment:
        self.requests.append(request)
        payment_id = f"fake-{len(self.requests)}"
        return CreatedPayment(
            provider_payment_id=payment_id,
            checkout_url=f"https://payments.example/{payment_id}",
        )

    def normalize_confirmation(
        self,
        payload: Mapping[str, object],
    ) -> PaymentConfirmation:
        provider_payment_id = payload.get("provider_payment_id")
        status = payload.get("status")
        paid_at = payload.get("paid_at")

        if not isinstance(provider_payment_id, str):
            raise ValueError("provider_payment_id must be a string")
        if not isinstance(status, str):
            raise ValueError("status must be a string")
        if paid_at is not None and not isinstance(paid_at, datetime):
            raise ValueError("paid_at must be a datetime")

        try:
            payment_status = PaymentStatus(status)
        except ValueError as error:
            raise ValueError("Unsupported payment status") from error

        return PaymentConfirmation(
            provider_payment_id=provider_payment_id,
            status=payment_status,
            paid_at=paid_at,
        )
