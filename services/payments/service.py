from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import (
    PaymentRepository,
    TariffRepository,
    UserRepository,
)
from services.payments.models import PaymentRequest
from services.payments.provider import PaymentProvider


class PaymentServiceError(Exception):
    pass


class PaymentUserNotFoundError(PaymentServiceError):
    pass


class TariffUnavailableError(PaymentServiceError):
    pass


@dataclass(frozen=True, slots=True)
class PaymentCheckout:
    payment_id: int
    provider_payment_id: str
    checkout_url: str


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
