"""Bootstrap endpoint -- initialize default data for first-time setup."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user, get_db
from app.core.database import Database
from app.services.investment_policy_service import InvestmentPolicyService

router = APIRouter(prefix="/bootstrap", tags=["bootstrap"])


@router.post("")
def bootstrap(
    _user: str | None = Depends(get_current_user),
    db: Database = Depends(get_db),
) -> dict:
    """Initialize default data: seed investment policies from thesis.

    Safe to call multiple times -- existing policies are skipped unless
    force=true.
    """
    svc = InvestmentPolicyService(db)
    created, skipped = svc.seed_defaults(force=False)
    return {
        "investment_policies": {
            "created": len(created),
            "skipped": len(skipped),
        },
        "message": f"Bootstrap complete. Created {len(created)} policies, skipped {len(skipped)}.",
    }
