# src/services/HealthMaintenance.py
from langchain_community.llms import Tongyi
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from src.services.base_service import BaseConversationService
from overrides import overrides


class HealthMaintenanceService(BaseConversationService):
    def __init__(self):
        """初始化养生咨询服务"""
        super().__init__()
        # 初始化LLM
        self.llm = Tongyi(model="qwen-max", temperature=0.7)
        self.chain = self._create_chain()

    @overrides
    def _create_chain(self):
        """创建养生咨询链路"""
        prompt_template = """你是一位中医养生专家，擅长针对不同体质、季节和生活习惯提供养生保健建议。

        请针对用户的问题提供专业、科学的养生建议。

        要求：
        1. 回答应尊重传统养生理念，同时符合现代医学常识；
        2. 建议应具体实用，易于执行；
        3. 适当引导用户补充更多信息以提供更精准的建议；
        4. 请你严格使用markdown格式进行输出，要求层次分明，可读性强

        [对话历史]
        {history}

        用户问题：{input}
        """

        return RunnablePassthrough.assign(
            history=lambda x: self._get_current_memory().load_memory_variables(x)["history"]
        ) | PromptTemplate.from_template(prompt_template) | self.llm | StrOutputParser()

    @overrides
    def process_input(self, query: str) -> str:
        """处理用户输入并生成回答"""
        # 如果该会话还没有标题，设置当前query为标题
        if not self.sessions[self.active_session_id]["title"]:
            self.sessions[self.active_session_id]["title"] = query.strip()[:30]

        result = self.chain.invoke({"input": query})

        memory = self._get_current_memory()
        memory.save_context({"input": query}, {"output": result})

        return result