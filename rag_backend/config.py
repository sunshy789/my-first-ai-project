"""
统一配置管理模块
将所有环境变量、默认值、连接参数集中在此。
使用方式：from config import VOLCES_API_KEY, QDRANT_HOST, ...
加载顺序：先读 .env 文件，再读系统环境变量（系统环境变量优先级更高）
"""
import os
from dotenv import load_dotenv, find_dotenv

# 自动向上查找 .env 文件并加载到 os.environ，已存在的系统环境变量不会被覆盖
load_dotenv(find_dotenv())

# ========== LLM 相关配置 ==========
VOLCES_API_KEY = os.environ.get("VOLCES_API_KEY", "")          # 必填：火山引擎 API Key
VOLCES_BASE_URL = os.environ.get("VOLCES_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
LLM_MODEL_NAME = os.environ.get("LLM_MODEL_NAME", "ep-20260409093030-l25lg")

# ========== Qdrant 配置 ==========
QDRANT_HOST = os.environ.get("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", 6333))
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "rag_docs")
QDRANT_VECTOR_SIZE = int(os.environ.get("QDRANT_VECTOR_SIZE", 512))
QDRANT_DISTANCE = os.environ.get("QDRANT_DISTANCE", "Cosine")  # 可选: Cosine, Dot, Euclid

# ========== Redis 配置 ==========
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))
REDIS_SESSION_TTL = int(os.environ.get("REDIS_SESSION_TTL", 1800))  # 秒

# ========== RAG 默认参数 ==========
RAG_CHUNK_SIZE = int(os.environ.get("RAG_CHUNK_SIZE", 500))
RAG_OVERLAP = int(os.environ.get("RAG_OVERLAP", 50))
RAG_TOP_K = int(os.environ.get("RAG_TOP_K", 3))
RAG_VECTOR_LIMIT = int(os.environ.get("RAG_VECTOR_LIMIT", 10))   # 向量检索候选数
RAG_RRF_K = int(os.environ.get("RAG_RRF_K", 60))                 # RRF 融合常数
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "BAAI-bge-small-zh")
# ========== 服务端点（供 Gradio 等调用）==========
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8001")
AGENT_URL = os.environ.get("AGENT_URL", "http://localhost:8002")

# ========== 其他 ==========
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")  # development / production
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
