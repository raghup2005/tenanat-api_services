from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class APIUsage(Base):
    __tablename__ = "api_usage"

    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "usage_date",
            name="uq_api_usage_tenant_date",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
    )

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    usage_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    request_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )