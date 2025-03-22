from langchain_community.llms import Tongyi
from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from src.services.base_service import BaseConversationService
from overrides import overrides



class MedicineInquiryService(BaseConversationService):
    def __init__(self):
        """初始化药品咨询服务"""
        super().__init__()
        # 初始化LLM
        self.llm = Tongyi(model="qwen-max", temperature=0.7)
        self.chain = self._create_chain()

    @overrides
    def _create_chain(self):
        """创建养生咨询链路"""
        prompt_template = """你是一位药学专家，精通各类药品的适应症、用法用量、禁忌症和不良反应。
        
        请结合下方药学知识和对话历史，针对用户的问题提供准确的用药建议。
        
        要求：
        1. 回答应严格基于循证医学，准确描述药品信息；
        2. 明确说明用药注意事项和可能的风险；
        3. 遇到需要就医的情况，建议用户及时就医；
        4. 主动询问用户年龄、既往病史、过敏史等用药相关信息；
        5. 请勿使用代码格式输出。
        
        
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



