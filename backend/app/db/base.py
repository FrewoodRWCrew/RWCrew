# Alembic (our database migration tool) and our test setup both need one
# place that imports every single database model. Just importing this file
# is enough to make sure SQLAlchemy knows about every table we've defined,
# without any of the code that uses this file needing to know the exact
# list of models.

from app.core.database import Base  # noqa: F401  (re-exported for convenience)
from app.db.models.masterdata_role import MasterDataRole  # noqa: F401
from app.db.models.masterdata_role_permission import MasterDataRolePermission  # noqa: F401
from app.db.models.masterdata_screen import MasterDataScreen  # noqa: F401
from app.db.models.masterdata_user_role import MasterDataUserRole  # noqa: F401
from app.db.models.module import Module  # noqa: F401
from app.db.models.module_role import ModuleRole  # noqa: F401
from app.db.models.product import Product  # noqa: F401
from app.db.models.product_category import ProductCategory  # noqa: F401
from app.db.models.product_limit import ProductLimit  # noqa: F401
from app.db.models.product_type import ProductType  # noqa: F401
from app.db.models.refresh_token import RefreshToken  # noqa: F401
from app.db.models.rfid_tag import RfidTag  # noqa: F401
from app.db.models.scanner import Scanner  # noqa: F401
from app.db.models.season import Season  # noqa: F401
from app.db.models.tag_header_data import TagHeaderData  # noqa: F401
from app.db.models.tag_line_data import TagLineData  # noqa: F401
from app.db.models.tagscan_role import TagscanRole  # noqa: F401
from app.db.models.tagscan_role_permission import TagscanRolePermission  # noqa: F401
from app.db.models.tagscan_screen import TagscanScreen  # noqa: F401
from app.db.models.tagscan_user_role import TagscanUserRole  # noqa: F401
from app.db.models.user import User  # noqa: F401
from app.db.models.user_module_access import UserModuleAccess  # noqa: F401
from app.db.models.warehouse import Warehouse  # noqa: F401
