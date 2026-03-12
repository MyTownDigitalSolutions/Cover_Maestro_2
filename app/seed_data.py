from app.database import SessionLocal, engine, Base
from app.models.core import (
    Manufacturer, Series, EquipmentType, Model, Material,
    MaterialColourSurcharge, Supplier, PricingOption, ShippingRate
)
from app.models.templates import EquipmentTypeProductType
from app.models.enums import HandleLocation, AngleType, Carrier

def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    try:
        if db.query(EquipmentType).count() == 0:
            equipment_types = [
                EquipmentType(name="Guitar Amplifier"),
                EquipmentType(name="Bass Amplifier"),
                EquipmentType(name="Keyboard Amplifier"),
                EquipmentType(name="Speaker Cabinet"),
                EquipmentType(name="Combo Amp"),
                EquipmentType(name="Head Unit"),
                EquipmentType(name="Pedalboard"),
                EquipmentType(name="Mixer"),
            ]
            db.add_all(equipment_types)
            db.commit()
        
        if db.query(Material).count() == 0:
            materials = [
                Material(
                    name="Waterproof Nylon",
                    base_color="Black",
                    linear_yard_width=54,
                    weight_per_linear_yard=8.0,
                ),
                Material(
                    name="Waterproof Nylon + Padding",
                    base_color="Black",
                    linear_yard_width=54,
                    weight_per_linear_yard=12.8,
                ),
                Material(
                    name="Heavy Duty Canvas",
                    base_color="Tan",
                    linear_yard_width=60,
                    weight_per_linear_yard=11.2,
                ),
                Material(
                    name="Vinyl Cover",
                    base_color="Black",
                    linear_yard_width=54,
                    weight_per_linear_yard=6.4,
                ),
            ]
            db.add_all(materials)
            db.commit()
            
            waterproof = db.query(Material).filter(Material.name == "Waterproof Nylon").first()
            if waterproof:
                surcharges = [
                    MaterialColourSurcharge(material_id=waterproof.id, colour="Red", surcharge=2.00),
                    MaterialColourSurcharge(material_id=waterproof.id, colour="Blue", surcharge=2.00),
                    MaterialColourSurcharge(material_id=waterproof.id, colour="Green", surcharge=2.50),
                    MaterialColourSurcharge(material_id=waterproof.id, colour="White", surcharge=3.00),
                ]
                db.add_all(surcharges)
                db.commit()
        
        if db.query(PricingOption).count() == 0:
            pricing_options = [
                PricingOption(name="handle_zipper", price=8.00),
                PricingOption(name="two_in_one_pocket", price=12.00),
                PricingOption(name="music_rest_zipper", price=10.00),
            ]
            db.add_all(pricing_options)
            db.commit()
        
        if db.query(ShippingRate).count() == 0:
            zones = ["1", "2", "3", "4", "5"]
            base_rates = {
                "1": 7.50, "2": 8.50, "3": 9.50, "4": 11.00, "5": 13.00
            }
            shipping_rates = []
            for zone in zones:
                base = base_rates[zone]
                shipping_rates.extend([
                    ShippingRate(carrier=Carrier.USPS, min_weight=0, max_weight=1, zone=zone, rate=base, surcharge=0),
                    ShippingRate(carrier=Carrier.USPS, min_weight=1, max_weight=3, zone=zone, rate=base + 2, surcharge=0),
                    ShippingRate(carrier=Carrier.USPS, min_weight=3, max_weight=5, zone=zone, rate=base + 4, surcharge=0),
                    ShippingRate(carrier=Carrier.USPS, min_weight=5, max_weight=10, zone=zone, rate=base + 7, surcharge=0),
                    ShippingRate(carrier=Carrier.USPS, min_weight=10, max_weight=20, zone=zone, rate=base + 12, surcharge=0),
                ])
            db.add_all(shipping_rates)
            db.commit()
        
        if db.query(Manufacturer).count() == 0:
            manufacturers = [
                Manufacturer(name="Fender"),
                Manufacturer(name="Marshall"),
                Manufacturer(name="Vox"),
                Manufacturer(name="Orange"),
                Manufacturer(name="Mesa Boogie"),
            ]
            db.add_all(manufacturers)
            db.commit()
            
            fender = db.query(Manufacturer).filter(Manufacturer.name == "Fender").first()
            marshall = db.query(Manufacturer).filter(Manufacturer.name == "Marshall").first()
            
            if fender:
                fender_series = [
                    Series(name="Hot Rod", manufacturer_id=fender.id),
                    Series(name="Blues", manufacturer_id=fender.id),
                    Series(name="Twin", manufacturer_id=fender.id),
                ]
                db.add_all(fender_series)
            
            if marshall:
                marshall_series = [
                    Series(name="JCM", manufacturer_id=marshall.id),
                    Series(name="DSL", manufacturer_id=marshall.id),
                    Series(name="Origin", manufacturer_id=marshall.id),
                ]
                db.add_all(marshall_series)
            db.commit()
            
            guitar_amp = db.query(EquipmentType).filter(EquipmentType.name == "Guitar Amplifier").first()
            hot_rod = db.query(Series).filter(Series.name == "Hot Rod").first()
            
            if guitar_amp and hot_rod:
                sample_models = [
                    Model(
                        name="Hot Rod Deluxe",
                        series_id=hot_rod.id,
                        equipment_type_id=guitar_amp.id,
                        width=24.5,
                        depth=10.5,
                        height=17.5,
                        handle_location=HandleLocation.TOP_AMP_HANDLE,
                        angle_type=AngleType.TOP_ANGLE
                    ),
                    Model(
                        name="Hot Rod DeVille 212",
                        series_id=hot_rod.id,
                        equipment_type_id=guitar_amp.id,
                        width=26.5,
                        depth=10.5,
                        height=20.5,
                        handle_location=HandleLocation.TOP_AMP_HANDLE,
                        angle_type=AngleType.TOP_ANGLE
                    ),
                ]
                db.add_all(sample_models)
                db.commit()
        
        if db.query(Supplier).count() == 0:
            suppliers = [
                Supplier(name="Fabric World"),
                Supplier(name="Industrial Textiles Co"),
                Supplier(name="Quality Fabrics Inc"),
            ]
            db.add_all(suppliers)
            db.commit()
        
        print("Database seeded successfully!")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
