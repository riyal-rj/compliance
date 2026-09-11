import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv(override=True)

@dataclass
class EnvConfig:
    app_name: str = os.getenv("APP_NAME", "Brand Guardian AI")
    api_title: str = os.getenv("API_TITLE", "Brand Guardian AI API")
    api_version: str = os.getenv("API_VERSION", "1.0.0")
    app_description: str = os.getenv(
        "API_DESCRIPTION",
        "API for auditing video content against brand compliance rules.",
    )
    azure_openai_endpoint: str | None = os.getenv("AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str | None = os.getenv("AZURE_OPENAI_API_KEY")
    azure_openai_api_version: str = os.getenv(
        "AZURE_OPENAI_API_VERSION", "2024-02-01"
    )
    azure_openai_chat_deployment: str | None = os.getenv(
        "AZURE_OPENAI_CHAT_DEPLOYMENT"
    )
    azure_openai_embedding_deployment: str = os.getenv(
        "AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small"
    )
    azure_search_endpoint: str | None = os.getenv("AZURE_SEARCH_ENDPOINT")
    azure_search_api_key: str | None = os.getenv("AZURE_SEARCH_API_KEY")
    azure_search_index_name: str | None = os.getenv("AZURE_SEARCH_INDEX_NAME")
    azure_vi_account_id: str | None = os.getenv("AZURE_VI_ACCOUNT_ID")
    azure_vi_location: str | None = os.getenv("AZURE_VI_LOCATION")
    azure_subscription_id: str | None = os.getenv("AZURE_SUBSCRIPTION_ID")
    azure_resource_group: str | None = os.getenv("AZURE_RESOURCE_GROUP")
    azure_vi_name: str = os.getenv("AZURE_VI_NAME", "project-brand-guardian-001")

    azure_application_insights_connection_str: str | None = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")


envConfig = EnvConfig()