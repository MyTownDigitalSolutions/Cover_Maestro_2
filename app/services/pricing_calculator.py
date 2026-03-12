from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional, List, Dict
import logging

from app.models.core import (
    Model, Material, MaterialRoleAssignment, MarketplaceShippingProfile,
    ShippingRateCard, ShippingRateTier, ShippingZoneRate, LaborSetting,
    VariantProfitSetting, MarketplaceFeeRate, ModelPricingSnapshot, ModelPricingHistory,
    ShippingDefaultSetting
)
from app.models.enums import Marketplace

logger = logging.getLogger(__name__)

# Constants
WASTE_PERCENTAGE = 0.05

class PricingConfigError(ValueError):
    """Raised when pricing configuration (settings, defaults, profiles) is invalid or incomplete."""
    pass

class PricingCalculator:
    def __init__(self, db: Session):
        self.db = db
        self._shipping_defaults: Optional[ShippingDefaultSetting] = None
        self._fixed_cell_rate_cents: Optional[int] = None
        self._fixed_cell_lookup_done: bool = False
        
    def _get_shipping_defaults(self) -> ShippingDefaultSetting:
        if not self._shipping_defaults:
            defaults = self.db.query(ShippingDefaultSetting).first()
            if not defaults:
                # Fallback in memory if row missing (though API creates it)
                defaults = ShippingDefaultSetting() 
            self._shipping_defaults = defaults
        return self._shipping_defaults

    def _get_fixed_cell_rate(self) -> int:
        """Lazily fetches the fixed cell rate from the assumed tier+zone."""
        if self._fixed_cell_lookup_done:
             if self._fixed_cell_rate_cents is None:
                 raise PricingConfigError("Fixed Cell mode is active, but no rate could be found.")
             return self._fixed_cell_rate_cents
             
        defaults = self._get_shipping_defaults()
        if not defaults.assumed_rate_card_id or \
           not defaults.assumed_tier_id or \
           not defaults.assumed_zone_code:
            raise PricingConfigError("Shipping mode is 'fixed_cell' but Assumed Shipping Settings are incomplete.")
            
        # Fetch rate
        
        from app.models.core import ShippingZone
        
        zone_obj = self.db.query(ShippingZone).filter(ShippingZone.code == defaults.assumed_zone_code).first()
        if not zone_obj:
            raise PricingConfigError(f"Assumed zone code '{defaults.assumed_zone_code}' not found in ShippingZone table.")
            
        rate = self.db.query(ShippingZoneRate).filter(
            ShippingZoneRate.tier_id == defaults.assumed_tier_id,
            ShippingZoneRate.zone == zone_obj.id
        ).first()

        self._fixed_cell_lookup_done = True

        if not rate:
            raise PricingConfigError(f"No rate found for Assumed Tier {defaults.assumed_tier_id} + Zone {defaults.assumed_zone_code} (ID {zone_obj.id}).")
        
        self._fixed_cell_rate_cents = rate.rate_cents
        return self._fixed_cell_rate_cents

    def calculate_model_prices(self, model_id: int, marketplace: str = "DEFAULT"):
        """
        Calculate and persist pricing snapshots for all 4 variants of a model for a specific marketplace.
        """
        logger.info(f"recalc_baselines start model_id={model_id} marketplace={marketplace}")
        model = self.db.query(Model).filter(Model.id == model_id).first()
        if not model:
            raise ValueError(f"Model ID {model_id} not found")

        # 1. Resolve Configuration
        # ----------------------------------------------------
        labor_settings = self.db.query(LaborSetting).first()
        if not labor_settings:
            raise ValueError("Labor Settings not configured.")

        fee_rate_obj = self.db.query(MarketplaceFeeRate).filter(MarketplaceFeeRate.marketplace == marketplace).first()
        if not fee_rate_obj:
            raise ValueError(f"Fee rate not configured for marketplace: {marketplace}")
        fee_rate = fee_rate_obj.fee_rate

        # Shipping Profile Rules:
        # - Reverb uses global Shipping Defaults (no marketplace profile required)
        # - eBay should behave EXACTLY like Reverb for now (use Shipping Defaults; no profile required)
        # - Other marketplaces (Amazon/Etsy/etc.) require a marketplace shipping profile for calculated mode
        shipping_profile = self._get_shipping_profile(marketplace)

        if marketplace.lower() in ("reverb", "ebay"):
            shipping_profile = None
        elif not shipping_profile:
            # Fallback to DEFAULT profile when marketplace-specific profile is absent.
            shipping_profile = self._get_shipping_profile("DEFAULT")
            if not shipping_profile:
                raise ValueError(f"Shipping profile not configured for marketplace: {marketplace}")

        # 2. Resolve Materials (As of Now)
        # ----------------------------------------------------
        materials_map = self._resolve_materials()
        
        # 3. Calculate Area
        # ----------------------------------------------------
        if not model.surface_area_sq_in or model.surface_area_sq_in <= 0:
             raise ValueError("Pricing cannot be calculated: model.surface_area_sq_in is missing or invalid.")
             
        area_sq_in = model.surface_area_sq_in

        # 4. Iterate Variants and Calculate
        # ----------------------------------------------------
        variants = [
            "choice_no_padding", "choice_padded",
            "premium_no_padding", "premium_padded"
        ]
        
        shipping_defaults = self._get_shipping_defaults()
        current_shipping_version = shipping_defaults.shipping_settings_version
        
        for variant_key in variants:
            logger.info(f"variant attempt key={variant_key} model_id={model_id}")
            try:
                self._calculate_single_variant(
                    model, variant_key, marketplace, area_sq_in,
                    materials_map, labor_settings, fee_rate, shipping_profile,
                    current_shipping_version
                )
            except Exception as e:
                logger.error(f"variant fail key={variant_key} model_id={model_id} error={str(e)}")
                raise e

    def _calculate_single_variant(
        self, model: Model, variant_key: str, marketplace: str, area_sq_in: float,
        materials_map: Dict[str, Material], labor_settings: LaborSetting, 
        fee_rate: float, shipping_profile: MarketplaceShippingProfile,
        shipping_version: Optional[int]
    ):
        # A. Determine Components based on variant key
        # ------------------------------------------------
        is_premium = "premium" in variant_key
        has_padding = "padded" in variant_key or ("padding" in variant_key and "no_padding" not in variant_key)

        main_fabric_role = "PREMIUM_SYNTHETIC_LEATHER" if is_premium else "CHOICE_WATERPROOF_FABRIC"
        main_material = materials_map.get(self._normalize_role_key(main_fabric_role))
        if not main_material:
            raise ValueError(f"Missing active material assignment for role: {main_fabric_role}")

        padding_material = None
        if has_padding:
            padding_material = materials_map.get(self._normalize_role_key("PADDING"))
            if not padding_material:
                raise ValueError("Missing active material assignment for role: PADDING")

        # B. Calculate Material Cost & Weight
        # ------------------------------------------------
        material_cost_cents = self._get_material_cost_cents(main_material, area_sq_in)
        weight_oz = self._get_material_weight_oz(main_material, area_sq_in)
        
        if padding_material:
            material_cost_cents += self._get_material_cost_cents(padding_material, area_sq_in)
            weight_oz += self._get_material_weight_oz(padding_material, area_sq_in)

        # C. Calculate Labor Cost
        # ------------------------------------------------
        minutes = labor_settings.minutes_with_padding if has_padding else labor_settings.minutes_no_padding
        labor_cost_cents = int((minutes / 60.0) * labor_settings.hourly_rate_cents)

        # D. Calculate Shipping Cost
        # ------------------------------------------------
        shipping_cost_cents = self._get_shipping_cost_cents(shipping_profile, weight_oz)

        # E. Totals & Pricing
        # ------------------------------------------------
        raw_cost_cents = material_cost_cents + labor_cost_cents + shipping_cost_cents
        
        profit_setting = self.db.query(VariantProfitSetting).filter(VariantProfitSetting.variant_key == variant_key).first()
        if not profit_setting:
            raise ValueError(f"Profit config missing for variant: {variant_key}")
        profit_cents = profit_setting.profit_cents

        if fee_rate >= 1.0:
            raise ValueError("Fee rate cannot be 100% or more")
            
        target_retail_cents_float = (raw_cost_cents + profit_cents) / (1.0 - fee_rate)
        
        # Round up to nearest .95
        import math
        target_dollars = target_retail_cents_float / 100.0
        floor_dollars = math.floor(target_dollars)
        candidate = floor_dollars + 0.95
        
        if candidate >= target_dollars:
            final_dollars = candidate
        else:
            final_dollars = floor_dollars + 1.95
            
        retail_price_cents = int(round(final_dollars * 100))
        
        marketplace_fee_cents = int(round(retail_price_cents * fee_rate))
        base_cost_cents = retail_price_cents - profit_cents

        # Calculate metadata
        labor_minutes = int(minutes)
        labor_rate = labor_settings.hourly_rate_cents
        mp_fee_rate = fee_rate
        
        material_rate = None

        # F. Persist
        # ------------------------------------------------
        self._save_snapshot(
            model.id, marketplace, variant_key,
            raw_cost_cents, base_cost_cents, retail_price_cents,
            marketplace_fee_cents, profit_cents,
            material_cost_cents, shipping_cost_cents, labor_cost_cents,
            weight_oz, shipping_version,
            # Metadata
            area_sq_in, material_rate, labor_minutes, labor_rate, mp_fee_rate
        )

    def _save_snapshot(
        self, model_id: int, marketplace: str, variant_key: str,
        raw: int, base: int, retail: int, mp_fee: int, profit: int,
        mat: int, ship: int, labor: int, weight: float, shipping_version: Optional[int],
        # Metadata
        surface_area_sq_in: float, material_cost_per_sq_in_cents: int,
        labor_minutes: int, labor_rate_cents_per_hour: int, marketplace_fee_rate: float
    ):
        existing = self.db.query(ModelPricingSnapshot).filter(
            ModelPricingSnapshot.model_id == model_id,
            ModelPricingSnapshot.marketplace == marketplace,
            ModelPricingSnapshot.variant_key == variant_key
        ).first()

        should_insert_history = False
        
        if existing:
            has_changed = (
                existing.raw_cost_cents != raw or
                existing.base_cost_cents != base or
                existing.retail_price_cents != retail or
                existing.marketplace_fee_cents != mp_fee or
                existing.profit_cents != profit or
                existing.material_cost_cents != mat or
                existing.shipping_cost_cents != ship or
                existing.labor_cost_cents != labor or
                abs(existing.weight_oz - weight) > 0.0001 or
                existing.shipping_settings_version_used != shipping_version or
                (existing.surface_area_sq_in is None or abs(existing.surface_area_sq_in - surface_area_sq_in) > 0.0001) or
                existing.material_cost_per_sq_in_cents != material_cost_per_sq_in_cents or
                existing.labor_minutes != labor_minutes or
                existing.labor_rate_cents_per_hour != labor_rate_cents_per_hour or
                (existing.marketplace_fee_rate is None or abs(existing.marketplace_fee_rate - marketplace_fee_rate) > 0.000001)
            )
            
            if has_changed:
                existing.raw_cost_cents = raw
                existing.base_cost_cents = base
                existing.retail_price_cents = retail
                existing.marketplace_fee_cents = mp_fee
                existing.profit_cents = profit
                existing.material_cost_cents = mat
                existing.shipping_cost_cents = ship
                existing.labor_cost_cents = labor
                existing.weight_oz = weight
                existing.shipping_settings_version_used = shipping_version
                
                existing.surface_area_sq_in = surface_area_sq_in
                existing.material_cost_per_sq_in_cents = material_cost_per_sq_in_cents
                existing.labor_minutes = labor_minutes
                existing.labor_rate_cents_per_hour = labor_rate_cents_per_hour
                existing.marketplace_fee_rate = marketplace_fee_rate
                
                existing.calculated_at = datetime.utcnow()
                should_insert_history = True
        else:
            new_snap = ModelPricingSnapshot(
                model_id=model_id,
                marketplace=marketplace,
                variant_key=variant_key,
                raw_cost_cents=raw,
                base_cost_cents=base,
                retail_price_cents=retail,
                marketplace_fee_cents=mp_fee,
                profit_cents=profit,
                material_cost_cents=mat,
                shipping_cost_cents=ship,
                labor_cost_cents=labor,
                weight_oz=weight,
                shipping_settings_version_used=shipping_version,
                calculated_at=datetime.utcnow(),
                surface_area_sq_in=surface_area_sq_in,
                material_cost_per_sq_in_cents=material_cost_per_sq_in_cents,
                labor_minutes=labor_minutes,
                labor_rate_cents_per_hour=labor_rate_cents_per_hour,
                marketplace_fee_rate=marketplace_fee_rate
            )
            self.db.add(new_snap)
            should_insert_history = True
            
        if should_insert_history:
            history_row = ModelPricingHistory(
                model_id=model_id,
                marketplace=marketplace,
                variant_key=variant_key,
                raw_cost_cents=raw,
                base_cost_cents=base,
                retail_price_cents=retail,
                marketplace_fee_cents=mp_fee,
                profit_cents=profit,
                material_cost_cents=mat,
                shipping_cost_cents=ship,
                labor_cost_cents=labor,
                weight_oz=weight,
                calculated_at=datetime.utcnow(),
                reason="recalculate",
                surface_area_sq_in=surface_area_sq_in,
                material_cost_per_sq_in_cents=material_cost_per_sq_in_cents,
                labor_minutes=labor_minutes,
                labor_rate_cents_per_hour=labor_rate_cents_per_hour,
                marketplace_fee_rate=marketplace_fee_rate
            )
            self.db.add(history_row)
            
        logger.info(f"variant success key={variant_key} model_id={model_id}")
        
        self.db.flush()

    def _resolve_materials(self) -> Dict[str, Material]:
        """Returns map of Role -> Material object for all currently active roles."""
        now = datetime.utcnow()
        assignments = self.db.query(MaterialRoleAssignment).filter(
            MaterialRoleAssignment.effective_date <= now,
            (MaterialRoleAssignment.end_date == None) | (MaterialRoleAssignment.end_date > now)
        ).all()
        
        result = {}
        for a in assignments:
            result[self._normalize_role_key(a.role)] = a.material
        return result

    def _normalize_role_key(self, role: str) -> str:
        return " ".join(str(role or "").replace("_", " ").upper().split())

    def _get_shipping_profile(self, marketplace: str) -> Optional[MarketplaceShippingProfile]:
        now = datetime.utcnow()
        return self.db.query(MarketplaceShippingProfile).filter(
            MarketplaceShippingProfile.marketplace == marketplace,
            MarketplaceShippingProfile.effective_date <= now,
            (MarketplaceShippingProfile.end_date == None) | (MarketplaceShippingProfile.end_date > now)
        ).first()

    def _get_material_cost_cents(self, material: Material, area_sq_in: float) -> int:
        """Calculates material cost in cents for the given area."""
        from app.models.core import SupplierMaterial
        
        sup_mat = self.db.query(SupplierMaterial).filter(
            SupplierMaterial.material_id == material.id,
            SupplierMaterial.is_preferred == True
        ).first()
        
        if not sup_mat:
             raise ValueError(f"No preferred supplier found for material: {material.name}")
        
        if not material.linear_yard_width:
             raise ValueError(f"Material {material.name} missing linear yard width")

        qty = sup_mat.quantity_purchased or 0.0
        shipping = sup_mat.shipping_cost or 0.0
        shipping_per_unit = (shipping / qty) if qty > 0 else 0.0
        effective_unit_cost = sup_mat.unit_cost + shipping_per_unit
        area_per_unit = material.linear_yard_width * 36.0
        cost_per_sq_in = effective_unit_cost / area_per_unit

        total_cost_dollars = cost_per_sq_in * area_sq_in
        total_cost_cents = int(round(total_cost_dollars * 100))
        logger.info(
            "pricing_material_cost material=%s width=%s unit_cost=%s shipping_cost=%s qty=%s effective_unit=%s cost_per_sq_in=%s area_sq_in=%s total_cost_cents=%s",
            material.name,
            material.linear_yard_width,
            sup_mat.unit_cost,
            shipping,
            qty,
            effective_unit_cost,
            cost_per_sq_in,
            area_sq_in,
            total_cost_cents,
        )
        return total_cost_cents

    def _get_material_weight_oz(self, material: Material, area_sq_in: float) -> float:
        if material.weight_per_sq_in_oz is not None:
            return float(material.weight_per_sq_in_oz) * area_sq_in
        
        if material.weight_per_linear_yard and material.linear_yard_width:
             # Strict mode: do not infer; keep as-is.
             pass
        
        if material.weight_per_sq_in_oz is None:
             raise ValueError(f"Material {material.name} missing weight_per_sq_in_oz config")
             
        return float(material.weight_per_sq_in_oz) * area_sq_in

    def _get_shipping_cost_cents(self, profile: MarketplaceShippingProfile, weight_oz: float) -> int:
        defaults = self._get_shipping_defaults()
        
        # 1. Global Flat Rate Override (Highest Priority)
        if defaults.shipping_mode == "flat":
             return defaults.flat_shipping_cents
        
        # 2. Fixed Cell Mode (Assumed Matrix Cell)
        if defaults.shipping_mode == "fixed_cell":
             return self._get_fixed_cell_rate()
             
        # 3. Calculated Mode (Profile Required)
        # However, for Reverb/eBay (where profile is forced to None), we MUST fallback to Fixed Cell Assumption.
        if profile is None:
             return self._get_fixed_cell_rate()
             
        # 4. Standard Calculated Profile Logic
        zone = profile.pricing_zone
        if not zone and defaults.default_zone_code:
            try:
                zone = int(defaults.default_zone_code)
            except ValueError:
                pass
            
        effective_zone = zone
        if effective_zone is None:
             raise ValueError("No pricing zone available (neither profile nor default)")

        tier = self.db.query(ShippingRateTier).filter(
            ShippingRateTier.rate_card_id == profile.rate_card_id,
            ShippingRateTier.max_oz >= weight_oz
        ).order_by(
            ShippingRateTier.max_oz.asc(),
            ShippingRateTier.id.asc()
        ).first()
        
        if not tier:
            raise ValueError(f"No shipping tier found for weight {weight_oz}oz on card {profile.rate_card_id} (weight exceeds max available tier)")
            
        rate = self.db.query(ShippingZoneRate).filter(
            ShippingZoneRate.tier_id == tier.id,
            ShippingZoneRate.zone == effective_zone
        ).first()
        
        if not rate:
            raise ValueError(f"No shipping rate found for Tier {tier.id} Zone {effective_zone}")
            
        return rate.rate_cents

    @staticmethod
    def is_snapshot_stale(snapshot: ModelPricingSnapshot, current_version: int) -> bool:
        if not snapshot.shipping_settings_version_used:
             return True
        return snapshot.shipping_settings_version_used != current_version
