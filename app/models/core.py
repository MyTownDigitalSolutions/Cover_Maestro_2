
from sqlalchemy import (
    Boolean, Column, ForeignKey, Integer, BigInteger, String, Float, DateTime, Enum,
    Table, UniqueConstraint, event, Index, JSON, Text
)
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import List
from app.database import Base
from app.models.enums import HandleLocation, AngleType, Carrier, Marketplace, MaterialType, UnitOfMeasure, OrderSource, NormalizedOrderStatus

class Manufacturer(Base):
    __tablename__ = "manufacturers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    
    series = relationship("Series", back_populates="manufacturer", cascade="all, delete-orphan")

class Series(Base):
    __tablename__ = "series"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    manufacturer_id = Column(Integer, ForeignKey("manufacturers.id"), nullable=False)
    
    manufacturer = relationship("Manufacturer", back_populates="series")
    models = relationship("Model", back_populates="series", cascade="all, delete-orphan")
    
    __table_args__ = (UniqueConstraint('manufacturer_id', 'name', name='uq_series_manufacturer_name'),)

class EquipmentType(Base):
    __tablename__ = "equipment_types"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    
    models = relationship("Model", back_populates="equipment_type")
    
    amazon_customization_template_id = Column(Integer, ForeignKey("amazon_customization_templates.id"), nullable=True)
    amazon_customization_template = relationship("AmazonCustomizationTemplate")

    reverb_template_id = Column(Integer, ForeignKey("reverb_templates.id"), nullable=True)
    reverb_template = relationship("app.models.templates.ReverbTemplate")

    # product_types = relationship("EquipmentTypeProductType", back_populates="equipment_type")
    # Relationships defined at end of file to resolve forward references

class Model(Base):
    __tablename__ = "models"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=False)
    equipment_type_id = Column(Integer, ForeignKey("equipment_types.id"), nullable=False)
    width = Column(Float, nullable=False)
    depth = Column(Float, nullable=False)
    height = Column(Float, nullable=False)
    handle_length = Column(Float, nullable=True)
    handle_width = Column(Float, nullable=True)
    handle_location = Column(Enum(HandleLocation), default=HandleLocation.NO_AMP_HANDLE)
    angle_type = Column(Enum(AngleType), default=AngleType.NO_ANGLE)
    image_url = Column(String, nullable=True)
    parent_sku = Column(String(40), nullable=True)
    sku_override = Column(String, nullable=True)
    
    # Marketplace export exclusions
    exclude_from_amazon_export = Column(Boolean, nullable=False, default=False, server_default="false")
    exclude_from_ebay_export = Column(Boolean, nullable=False, default=False, server_default="false")
    exclude_from_reverb_export = Column(Boolean, nullable=False, default=False, server_default="false")
    exclude_from_etsy_export = Column(Boolean, nullable=False, default=False, server_default="false")
    
    surface_area_sq_in = Column(Float, nullable=True)
    top_depth_in = Column(Float, nullable=True)
    angle_drop_in = Column(Float, nullable=True)
    
    # FK-based design option selection (replaces enum-based selection in UI)
    handle_location_option_id = Column(Integer, ForeignKey("design_options.id", ondelete="SET NULL"), nullable=True)
    angle_type_option_id = Column(Integer, ForeignKey("design_options.id", ondelete="SET NULL"), nullable=True)
    
    # Top handle measurements for design notes
    top_handle_length_in = Column(Float, nullable=True)
    top_handle_height_in = Column(Float, nullable=True)
    top_handle_rear_edge_to_center_in = Column(Float, nullable=True)
    
    # Universal model notes field (not a design option)
    model_notes = Column(String, nullable=True)
    
    # Reverb product ID for order line resolution
    reverb_product_id = Column(String(32), nullable=True, index=True)
    
    series = relationship("Series", back_populates="models")
    equipment_type = relationship("EquipmentType", back_populates="models")
    order_lines = relationship("OrderLine", back_populates="model")
    
    # Relationships to design options for dynamic handle/angle selection
    handle_location_option = relationship("DesignOption", foreign_keys=[handle_location_option_id])
    angle_type_option = relationship("DesignOption", foreign_keys=[angle_type_option_id])
    
    # Marketplace listings
    marketplace_listings = relationship("MarketplaceListing", back_populates="model", cascade="all, delete-orphan")
    
    # Amazon A+ Content
    amazon_a_plus_content = relationship("ModelAmazonAPlusContent", back_populates="model", cascade="all, delete-orphan")
    
    # eBay Variation SKUs
    variation_skus = relationship("ModelVariationSKU", back_populates="model", cascade="all, delete-orphan")
    
    __table_args__ = (UniqueConstraint('series_id', 'name', name='uq_model_series_name'),)

