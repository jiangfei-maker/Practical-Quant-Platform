import streamlit as st
import sys
import os

# Ensure project root is in path
current_dir = os.path.dirname(os.path.abspath(__file__))
app_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(app_dir)
sys.path.append(root_dir)

from services.ai_research.research_agent import research_agent
from app.utils import load_style

st.set_page_config(page_title="AI 投研 | 实战量化交易平台", page_icon="🧠", layout="wide")

load_style()

st.title("🧠 智能投研 (AI Research Agent)")

# API Key Config (Optional in UI)
with st.sidebar:
    st.divider()
    st.subheader("🔑 模型配置")
    api_key = st.text_input("ZhipuAI API Key", type="password", help="如果没有设置环境变量，请在此输入 Key")
    if api_key:
        os.environ["ZHIPUAI_API_KEY"] = api_key
        # Re-init agent
        from services.ai_research.research_agent import ResearchAgent
        st.session_state['agent'] = ResearchAgent()
    
    st.caption("Powered by ChatGLM-4")

    st.divider()
    st.subheader("📚 知识库管理")
    uploaded_files = st.file_uploader("上传研报/文档 (PDF/TXT)", accept_multiple_files=True, type=["pdf", "txt", "md"])
    if uploaded_files:
        from core.rag.knowledge_base import knowledge_base
        import shutil
        
        # Ensure upload dir exists
        upload_dir = os.path.join(root_dir, "data", "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        
        for uploaded_file in uploaded_files:
            file_path = os.path.join(upload_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            with st.spinner(f"正在向量化 {uploaded_file.name}..."):
                res = knowledge_base.add_document(file_path)
                if "Successfully" in res:
                    st.success(res)
                else:
                    st.error(res)

    st.divider()
    st.subheader("💡 推荐提问")
    
    st.markdown("**自然语言选股**")
    ex_select = [
        "选出市盈率小于 20 且总市值大于 100 亿的医药股",
        "筛选出 ROE 大于 15% 且净利润增长率大于 20% 的成长股",
        "查找最近一周涨幅超过 10% 的科技行业股票",
        "筛选出总市值大于 500 亿且 PB 小于 3 的银行股"
    ]
    for ex in ex_select:
        if st.button(ex, key=f"btn_{hash(ex)}"):
            st.session_state.messages.append({"role": "user", "content": ex})
            st.rerun()

    st.markdown("**数据查询与分析**")
    ex_query = [
        "贵州茅台最近一周的股价走势如何？",
        "分析一下宁德时代的最新财务状况，特别是 ROE 和毛利率",
        "最近有什么关于半导体行业的新闻？",
        "根据知识库中的研报，分析 HBM 产业链核心标的"
    ]
    for ex in ex_query:
        if st.button(ex, key=f"btn_{hash(ex)}"):
            st.session_state.messages.append({"role": "user", "content": ex})
            st.rerun()

st.info("💡 我是您的专属 AI 基金经理。支持 **自然语言选股**、**研报深度分析** (RAG) 和 **实时行情查询**。")

# Chat Interface
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Ask something about the market..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("AI 正在思考与检索 (RAG)..."):
            # Use session state agent if available, else default singleton
            agent = st.session_state.get('agent', research_agent)
            response = agent.run(prompt)
            st.markdown(response)
            
    st.session_state.messages.append({"role": "assistant", "content": response})
