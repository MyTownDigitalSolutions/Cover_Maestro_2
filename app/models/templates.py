from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Text, JSON, DateTime, UniqueConstraint, Index, CheckConstraint, LargeBinary
from sqlalchemy.orm import relationship, deferred
from app.database import Base
from datetime import datetime

class AmazonCustomizationTemplate(Base):
    __tablename__ = "amazon_customization_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer, nullable=True)

class EquipmentTypeCustomizationTemplate(Base):
    """
    Join table for multi-template assignment to equipment types.
    Supports up to 3 templates per equipment type via slot-based assignment.
    """
    __tablename__ = "equipment_type_customization_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_type_id = Column(Integer, ForeignKey("equipment_types.id"), nullable=False)
    template_id = Column(Integer, ForeignKey("amazon_customization_templates.id"), nullable=False)
    slot = Column(Integer, nullable=False)  # 1, 2, or 3
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    equipment_type = relationship("EquipmentType")
    template = relationship("AmazonCustomizationTemplate")
    
    __table_args__ = (
        UniqueConstraint('equipment_type_id', 'slot', name='uq_equipment_type_customization_templates_slot'),
        UniqueConstraint('equipment_type_id', 'template_id', name='uq_equipment_type_customization_templates_template'),
    )

class AmazonProductType(Base):
    __tablename__ = "amazon_product_types"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    header_rows = Column(JSON, nullable=True)
    original_filename = Column(String, nullable=True)
    file_path = Column(String, nullable=True)
    upload_date = Column(DateTime, nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Export Configuration
    export_sheet_name_override = Column(String, nullable=True)
    export_start_row_override = Column(Integer, nullable=True)
    export_force_exact_start_row = Column(Boolean, nullable=False, default=False, server_default="0")
    
    keywords = relationship("ProductTypeKeyword", back_populates="product_type", cascade="all, delete-orphan")
    fields = relationship("ProductTypeField", back_populates="product_type", cascade="all, delete-orphan")
    equipment_types = relationship("EquipmentTypeProductType", back_populates="product_type", cascade="all, delete-orphan")


class EquipmentTypeProductType(Base):
    __tablename__ = "equipment_type_product_types"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_type_id = Column(Integer, ForeignKey("equipment_types.id"), nullable=False)
    product_type_id = Column(Integer, ForeignKey("amazon_product_types.id"), nullable=False)
    
    equipment_type = relationship("EquipmentType")
    product_type = relationship("AmazonProductType", back_populates="equipment_types")
    
    __table_args__ = (
        UniqueConstraint('equipment_type_id', name='uq_equipment_type_product_types_equipment_type_id'),
    )

class ProductTypeKeyword(Base):
    __tablename__ = "product_type_keywords"
    
    id = Column(Integer, primary_key=True, index=True)
    product_type_id = Column(Integer, ForeignKey("amazon_product_types.id"), nullable=False)
    keyword = Column(String, nullable=False)
    
    product_type = relationship("AmazonProductType", back_populates="keywords")

class ProductTypeField(Base):
    __tablename__ = "product_type_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    product_type_id = Column(Integer, ForeignKey("amazon_product_types.id"), nullable=False)
    field_name = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    attribute_group = Column(String, nullable=True)
    required = Column(Boolean, default=False)
    order_index = Column(Integer, default=0)
    description = Column(Text, nullable=True)
    selected_value = Column(String, nullable=True)
    custom_value = Column(String, nullable=True)
    
    product_type = relationship("AmazonProductType", back_populates="fields")
    valid_values = relationship("ProductTypeFieldValue", back_populates="field", cascade="all, delete-orphan")

class ProductTypeFieldValue(Base):
    __tablename__ = "product_type_field_values"
    
    id = Column(Integer, primary_key=True, index=True)
    product_type_field_id = Column(Integer, ForeignKey("product_type_fields.id"), nullable=False)
    value = Column(String, nullable=False)
    
    field = relationship("ProductTypeField", back_populates="valid_values")

class EbayTemplate(Base):
    __tablename__ = "ebay_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    sha256 = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    fields = relationship("EbayField", back_populates="ebay_template", cascade="all, delete-orphan")


class TemplateField(Base):
    __tablename__ = "template_fields"

    id = Column(Integer, primary_key=True, index=True)
    marketplace = Column(String, nullable=False)
    field_name = Column(String, nullable=False)
    field_key_norm = Column(String, nullable=False)
    order_index = Column(Integer, nullable=True)
    required = Column(Boolean, nullable=False, default=False, server_default="false")
    is_asset_managed = Column(Boolean, nullable=False, default=False, server_default="false")
    row_scope = Column(String, nullable=True)
    selected_value = Column(String, nullable=True)
    selected_value_source = Column(String, nullable=True)
    custom_value = Column(String, nullable=True)
    parent_selected_value = Column(String, nullable=True)
    parent_selected_value_source = Column(String, nullable=True)
    parent_custom_value = Column(String, nullable=True)
    variation_selected_value = Column(String, nullable=True)
    variation_selected_value_source = Column(String, nullable=True)
    variation_custom_value = Column(String, nullable=True)
    parsed_default_value = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    ebay_fields = relationship("EbayField", back_populates="template_field")
    assets = relationship(
        "TemplateFieldAsset",
        back_populates="template_field",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("marketplace", "field_key_norm", name="uq_template_fields_marketplace_field_key_norm"),
        Index("ix_template_fields_marketplace_field_key_norm", "marketplace", "field_key_norm"),
    )

class EbayField(Base):
    __tablename__ = "ebay_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    ebay_template_id = Column(Integer, ForeignKey("ebay_templates.id"), nullable=False)
    template_field_id = Column(Integer, ForeignKey("template_fields.id"), nullable=True)
    field_name = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    required = Column(Boolean, default=False)
    order_index = Column(Integer, nullable=True)
    selected_value = Column(String, nullable=True)
    custom_value = Column(String, nullable=True)
    parsed_default_value = Column(String, nullable=True)
    parent_selected_value = Column(String, nullable=True)
    parent_custom_value = Column(String, nullable=True)
    variation_selected_value = Column(String, nullable=True)
    variation_custom_value = Column(String, nullable=True)
    row_scope = Column(String, nullable=True)
    
    ebay_template = relationship("EbayTemplate", back_populates="fields")
    template_field = relationship("TemplateField", back_populates="ebay_fields")
    valid_values = relationship("EbayFieldValue", back_populates="field", cascade="all, delete-orphan")
    equipment_type_contents = relationship(
        "EbayFieldEquipmentTypeContent",
        back_populates="field",
        cascade="all, delete-orphan",
    )
    equipment_type_image_patterns = relationship(
        "EbayFieldEquipmentTypeImagePattern",
        back_populates="field",
        cascade="all, delete-orphan",
    )

class EbayFieldValue(Base):
    __tablename__ = "ebay_field_values"
    
    id = Column(Integer, primary_key=True, index=True)
    ebay_field_id = Column(Integer, ForeignKey("ebay_fields.id"), nullable=False)
    value = Column(String, nullable=False)
    
    field = relationship("EbayField", back_populates="valid_values")


class EbayFieldEquipmentTypeContent(Base):
    __tablename__ = "ebay_field_equipment_type_contents"

    id = Column(Integer, primary_key=True, index=True)
    ebay_field_id = Column(Integer, ForeignKey("ebay_fields.id", ondelete="CASCADE"), nullable=False)
    equipment_type_id = Column(Integer, ForeignKey("equipment_types.id", ondelete="CASCADE"), nullable=True)
    html_value = Column(Text, nullable=False)
    is_default_fallback = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    field = relationship("EbayField", back_populates="equipment_type_contents")
    equipment_type = relationship("EquipmentType")

    __table_args__ = (
        UniqueConstraint("ebay_field_id", "equipment_type_id", name="uq_ebay_field_equipment_type_content"),
    )


class EbayFieldEquipmentTypeImagePattern(Base):
    __tablename__ = "ebay_field_equipment_type_image_patterns"

    id = Column(Integer, primary_key=True, index=True)
    ebay_field_id = Column(Integer, ForeignKey("ebay_fields.id", ondelete="CASCADE"), nullable=False)
    equipment_type_id = Column(Integer, ForeignKey("equipment_types.id", ondelete="CASCADE"), nullable=True)
    parent_pattern = Column(Text, nullable=False)
    variation_pattern = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    field = relationship("EbayField", back_populates="equipment_type_image_patterns")
    equipment_type = relationship("EquipmentType")

    __table_args__ = (
        UniqueConstraint("ebay_field_id", "equipment_type_id", name="uq_ebay_field_equipment_type_image_pattern"),
    )


class TemplateFieldAsset(Base):
    __tablename__ = "template_field_assets"

    id = Column(Integer, primary_key=True, index=True)
    template_field_id = Column(Integer, ForeignKey("template_fields.id", ondelete="CASCADE"), nullable=False)
    asset_type = Column(String, nullable=False)
    name = Column(String, nullable=True)
    value = Column(Text, nullable=False)
    source = Column(String, nullable=False, default="user", server_default="user")
    is_default_fallback = Column(Boolean, nullable=False, default=False, server_default="false")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    template_field = relationship("TemplateField", back_populates="assets")
    equipment_type_links = relationship(
        "TemplateFieldAssetEquipmentType",
        back_populates="asset",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "asset_type in ('description_html','image_parent_pattern','image_variation_pattern')",
            name="ck_template_field_assets_asset_type",
        ),
    )