class Material(Base):
    __tablename__ = "materials"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    base_color = Column(String, nullable=False)
    material_type = Column(Enum(MaterialType), default=MaterialType.FABRIC, nullable=False)
    linear_yard_width = Column(Float, nullable=True)
    weight_per_linear_yard = Column(Float, nullable=True)
    unit_of_measure = Column(Enum(UnitOfMeasure), default=UnitOfMeasure.YARD, nullable=True)
    package_quantity = Column(Float, nullable=True)
    weight_per_sq_in_oz = Column(Float, nullable=True)
    
    # eBay variation SKU fields
    sku_abbreviation = Column(String(3), nullable=True)
    ebay_variation_enabled = Column(Boolean, default=False, nullable=False)
    
    colour_surcharges = relationship("MaterialColourSurcharge", back_populates="material", cascade="all, delete-orphan")
    material_colors = relationship("MaterialColor", back_populates="material", cascade="all, delete-orphan")
    supplier_materials = relationship("SupplierMaterial", back_populates="material", cascade="all, delete-orphan")
    order_lines = relationship("OrderLine", back_populates="material")

class Color(Base):
    __tablename__ = "colors"

    id = Column(Integer, primary_key=True, index=True)
    internal_name = Column(String(128), nullable=False, unique=True)
    friendly_name = Column(String(128), nullable=False)
    sku_abbrev = Column(String(16), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    material_colors = relationship("MaterialColor", back_populates="color", cascade="all, delete-orphan")

class MaterialColor(Base):
    __tablename__ = "material_colors"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False, index=True)
    color_id = Column(Integer, ForeignKey("colors.id"), nullable=False, index=True)
    surcharge = Column(Float, nullable=False, default=0.0, server_default="0")
    ebay_variation_enabled = Column(Boolean, nullable=False, default=False, server_default="false")
    sort_order = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    material = relationship("Material", back_populates="material_colors")
    color = relationship("Color", back_populates="material_colors")

    __table_args__ = (UniqueConstraint("material_id", "color_id", name="uq_material_colors_material_color"),)

class MaterialColourSurcharge(Base):
    __tablename__ = "material_colour_surcharges"
    
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    colour = Column(String, nullable=False)
    surcharge = Column(Float, nullable=False)
    
    # eBay variation SKU fields
    color_friendly_name = Column(String(64), nullable=True)
    sku_abbreviation = Column(String(3), nullable=True)
    ebay_variation_enabled = Column(Boolean, default=False, nullable=False)
    
    material = relationship("Material", back_populates="colour_surcharges")

class Supplier(Base):
    __tablename__ = "suppliers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    contact_name = Column(String, nullable=True)
    address = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    website = Column(String, nullable=True)
    
    supplier_materials = relationship("SupplierMaterial", back_populates="supplier", cascade="all, delete-orphan")

class SupplierMaterial(Base):
    __tablename__ = "supplier_materials"
    
    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    unit_cost = Column(Float, nullable=False)
    shipping_cost = Column(Float, default=0.0)
    quantity_purchased = Column(Float, default=1.0)
    is_preferred = Column(Boolean, default=False)
    
    supplier = relationship("Supplier", back_populates="supplier_materials")
    material = relationship("Material", back_populates="supplier_materials")
    
    __table_args__ = (UniqueConstraint('supplier_id', 'material_id', name='uq_supplier_material'),)

class Customer(Base):
    __tablename__ = "customers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    address = Column(String, nullable=True)  # Legacy field, kept for backwards compat
    phone = Column(String, nullable=True)    # Legacy field, kept for backwards compat
    
    # Names
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    
    # Emails (TWO DISTINCT EMAILS)
    buyer_email = Column(String(255), nullable=True, index=True)           # Real customer email, editable
    marketplace_buyer_email = Column(String(255), nullable=True, index=True)  # Relay/proxy from marketplaces, read-only
    
    # Phones
    mobile_phone = Column(String(40), nullable=True)
    work_phone = Column(String(40), nullable=True)
    other_phone = Column(String(40), nullable=True)
    
    # Billing Address
    billing_address1 = Column(String(255), nullable=True)
    billing_address2 = Column(String(255), nullable=True)
    billing_city = Column(String(120), nullable=True)
    billing_state = Column(String(120), nullable=True)
    billing_postal_code = Column(String(40), nullable=True)
    billing_country = Column(String(80), nullable=True)
    
    # Shipping Name + Address
    shipping_name = Column(String(255), nullable=True)
    shipping_address1 = Column(String(255), nullable=True)
    shipping_address2 = Column(String(255), nullable=True)
    shipping_city = Column(String(120), nullable=True)
    shipping_state = Column(String(120), nullable=True)
    shipping_postal_code = Column(String(40), nullable=True)
    shipping_country = Column(String(80), nullable=True)
    
    # Marketplace identity (for deterministic matching)
    source_marketplace = Column(String(40), nullable=True)
    source_customer_id = Column(String(80), nullable=True)
    
    # Relationships
    orders = relationship("Order", back_populates="customer", cascade="all, delete-orphan")
    marketplace_orders = relationship("MarketplaceOrder", back_populates="customer")

