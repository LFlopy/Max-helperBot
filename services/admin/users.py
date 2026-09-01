from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from math import ceil

from sqlalchemy.ext.asyncio import AsyncSession

from config import FREE_HISTORY_LIMIT
from database.repositories import TariffRepository, UserRepository
from services.subscriptions import AccessType, SubscriptionService


@dataclass(frozen=True, slots=True)
class AdminUserSummary:
    id: int
    max_user_id: int
    first_name: str | None
    access_type: AccessType
    tariff_name: str | None
    access_expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class AdminUserCard(AdminUserSummary):
    created_at: datetime
    trial_used_at: datetime | None


@dataclass(frozen=True, slots=True)
class AdminUserPage:
    items: tuple[AdminUserSummary, ...]
    page: int
    page_count: int
    total: int


@dataclass(frozen=True, slots=True)
class AdminTariff:
    id: int
    code: str
    name: str
    price: Decimal
    duration_days: int
    history_limit: int


class AdminTariffUnavailableError(Exception):
    pass


class AdminUserService:
    def __init__(
        self,
        session: AsyncSession,
        free_history_limit: int = FREE_HISTORY_LIMIT,
    ) -> None:
        self.users = UserRepository(session)
        self.tariffs = TariffRepository(session)
        self.subscriptions = SubscriptionService(
            session,
            free_history_limit=free_history_limit,
        )

    async def list_users(
        self,
        page: int = 1,
        page_size: int = 5,
    ) -> AdminUserPage:
        if page < 1:
            raise ValueError("page must be positive")
        if page_size < 1:
            raise ValueError("page_size must be positive")

        total = await self.users.count()
        page_count = max(1, ceil(total / page_size))
        current_page = min(page, page_count)
        users = await self.users.list_page(
            offset=(current_page - 1) * page_size,
            limit=page_size,
        )
        items = tuple([await self._to_summary(user.id) for user in users])
        return AdminUserPage(
            items=items,
            page=current_page,
            page_count=page_count,
            total=total,
        )

    async def get_user_card(self, user_id: int) -> AdminUserCard | None:
        user = await self.users.get_by_id(user_id)
        if user is None:
            return None
        summary = await self._to_summary(user.id)
        return AdminUserCard(
            id=summary.id,
            max_user_id=summary.max_user_id,
            first_name=summary.first_name,
            access_type=summary.access_type,
            tariff_name=summary.tariff_name,
            access_expires_at=summary.access_expires_at,
            created_at=user.created_at,
            trial_used_at=user.trial_used_at,
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

    async def grant_subscription(
        self,
        user_id: int,
        tariff_id: int,
    ) -> None:
        tariff = await self.tariffs.get_by_id(tariff_id)
        if tariff is None or not tariff.is_active:
            raise AdminTariffUnavailableError("Tariff is not available")
        await self.subscriptions.grant_paid_subscription(
            user_id=user_id,
            tariff_id=tariff.id,
        )

    async def cancel_subscription(self, user_id: int) -> bool:
        return await self.subscriptions.cancel_paid_subscription(user_id)

    async def _to_summary(self, user_id: int) -> AdminUserSummary:
        user = await self.users.get_by_id(user_id)
        if user is None:
            raise RuntimeError("User disappeared while building admin view")
        access = await self.subscriptions.get_user_access(user.id)
        return AdminUserSummary(
            id=user.id,
            max_user_id=user.max_user_id,
            first_name=user.first_name,
            access_type=access.access_type,
            tariff_name=access.tariff_name,
            access_expires_at=access.expires_at,
        )
