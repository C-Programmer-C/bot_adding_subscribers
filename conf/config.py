from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LOGIN: str
    SECURITY_KEY: str
    PORT: int = 8080
    TELEPHONE_FIELD_ID: int
    class Config:
        env_file = str(Path(__file__).resolve().parent.parent / ".env")

settings = Settings() # type: ignore
