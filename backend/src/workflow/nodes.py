import json
import logging
import os
import tempfile
from typing import Any, Dict
from urllib.parse import urlparse

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from langchain_core.messages import SystemMessage, HumanMessage

from backend.src.config.env_config import envConfig
from backend.src.config.prompt_loader import load_system_prompt
from backend.src.workflow.state import VideoAuditState
from backend.src.integrations.azure.video_indexer import AzureVideoIndexer

logger = logging.getLogger("brand-guardian")
logging.basicConfig(level=logging.INFO)


def index_video_node(state: VideoAuditState) -> Dict[str, Any]:
    """Download, index, and extract data for a YouTube video."""
    video_url = state.get("video_url")
    video_id_input = state.get("video_id") or "vid_demo"

    logger.info("--- [Node: Indexer] Processing: %s ---", video_url)
    local_path: str | None = None

    try:
        if not isinstance(video_url, str) or not video_url.strip():
            raise ValueError("A video URL is required")

        hostname = (urlparse(video_url).hostname or "").lower()
        if hostname not in {"youtube.com", "www.youtube.com", "youtu.be", "www.youtu.be"}:
            raise ValueError("Please provide a valid YouTube URL")

        with tempfile.NamedTemporaryFile(
            prefix="audit_video_", suffix=".mp4", delete=False
        ) as temporary_file:
            local_path = temporary_file.name

        vi_service = AzureVideoIndexer()
        local_path = vi_service.download_youtube_video(video_url, output_path=local_path)
        azure_video_id = vi_service.upload_video(local_path, video_name=video_id_input)
        if not azure_video_id:
            raise RuntimeError("Azure Video Indexer did not return a video ID")
        logger.info("Upload Success. Azure Video ID: %s", azure_video_id)

        raw_insights = vi_service.wait_for_processing(azure_video_id)
        clean_data = vi_service.extract_data(raw_insights)

        logger.info("--- [Node: Indexer] Extraction Complete ---")
        return {
            **clean_data,
            "ocr_text": clean_data.get("ocr_text", clean_data.get("ocr", [])),
        }

    except Exception as exc:
        logger.error("Video Indexer Failed: %s",exc)
        return {
            "errors": [str(exc)],
            "final_status": "FAIL",
            "transcript": "",
            "ocr_text":[]
        }
    finally:
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except OSError:
                logger.warning("Unable to remove temporary video file: %s", local_path)



def audit_content_node(state: VideoAuditState) -> Dict[str, Any]:
    """Run retrieval-augmented compliance analysis against indexed video data."""
    logger.info("--- [Node: Auditor] querying Knowledge Base  & LLM---")

    transcript = state.get("transcript", "")
    if not transcript:
        logger.warning("No transcript available. Skipping Audit.")
        return {
            "final_status": "FAIL",
            "final_report":"Audit skipped because video processing failed (No transcript available).",
        }

    response = None
    try:
        llm = AzureChatOpenAI(
            azure_deployment=envConfig.azure_openai_chat_deployment,
            api_version=envConfig.azure_openai_api_version,
            temperature=0.0
        )

        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=envConfig.azure_openai_embedding_deployment,
            api_version=envConfig.azure_openai_api_version
        )

        search_index_name = envConfig.azure_search_index_name
        search_endpoint = envConfig.azure_search_endpoint
        if search_index_name is None:
            raise ValueError("Azure Search index name is not configured")
        if search_endpoint is None:
            raise ValueError("Azure Search endpoint is not configured")

        vector_store = AzureSearch(
            azure_search_endpoint=search_endpoint,
            azure_search_key=envConfig.azure_search_api_key,
            index_name=search_index_name,
            embedding_function=embeddings.embed_query
        )

        ocr_text = state.get("ocr_text", [])
        query_text = f"{transcript} {' '.join(ocr_text)}"
        docs = vector_store.similarity_search(query_text, k=5)
        retrieved_rules = "\n\n".join(doc.page_content for doc in docs)

        system_prompt = load_system_prompt(
            "audit_compliance",
            RETRIEVED_RULES=retrieved_rules
        )

        user_message = f"""
        VIDEO_METADATA: {state.get("video_metadata", {})}
        TRANSCRIPT: {transcript}
        OCR_TEXT: {ocr_text}
        """

        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_message)
        ])

        content = response.content
        if not isinstance(content, str):
            raise ValueError("The auditor returned a non-text response")
        if content.startswith("```"):
            content = content.strip().removeprefix("```json").removesuffix("```").strip()

        audit_data = json.loads(content)
        if not isinstance(audit_data, dict):
            raise ValueError("The auditor response must be a JSON object")

        return {
            "compliance_results": audit_data.get("compliance_results", []),
            "final_status": audit_data.get(
                "final_status", audit_data.get("status", "FAIL")
            ),
            "final_report": audit_data.get("final_report", "No report generated"),
        }
    
    except Exception as exc:
        logger.error("System Error in Auditor Mode: %s", exc)
        logger.error("Raw LLM Response: %s", response.content if response else "None")
        return {
            "errors": [str(exc)],
            "final_status": "FAIL",
        }


    