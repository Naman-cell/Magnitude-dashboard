from fastapi import APIRouter


router = APIRouter(
    prefix="/ecr",
    tags=["ECR"]
)
