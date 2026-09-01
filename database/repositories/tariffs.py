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
