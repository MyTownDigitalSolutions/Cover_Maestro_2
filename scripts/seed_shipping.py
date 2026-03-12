import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
# Import modules to ensure all models are registered
import app.models.core
import app.models.templates

from app.models.core import ShippingRateCard, ShippingRateTier, ShippingZoneRate, MarketplaceShippingProfile

def seed_shipping():
    db = SessionLocal()
    try:
        # 1. Rate Card
        card = db.query(ShippingRateCard).filter(ShippingRateCard.name == "Standard USPS").first()
        if not card:
            card = ShippingRateCard(
                carrier="USPS",
                name="Standard USPS",
                effective_date=datetime.utcnow()
            )
            db.add(card)
            db.flush()
            print("Created Rate Card: Standard USPS")
        else:
            print("Rate Card exists: Standard USPS")

        # 2. Tiers (0-10 lbs coverage)
        # Tier 1: 0 - 160oz (10 lbs)
        tier1 = db.query(ShippingRateTier).filter(
            ShippingRateTier.rate_card_id == card.id,
            ShippingRateTier.min_oz == 0
        ).first()
        
        if not tier1:
            tier1 = ShippingRateTier(
                rate_card_id=card.id,
                min_oz=0,
                max_oz=16000, # 1000 lbs coverage to be safe
                label="Tier 1"
            )
            db.add(tier1)
            db.flush()
            print("Created Tier 1 (0-1000 lbs)")
        
        # 3. Zone Rates (Zone 1 - 8)
        # Assuming Zone 1 is requested.
        for z in range(1, 9):
            rate = db.query(ShippingZoneRate).filter(
                ShippingZoneRate.tier_id == tier1.id,
                ShippingZoneRate.zone == z
            ).first()
            if not rate:
                rate = ShippingZoneRate(
                    tier_id=tier1.id,
                    zone=z,
                    rate_cents=500 + (z * 100) # Dummy rates: $6, $7, ...
                )
                db.add(rate)
                print(f"Created Rate for Zone {z}")
        
        # 4. Marketplace Profile
        profile = db.query(MarketplaceShippingProfile).filter(
            MarketplaceShippingProfile.marketplace == "amazon"
        ).first()
        
        if not profile:
            profile = MarketplaceShippingProfile(
                marketplace="amazon",
                rate_card_id=card.id,
                pricing_zone=1, # Default zone for calc
                effective_date=datetime.utcnow()
            )
            db.add(profile)
            print("Created Marketplace Profile for Amazon")
        else:
            print("Marketplace Profile for Amazon exists (using Zone 1?)")
            if profile.pricing_zone != 1:
                print(f"Warning: Profile uses Zone {profile.pricing_zone}, ensure rates exist.")
            # Ensure connection
            if profile.rate_card_id != card.id:
                 profile.rate_card_id = card.id
                 print("Updated Amazon Profile to point to Standard USPS card")

        db.commit()
        print("Shipping Seed Complete.")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_shipping()