class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    marketplace = Column(Enum(Marketplace), nullable=True)
    marketplace_order_number = Column(String, nullable=True)
    order_date = Column(DateTime, default=datetime.utcnow)
    
    customer = relationship("Customer", back_populates="orders")
    order_lines = relationship("OrderLine", back_populates="order", cascade="all, delete-orphan")

class OrderLine(Base):
    __tablename__ = "order_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    colour = Column(String, nullable=True)
    quantity = Column(Integer, default=1)
    handle_zipper = Column(Boolean, default=False)
    two_in_one_pocket = Column(Boolean, default=False)
    music_rest_zipper = Column(Boolean, default=False)
    unit_price = Column(Float, nullable=True)
    
    order = relationship("Order", back_populates="order_lines")
    model = relationship("Model", back_populates="order_lines")
    material = relationship("Material", back_populates="order_lines")

class PricingOption(Base):
    __tablename__ = "pricing_options"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    price = Column(Float, nullable=False)
    
    # eBay variation SKU fields
    sku_abbreviation = Column(String(3), nullable=True)
    ebay_variation_enabled = Column(Boolean, default=False, nullable=False)
    
    # Optional mapping to design option (for features representing same real-world option)
    linked_design_option_id = Column(Integer, ForeignKey("design_options.id"), nullable=True)
    
    # Relationships
    equipment_types = relationship("EquipmentTypePricingOption", back_populates="pricing_option")
    linked_design_option = relationship("DesignOption", foreign_keys=[linked_design_option_id])

class EquipmentTypePricingOption(Base):
    __tablename__ = "equipment_type_pricing_options"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_type_id = Column(Integer, ForeignKey("equipment_types.id"), nullable=False)
    pricing_option_id = Column(Integer, ForeignKey("pricing_options.id"), nullable=False)
    
    equipment_type = relationship("EquipmentType", back_populates="pricing_options")
    pricing_option = relationship("PricingOption", back_populates="equipment_types")
    
    __table_args__ = (UniqueConstraint('equipment_type_id', 'pricing_option_id', name='uq_equip_type_pricing_option'),)

class ShippingZone(Base):
    __tablename__ = "shipping_zones"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    sort_order = Column(Integer, default=0)
    active = Column(Boolean, default=True)
    
class ShippingRate(Base):
    __tablename__ = "shipping_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    carrier = Column(Enum(Carrier), nullable=False)
    min_weight = Column(Float, nullable=False)
    max_weight = Column(Float, nullable=False)
    zone = Column(String, nullable=False)
    rate = Column(Float, nullable=False)
    surcharge = Column(Float, default=0.0)

class DesignOption(Base):
    __tablename__ = "design_options"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    option_type = Column(String, nullable=False, index=True)
    is_pricing_relevant = Column(Boolean, nullable=False, default=False, server_default="false")
    price_cents = Column(Integer, nullable=False, default=0, server_default="0")
    placeholder_token = Column(String, unique=True, nullable=True)
    
    # eBay variation SKU fields
    sku_abbreviation = Column(String(3), nullable=True)
    ebay_variation_enabled = Column(Boolean, default=False, nullable=False)
    
    equipment_types = relationship("EquipmentTypeDesignOption", back_populates="design_option")

    @property
    def equipment_type_ids(self) -> List[int]:
        return [assoc.equipment_type_id for assoc in self.equipment_types]

class EquipmentTypeDesignOption(Base):
    __tablename__ = "equipment_type_design_options"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_type_id = Column(Integer, ForeignKey("equipment_types.id"), nullable=False)
    design_option_id = Column(Integer, ForeignKey("design_options.id"), nullable=False)
    
    equipment_type = relationship("EquipmentType", back_populates="design_options")
    design_option = relationship("DesignOption", back_populates="equipment_types")
    
    __table_args__ = (UniqueConstraint('equipment_type_id', 'design_option_id', name='uq_equip_type_design_option'),)

class MaterialRoleAssignment(Base):
    __tablename__ = "material_role_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False)
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    effective_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    material = relationship("Material")
    
    __table_args__ = (
        # Index for fast lookup of active roles
        # In SQLite/others, we often just index the columns. 
        # For effective dating, (role, end_date) is useful.
        # We'll rely on simple indexing for now.
    )

