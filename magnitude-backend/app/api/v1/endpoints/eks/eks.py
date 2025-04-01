from fastapi import APIRouter, HTTPException, Body
from app.manager.services.eks.eks_service import EKSService
from typing import Optional
from pydantic import BaseModel

router = APIRouter(
    prefix="/eks",
    tags=["EKS"]
)

class YAMLUpdateRequest(BaseModel):
    yaml_content: str
    namespace: Optional[str] = "default"

@router.get("/clusters")
async def list_clusters():
    try:
        eks_service = EKSService()
        clusters = await eks_service.list_clusters()
        return {"clusters": clusters}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clusters/{cluster_name}/components")
async def list_cluster_components(cluster_name: str):
    try:
        eks_service = EKSService()
        components = await eks_service.list_cluster_components(cluster_name)
        return {"components": components}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clusters/{cluster_name}/components/{component_name}/yaml")
async def get_component_yaml(
    cluster_name: str,
    component_name: str,
    component_type: str,
    namespace: Optional[str] = "default"
):
    try:
        eks_service = EKSService()
        yaml_content = await eks_service.get_component_yaml(
            cluster_name=cluster_name,
            component_name=component_name,
            component_type=component_type,
            namespace=namespace
        )
        return {"yaml": yaml_content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clusters/{cluster_name}/pods")
async def list_pods(
    cluster_name: str,
    namespace: Optional[str] = "default"
):
    try:
        eks_service = EKSService()
        pods = await eks_service.list_pods(
            cluster_name=cluster_name,
            namespace=namespace
        )
        return {"pods": pods}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/clusters/{cluster_name}/pods/{pod_name}")
async def get_pod_details(
    cluster_name: str,
    pod_name: str,
    namespace: Optional[str] = "default"
):
    try:
        eks_service = EKSService()
        pod_details = await eks_service.get_pod_details(
            cluster_name=cluster_name,
            pod_name=pod_name,
            namespace=namespace
        )
        return {"pod": pod_details}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/clusters/{cluster_name}/components/{component_name}/yaml")
async def update_component_yaml(
    cluster_name: str,
    component_name: str,
    component_type: str,
    update_request: YAMLUpdateRequest = Body(...)
):
    try:
        eks_service = EKSService()
        result = await eks_service.update_component_yaml(
            cluster_name=cluster_name,
            component_name=component_name,
            component_type=component_type,
            yaml_content=update_request.yaml_content,
            namespace=update_request.namespace
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/clusters/{cluster_name}/pods/{pod_name}/yaml")
async def update_pod_yaml(
    cluster_name: str,
    pod_name: str,
    update_request: YAMLUpdateRequest = Body(...)
):
    try:
        eks_service = EKSService()
        result = await eks_service.update_pod_yaml(
            cluster_name=cluster_name,
            pod_name=pod_name,
            yaml_content=update_request.yaml_content,
            namespace=update_request.namespace
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 