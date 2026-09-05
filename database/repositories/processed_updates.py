from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ProcessedUpdate


class ProcessedUpdateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def register(
        self,
        update_key: str,
        update_type: str,
    ) -> bool:
        result = await self.session.execute(
            insert(ProcessedUpdate)
            .values(
                update_key=update_key,
                update_type=update_type,
            )
            .on_conflict_do_nothing(
                index_elements=[ProcessedUpdate.update_key],
            )
            .returning(ProcessedUpdate.id)
        )
        registered = result.scalar_one_or_none() is not None
        await self.session.commit()
        return registered
