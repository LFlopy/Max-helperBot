import argparse
import asyncio

from database.models import User
from database.repositories import TariffRepository, UserRepository
from database.session import engine, session_factory
from services import SubscriptionService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    user_group = parser.add_mutually_exclusive_group(required=True)
    user_group.add_argument("--max-user-id", type=int)
    user_group.add_argument("--user-id", type=int)
    parser.add_argument("--tariff-code", required=True)
    return parser.parse_args()


async def resolve_user(
    repository: UserRepository,
    args: argparse.Namespace,
) -> User | None:
    if args.max_user_id is not None:
        return await repository.get_by_max_user_id(args.max_user_id)
    return await repository.get_by_id(args.user_id)


async def grant(args: argparse.Namespace) -> None:
    try:
        async with session_factory() as session:
            users = UserRepository(session)
            tariffs = TariffRepository(session)

            user = await resolve_user(users, args)
            if user is None:
                raise ValueError("User not found")

            tariff = await tariffs.get_by_code(args.tariff_code)
            if tariff is None:
                raise ValueError("Tariff not found")

            subscription = await SubscriptionService(
                session,
                free_history_limit=1,
            ).grant_paid_subscription(
                user_id=user.id,
                tariff_id=tariff.id,
            )
    finally:
        await engine.dispose()

    print(
        f"Granted subscription {subscription.id} to user {user.id} "
        f"until {subscription.expires_at.isoformat()}"
    )


if __name__ == "__main__":
    asyncio.run(grant(parse_args()))
