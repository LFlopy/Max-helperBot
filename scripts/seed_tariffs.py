import asyncio
from dataclasses import dataclass
from decimal import Decimal

from database.repositories import TariffRepository
from database.session import engine, session_factory


@dataclass(frozen=True, slots=True)
class TariffSeed:
    code: str
    name: str
    price: Decimal
    duration_days: int
    history_limit: int


TARIFFS = (
    TariffSeed(
        code="standard",
        name="Стандарт",
        price=Decimal("990.00"),
        duration_days=30,
        history_limit=50,
    ),
)


async def main() -> None:
    try:
        async with session_factory() as session:
            repository = TariffRepository(session)
            for tariff in TARIFFS:
                await repository.upsert(
                    code=tariff.code,
                    name=tariff.name,
                    price=tariff.price,
                    duration_days=tariff.duration_days,
                    history_limit=tariff.history_limit,
                )
    finally:
        await engine.dispose()

    print(f"Seeded {len(TARIFFS)} tariff(s)")


if __name__ == "__main__":
    asyncio.run(main())
