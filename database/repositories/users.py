from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_max_user_id(self, max_user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.max_user_id == max_user_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        max_user_id: int,
        first_name: str | None = None,
    ) -> User:
        user = User(
            max_user_id=max_user_id,
            first_name=first_name,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_or_create(
        self,
        max_user_id: int,
        first_name: str | None = None,
    ) -> User:
        user = await self.get_by_max_user_id(max_user_id)
        if user is not None:
            return user

        try:
            return await self.create(
                max_user_id=max_user_id,
                first_name=first_name,
            )
        except IntegrityError:
            await self.session.rollback()
            user = await self.get_by_max_user_id(max_user_id)
            if user is None:
                raise
            return user
