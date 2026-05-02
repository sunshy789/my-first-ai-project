import json
from llm_client import LLMClient
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer
import rag_backend.config as config
# 初始化
llm = LLMClient(api_key=config.VOLCES_API_KEY)
qdrant_client = QdrantClient(host=config.QDRANT_HOST, port=config.QDRANT_PORT)
encoder = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
COLLECTION_NAME = config.QDRANT_COLLECTION
# ========== 1. 定义工具函数 ==========
def get_weather(city: str) -> str:
    return f"{city}今天晴天，气温25度。"
def retrieve_from_docs(query: str) -> str:
    """
    从Qdrant中检索与query最相关的文本，返回拼接后的字符串
    :param query:
    :return:
    """
    query_vector = encoder.encode([query]).tolist()[0]
    from qdrant_client import models
    query_filter = models.Filter()   #空过滤，表示不限制doc_id
    #执行搜索
    search_result = qdrant_client.query_points(
        collection_name = COLLECTION_NAME,
        query = query_vector,
        query_filter = query_filter,
        limit = 3
    )
    #提取文本块
    context_chunks = [hit.payload["text"] for hit in search_result.points]
    if not context_chunks:
        return "未找到相关内容"
    return "\n---\n".join(context_chunks)
def calculator(expression: str) -> str:
    try:
        # 用 ast.parse 做白名单校验，只在安全的数学表达式范围内求值
        import ast
        import operator
        tree = ast.parse(expression, mode='eval')
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp):
                continue       # + - * / // ** 等二元运算
            if isinstance(node, ast.UnaryOp):
                continue       # -x 等一元运算
            if isinstance(node, ast.Num):
                continue       # 数字字面量
            if isinstance(node, ast.operator):
                continue       # 运算符本身
            if isinstance(node, ast.Expression):
                continue       # 根节点
            raise ValueError(f"不安全的操作: {type(node).__name__}")
        # 在干净的命名空间里执行，没有 __builtins__，无法调用任何函数
        result = eval(
            compile(tree, '<calculator>', 'eval'),
            {"__builtins__": {}},
            {}
        )
        return f"{expression}={result}"
    except Exception as e:
        return "计算表达式有误，请重新输入"
# ========== 2. 注册工具映射 ==========
TOOLS_MAP = {
    "get_weather": get_weather,
    "retrieve_from_docs": retrieve_from_docs,
    "calculator": calculator
}
# ========== 3. 更新 system_prompt ==========
SYSTEM_PROMPT = """
你是一个智能助手，你**只能**使用以下三个工具，不能使用任何其他工具。如果用户的问题无法用这些工具回答，请回复：抱歉，我无法处理这个问题。

工具列表：
1. get_weather: 获取天气，参数 {"city": "城市名"}
2. retrieve_from_docs: 从知识库中检索信息，参数 {"query": "问题"}   (例如：问“太原理工大学是211吗”应使用此工具)
3. calculator: 进行数学计算，参数 {"expression": "计算表达式"}

返回格式必须是 JSON，例如：
{"function": "get_weather", "arguments": {"city": "北京"}}
{"function": "retrieve_from_docs", "arguments": {"query": "太原理工大学是211吗"}}
{"function": "calculator", "arguments": {"expression": "123*456"}}

只返回 JSON，不要返回其他内容。
"""
# ========== 4. 主流程（与昨天相同，无需修改） ==========
def run_agent(user_query: str,messages:list=None)->tuple[str,list]:
    """
    执行Agent对话
    参数：
    :param user_query:用户输入
    :param messages:对话历史列表，每个元素为{"role":"user/assistant","content":"..."}
    :return:
            {final_answer,updated_messages}
    """
    if messages is None:
        #初始化列表消息，包含system prompt
        messages = [
            {"role":"system","content":SYSTEM_PROMPT}
        ]
    #1.将用户问题添加到历史中
    messages.append({"role":"user","content":user_query})
    # 2. 调用模型获取工具决策（需要把当前对话历史传给模型）
    # 或者临时拼接：把 messages 中除了 system 以外的 user/assistant 拼成一个大 prompt。
    history_text=""
    for msg in messages[-4:-1]:
        if msg["role"] == "user":
            history_text+=f"用户：{msg['content']}\n"
        elif msg["role"] == "assistant":
            history_text += f"助手：{msg['content']}\n"
    decision_prompt = f"""对话历史：
    {history_text}
    当前用户问题：{user_query}

    请根据对话历史，决定调用哪个工具。如果用户问题不完整（比如只说“上海吧”），请结合历史推断完整意图。
    如果用户询问学校、大学、知识库中的内容，请使用 retrieve_from_docs 工具。

    返回格式必须为 JSON，例如：
    {{"function": "get_weather", "arguments": {{"city": "上海"}}}}
    {{"function": "retrieve_from_docs", "arguments": {{"query": "太原理工大学是211吗"}}}}
    {{"function": "calculator", "arguments": {{"expression": "2+3"}}}}

    只返回 JSON，不要有其他内容。"""
    response = llm.chat(prompt=decision_prompt, system_prompt="")
    print("[模型决策]：", response)
    try:
        tool_call = json.loads(response)
        func_name = tool_call["function"]
        args = tool_call["arguments"]
    except Exception as e:
        print("解析失败：", e)
        error_msg = "抱歉，我没能理解您的请求，请重新描述"
        #将错误信息也加入历史，保持对话连贯
        messages.append({"role":"assistant","content":error_msg})
        return error_msg, messages

    if func_name not in TOOLS_MAP:
        error_msg = f"抱歉，我不支持工具 '{func_name}'，请使用天气、文档检索或计算器。"
        messages.append({"role": "assistant", "content": error_msg})
        return error_msg, messages
    tool_result = TOOLS_MAP[func_name](**args)
    print(f"[工具执行结果]：{tool_result}")
    # ----- 生成最终回答：需要加入历史对话 -----
    # 构造包含历史的 prompt
    history_context = ""
    for msg in messages[:-1]:
        if msg["role"] == "user":
            history_context += f"用户：{msg['content']}\n"
        elif msg["role"] == "assistant":
            history_context += f"助手：{msg['content']}\n"
    final_prompt = f"""
对话历史：{history_context}
用户最新问题：{user_query}
工具返回的结果：{tool_result}
请根据对话历史和工具返回的信息，用自然语言回答用户"""
    final_answer = llm.chat(prompt=final_prompt)
    #将助手的回答添加到历史中
    messages.append({"role":"assistant","content":final_answer})
    return final_answer, messages

# if __name__ == "__main__":
#     # 测试两个场景
#     print("=== 测试天气 ===")
#     run_agent("上海天气怎么样？")
#     print("\n=== 测试文档检索 ===")
#     run_agent("太原理工大学是211吗？")
#     print("\n=== 测试计算器 ===")
#     run_agent("123 * 456 等于多少？")
if __name__ == "__main__":
    msgs = None
    while True:
        user_input = input("你：")
        if user_input.lower() in ["exit", "quit"]:
            break
        try:
            answer, msgs = run_agent(user_input, msgs)
            print("Agent：", answer)
        except Exception as e:
            print("出错：", e)
