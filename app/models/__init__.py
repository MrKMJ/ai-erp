"""Import every model module so SQLAlchemy mappers are registered."""
from app.models import (  # noqa: F401
    accounting,
    ai,
    audit,
    inventory,
    manufacturing,
    master,
    purchasing,
    rbac,
    sales,
    sequence,
    tenant,
    user,
    workflow,
)
