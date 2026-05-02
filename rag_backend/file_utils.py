import io
import pdfplumber
from typing import Optional
def parse_file_content(file_bytes:bytes,content_type: str) ->Optional[str]:
    #函数文档注释
    """
        解析文件内容，支持 TXT 和 PDF
        :param file_bytes: 文件的二进制内容
        :param content_type: 文件的 MIME 类型（text/plain 或 application/pdf）
        :return: 解析后的纯文本内容
        """
    try:
        #txt逻辑解析
        if content_type == "text/plain":
            return file_bytes.decode("utf-8",errors = 'ignore')
        elif content_type == "application/pdf":
    # 解析 PDF 文件：用 pdfplumber 提取每一页的文字
            text_content = ""
            with io.BytesIO(file_bytes) as pdf_file:
                with pdfplumber.open(pdf_file) as pdf:
                    for page in pdf.pages:
                        page_text =page.extract_text()
                        if page_text:
                            text_content += page_text + "\n"
            return text_content
        else :
            return None
    except Exception as e:
        print(f"文件解析失败：{str(e)}")
        return None