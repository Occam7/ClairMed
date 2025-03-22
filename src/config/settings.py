from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from dotenv import load_dotenv
load_dotenv()  # 手动加载 .env 文件

class AppSettings(BaseSettings):
    # 新增模型配置
    DEEPSEEK_API_KEY: str = Field(env="DEEPSEEK_API_KEY")
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL_NAME: str = "deepseek-chat"

    # 告诉 Pydantic 使用 .env 文件加载环境变量
    model_config = SettingsConfigDict(env_file=".env")

    # 分块配置
    CHUNK_SIZE: int = 256
    CHUNK_OVERLAP: int = 64
    MARKDOWN_HEADER_PATTERN: str = r"^#\s*\d+\..*"

    # Milvus 配置
    MILVUS_HOST: str = "localhost"
    MILVUS_PORT: int = 19530
    MILVUS_COLLECTION: str = "pharma_docs"



settings = AppSettings()
