from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Union, Any
from datetime import datetime
from app.models.enums import HandleLocation, AngleType, Carrier, Marketplace, MaterialType, UnitOfMeasure, OrderSource, NormalizedOrderStatus

class ManufacturerBase(BaseModel):
    name: str

class ManufacturerCreate(ManufacturerBase):
    pass

class ManufacturerResponse(ManufacturerBase):
    id: int
    
    class Config:
        from_attributes = True

class SeriesBase(BaseModel):
    name: str
    manufacturer_id: int

class SeriesCreate(SeriesBase):
    pass

class SeriesResponse(SeriesBase):
    id: int
    
    class Config:
        from_attributes = True

class AmazonCustomizationTemplateResponse(BaseModel):
    id: int
    original_filename: str
    class Config:
        from_attributes = True

class ReverbTemplateReference(BaseModel):
    id: int
    display_name: Optional[str] = None
    original_filename: str
    class Config:
        from_attributes = True

class AmazonCustomizationTemplatePreviewResponse(BaseModel):
    template_id: int
    original_filename: str
    sheet_name: str
    max_row: int
    max_column: int
    preview_row_count: int
    preview_column_count: int
    grid: List[List[str]]

    class Config:
        from_attributes = True

class AmazonCustomizationTemplateAssignmentRequest(BaseModel):
    template_id: Optional[int] = None

class ReverbTemplateAssignmentRequest(BaseModel):
    template_id: Optional[int] = None

# Multi-template assignment schemas (slot-based)
class EquipmentTypeCustomizationTemplateAssignRequest(BaseModel):
    """Request to assign a template to a specific slot (1-3) for an equipment type."""
    template_id: int
    slot: int  # 1, 2, or 3

class EquipmentTypeCustomizationTemplateItem(BaseModel):
    """Single template assignment in a slot."""
    template_id: int
    slot: int
    original_filename: str
    upload_date: datetime
    
    class Config:
        from_attributes = True

class EquipmentTypeCustomizationTemplatesResponse(BaseModel):
    """Response showing all assigned templates (up to 3) for an equipment type."""
    equipment_type_id: int
    templates: List[EquipmentTypeCustomizationTemplateItem]
    default_template_id: Optional[int] = None

class EquipmentTypeCustomizationTemplateSetDefaultRequest(BaseModel):
    """Request to set one of the assigned templates as the default."""
    template_id: int


class EquipmentTypeBase(BaseModel):
    name: str

class EquipmentTypeCreate(EquipmentTypeBase):
    pass

class EquipmentTypeResponse(EquipmentTypeBase):
    id: int
    amazon_customization_template_id: Optional[int] = None
    amazon_customization_template: Optional[AmazonCustomizationTemplateResponse] = None
    
    reverb_template_id: Optional[int] = None
    reverb_template: Optional[ReverbTemplateReference] = None

    class Config:
        from_attributes = True

class AmazonAPlusContentBase(BaseModel):
    content_type: str
    is_uploaded: bool = False
    notes: Optional[str] = None

class AmazonAPlusContentCreate(AmazonAPlusContentBase):
    pass

class AmazonAPlusContentResponse(AmazonAPlusContentBase):
    id: int
    model_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ModelBase(BaseModel):
    name: str
    series_id: int
    equipment_type_id: int
    width: float
    depth: float
    height: float
    handle_length: Optional[float] = None
    handle_width: Optional[float] = None
    handle_location: HandleLocation = HandleLocation.NO_AMP_HANDLE
    angle_type: AngleType = AngleType.NO_ANGLE
    image_url: Optional[str] = None
    sku_override: Optional[str] = None
    top_depth_in: Optional[float] = None
    angle_drop_in: Optional[float] = None
    handle_location_option_id: Optional[int] = None
    angle_type_option_id: Optional[int] = None
    top_handle_length_in: Optional[float] = None
    top_handle_height_in: Optional[float] = None
    top_handle_rear_edge_to_center_in: Optional[float] = None
    model_notes: Optional[str] = None
    reverb_product_id: Optional[str] = None
    exclude_from_amazon_export: bool = False
    exclude_from_ebay_export: bool = False
    exclude_from_reverb_export: bool = False
    exclude_from_etsy_export: bool = False

