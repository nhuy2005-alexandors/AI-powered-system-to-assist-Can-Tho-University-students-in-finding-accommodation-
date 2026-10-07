"""Adapter for the repository's existing PostgreSQL/JWT authentication."""
from fastapi import Depends

from ...auth.deps import get_current_user
from ...auth.schemas import UserOut


def get_postgres_recommendation_user_id(user: UserOut = Depends(get_current_user)) -> str:
    # Keep account IDs distinct if another authentication provider is added.
    return f"postgres:{user.id}"
