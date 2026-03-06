from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # MongoDB
    mongodb_url: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "insurance_copilot"
     
    # S3 / MinIO
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "us-east-1"
    s3_bucket_name: str
    s3_endpoint_url: str = ""  # Set for MinIO, e.g. "https://minio.bharatgen.dev"
    s3_upload_url_expiry: int = 900  # 15 minutes
    s3_download_url_expiry: int = 1800  # 30 minutes
    
    # LLM
    llm_api_key: str
    llm_api_base_url: str = "https://api.openai.com/v1"
    
    # OpenRouter experiment toggle
    use_openrouter: bool = False
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1/chat/completions"
    openrouter_model: str = "qwen/qwen3.5-35b-a3b"
    
    # JWT
    jwt_secret_key: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours
    
    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    
    # Face Match Algorithm: "v1" (YuNet+SFace) or "v2" (InsightFace/MobileFaceNet)
    face_match_algorithm: str = "v2"
    
    # Concurrency limits (reduce to avoid OOM / CPU oversubscription)
    ocr_max_workers: int = 2
    face_match_max_workers: int = 2
    omp_num_threads: int = 2  # OpenMP/ONNX/Tesseract threads per process
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

settings = Settings()

