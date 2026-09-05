from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from config import FREE_HISTORY_LIMIT
from services.subscriptions import AccessType, SubscriptionService


@dataclass(frozen=True, slots=True)
class UserProfile:
    first_name: str | None
    access_type: AccessType
    tariff_name: str | None
    expires_at: datetime | None
    can_activate_trial: bool


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
