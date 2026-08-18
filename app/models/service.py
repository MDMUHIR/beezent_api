from typing import List, Optional
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# Many-to-Many association table between Service and TechStack
service_tech_stack = Table(
    "service_tech_stack",
    Base.metadata,
    Column("service_id", Integer, ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
    Column("tech_stack_id", Integer, ForeignKey("tech_stacks.id", ondelete="CASCADE"), primary_key=True),
)


class ServiceCategory(Base, TimestampMixin):
    __tablename__ = "service_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    services: Mapped[List["Service"]] = relationship(
        "Service",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="Service.display_order"
    )

    def __repr__(self) -> str:
        return f"<ServiceCategory(id={self.id}, name='{self.name}')>"


class TechStack(Base, TimestampMixin):
    __tablename__ = "tech_stacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="General")  # e.g., AI/ML, Cloud, Backend, Frontend
    icon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    website_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    services: Mapped[List["Service"]] = relationship(
        "Service",
        secondary=service_tech_stack,
        back_populates="tech_stacks"
    )

    def __repr__(self) -> str:
        return f"<TechStack(id={self.id}, name='{self.name}', category='{self.category}')>"


class Service(Base, TimestampMixin):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("service_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False, index=True)
    short_description: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown or HTML body
    icon_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    category: Mapped["ServiceCategory"] = relationship("ServiceCategory", back_populates="services")
    tech_stacks: Mapped[List["TechStack"]] = relationship(
        "TechStack",
        secondary=service_tech_stack,
        back_populates="services"
    )

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, title='{self.title}', slug='{self.slug}')>"
