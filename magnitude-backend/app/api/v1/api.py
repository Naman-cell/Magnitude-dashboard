from fastapi import APIRouter
from app.api.v1.endpoints.ecr import ecr
from app.api.v1.endpoints.eks import eks

api_router = APIRouter()

api_router.include_router(ecr.router, prefix="/api/v1")
api_router.include_router(eks.router, prefix="/api/v1") 