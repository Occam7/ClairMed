from langchain.schema import Document
from langchain_community.embeddings import DashScopeEmbeddings
from langchain_milvus import Milvus
from langchain_openai import OpenAIEmbeddings
from src.config.settings import settings
from pymilvus import connections
from typing import List

from src.core.processing.schemas import ProcessedChunk


class VectorDBHandler:
    def __init__(self):
        self._connect_milvus()
        self.embeddings = OpenAIEmbeddings()
        self.vector_store = Milvus(
            embedding_function=self.embeddings,
            collection_name=settings.MILVUS_COLLECTION,
            auto_id=True
        )


    @staticmethod
    def _connect_milvus():
        """
        统一管理milvus链接
        :return: void
        """
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT
        )


    def store_documents(self, sections: List[ProcessedChunk]) -> None:
        """
        将文档存储到milvus中
        :param sections: 文档列表
        :return: void
        """
        docs = [
            Document(
                page_content=chunk.content,
                metadata=chunk.metadata
            )
            for chunk in sections
        ]
        self.vector_store.add_documents(docs, auto_id=True)