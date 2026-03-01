from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database.models import User, Payment
from datetime import datetime

async def get_user(session: AsyncSession, user_id: int) -> User | None:
    """Получить пользователя по ID."""
    result = await session.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def create_user(session: AsyncSession, user_id: int, username: str | None, full_name: str, referrer_id: int | None = None) -> User:
    """Создать нового пользователя."""
    user = User(id=user_id, username=username, full_name=full_name, referrer_id=referrer_id)
    session.add(user)
    await session.commit()
    return user

async def update_subscription(session: AsyncSession, user_id: int, end_date: datetime, marzban_username: str, sub_url: str):
    """Обновить данные подписки пользователя."""
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(sub_end_date=end_date, marzban_username=marzban_username, sub_url=sub_url)
    )
    await session.commit()

async def get_active_users(session: AsyncSession) -> list[User]:
    """Получить всех пользователей с активной подпиской."""
    result = await session.execute(select(User).where(User.sub_end_date > datetime.utcnow()))
    return list(result.scalars().all())

async def create_payment(session: AsyncSession, user_id: int, amount: int, method: str) -> Payment:
    """Создать запись о платеже."""
    payment = Payment(user_id=user_id, amount=amount, payment_method=method)
    session.add(payment)
    await session.commit()
    return payment
