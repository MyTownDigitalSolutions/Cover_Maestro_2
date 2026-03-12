from pydantic import BaseModel, field_validator
from typing import Optional, List
from datetime import datetime

class ProductTypeFieldValueResponse(BaseModel):
    id: int
    value: str
    
    class Config:
        from_attributes = True

class ProductTypeFieldResponse(BaseModel):
    id: int
    field_name: str
    display_name: Optional[str] = None
    attribute_group: Optional[str] = None
    required: bool = False
    order_index: int = 0
    description: Optional[str] = None
    selected_value: Optional[str] = None
    custom_value: Optional[str] = None
    valid_values: List[ProductTypeFieldValueResponse] = []
    
    class Config:
        from_attributes = True

class ProductTypeKeywordResponse(BaseModel):
    id: int
    keyword: str
    
    class Config:
        from_attributes = True

class AmazonProductTypeResponse(BaseModel):
    id: int
    code: str
    name: Optional[str] = None
    description: Optional[str] = None
    header_rows: Optional[List[List[Optional[str]]]] = None
    export_sheet_name_override: Optional[str] = None
    export_start_row_override: Optional[int] = None
    export_force_exact_start_row: bool = False
    keywords: List[ProductTypeKeywordResponse] = []
    fields: List[ProductTypeFieldResponse] = []
    
    class Config:
        from_attributes = True

class TemplateImportResponse(BaseModel):
    product_code: str
    fields_imported: int
    keywords_imported: int
    valid_values_imported: int
    sheet_count: int = 0
    sheet_names: List[str] = []

class EquipmentTypeProductTypeLinkCreate(BaseModel):
    equipment_type_id: int
    product_type_id: int

class EquipmentTypeProductTypeLinkResponse(BaseModel):
    id: int
    equipment_type_id: int
    product_type_id: int
    
    class Config:
        from_attributes = True

class ProductTypeFieldUpdate(BaseModel):
    required: Optional[bool] = None
    selected_value: Optional[str] = None

class ProductTypeFieldValueCreate(BaseModel):
    value: str

class AmazonProductTypeTemplatePreviewResponse(BaseModel):
    product_code: str
    original_filename: str
    sheet_name: str
    max_row: int
    max_column: int
    preview_row_count: int
    preview_column_count: int
    grid: List[List[str]]

