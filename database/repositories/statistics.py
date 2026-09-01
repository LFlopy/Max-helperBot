from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Message, Payment, PaymentStatus, User


class StatisticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def count_users(self) -> int:
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar_one()

    async def count_users_created_since(self, datetime_from: datetime) -> int:
        result = await self.session.execute(
            select(func.count(User.id)).where(User.created_at >= datetime_from)
        )
        return result.scalar_one()

    async def get_paid_payment_totals(self) -> tuple[int, Decimal]:
        result = await self.session.execute(
            select(
                func.count(Payment.id),
                func.coalesce(func.sum(Payment.amount), Decimal("0.00")),
            ).where(Payment.status == PaymentStatus.PAID)
        )
        row = result.one()
        return row[0], row[1]

    async def count_messages(self) -> int:
        result = await self.session.execute(select(func.count(Message.id)))
        return result.scalar_one()

    async def count_messages_created_since(
        self,
        datetime_from: datetime,
    ) -> int:
        result = await self.session.execute(
            select(func.count(Message.id)).where(
                Message.created_at >= datetime_from
            )
        )
        return result.scalar_one()
