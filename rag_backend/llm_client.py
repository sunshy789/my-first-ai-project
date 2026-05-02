import requests
import logging
from typing import Optional
import config
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)


class LLMClient:
    """大模型api统一调用客户端，后续RAG项目直接复用"""

    def __init__(self,
                 api_key: str,
                 model_name: str = config.LLM_MODEL_NAME,
                 time_out: int = 60,
                 max_retries: int = 3
                 ):
        self.api_key = api_key
        self.model_name = model_name
        self.time_out = time_out
        self.max_retries = max_retries
        self.api_url = f"{config.VOLCES_BASE_URL}/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        logging.info(f"LLM客户端初始化完成，模型:{self.model_name}")

    def chat(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        request_body = {
            'model': self.model_name,
            'messages': messages,
            'temperature': 0.3,
            'stream': False
        }
        # 重试逻辑缩进修正，归属于chat方法
        current_retry = 0
        while current_retry <= self.max_retries:
            try:
                response = requests.post(
                    url=self.api_url,
                    headers=self.headers,
                    json=request_body,
                    timeout=self.time_out
                )
                response.raise_for_status()
                response_json = response.json()
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
                logging.error(f"未知错误{e}", exc_info=True)
                return None
        logging.error("达到最大重试次数，请求失败")
        return None

    def stream_chat(self, prompt: str, system_prompt: Optional[str] = None):
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        request_body = {
            'model': self.model_name,
            'messages': messages,
            'temperature': 0.3,
            'stream': True
        }
        try:
            response = requests.post(
                url=self.api_url,
                headers=self.headers,
                json=request_body,
                timeout=self.time_out,
                stream=True
            )
            response.raise_for_status()
            for line in response.iter_lines():
                if not line:
                    continue
                line_str = line.decode('utf-8').strip('data: ')
                if line_str == '[DONE]':
                    break
                import json
                try:
                    chunk_data = json.loads(line_str)
                    chunk_text = chunk_data['choices'][0]['delta'].get('content', '')
                    if chunk_text:
                        yield chunk_text
                except:
                    continue
        except Exception as e:
            logging.error(f"流式调用错误：{str(e)}", exc_info=True)
            yield "调用失败，请稍后重试"


if __name__ == '__main__':
    API_KEY = config.VOLCES_API_KEY
    llm = LLMClient(
        api_key=API_KEY,
    )
    answer = llm.chat(prompt="什么是RAG检索增强技术？")
    if answer:
        print("大模型回答:", answer)
    print("\n===== 流式回答 =====")
    for chunk in llm.stream_chat(prompt="什么是RAG检索增强技术？"):
        print(chunk, end='', flush=True)