class MaterialRoleConfig(Base):
    __tablename__ = "material_role_configs"

    id = Column(Integer, primary_key=True, index=True)

    # Identifier key (stored uppercase by API)
    # Example: "CHOICE_WATERPROOF_FABRIC"
    role = Column(String, nullable=False, index=True)

    # Optional friendly name for admin/UI use
    display_name = Column(String, nullable=True)
    display_name_with_padding = Column(String, nullable=True)

    # Role-level SKU abbreviations used for variation generation
    # Example: "C" (no padding), "CG" (with padding)
    sku_abbrev_no_padding = Column(String(4), nullable=True)
    sku_abbrev_with_padding = Column(String(4), nullable=True)

    ebay_variation_enabled = Column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    sort_order = Column(
        Integer, nullable=False, default=0, server_default="0"
    )

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("role", name="uq_material_role_config_role"),
    )


class ShippingRateCard(Base):
    __tablename__ = "shipping_rate_cards"
    
    id = Column(Integer, primary_key=True, index=True)
    carrier = Column(Enum(Carrier), nullable=False)
    name = Column(String, nullable=False)
    effective_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True)
    
    tiers = relationship("ShippingRateTier", back_populates="rate_card", cascade="all, delete-orphan")
    zone_rates = relationship("ShippingZoneRate", back_populates="rate_card", cascade="all, delete-orphan")

class ShippingRateTier(Base):
    __tablename__ = "shipping_rate_tiers"
    
    id = Column(Integer, primary_key=True, index=True)
    rate_card_id = Column(Integer, ForeignKey("shipping_rate_cards.id"), nullable=False)
    min_oz = Column(Float, nullable=False) # DECIMAL(10,4) handled as Float in SQLite for simplicity/compat
    max_oz = Column(Float, nullable=False)
    label = Column(String, nullable=True)
    active = Column(Boolean, default=True)
    
    rate_card = relationship("ShippingRateCard", back_populates="tiers")
    zone_rates = relationship("ShippingZoneRate", back_populates="tier", cascade="all, delete-orphan")

class ShippingZoneRate(Base):
    __tablename__ = "shipping_zone_rates"
    
    id = Column(Integer, primary_key=True, index=True)
    rate_card_id = Column(Integer, ForeignKey("shipping_rate_cards.id"), nullable=False)
    tier_id = Column(Integer, ForeignKey("shipping_rate_tiers.id"), nullable=False)
    zone = Column(Integer, nullable=False)
    rate_cents = Column(Integer, nullable=False)
    
    rate_card = relationship("ShippingRateCard", back_populates="zone_rates")
    tier = relationship("ShippingRateTier", back_populates="zone_rates")
    
    __table_args__ = (UniqueConstraint('tier_id', 'zone', name='uq_tier_zone'),)

class MarketplaceShippingProfile(Base):
    __tablename__ = "marketplace_shipping_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    marketplace = Column(String, nullable=False, default="DEFAULT")
    rate_card_id = Column(Integer, ForeignKey("shipping_rate_cards.id"), nullable=False)
    pricing_zone = Column(Integer, nullable=False)
    effective_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    
    rate_card = relationship("ShippingRateCard")

# Force reload
class ShippingDefaultSetting(Base):
    __tablename__ = "shipping_default_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    shipping_mode = Column(String, default="calculated", nullable=False) # 'calculated' | 'flat'
    flat_shipping_cents = Column(Integer, default=0)
    default_rate_card_id = Column(Integer, ForeignKey("shipping_rate_cards.id"), nullable=True)
    default_zone_code = Column(String, nullable=True) # "1"-"5"
    
    assumed_rate_card_id = Column(Integer, ForeignKey("shipping_rate_cards.id"), nullable=True)
    assumed_tier_id = Column(Integer, ForeignKey("shipping_rate_tiers.id"), nullable=True)
    assumed_zone_code = Column(String, nullable=True)

    shipping_settings_version = Column(Integer, default=1)
    
    default_rate_card = relationship("ShippingRateCard", foreign_keys=[default_rate_card_id])
    assumed_rate_card = relationship("ShippingRateCard", foreign_keys=[assumed_rate_card_id])

class LaborSetting(Base):
    __tablename__ = "labor_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    hourly_rate_cents = Column(Integer, default=1700)
    minutes_no_padding = Column(Integer, default=35)
    minutes_with_padding = Column(Integer, default=60)

class VariantProfitSetting(Base):
    __tablename__ = "variant_profit_settings"
    
    variant_key = Column(String, primary_key=True)
    profit_cents = Column(Integer, nullable=False)

class MarketplaceFeeRate(Base):
    __tablename__ = "marketplace_fee_rates"
    
    marketplace = Column(String, primary_key=True)
    fee_rate = Column(Float, nullable=False) # DECIMAL(6,5)

