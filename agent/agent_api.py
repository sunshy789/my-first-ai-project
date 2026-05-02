import uvicorn
import redis
import json
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Optional
from agent_with_rag import run_agent
import os
import rag_backend.config as config
#连接redis
redis_host = config.REDIS_HOST
redis_client = redis.Redis(host=redis_host, port=config.REDIS_PORT, decode_responses=True)
app = FastAPI()
#存储每个会话的对话历史（生产环境应换为Redis） ？Redis是什么

class ChatRequest(BaseModel):
    query:str
    session_id: str
@app.post("/agent/chat")
async def agent_chat(req:ChatRequest):
    sid =req.session_id
    key = f"session:{sid}"   #redis中存储的键名
    #1.从redis中读取历史
    history_json = redis_client.get(key)
    if history_json:
        #将json字符串转化为python字典
        history = json.loads(history_json)
    else:
        history = None
    #2.调用agent核心逻辑
    answer,new_history = run_agent(req.query,history)
    #将更新后的历史存入Redis，并设置过期时间
    redis_client.setex(key,config.REDIS_SESSION_TTL,json.dumps(new_history))
    return {"answer":answer}
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)