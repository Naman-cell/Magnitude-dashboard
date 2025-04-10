from fastapi import APIRouter, HTTPException,Query,Depends
import boto3
import yaml 
from typing import List, Dict, Any, Optional

from fastapi.responses import JSONResponse
from app.services.k8s_service import EKSService

from kubernetes import client
import subprocess
import json

router = APIRouter(
    prefix="/eks",
    tags=["EKS"])


eks_client = boto3.client("eks", region_name="ap-south-1")
ec2_client = boto3.client("ec2", region_name="ap-south-1")
sts_client = boto3.client("sts", region_name="us-east-1")


def get_eks_service():
    return EKSService()

@router.get("/clusters", response_model=List[Dict[str, Any]])
async def list_clusters(eks_service: EKSService = Depends(get_eks_service)):
    return await eks_service.list_clusters()


@router.get("/cluster/{cluster_name}")
async def get_eks_cluster_details(cluster_name: str, eks_service: EKSService = Depends(get_eks_service)):
    try:
        response =  await eks_service.get_eks_cluster_details(cluster_name)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/cluster/{cluster_name}/yaml")
async def get_eks_cluster_yaml(cluster_name: str, eks_service: EKSService = Depends(get_eks_service)):
    try:
        response = await eks_service.get_eks_cluster_yaml(cluster_name)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cluster/{cluster_name}/overview")
