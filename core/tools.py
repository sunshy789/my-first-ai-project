import logging
class BaseTool(object):
    def __init__(self,tool_name:str,tool_desc:str):
        self.tool_name = tool_name
        self.tool_desc = tool_desc
    def run(self,query):
        pass
    def __str__(self):
        return '工具名称是:%s 描述是%s' %(self.tool_name,self.tool_desc)
import time
import functools
def timer(func):
    @functools.wraps(func)  #functools.wraps(func) 的作用是：保留原函数的「身份信息」，让装饰后的函数看起来还是原来的函数，不会变成 wrapper。
    def wrapper(*args,**kwargs):
        start = time.time()
        result = func(*args,**kwargs) #此行指代码运行，俩参数表示可以接受任何类型的参数
        end = time.time()
        logging.info('工具执行耗时：%s秒' %(end-start))
        return result   #不管怎样，装饰器最内层一定返回函数
    return wrapper

class SearchTool(BaseTool): #query是搜索关键词
    @timer
    def run(self,query):
        return f'[搜索结果] 关于{query}的网页搜索结果'
class FileProcessTool(BaseTool):#文件路劲query
    @timer
    def run(self,query):
        return f'[文件处理] 已读取并清洗文件：{query}'
class LLMCallTool(BaseTool):
    @timer
    def run(self,query):
        return f'[大模型回答] 针对问题{query}的生成结果'
