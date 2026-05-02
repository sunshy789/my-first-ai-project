import gradio as gr
import requests
import os
import uuid
import rag_backend.config as config
# 后端服务地址
BACKEND_URL = config.BACKEND_URL
AGENT_URL = config.AGENT_URL
# 全局变量存储上传后的文档ID
current_doc_id = ""


def chat_with_rag(message, history):
    """
    调用FastAPI的/rag/chat接口，严格按照接口要求传参
    """
    global current_doc_id
    try:
        # 前置校验：必须先上传文件
        if not current_doc_id:
            return "⚠️ 请先上传TXT/PDF文件，再进行提问！"
        # 前置校验：必须输入有效问题
        if not message or not message.strip():
            return "⚠️ 请输入有效的问题！"

        # 严格按照接口要求，同时传递 query 和 doc_id 两个必填参数
        params = {
            "query": message.strip(),
            "doc_id": current_doc_id
        }

        # 发送请求，增加超时避免卡死
        response = requests.get(
            f"{BACKEND_URL}/rag/chat",
            params=params,
            timeout=30
        )

        # 处理响应
        if response.status_code == 200:
            print("服务器返回：", response.text)
            return response.text
        else:
            # 打印详细错误，方便排查
            return f"❌ 接口调用失败：{response.status_code}\n详细信息：{response.text}"
    except Exception as e:
        return f"❌ 连接失败：{str(e)}"

SESSION_ID = str(uuid.uuid4())
def chat_with_agent(message,history):
      # 每次启动应用生成一个新的会话ID，实际使用中可以改为用户登录ID等
    """
    调用Agent API进行对话
    :param message:
    :param history:
    :return:
    """
    try:
        response = requests.post(
            f"{AGENT_URL}/agent/chat",#agent api地址
            json = {"query":message,"session_id":SESSION_ID},
            timeout=30
        )
        if response.status_code ==200:
            return response.json().get("answer","无回答")
        else:
            return f"❌ 接口错误：{response.status_code}"
    except Exception as e:
        return f"❌ 连接失败：{str(e)}"


def load_file(file):
    """
    调用FastAPI的/rag/upload接口，上传文件并获取doc_id
    """
    global current_doc_id
    try:
        # 前置校验：必须选择文件
        if not file:
            return "⚠️ 请先选择要上传的文件！"

        # 获取文件名和文件类型
        file_name = os.path.basename(file)
        # 根据文件后缀判断 MIME 类型
        if file_name.lower().endswith(".pdf"):
            content_type = "application/pdf"
        elif file_name.lower().endswith(".txt"):
            content_type = "text/plain"
        else:
            return "❌ 仅支持上传TXT/PDF格式文件！"

        # 打开文件，构造符合FastAPI要求的请求
        with open(file, "rb") as f:
            files = {"file": (file_name, f, content_type)}
            response = requests.post(
                f"{BACKEND_URL}/rag/upload",
                files=files,
                timeout=30
            )

        # 处理响应
        if response.status_code == 200:
            print("服务器返回：", response.text)
            result = response.json()
            # 保存上传成功后的文档ID
            current_doc_id = result["data"]["doc_id"]
            return f"✅ 上传成功！\n文件名：{result['data']['filename']}\n文档ID：{current_doc_id}"
        else:
            return f"❌ 上传失败 {response.status_code}\n详细信息：{response.text}"
    except Exception as e:
        return f"❌ 上传失败：{str(e)}"


# -------------------------- 构建Gradio界面 --------------------------
with gr.Blocks(title="简化版RAG问答系统") as demo:
    gr.Markdown("# 🤖 简化版RAG问答系统")
    gr.Markdown("### 操作流程：先上传TXT/PDF文件 → 再基于文件内容提问")

    # 第一部分：文件上传模块
    with gr.Row():
        file_input = gr.File(
            label="上传TXT/PDF文件",
            file_types=[".txt", ".pdf"],
            file_count="single"
        )
        upload_output = gr.Textbox(
            label="上传结果",
            interactive=False,
            lines=3
        )
    upload_btn = gr.Button("上传文件", variant="primary", size="lg")
    upload_btn.click(
        fn=load_file,
        inputs=file_input,
        outputs=upload_output
    )

    # 第二部分：聊天问答模块
    gr.Markdown("---")
    gr.Markdown("## 💬 开始提问")
    chat_interface = gr.ChatInterface(
        fn=chat_with_agent,
        title="",
        description="基于你上传的文档内容回答问题",
        examples=[
            ["太原理工是211吗？"],
            ["太原理工在哪里？"],
            ["太原理工始建于哪一年？"]
        ],
        cache_examples=False
    )

# 启动Gradio应用
if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True
    )