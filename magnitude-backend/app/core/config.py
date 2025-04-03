from pydantic_settings import BaseSettings
 
 
class Settings(BaseSettings):
    ELASTICSEARCH_HOST: str = "https://localhost:9200"
    ELASTICSEARCH_USER: str = "elastic"
    ELASTICSEARCH_PASSWORD: str = "your-password"
    ELASTICSEARCH_FINGERPRINT: str = "your-fingerprint"
 
    class Config:
        env_file = ".env"
 
 
settings = Settings()
 