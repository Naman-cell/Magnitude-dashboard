from fastapi import APIRouter
from app.api.v1.endpoints.container_registry import router as ecr_router
from app.api.v1.endpoints.k8s import router as eks_router

api_router = APIRouter()

api_router.include_router(ecr_router, prefix="/api/v1")
api_router.include_router(eks_router, prefix="/api/v1") 