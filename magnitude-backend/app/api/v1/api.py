from fastapi import APIRouter
from app.api.v1.endpoints import ecr

api_router = APIRouter()

api_router.include_router(ecr.router, prefix="/api/v1") 