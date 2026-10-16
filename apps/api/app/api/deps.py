from fastapi import Depends, HTTPException, Header, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from ..db.session import get_db
from ..core.security import decode_access_token
from ..models.models import User, WorkspaceMembership

security_scheme = HTTPBearer(auto_error=False)

ROLE_HIERARCHY = {
    "VIEWER": 1,
    "EDITOR": 2,
    "APPROVER": 3,
    "OWNER": 4,
}

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
        )
    
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token subject")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

async def get_tenant_context(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WorkspaceMembership:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header required")

    result = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.tenant_id == x_tenant_id,
            WorkspaceMembership.user_id == current_user.id,
        )
    )
    membership = result.scalar_one_or_none()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized for this workspace/tenant")
    return membership

def require_role(minimum_role: str):
    async def role_checker(
        membership: WorkspaceMembership = Depends(get_tenant_context),
    ) -> WorkspaceMembership:
        user_rank = ROLE_HIERARCHY.get(membership.role, 0)
        required_rank = ROLE_HIERARCHY.get(minimum_role, 0)
        if user_rank < required_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Action requires minimum role of '{minimum_role}', user has '{membership.role}'",
            )
        return membership
    return role_checker
