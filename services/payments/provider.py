from collections.abc import Mapping
from typing import Protocol

from services.payments.models import (
    CreatedPayment,
    PaymentConfirmation,
    PaymentRequest,
)


class PaymentProvider(Protocol):
    @property
    def name(self) -> str: ...

    async def create_payment(self, request: PaymentRequest) -> CreatedPayment: ...

    def normalize_confirmation(
        self,
        payload: Mapping[str, object],
    ) -> PaymentConfirmation: ...
