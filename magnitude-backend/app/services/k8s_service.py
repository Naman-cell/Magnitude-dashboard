import boto3
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import yaml
import json
from app.core.config import settings

class EKSService:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Initialize EKS client with credentials from environment variables
        self.eks_client = boto3.client(
            'eks',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_DEFAULT_REGION')
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