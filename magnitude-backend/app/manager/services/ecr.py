import boto3
import os
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

class ECRService:
    def __init__(self):
        # Load environment variables from .env file
        load_dotenv()
        
        # Initialize ECR client with credentials from environment variables
        self.ecr_client = boto3.client(
            'ecr',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_DEFAULT_REGION')
        )

    async def list_images(self) -> List[Dict[str, Any]]:
        """
        List all ECR images across all repositories
        """
        try:
            # Get all repositories
            repositories = self.ecr_client.describe_repositories()
            
            all_images = []
            
            for repo in repositories['repositories']:
                repo_name = repo['repositoryName']
                
                # Get image details for each repository
                images = self.ecr_client.describe_images(repositoryName=repo_name)
                
                for image in images['imageDetails']:
                    image_info = {
                        'repository': repo_name,
                        'image_digest': image.get('imageDigest', ''),
                        'image_tags': image.get('imageTags', []),
                        'size': image.get('imageSizeInBytes', 0),
                        'pushed_at': image.get('imagePushedAt', datetime.now()).isoformat(),
                    }
                    all_images.append(image_info)
            
            return all_images
            
        except Exception as e:
            raise Exception(f"Failed to list ECR images: {str(e)}") 