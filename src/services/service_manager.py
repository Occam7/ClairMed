# service_manager.py
from src.services.MedicalGuidance import MedicalGuidanceService
from src.services.HealthMaintenanceService import HealthMaintenanceService
from src.services.MedicineInquiryService import MedicineInquiryService
from src.services.HomeService import HomeService
from src.services.doctor_service import DoctorService
from enum import Enum


class ServiceType(str, Enum):
    """服务类型枚举"""
    HOME = "home"
    MEDICAL = "medical"
    HEALTH = "health"
    MEDICINE = "medicine"
    DOCTOR = "doctor"


class ServiceManager:
    """服务管理器，统一管理不同类型的会话服务"""

    def __init__(self):
        """初始化各类服务"""
        self.services = {
            ServiceType.HOME: HomeService(),
            ServiceType.MEDICAL: MedicalGuidanceService(),
            ServiceType.HEALTH: HealthMaintenanceService(),
            ServiceType.MEDICINE: MedicineInquiryService(),
            ServiceType.DOCTOR: DoctorService()
        }
        self.active_service_type = ServiceType.HOME  # 默认使用医疗指导服务

    @property
    def active_service(self):
        """获取当前活跃的服务"""
        return self.services[self.active_service_type]

    def switch_service_type(self, service_type: ServiceType):
        """切换当前活跃的服务类型"""
        if service_type not in self.services:
            raise ValueError(f"不支持的服务类型: {service_type}")
        self.active_service_type = service_type
        return self.active_service_type

    def get_service_types(self):
        """获取所有支持的服务类型"""
        return [{"type": service_type.value, "name": self._get_service_name(service_type)}
                for service_type in self.services.keys()]

    def _get_service_name(self, service_type: ServiceType):
        """获取服务类型的友好名称"""
        names = {
            ServiceType.MEDICAL: "医疗问诊",
            ServiceType.HEALTH: "中医养生",
            ServiceType.MEDICINE: "药品咨询",
            ServiceType.HOME: "首页助手",
            ServiceType.DOCTOR: "医生咨询"

        }
        return names.get(service_type, "未知服务")

    # 代理方法，将常用操作直接代理到当前活跃的服务
    def process_input(self, query: str):
        """处理用户输入"""
        return self.active_service.process_input(query)

    def switch_session(self, session_id: str):
        """切换会话"""
        return self.active_service.switch_session(session_id)

    def create_and_switch_new_session(self):
        """创建并切换到新会话"""
        return self.active_service.create_and_switch_new_session()

    def delete_session(self, session_id: str):
        """删除会话"""
        return self.active_service.delete_session(session_id)

    def get_all_session_titles(self):
        """获取当前服务类型的所有会话标题"""
        sessions = self.active_service.get_all_session_titles()
        # 增加服务类型标记
        for session in sessions:
            session["service_type"] = self.active_service_type
        return sessions

    def get_active_session_info(self):
        """获取当前活跃会话的信息"""
        service = self.active_service
        session_id = service.active_session_id
        session = service.sessions[session_id]

        info = {
            "session_id": session_id,
            "title": session["title"] or f"[空标题] {session_id[:6]}",
            "service_type": self.active_service_type
        }

        # 如果是医疗服务，添加科室信息
        if self.active_service_type == ServiceType.MEDICAL:
            info["department"] = session.get("suggested_department") or "未设置"

        return info

    def set_department(self, department: str):
        """设置科室（仅适用于医疗服务）"""
        if self.active_service_type != ServiceType.MEDICAL:
            raise ValueError("只有医疗服务支持设置科室")
        return self.active_service.set_department(department)

    def get_session_messages(self, session_id: str):
        """获取特定会话的所有消息"""
        service = self.active_service
        if session_id not in service.sessions:
            raise ValueError(f"会话不存在: {session_id}")

        memory = service.sessions[session_id]["memory"].chat_memory.messages
        messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": message.content}
            for i, message in enumerate(memory)
        ]
        return messages

    def process_image_input(self, image_path: str, query: str = None):
        """处理用户上传的医疗图像（仅适用于医疗服务）"""
        if self.active_service_type != ServiceType.MEDICAL:
            raise ValueError("只有医疗服务支持图像分析")

        # 转换为MedicalGuidanceService类型并调用方法
        medical_service = self.services[ServiceType.MEDICAL]
        return medical_service.process_image_input(image_path, query)