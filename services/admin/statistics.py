from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from config import TRIAL_DURATION_DAYS
from database.repositories import AdminRepository, StatisticsRepository


@dataclass(frozen=True, slots=True)
class AdminStatistics:
    users_count: int
    new_users_24h: int
    new_users_7d: int
    active_paid_count: int
    active_trial_count: int
    paid_payments_count: int
    revenue: Decimal
    messages_count: int
    messages_24h: int


class AdminStatisticsService:
    def __init__(
        self,
        session: AsyncSession,
        trial_duration_days: int = TRIAL_DURATION_DAYS,
    ) -> None:
        self.statistics = StatisticsRepository(session)
        self.admin = AdminRepository(session)
        self.trial_duration_days = trial_duration_days

    async def get_statistics(
        self,
        now: datetime | None = None,
    ) -> AdminStatistics:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        users_count = await self.statistics.count_users()
        new_users_24h = await self.statistics.count_users_created_since(
            current_time - timedelta(days=1)
        )
        new_users_7d = await self.statistics.count_users_created_since(
            current_time - timedelta(days=7)
        )
        active_paid_count = await self.admin.count_active_paid_users(
            current_time
        )
        active_trial_count = await self.admin.count_active_trial_users(
            current_time,
            self.trial_duration_days,
        )
        paid_payments_count, revenue = (
            await self.statistics.get_paid_payment_totals()
        )
        messages_count = await self.statistics.count_messages()
        messages_24h = await self.statistics.count_messages_created_since(
            current_time - timedelta(days=1)
        )
        return AdminStatistics(
            users_count=users_count,
            new_users_24h=new_users_24h,
            new_users_7d=new_users_7d,
            active_paid_count=active_paid_count,
            active_trial_count=active_trial_count,
            paid_payments_count=paid_payments_count,
            revenue=revenue,
            messages_count=messages_count,
            messages_24h=messages_24h,
        )
