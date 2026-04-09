\# My First AI Application Project



\## 项目简介

这是我的第一个AI应用开发项目，包含大模型API调用客户端和一个简易的RAG（检索增强生成）问答系统。



\## 技术栈

\- Python 3.10+

\- 大模型API：通义千问/DeepSeek

\- 核心库：requests, json, logging



\## 项目功能

1\. \*\*LLMClient类\*\*：封装了大模型API调用，支持重试机制、超时处理、异常捕获、日志记录

2\. \*\*简易RAG系统\*\*：支持加载本地知识库文档，基于参考文档回答用户问题



\## 快速开始

1\. 克隆仓库到本地

2\. 安装依赖：`pip install requests`

3\. 创建 `.env` 文件，填入你的API密钥

4\. 运行 `python rag\_demo.py`



\## 项目结构

my-first-ai-project/

├── llm\_client.py # 大模型 API 调用客户端

├── rag\_demo.py # 简易 RAG 系统

└── README.md # 项目说明文档



\## 作者

sunshy789

