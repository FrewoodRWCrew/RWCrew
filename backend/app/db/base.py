# Alembic (our database migration tool) and our test setup both need one
# place that imports every single database model. Just importing this file
# is enough to make sure SQLAlchemy knows about every table we've defined,
# without any of the code that uses this file needing to know the exact
# list of models.

from app.core.database import Base  # noqa: F401  (re-exported for convenience)
from app.db.models.module import Module  # noqa: F401
from app.db.models.module_role import ModuleRole  # noqa: F401
from app.db.models.refresh_token import RefreshToken  # noqa: F401
from app.db.models.season import Season  # noqa: F401
from app.db.models.user import User  # noqa: F401
from app.db.models.user_module_access import UserModuleAccess  # noqa: F401
