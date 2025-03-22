# src/services/base_service.py
from abc import ABC, abstractmethod
from langchain.memory import ConversationBufferMemory
import uuid


class BaseConversationService(ABC):
    def __init__(self):
        """初始化会话管理"""
        self.sessions = {}
        self.active_session_id = self._create_new_session()

    def _create_new_session(self):
        """创建新会话并返回会话ID"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "memory": ConversationBufferMemory(
                memory_key="history",  # 统一使用 "history" 作为 memory_key
                return_messages=True,
                input_key="input",
                output_key="output"
            ),
            "title": None
        }
        # 允许子类扩展会话结构
        self._extend_session_structure(self.sessions[session_id])
        return session_id

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
            del self.sessions[session_id]
            # 如果删除的是当前活跃会话，切换到其他会话或创建新会话
            if session_id == self.active_session_id:
                if self.sessions:
                    self.active_session_id = list(self.sessions.keys())[0]
                else:
                    self.active_session_id = self._create_new_session()
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