from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Payment, PaymentStatus


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        user_id: int,
        tariff_id: int,
        provider: str,
        provider_payment_id: str,
        amount: Decimal,
        currency: str,
    ) -> Payment:
        payment = Payment(
            user_id=user_id,
            tariff_id=tariff_id,
            provider=provider,
            provider_payment_id=provider_payment_id,
            amount=amount,
            currency=currency,
            status=PaymentStatus.PENDING,
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_by_id(self, payment_id: int) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def get_by_id_and_user_id(
        self,
        payment_id: int,
        user_id: int,
    ) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(
                Payment.id == payment_id,
                Payment.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_provider_payment_id(
        self,
        provider: str,
        provider_payment_id: str,
        *,
        for_update: bool = False,
    ) -> Payment | None:
        query = select(Payment).where(
            Payment.provider == provider,
            Payment.provider_payment_id == provider_payment_id,
        )
        if for_update:
            query = query.with_for_update()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def update_status(
        self,
        payment: Payment,
        status: PaymentStatus,
    ) -> Payment:
        payment.status = status
        if status is not PaymentStatus.PAID:
            payment.paid_at = None
        await self.session.flush()
        return payment

    async def mark_paid(
        self,
        payment: Payment,
        paid_at: datetime | None = None,
    ) -> Payment:
        payment_time = paid_at or datetime.now(timezone.utc)
        if payment_time.tzinfo is None:
            raise ValueError("paid_at must be timezone-aware")

        payment.status = PaymentStatus.PAID
        payment.paid_at = payment_time
        await self.session.flush()
        return payment