class ProductTypeExportConfigUpdate(BaseModel):
    export_sheet_name_override: Optional[str] = None
    export_start_row_override: Optional[int] = None
    
    @field_validator('export_start_row_override')
    def validate_start_row(cls, v):
        if v is not None and v < 1:
            raise ValueError('Start row must be >= 1')
        return v
    
    @field_validator('export_sheet_name_override')
    def validate_sheet_name(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
        return v

class EbayTemplateResponse(BaseModel):
    id: int
    original_filename: str
    file_size: int
    sha256: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    template_unchanged: bool = False
    message: Optional[str] = None
    
    class Config:
        from_attributes = True

class EbayTemplateParseSummary(BaseModel):
    template_id: int
    fields_inserted: int
    values_inserted: int
    defaults_applied: int
    values_ignored_not_in_template: int
    defaults_ignored_not_in_template: int
    sheet_names: List[str]

# --- New Schemas for Field Access ---

class EbayFieldValueResponse(BaseModel):
    id: int
    value: str
    
    class Config:
        from_attributes = True

# Alias for clarity in delete operations
EbayValidValueDetailed = EbayFieldValueResponse

class EbayFieldResponse(BaseModel):
    id: int
    ebay_template_id: int
    field_name: str
    display_name: Optional[str] = None
    required: bool
    is_asset_managed: bool = False
    order_index: Optional[int] = None
    selected_value: Optional[str] = None
    custom_value: Optional[str] = None
    parsed_default_value: Optional[str] = None
    parent_selected_value: Optional[str] = None
    parent_custom_value: Optional[str] = None
    variation_selected_value: Optional[str] = None
    variation_custom_value: Optional[str] = None
    row_scope: Optional[str] = None
    
    # We map 'valid_values' from DB model to 'allowed_values' list of strings here.
    # But since nomenclature differs (valid_values vs allowed_values), we need to alias or validator.
    # The user asked for "allowed_values: List[str]".
    # The DB model has relationship "valid_values".
    allowed_values: List[str] = []
    # Detailed version with IDs for delete operations
    allowed_values_detailed: List[EbayValidValueDetailed] = []

    @field_validator('allowed_values', mode='before')
    def map_valid_values(cls, v):
        """
        Handle both cases:
        1. ORM objects with .value attribute (when using from_attributes)
        2. Already-processed list of strings (when API manually constructs)
        """
        if not v:
            return []
        
        # If already strings, return as-is
        if isinstance(v, list) and v and isinstance(v[0], str):
            return v
            
        # Otherwise, extract .value from ORM objects
        return [item.value for item in v if hasattr(item, 'value')]

    # HACK: Because source is "valid_values" but target is "allowed_values",
    # we need to tell Pydantic to look at "valid_values" if "allowed_values" is missing?
    # Or we can use Field(alias='valid_values')?
    # But alias is for input/serialization key.
    # We can use a root_validator or pre-validator on the whole model, or just rely on API manual mapping.
    # Manual mapping in API is safer. 
    # BUT "from_attributes=True" is requested.
    # So I will use Field(validation_alias='valid_values') 
    # But wait, Pydantic v2 uses `validation_alias`.
    
    # Let's try to be simple: the API function will construct this Pydantic object, 
    # or we trust 'from_attributes' with an aliased field.
    
    # Actually, simpler approach: 
    # Define `valid_values` in schema to match ORM, then `allowed_values` as computed field? 
    # But response shape must match requirements "allowed_values".
    
    # I'll stick to manual mapping in the route or a generic validator that tolerates missing source.
    # Let's add `class Config` and see.
    
    class Config:
        from_attributes = True

class EbayTemplateFieldsResponse(BaseModel):
    template_id: int
    fields: List[EbayFieldResponse]


class EbayFieldEquipmentTypeContentResponse(BaseModel):
    id: int
    ebay_field_id: int
    equipment_type_id: Optional[int] = None
    html_value: str
    is_default_fallback: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EbayFieldEquipmentTypeContentUpsertRequest(BaseModel):
    equipment_type_id: Optional[int] = None
    html_value: str
    is_default_fallback: Optional[bool] = None


class EbayFieldEquipmentTypeImagePatternResponse(BaseModel):
    id: int
    ebay_field_id: int
    equipment_type_id: Optional[int] = None
    parent_pattern: str
    variation_pattern: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class EbayFieldEquipmentTypeImagePatternUpsertRequest(BaseModel):
    equipment_type_id: Optional[int] = None
    parent_pattern: str
    variation_pattern: str


class TemplateFieldAssetResponse(BaseModel):
    id: int
    template_field_id: int
    asset_type: str
    name: str
    value: str
    is_default_fallback: bool = False
    equipment_type_ids: List[int] = []
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TemplateFieldAssetCreateRequest(BaseModel):
    asset_type: str
    name: Optional[str] = None
    value: str
    is_default_fallback: bool = False
    equipment_type_ids: List[int] = []


class TemplateFieldAssetUpdateRequest(BaseModel):
    name: Optional[str] = None
    value: str
    is_default_fallback: bool = False
    equipment_type_ids: List[int] = []


class EbayFieldUpdateRequest(BaseModel):
    """
    Request schema for updating eBay field properties.
    All fields are optional - only provided fields will be updated.
    """
    required: Optional[bool] = None
    selected_value: Optional[str] = None
    custom_value: Optional[str] = None
    parent_selected_value: Optional[str] = None
    parent_custom_value: Optional[str] = None
    variation_selected_value: Optional[str] = None
    variation_custom_value: Optional[str] = None
    row_scope: Optional[str] = None

class EbayValidValueCreateRequest(BaseModel):
    """
    Request schema for adding a valid value to an eBay field.
    """
    value: str

class EbayTemplatePreviewResponse(BaseModel):
    """
    Response schema for eBay template preview grid.
    """
    template_id: int
    original_filename: str
    sheet_name: str
    max_row: int
    max_column: int
    preview_row_count: int
    preview_column_count: int
    grid: List[List[str]]

class EbayTemplateIntegrityResponse(BaseModel):
    """
    Response schema for eBay template file integrity information.
    """
    template_id: int
    original_filename: str
    file_size: int
    sha256: Optional[str] = None
    uploaded_at: Optional[str] = None

class EbayTemplateVerificationResponse(BaseModel):
    """
    Response schema for eBay template file verification.
    """
    template_id: int
    status: str  # "match", "mismatch", "missing", "unknown"
    stored_sha256: Optional[str] = None
    stored_file_size: Optional[int] = None
    computed_sha256: Optional[str] = None
    computed_file_size: Optional[int] = None
    verified_at: str


# --- Reverb Template Schemas ---

class ReverbTemplateResponse(BaseModel):
    id: int
    display_name: Optional[str] = None
    original_filename: str
    file_size: int
    sha256: Optional[str] = None
    uploaded_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class ReverbTemplateParseSummary(BaseModel):
    template_id: int
    fields_inserted: int
    values_inserted: int
    defaults_applied: int
    values_ignored_not_in_template: int
    defaults_ignored_not_in_template: int
    # Reverb templates are CSV, so no "sheets", but keeping structure similar
    sheet_names: List[str] = []

class ReverbFieldValueResponse(BaseModel):
    id: int
    value: str
    
    class Config:
        from_attributes = True

# Alias for clarity 
ReverbValidValueDetailed = ReverbFieldValueResponse

class ReverbFieldResponse(BaseModel):
    id: int
    reverb_template_id: int
    field_name: str
    display_name: Optional[str] = None
    required: bool
    order_index: Optional[int] = None
    selected_value: Optional[str] = None
    custom_value: Optional[str] = None
    
    allowed_values: List[str] = []
    allowed_values_detailed: List[ReverbValidValueDetailed] = []
    
    # We will need to use a forward reference or loose type if Response is defined after
    # But Response is defined AFTER. I need to move ReverbFieldOverrideResponse UP or use strict strings?
    # Pydantic handles recursive if configured.
    # Actually, I'll just put Any for now or move the class up. Moving up is cleaner.
    # But updating file content via replace is hard for reordering.
    # I'll just use "overrides: List['ReverbFieldOverrideResponse'] = []" and keep it where it is.
    overrides: List['ReverbFieldOverrideResponse'] = []

    @field_validator('allowed_values', mode='before')
    def map_valid_values(cls, v):
        if not v:
            return []
        if isinstance(v, list) and v and isinstance(v[0], str):
            return v
        return [item.value for item in v if hasattr(item, 'value')]

    class Config:
        from_attributes = True

class ReverbTemplateFieldsResponse(BaseModel):
    template_id: int
    fields: List[ReverbFieldResponse]

class ReverbFieldUpdateRequest(BaseModel):
    required: Optional[bool] = None
    selected_value: Optional[str] = None
    custom_value: Optional[str] = None

class ReverbValidValueCreateRequest(BaseModel):
    value: str

class ReverbTemplatePreviewResponse(BaseModel):
    template_id: int
    original_filename: str
    # Reverb is CSV, so sheet_name might be "csv" or empty
    sheet_name: str
    max_row: int
    max_column: int
    preview_row_count: int
    preview_column_count: int
    grid: List[List[str]]


class ReverbTemplateUpdateRequest(BaseModel):
    display_name: str

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        cleaned = str(value or "").strip()
        if not cleaned:
            raise ValueError("display_name cannot be empty")
        return cleaned

class ReverbFieldOverrideResponse(BaseModel):
    id: int
    equipment_type_id: int
    reverb_field_id: int
    default_value: Optional[str] = None
    
    class Config:
        from_attributes = True

class ReverbFieldOverrideCreateRequest(BaseModel):
    equipment_type_id: int
    # reverb_field_id is passed via URL path
    default_value: Optional[str] = None
