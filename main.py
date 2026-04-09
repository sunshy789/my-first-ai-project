from core.document import Document
from core.tools import BaseTool
import logging
from utils.io_utils import save_docs_to_json, loads_docs_from_json,tool_executor

if __name__ == '__main__':
    test_doc = Document(doc_id=1, content="测试内容", doc_type="txt", similarity=0.8) #这把document实例化
    #给实例设置embedding #test_doc是一个document实例
    test_doc.embedding = [0.1, 0.2, 0.3]
    doc_dict = test_doc.to_dict()   #这是一个doc文档字典，保存的是document转化为字典的数据
    logging.debug(f"转成的字典,{doc_dict}")
    logging.debug(f"字典的类型,{type(doc_dict)}")
    new_doc=Document.from_dict(doc_dict)
    logging.info(f"\n转回的Document实例：, {new_doc}")
    logging.info(f"实例的content属性：, {new_doc.content}")
    logging.info(f"实例的embedding属性：, {new_doc.embedding}")
    doc1 = Document(1, "RAG是检索增强生成技术", doc_type="txt", similarity=0.9)
    doc2 = Document(2, "Agent是智能体", doc_type="md", similarity=0.8)
    doc3 = Document(3, "Python是AI常用语言", doc_type="txt", similarity=0.7)
    doc1.embedding = []
    doc2.embedding = []
    doc3.embedding = []
    doc_list = [doc1, doc2, doc3]
    save_docs_to_json(doc_list,"docs.json")
    loaded_docs = loads_docs_from_json("docs.json")
    for doc in loaded_docs:
        logging.debug(doc)  # 验证__str__方法
        logging.debug(f"文档长度：{len(doc)}")  # 验证__len__方法
        logging.debug(f"内容摘要：{doc.get_summary(5)}")  # 验证get_summary方法
        logging.info("-" * 30)
        # 异常场景测试：传入无效的工具
    logging.info("\n===== 异常测试3：传入无效工具 =====")
    tool_executor("这不是一个工具", "测试query")