class MarketplaceListingBase(BaseModel):
    marketplace: str
    external_id: str
    listing_url: Optional[str] = None

class MarketplaceListingCreate(MarketplaceListingBase):
    pass

class MarketplaceListingResponse(MarketplaceListingBase):
    id: int
    model_id: int
    status: Optional[str] = None
    parent_external_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ModelCreate(ModelBase):
    marketplace_listings: Optional[List[MarketplaceListingCreate]] = []
    amazon_a_plus_content: Optional[List[AmazonAPlusContentCreate]] = []

class ModelResponse(ModelBase):
    id: int
    parent_sku: Optional[str] = None
    surface_area_sq_in: Optional[float] = None
    marketplace_listings: List[MarketplaceListingResponse] = []
    amazon_a_plus_content: List[AmazonAPlusContentResponse] = []
    
    class Config:
        from_attributes = True

class MaterialBase(BaseModel):
    name: str
    base_color: str
    material_type: MaterialType = MaterialType.FABRIC
    linear_yard_width: Optional[float] = None
    weight_per_linear_yard: Optional[float] = None
    unit_of_measure: Optional[UnitOfMeasure] = UnitOfMeasure.YARD
    package_quantity: Optional[float] = None
    sku_abbreviation: Optional[str] = None
    ebay_variation_enabled: bool = False

class MaterialCreate(MaterialBase):
    pass

class MaterialResponse(MaterialBase):
    id: int
    
    class Config:
        from_attributes = True

class ColorBase(BaseModel):
    internal_name: str
    friendly_name: str
    sku_abbrev: str
    is_active: bool = True

class ColorCreate(ColorBase):
    pass

class ColorUpdate(BaseModel):
    internal_name: Optional[str] = None
    friendly_name: Optional[str] = None
    sku_abbrev: Optional[str] = None
    is_active: Optional[bool] = None