class TemplateFieldAssetEquipmentType(Base):
    __tablename__ = "template_field_asset_equipment_types"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("template_field_assets.id", ondelete="CASCADE"), nullable=False)
    equipment_type_id = Column(Integer, ForeignKey("equipment_types.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    asset = relationship("TemplateFieldAsset", back_populates="equipment_type_links")
    equipment_type = relationship("EquipmentType")

    __table_args__ = (
        UniqueConstraint("asset_id", "equipment_type_id", name="uq_template_field_asset_equipment_type"),
    )


class ReverbTemplate(Base):
    __tablename__ = "reverb_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    display_name = Column(String, nullable=True)
    original_filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    asset_blob = deferred(Column(LargeBinary, nullable=True))
    file_size = Column(Integer, nullable=False)
    sha256 = Column(String, nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    fields = relationship("ReverbField", back_populates="reverb_template", cascade="all, delete-orphan")


class ReverbField(Base):
    __tablename__ = "reverb_fields"
    
    id = Column(Integer, primary_key=True, index=True)
    reverb_template_id = Column(Integer, ForeignKey("reverb_templates.id"), nullable=False)
    field_name = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    required = Column(Boolean, default=False)
    order_index = Column(Integer, nullable=True)
    selected_value = Column(String, nullable=True)
    custom_value = Column(String, nullable=True)
    
    reverb_template = relationship("ReverbTemplate", back_populates="fields")
    valid_values = relationship("ReverbFieldValue", back_populates="field", cascade="all, delete-orphan")
    overrides = relationship("ReverbEquipmentTypeFieldOverride", back_populates="field", cascade="all, delete-orphan")


class ReverbFieldValue(Base):
    __tablename__ = "reverb_field_values"
    
    id = Column(Integer, primary_key=True, index=True)
    reverb_field_id = Column(Integer, ForeignKey("reverb_fields.id"), nullable=False)
    value = Column(String, nullable=False)
    
    field = relationship("ReverbField", back_populates="valid_values")


class ReverbEquipmentTypeFieldOverride(Base):
    __tablename__ = "reverb_equipment_type_field_overrides"
    
    id = Column(Integer, primary_key=True, index=True)
    equipment_type_id = Column(Integer, ForeignKey("equipment_types.id"), nullable=False)
    reverb_field_id = Column(Integer, ForeignKey("reverb_fields.id"), nullable=False)
    default_value = Column(String, nullable=True)
    
    equipment_type = relationship("EquipmentType")
    field = relationship("ReverbField", back_populates="overrides")
    
    __table_args__ = (
        UniqueConstraint('equipment_type_id', 'reverb_field_id', name='uq_reverb_et_field_override'),
    )
