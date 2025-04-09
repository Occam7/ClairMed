# src/services/MedicalGuidance.py
from langchain_openai import ChatOpenAI
from langchain_community.llms import Tongyi
from langchain_deepseek import ChatDeepSeek
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables import RunnablePassthrough, RunnableBranch
from langchain_core.output_parsers import StrOutputParser
from src.core.retrieval.vector_db import VectorDBHandler
from src.services.base_service import BaseConversationService
from overrides import overrides
import uuid
import os
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
import base64
import time
import logging
logger = logging.getLogger(__name__)

class ImageProcessor:
    """处理图像的类"""

    def __init__(self):
        """初始化图像处理器"""
        # 初始化多模态模型
        self.vl_model = ChatOpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            model="qwen-vl-plus",
            temperature=0.2
        )

    def encode_image(self, image_path):
        """将图像编码为base64字符串

        Args:
            image_path (str): 图像文件的路径

        Returns:
            str: 图像的base64编码
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def process_image(self, image_path, query="请分析这张医疗图像，并描述可能的医学发现"):
        """处理医疗图像并返回分析结果

        Args:
            image_path (str): 图像文件的路径
            query (str): 发送给模型的提示词

        Returns:
            str: 图像分析结果
        """
        # 检查文件是否存在
        # if not os.path.exists(image_path):
        #     return "错误：找不到指定的图像文件"

        # 使用base64编码或直接使用image_url
        if image_path.startswith(('http://', 'https://')):
            # 如果是URL，直接使用
            image_url = image_path
            content = [
                {"type": "text", "text": query},
                {"type": "image_url", "image_url": {"url": image_url}}
            ]
        else:
            # 如果是本地文件，使用base64编码
            base64_image = self.encode_image(image_path)
            content = [
                {"type": "text", "text": query},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
            ]

        # 发送请求
        message = HumanMessage(content=content)
        response = self.vl_model.invoke([message])

        return response.content

class MedicalGuidanceService(BaseConversationService):
    def __init__(self):
        """初始化 MedicalGuidanceService 类。
        初始化向量数据库、会话容器、模型实例以及主链路。
        """
        super().__init__()
        self.vector_db = VectorDBHandler()

        # 模型初始化
        self.router_llm = Tongyi(model="qwen-turbo", temperature=0.2)
        self.medical_llm = Tongyi(model="qwen-max", temperature=0.2)
        self.general_llm = Tongyi(model="qwen-max", temperature=0.7)
        self.image_processor = ImageProcessor()

        # 路由链路
        self.router_chain = self._create_router_chain()

        # 主链路
        self.chain = self._build_main_chain()

    @overrides
    def _extend_session_structure(self, session):
        """扩展会话结构，添加科室字段"""
        session["service_type"] = "medical"

    @overrides
    def _extend_session_info(self, session, session_info):
        """扩展会话信息，添加科室信息"""
        session_info["suggested_department"] = session.get("suggested_department") or "未选择"

    def set_department(self, department: str):
        """设置当前会话的建议科室"""
        self.sessions[self.active_session_id]["suggested_department"] = department

    def _build_main_chain(self):
        """构建主处理链路。
        根据问题类型选择医学链路或通用链路。
        Returns:
            RunnableBranch: 主处理链路。
        """
        department_router_chain = self._create_department_router_chain()
        medical_chain = self._create_medical_chain()
        general_chain = self._create_general_chain()
        return RunnableBranch(
            (lambda x: x["destination"] == "medical_advice_with_department", medical_chain),
            (lambda x: x["destination"] == "medical_advice_without_department", department_router_chain),
            general_chain
        ) | StrOutputParser()

    def _create_router_chain(self):
        """创建路由链路。
        根据输入问题判断应选择的处理路径（医学或通用）。
        Returns:
            Runnable: 路由链路。
        """
        template = """根据问题类型选择处理路径：
        可选路径：
        - medical_advice: 医学健康相关问题
        - general_llm: 通用问题

        当前问题：{input}
        请只返回路径名称"""
        return PromptTemplate.from_template(template) | self.router_llm | StrOutputParser()

    @overrides
    def _create_chain(self):
        """实现基类的抽象方法
        返回主链路
        """
        return self._build_main_chain()

    def _create_department_router_chain(self):
        """
        自动引导科室选择或进行问诊
        :return: Runnable: 科室处理链路。
        """
        department_prompt = """你是一个医学分诊助手，请根据以下信息判断所属医学科室。
        请你严格使用markdown格式进行输出，要求层次分明，可读性强
        [医学知识]
        {context}

        [对话历史]
        {history}

        问题：{input}
        请输出建议您选择科室名称，并简短解释。"""
        return RunnablePassthrough.assign(
            context=lambda x: self._retrieve_context(x["input"]),
            history=lambda x: self._get_current_memory().load_memory_variables(x)["history"]
        ) | PromptTemplate.from_template(department_prompt) | self.medical_llm

    def _create_medical_chain(self):
        """创建医学问题处理链路。
        结合检索到的上下文和对话历史，生成医学问题的回答。
        Returns:
            Runnable: 医学问题处理链路。
        """
        prompt_template = """你是{department}的医学专家，现在正在为患者进行在线问诊。
        请结合下方医学知识、患者的对话历史，针对患者的问题进行专业回答，并主动引导患者补充更多信息以帮助诊断。

        要求：
        1. 回答应清晰准确、具有指导性；
        2. 根据上下文主动提出后续问题，引导患者继续描述病情；
        3. 请你严格使用markdown格式进行输出，要求层次分明，可读性强

        [医学知识]
        {context}

        [对话历史]
        {history}

        患者的问题：{input}
        """

        return RunnablePassthrough.assign(
            context=lambda x: self._retrieve_context(x["input"]),
            history=lambda x: self._get_current_memory().load_memory_variables(x)["history"],
            department=lambda x: self.sessions[self.active_session_id]["suggested_department"]
        ) | PromptTemplate.from_template(prompt_template) | self.medical_llm

    def _create_general_chain(self):
        """创建通用问题处理链路。
        根据对话历史生成通用问题的回答。
        Returns:
            Runnable: 通用问题处理链路。
        """
        prompt_template = """你是一个AI助手，根据历史对话回答问题：
        PS:请勿使用代码格式输出
        {history}
        问题：{input}"""

        return RunnablePassthrough.assign(
            history=lambda x: self._get_current_memory().load_memory_variables(x)["history"]
        ) | PromptTemplate.from_template(prompt_template) | self.general_llm

    def _retrieve_context(self, query: str) -> str:
        try:
            docs = self.vector_db.vector_store.similarity_search(
                query,
                k=3,
                fetch_k=5,  # 抓取更多，但只返回最相关的k个
                timeout=5  # 5秒超时
            )
            return "\n".join(d.page_content for d in docs)
        except Exception as e:
            self._debug_log("vector search error", {"error": str(e)})
            return ""  # 出错时返回空字符串，避免整体失败

    @overrides
    def process_input(self, query: str) -> str:
        """处理用户输入并生成回答。
        根据输入问题选择合适的处理链路，并保存对话历史。
        Args:
            query (str): 用户输入的问题。
        Returns:
            str: 生成的回答。
        """
        start_time = time.time()
        self._debug_log("input received", {"query": query})

        try:
            # 如果该会话还没有标题，设置当前 query 为标题
            if not self.sessions[self.active_session_id]["title"]:
                self.sessions[self.active_session_id]["title"] = query.strip()[:30]  # 最多保留前30字
                self._save_session(self.active_session_id)

            destination = self.router_chain.invoke({"input": query})

            if destination == "medical_advice":
                if not self.sessions[self.active_session_id]["suggested_department"]:
                    destination = destination + "_without_department"
                else:
                    destination = destination + "_with_department"

            self._debug_log("router decision", {"destination": destination})

            result = self.chain.invoke({"input": query, "destination": destination})
            self._debug_log("chain output", {"output": result[:100] + "..." if len(result) > 100 else result})

            memory = self._get_current_memory()
            memory.save_context({"input": query}, {"output": result})

            self._save_session(self.active_session_id)

            logger.info(f"会话 {self.active_session_id} 处理了用户输入")

            processing_time = time.time() - start_time
            self._debug_log("processing complete", {
                "time_taken": f"{processing_time:.2f}s",
                "output_length": len(result)
            })

            return result
        except Exception as e:
            logging.exception("Error processing input")
            return f"处理时出现错误: {str(e)}"


    def process_image_input(self, image_path: str, query: str = None) -> str:
        """处理用户上传的医疗图像并生成分析结果。

        Args:
            image_path (str): 图像文件的路径或URL
            query (str, optional): 用户关于图像的具体问题。默认为标准医疗分析提示。

        Returns:
            str: 生成的图像分析结果。
        """
        self._debug_log("image input received", {"image_path": image_path, "query": query})

        # 如果没有提供查询，使用默认提示
        if not query:
            query = "请分析这张医疗图像，识别可能的医学问题，并提供专业见解 请你严格使用markdown格式进行输出，要求层次分明，可读性强"

        # 使用图像处理器处理图像
        result = self.image_processor.process_image(image_path, query)
        self._debug_log("image analysis output", {"output": result[:100] + "..." if len(result) > 100 else result})

        # 获取当前会话科室信息，对结果进行科室相关的补充
        department = self.sessions[self.active_session_id]["suggested_department"]
        if department:
            # 使用医学模型补充科室相关信息
            enrichment_prompt = f"""
            请你严格使用markdown格式进行输出，要求层次分明，可读性强
            你是{department}的医学专家。基于以下图像分析结果，
            从{department}专业角度补充分析并给出专业建议：

            [图像分析结果]
            {result}
            """
            enriched_result = self.medical_llm.invoke(enrichment_prompt)
            result = f"{result}\n\n[{department}专业分析补充]\n{enriched_result}"

        # 保存到对话历史
        memory = self._get_current_memory()
        memory.save_context(
            {"input": f"[上传了一张医疗图像，用户问题: {query}]"},
            {"output": result}
        )

        # 如果该会话还没有标题，设置当前会话的标题
        if not self.sessions[self.active_session_id]["title"]:
            self.sessions[self.active_session_id]["title"] = "医疗图像分析" + (
                f" - {department}" if department else ""
            )

        return result



    @staticmethod
    def _debug_log(stage: str, data: dict):
        """打印调试日志。
        Args:
            stage (str): 当前阶段的名称。
            data (dict): 需要记录的调试数据。
        """
        print(f"\n[DEBUG] {stage.upper()} STAGE")
        for k, v in data.items():
            print(f"  ├─ {k}: {str(v)[:80]}{'...' if len(str(v)) > 80 else ''}")
