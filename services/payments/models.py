from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from database.models import PaymentStatus


@dataclass(frozen=True, slots=True)
class PaymentRequest:
    amount: Decimal
    currency: str
    description: str


@dataclass(frozen=True, slots=True)
class CreatedPayment:
    provider_payment_id: str
    checkout_url: str


@dataclass(frozen=True, slots=True)
class PaymentConfirmation:
    provider_payment_id: str
    status: PaymentStatus
    paid_at: datetime | None = None