class ColorResponse(ColorBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MaterialColorAssignmentBase(BaseModel):
    material_id: int
    color_id: int
    surcharge: float = 0.0
    ebay_variation_enabled: bool = False
    sort_order: Optional[int] = None

class MaterialColorAssignmentCreate(MaterialColorAssignmentBase):
    pass

class MaterialColorAssignmentUpdate(BaseModel):
    surcharge: Optional[float] = None
    ebay_variation_enabled: Optional[bool] = None
    sort_order: Optional[int] = None

class MaterialColorAssignmentResponse(BaseModel):
    id: int
    material_id: int
    color_id: int
    surcharge: float
    ebay_variation_enabled: bool
    sort_order: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    color: ColorResponse

    class Config:
        from_attributes = True

class MaterialColourSurchargeBase(BaseModel):
    material_id: int
    colour: str
    surcharge: float
    color_friendly_name: Optional[str] = None
    sku_abbreviation: Optional[str] = None
    ebay_variation_enabled: bool = False

class MaterialColourSurchargeCreate(MaterialColourSurchargeBase):
    pass

class MaterialColourSurchargeResponse(MaterialColourSurchargeBase):
    id: int
    
    class Config:
        from_attributes = True

class SupplierBase(BaseModel):
    name: str
    contact_name: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None

class SupplierCreate(SupplierBase):
    pass

class SupplierResponse(SupplierBase):
    id: int
    
    class Config:
        from_attributes = True

class SupplierMaterialBase(BaseModel):
    supplier_id: int
    material_id: int
    unit_cost: float
    shipping_cost: float = 0.0
    quantity_purchased: float = 1.0
    is_preferred: bool = False

class SupplierMaterialCreate(SupplierMaterialBase):
    pass

class SupplierMaterialResponse(SupplierMaterialBase):
    id: int
    
    class Config:
        from_attributes = True

class SupplierMaterialWithSupplierResponse(BaseModel):
    id: int
    supplier_id: int
    material_id: int
    unit_cost: float
    shipping_cost: float
    quantity_purchased: float
    is_preferred: bool
    supplier_name: str
    material_type: Optional[MaterialType] = None
    cost_per_linear_yard: float = 0.0
    cost_per_square_inch: float = 0.0
    
    class Config:
        from_attributes = True

class SupplierMaterialWithMaterialResponse(BaseModel):
    id: int
    supplier_id: int
    material_id: int
    unit_cost: float
    shipping_cost: float
    quantity_purchased: float
    is_preferred: bool
    material_name: str
    material_type: Optional[MaterialType] = None
    linear_yard_width: Optional[float] = None
    cost_per_linear_yard: float = 0.0
    cost_per_square_inch: float = 0.0
    
    class Config:
        from_attributes = True

class SetPreferredSupplierRequest(BaseModel):
    supplier_id: int

class CustomerBase(BaseModel):
    name: str
    address: Optional[str] = None
    phone: Optional[str] = None

class CustomerCreate(CustomerBase):
    pass

class CustomerResponse(CustomerBase):
    id: int
    
    class Config:
        from_attributes = True

class OrderLineBase(BaseModel):
    model_id: int
    material_id: int
    colour: Optional[str] = None
    quantity: int = 1
    handle_zipper: bool = False
    two_in_one_pocket: bool = False
    music_rest_zipper: bool = False
    unit_price: Optional[float] = None

class OrderLineCreate(OrderLineBase):
    pass

class OrderLineResponse(OrderLineBase):
    id: int
    order_id: int
    
    class Config:
        from_attributes = True

class OrderBase(BaseModel):
    customer_id: int
    marketplace: Optional[Marketplace] = None
    marketplace_order_number: Optional[str] = None

class OrderCreate(OrderBase):
    order_lines: List[OrderLineCreate] = []

class OrderResponse(OrderBase):
    id: int
    order_date: datetime
    order_lines: List[OrderLineResponse] = []
    
    class Config:
        from_attributes = True

class PricingOptionBase(BaseModel):
    name: str
    price: float
    sku_abbreviation: Optional[str] = None
    ebay_variation_enabled: bool = False
    linked_design_option_id: Optional[int] = None

class PricingOptionCreate(PricingOptionBase):
    pass

class LinkedDesignOptionDetails(BaseModel):
    """Nested details for linked design option (for validation display)"""
    id: int
    name: str
    sku_abbreviation: Optional[str] = None
    ebay_variation_enabled: bool = False
    
    class Config:
        from_attributes = True

class PricingOptionResponse(PricingOptionBase):
    id: int
    linked_design_option: Optional[LinkedDesignOptionDetails] = None
    
    class Config:
        from_attributes = True

class ShippingRateBase(BaseModel):
    carrier: Carrier
    min_weight: float
    max_weight: float
    zone: str
    rate: float
    surcharge: float = 0.0

class ShippingRateCreate(ShippingRateBase):
    pass

class ShippingRateResponse(ShippingRateBase):
    id: int
    
    class Config:
        from_attributes = True

class PricingCalculateRequest(BaseModel):
    model_id: int
    material_id: int
    colour: Optional[str] = None
    quantity: int = 1
    handle_zipper: bool = False
    two_in_one_pocket: bool = False
    music_rest_zipper: bool = False
    carrier: Optional[Carrier] = Carrier.USPS
    zone: Optional[str] = "1"

class PricingCalculateResponse(BaseModel):
    area: float
    waste_area: float
    material_cost: float
    colour_surcharge: float
    option_surcharge: float
    weight: float
    shipping_cost: float
    unit_total: float
    total: float

class DesignOptionBase(BaseModel):
    name: str
    description: Optional[str] = None
    option_type: str
    is_pricing_relevant: bool = False
    equipment_type_ids: List[int] = []
    sku_abbreviation: Optional[str] = None
    ebay_variation_enabled: bool = False
    price_cents: int = 0
    placeholder_token: Optional[str] = None

class DesignOptionCreate(DesignOptionBase):
    pass

class DesignOptionResponse(DesignOptionBase):
    id: int
    price_cents: int
    
    class Config:
        from_attributes = True

# Settings Schemas

class MaterialRoleAssignmentCreate(BaseModel):
    role: str
    material_id: int
    effective_date: Optional[datetime] = None

class MaterialRoleAssignmentResponse(MaterialRoleAssignmentCreate):
    id: int
    end_date: Optional[datetime] = None
    created_at: datetime
    
    class Config:
         from_attributes = True

class ShippingZoneResponse(BaseModel):
    id: int
    code: str
    name: str
    sort_order: Optional[int] = 0
    active: bool
    
    class Config:
        from_attributes = True

class ShippingRateCardCreate(BaseModel):
    name: str # Only allow name. Carrier is defaulted by backend.
    effective_date: Optional[datetime] = None
    active: bool = True

    class Config:
        extra = "forbid"


class ShippingRateCardUpdate(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None

class ShippingRateCardResponse(ShippingRateCardCreate):
    id: int
    end_date: Optional[datetime] = None
    active: bool
    
    class Config:
        from_attributes = True

class ShippingRateTierCreate(BaseModel):
    rate_card_id: int
    min_oz: float
    max_oz: float
    label: Optional[str] = None
    active: bool = True

class ShippingRateTierUpdate(BaseModel):
    label: Optional[str] = None
    max_weight_oz: Optional[float] = None
    active: Optional[bool] = None

class TierCreateRequest(BaseModel):
    label: Optional[str] = None
    max_weight_oz: float

class ShippingRateTierResponse(ShippingRateTierCreate):
    id: int
    active: bool
    class Config:
        from_attributes = True

class ShippingZoneRateCreate(BaseModel):
    rate_card_id: int
    tier_id: int
    zone: int
    rate_cents: int

class ShippingZoneRateResponse(ShippingZoneRateCreate):
    id: int
    class Config:
        from_attributes = True

class ShippingZoneRateNormalizedResponse(BaseModel):
    zone_id: int
    zone_code: str
    zone_name: str
    rate_cents: Optional[int]
    zone_rate_id: Optional[int]

class ShippingZoneRateUpsertRequest(BaseModel):
    rate_cents: Optional[int]

class MarketplaceShippingProfileCreate(BaseModel):
    marketplace: str
    rate_card_id: int
    pricing_zone: int
    effective_date: Optional[datetime] = None

class MarketplaceShippingProfileUpdate(BaseModel):
    marketplace: Optional[str] = None
    rate_card_id: Optional[int] = None
    pricing_zone: Optional[int] = None
    effective_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

class MarketplaceShippingProfileResponse(MarketplaceShippingProfileCreate):
    id: int
    end_date: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ShippingDefaultSettingCreate(BaseModel):
    shipping_mode: str = "calculated" # "flat", "calculated", "fixed_cell"
    flat_shipping_cents: int = 0
    default_rate_card_id: Optional[int] = None
    default_zone_code: Optional[str] = None
    assumed_rate_card_id: Optional[int] = None
    assumed_tier_id: Optional[int] = None
    assumed_zone_code: Optional[str] = None

class ShippingDefaultSettingResponse(ShippingDefaultSettingCreate):
    id: int
    shipping_settings_version: int
    
    class Config:
        from_attributes = True

class LaborSettingCreate(BaseModel):
    hourly_rate_cents: int
    minutes_no_padding: int
    minutes_with_padding: int

class LaborSettingResponse(LaborSettingCreate):
    id: int
    class Config:
        from_attributes = True

class MarketplaceFeeRateCreate(BaseModel):
    marketplace: str
    fee_rate: float

class MarketplaceFeeRateResponse(MarketplaceFeeRateCreate):
    class Config:
        from_attributes = True

class VariantProfitSettingCreate(BaseModel):
    variant_key: str
    profit_cents: int

class VariantProfitSettingResponse(VariantProfitSettingCreate):
    class Config:
        from_attributes = True

class ExportSettingCreate(BaseModel):
    default_save_path_template: Optional[str] = None
    amazon_customization_export_format: Optional[str] = "xlsx"
    ebay_fabric_template_no_padding: Optional[str] = None
    ebay_fabric_template_with_padding: Optional[str] = None
    ebay_store_category_default_level: Optional[str] = None
    ebay_parent_image_pattern: Optional[str] = None
    ebay_variation_image_pattern: Optional[str] = None
    ebay_description_selection_mode: Optional[str] = None

class ExportSettingResponse(ExportSettingCreate):
    id: int
    class Config:
        from_attributes = True


class EbayVariationPresetPayload(BaseModel):
    role_keys: List[str]
    color_surcharge_ids: List[int]
    design_option_ids: List[int]
    with_padding: str

    @field_validator("with_padding")
    @classmethod
    def validate_with_padding(cls, value: str) -> str:
        if value not in ("non_padded", "padded", "both"):
            raise ValueError("with_padding must be one of: non_padded, padded, both")
        return value


class EbayVariationPresetCreate(BaseModel):
    name: str
    equipment_type_ids: Optional[List[int]] = []
    payload: EbayVariationPresetPayload


class EbayVariationPresetUpdate(BaseModel):
    name: Optional[str] = None
    equipment_type_ids: Optional[List[int]] = None
    payload: Optional[EbayVariationPresetPayload] = None


class EbayVariationPresetResponse(BaseModel):
    id: int
    name: str
    marketplace: str
    equipment_type_ids: List[int] = []
    payload: EbayVariationPresetPayload
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EbayStoreCategoryCreate(BaseModel):
    system: str = "ebay"
    level: str
    equipment_type_id: int
    manufacturer_id: Optional[int] = None
    series_id: Optional[int] = None
    parent_id: Optional[int] = None
    category_id: str
    category_name: Optional[str] = None
    store_category_number: Optional[int] = None
    ebay_category_id: Optional[int] = None
    is_enabled: bool = True


class EbayStoreCategoryUpdate(BaseModel):
    system: Optional[str] = None
    level: Optional[str] = None
    equipment_type_id: Optional[int] = None
    manufacturer_id: Optional[int] = None
    series_id: Optional[int] = None
    parent_id: Optional[int] = None
    category_id: Optional[str] = None
    category_name: Optional[str] = None
    store_category_number: Optional[int] = None
    ebay_category_id: Optional[int] = None
    is_enabled: Optional[bool] = None


class EbayStoreCategoryResponse(BaseModel):
    id: int
    system: str
    level: str
    equipment_type_id: int
    manufacturer_id: Optional[int] = None
    series_id: Optional[int] = None
    parent_id: Optional[int] = None
    category_id: str
    category_name: Optional[str] = None
    store_category_number: Optional[int] = None
    ebay_category_id: Optional[int] = None
    is_enabled: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EbayStoreCategoryNodeCreate(BaseModel):
    system: str = "ebay"
    level: str
    name: str
    store_category_number: int
    parent_id: Optional[int] = None
    is_enabled: bool = True
    binding_type: str = "none"
    binding_id: Optional[int] = None
    binding_label: Optional[str] = None
    bindings: Optional[List['EbayStoreCategoryNodeBindingCreate']] = None


class EbayStoreCategoryNodeBindingCreate(BaseModel):
    binding_type: str
    binding_id: int


class EbayStoreCategoryNodeBindingResponse(BaseModel):
    id: int
    binding_type: str
    binding_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EbayStoreCategoryNodeUpdate(BaseModel):
    system: Optional[str] = None
    level: Optional[str] = None
    name: Optional[str] = None
    store_category_number: Optional[int] = None
    parent_id: Optional[int] = None
    is_enabled: Optional[bool] = None
    binding_type: Optional[str] = None
    binding_id: Optional[int] = None
    binding_label: Optional[str] = None
    bindings: Optional[List[EbayStoreCategoryNodeBindingCreate]] = None


class EbayStoreCategoryNodeResponse(BaseModel):
    id: int
    system: str
    level: str
    name: str
    store_category_number: int
    parent_id: Optional[int] = None
    is_enabled: bool
    binding_type: str
    binding_id: Optional[int] = None
    binding_label: Optional[str] = None
    bindings: List[EbayStoreCategoryNodeBindingResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ModelPricingSnapshotResponse(BaseModel):
    id: int
    model_id: int
    marketplace: str
    variant_key: str
    raw_cost_cents: int
    base_cost_cents: int
    retail_price_cents: int
    marketplace_fee_cents: int
    profit_cents: int
    material_cost_cents: int
    shipping_cost_cents: int
    labor_cost_cents: int
    weight_oz: float
    
    # New Tooltip Metadata
    surface_area_sq_in: Optional[float] = None
    material_cost_per_sq_in_cents: Optional[int] = None
    labor_minutes: Optional[int] = None
    labor_rate_cents_per_hour: Optional[int] = None
    marketplace_fee_rate: Optional[float] = None
    
    calculated_at: datetime
    
    class Config:
        from_attributes = True

class ModelPricingHistoryResponse(BaseModel):
    id: int
    model_id: int
    marketplace: str
    variant_key: str
    
    raw_cost_cents: int
    base_cost_cents: int
    retail_price_cents: int
    marketplace_fee_cents: int
    profit_cents: int
    material_cost_cents: int
    shipping_cost_cents: int
    labor_cost_cents: int
    weight_oz: float
    
    # New Tooltip Metadata
    surface_area_sq_in: Optional[float] = None
    material_cost_per_sq_in_cents: Optional[int] = None
    labor_minutes: Optional[int] = None
    labor_rate_cents_per_hour: Optional[int] = None
    marketplace_fee_rate: Optional[float] = None
    
    calculated_at: datetime
    pricing_context_hash: Optional[str] = None
    reason: Optional[str] = None
    
    class Config:
        from_attributes = True

class PricingRecalculateBulkRequest(BaseModel):
    marketplaces: List[str] = ["amazon"]
    scope: str  # "manufacturer" | "series" | "models"
    manufacturer_id: Optional[int] = None
    series_id: Optional[int] = None
    model_ids: Optional[List[int]] = None
    variant_set: str = "baseline4"
    dry_run: bool = False

class PricingRecalculateResult(BaseModel):
    model_id: int
    error: Optional[str] = None

class PricingRecalculateBulkResponse(BaseModel):
    marketplaces: List[str]
    scope: str
    resolved_model_count: int
    results: Dict[str, Dict[str, List[Union[int, PricingRecalculateResult]]]] 
    # structure: { "amazon": { "succeeded": [1, 2], "failed": [{ "model_id": 3, "error": "msg" }] } }


class ExportStatsResponse(BaseModel):
    total_models: int
    models_with_pricing: int
    models_missing_pricing: int
    models_with_images: int
    models_missing_images: int
    equipment_types: Dict[str, int]

# eBay Variation SKU Schemas
class ModelVariationSKUBase(BaseModel):
    model_id: int
    variation_sku: str
    material_id: Optional[int] = None
    color_id: Optional[int] = None
    design_option_ids: Optional[List[int]] = None
    is_parent: bool = False
    retail_price_cents: Optional[int] = None

class ModelVariationSKUCreate(ModelVariationSKUBase):
    pass

class ModelVariationSKUResponse(ModelVariationSKUBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ============================================================
# Material Role Config Schemas
# ============================================================

class MaterialRoleConfigBase(BaseModel):
    role: str
    display_name: Optional[str] = None
    display_name_with_padding: Optional[str] = None
    sku_abbrev_no_padding: Optional[str] = None
    sku_abbrev_with_padding: Optional[str] = None
    ebay_variation_enabled: bool = False
    sort_order: int = 0


class MaterialRoleConfigCreate(MaterialRoleConfigBase):
    pass


class MaterialRoleConfigUpdate(BaseModel):
    display_name: Optional[str] = None
    display_name_with_padding: Optional[str] = None
    sku_abbrev_no_padding: Optional[str] = None
    sku_abbrev_with_padding: Optional[str] = None
    ebay_variation_enabled: Optional[bool] = None
    sort_order: Optional[int] = None


class MaterialRoleConfigResponse(MaterialRoleConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# ============================================================
# Material Role Assignment Schemas
# ============================================================

class MaterialRoleAssignmentBase(BaseModel):
    role: str
    material_id: int
    effective_date: Optional[datetime] = None


class MaterialRoleAssignmentCreate(MaterialRoleAssignmentBase):
    auto_end_previous: bool = True  # Auto-end previous active assignment for same role


class MaterialRoleAssignmentResponse(MaterialRoleAssignmentBase):
    id: int
    end_date: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Marketplace Order Import Schemas (Canonical Import Tables)
# ============================================================

# --- MarketplaceImportRun ---

class MarketplaceImportRunBase(BaseModel):
    marketplace: Marketplace
    external_store_id: Optional[str] = None
    started_at: datetime
    finished_at: Optional[datetime] = None
    status: str  # success | partial | failed
    orders_fetched: int = 0
    orders_upserted: int = 0
    errors_count: int = 0
    error_summary: Optional[Dict[str, Any]] = None

class MarketplaceImportRunCreate(MarketplaceImportRunBase):
    pass

class MarketplaceImportRunResponse(MarketplaceImportRunBase):
    id: int

    class Config:
        from_attributes = True


# --- MarketplaceOrderAddress ---

class MarketplaceOrderAddressBase(BaseModel):
    address_type: str  # shipping | billing
    name: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    line1: Optional[str] = None
    line2: Optional[str] = None
    city: Optional[str] = None
    state_or_region: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: Optional[str] = None
    raw_payload: Optional[Dict[str, Any]] = None

class MarketplaceOrderAddressCreate(MarketplaceOrderAddressBase):
    pass

class MarketplaceOrderAddressResponse(MarketplaceOrderAddressBase):
    id: int
    order_id: int

    class Config:
        from_attributes = True


# --- MarketplaceOrderLine ---

class MarketplaceOrderLineBase(BaseModel):
    external_line_item_id: Optional[str] = None
    marketplace_item_id: Optional[str] = None
    sku: Optional[str] = None
    asin: Optional[str] = None
    listing_id: Optional[str] = None
    product_id: Optional[str] = None
    title: Optional[str] = None
    variant: Optional[str] = None
    quantity: int
    currency_code: Optional[str] = None
    unit_price_cents: Optional[int] = None
    line_subtotal_cents: Optional[int] = None
    tax_cents: Optional[int] = None
    discount_cents: Optional[int] = None
    line_total_cents: Optional[int] = None
    fulfillment_status_raw: Optional[str] = None
    fulfillment_status_normalized: Optional[str] = None
    model_id: Optional[int] = None
    customization_data: Optional[Dict[str, Any]] = None
    raw_marketplace_data: Optional[Dict[str, Any]] = None

class MarketplaceOrderLineCreate(MarketplaceOrderLineBase):
    pass

class MarketplaceOrderLineUpdate(BaseModel):
    model_id: Optional[int] = None
    fulfillment_status_normalized: Optional[str] = None

class MarketplaceOrderLineResponse(MarketplaceOrderLineBase):
    id: int
    order_id: int
    # Resolved model information (populated during GET)
    resolved_model_id: Optional[int] = None
    resolved_model_name: Optional[str] = None
    resolved_manufacturer_name: Optional[str] = None
    resolved_series_name: Optional[str] = None

    class Config:
        from_attributes = True


# --- MarketplaceOrderShipment ---

class MarketplaceOrderShipmentBase(BaseModel):
    external_shipment_id: Optional[str] = None
    carrier: Optional[str] = None
    service: Optional[str] = None
    tracking_number: Optional[str] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    raw_marketplace_data: Optional[Dict[str, Any]] = None

class MarketplaceOrderShipmentCreate(MarketplaceOrderShipmentBase):
    pass

class MarketplaceOrderShipmentResponse(MarketplaceOrderShipmentBase):
    id: int
    order_id: int

    class Config:
        from_attributes = True


# --- MarketplaceOrder ---

class MarketplaceOrderBase(BaseModel):
    source: OrderSource
    marketplace: Optional[Marketplace] = None  # NULL for manual orders
    external_order_id: Optional[str] = None
    external_order_number: Optional[str] = None
    external_store_id: Optional[str] = None
    order_date: datetime
    created_at_external: Optional[datetime] = None
    updated_at_external: Optional[datetime] = None
    imported_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    status_raw: Optional[str] = None
    status_normalized: NormalizedOrderStatus = NormalizedOrderStatus.UNKNOWN
    buyer_name: Optional[str] = None
    buyer_email: Optional[str] = None
    buyer_phone: Optional[str] = None
    currency_code: str = "USD"
    items_subtotal_cents: Optional[int] = None
    shipping_cents: Optional[int] = None
    tax_cents: Optional[int] = None
    discount_cents: Optional[int] = None
    fees_cents: Optional[int] = None
    refunded_cents: Optional[int] = None
    order_total_cents: Optional[int] = None
    fulfillment_channel: Optional[str] = None
    shipping_service_level: Optional[str] = None
    ship_by_date: Optional[datetime] = None
    deliver_by_date: Optional[datetime] = None
    notes: Optional[str] = None
    import_error: Optional[str] = None
    raw_marketplace_data: Optional[Dict[str, Any]] = None

class MarketplaceOrderCreate(MarketplaceOrderBase):
    import_run_id: Optional[int] = None
    addresses: List[MarketplaceOrderAddressCreate] = []
    lines: List[MarketplaceOrderLineCreate] = []
    shipments: List[MarketplaceOrderShipmentCreate] = []

class MarketplaceOrderUpdate(BaseModel):
    status_raw: Optional[str] = None
    status_normalized: Optional[NormalizedOrderStatus] = None
    last_synced_at: Optional[datetime] = None
    notes: Optional[str] = None
    import_error: Optional[str] = None
    raw_marketplace_data: Optional[Dict[str, Any]] = None

class MarketplaceOrderResponse(MarketplaceOrderBase):
    id: int
    import_run_id: Optional[int] = None
    customer_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class MarketplaceOrderDetailResponse(MarketplaceOrderResponse):
    """Extended response with nested addresses, lines, and shipments."""
    addresses: List[MarketplaceOrderAddressResponse] = []
    lines: List[MarketplaceOrderLineResponse] = []
    shipments: List[MarketplaceOrderShipmentResponse] = []

    class Config:
        from_attributes = True


# ============================================================
# Customer Schemas
# ============================================================

class CustomerCreate(BaseModel):
    """Schema for creating a new customer."""
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    buyer_email: Optional[str] = None
    # Note: marketplace_buyer_email not in create - set during import only
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    work_phone: Optional[str] = None
    other_phone: Optional[str] = None
    address: Optional[str] = None  # Legacy field
    # Billing
    billing_address1: Optional[str] = None
    billing_address2: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_country: Optional[str] = None
    # Shipping
    shipping_name: Optional[str] = None
    shipping_address1: Optional[str] = None
    shipping_address2: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_postal_code: Optional[str] = None
    shipping_country: Optional[str] = None


class CustomerUpdate(BaseModel):
    """Schema for updating a customer. Only editable fields included."""
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    buyer_email: Optional[str] = None
    # marketplace_buyer_email: read-only, not editable
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    work_phone: Optional[str] = None
    other_phone: Optional[str] = None
    address: Optional[str] = None  # Legacy field
    # Billing
    billing_address1: Optional[str] = None
    billing_address2: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_country: Optional[str] = None
    # Shipping
    shipping_name: Optional[str] = None
    shipping_address1: Optional[str] = None
    shipping_address2: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_postal_code: Optional[str] = None
    shipping_country: Optional[str] = None


class CustomerResponse(BaseModel):
    """Response schema for customer data."""
    id: int
    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    buyer_email: Optional[str] = None
    marketplace_buyer_email: Optional[str] = None
    phone: Optional[str] = None
    mobile_phone: Optional[str] = None
    work_phone: Optional[str] = None
    other_phone: Optional[str] = None
    address: Optional[str] = None  # Legacy field
    # Billing
    billing_address1: Optional[str] = None
    billing_address2: Optional[str] = None
    billing_city: Optional[str] = None
    billing_state: Optional[str] = None
    billing_postal_code: Optional[str] = None
    billing_country: Optional[str] = None
    # Shipping
    shipping_name: Optional[str] = None
    shipping_address1: Optional[str] = None
    shipping_address2: Optional[str] = None
    shipping_city: Optional[str] = None
    shipping_state: Optional[str] = None
    shipping_postal_code: Optional[str] = None
    shipping_country: Optional[str] = None
    # Marketplace identity (read-only)
    source_marketplace: Optional[str] = None
    source_customer_id: Optional[str] = None

    class Config:
        from_attributes = True


# ============================================================
# Marketplace Credentials Schemas (Reverb)
# ============================================================

class ReverbCredentialsUpsertRequest(BaseModel):
    """Request schema for creating/updating Reverb API credentials."""
    is_enabled: bool = True
    api_token: str
    base_url: Optional[str] = "https://api.reverb.com"


class ReverbCredentialsResponse(BaseModel):
    """Response schema for Reverb credentials (token may be masked)."""
    marketplace: str = "reverb"
    is_enabled: bool
    api_token: str  # Either revealed or masked "********" depending on flag
    base_url: str
    updated_at: datetime

    class Config:
        from_attributes = True


class CredentialsTestResponse(BaseModel):
    """Response schema for credential testing endpoint."""
    ok: bool
    marketplace: str
    status_code: int
    account: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

