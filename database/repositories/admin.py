from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Subscription, Tariff, User


class AdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _active_subscription_ids(datetime_at: datetime):
        return (
            select(
                Subscription.id.label("subscription_id"),
                func.row_number()
                .over(
                    partition_by=Subscription.user_id,
                    order_by=(
                        Subscription.expires_at.desc(),
                        Subscription.id.desc(),
                    ),
                )
                .label("position"),
            )
            .where(
                Subscription.starts_at <= datetime_at,
                Subscription.expires_at > datetime_at,
            )
            .subquery()
        )

    async def count_active_paid_users(self, datetime_at: datetime) -> int:
        result = await self.session.execute(
            select(func.count(func.distinct(Subscription.user_id))).where(
                Subscription.starts_at <= datetime_at,
                Subscription.expires_at > datetime_at,
            )
        )
        return result.scalar_one()

    async def count_active_trial_users(
        self,
        datetime_at: datetime,
        trial_duration_days: int,
    ) -> int:
        active_paid = select(Subscription.id).where(
            Subscription.user_id == User.id,
            Subscription.starts_at <= datetime_at,
            Subscription.expires_at > datetime_at,
        )
        trial_cutoff = datetime_at - timedelta(days=trial_duration_days)
        result = await self.session.execute(
            select(func.count(User.id)).where(
                User.trial_used_at.is_not(None),
                User.trial_used_at <= datetime_at,
                User.trial_used_at > trial_cutoff,
                ~active_paid.exists(),
            )
        )
        return result.scalar_one()

    async def list_active_paid_page(
        self,
        datetime_at: datetime,
        offset: int,
        limit: int,
    ) -> list[tuple[User, Subscription, Tariff]]:
        active_ids = self._active_subscription_ids(datetime_at)
        result = await self.session.execute(
            select(User, Subscription, Tariff)
            .join(Subscription, Subscription.user_id == User.id)
            .join(Tariff, Tariff.id == Subscription.tariff_id)
            .join(
                active_ids,
                active_ids.c.subscription_id == Subscription.id,
            )
            .where(active_ids.c.position == 1)
            .order_by(Subscription.expires_at, User.id)
            .offset(offset)
            .limit(limit)
        )
        return [
            (row[0], row[1], row[2])
            for row in result.all()
        ]
