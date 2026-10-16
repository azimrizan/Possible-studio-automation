import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "dev-secret-key-32-chars-long-for-jwt-signing"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # Master key for AES local vault
    APP_MASTER_KEY: str = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./platform_data.db"
    
    # Ed25519 Keys for Approval Token Minting
    APPROVAL_PRIVATE_KEY_HEX: Optional[str] = None
    APPROVAL_PUBLIC_KEY_HEX: Optional[str] = None
    
    # MCP Gateway
    MCP_GATEWAY_URL: str = "http://localhost:8100"

    model_config = {
        "env_file": ".env",
        "extra": "ignore",
    }

settings = Settings()