class ExportSetting(Base):
    __tablename__ = "export_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    default_save_path_template = Column(String, nullable=True)
    amazon_customization_export_format = Column(String, default="xlsx", nullable=False)
    ebay_fabric_template_no_padding = Column(String, nullable=True, default="{role}")
    ebay_fabric_template_with_padding = Column(String, nullable=True, default="{role} w/ Padding")
    ebay_store_category_default_level = Column(String, nullable=False, default="series")
    ebay_parent_image_pattern = Column(String, nullable=True)
    ebay_variation_image_pattern = Column(String, nullable=True)
    ebay_description_selection_mode = Column(String, nullable=False, default="GLOBAL_PRIMARY")


class EbayVariationPresetAsset(Base):
    __tablename__ = "ebay_variation_preset_assets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    marketplace = Column(String, nullable=False, default="EBAY", server_default="EBAY", index=True)
    equipment_type_ids = Column(JSON, nullable=False, default=list, server_default="[]")
    payload = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class EbayStoreCategory(Base):
    __tablename__ = "ebay_store_categories"

    id = Column(Integer, primary_key=True, index=True)
    system = Column(String, nullable=False, default="ebay", index=True)
    level = Column(String, nullable=False, index=True)  # equipment_type | manufacturer | series

    equipment_type_id = Column(Integer, ForeignKey("equipment_types.id"), nullable=False, index=True)
    manufacturer_id = Column(Integer, ForeignKey("manufacturers.id"), nullable=True, index=True)
    series_id = Column(Integer, ForeignKey("series.id"), nullable=True, index=True)
    parent_id = Column(Integer, ForeignKey("ebay_store_categories.id"), nullable=True, index=True)

    category_id = Column(String, nullable=False)
    category_name = Column(String, nullable=True)
    store_category_number = Column(BigInteger, nullable=True)
    ebay_category_id = Column(Integer, nullable=True)
    is_enabled = Column(Boolean, nullable=False, default=True, server_default="true")

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    equipment_type = relationship("EquipmentType")
    manufacturer = relationship("Manufacturer")
    series = relationship("Series")
    parent = relationship("EbayStoreCategory", remote_side=[id], back_populates="children")
    children = relationship("EbayStoreCategory", back_populates="parent")

    __table_args__ = (
        Index(
            "uq_ebay_store_cat_equipment_type",
            "system",
            "level",
            "equipment_type_id",
            unique=True,
            sqlite_where=(level == "equipment_type"),
            postgresql_where=(level == "equipment_type"),
        ),
        Index(
            "uq_ebay_store_cat_manufacturer",
            "system",
            "level",
            "equipment_type_id",
            "manufacturer_id",
            unique=True,
            sqlite_where=(level == "manufacturer"),
            postgresql_where=(level == "manufacturer"),
        ),
        Index(
            "uq_ebay_store_cat_series",
            "system",
            "level",
            "equipment_type_id",
            "series_id",
            unique=True,
            sqlite_where=(level == "series"),
            postgresql_where=(level == "series"),
        ),
    )


class EbayStoreCategoryNode(Base):
    __tablename__ = "ebay_store_category_nodes"

    id = Column(Integer, primary_key=True, index=True)
    system = Column(String, nullable=False, default="ebay", index=True)
    level = Column(String, nullable=False, index=True)  # top | second | third
    name = Column(String, nullable=False)
    store_category_number = Column(BigInteger, nullable=False)
    parent_id = Column(Integer, ForeignKey("ebay_store_category_nodes.id"), nullable=True, index=True)
    is_enabled = Column(Boolean, nullable=False, default=True, server_default="true")

    binding_type = Column(String, nullable=False, default="none", server_default="none")
    binding_id = Column(Integer, nullable=True)
    binding_label = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    parent = relationship("EbayStoreCategoryNode", remote_side=[id], back_populates="children")
    children = relationship("EbayStoreCategoryNode", back_populates="parent")
    bindings = relationship("EbayStoreCategoryNodeBinding", back_populates="node", cascade="all, delete-orphan")


class EbayStoreCategoryNodeBinding(Base):
    __tablename__ = "ebay_store_category_node_bindings"

    id = Column(Integer, primary_key=True, index=True)
    node_id = Column(Integer, ForeignKey("ebay_store_category_nodes.id", ondelete="CASCADE"), nullable=False, index=True)
    binding_type = Column(String, nullable=False, index=True)
    binding_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    node = relationship("EbayStoreCategoryNode", back_populates="bindings")

    __table_args__ = (
        UniqueConstraint("node_id", "binding_type", "binding_id", name="uq_ebay_store_category_node_binding"),
    )

