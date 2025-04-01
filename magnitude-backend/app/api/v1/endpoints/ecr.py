from fastapi import APIRouter, HTTPException
from app.manager.services.ecr import ECRService

router = APIRouter(
    prefix="/ecr",
    tags=["ECR"]
)

@router.get("/images")
async def list_ecr_images():
    try:
        ecr_service = ECRService()
        images = await ecr_service.list_images()
        return {"images": images}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 