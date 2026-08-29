# This is Module 6's own router file. Right now it just uses the shared,
# generic module endpoints (see app/modules/common.py) for the "coming
# soon" placeholder page and role management. Once Module 6's real
# functionality is designed, its module-specific endpoints get added
# here, in this same file, keeping everything about Module 6 together.

from app.modules.common import create_module_router

router = create_module_router(module_key="module-6", module_label="Module 6")