class ModelPricingSnapshot(Base):
    __tablename__ = "model_pricing_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    marketplace = Column(String, nullable=False, default="DEFAULT")
    variant_key = Column(String, nullable=False)
    
    raw_cost_cents = Column(Integer, nullable=False)
    base_cost_cents = Column(Integer, nullable=False)
    retail_price_cents = Column(Integer, nullable=False)
    marketplace_fee_cents = Column(Integer, nullable=False)
    profit_cents = Column(Integer, nullable=False)
    
    material_cost_cents = Column(Integer, nullable=False)
    shipping_cost_cents = Column(Integer, nullable=False)
    labor_cost_cents = Column(Integer, nullable=False)
    weight_oz = Column(Float, nullable=False)
    
    shipping_settings_version_used = Column(Integer, nullable=True)
    
    # Tooltip / Reconciliation Metadata (Nullable)
    surface_area_sq_in = Column(Float, nullable=True)
    material_cost_per_sq_in_cents = Column(Integer, nullable=True)
    labor_minutes = Column(Integer, nullable=True)
    labor_rate_cents_per_hour = Column(Integer, nullable=True)
    marketplace_fee_rate = Column(Float, nullable=True)
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    model = relationship("Model")
    
    __table_args__ = (UniqueConstraint('model_id', 'marketplace', 'variant_key', name='uq_model_mp_variant'),)

class ModelPricingHistory(Base):
    __tablename__ = "model_pricing_history"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("models.id"), nullable=False)
    marketplace = Column(String, nullable=False)
    variant_key = Column(String, nullable=False)
    
    raw_cost_cents = Column(Integer, nullable=False)
    base_cost_cents = Column(Integer, nullable=False)
    retail_price_cents = Column(Integer, nullable=False)
    marketplace_fee_cents = Column(Integer, nullable=False)
    profit_cents = Column(Integer, nullable=False)
    
    material_cost_cents = Column(Integer, nullable=False)
    shipping_cost_cents = Column(Integer, nullable=False)
    labor_cost_cents = Column(Integer, nullable=False)
    weight_oz = Column(Float, nullable=False)
    
    # Tooltip / Reconciliation Metadata (Nullable)
    surface_area_sq_in = Column(Float, nullable=True)
    material_cost_per_sq_in_cents = Column(Integer, nullable=True)
    labor_minutes = Column(Integer, nullable=True)
    labor_rate_cents_per_hour = Column(Integer, nullable=True)
    marketplace_fee_rate = Column(Float, nullable=True)
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    pricing_context_hash = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    
    model = relationship("Model")
    
    __table_args__ = (
        Index('ix_model_pricing_history_lookup', 'model_id', 'marketplace', 'variant_key', 'calculated_at'),
    )

class ModelAmazonAPlusContent(Base):
    __tablename__ = "model_amazon_a_plus_content"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    content_type = Column(String(20), nullable=False) # BRAND_STORY, EBC
    is_uploaded = Column(Boolean, default=False, nullable=False)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    model = relationship("Model", back_populates="amazon_a_plus_content")
    
    __table_args__ = (
        UniqueConstraint('model_id', 'content_type', name='uq_model_aplus_content_type'),
    )

class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False)
    marketplace = Column(String(20), nullable=False)
    external_id = Column(String(64), nullable=False)
    listing_url = Column(String, nullable=True)
    status = Column(String(20), nullable=True)
    parent_external_id = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    model = relationship("Model", back_populates="marketplace_listings")
    
    __table_args__ = (
        UniqueConstraint('model_id', 'marketplace', 'external_id', name='uq_model_marketplace_external_id'),
        Index('ix_marketplace_listings_model_id', 'model_id'),
        Index('ix_marketplace_listings_marketplace_external_id', 'marketplace', 'external_id')
    )

class ModelVariationSKU(Base):
    __tablename__ = "model_variation_skus"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(Integer, ForeignKey("models.id", ondelete="CASCADE"), nullable=False, index=True)
    sku = Column(String, nullable=False, unique=True, index=True)
    
    # Variation components
    material_id = Column(Integer, ForeignKey("materials.id"), nullable=False)
    material_colour_surcharge_id = Column(Integer, ForeignKey("material_colour_surcharges.id"), nullable=True)
    
    # Stored as JSON arrays
    design_option_ids = Column(JSON, nullable=False, default=list)
    pricing_option_ids = Column(JSON, nullable=False, default=list)
    
    # Legacy/additional fields
    is_parent = Column(Boolean, default=False, nullable=False)
    with_padding = Column(Boolean, nullable=False, default=False)
    retail_price_cents = Column(Integer, nullable=True)
    role_key = Column(String, nullable=True)
        
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    model = relationship("Model", back_populates="variation_skus")
    material = relationship("Material")
    material_colour_surcharge = relationship("MaterialColourSurcharge")


# =============================================================================
# MARKETPLACE ORDER IMPORT MODELS (Canonical Import Tables)
# =============================================================================

