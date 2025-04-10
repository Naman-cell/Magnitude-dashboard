from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import APIRouter
from app.api.v1.endpoints.container_registry import router as ecr_router
from app.api.v1.endpoints.k8s import router as eks_router

api_router = APIRouter()

api_router.include_router(ecr_router, prefix="/api/v1")
api_router.include_router(eks_router, prefix="/api/v1") 

app = FastAPI(
    title="Magnitude Dashboard API",
    description="API for listing AWS ECR images",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to Magnitude Dashboard API"}
