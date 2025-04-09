#/src/config/settings.py
from pydantic_settings import BaseSettings
from pydantic import Field
import os

class AppSettings(BaseSettings):
    # 分块配置
    CHUNK_SIZE: int = 256
    CHUNK_OVERLAP: int = 64
    MARKDOWN_HEADER_PATTERN: str = r"^#\s*\d+\..*"

    # Milvus 配置 - 从环境变量读取，提供默认值
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "pharma_docs"

    # 让pydantic支持从环境变量读取所有设置
    class Config:
        env_prefix = ""  # 无前缀的环境变量
        case_sensitive = False  # 不区分大小写


settings = AppSettings()