async def get_eks_cluster_overview(
    cluster_name: str,
    include_compute: bool = Query(True, description="Include compute details"),
    include_networking: bool = Query(True, description="Include networking details"),
    include_addons: bool = Query(True, description="Include installed add-ons"),
    include_observability: bool = Query(True, description="Include logging details"),
    include_updates: bool = Query(True, description="Include update history"),
    eks_service: EKSService = Depends(get_eks_service),
):
    try: 
        result = await eks_service.get_eks_cluster_overview(
            cluster_name,
            include_compute,
            include_networking,
            include_addons,
            include_observability,
            include_updates,
        )
        return JSONResponse(content=result, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/cluster/{cluster_name}/addons")
async def get_eks_addons(
    cluster_name: str,
    max_results: Optional[int] = Query(None, description="Maximum number of add-ons to return"),
    next_token: Optional[str] = Query(None, description="Pagination token for next set of results"),
    eks_service: EKSService = Depends(get_eks_service),
):
    try:
        """FastAPI route to list EKS add-ons with pagination support."""
        result = await eks_service.list_addons(cluster_name, max_results, next_token)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/cluster/{cluster_name}/addon/{addon_name}")
async def get_eks_addon(
    cluster_name: str,
    addon_name: str,
    eks_service: EKSService = Depends(get_eks_service),
):
    try:
        result = await eks_service.get_eks_addon_details(cluster_name, addon_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/cluster/{cluster_name}/nodegroups")
async def get_eks_nodegroups(
    cluster_name: str,
    eks_service: EKSService = Depends(get_eks_service),
):
    """FastAPI route to list all node groups in an EKS cluster."""
    try:
        result = await eks_service.list_nodegroups(cluster_name)
        return {"nodegroups": result}
    except Exception as e:  
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/cluster/{cluster_name}/nodes")
async def get_eks_cluster_nodes(
    cluster_name: str,
    instance_type: Optional[str] = Query(None, description="Filter by instance type"),
    min_cpu: Optional[int] = Query(None, description="Minimum vCPU required"),
    min_memory: Optional[int] = Query(None, description="Minimum memory in MiB"),
    eks_service: EKSService = Depends(get_eks_service),
):
    """List EKS node groups in a cluster with optional filters."""
    try:
        result = await eks_service.list_node_groups(cluster_name, instance_type, min_cpu, min_memory)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/cluster/{cluster_name}/nodegroup/{nodegroup_name}")
async def get_eks_nodegroup_details(
    cluster_name: str,
    nodegroup_name: str,
    eks_service: EKSService = Depends(get_eks_service),
):
    """FastAPI route to fetch EKS Node Group details."""
    try:
        result = await eks_service.get_nodegroup_details(cluster_name, nodegroup_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    

@router.get("/cluster/{cluster_name}/updates")
async def get_eks_updates(
    cluster_name: str,
    nodegroup_name: Optional[str] = Query(None, description="Filter by Node Group"),
    addon_name: Optional[str] = Query(None, description="Filter by Add-on"),
    max_results: Optional[int] = Query(None, description="Max results per request"),
    next_token: Optional[str] = Query(None, description="Pagination token"),
    eks_service: EKSService = Depends(get_eks_service),
):
    """List EKS updates for a cluster, nodegroup, or add-on."""
    result = await eks_service.list_updates(cluster_name, nodegroup_name, addon_name, max_results, next_token)
    return result

@router.get("/cluster/{cluster_name}/access-entries")
async def get_eks_access_entries(
    cluster_name: str,
    associated_policy_arn: Optional[str] = Query(None, description="Filter by associated IAM policy ARN"),
    max_results: Optional[int] = Query(None, description="Max results per request"),
    next_token: Optional[str] = Query(None, description="Pagination token"),
    eks_service: EKSService = Depends(get_eks_service),
):
    """List access entries for an EKS cluster."""
    try:    
        result = await eks_service.list_access_entries(cluster_name, associated_policy_arn, max_results, next_token)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/cluster/{cluster_name}/access-entry/{principal_arn}")
async def get_eks_access_entry(
    cluster_name: str,
    principal_arn: str,
    eks_service: EKSService = Depends(get_eks_service),
):
    """Describe a specific access entry for an EKS cluster."""
    try: 

        result = await eks_service.describe_access_entry(cluster_name, principal_arn)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/cluster/{cluster_name}/pod-identity")
async def list_pod_identities(
    cluster_name: str,
    namespace: Optional[str] = Query(None, description="Filter by Kubernetes namespace"),
    service_account: Optional[str] = Query(None, description="Filter by service account"),
    max_results: int = Query(50, description="Maximum results per page"),
    next_token: Optional[str] = Query(None, description="Pagination token"),
    eks_service: EKSService = Depends(get_eks_service),
):
    """List all Pod Identity Associations in an EKS cluster."""
    try:
        result =  await eks_service.list_pod_identity_associations(cluster_name, namespace, service_account, max_results, next_token)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
     
@router.get("/cluster/{cluster_name}/pod-identity/{association_id}")
async def describe_pod_identity(
    cluster_name: str,
    association_id: str,
    eks_service: EKSService = Depends(get_eks_service),
):
    """Describe a specific Pod Identity Association."""
    try:
        return await eks_service.describe_pod_identity_association(cluster_name, association_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




def get_k8s_client(cluster_name: str):
    """Get an authenticated Kubernetes client for the EKS cluster."""
    try:
        # Get the EKS cluster endpoint
        cluster_info = subprocess.run(
            ["aws", "eks", "describe-cluster", "--name", cluster_name, "--query", "cluster.endpoint", "--output", "text"],
            capture_output=True,
            text=True
        )

        if cluster_info.returncode != 0:
            raise Exception(f"Failed to get cluster endpoint: {cluster_info.stderr}")

        cluster_endpoint = cluster_info.stdout.strip()

        # Get the EKS token
        result = subprocess.run(
            ["aws", "eks", "get-token", "--cluster-name", cluster_name, "--output", "json"],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise Exception(f"Failed to get token: {result.stderr}")

        try:
            token_data = json.loads(result.stdout)
        except json.JSONDecodeError:
            raise Exception(f"Failed to parse JSON output: {result.stdout}")

        token = token_data.get("status", {}).get("token")
        if not token:
            raise Exception("No authentication token found in AWS EKS response.")

        configuration = client.Configuration()
        configuration.host = cluster_endpoint
        configuration.api_key = {"authorization": f"Bearer {token}"}
        configuration.verify_ssl = False
        client.Configuration.set_default(configuration)

        return client.CoreV1Api(), client.AppsV1Api()

    except Exception as e:
        raise Exception(f"Error initializing Kubernetes client: {str(e)}")

@router.get("/cluster/{cluster_name}/components")
def get_kubernetes_components(cluster_name: str):
    """Fetch all Kubernetes components (Deployments, Pods, Services, etc.) in the cluster."""
    try:
        core_v1, apps_v1 = get_k8s_client(cluster_name)
        components = {
            "namespaces": [ns.metadata.name for ns in core_v1.list_namespace().items],
            "pods": [{"name": pod.metadata.name, "namespace": pod.metadata.namespace} for pod in core_v1.list_pod_for_all_namespaces().items],
            "services": [{"name": svc.metadata.name, "namespace": svc.metadata.namespace} for svc in core_v1.list_service_for_all_namespaces().items],
            "deployments": [{"name": dep.metadata.name, "namespace": dep.metadata.namespace} for dep in apps_v1.list_deployment_for_all_namespaces().items],
            "daemonsets": [{"name": ds.metadata.name, "namespace": ds.metadata.namespace} for ds in apps_v1.list_daemon_set_for_all_namespaces().items],
            "statefulsets": [{"name": ss.metadata.name, "namespace": ss.metadata.namespace} for ss in apps_v1.list_stateful_set_for_all_namespaces().items],
        }
        
        return components

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cluster/{cluster_name}/component-yaml")
def get_kubernetes_component_yaml(
    cluster_name: str,
    namespace: str,
    component_type: str = Query(..., description="Component type (pod, service, deployment, etc.)"),
    component_name: str = Query(..., description="Name of the Kubernetes component")
):
    """Fetch YAML definition of a selected Kubernetes component."""
    try:
        core_v1, apps_v1 = get_k8s_client(cluster_name)
        component_yaml = None

        if component_type == "pod":
            pod = core_v1.read_namespaced_pod(name=component_name, namespace=namespace)
            component_yaml = pod.to_dict()
        elif component_type == "service":
            svc = core_v1.read_namespaced_service(name=component_name, namespace=namespace)
            component_yaml = svc.to_dict()
        elif component_type == "deployment":
            dep = apps_v1.read_namespaced_deployment(name=component_name, namespace=namespace)
            component_yaml = dep.to_dict()
        elif component_type == "daemonset":
            ds = apps_v1.read_namespaced_daemon_set(name=component_name, namespace=namespace)
            component_yaml = ds.to_dict()
        elif component_type == "statefulset":
            ss = apps_v1.read_namespaced_stateful_set(name=component_name, namespace=namespace)
            component_yaml = ss.to_dict()
        else:
            raise HTTPException(status_code=400, detail="Invalid component type")

        # Convert Python dictionary to YAML format
        yaml_output = yaml.dump(component_yaml, default_flow_style=False)
        return {"component": component_name, "namespace": namespace, "yaml": yaml_output}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
