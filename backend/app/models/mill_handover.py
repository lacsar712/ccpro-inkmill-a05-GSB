from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

HANDOVER_SLOTS = ("morning", "afternoon", "night")


class MillHandover(Base):
    __tablename__ = "mill_handovers"
    __table_args__ = (
        UniqueConstraint("mill_id", "shift_date", "slot", name="uq_handover_mill_date_slot"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mill_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("mills.id", ondelete="CASCADE"), nullable=False
    )
    shift_date: Mapped[date] = mapped_column(Date, nullable=False)
    slot: Mapped[str] = mapped_column(String(16), nullable=False)
    from_operator: Mapped[str] = mapped_column(String(128), nullable=False)
    to_operator: Mapped[str] = mapped_column(String(128), nullable=False)
    mill_status_snapshot: Mapped[str] = mapped_column(String(16), nullable=False)
    note: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.current_timestamp()
    )

    mill: Mapped["Mill"] = relationship("Mill")