class MarketplaceImportRun(Base):
    """Audit log for each marketplace order import execution."""
    __tablename__ = "marketplace_import_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    marketplace = Column(Enum(Marketplace), nullable=False)
    external_store_id = Column(String(128), nullable=True)
    started_at = Column(DateTime, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)  # success | partial | failed
    orders_fetched = Column(Integer, nullable=False, default=0)
    orders_upserted = Column(Integer, nullable=False, default=0)
    errors_count = Column(Integer, nullable=False, default=0)
    error_summary = Column(JSON, nullable=True)
    
    # Relationships
    orders = relationship("MarketplaceOrder", back_populates="import_run")


class MarketplaceOrder(Base):
    """Canonical order header for marketplace imports and manual orders."""
    __tablename__ = "marketplace_orders"
    
    id = Column(Integer, primary_key=True, index=True)
    import_run_id = Column(Integer, ForeignKey("marketplace_import_runs.id", ondelete="SET NULL"), nullable=True)
    source = Column(Enum(OrderSource), nullable=False)
    marketplace = Column(Enum(Marketplace), nullable=True)  # NULL for manual orders
    external_order_id = Column(String(128), nullable=True)
    external_order_number = Column(String(128), nullable=True)
    external_store_id = Column(String(128), nullable=True)
    
    # Dates
    order_date = Column(DateTime, nullable=False)
    created_at_external = Column(DateTime, nullable=True)
    updated_at_external = Column(DateTime, nullable=True)
    imported_at = Column(DateTime, nullable=False)
    last_synced_at = Column(DateTime, nullable=True)
    
    # Status
    status_raw = Column(String(64), nullable=True)
    status_normalized = Column(Enum(NormalizedOrderStatus), nullable=False, default=NormalizedOrderStatus.UNKNOWN)
    
    # Buyer
    buyer_name = Column(String(255), nullable=True)
    buyer_email = Column(String(255), nullable=True)
    buyer_phone = Column(String(50), nullable=True)
    
    # Money (cents)
    currency_code = Column(String(3), nullable=False, default='USD')
    items_subtotal_cents = Column(Integer, nullable=True)
    shipping_cents = Column(Integer, nullable=True)
    tax_cents = Column(Integer, nullable=True)
    discount_cents = Column(Integer, nullable=True)
    fees_cents = Column(Integer, nullable=True)
    refunded_cents = Column(Integer, nullable=True)
    order_total_cents = Column(Integer, nullable=True)
    
    # Fulfillment
    fulfillment_channel = Column(String(64), nullable=True)
    shipping_service_level = Column(String(64), nullable=True)
    ship_by_date = Column(DateTime, nullable=True)
    deliver_by_date = Column(DateTime, nullable=True)
    
    # Ops
    notes = Column(Text, nullable=True)
    import_error = Column(Text, nullable=True)
    raw_marketplace_data = Column(JSON, nullable=True)
    raw_marketplace_detail_data = Column(JSON, nullable=True)
    
    # Expanded fields (Reverb & others)
    payment_method = Column(String(64), nullable=True)
    payment_status = Column(String(64), nullable=True)
    shipping_provider = Column(String(64), nullable=True)
    shipping_code = Column(String(64), nullable=True)
    shipping_method = Column(String(128), nullable=True)
    reverb_buyer_id = Column(String(128), nullable=True)
    reverb_order_status = Column(String(64), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Customer linkage
    customer_id = Column(Integer, ForeignKey("customers.id", ondelete="SET NULL"), nullable=True)
    
    # Relationships
    import_run = relationship("MarketplaceImportRun", back_populates="orders")
    addresses = relationship("MarketplaceOrderAddress", back_populates="order", cascade="all, delete-orphan")
    lines = relationship("MarketplaceOrderLine", back_populates="order", cascade="all, delete-orphan")
    shipments = relationship("MarketplaceOrderShipment", back_populates="order", cascade="all, delete-orphan")
    customer = relationship("Customer", back_populates="marketplace_orders")
    
    __table_args__ = (
        UniqueConstraint('marketplace', 'external_order_id', name='uq_marketplace_external_order_id'),
    )


class MarketplaceOrderAddress(Base):
    """Shipping and billing addresses for marketplace orders."""
    __tablename__ = "marketplace_order_addresses"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("marketplace_orders.id", ondelete="CASCADE"), nullable=False)
    address_type = Column(String(20), nullable=False)  # shipping | billing
    name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    company = Column(String(255), nullable=True)
    line1 = Column(String(255), nullable=True)
    line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_or_region = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country_code = Column(String(10), nullable=True)
    raw_payload = Column(JSON, nullable=True)
    
    # Relationships
    order = relationship("MarketplaceOrder", back_populates="addresses")
    
    __table_args__ = (
        UniqueConstraint('order_id', 'address_type', name='uq_order_address_type'),
    )


