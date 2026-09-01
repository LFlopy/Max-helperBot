from dataclasses import dataclass
from datetime import datetime, timezone
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from config import TRIAL_DURATION_DAYS
from database.repositories import AdminRepository, TariffRepository, UserRepository
from services.admin.users import AdminTariff


@dataclass(frozen=True, slots=True)
class AdminSubscriptionOverview:
    paid_count: int
    trial_count: int
    free_count: int


@dataclass(frozen=True, slots=True)
class ActiveSubscriptionSummary:
    user_id: int
    max_user_id: int
    first_name: str | None
    tariff_name: str
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ActiveSubscriptionPage:
    items: tuple[ActiveSubscriptionSummary, ...]
    page: int
    page_count: int
    total: int


class AdminSubscriptionService:
    def __init__(
        self,
        session: AsyncSession,
        trial_duration_days: int = TRIAL_DURATION_DAYS,
    ) -> None:
        if trial_duration_days < 1:
            raise ValueError("trial_duration_days must be positive")
        self.admin = AdminRepository(session)
        self.users = UserRepository(session)
        self.tariffs = TariffRepository(session)
        self.trial_duration_days = trial_duration_days

    async def get_overview(
        self,
        now: datetime | None = None,
    ) -> AdminSubscriptionOverview:
        current_time = self._current_time(now)
        total_users = await self.users.count()
        paid_count = await self.admin.count_active_paid_users(current_time)
        trial_count = await self.admin.count_active_trial_users(
            current_time,
            self.trial_duration_days,
        )
        return AdminSubscriptionOverview(
            paid_count=paid_count,
            trial_count=trial_count,
            free_count=max(0, total_users - paid_count - trial_count),
        )

    async def list_active_subscriptions(
        self,
        page: int = 1,
        page_size: int = 5,
        now: datetime | None = None,
    ) -> ActiveSubscriptionPage:
        if page < 1:
            raise ValueError("page must be positive")
        if page_size < 1:
            raise ValueError("page_size must be positive")
        current_time = self._current_time(now)
        total = await self.admin.count_active_paid_users(current_time)
        page_count = max(1, ceil(total / page_size))
        current_page = min(page, page_count)
        rows = await self.admin.list_active_paid_page(
            current_time,
            offset=(current_page - 1) * page_size,
            limit=page_size,
        )
        return ActiveSubscriptionPage(
            items=tuple(
                ActiveSubscriptionSummary(
                    user_id=user.id,
                    max_user_id=user.max_user_id,
                    first_name=user.first_name,
                    tariff_name=tariff.name,
                    expires_at=subscription.expires_at,
                )
                for user, subscription, tariff in rows
            ),
            page=current_page,
            page_count=page_count,
            total=total,
        )

    async def list_active_tariffs(self) -> tuple[AdminTariff, ...]:
        tariffs = await self.tariffs.list_active()
        return tuple(
            AdminTariff(
                id=tariff.id,
                code=tariff.code,
                name=tariff.name,
                price=tariff.price,
                duration_days=tariff.duration_days,
                history_limit=tariff.history_limit,
            )
            for tariff in tariffs
        )

    @staticmethod
    def _current_time(value: datetime | None) -> datetime:
        current_time = value or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        return current_time
