from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories import SubscriptionRepository, TariffRepository


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

        self.subscriptions = SubscriptionRepository(session)
        self.tariffs = TariffRepository(session)
        self.free_history_limit = free_history_limit

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
