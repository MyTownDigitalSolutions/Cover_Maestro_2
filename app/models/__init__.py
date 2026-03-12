# Database models
#
# Import both core and templates modules to ensure SQLAlchemy can resolve
# circular string-based relationship references during mapper configuration.
# (e.g., EquipmentType references "AmazonCustomizationTemplate" and vice versa)

from . import core
from . import templates
