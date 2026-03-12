import enum

class HandleLocation(str, enum.Enum):
    TOP_AMP_HANDLE = "Top Amp Handle"
    SIDE_AMP_HANDLES = "Side Amp Handles"
    REAR_AMP_HANDLE = "Rear Amp Handle"
    NO_AMP_HANDLE = "No Amp Handle"
    TOP_AND_SIDE_AMP_HANDLES = "Top & Side Amp Handles"

class AngleType(str, enum.Enum):
    NO_ANGLE = "No Angle"
    TOP_ANGLE = "Top Angle"
    MID_ANGLE = "Mid Angle"
    FULL_ANGLE = "Full Angle"
    MIDCURVE = "Midcurve"
    FULLCURVE = "Fullcurve"

class Carrier(str, enum.Enum):
    USPS = "usps"
    UPS = "ups"
    FEDEX = "fedex"

class Marketplace(str, enum.Enum):
    AMAZON = "amazon"
    EBAY = "ebay"
    REVERB = "reverb"
    ETSY = "etsy"

class MaterialType(str, enum.Enum):
    FABRIC = "fabric"
    HARDWARE = "hardware"
    PACKAGING = "packaging"

class UnitOfMeasure(str, enum.Enum):
    YARD = "yard"
    EACH = "each"
    PACKAGE = "package"
    BOX = "box"
    SET = "set"

class OrderSource(str, enum.Enum):
    API_IMPORT = "api_import"
    MANUAL = "manual"

class NormalizedOrderStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    UNKNOWN = "unknown"
