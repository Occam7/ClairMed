import re,sys,os
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.config.settings import settings
from src.core.retrieval.vector_db import VectorDBHandler
from src.core.processing.schemas import ProcessedChunk  # [NEW] 明确数据模型


class DataProcessor:
    def __init__(self, content: str = None, file_path: str = None):
        """
        初始化 MarkdownSectionSplitter，可以传入 Markdown 文本或文件路径。

        :param content: Markdown 文本
        :param file_path: Markdown 文件路径
        """
        if file_path:
            with open(file_path, "r", encoding="utf-8") as f:
                self.content = f.read()
        elif content:
            self.content = content
        else:
            raise ValueError("必须提供 Markdown 文本或文件路径")

        self.sections = []
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )

        self.vector_handler = VectorDBHandler()


    @staticmethod
    def clean_html_tags(content):
        """
        清理 HTML 标签。

        :param content: 包含 HTML 标签的文本
        :return: 清理后的文本
        """

        clean_text = re.sub(r'<[^>]+>', '', content)
        return clean_text.strip()


    def split_into_sections(self, idx, content: str = None, header_line: str = None):
        """
        Split the markdown content into sections.

        :param header_line:
        :param content:
        :param idx: 当前是第几个章节

        """
        chunks = self.splitter.split_text(content)
        processed_chunks = [
            ProcessedChunk(
                content=chunk,
                metadata={
                    "header": header_line,
                    "section_id": idx,
                    "chunk_id": i + 1,
                    "chunk_type": "text"
                }
            ) for i, chunk in enumerate(chunks)
        ]
        self.sections.extend(processed_chunks)


    def split(self):
        header1_pattern = re.compile(r"^#\s*\d+\..*", re.MULTILINE)
        matches = list(header1_pattern.finditer(self.content))


        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(self.content)
            section_text = self.content[start:end].strip()

            # 第一步：提取并移除表格
            header_line = match.group().lstrip("#").strip()
            content_without_header = "\n".join(section_text.split("\n")[1:])  # 移除标题行
            soup = BeautifulSoup(content_without_header, 'html.parser')
            tables = []

            # 提取所有表格并生成描述
            for table in soup.find_all('table'):
                # 提取表格数据（与原有逻辑一致）
                caption = table.find('caption')
                title = caption.text.strip() if caption else "未命名表格"
                headers = [th.text.strip() for th in table.find_all('th')]
                rows = []
                for tr in table.find_all('tr'):
                    cells = [td.text.strip() for td in tr.find_all('td')]
                    if cells:
                        rows.append(cells)

                # 生成自然语言描述
                desc = f"{title}："
                if headers:
                    desc += "，".join(headers) + "。"
                for row in rows:
                    desc += "；".join(row) + "。"
                tables.append(desc.strip())

                # 从 soup 中移除该表格（关键步骤）
                table.decompose()

                # 第二步：清理剩余内容

            # 获取无表格的干净内容
            cleaned_content = self.clean_html_tags(str(soup))

            # 移除可能的残留空行
            cleaned_content = re.sub(r'\n{3,}', '\n\n', cleaned_content).strip()

            self.split_into_sections(i + 1, cleaned_content, header_line)


    def store_in_milvus(self):
        """
        将数据存储到 Milvus 中。
        :return: void
        """
        self.vector_handler.store_documents(self.sections)


    def get_sections(self):
        """
        获取拆分后的 Markdown 章节列表。

        :return: List[Dict]，包含标题、内容和表格
        """
        return self.sections



# 示例使用
if __name__ == "__main__":
    path = "../../../mergedMd/merged.md"  # 你的 Markdown 文件路径
    splitter = DataProcessor(file_path=path)
    splitter.split()
    splitter.store_in_milvus()


