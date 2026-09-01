import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from time import time_ns
from unittest.mock import patch

from sqlalchemy import delete

from database.models import Payment, PaymentStatus, Subscription, Tariff, User
from database.repositories import (
    PaymentRepository,
    SubscriptionRepository,
    TariffRepository,
    UserRepository,
)
from database.session import engine, session_factory
from services import AccessType, PaymentService, SubscriptionService
from services.payments import (
    FakePaymentProvider,
    PaymentConfirmation,
    TariffUnavailableError,
)


async def cleanup(max_user_ids: tuple[int, ...], tariff_codes: tuple[str, ...]) -> None:
    async with session_factory() as session:
        user_ids = list(
            (
                await session.execute(
                    User.__table__.select()
                    .with_only_columns(User.id)
                    .where(User.max_user_id.in_(max_user_ids))
                )
            ).scalars()
        )
        tariff_ids = list(
            (
                await session.execute(
                    Tariff.__table__.select()
                    .with_only_columns(Tariff.id)
                    .where(Tariff.code.in_(tariff_codes))
                )
            ).scalars()
        )
        if user_ids:
            await session.execute(delete(Payment).where(Payment.user_id.in_(user_ids)))
            await session.execute(
                delete(Subscription).where(Subscription.user_id.in_(user_ids))
            )
            await session.execute(delete(User).where(User.id.in_(user_ids)))
        if tariff_ids:
            await session.execute(delete(Tariff).where(Tariff.id.in_(tariff_ids)))
        await session.commit()


async def main() -> None:
    marker = time_ns()
    max_user_ids = tuple(-marker - offset for offset in range(3))
    tariff_codes = (f"payment-{marker}", f"inactive-{marker}")
    now = datetime.now(timezone.utc)
    provider = FakePaymentProvider()

    try:
        async with session_factory() as session:
            users = UserRepository(session)
            tariffs = TariffRepository(session)
            active_tariff = await tariffs.upsert(
                code=tariff_codes[0],
                name="Payment check",
                price=Decimal("1234.56"),
                duration_days=30,
                history_limit=41,
            )
            await tariffs.upsert(
                code=tariff_codes[1],
                name="Inactive check",
                price=Decimal("1.00"),
                duration_days=1,
                history_limit=1,
                is_active=False,
            )
            users_by_max_id = {
                max_user_id: await users.get_or_create(max_user_id)
                for max_user_id in max_user_ids
            }

            service = PaymentService(session, provider)
            checkout = await service.create_payment(
                max_user_id=max_user_ids[0],
                tariff_code=active_tariff.code,
            )
            payment = await PaymentRepository(session).get_by_id(checkout.payment_id)
            assert payment is not None
            assert payment.amount == Decimal("1234.56")
            assert payment.currency == "RUB"
            assert payment.status is PaymentStatus.PENDING
            assert payment.provider_payment_id == checkout.provider_payment_id
            assert checkout.checkout_url.endswith(checkout.provider_payment_id)
            assert provider.requests[-1].amount == active_tariff.price

            try:
                await service.create_payment(
                    max_user_id=max_user_ids[0],
                    tariff_code=tariff_codes[1],
                )
            except TariffUnavailableError:
                pass
            else:
                raise AssertionError("Inactive tariff was accepted")

            confirmation = PaymentConfirmation(
                provider_payment_id=checkout.provider_payment_id,
                status=PaymentStatus.PAID,
                paid_at=now,
            )
            await service.process_successful_confirmation(confirmation)
            subscription = await SubscriptionRepository(session).get_active_by_user(
                users_by_max_id[max_user_ids[0]].id,
                now=now,
            )
            assert subscription is not None
            first_expiry = subscription.expires_at
            assert payment.status is PaymentStatus.PAID
            assert payment.paid_at == now
            access = await SubscriptionService(
                session,
                free_history_limit=3,
            ).get_user_access(users_by_max_id[max_user_ids[0]].id, now=now)
            assert access.access_type is AccessType.PAID

            await service.process_successful_confirmation(confirmation)
            await session.refresh(subscription)
            assert subscription.expires_at == first_expiry

            renewal = await service.create_payment(
                max_user_id=max_user_ids[0],
                tariff_code=active_tariff.code,
            )
            await service.process_successful_confirmation(
                PaymentConfirmation(
                    provider_payment_id=renewal.provider_payment_id,
                    status=PaymentStatus.PAID,
                    paid_at=now + timedelta(seconds=1),
                )
            )
            await session.refresh(subscription)
            assert subscription.expires_at == first_expiry + timedelta(days=30)

            expired_user = users_by_max_id[max_user_ids[1]]
            await SubscriptionRepository(session).create(
                user_id=expired_user.id,
                tariff_id=active_tariff.id,
                starts_at=now - timedelta(days=2),
                expires_at=now - timedelta(days=1),
            )
            expired_checkout = await service.create_payment(
                max_user_id=max_user_ids[1],
                tariff_code=active_tariff.code,
            )
            expired_paid_at = now + timedelta(seconds=2)
            await service.process_successful_confirmation(
                PaymentConfirmation(
                    provider_payment_id=expired_checkout.provider_payment_id,
                    status=PaymentStatus.PAID,
                    paid_at=expired_paid_at,
                )
            )
            new_subscription = await SubscriptionRepository(
                session
            ).get_active_by_user(expired_user.id, now=expired_paid_at)
            assert new_subscription is not None
            assert new_subscription.starts_at == expired_paid_at

            rollback_checkout = await service.create_payment(
                max_user_id=max_user_ids[2],
                tariff_code=active_tariff.code,
            )
            original_grant = SubscriptionService.grant_paid_subscription

            async def fail_after_activation(
                subscription_service: SubscriptionService,
                user_id: int,
                tariff_id: int,
                now: datetime | None = None,
                *,
                commit: bool = True,
            ) -> Subscription:
                await original_grant(
                    subscription_service,
                    user_id,
                    tariff_id,
                    now,
                    commit=False,
                )
                raise RuntimeError("Synthetic activation failure")

            with patch.object(
                SubscriptionService,
                "grant_paid_subscription",
                fail_after_activation,
            ):
                try:
                    await service.process_successful_confirmation(
                        PaymentConfirmation(
                            provider_payment_id=rollback_checkout.provider_payment_id,
                            status=PaymentStatus.PAID,
                            paid_at=now + timedelta(seconds=3),
                        )
                    )
                except RuntimeError as error:
                    assert str(error) == "Synthetic activation failure"
                else:
                    raise AssertionError("Synthetic failure was not raised")

        async with session_factory() as verification_session:
            rollback_payment = await PaymentRepository(
                verification_session
            ).get_by_provider_payment_id(
                provider.name,
                rollback_checkout.provider_payment_id,
            )
            assert rollback_payment is not None
            assert rollback_payment.status is PaymentStatus.PENDING
            rollback_subscription = await SubscriptionRepository(
                verification_session
            ).get_active_by_user(
                users_by_max_id[max_user_ids[2]].id,
                now=now + timedelta(seconds=3),
            )
            assert rollback_subscription is None
    finally:
        await cleanup(max_user_ids, tariff_codes)
        await engine.dispose()

    print("Payment flow check passed")


if __name__ == "__main__":
    asyncio.run(main())
