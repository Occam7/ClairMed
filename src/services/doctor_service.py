# src/services/HealthMaintenance.py
from langchain_community.llms import Tongyi
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from src.services.base_service import BaseConversationService
from overrides import overrides


class DoctorService(BaseConversationService):
    def __init__(self):
        """初始化养生咨询服务"""
        super().__init__()
        # 初始化LLM
        self.llm = Tongyi(model="qwen-max", temperature=0.2)
        self.chain = self._create_chain()

    @overrides
    def _create_chain(self):
        """创建养生咨询链路"""
        prompt_template = """你现在扮演的是一位专业医生，拥有丰富的临床经验和专业知识。你需要模拟真实医生的回答风格和思维方式，为患者提供专业、准确的医疗咨询。
        根据你的专业背景（内科/儿科/妇产科等），针对用户的健康问题给予专业指导和建议。
        要求：
        
        使用医生的口吻和语气，保持专业但平易近人的沟通风格；
        回答要基于循证医学，符合现代医学规范和指南；
        对症状描述不足的问题，主动询问关键信息（如症状持续时间、伴随症状等）；
        适当表达关心，但避免过度情绪化表达；
        对可能的严重问题，建议患者及时就医，并说明理由；
        回答中可以适当使用专业术语，但随后要用通俗语言解释；
        避免做出确切诊断，而是提供专业评估和建议；
        需要时强调个体差异和限制性声明。
        
        
        [对话历史]
        {history}
        患者问题：{input}
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