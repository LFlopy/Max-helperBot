from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(
        self,
        user_id: int,
        *,
        for_update: bool = False,
    ) -> User | None:
        return await self.session.get(
            User,
            user_id,
            with_for_update=for_update,
        )

    async def get_by_max_user_id(self, max_user_id: int) -> User | None:
        result = await self.session.execute(
            select(User).where(User.max_user_id == max_user_id)
        )
        return result.scalar_one_or_none()

    async def count(self) -> int:
        result = await self.session.execute(select(func.count(User.id)))
        return result.scalar_one()

    async def list_page(
        self,
        offset: int,
        limit: int,
    ) -> list[User]:
        if offset < 0:
            raise ValueError("offset must not be negative")
        if limit < 1:
            raise ValueError("limit must be positive")

        result = await self.session.execute(
            select(User)
            .order_by(User.created_at.desc(), User.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars())

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

    async def mark_trial_used(
        self,
        user: User,
        used_at: datetime,
    ) -> User:
        if used_at.tzinfo is None:
            raise ValueError("used_at must be timezone-aware")
        user.trial_used_at = used_at
        await self.session.flush()
        return user
