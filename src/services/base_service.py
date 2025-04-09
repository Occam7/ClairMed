# src/services/base_service.py
from abc import ABC, abstractmethod
from langchain.memory import ConversationBufferMemory
import uuid
import logging
from src.storage.mongo_storage import MongoDBStorage, PersistentConversationMemory

logger = logging.getLogger(__name__)


class BaseConversationService(ABC):
    def __init__(self):
        """初始化会话管理"""
        # 初始化存储
        self.storage = MongoDBStorage()
        self.sessions = {}

        # 加载已存在的会话
        self._load_all_sessions()

        # 如果没有会话，创建一个新会话
        if not self.sessions:
            self.active_session_id = self._create_new_session()
        else:
            # 使用第一个会话作为活跃会话
            self.active_session_id = list(self.sessions.keys())[0]
            logger.info(f"已加载 {len(self.sessions)} 个会话，当前活跃会话: {self.active_session_id}")

    def _load_all_sessions(self):
        """从存储加载所有会话"""
        try:
            session_list = self.storage.list_sessions()
            for session_info in session_list:
                session_id = session_info.pop('session_id')

                # 创建会话对象
                self.sessions[session_id] = {
                    "memory": PersistentConversationMemory(
                        storage=self.storage,
                        session_id=session_id,
                        memory_key="history",
                        return_messages=True,
                        input_key="input",
                        output_key="output"
                    ),
                    **session_info  # 添加其他会话信息
                }

                # 允许子类扩展会话结构
                self._extend_session_structure(self.sessions[session_id])

            logger.info(f"从存储加载了 {len(session_list)} 个会话")
        except Exception as e:
            logger.error(f"加载会话时出错: {str(e)}")

    def _create_new_session(self):
        """创建新会话并返回会话ID"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "memory": PersistentConversationMemory(
                storage=self.storage,
                session_id=session_id,
                memory_key="history",
                return_messages=True,
                input_key="input",
                output_key="output"
            ),
            "title": None
        }

        # 允许子类扩展会话结构
        self._extend_session_structure(self.sessions[session_id])

        # 保存新会话到存储
        self._save_session(session_id)

        logger.info(f"创建了新会话: {session_id}")
        return session_id

    def _save_session(self, session_id):
        """保存会话信息到存储"""
        try:
            session_data = self.sessions[session_id].copy()
            self.storage.save_session(session_id, session_data)
            logger.debug(f"会话 {session_id} 已保存到存储")
        except Exception as e:
            logger.error(f"保存会话 {session_id} 时出错: {str(e)}")

    def _extend_session_structure(self, session):
        """
        扩展点：允许子类扩展会话结构
        子类可以重写此方法来添加额外的会话字段
        """
        pass

    def _get_current_memory(self):
        """获取当前活跃会话的内存"""
        active_session = self.sessions[self.active_session_id]
        return active_session["memory"]

    def switch_session(self, session_id: str):
        """切换到指定会话"""
        if session_id in self.sessions:
            self.active_session_id = session_id
            logger.info(f"切换到会话: {session_id}")
        else:
            raise ValueError(f"会话不存在: {session_id}")

    def create_and_switch_new_session(self):
        """创建新会话并切换到该会话"""
        new_id = self._create_new_session()
        self.switch_session(new_id)
        return new_id

    def delete_session(self, session_id: str):
        """删除指定会话"""
        if session_id in self.sessions:
            # 从内存中删除
            del self.sessions[session_id]

            # 从存储中删除
            self.storage.delete_session(session_id)

            # 如果删除的是当前活跃会话，切换到其他会话或创建新会话
            if session_id == self.active_session_id:
                if self.sessions:
                    self.active_session_id = list(self.sessions.keys())[0]
                else:
                    self.active_session_id = self._create_new_session()

            logger.info(f"删除了会话: {session_id}")
        else:
            raise ValueError(f"会话不存在: {session_id}")

    def get_all_session_titles(self):
        """获取所有会话的基本信息"""
        result = []
        for sid, info in self.sessions.items():
            session_info = {
                "session_id": sid,
                "title": info["title"] or "无标题"
            }
            # 允许子类添加额外信息
            self._extend_session_info(info, session_info)
            result.append(session_info)
        return result

    def _extend_session_info(self, session, session_info):
        """
        扩展点：允许子类扩展会话信息
        子类可以重写此方法来添加额外的会话信息字段
        """
        pass

    @abstractmethod
    def _create_chain(self):
        """
        创建处理链
        子类必须实现此方法
        """
        pass

    @abstractmethod
    def process_input(self, query: str) -> str:
        """
        处理用户输入
        子类必须实现此方法
        Args:
            query: 用户输入的查询
        Returns:
            str: 处理结果
        """
        pass