import boto3
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import yaml
import json
from app.core.config import settings

from fastapi import HTTPException, Response
import asyncio
class EKSService:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Initialize EKS client with credentials from environment variables
        self.eks_client = boto3.client(
            'eks'
        )
        self.ec2_client = boto3.client(
            'ec2'
        )

    async def list_clusters(self) -> List[Dict[str, Any]]:
        """
        List all EKS clusters
        """
        try:
            response = self.eks_client.list_clusters()
            clusters = []
            for cluster_name in response['clusters']:
                cluster_details = self.eks_client.describe_cluster(name=cluster_name)
                cluster_info = {
                    'name': cluster_name,
                    'status': cluster_details['cluster']['status'],
                    'version': cluster_details['cluster']['version'],
                    'endpoint': cluster_details['cluster']['endpoint'],
                    'created_at': cluster_details['cluster']['createdAt'].isoformat(),
                }
                clusters.append(cluster_info)
            return clusters
            
        except Exception as e:
            raise Exception(f"Failed to list EKS clusters: {str(e)}")
    
    async def _describe_cluster_async(self, cluster_name: str) -> Dict[str, Any]:
        """
        Helper method to call describe_cluster asynchronously.
        """
        return self.eks_client.describe_cluster(name=cluster_name)
        
    async def get_eks_cluster_details(self, cluster_name: str) -> Dict[str, Any]:
        """
        Fetch details of a specific EKS cluster asynchronously.
        """
        try:
            response = await self._describe_cluster_async(cluster_name)
            return response.get("cluster", {})
        except Exception as e:
            raise Exception(f"Failed to fetch EKS cluster details: {str(e)}")
    
    async def get_eks_cluster_yaml(self, cluster_name: str) -> Response:
        """
        Fetch the EKS cluster details asynchronously and return YAML response.
        """
        try:
            response = await self._describe_cluster_async(cluster_name)
            cluster_data = response.get("cluster", {})

            if not cluster_data:
                raise HTTPException(status_code=404, detail="Cluster not found")

            yaml_data = yaml.dump(cluster_data, default_flow_style=False)
            return Response(content=yaml_data, media_type="text/yaml")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch cluster YAML: {str(e)}")
        
    
    async def get_eks_cluster_overview(
        self,
        cluster_name: str,
        include_compute: bool = True,
        include_networking: bool = True,
        include_addons: bool = True,
        include_observability: bool = True,
        include_updates: bool = True,
    ) -> Dict[str, Any]:
        """
        Fetch EKS cluster overview asynchronously with optional filters.
        """
        try:

            cluster_response = await asyncio.to_thread(self.eks_client.describe_cluster, name=cluster_name)
            cluster_data = cluster_response.get("cluster", {})

            if not cluster_data:
                raise HTTPException(status_code=404, detail="Cluster not found")

            cluster_overview = {
                "name": cluster_data.get("name"),
                "status": cluster_data.get("status"),
                "version": cluster_data.get("version"),
                "tags": cluster_data.get("tags", {}),
                "arn": cluster_data.get("arn"),
                "created_at": cluster_data.get("createdAt").isoformat(),
            }

            if include_compute:
                node_groups_response = await asyncio.to_thread(self.eks_client.list_nodegroups, clusterName=cluster_name)
                node_groups = node_groups_response.get("nodegroups", [])
                compute_details = []

                async def fetch_nodegroup_details(node_group):
                    node_info = await asyncio.to_thread(
                        self.eks_client.describe_nodegroup,
                        clusterName=cluster_name,
                        nodegroupName=node_group,
                    )
                    node_data = node_info.get("nodegroup", {})
                    return {
                        "node_group": node_data.get("nodegroupName"),
                        "instance_types": node_data.get("instanceTypes", []),
                        "scaling": node_data.get("scalingConfig", {}),
                        "subnets": node_data.get("subnets", []),
                    }

                compute_details = await asyncio.gather(*(fetch_nodegroup_details(ng) for ng in node_groups))
                cluster_overview["compute"] = compute_details

            if include_networking:
                vpc_config = cluster_data.get("resourcesVpcConfig", {})
                cluster_overview["networking"] = {
                    "subnets": vpc_config.get("subnetIds", []),
                    "security_groups": vpc_config.get("securityGroupIds", []),
                    "vpc_id": vpc_config.get("vpcId"),
                }

            if include_addons:
                addons_response = await asyncio.to_thread(self.eks_client.list_addons, clusterName=cluster_name)
                cluster_overview["addons"] = addons_response.get("addons", [])

            if include_observability:
                logging_info = cluster_data.get("logging", {}).get("clusterLogging", [])
                cluster_overview["logging"] = logging_info

            if include_updates:
                update_history_response = await asyncio.to_thread(self.eks_client.list_updates, name=cluster_name)
                cluster_overview["update_history"] = update_history_response.get("updateIds", [])

            return cluster_overview

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch cluster overview: {str(e)}")
        
    """Service class to handle EKS Add-ons operations."""

    async def list_addons(self, cluster_name: str, max_results: Optional[int] = None, next_token: Optional[str] = None) -> Dict[str, Any]:
        """Fetch paginated list of add-ons for a given EKS cluster."""
        try:
            params = {"clusterName": cluster_name}
            if max_results:
                params["maxResults"] = max_results
            if next_token:
                params["nextToken"] = next_token

            response = await asyncio.to_thread(self.eks_client.list_addons, **params)

            return {
                "addons": response.get("addons", []),
                "next_token": response.get("nextToken") 
            }

        except self.eks_client.exceptions.ResourceNotFoundException:
            raise HTTPException(status_code=404, detail=f"EKS cluster '{cluster_name}' not found.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list add-ons: {str(e)}")

        
    async def get_eks_addon_details(self, cluster_name: str, addon_name: str) -> Dict[str, Any]:
        """Fetch details of a specific EKS Addon."""
        try:
            response = await asyncio.to_thread(
                self.eks_client.describe_addon,
                clusterName=cluster_name,
                addonName=addon_name
            )
            return response.get("addon", {})

        except self.eks_client.exceptions.ResourceNotFoundException:
            raise HTTPException(status_code=404, detail=f"Addon '{addon_name}' not found in cluster '{cluster_name}'")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch addon details: {str(e)}")


    """Service class to handle EKS Node Group operations."""

    async def get_nodegroup_details(self, cluster_name: str, nodegroup_name: str) -> Dict[str, Any]:
        """Fetch details of a specific EKS Node Group."""
        try:
            response = await asyncio.to_thread(
                self.eks_client.describe_nodegroup,
                clusterName=cluster_name,
                nodegroupName=nodegroup_name
            )
            return response.get("nodegroup", {})

        except self.eks_client.exceptions.ResourceNotFoundException:
            raise HTTPException(status_code=404, detail=f"Node group '{nodegroup_name}' not found in cluster '{cluster_name}'.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to fetch node group details: {str(e)}")
        
    
    """Service class to handle EKS Node Group operations."""

    async def list_nodegroups(self, cluster_name: str) -> List[str]:
        """Fetch all node groups for a given EKS cluster."""
        try:
            response = await asyncio.to_thread(
                self.eks_client.list_nodegroups,
                clusterName=cluster_name
            )
            return response.get("nodegroups", [])

        except self.eks_client.exceptions.ResourceNotFoundException:
            raise HTTPException(status_code=404, detail=f"EKS cluster '{cluster_name}' not found.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list node groups: {str(e)}")
    
    async def list_node_groups(
        self, cluster_name: str, instance_type: Optional[str] = None, 
        min_cpu: Optional[int] = None, min_memory: Optional[int] = None
    ) -> Dict[str, Any]:
        """Fetch and filter node groups for a given EKS cluster."""
        try:
            # Step 1: Get Node Groups in the Cluster
            node_groups_response = await asyncio.to_thread(
                self.eks_client.list_nodegroups, clusterName=cluster_name
            )
            node_groups = node_groups_response.get("nodegroups", [])

            if not node_groups:
                return {"message": "No node groups found for this cluster", "nodes": []}

            nodes_data = []

            for node_group_name in node_groups:
                # Step 2: Describe Each Node Group
                node_group_details = await asyncio.to_thread(
                    self.eks_client.describe_nodegroup, 
                    clusterName=cluster_name, 
                    nodegroupName=node_group_name
                )
                node_group = node_group_details.get("nodegroup", {})

                if not node_group:
                    continue

                instance_types = node_group.get("instanceTypes", [])
                scaling_config = node_group.get("scalingConfig", {})

                node_info = {
                    "node_group_name": node_group_name,
                    "instance_types": instance_types,
                    "min_size": scaling_config.get("minSize"),
                    "max_size": scaling_config.get("maxSize"),
                    "desired_size": scaling_config.get("desiredSize"),
                    "subnets": node_group.get("subnets", []),
                    "ami_type": node_group.get("amiType"),
                }

                # Step 3: Apply Filters (If Provided)
                if instance_type and instance_type not in instance_types:
                    continue  # Skip if instance type doesn't match

                if min_cpu or min_memory:
                    # Fetch EC2 instance details for filtering
                    ec2_response = await asyncio.to_thread(
                        self.ec2_client.describe_instance_types, InstanceTypes=instance_types
                    )

                    filtered = False
                    for instance in ec2_response.get("InstanceTypes", []):
                        vcpu_count = instance.get("VCpuInfo", {}).get("DefaultVCpus", 0)
                        memory_mib = instance.get("MemoryInfo", {}).get("SizeInMiB", 0)

                        if (min_cpu and vcpu_count < min_cpu) or (min_memory and memory_mib < min_memory):
                            filtered = True
                            break  

                    if filtered:
                        continue  

                nodes_data.append(node_info)

            return {"nodes": nodes_data}

        except self.eks_client.exceptions.ResourceNotFoundException:
            raise HTTPException(status_code=404, detail=f"EKS cluster '{cluster_name}' not found.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list node groups: {str(e)}")

        

    
    async def list_updates(
        self, cluster_name: str, nodegroup_name: Optional[str] = None, addon_name: Optional[str] = None, 
        max_results: Optional[int] = None, next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch paginated list of updates for a given EKS cluster, nodegroup, or add-on."""
        try:
            params = {"name": cluster_name}
            if nodegroup_name:
                params["nodegroupName"] = nodegroup_name
            if addon_name:
                params["addonName"] = addon_name
            if max_results:
                params["maxResults"] = max_results
            if next_token:
                params["nextToken"] = next_token

            response = await asyncio.to_thread(self.eks_client.list_updates, **params)

            return {
                "updates": response.get("updateIds", []),
                "next_token": response.get("nextToken")  # Pagination token
            }

        except self.eks_client.exceptions.ResourceNotFoundException:
            raise HTTPException(status_code=404, detail=f"EKS cluster '{cluster_name}' not found.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list updates: {str(e)}")

    async def list_access_entries(
        self, cluster_name: str, associated_policy_arn: Optional[str] = None, 
        max_results: Optional[int] = None, next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch paginated list of access entries for an EKS cluster."""
        try:
            params = {"clusterName": cluster_name}
            if associated_policy_arn:
                params["associatedPolicyArn"] = associated_policy_arn
            if max_results:
                params["maxResults"] = max_results
            if next_token:
                params["nextToken"] = next_token

            response = await asyncio.to_thread(self.eks_client.list_access_entries, **params)

            return {
                "access_entries": response.get("accessEntries", []),
                "next_token": response.get("nextToken")
            }

        except self.eks_client.exceptions.ResourceNotFoundException:
            raise HTTPException(status_code=404, detail=f"EKS cluster '{cluster_name}' not found.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list access entries: {str(e)}")

    async def describe_access_entry(self, cluster_name: str, principal_arn: str) -> Dict[str, Any]:
        """Fetch details of a specific access entry in an EKS cluster."""
        try:
            response = await asyncio.to_thread(
                self.eks_client.describe_access_entry,
                clusterName=cluster_name,
                principalArn=principal_arn
            )
            return response.get("accessEntry", {})

        except self.eks_client.exceptions.ResourceNotFoundException:
            raise HTTPException(status_code=404, detail=f"Access entry for '{principal_arn}' not found in cluster '{cluster_name}'.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to describe access entry: {str(e)}")

    async def list_pod_identity_associations(
        self, cluster_name: str, namespace: Optional[str] = None, 
        service_account: Optional[str] = None, max_results: int = 50, 
        next_token: Optional[str] = None
    ) -> Dict[str, Any]:
        """List Pod Identity Associations for a given EKS cluster."""
        try:
            params = {"clusterName": cluster_name, "maxResults": max_results}
            if namespace:
                params["namespace"] = namespace
            if service_account:
                params["serviceAccount"] = service_account
            if next_token:
                params["nextToken"] = next_token

            response = await asyncio.to_thread(self.eks_client.list_pod_identity_associations, **params)
            return response

        except self.eks_client.exceptions.ResourceNotFoundException:
            raise HTTPException(status_code=404, detail=f"EKS cluster '{cluster_name}' not found.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to list Pod Identity Associations: {str(e)}")

    async def describe_pod_identity_association(self, cluster_name: str, association_id: str) -> Dict[str, Any]:
        """Describe a specific Pod Identity Association."""
        try:
            response = await asyncio.to_thread(
                self.eks_client.describe_pod_identity_association,
                clusterName=cluster_name,
                associationId=association_id,
            )
            return response.get("podIdentityAssociation", {})

        except self.eks_client.exceptions.ResourceNotFoundException:
            raise HTTPException(status_code=404, detail=f"Pod Identity Association '{association_id}' not found in cluster '{cluster_name}'.")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to describe Pod Identity Association: {str(e)}")




    async def list_cluster_components(self, cluster_name: str) -> List[Dict[str, Any]]:
        """
        List all Kubernetes components in a specific cluster
        """
        try:
            # Get cluster details to get the endpoint and certificate
            cluster_details = self.eks_client.describe_cluster(name=cluster_name)
            
            # Here you would typically use the AWS EKS API to get the kubeconfig
            # and then use kubectl to list components
            # This is a placeholder for the actual implementation
            components = [
                {
                    'name': 'example-deployment',
                    'type': 'deployment',
                    'namespace': 'default',
                    'status': 'running'
                }
            ]
            
            return components
            
        except Exception as e:
            raise Exception(f"Failed to list cluster components: {str(e)}")

    async def get_component_yaml(self, cluster_name: str, component_name: str, 
                               component_type: str, namespace: str = 'default') -> str:
        """
        Get YAML configuration for a specific Kubernetes component
        """
        try:
            # Here you would typically use the AWS EKS API to get the kubeconfig
            # and then use kubectl to get the component YAML
            # This is a placeholder for the actual implementation
            example_yaml = {
                'apiVersion': 'apps/v1',
                'kind': 'Deployment',
                'metadata': {
                    'name': component_name,
                    'namespace': namespace
                },
                'spec': {
                    'replicas': 1,
                    'selector': {
                        'matchLabels': {
                            'app': component_name
                        }
                    }
                }
            }
            
            return yaml.dump(example_yaml)
            
        except Exception as e:
            raise Exception(f"Failed to get component YAML: {str(e)}")

    async def list_pods(self, cluster_name: str, namespace: str = 'default') -> List[Dict[str, Any]]:
        """
        List all pods in a specific namespace of a cluster
        """
        try:
            # Get cluster details to get the endpoint and certificate
            cluster_details = self.eks_client.describe_cluster(name=cluster_name)
            
            # Here you would typically use the AWS EKS API to get the kubeconfig
            # and then use kubectl to list pods
            # This is a placeholder for the actual implementation
            pods = [
                {
                    'name': 'example-pod',
                    'namespace': namespace,
                    'status': 'Running',
                    'ip': '10.0.0.1',
                    'node': 'ip-10-0-0-1.ec2.internal',
                    'containers': [
                        {
                            'name': 'main',
                            'image': 'example:latest',
                            'ready': True,
                            'restart_count': 0
                        }
                    ]
                }
            ]
            
            return pods
            
        except Exception as e:
            raise Exception(f"Failed to list pods: {str(e)}")

    async def get_pod_details(self, cluster_name: str, pod_name: str, 
                            namespace: str = 'default') -> Dict[str, Any]:
        """
        Get detailed information about a specific pod
        """
        try:
            # Get cluster details to get the endpoint and certificate
            cluster_details = self.eks_client.describe_cluster(name=cluster_name)
            
            # Here you would typically use the AWS EKS API to get the kubeconfig
            # and then use kubectl to get pod details
            # This is a placeholder for the actual implementation
            pod_details = {
                'name': pod_name,
                'namespace': namespace,
                'status': 'Running',
                'ip': '10.0.0.1',
                'node': 'ip-10-0-0-1.ec2.internal',
                'containers': [
                    {
                        'name': 'main',
                        'image': 'example:latest',
                        'ready': True,
                        'restart_count': 0,
                        'ports': [
                            {
                                'container_port': 8080,
                                'protocol': 'TCP'
                            }
                        ],
                        'resources': {
                            'requests': {
                                'cpu': '100m',
                                'memory': '128Mi'
                            },
                            'limits': {
                                'cpu': '500m',
                                'memory': '512Mi'
                            }
                        }
                    }
                ],
                'events': [
                    {
                        'type': 'Normal',
                        'reason': 'Scheduled',
                        'message': 'Successfully assigned pod to node',
                        'timestamp': '2024-02-14T10:00:00Z'
                    }
                ]
            }
            
            return pod_details
            
        except Exception as e:
            raise Exception(f"Failed to get pod details: {str(e)}") 