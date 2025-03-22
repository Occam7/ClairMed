# import streamlit as st
# from src.services.MedicalGuidance import MedicalGuidanceService
#
# # 初始化系统
# def init_systems():
#     if "llm_service" not in st.session_state:
#         st.session_state.llm_service = MedicalGuidanceService()
#     if "sessions" not in st.session_state:
#         st.session_state.sessions = st.session_state.llm_service.get_all_session_titles()
#     if "active_session_id" not in st.session_state:
#         st.session_state.active_session_id = st.session_state.llm_service.active_session_id
#     if "messages" not in st.session_state:
#         st.session_state.messages = []
#
# init_systems()
#
# # ✅ 切换会话函数
# def switch_session(session_id):
#     st.session_state.llm_service.switch_session(session_id)
#     st.session_state.active_session_id = session_id
#     st.rerun()
#
# # ✅ 创建新会话函数
# def create_new_session():
#     new_id = st.session_state.llm_service.create_and_switch_new_session()
#     st.session_state.sessions = st.session_state.llm_service.get_all_session_titles()
#     st.session_state.active_session_id = new_id
#     st.rerun()
#
# # ✅ 删除会话函数
# def delete_session(session_id):
#     st.session_state.llm_service.delete_session(session_id)
#     st.session_state.sessions = st.session_state.llm_service.get_all_session_titles()
#     st.session_state.active_session_id = st.session_state.llm_service.active_session_id
#     st.rerun()
#
# # Sidebar
# with st.sidebar:
#     st.header("💬 会话管理")
#
#     # ✅ 会话列表：显示标题+删除按钮
#     for title, session_id in st.session_state.sessions:
#         col1, col2 = st.columns([6, 1])
#         with col1:
#             if st.button(title, key=f"switch_{session_id}"):
#                 switch_session(session_id)
#         with col2:
#             if st.button("❌", key=f"delete_{session_id}", help="删除该会话"):
#                 delete_session(session_id)
#
#     # ✅ 新建会话按钮
#     if st.button("➕ 新建会话"):
#         create_new_session()
#
#     st.divider()
#     st.header("📂 知识库上传")
#     uploaded_file = st.file_uploader(
#         "上传医疗文档（支持Markdown）",
#         type=["md"],
#         help="上传医疗知识文档以增强问答能力",
#         key="file_uploader"
#     )
#
# # 主页面标题
# st.title("Merck医疗助手 💊")
#
# # 容器区
# message_container = st.container(height=800, border=False)
# button_container = st.container(height=100, border=False)
#
# # 按钮区域
# with button_container:
#     button_col1, button_col2, button_col3 = st.columns([1, 1, 1])
#     with button_col1:
#         if st.button("🗑️ 重置对话", help="清除当前会话历史", use_container_width=True):
#             st.session_state.llm_service.sessions[
#                 st.session_state.active_session_id
#             ]["memory"].clear()
#             st.rerun()
#     with button_col2:
#         if st.button("⬅ 撤回", help="撤回上一次对话", use_container_width=True):
#             st.session_state.llm_service.remove_last_interaction()
#             st.rerun()
#     with button_col3:
#         if st.button("📖 外挂知识库 [未加载]", help="发送", use_container_width=True):
#             st.session_state.llm_service.sessions[
#                 st.session_state.active_session_id
#             ]["memory"].clear()
#             st.rerun()
#
# # ✅ 获取当前会话 memory
# memory = st.session_state.llm_service.sessions[st.session_state.active_session_id]["memory"]
#
# # 聊天历史展示
# with message_container:
#     if memory:
#         for msg in memory.load_memory_variables({})["history"][-20:]:
#             role = "human" if msg.type == "human" else "ai"
#             with st.chat_message(role):
#                 st.markdown(msg.content)
#
# # ✅ 输入框和发送处理
# user_input = st.chat_input("请输入你的问题")
# if user_input:
#     with st.chat_message("human"):
#         st.write(user_input)
#
#     with st.spinner("正在思考..."):
#         response = st.session_state.llm_service.process_input(user_input)
#
#     with st.chat_message("ai"):
#         st.write(response)
#
#     # ✅ 更新会话标题显示
#     st.session_state.sessions = st.session_state.llm_service.get_all_session_titles()