from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Payment, PaymentStatus
from database.repositories import (
    PaymentRepository,
    TariffRepository,
    UserRepository,
)
from services.payments.models import PaymentConfirmation, PaymentRequest
from services.payments.provider import PaymentProvider
from services.subscriptions import SubscriptionService


class PaymentServiceError(Exception):
    pass


class PaymentUserNotFoundError(PaymentServiceError):
    pass


class TariffUnavailableError(PaymentServiceError):
    pass


class PaymentNotFoundError(PaymentServiceError):
    pass


class PaymentStateError(PaymentServiceError):
    pass


@dataclass(frozen=True, slots=True)
class PaymentCheckout:
    payment_id: int
    provider_payment_id: str
    checkout_url: str


@dataclass(frozen=True, slots=True)
class UserPaymentStatus:
    payment_id: int
    status: PaymentStatus
    tariff_name: str
    subscription_expires_at: datetime | None


class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        provider: PaymentProvider,
        currency: str = "RUB",
    ) -> None:
        normalized_currency = currency.upper()
        if len(normalized_currency) != 3:
            raise ValueError("currency must be a three-letter code")
        if not provider.name.strip():
            raise ValueError("provider name must not be empty")

        self.session = session
        self.provider = provider
        self.currency = normalized_currency
        self.payments = PaymentRepository(session)
        self.tariffs = TariffRepository(session)
        self.users = UserRepository(session)

    async def create_payment(
        self,
        max_user_id: int,
        tariff_code: str,
    ) -> PaymentCheckout:
        try:
            user = await self.users.get_by_max_user_id(max_user_id)
            if user is None:
                raise PaymentUserNotFoundError("User not found")

            tariff = await self.tariffs.get_by_code(tariff_code)
            if tariff is None or not tariff.is_active:
                raise TariffUnavailableError("Tariff is not available")

            created = await self.provider.create_payment(
                PaymentRequest(
                    amount=tariff.price,
                    currency=self.currency,
                    description=tariff.name,
                )
            )
            payment = await self.payments.create(
                user_id=user.id,
                tariff_id=tariff.id,
                provider=self.provider.name,
                provider_payment_id=created.provider_payment_id,
                amount=tariff.price,
                currency=self.currency,
            )
            await self.session.commit()
            await self.session.refresh(payment)
        except Exception:
            await self.session.rollback()
            raise

        return PaymentCheckout(
            payment_id=payment.id,
            provider_payment_id=payment.provider_payment_id,
            checkout_url=created.checkout_url,
        )

    async def get_user_payment_status(
        self,
        max_user_id: int,
        payment_id: int,
    ) -> UserPaymentStatus | None:
        user = await self.users.get_by_max_user_id(max_user_id)
        if user is None:
            return None
        payment = await self.payments.get_by_id_and_user_id(
            payment_id,
            user.id,
        )
        if payment is None:
            return None
        tariff = await self.tariffs.get_by_id(payment.tariff_id)
        if tariff is None:
            raise RuntimeError("Payment tariff does not exist")
        expires_at = None
        if payment.status is PaymentStatus.PAID:
            access = await SubscriptionService(
                self.session,
                free_history_limit=1,
            ).get_user_access(user.id)
            expires_at = access.expires_at
        return UserPaymentStatus(
            payment_id=payment.id,
            status=payment.status,
            tariff_name=tariff.name,
            subscription_expires_at=expires_at,
        )

    async def process_successful_confirmation(
        self,
        confirmation: PaymentConfirmation,
    ) -> Payment:
        if confirmation.status is not PaymentStatus.PAID:
            raise PaymentStateError("Confirmation is not successful")

        paid_at = confirmation.paid_at or datetime.now(timezone.utc)
        if paid_at.tzinfo is None:
            raise PaymentStateError("paid_at must be timezone-aware")

        try:
            payment = await self.payments.get_by_provider_payment_id(
                provider=self.provider.name,
                provider_payment_id=confirmation.provider_payment_id,
                for_update=True,
            )
            if payment is None:
                raise PaymentNotFoundError("Payment not found")
            if payment.status is PaymentStatus.PAID:
                await self.session.commit()
                return payment
            if payment.status is not PaymentStatus.PENDING:
                raise PaymentStateError(
                    f"Payment cannot be paid from status {payment.status.value}"
                )

            await SubscriptionService(
                self.session,
                free_history_limit=1,
            ).grant_paid_subscription(
                user_id=payment.user_id,
                tariff_id=payment.tariff_id,
                now=paid_at,
                commit=False,
            )
            await self.payments.mark_paid(payment, paid_at=paid_at)
            await self.session.commit()
            await self.session.refresh(payment)
            return payment
        except Exception:
            await self.session.rollback()
            raise
