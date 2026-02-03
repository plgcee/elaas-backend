from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List


class Settings(BaseSettings):
    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_role_key: Optional[str] = None  # Required for admin operations like setting super_user
    
    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_topic_prefix: str = "elaas"
    
    # AWS S3 (will read from uppercase env vars automatically)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-east-1"
    s3_bucket_name: Optional[str] = None
    
    # GCP Credentials
    gcp_project_id: Optional[str] = None
    gcp_service_account_key: Optional[str] = None  # JSON key as string or path
    
    # Azure Credentials
    azure_subscription_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    azure_tenant_id: Optional[str] = None
    
    # MongoDB Credentials
    mongodb_public_key: Optional[str] = None
    mongodb_private_key: Optional[str] = None
    
    # Snowflake Credentials
    snowflake_account: Optional[str] = None
    snowflake_user: Optional[str] = None
    snowflake_password: Optional[str] = None
    snowflake_warehouse: Optional[str] = None
    
    # App
    app_name: str = "elaas-backend"
    debug: bool = False
    environment: str = "development"  # development | staging | production
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://127.0.0.1:3000,http://127.0.0.1:5173"
    rate_limit: str = "100/minute"  # slowapi format, e.g. "100/minute"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    def get_cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_prefix="",  # No prefix needed
        extra="ignore"
    )


settings = Settings()
