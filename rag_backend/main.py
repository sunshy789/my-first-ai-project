from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance
from qdrant_client import models
from llm_client import LLMClient
from fastapi.responses import StreamingResponse
import asyncio
from rank_bm25 import BM25Okapi
from fastapi import FastAPI,File,UploadFile,HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uuid
import logging
import os
import config
Distance_MAP = {
    "Cosine":Distance.COSINE,
    "Dot":Distance.DOT,
    "Euclid":Distance.EUCLID
}
# 全局初始化一次大模型客户端，不用每次请求都新建
llm_client = LLMClient(api_key=config.VOLCES_API_KEY)      #其余参数设置好默认值，可以不传，必须传api-key
#导入文件解析函数
from file_utils import parse_file_content

#配置日志
logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

)
logger  = logging.getLogger(__name__)
def chunktext(text:str,chunk_size:int=config.RAG_CHUNK_SIZE,overlap:int=config.RAG_OVERLAP)->list[str]:
    words = text.split()
    chunks=[]
    for i in range(0,len(words),chunk_size-overlap):
        chunk = ' '.join(words[i:i+chunk_size])
        chunks.append(chunk)
    return chunks

#多查询扩展
def expand_queries(original_query:str,num_queries:int = 3)->list:
    """
    调用大模型，将原始问题扩展成num_queries个不同表达的查询
    :param original_query:用户提出的原始问题
    :param num_queries:扩展问题的数量
    :return: 一个包含三个扩展问题的列表
    """
    prompt = f"""你是一个查询扩展助手。请将以下用户问题改写为{num_queries}个不同表达方式的问题，每个问题都要保留原意，但注意使用不同的措辞和角度。
每个问题单独一行，不要编号，不要加额外说明。
用户问题:{original_query}
改写的查询:
"""
    response = llm_client.chat(prompt)
    #解析response，按行分割，过滤空行
    queries = [q.strip() for q in response.strip().split('\n') if q.strip()]
    #确保返回num_queries个，不足则补充原问题
    while len(queries)<num_queries:
        queries.append(original_query)
    return queries[:num_queries]






#混合检索
def hybrid_search(query:str,doc_id:str=None,top_k:int=config.RAG_TOP_K):
    """
混合检索：向量检索+BM25关键词检索，使用RRF融合
    """
#-----------------1：向量检索--------------------------
    query_vec = encoder.encode([query]).tolist()[0]
    #新增：构造过滤条件
    query_filter = None
    if doc_id:
        query_filter = models.Filter(
            must = [models.FieldCondition(key="doc_id",match=models.MatchValue(value=doc_id))]
        )
    vector_hits = qdrant_client.query_points(
        collection_name=COLLECTION_NAME,
        query = query_vec,
        query_filter = query_filter,
        limit = config.RAG_VECTOR_LIMIT
    ).points
    #记录向量的排名
    vector_ranks = {}
    for rank,hit in enumerate(vector_hits,start=1):   #enumerate用于遍历可迭代对象，获取元素的索引和值
        text = hit.payload['text']
        vector_ranks[text] = rank
    if not vector_ranks:
        return []
    corpus = list(vector_ranks.keys()) #corpus 是候选文本块列表（即向量检索返回的 10 个文本）    .keys是字典一个内置方法，用于返回字典里的所有键
    tokenized_corpus = [doc.split() for doc in corpus]   #返回的是一个列表的列表
    bm25 = BM25Okapi(tokenized_corpus)
    tokenized_query = query.split()
    bm25_scores = bm25.get_scores(tokenized_query)
    bm25_ranked = sorted(range(len(corpus)),key = lambda i :bm25_scores[i],reverse = True)
    bm25_ranks = {}
    for rank,idx in enumerate(bm25_ranked,start=1):
        text = corpus[idx]
        bm25_ranks[text] = rank
    #-------------3.RRF融合----------------------
    k = config.RAG_RRF_K
    combined_scores = {}
    all_texts = set(vector_ranks.keys()) | set(bm25_ranks.keys())
    for text in all_texts:
        score = 0.0
        if text in vector_ranks:
            score += 1/(k+vector_ranks[text])
        if text in bm25_ranks:
            score += 1/(k+bm25_ranks[text])
        combined_scores[text] = score
    sorted_texts = sorted(combined_scores.items(),key = lambda x : x[1],reverse = True)[:top_k]  #combined_scores.items 返回一个可迭代对象，每个元素是（text，score）的元组
    return [text for text,_ in sorted_texts]


# 流式RAG生成函数
async def rag_stream_generate(doc_id: str, query: str):
    # 提取文本块
    queries = expand_queries(query)
    all_chunks = []
    for q in queries:
        chunks = hybrid_search(q,doc_id=doc_id,top_k=5)
        all_chunks.extend(chunks)
    unique_chunks = list(dict.fromkeys(all_chunks))  #保持顺序去重
    context_chunks = unique_chunks[:3]
    if not context_chunks:
        yield "未找到相关内容，请确认文档已上传且包含相关信息。"
        return
    # 5.拼接prompt
    context = "\n---\n".join(context_chunks)
    prompt = f"""
请仅根据以下给定的上下文回答用户的问题。如果上下文中没有答案，请回答「我不知道，没有找到相关信息」，不要编造内容。
===========上下文开始=========================
{context}
===========上下文结束=========================
用户问题：{query}
回答：
"""
    #6.流式调用大模型
    for chunk in llm_client.stream_chat(prompt):
        await asyncio.sleep(0.01)
        yield chunk
#初始化Fast API应用
app = FastAPI()

