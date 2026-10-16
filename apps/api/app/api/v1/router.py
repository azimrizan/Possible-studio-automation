from fastapi import APIRouter
from .auth import router as auth_router
from .workspaces import router as workspaces_router
from .approvals import router as approvals_router
from .brand_kit import router as brand_kit_router
from .campaigns import router as campaigns_router
from .briefs import router as briefs_router
from .creative import router as creative_router
from .reels import router as reels_router
from .review_gate import router as review_gate_router

api_router = APIRouter(prefix="/v1")
api_router.include_router(auth_router)
api_router.include_router(workspaces_router)
api_router.include_router(approvals_router)
api_router.include_router(brand_kit_router)
api_router.include_router(campaigns_router)
api_router.include_router(briefs_router)
api_router.include_router(creative_router)
api_router.include_router(reels_router)
api_router.include_router(review_gate_router)


