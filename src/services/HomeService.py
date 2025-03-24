from langchain_community.llms import Tongyi
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from src.services.base_service import BaseConversationService
from overrides import overrides


class HomeService(BaseConversationService):
    def __init__(self):
        """初始化首页咨询服务"""
        super().__init__()
        # 初始化LLM
        self.llm = Tongyi(model="qwen-turbo", temperature=0.7)
        self.chain = self._create_chain()

    @overrides
    def _create_chain(self):
        """创建养生咨询链路"""
        prompt_template = """你是医学专家，现在正在为患者提供医疗建议。

        要求：
        1. 回答应清晰准确、具有指导性；
        2. 根据上下文主动提出后续问题，引导患者继续描述病情；
        3. 请你严格使用markdown格式进行输出，要求层次分明，可读性强


        [对话历史]
        {history}

        患者的问题：{input}
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