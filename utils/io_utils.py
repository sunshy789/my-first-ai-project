from core.document import Document
from core.tools import BaseTool
import json
import logging
def save_docs_to_json(doc_list,file_path):   #docs是document doc_list是一个doc实例组成的列表
    try:
        if not isinstance(doc_list,list):
            raise TypeError('第一个参数必须是Document实例组成的列表')
        doc_dict_list=[] #这是一的document类实例转化成的dict列表
        for doc in doc_list:
            doc_dict=doc.to_dict()    #把doc实例转化为字典
            doc_dict_list.append(doc_dict)#把字典添加进列表

            #把字典列表写入JSON文件
        with open(file_path,'w',encoding='utf-8') as f:
            json.dump(doc_dict_list,
                      f,
                      ensure_ascii=False,
                      indent=4)
            #  下面是异常捕获，先捕获具体异常
    except AttributeError as e:   #Attribute是什么错误
        logging.error(f"❌ 错误：文档实例缺少to_dict()方法",exc_info=True)
        return False
    except TypeError as e:
        logging.error(f"❌ 错误：数据类型不对",exc_info = True)
        return False
    except IOError as e:
        logging.error(f"❌ 错误：文件写入失败，权限/路径不对",exc_info = True)
        return False
    except Exception as e:
        logging.error(f"❌ 未知错误，保存失败",exc_info = True)
        return False
    else:
        logging.info(f"✅ 保存成功！共保存了{len(doc_list)}个文档到{file_path}")
        return True
    finally:
        logging.debug("保存操作执行完毕")


# ========== 全局函数：从JSON文件读取数据，转回Document实例列表 ==========
def loads_docs_from_json(file_path):
    try:
        with open(file_path,'r',encoding='utf-8') as f:
#json.load() 直接从文件里读取数据，转回Python的字典列表
            docs_dict_list=json.load(f)
            doc_list = []
            for doc_dict in docs_dict_list:
                doc_list.append(Document.from_dict(doc_dict))  #这里为啥要用Document  只是调用了一个document的方法，把doc_dict转变成实例添加入实例列表
    except FileNotFoundError:
        logging.error(f"❌ 错误：文件{file_path}不存在",exc_info=True)
        return []
    except json.JSONDecodeError:
        logging.error(f"❌ 错误：文件{file_path}格式损坏，不是合法的JSON文件",exc_info=True)
        return []
    except IOError as e:
        logging.error(f"❌ 错误：文件读取失败，详情：{e}",exc_info=True)
        return []
    except Exception as e:
        logging.error(f"❌ 未知错误，读取失败，详情：{e}",exc_info=True)
        return []
        # 无报错才执行
    else:
        logging.info(f"✅ 读取成功！共加载了{len(doc_list)}个文档")
        return doc_list
        # 无论成功失败都执行
    finally:
        logging.debug("读取操作执行完毕")
def tool_executor(tool:BaseTool,query):
    try:
        result = tool.run(query)
    except AttributeError:
        logging.error(f"❌ 错误：无效的工具，缺少可调用的run方法",exc_info=True)
        return None
    except Exception as e:
        logging.error(f"❌ 工具执行出错,详情：{e}")
        return None
    else:
        logging.info(f"✅ 工具【{tool.tool_name}】执行成功")
        return result