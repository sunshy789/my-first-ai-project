import logging
import json
class Document(object):
    def __init__(self, doc_id:int, content:str,doc_type:str='txt',similarity:float=0.0): #给参数设置默认值俩种方法，一种是名字：参数类型，另外一种是强制类型检查使用isinstance不符合就报错
        self.doc_id = doc_id
        self.content = content
        self.doc_type = doc_type
        self.similarity = similarity
        self.__embedding = None
        logging.debug(f'Document类实例创建完成,doc_id={self.doc_id}')
    def __str__(self):
        return '文档ID：%s，文档类型：%s，内容摘要：%s（前20个字符）' % (self.doc_id,self.doc_type,self.content[0:20])
    def __len__(self):
        return len(self.content)
    @property
    def embedding(self):
        return self.__embedding
    @embedding.setter
    def embedding(self,value):
        if not isinstance(value,list):
            raise TypeError('value must be list')
        self.__embedding = value
    def get_summary(self,max_len):
        return self.content[:max_len]
    def to_dict(self):
        #把类所有属性，打包成一个python字典
        """把Document实例转成字典，适配JSON序列化"""
        return {
            'doc_id':self.doc_id,
            'content':self.content,
            'doc_type':self.doc_type,
            'similarity':self.similarity,
            'embedding':self.embedding
        }
    @classmethod   #fixme这个装饰器什么意思   这是类方法，不用创建实例就可以直接用Document.from_dict()调用，专门用来批量创建实例
    def from_dict(cls,doc_dict):  #doc_dict是一个字典；接受一个document类和字典
        """类方法：把字典转回Document实例"""
        #作用，接受一个字典，返回一个document实例
        #cls表示document类本身，不同自己写document，用cls更规范？fixme为啥
        doc=cls(
        doc_id = doc_dict.get('doc_id',0),   #用doc_dict.get()而不是doc_dict['key']，是为了避免字典里缺少某个 key 时，程序直接报错，更健壮
        content = doc_dict.get('content',''),
        doc_type = doc_dict.get('doc_type',''),
        similarity = doc_dict.get('similarity',0.0)
        )
        #单独给私有属性embedding赋值
        embedding = doc_dict.get('embedding')
        #只有取到的是列表时，才赋值
        if isinstance(embedding,list):
            doc.embedding = embedding
        logging.debug(f'document类实例创建完成，doc_id={doc.doc_id}')
        return doc