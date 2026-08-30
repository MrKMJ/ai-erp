"""Import every model module so SQLAlchemy mappers are registered."""
from app.models import (  # noqa: F401
    accounting,
    ai,
    audit,
    inventory,
    master,
    purchasing,
    rbac,
    sales,
    tenant,
    user,
    workflow,
)
