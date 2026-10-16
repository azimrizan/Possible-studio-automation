from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from ...db.session import get_db
from ...models.models import User, Tenant, WorkspaceMembership
from ...schemas.schemas import WorkspaceCreate, WorkspaceOut, MembershipCreate
from ..deps import get_current_user, require_role

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])

@router.post("/", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check if slug taken
    result = await db.execute(select(Tenant).where(Tenant.slug == data.slug))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Workspace slug already in use")

    new_tenant = Tenant(
        name=data.name,
        slug=data.slug,
        daily_budget_limit_cents=data.daily_budget_limit_cents or 100000,
    )
    db.add(new_tenant)
    await db.flush()

    membership = WorkspaceMembership(
        tenant_id=new_tenant.id,
        user_id=current_user.id,
        role="OWNER",
    )
    db.add(membership)
    await db.commit()
    await db.refresh(new_tenant)

    return WorkspaceOut(
        id=new_tenant.id,
        name=new_tenant.name,
        slug=new_tenant.slug,
        role="OWNER",
        daily_budget_limit_cents=new_tenant.daily_budget_limit_cents,
        created_at=new_tenant.created_at,
    )

@router.get("/", response_model=List[WorkspaceOut])
async def list_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Tenant, WorkspaceMembership.role)
        .join(WorkspaceMembership, WorkspaceMembership.tenant_id == Tenant.id)
        .where(WorkspaceMembership.user_id == current_user.id)
    )
    result = await db.execute(stmt)
    workspaces = []
    for tenant, role in result.all():
        workspaces.append(
            WorkspaceOut(
                id=tenant.id,
                name=tenant.name,
                slug=tenant.slug,
                role=role,
                daily_budget_limit_cents=tenant.daily_budget_limit_cents,
                created_at=tenant.created_at,
            )
        )
    return workspaces

@router.post("/{workspace_id}/members", status_code=status.HTTP_201_CREATED)
async def add_workspace_member(
    workspace_id: str,
    data: MembershipCreate,
    membership: WorkspaceMembership = Depends(require_role("OWNER")),
    db: AsyncSession = Depends(get_db),
):
    # Find user by email
    res = await db.execute(select(User).where(User.email == data.email))
    target_user = res.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User with this email not found")

    # Check if already a member
    mem_res = await db.execute(
        select(WorkspaceMembership).where(
            WorkspaceMembership.tenant_id == workspace_id,
            WorkspaceMembership.user_id == target_user.id,
        )
    )
    if mem_res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already a member of this workspace")

    new_member = WorkspaceMembership(
        tenant_id=workspace_id,
        user_id=target_user.id,
        role=data.role,
    )
    db.add(new_member)
    await db.commit()
    return {"status": "success", "user_id": target_user.id, "role": data.role}
