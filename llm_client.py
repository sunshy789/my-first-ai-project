import requests
import logging
from typing import Optional

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    encoding = 'utf-8'
)

class LLMClient:
    """大模型api统一调用客户端，后续RAG项目直接复用"""
    def __init__(self,
                 api_key:str,
                 #密钥是UUID，模型名用官方默认值
                 model_name :str = "ep:",
                 time_out :int = 60,   #单词调用时间 请求超时时间：60s没响应就放弃
                 max_retries :int = 3    # 最大重新调用次数：失败自动尝试3次
                 ):
        self.api_key = api_key
        self.model_name = model_name
        self.time_out = time_out
        self.max_retries = max_retries
        #地址完全正确 火山豆包引擎API固定请求地址
        self.api_url= "https://ark.cn-beijing.volces.com/api/v3/chat/completions"

        #请求头：身份认证（必须带，否则服务器不认你）
        self.headers = {
            "Authorization":f"Bearer {self.api_key}", #密钥认证格式固定
            "Content-Type":"application/json"   #传输数据格式：json
        }
        logging.info(f"LLM客户端初始化完成，模型:{self.model_name}")
    def chat(self,prompt:str,system_prompt:Optional[str]= None) -> Optional[str]:
        """prompt：用户提问的问题
           System_prompt 系统提示词（可选，比如“你是ai助手”）"""
        messages = []
        if system_prompt:           #即system_prompt is not None
            messages.append({'role':'system','content':system_prompt})
        messages.append({'role':'user','content':prompt})
        # 大模型要求的固定格式：
        # system：设定角色
        # user：用户提问
        # 例子：[{"role": "user", "content": "什么是RAG？"}]
        request_body ={
            'model':self.model_name, #模型名称
            'messages':messages,  #对话内容
            'temperature':0.3, #随机性：0.3适合RAG（稳定，不胡编）
            'stream':False  #关闭流式输出，一次性返回结果
        }
        # temperature = 0.3：RAG
        # 项目专用参数，数值越低回答越准确

        #重试机制
        current_retry = 0
        while current_retry <= self.max_retries:
            # 网络波动、超时的时候，自动重试，不用手动重跑
            # 最多重试2次
            #发送post请求加解析结果
            try:
                response =  requests.post(
                    url = self.api_url,
                    headers = self.headers,
                    json = request_body,
                    timeout = self.time_out
                )
                response.raise_for_status() #自动抛出http错误
                response_json = response.json() #把返回来的JSON转成python字典
                answer = response_json['choices'][0]['message']['content'].strip()
                return answer
            except requests.exceptions.Timeout:
                current_retry += 1
                logging.warning(f"请求超时，第{current_retry}重试")
                continue
            except requests.exceptions.HTTPError as e:
                logging.error(f"HTTP错误，错误码{response.status_code}")
                logging.error(f"错误详情：{response.text}")
                return None
            except Exception as e:
                logging.error(f"未知错误{e}",exc_info = True)
                return None
        logging.error("达到最大重试次数，请求失败")
        return None

# requests.post：发送请求
# response.json()：解析大模型返回的结果
# 最后一行：从返回结果里提取回答文本
if __name__ == '__main__':
    API_KEY = 'API_KEY'
    llm =  LLMClient(
        api_key = API_KEY,
    )
    answer = llm.chat(prompt = "什么是RAG检索增强技术？")  #调用对话
    if answer:
        print("大模型回答:",answer)