#连接Qdrant
qdrant_host = config.QDRANT_HOST
qdrant_client = QdrantClient(host=qdrant_host,port=config.QDRANT_PORT)
#加载embedding模型
encoder = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
#定义collection名称
COLLECTION_NAME=config.QDRANT_COLLECTION
#确保collection存在，不存在则重新创建
try:
    qdrant_client.get_collection(COLLECTION_NAME)
except Exception:
    qdrant_client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config = VectorParams(size=config.QDRANT_VECTOR_SIZE,distance=Distance_MAP[config.QDRANT_DISTANCE])
                                    )
#配置跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 核心接口：文件上传
@app.post("/rag/upload", summary="上传TXT/PDF文件并解析")
async def upload_file(file: UploadFile = File(...)):
    try:
        # 1. 校验文件格式
        if file.content_type not in ["text/plain", "application/pdf"]:
            logger.warning(f"不支持的文件格式: {file.content_type}, 文件名: {file.filename}")
            raise HTTPException(
                status_code=400,
                detail=f"仅支持上传 TXT/PDF 文件，当前格式: {file.content_type}"
            )

        # 2. 校验文件大小（100MB）
        if file.size and file.size > 100 * 1024 * 1024:
            logger.warning(f"文件过大: {file.size} bytes, 文件名: {file.filename}")
            raise HTTPException(
                status_code=413,
                detail=f"文件大小不能超过 100MB，当前文件大小: {file.size / (1024 * 1024):.2f}MB"
            )

        # 3. 读取并解析文件
        file_bytes = await file.read()
        content = parse_file_content(file_bytes, file.content_type)

        if content is None:
            logger.error(f"文件解析失败: 文件名={file.filename}")
            raise HTTPException(status_code=500, detail="文件解析失败，请检查文件是否损坏")

        # 4. 生成唯一文档ID
        doc_id = str(uuid.uuid4())
        points = []
        chunks = chunktext(content)
        for idx,chunk in enumerate(chunks):        #enumerate的作用是同时获取元素的索引和值
            vector = encoder.encode([chunk]).tolist()[0]
            point_id = str(uuid.uuid4())
            payload={
                "doc_id":doc_id,
                "text":chunk
            }
            points.append({
                "id":point_id,
                "vector":vector,
                "payload":payload
            })
        qdrant_client.upsert(
            collection_name = COLLECTION_NAME,
            points = points
        )

        # 5. 返回结果
        logger.info(f"文件上传成功: 文件名={file.filename}, doc_id={doc_id}, 文本长度={len(content)}")
        return {
            "code": 200,
            "msg": "上传成功",
            "data": {
                "doc_id": doc_id,
                "filename": file.filename,
                "chunks_count": len(chunks)
            }
        }

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"上传失败: 文件名={file.filename}, 错误={str(e)}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@app.get("/rag/chat")
async def chat(doc_id: str, query: str):
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    try:
        # 使用混合检索，传入 doc_id 实现多文档隔离，取 top3
        # context_chunks = hybrid_search(query, doc_id=doc_id, top_k=3)
        #先扩展查询
        queries = expand_queries(query)
        #对每个查询分别检索，合并结果（例如每检索“top_k = 5",最后去重取top_k)
        all_chunks = []
        for q in queries:
            chunks = hybrid_search(q,doc_id=doc_id,top_k = 5)
            all_chunks.extend(chunks)
        #去重，文本块可能相同，用set去重
        unique_chunks = list(dict.fromkeys(all_chunks))
        #截取前top_k个（例如top_k=3)
        context_chunks = unique_chunks[:3]
        if not context_chunks:
            return "未找到相关内容，请确认文档已上传且包含相关信息。"

        # 拼接上下文并构造 Prompt
        context = "\n---\n".join(context_chunks)
        prompt = f"""请仅根据以下给定的上下文回答用户的问题。如果上下文中没有答案，请回答「我不知道，没有找到相关信息」，不要编造内容。

===== 上下文开始 =====
{context}
===== 上下文结束 =====

用户问题：{query}
回答："""

        # 调用大模型（非流式）
        answer = llm_client.chat(prompt)
        if answer is None:
            raise HTTPException(status_code=500, detail="大模型调用失败")
        return answer
    except Exception as e:
        logger.error(f"聊天失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"聊天失败: {str(e)}")
#流式调用
@app.get("/rag/chat/stream")
async def rag_chat(doc_id: str, query: str):
    if not query or not query.strip():
        raise HTTPException(status_code=400,detail='问题不能空')
    try:
        return StreamingResponse(
            rag_stream_generate(doc_id, query),
            media_type = "text/plain"

        )
    except Exception as e:
        raise HTTPException(status_code=500,detail=f"提问失败：{str(e)}")
@app.get("/test_retrieve")
async def retrieve(doc_id:str,query:str):
    query_vector = encoder.encode([query]).tolist()[0]
    query_filter = models.Filter(
        must=[models.FieldCondition(key="doc_id",match=models.MatchValue(value=doc_id))]
    )
    #执行搜索
    search_result = qdrant_client.query_points(
        collection_name = COLLECTION_NAME,
        query = query_vector,
        query_filter = query_filter,
        limit = 3
    )
    context_chunks = [hit.payload["text"] for hit in search_result.points]
    if not context_chunks:
        return "未找到相关内容，请确认文档已上传且包含相关信息。"
    return context_chunks






# 健康检查接口
@app.get("/", summary="健康检查")
def health_check():
    return {"status": "ok", "message": "RAG服务已启动！"}