class MarketplaceOrderLine(Base):
    """Line items for marketplace orders with optional model linking."""
    __tablename__ = "marketplace_order_lines"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("marketplace_orders.id", ondelete="CASCADE"), nullable=False)
    external_line_item_id = Column(String(128), nullable=True)
    
    # Item references
    marketplace_item_id = Column(String(128), nullable=True)
    sku = Column(String(64), nullable=True)
    asin = Column(String(20), nullable=True)
    listing_id = Column(String(64), nullable=True)
    product_id = Column(String(64), nullable=True)
    title = Column(String(500), nullable=True)
    variant = Column(String(255), nullable=True)
    
    # Qty & pricing
    quantity = Column(Integer, nullable=False)
    currency_code = Column(String(3), nullable=True)
    unit_price_cents = Column(Integer, nullable=True)
    line_subtotal_cents = Column(Integer, nullable=True)
    tax_cents = Column(Integer, nullable=True)
    discount_cents = Column(Integer, nullable=True)
    line_total_cents = Column(Integer, nullable=True)
    
    # Fulfillment
    fulfillment_status_raw = Column(String(64), nullable=True)
    fulfillment_status_normalized = Column(String(20), nullable=True)
    
    # Internal link
    model_id = Column(Integer, ForeignKey("models.id", ondelete="SET NULL"), nullable=True)
    
    # Customization
    customization_data = Column(JSON, nullable=True)
    
    # Raw
    raw_marketplace_data = Column(JSON, nullable=True)
    
    # Relationships
    order = relationship("MarketplaceOrder", back_populates="lines")
    model = relationship("Model")
    
    __table_args__ = (
        UniqueConstraint('order_id', 'external_line_item_id', name='uq_order_line_item_id'),
    )


class MarketplaceOrderShipment(Base):
    """Tracking and fulfillment shipments for marketplace orders."""
    __tablename__ = "marketplace_order_shipments"
    
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("marketplace_orders.id", ondelete="CASCADE"), nullable=False)
    external_shipment_id = Column(String(128), nullable=True)
    carrier = Column(String(64), nullable=True)
    service = Column(String(64), nullable=True)
    tracking_number = Column(String(128), nullable=True)
    shipped_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    raw_marketplace_data = Column(JSON, nullable=True)
    
    # Relationships
    order = relationship("MarketplaceOrder", back_populates="shipments")


class MarketplaceCredential(Base):
    """Storage for marketplace API credentials.
    
    Stores encrypted (or plaintext if allowed) credentials for each marketplace.
    Only one row per marketplace is allowed (unique constraint).
    """
    __tablename__ = "marketplace_credentials"
    
    id = Column(Integer, primary_key=True, index=True)
    marketplace = Column(String(50), nullable=False, unique=True, index=True)
    is_enabled = Column(Boolean, nullable=False, default=True)
    label = Column(String(255), nullable=True)
    secrets_blob = Column(Text, nullable=False)  # Encrypted or plaintext JSON
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('marketplace', name='uq_marketplace_credentials_marketplace'),
    )


# Post-class relationship definitions to handle forward references
EquipmentType.pricing_options = relationship("EquipmentTypePricingOption", back_populates="equipment_type", cascade="all, delete-orphan")
EquipmentType.design_options = relationship("EquipmentTypeDesignOption", back_populates="equipment_type", cascade="all, delete-orphan")


# =============================================================================
# MARKETPLACE MESSAGING
# =============================================================================

class MarketplaceConversation(Base):
    """Conversations from marketplaces (e.g. Reverb)."""
    __tablename__ = "marketplace_conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    marketplace = Column(String(20), nullable=True)
    external_conversation_id = Column(String(128), nullable=True)
    external_buyer_id = Column(String(128), nullable=True)
    external_order_id = Column(String(128), nullable=True)
    subject = Column(String(500), nullable=True)
    last_message_at = Column(DateTime, nullable=True)
    raw_conversation_data = Column(JSON, nullable=True)
    
    messages = relationship("MarketplaceMessage", back_populates="conversation", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('marketplace', 'external_conversation_id', name='uq_conversation_mp_ext_id'),
    )


class MarketplaceMessage(Base):
    """Individual messages within a conversation."""
    __tablename__ = "marketplace_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("marketplace_conversations.id", ondelete="CASCADE"), nullable=False)
    external_message_id = Column(String(128), nullable=True)
    sender_type = Column(String(20), nullable=True)  # buyer | seller | system
    sent_at = Column(DateTime, nullable=True)
    body_text = Column(Text, nullable=True)
    raw_message_data = Column(JSON, nullable=True)
    
    conversation = relationship("MarketplaceConversation", back_populates="messages")
    
    __table_args__ = (
        UniqueConstraint('conversation_id', 'external_message_id', name='uq_message_conv_ext_id'),
    )

