import os
import glob 
import logging

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch

from backend.src.config.env_config import envConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def index_docs():
    """
    Read PDFs from backend/data, chunks them, and uploads to Azure AI Search.
    """

    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_folder = os.path.join(current_dir, "../../backend/data")

    logger.info("="*60)
    logger.info("Environment Configuration Check:")
    logger.info(f"AZURE_OPENAI_ENDPOINT: {envConfig.azure_openai_endpoint}")
    logger.info(f"AZURE_OPENAI_API_VERSION: {envConfig.azure_openai_api_version}")
    logger.info(f"Embedding Deployment: {envConfig.azure_openai_embedding_deployment}")
    logger.info(f"AZURE_SEARCH_ENDPOINT: {envConfig.azure_search_endpoint}")
    logger.info(f"AZURE_SEARCH_INDEX_NAME: {envConfig.azure_search_index_name}")
    logger.info("=" * 60)

    required_vars = {
        "AZURE_OPENAI_ENDPOINT": envConfig.azure_openai_endpoint,
        "AZURE_OPENAI_API_VERSION": envConfig.azure_openai_api_version,
        "AZURE_SEARCH_API_KEY": envConfig.azure_search_api_key,
        "AZURE_SEARCH_ENDPOINT": envConfig.azure_search_endpoint,
        "AZURE_SEARCH_INDEX_NAME": envConfig.azure_search_index_name,
    }

    missing_vars = [var for var, value in required_vars.items() if not value]
    if  missing_vars:
        logger.error(f"Missing environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file and ensure all variables are set.")
        return

    try:

        logger.info("Initializing Azure OpenAI Embeddings")
        embeddings = AzureOpenAIEmbeddings(
            azure_deployment=envConfig.azure_openai_embedding_deployment,
            azure_endpoint=envConfig.azure_openai_endpoint,
            api_key=envConfig.azure_openai_api_key,
            openai_api_version=envConfig.azure_openai_api_version,
        )
        logger.info("Azure Embedding Model initialized successfully.")
    except Exception as exc:
        logger.error(f"Failed to inialize the Azure Open AI Embeddings")
        logger.error("Please verify the Azure OpenAI deployment name and endpoint.")
        return

    try:
        logger.info(f"Initializing Azure AI Search vector store.")
        index_name = envConfig.azure_search_index_name
        vector_store=AzureSearch(
            azure_search_endpoint=envConfig.azure_search_endpoint,
            azure_search_key=envConfig.azure_search_api_key,
            index_name=index_name,
            embedding_function=embeddings.embed_query,
        )
        logger.info(f"Vector store initialized for index: {index_name}")
    except Exception as exc:
        logger.error(f"Failed to initialize the Azure Search {exc}")
        logger.error("Please verify your Azure Search endpoint, API key, and index name.")
        return

    pdf_files = glob.glob(os.path.join(data_folder, "*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDFs found in {data_folder}. Please add the files")
        return

    logger.info(f"Found {len(pdf_files)} PDFs to process: {[os.path.basename(file) for file in pdf_files]}")

    all_splits=[]

    for pdf_path in pdf_files:
        try:
            logger.info(f"Loading: {os.path.basename(pdf_path)}...")
            loader = PyPDFLoader(pdf_path)
            raw_docs = loader.load()

            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=100,
                chunk_overlap=200
            )
            splits = text_splitter.split_documents(raw_docs)

            for split in splits:
                split.metadata["source"] = os.path.basename(pdf_path)

            all_splits.extend(splits)
            logger.info(f" -> Split into {len(splits)} chunks.")
        except Exception as exc:
            logger.error(f"Failed to process {pdf_path}: {exc}")

    if all_splits:
        logger.info(f"Uploading {len(all_splits)} chunks to Azure AI Search Index '{index_name}' ...")
        try:
            vector_store.add_documents(all_splits)
            logger.info("="*60)
            logger.info("Imdexing complete! The Knowledgebase is ready.")
            logger.info(f"Total chunks indexed: {len(all_splits)}")
            logger.info("="*60)
        except Exception as exc:
            logger.error(f"Failed to upload the documents to Azure Search {exc}")
            logger.error("Please check your Azure Search configuration and try again.")
    else:
        logger.warning("No documents were processed.")

if __name__ == "__main__":
    index_docs()