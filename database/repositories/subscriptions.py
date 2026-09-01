from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Subscription


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_by_user(
        self,
        user_id: int,
        now: datetime | None = None,
        *,
        for_update: bool = False,
    ) -> Subscription | None:
        current_time = now or datetime.now(timezone.utc)
        if current_time.tzinfo is None:
            raise ValueError("now must be timezone-aware")

        query = (
            select(Subscription)
            .where(
                Subscription.user_id == user_id,
                Subscription.starts_at <= current_time,
                Subscription.expires_at > current_time,
            )
            .order_by(Subscription.expires_at.desc(), Subscription.id.desc())
            .limit(1)
        )
        if for_update:
            query = query.with_for_update()
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_latest_by_user(
        self,
        user_id: int,
    ) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .order_by(Subscription.created_at.desc(), Subscription.id.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        user_id: int,
        tariff_id: int,
        starts_at: datetime,
        expires_at: datetime,
        *,
        commit: bool = True,
    ) -> Subscription:
        subscription = Subscription(
            user_id=user_id,
            tariff_id=tariff_id,
            starts_at=starts_at,
            expires_at=expires_at,
        )
        self.session.add(subscription)
        await self.session.flush()
        if commit:
            await self.session.commit()
            await self.session.refresh(subscription)
        return subscription

    async def update_period(
        self,
        subscription: Subscription,
        tariff_id: int,
        expires_at: datetime,
        *,
        commit: bool = True,
    ) -> Subscription:
        subscription.tariff_id = tariff_id
        subscription.expires_at = expires_at
        await self.session.flush()
        if commit:
            await self.session.commit()
            await self.session.refresh(subscription)
        return subscription
