"""
Config Validator — يتحقق من كل متغيرات البيئة عند الـ start
"""
import os, sys
from pydantic_settings import BaseSettings
from pydantic import field_validator

class Settings(BaseSettings):
    # MongoDB
    MONGODB_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "cyberguard"

    # Auth
    SECRET_KEY: str = "change_me_to_random_64_chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Admin
    ADMIN_ID: int = 0

    # Google
    GOOGLE_API_KEY: str = ""
    GOOGLE_CX: str = ""

    # GitHub
    GITHUB_TOKEN: str = ""

    # SerpAPI
    SERP_API_KEY: str = ""

    # VirusTotal (اختياري)
    VIRUSTOTAL_API_KEY: str = ""

    # Server
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    ENVIRONMENT: str = "development"

    # Limits
    MAX_UPLOAD_SIZE_MB: int = 50
    RATE_LIMIT_PER_MINUTE: int = 30
    MIN_TRUST_THRESHOLD: float = 0.65
    MAX_KNOWLEDGE_SIZE: int = 50000

    # Neural
    FORGET_THRESHOLD: float = 0.30
    SHORT_MEMORY_SIZE: int = 1000

    class Config:
        env_file = ".env"
        extra = "ignore"

    def validate_critical(self):
        """يوقف البرنامج إذا متغير أساسي ناقص"""
        errors = []
        if self.SECRET_KEY == "change_me_to_random_64_chars":
            errors.append("SECRET_KEY لم يتغير — غير القيمة في .env")
        if self.ENVIRONMENT == "production":
            if not self.MONGODB_URI.startswith("mongodb"):
                errors.append("MONGODB_URI غير صحيح")
            if not self.GOOGLE_API_KEY:
                print("⚠️  GOOGLE_API_KEY غير موجود — سيعمل بمصادر محدودة")
        if errors:
            print("\n❌ أخطاء في الإعدادات:")
            for e in errors:
                print(f"   • {e}")
            print()
            if self.ENVIRONMENT == "production":
                sys.exit(1)

settings = Settings()
