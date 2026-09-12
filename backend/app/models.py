from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Retailer(Base):
    __tablename__ = "retailers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500))
    website_url: Mapped[str] = mapped_column(String(500), nullable=False)
    platform: Mapped[str | None] = mapped_column(String(120))
    scraping_method: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="planned", nullable=False)
    last_successful_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    cities: Mapped[list["RetailerCity"]] = relationship(back_populates="retailer", cascade="all, delete-orphan")
    products: Mapped[list["RetailerProduct"]] = relationship(back_populates="retailer")


class RetailerCity(Base):
    __tablename__ = "retailer_cities"

    retailer_id: Mapped[str] = mapped_column(ForeignKey("retailers.id"), primary_key=True)
    city: Mapped[str] = mapped_column(String(80), primary_key=True)
    retailer: Mapped[Retailer] = relationship(back_populates="cities")


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    brand: Mapped[str | None] = mapped_column(String(160))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"))
    description: Mapped[str | None] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500))
    search_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    category: Mapped[Category | None] = relationship()
    variants: Mapped[list["ProductVariant"]] = relationship(back_populates="product")


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "pack_count", "size_value", "size_unit", name="uq_variant_size"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    variant_name: Mapped[str] = mapped_column(String(300), nullable=False)
    pack_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    size_value: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    size_unit: Mapped[str] = mapped_column(String(16), nullable=False)
    size_label: Mapped[str] = mapped_column(String(80), nullable=False)
    barcode: Mapped[str | None] = mapped_column(String(32), unique=True)
    search_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    product: Mapped[Product] = relationship(back_populates="variants")
    retailer_products: Mapped[list["RetailerProduct"]] = relationship(back_populates="variant")


class RetailerProduct(Base):
    __tablename__ = "retailer_products"
    __table_args__ = (
        UniqueConstraint("retailer_id", "retailer_sku", "city", name="uq_retailer_sku_city"),
        UniqueConstraint("retailer_id", "retailer_product_url", name="uq_retailer_url"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    retailer_id: Mapped[str] = mapped_column(ForeignKey("retailers.id"), nullable=False)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"))
    retailer_product_name: Mapped[str] = mapped_column(String(400), nullable=False)
    retailer_product_url: Mapped[str] = mapped_column(String(700), nullable=False)
    retailer_sku: Mapped[str | None] = mapped_column(String(80))
    barcode: Mapped[str | None] = mapped_column(String(32))
    image_url: Mapped[str | None] = mapped_column(String(500))
    availability: Mapped[str] = mapped_column(String(32), default="unknown", nullable=False)
    match_confidence: Mapped[float | None] = mapped_column(Numeric(5, 2))
    match_decision: Mapped[str] = mapped_column(String(32), default="unmatched", nullable=False)
    city: Mapped[str] = mapped_column(String(80), default="Karachi", nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    current_compare_at: Mapped[float | None] = mapped_column(Numeric(12, 2))
    normalized_name: Mapped[str] = mapped_column(String(300), default="", nullable=False)

    retailer: Mapped[Retailer] = relationship(back_populates="products")
    product: Mapped[Product | None] = relationship()
    variant: Mapped[ProductVariant | None] = relationship(back_populates="retailer_products")
    prices: Mapped[list["Price"]] = relationship(back_populates="retailer_product")


class Price(Base):
    __tablename__ = "prices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    retailer_product_id: Mapped[int] = mapped_column(ForeignKey("retailer_products.id"), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    compare_at_price: Mapped[float | None] = mapped_column(Numeric(12, 2))
    discount: Mapped[float | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="PKR", nullable=False)
    availability: Mapped[str] = mapped_column(String(32), nullable=False)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    suspicious: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    suspicion_reason: Mapped[str | None] = mapped_column(String(300))

    retailer_product: Mapped[RetailerProduct] = relationship(back_populates="prices")


class MatchReview(Base):
    __tablename__ = "match_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    retailer_product_id: Mapped[int] = mapped_column(ForeignKey("retailer_products.id"), nullable=False)
    candidate_variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id"))
    confidence: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="review", nullable=False)
    reviewer_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CollectionJob(Base):
    __tablename__ = "collection_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    retailer_id: Mapped[str] = mapped_column(ForeignKey("retailers.id"), nullable=False)
    job_type: Mapped[str] = mapped_column(String(40), nullable=False)
    tier: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
    items_upserted: Mapped[int] = mapped_column(Integer, default=0)
