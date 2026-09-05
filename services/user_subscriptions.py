from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from config import FREE_HISTORY_LIMIT
from services.subscriptions import (
    AccessType,
    SubscriptionService,
    TrialAccess,
)


@dataclass(frozen=True, slots=True)
class UserProfile:
    first_name: str | None
    access_type: AccessType
    tariff_name: str | None
    expires_at: datetime | None
    can_activate_trial: bool


@dataclass(frozen=True, slots=True)
class UserTariff:
    id: int
    name: str
    price: Decimal
    duration_days: int


class UserSubscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.subscriptions = SubscriptionService(
            session,
            free_history_limit=FREE_HISTORY_LIMIT,
        )

    async def get_profile(self, max_user_id: int) -> UserProfile | None:
        user = await self.subscriptions.users.get_by_max_user_id(max_user_id)
        if user is None:
            return None
        access = await self.subscriptions.get_user_access(user.id)
        return UserProfile(
            first_name=user.first_name,
            access_type=access.access_type,
            tariff_name=access.tariff_name,
            expires_at=access.expires_at,
            can_activate_trial=(
                access.access_type is AccessType.FREE
                and user.trial_used_at is None
            ),
        )

    async def activate_trial(self, max_user_id: int) -> TrialAccess:
        user = await self.subscriptions.users.get_by_max_user_id(max_user_id)
        if user is None:
            raise ValueError("User not found")
        return await self.subscriptions.activate_trial(user.id)

    async def list_tariffs(self) -> tuple[UserTariff, ...]:
        tariffs = await self.subscriptions.tariffs.list_active()
        return tuple(
            UserTariff(
                id=tariff.id,
                name=tariff.name,
                price=tariff.price,
                duration_days=tariff.duration_days,
            )
            for tariff in tariffs
        )

    async def get_tariff(self, tariff_id: int) -> UserTariff | None:
        tariff = await self.subscriptions.tariffs.get_by_id(tariff_id)
        if tariff is None or not tariff.is_active:
            return None
        return UserTariff(
            id=tariff.id,
            name=tariff.name,
            price=tariff.price,
            duration_days=tariff.duration_days,
        )
