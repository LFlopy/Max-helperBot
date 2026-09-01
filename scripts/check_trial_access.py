import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from time import time_ns

from sqlalchemy import delete

from database.models import Subscription, Tariff, User
from database.repositories import (
    SubscriptionRepository,
    TariffRepository,
    UserRepository,
)
from database.session import engine, session_factory
from services import AccessType, SubscriptionService, TrialAlreadyUsedError


async def cleanup(max_user_id: int, tariff_code: str) -> None:
    async with session_factory() as session:
        user = await UserRepository(session).get_by_max_user_id(max_user_id)
        if user is not None:
            await session.execute(
                delete(Subscription).where(Subscription.user_id == user.id)
            )
            await session.delete(user)
        tariff = await TariffRepository(session).get_by_code(tariff_code)
        if tariff is not None:
            await session.delete(tariff)
        await session.commit()


async def main() -> None:
    marker = time_ns()
    max_user_id = -marker
    tariff_code = f"trial-{marker}"
    now = datetime.now(timezone.utc)

    try:
        async with session_factory() as session:
            user = await UserRepository(session).get_or_create(max_user_id)
            user_id = user.id
            service = SubscriptionService(
                session,
                free_history_limit=3,
                trial_duration_days=7,
                trial_history_limit=17,
            )

            trial = await service.activate_trial(user_id, now=now)
            assert trial.starts_at == now
            assert trial.expires_at == now + timedelta(days=7)
            access = await service.get_user_access(user_id, now=now)
            assert access.access_type is AccessType.TRIAL
            assert access.history_limit == 17

            try:
                await service.activate_trial(
                    user_id,
                    now=now + timedelta(days=8),
                )
            except TrialAlreadyUsedError:
                pass
            else:
                raise AssertionError("Trial was activated twice")

            expired_access = await service.get_user_access(
                user_id,
                now=now + timedelta(days=8),
            )
            assert expired_access.access_type is AccessType.FREE
            assert expired_access.history_limit == 3

            tariff = await TariffRepository(session).upsert(
                code=tariff_code,
                name="Trial priority check",
                price=Decimal("10.00"),
                duration_days=30,
                history_limit=50,
            )
            await SubscriptionRepository(session).create(
                user_id=user_id,
                tariff_id=tariff.id,
                starts_at=now,
                expires_at=now + timedelta(days=30),
            )
            paid_access = await service.get_user_access(user_id, now=now)
            assert paid_access.access_type is AccessType.PAID
            assert paid_access.history_limit == 50
    finally:
        await cleanup(max_user_id, tariff_code)
        await engine.dispose()

    print("Trial access check passed")


if __name__ == "__main__":
    asyncio.run(main())
