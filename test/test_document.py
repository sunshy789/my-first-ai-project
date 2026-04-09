import unittest
from core.document import Document
class TestDocument(unittest.TestCase):
    #setUp：每个测试用例前，都要执行这里的代码
    #作用：初始化测试用的实例，不用重复写
    def setUp(self):
#初始化一个同用的Doucment实例
        self.test_doc = Document(
            doc_id=999,
            content="1234567890",  # 长度固定是10，方便测试
            doc_type="txt",
            similarity=0.85
        )
#设置embedding属性
        self.test_doc.embedding = [0.1, 0.2, 0.3,0.4]
# 测试用例1：测试 __len__ 魔术方法
# 方法名必须以 test 开头，否则不会被执行
    def test_doc_length(self):
# 断言：实际结果 == 预期结果
# 预期：content是"1234567890"，长度是10
        self.assertEqual(len(self.test_doc),10) #核心断言方法 self.assertEqual(实际结果, 预期结果)	这是最常用的断言，意思是：我预期结果是 A，你实际运行结果是 B，如果 A==B，测试通过；否则测试失败	比如 self.assertEqual(len(self.test_doc), 10)，验证文档长度是不是 10
## 测试用例2：测试 get_summary 方法
    def test_doc_get_summary(self):
        self.assertEqual(self.test_doc.get_summary(5),'12345')
        # 测试2：边界场景，max_len超过内容长度（应该返回完整内容）
        self.assertEqual(self.test_doc.get_summary(20),'1234567890')
        # 测试3：边界场景，max_len=0（应该返回空字符串）
        self.assertEqual(self.test_doc.get_summary(0),'')
    # 测试用例3：测试 to_dict / from_dict 序列化/反序列化方法
    def test_doc_serialize(self):
        #第一步，实例转字典
        doc_dict = self.test_doc.to_dict()
        #第二步，字典转回实例
        new_doc = Document.from_dict(doc_dict)
        # 第三步：断言所有属性完全一致，验证序列化/反序列化没丢数据
        self.assertEqual(new_doc.doc_id, self.test_doc.doc_id)
        self.assertEqual(new_doc.content, self.test_doc.content)
        self.assertEqual(new_doc.doc_type, self.test_doc.doc_type)
        self.assertEqual(new_doc.similarity, self.test_doc.similarity)
        self.assertEqual(new_doc.embedding, self.test_doc.embedding)

# 测试用例4：测试 embedding 的 setter 方法（类型检查）
    def test_embedding_setter(self):
        self.test_doc.embedding = [0.1, 0.2, 0.3,0.4]
        assert(self.test_doc.embedding == [0.1, 0.2, 0.3,0.4])
        # 测试2：异常场景，传非列表（比如字符串），应该抛出 TypeError
        # 用 assertRaises 断言：验证代码会抛出指定的异常
        with self.assertRaises(TypeError):
            self.test_doc.embedding = "这不是列表"
            #with self.assertRaises(TypeError):：
# 专门用来测试「代码应该抛出异常」的场景
# 比如你的 embedding setter 要求必须传列表，传字符串就应该抛 TypeError，用这个断言就能验证：抛异常了才是对的，不抛异常反而测试失败
if __name__ == '__main__':
    unittest.main()