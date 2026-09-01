from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from sqlalchemy.ext.asyncio import AsyncSession

from config import TRIAL_DURATION_DAYS, TRIAL_HISTORY_LIMIT
from database.models import Subscription
from database.repositories import (
    SubscriptionRepository,
    TariffRepository,
    UserRepository,
)


class AccessType(StrEnum):
    FREE = "free"
    TRIAL = "trial"
    PAID = "paid"


@dataclass(frozen=True, slots=True)
class UserAccess:
    has_active_subscription: bool
    history_limit: int
    access_type: AccessType = AccessType.FREE
    tariff_code: str | None = None
    tariff_name: str | None = None
    expires_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class TrialAccess:
    starts_at: datetime
    expires_at: datetime


class TrialAlreadyUsedError(Exception):
    pass


class SubscriptionService:
    def __init__(
        self,
        session: AsyncSession,
        free_history_limit: int,
        trial_duration_days: int = TRIAL_DURATION_DAYS,
        trial_history_limit: int = TRIAL_HISTORY_LIMIT,
    ) -> None:
        if free_history_limit < 1:
            raise ValueError("free_history_limit must be positive")
        if trial_duration_days < 1:
            raise ValueError("trial_duration_days must be positive")
        if trial_history_limit < 1:
            raise ValueError("trial_history_limit must be positive")

        self.session = session
        self.subscriptions = SubscriptionRepository(session)
        self.tariffs = TariffRepository(session)
        self.users = UserRepository(session)
        self.free_history_limit = free_history_limit
        self.trial_duration_days = trial_duration_days
        self.trial_history_limit = trial_history_limit

    async def activate_trial(
        self,
        user_id: int,
        now: datetime | None = None,
    ) -> TrialAccess:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        try:
            user = await self.users.get_by_id(user_id, for_update=True)
            if user is None:
                raise ValueError("User not found")
            if user.trial_used_at is not None:
                raise TrialAlreadyUsedError("Trial has already been used")

            await self.users.mark_trial_used(user, current_time)
            await self.session.commit()
            await self.session.refresh(user)
        except Exception:
            await self.session.rollback()
            raise

        return TrialAccess(
            starts_at=current_time,
            expires_at=current_time
            + timedelta(days=self.trial_duration_days),
        )

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

    async def cancel_paid_subscription(
        self,
        user_id: int,
        now: datetime | None = None,
    ) -> bool:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        try:
            user = await self.users.get_by_id(user_id, for_update=True)
            if user is None:
                raise ValueError("User not found")
            active = await self.subscriptions.get_active_by_user(
                user_id,
                now=current_time,
                for_update=True,
            )
            if active is None:
                await self.session.commit()
                return False

            await self.subscriptions.update_period(
                active,
                tariff_id=active.tariff_id,
                expires_at=current_time,
                commit=False,
            )
            await self.session.commit()
            return True
        except Exception:
            await self.session.rollback()
            raise

    async def get_user_access(
        self,
        user_id: int,
        now: datetime | None = None,
    ) -> UserAccess:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        subscription = await self.subscriptions.get_active_by_user(
            user_id,
            now=current_time,
        )
        if subscription is None:
            user = await self.users.get_by_id(user_id)
            if user is None:
                raise ValueError("User not found")
            if (
                user.trial_used_at is not None
                and user.trial_used_at <= current_time
                and user.trial_used_at
                + timedelta(days=self.trial_duration_days)
                > current_time
            ):
                return UserAccess(
                    has_active_subscription=False,
                    history_limit=self.trial_history_limit,
                    access_type=AccessType.TRIAL,
                    expires_at=user.trial_used_at
                    + timedelta(days=self.trial_duration_days),
                )
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
            access_type=AccessType.PAID,
            tariff_code=tariff.code,
            tariff_name=tariff.name,
            expires_at=subscription.expires_at,
        )
