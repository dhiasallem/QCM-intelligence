from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, func, Table, Column
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

group_members = Table(
    "group_members",
    Base.metadata,
    Column("group_id", ForeignKey("student_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("student_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))  # admin | teacher | student
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Group(Base):
    __tablename__ = "student_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    students: Mapped[list[User]] = relationship(secondary=group_members)