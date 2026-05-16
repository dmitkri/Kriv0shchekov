from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Anketa(Base):
    __tablename__ = "anketas"

    account_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    age: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    about: Mapped[str] = mapped_column(Text, nullable=False)
    want_gender: Mapped[str] = mapped_column(String(20), nullable=False)
    want_age_min: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    want_age_max: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    want_city: Mapped[str] = mapped_column(String(100), nullable=False)
    visible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    photo_count: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="anketa",
        cascade="all, delete-orphan",
        order_by="Photo.position",
    )

    @property
    def photo_keys(self) -> list[str]:
        return [photo.file_key for photo in self.photos]

    @property
    def profile_completed(self) -> bool:
        required_fields = (
            self.display_name,
            self.age,
            self.gender,
            self.city,
            self.about,
            self.want_gender,
            self.want_age_min,
            self.want_age_max,
            self.want_city,
        )
        return all(field not in (None, "") for field in required_fields)


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    anketa_account_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("anketas.account_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_key: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    anketa: Mapped[Anketa] = relationship(back_populates="photos")
