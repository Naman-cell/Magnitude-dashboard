import boto3
import os
from typing import List, Dict, Any
from dotenv import load_dotenv
import yaml
import json
from datetime import datetime
import subprocess
import tempfile
import base64
import logging
from eks_token import get_token

logger = logging.getLogger(__name__)

class EKSService:
    def __init__(self):
        # Get the absolute path to the magnitude-backend directory
        backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..'))
        print(f"Backend directory: {backend_dir}")
        env_path = os.path.join(backend_dir, '.env')
        
        # Load environment variables from .env file
        load_dotenv(dotenv_path=env_path)
        
        # Initialize EKS client with credentials from environment variables
        self.eks_client = boto3.client(
            'eks',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_DEFAULT_REGION')
        )
        
        self.boto_session = boto3.Session(
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_DEFAULT_REGION')
        )
        
        # Print environment variables for debugging (remove in production)
        print(f"AWS Region: {os.getenv('AWS_DEFAULT_REGION')}")
        print(f"Access Key ID exists: {os.getenv('AWS_ACCESS_KEY_ID')}")
        print(f"Secret Access Key exists: {os.getenv('AWS_SECRET_ACCESS_KEY')}")

    async def _get_kubeconfig(self, cluster_name: str) -> str:
        """Get kubeconfig for the specified EKS cluster."""
        try:
            # Get cluster details
            cluster = self.eks_client.describe_cluster(name=cluster_name)
            cluster_data = cluster['cluster']
            
            # Get AWS credentials from the boto3 session
            credentials = self.boto_session.get_credentials()
            print(f"Credentials: {credentials.access_key}")
            
            # Create kubeconfig content
            kubeconfig = {
                "apiVersion": "v1",
                "kind": "Config",
                "clusters": [{
                    "name": cluster_name,
                    "cluster": {
                        "server": cluster_data['endpoint'],
                        "certificate-authority-data": cluster_data['certificateAuthority']['data']
                    }
                }],
                "contexts": [{
                    "name": cluster_name,
                    "context": {
                        "cluster": cluster_name,
                        "user": "aws"
                    }
                }],
                "current-context": cluster_name,
                "users": [{
                    "name": "aws",
                    "user": {
                        "exec": {
                            "apiVersion": "client.authentication.k8s.io/v1beta1",
                            "command": "aws-iam-authenticator",
                            "args": [
                                "token",
                                "-i",
                                cluster_name
                            ],
                            "env": [
                                {
                                    "name": "AWS_ACCESS_KEY_ID",
                                    "value": credentials.access_key
                                },
                                {
                                    "name": "AWS_SECRET_ACCESS_KEY",
                                    "value": credentials.secret_key
                                },
                                {
                                    "name": "AWS_DEFAULT_REGION",
                                    "value": os.getenv("AWS_DEFAULT_REGION")
                                }
                            ]
                        }
                    }
                }]
            }
            
            # Write kubeconfig to a temporary file for debugging
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(yaml.dump(kubeconfig))
                logger.info(f"Generated kubeconfig saved to: {f.name}")
            
            return yaml.dump(kubeconfig)
        except Exception as e:
            logger.error(f"Error getting kubeconfig: {str(e)}")
            raise

    def _apply_yaml(self, kubeconfig: str, yaml_content: str, namespace: str = 'default') -> Dict[str, Any]:
        """
        Apply YAML configuration using kubectl
        """
        try:
            # Create temporary files for kubeconfig and yaml
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as yaml_file, \
                 tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as kubeconfig_file:
                
                # Write kubeconfig
                kubeconfig_file.write(kubeconfig)
                kubeconfig_file.flush()
                
                # Write YAML content
                yaml_file.write(yaml_content)
                yaml_file.flush()
                
                # Apply YAML using kubectl
                cmd = [
                    'kubectl',
                    '--kubeconfig', kubeconfig_file.name,
                    'apply',
                    '-f', yaml_file.name,
                    '-n', namespace
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
                
                if result.returncode != 0:
                    raise Exception(f"Failed to apply YAML: {result.stderr}")
                
                # Get the applied resource details
                resource_type = yaml.safe_load(yaml_content)['kind'].lower()
                resource_name = yaml.safe_load(yaml_content)['metadata']['name']
                
                get_cmd = [
                    'kubectl',
                    '--kubeconfig', kubeconfig_file.name,
                    'get', resource_type, resource_name,
                    '-n', namespace,
                    '-o', 'json'
                ]
                
                get_result = subprocess.run(get_cmd, capture_output=True, text=True, env=os.environ.copy())
                
                if get_result.returncode != 0:
                    raise Exception(f"Failed to get resource details: {get_result.stderr}")
                
                return {
                    'status': 'success',
                    'message': f'Successfully applied {resource_type} {resource_name}',
                    'details': json.loads(get_result.stdout)
                }
                
        except Exception as e:
            raise Exception(f"Failed to apply YAML: {str(e)}")
        finally:
            # Clean up temporary files
            try:
                os.unlink(yaml_file.name)
                os.unlink(kubeconfig_file.name)
            except:
                pass

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
            # Get kubeconfig
            kubeconfig = await self._get_kubeconfig(cluster_name)
            
            # Create temporary file for kubeconfig
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as kubeconfig_file:
                kubeconfig_file.write(kubeconfig)
                kubeconfig_file.flush()
                
                # List all resources in all namespaces
                resources = [
                    ('deployments', 'Deployment'),
                    ('statefulsets', 'StatefulSet'),
                    ('daemonsets', 'DaemonSet'),
                    ('jobs', 'Job'),
                    ('cronjobs', 'CronJob'),
                    ('services', 'Service'),
                    ('ingresses', 'Ingress'),
                    ('configmaps', 'ConfigMap'),
                    ('secrets', 'Secret'),
                    ('persistentvolumeclaims', 'PersistentVolumeClaim'),
                    ('roles', 'Role'),
                    ('rolebindings', 'RoleBinding'),
                    ('serviceaccounts', 'ServiceAccount')
                ]
                
                all_components = []
                
                for resource, kind in resources:
                    cmd = [
                        'kubectl',
                        '--kubeconfig', kubeconfig_file.name,
                        'get', resource,
                        '--all-namespaces',
                        '-o', 'json'
                    ]
                    
                    result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
                    
                    if result.returncode == 0:
                        try:
                            data = json.loads(result.stdout)
                            for item in data.get('items', []):
                                metadata = item.get('metadata', {})
                                spec = item.get('spec', {})
                                status = item.get('status', {})
                                
                                component = {
                                    'name': metadata.get('name'),
                                    'namespace': metadata.get('namespace'),
                                    'type': kind,
                                    'status': status.get('phase', 'Unknown'),
                                    'creation_timestamp': metadata.get('creationTimestamp'),
                                    'labels': metadata.get('labels', {}),
                                    'annotations': metadata.get('annotations', {}),
                                    'spec': spec,
                                    'status': status
                                }
                                all_components.append(component)
                        except json.JSONDecodeError:
                            continue
                
                return all_components
                
        except Exception as e:
            raise Exception(f"Failed to list cluster components: {str(e)}")
        finally:
            # Clean up temporary file
            try:
                os.unlink(kubeconfig_file.name)
            except:
                pass

    async def get_component_yaml(self, cluster_name: str, component_name: str, 
                               component_type: str, namespace: str = 'default') -> str:
        """
        Get YAML configuration for a specific Kubernetes component
        """
        try:
            # Get kubeconfig
            kubeconfig = await self._get_kubeconfig(cluster_name)
            
            # Create temporary file for kubeconfig
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as kubeconfig_file:
                kubeconfig_file.write(kubeconfig)
                kubeconfig_file.flush()
                
                # Get component YAML using kubectl
                cmd = [
                    'kubectl',
                    '--kubeconfig', kubeconfig_file.name,
                    'get', component_type.lower(), component_name,
                    '-n', namespace,
                    '-o', 'yaml'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
                
                if result.returncode != 0:
                    raise Exception(f"Failed to get component YAML: {result.stderr}")
                
                return result.stdout
                
        except Exception as e:
            raise Exception(f"Failed to get component YAML: {str(e)}")
        finally:
            # Clean up temporary file
            try:
                os.unlink(kubeconfig_file.name)
            except:
                pass

    async def list_pods(self, cluster_name: str, namespace: str = 'default') -> List[Dict[str, Any]]:
        """
        List all pods in a specific namespace of a cluster
        """
        try:
            # Get kubeconfig
            kubeconfig = await self._get_kubeconfig(cluster_name)
            
            # Create temporary file for kubeconfig
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as kubeconfig_file:
                kubeconfig_file.write(kubeconfig)
                kubeconfig_file.flush()
                
                # Get pods in JSON format
                cmd = [
                    'kubectl',
                    '--kubeconfig', kubeconfig_file.name,
                    'get', 'pods',
                    '-n', namespace,
                    '-o', 'json'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
                
                if result.returncode != 0:
                    raise Exception(f"Failed to get pods: {result.stderr}")
                
                data = json.loads(result.stdout)
                pods = []
                
                for item in data.get('items', []):
                    metadata = item.get('metadata', {})
                    spec = item.get('spec', {})
                    status = item.get('status', {})
                    
                    # Get container statuses
                    container_statuses = status.get('containerStatuses', [])
                    containers = []
                    
                    for container_status in container_statuses:
                        container = {
                            'name': container_status.get('name'),
                            'image': container_status.get('image'),
                            'ready': container_status.get('ready', False),
                            'restart_count': container_status.get('restartCount', 0),
                            'state': container_status.get('state', {}),
                            'last_state': container_status.get('lastState', {})
                        }
                        containers.append(container)
                    
                    # Get pod conditions
                    conditions = status.get('conditions', [])
                    pod_conditions = []
                    for condition in conditions:
                        pod_conditions.append({
                            'type': condition.get('type'),
                            'status': condition.get('status'),
                            'last_transition_time': condition.get('lastTransitionTime'),
                            'reason': condition.get('reason'),
                            'message': condition.get('message')
                        })
                    
                    pod = {
                        'name': metadata.get('name'),
                        'namespace': metadata.get('namespace'),
                        'status': status.get('phase', 'Unknown'),
                        'ip': status.get('podIP'),
                        'node': spec.get('nodeName'),
                        'host_ip': status.get('hostIP'),
                        'start_time': status.get('startTime'),
                        'containers': containers,
                        'conditions': pod_conditions,
                        'labels': metadata.get('labels', {}),
                        'annotations': metadata.get('annotations', {}),
                        'spec': spec,
                        'status': status
                    }
                    pods.append(pod)
                
                return pods
                
        except Exception as e:
            raise Exception(f"Failed to list pods: {str(e)}")
        finally:
            # Clean up temporary file
            try:
                os.unlink(kubeconfig_file.name)
            except:
                pass

    async def get_pod_details(self, cluster_name: str, pod_name: str, 
                            namespace: str = 'default') -> Dict[str, Any]:
        """
        Get detailed information about a specific pod
        """
        try:
            # Get kubeconfig
            kubeconfig = await self._get_kubeconfig(cluster_name)
            
            # Create temporary file for kubeconfig
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as kubeconfig_file:
                kubeconfig_file.write(kubeconfig)
                kubeconfig_file.flush()
                
                # Get pod details in JSON format
                cmd = [
                    'kubectl',
                    '--kubeconfig', kubeconfig_file.name,
                    'get', 'pod', pod_name,
                    '-n', namespace,
                    '-o', 'json'
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, env=os.environ.copy())
                
                if result.returncode != 0:
                    raise Exception(f"Failed to get pod details: {result.stderr}")
                
                pod_data = json.loads(result.stdout)
                metadata = pod_data.get('metadata', {})
                spec = pod_data.get('spec', {})
                status = pod_data.get('status', {})
                
                # Get container statuses
                container_statuses = status.get('containerStatuses', [])
                containers = []
                
                for container_status in container_statuses:
                    container = {
                        'name': container_status.get('name'),
                        'image': container_status.get('image'),
                        'ready': container_status.get('ready', False),
                        'restart_count': container_status.get('restartCount', 0),
                        'state': container_status.get('state', {}),
                        'last_state': container_status.get('lastState', {}),
                        'resources': spec.get('containers', [{}])[0].get('resources', {})
                    }
                    containers.append(container)
                
                # Get pod conditions
                conditions = status.get('conditions', [])
                pod_conditions = []
                for condition in conditions:
                    pod_conditions.append({
                        'type': condition.get('type'),
                        'status': condition.get('status'),
                        'last_transition_time': condition.get('lastTransitionTime'),
                        'reason': condition.get('reason'),
                        'message': condition.get('message')
                    })
                
                # Get pod events
                events_cmd = [
                    'kubectl',
                    '--kubeconfig', kubeconfig_file.name,
                    'get', 'events',
                    '--field-selector', f'involvedObject.name={pod_name}',
                    '-n', namespace,
                    '-o', 'json'
                ]
                
                events_result = subprocess.run(events_cmd, capture_output=True, text=True, env=os.environ.copy())
                events = []
                
                if events_result.returncode == 0:
                    try:
                        events_data = json.loads(events_result.stdout)
                        for event in events_data.get('items', []):
                            events.append({
                                'type': event.get('type'),
                                'reason': event.get('reason'),
                                'message': event.get('message'),
                                'timestamp': event.get('lastTimestamp'),
                                'source': event.get('source', {})
                            })
                    except json.JSONDecodeError:
                        pass
                
                return {
                    'name': metadata.get('name'),
                    'namespace': metadata.get('namespace'),
                    'status': status.get('phase', 'Unknown'),
                    'ip': status.get('podIP'),
                    'node': spec.get('nodeName'),
                    'host_ip': status.get('hostIP'),
                    'start_time': status.get('startTime'),
                    'containers': containers,
                    'conditions': pod_conditions,
                    'events': events,
                    'labels': metadata.get('labels', {}),
                    'annotations': metadata.get('annotations', {}),
                    'spec': spec,
                    'status': status
                }
                
        except Exception as e:
            raise Exception(f"Failed to get pod details: {str(e)}")
        finally:
            # Clean up temporary file
            try:
                os.unlink(kubeconfig_file.name)
            except:
                pass

    async def update_component_yaml(self, cluster_name: str, component_name: str, 
                                  component_type: str, yaml_content: str, 
                                  namespace: str = 'default') -> Dict[str, Any]:
        """
        Update a Kubernetes component configuration using YAML
        """
        try:
            # Validate YAML content
            try:
                yaml_data = yaml.safe_load(yaml_content)
                if not yaml_data:
                    raise ValueError("Invalid YAML content")
                if yaml_data.get('kind') != component_type:
                    raise ValueError(f"YAML content must be for a {component_type} resource")
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML format: {str(e)}")
            
            # Get kubeconfig
            kubeconfig = await self._get_kubeconfig(cluster_name)
            
            # Apply YAML
            result = self._apply_yaml(kubeconfig, yaml_content, namespace)
            
            return {
                'status': 'success',
                'message': f'Successfully updated {component_type} {component_name} in namespace {namespace}',
                'component': {
                    'name': component_name,
                    'type': component_type,
                    'namespace': namespace,
                    'updated_at': datetime.now().isoformat(),
                    'details': result['details']
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to update component YAML: {str(e)}")

    async def update_pod_yaml(self, cluster_name: str, pod_name: str, 
                            yaml_content: str, namespace: str = 'default') -> Dict[str, Any]:
        """
        Update a pod configuration using YAML
        """
        try:
            # Validate YAML content
            try:
                yaml_data = yaml.safe_load(yaml_content)
                if not yaml_data:
                    raise ValueError("Invalid YAML content")
                if yaml_data.get('kind') != 'Pod':
                    raise ValueError("YAML content must be for a Pod resource")
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML format: {str(e)}")
            
            # Get kubeconfig
            kubeconfig = await self._get_kubeconfig(cluster_name)
            
            # Apply YAML
            result = self._apply_yaml(kubeconfig, yaml_content, namespace)
            
            return {
                'status': 'success',
                'message': f'Successfully updated pod {pod_name} in namespace {namespace}',
                'pod': {
                    'name': pod_name,
                    'namespace': namespace,
                    'updated_at': datetime.now().isoformat(),
                    'details': result['details']
                }
            }
            
        except Exception as e:
            raise Exception(f"Failed to update pod YAML: {str(e)}") 