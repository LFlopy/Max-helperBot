from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Subscription
from database.repositories import (
    SubscriptionRepository,
    TariffRepository,
    UserRepository,
)


@dataclass(frozen=True, slots=True)
class UserAccess:
    has_active_subscription: bool
    history_limit: int
    tariff_code: str | None = None
    tariff_name: str | None = None


class SubscriptionService:
    def __init__(
        self,
        session: AsyncSession,
        free_history_limit: int,
    ) -> None:
        if free_history_limit < 1:
            raise ValueError("free_history_limit must be positive")

        self.session = session
        self.subscriptions = SubscriptionRepository(session)
        self.tariffs = TariffRepository(session)
        self.users = UserRepository(session)
        self.free_history_limit = free_history_limit

    async def grant_paid_subscription(
        self,
        user_id: int,
        tariff_id: int,
        now: datetime | None = None,
        *,
        commit: bool = True,
    ) -> Subscription:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        try:
            user = await self.users.get_by_id(user_id, for_update=True)
            if user is None:
                raise ValueError("User not found")

            tariff = await self.tariffs.get_by_id(tariff_id)
            if tariff is None:
                raise ValueError("Tariff not found")

            active = await self.subscriptions.get_active_by_user(
                user_id,
                now=current_time,
                for_update=True,
            )
            duration = timedelta(days=tariff.duration_days)
            if active is None:
                subscription = await self.subscriptions.create(
                    user_id=user_id,
                    tariff_id=tariff.id,
                    starts_at=current_time,
                    expires_at=current_time + duration,
                    commit=False,
                )
            else:
                subscription = await self.subscriptions.update_period(
                    active,
                    tariff_id=tariff.id,
                    expires_at=active.expires_at + duration,
                    commit=False,
                )

            if commit:
                await self.session.commit()
                await self.session.refresh(subscription)
        except Exception:
            if commit:
                await self.session.rollback()
            raise

        return subscription

    async def get_user_access(self, user_id: int) -> UserAccess:
        subscription = await self.subscriptions.get_active_by_user(user_id)
        if subscription is None:
            return UserAccess(
                has_active_subscription=False,
                history_limit=self.free_history_limit,
            )

        tariff = await self.tariffs.get_by_id(subscription.tariff_id)
        if tariff is None:
            raise RuntimeError("Subscription tariff does not exist")

        return UserAccess(
            has_active_subscription=True,
            history_limit=tariff.history_limit,
            tariff_code=tariff.code,
            tariff_name=tariff.name,
        )
