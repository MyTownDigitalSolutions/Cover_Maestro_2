import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.getcwd())

import app.models.core
from sqlalchemy.orm import configure_mappers
configure_mappers()

from app.database import SessionLocal
from app.models.core import (
    MaterialRoleAssignment, Material, SupplierMaterial,
    ShippingRateCard, ShippingRateTier, ShippingZoneRate,
    MarketplaceShippingProfile, LaborSetting, MarketplaceFeeRate, VariantProfitSetting
)
from app.models.enums import Marketplace, Carrier

def seed_pricing_config():
    db = SessionLocal()
    try:
        print("Seeding Pricing Config...")
        
        # ... (Previous logic for settings/shipping is fine, skipping to roles)
        
        # 1. Labor Settings (Ensure it exists)
        if db.query(LaborSetting).count() == 0:
            db.add(LaborSetting(
                hourly_rate_cents=1700, 
                minutes_no_padding=35,
                minutes_with_padding=60
            ))

        # 2. Fee Rates
        fees = {"DEFAULT": 0.15, Marketplace.AMAZON.value: 0.15, Marketplace.EBAY.value: 0.13, Marketplace.REVERB.value: 0.10}
        for mp, rate in fees.items():
            if not db.query(MarketplaceFeeRate).filter(MarketplaceFeeRate.marketplace == mp).first():
                db.add(MarketplaceFeeRate(marketplace=mp, fee_rate=rate))

        # 3. Profits
        profits = {"choice_no_padding": 2000, "choice_with_padding": 2500, "premium_no_padding": 3000, "premium_with_padding": 3500}
        for key, cents in profits.items():
             if not db.query(VariantProfitSetting).filter(VariantProfitSetting.variant_key == key).first():
                 db.add(VariantProfitSetting(variant_key=key, profit_cents=cents))

        # 4. Shipping (As before)
        rate_card = db.query(ShippingRateCard).filter(ShippingRateCard.name == "USPS Ground Advantage 2024").first()
        if not rate_card:
            rate_card = ShippingRateCard(carrier=Carrier.USPS, name="USPS Ground Advantage 2024")
            db.add(rate_card)
            db.flush()
            # Add tiers (Simplified same as before)
            t1 = ShippingRateTier(rate_card_id=rate_card.id, min_oz=0, max_oz=16, label="Under 1lb")
            t2 = ShippingRateTier(rate_card_id=rate_card.id, min_oz=16, max_oz=80, label="1-5lbs")
            t3 = ShippingRateTier(rate_card_id=rate_card.id, min_oz=80, max_oz=3000, label="Heavy")
            db.add_all([t1, t2, t3])
            db.flush()
            db.add_all([
                ShippingZoneRate(rate_card_id=rate_card.id, tier_id=t1.id, zone=7, rate_cents=1000),
                ShippingZoneRate(rate_card_id=rate_card.id, tier_id=t2.id, zone=7, rate_cents=1500),
                ShippingZoneRate(rate_card_id=rate_card.id, tier_id=t3.id, zone=7, rate_cents=2500)
            ])
            
        if rate_card:
             if not db.query(MarketplaceShippingProfile).filter(MarketplaceShippingProfile.marketplace == "DEFAULT").first():
                 db.add(MarketplaceShippingProfile(marketplace="DEFAULT", rate_card_id=rate_card.id, pricing_zone=7))

        # 6. Explicit Role Assignments based on found materials
        print("  - Assigning Material Roles (Explicit Map)")
        role_map = {
            "CHOICE_WATERPROOF_FABRIC": "Cordura HP",
            "PREMIUM_SYNTHETIC_LEATHER": "Denali Automotive Vinyl",
            "PADDING": "Liberty Headliner" # Matches partial string
        }
        
        for role, material_name_part in role_map.items():
            existing = db.query(MaterialRoleAssignment).filter(MaterialRoleAssignment.role == role, MaterialRoleAssignment.end_date == None).first()
            if not existing:
                mat = db.query(Material).filter(Material.name.like(f"%{material_name_part}%")).first()
                if mat:
                    print(f"    Assigning {mat.name} to {role}")
                    db.add(MaterialRoleAssignment(role=role, material_id=mat.id))
                    
                    # Update metadata for calc
                    if not mat.weight_per_sq_in_oz:
                         mat.weight_per_sq_in_oz = 0.005 if "Padding" not in role else 0.002
                         mat.linear_yard_width = 60 if "Padding" not in role else 54
                    
                    sup_link = db.query(SupplierMaterial).filter(SupplierMaterial.material_id == mat.id).first()
                    if sup_link and not sup_link.is_preferred:
                        sup_link.is_preferred = True # Force preferred for calc
                else:
                    print(f"    WARNING: Material matching '{material_name_part}' not found for {role}")

        db.commit()
        print("Pricing Configuration Seeded Successfully.")

    except Exception as e:
        print(f"Error seeding: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_pricing_config()
