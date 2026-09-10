from dataclasses import dataclass

from backend.src.config.env_config import envConfig

@dataclass(frozen=True)
class Settings:
    app_name: str = "Brand Guardian AI"
    api_title: str = "Brand Guardian AI API"
    api_version: str = "1.0.0"
    app_description: str = "API for auditing video content against brand compliance rules."

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=envConfig.app_name,
            api_title=envConfig.api_title,
            api_version=envConfig.api_version,
            app_description=envConfig.app_description,
        )

settings = Settings.from_env()