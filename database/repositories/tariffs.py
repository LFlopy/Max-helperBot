from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Tariff


class TariffRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, tariff_id: int) -> Tariff | None:
        return await self.session.get(Tariff, tariff_id)

    async def get_by_code(self, code: str) -> Tariff | None:
        result = await self.session.execute(
            select(Tariff).where(Tariff.code == code)
        )
        return result.scalar_one_or_none()

    async def list_active(self) -> list[Tariff]:
        result = await self.session.execute(
            select(Tariff)
            .where(Tariff.is_active.is_(True))
            .order_by(Tariff.price, Tariff.id)
        )
        return list(result.scalars())

    async def upsert(
        self,
        code: str,
        name: str,
        price: Decimal,
        duration_days: int,
        history_limit: int,
        is_active: bool = True,
    ) -> Tariff:
        tariff = await self.get_by_code(code)
        if tariff is None:
            tariff = Tariff(code=code)
            self.session.add(tariff)

        tariff.name = name
        tariff.price = price
        tariff.duration_days = duration_days
        tariff.history_limit = history_limit
        tariff.is_active = is_active

        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(tariff)
        return tariff
