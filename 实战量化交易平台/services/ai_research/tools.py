from langchain_core.tools import Tool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper
from core.data.db_manager import db_manager
from loguru import logger
import json

class ResearchTools:
    
    @staticmethod
    def query_financial_data(query: str) -> str:
        """
        查询 DuckDB 中的财务数据。
        输入应该是 SQL 查询语句。
        """
        try:
            logger.info(f"执行 SQL 查询: {query}")
            conn = db_manager.get_connection()
            # 简单的安全检查
            if "DROP" in query.upper() or "DELETE" in query.upper() or "UPDATE" in query.upper():
                return "Error: 只允许查询操作 (SELECT)"
                
            # 限制返回行数
            if "LIMIT" not in query.upper():
                query += " LIMIT 10"
                
            df = conn.execute(query).df()
            if df.empty:
                return "查询结果为空"
            return df.to_markdown()
        except Exception as e:
            return f"查询失败: {e}. 请确保表名正确 (如 stock_daily_data, stock_basic, financial_statements)"

    @staticmethod
    def search_news(query: str) -> str:
        """
        搜索互联网新闻
        """
        try:
            # 优先尝试从本地数据库模糊匹配新闻
            conn = db_manager.get_connection()
            # 简单的全文检索模拟 (LIKE)
            local_news = conn.execute(f"SELECT title, content, publish_time FROM stock_news WHERE title LIKE '%{query}%' OR content LIKE '%{query}%' ORDER BY publish_time DESC LIMIT 5").df()
            
            local_result = ""
            if not local_news.empty:
                local_result = f"【本地新闻库】找到 {len(local_news)} 条相关新闻:\n" + local_news.to_markdown() + "\n\n"
            
            # 结合网络搜索 (DuckDuckGo)
            ddg = DuckDuckGoSearchAPIWrapper()
            web_result = ddg.run(query)
            
            return local_result + "【网络搜索结果】:\n" + web_result
            
        except Exception as e:
            logger.warning(f"搜索失败: {e}")
            return "搜索服务暂时不可用"
    
    @staticmethod
    def search_knowledge_base(query: str) -> str:
        """
        检索本地知识库 (RAG)
        """
        try:
            # Phase 3.2 提到构建基于 ChromaDB 的向量知识库
            # 这里先检查是否有现成的 RAG 服务接口，如果没有则返回占位符或尝试简单的文本匹配
            # 暂时实现为简单的文件搜索或返回提示，后续对接向量数据库
            
            # 模拟实现：尝试从 data/reports 目录搜索 PDF 文件名 (如果有)
            import os
            report_dir = "data/reports"
            if not os.path.exists(report_dir):
                return "本地知识库尚未初始化 (data/reports 目录不存在)"
            
            found_files = []
            for root, dirs, files in os.walk(report_dir):
                for file in files:
                    if query in file:
                        found_files.append(file)
            
            if found_files:
                return f"在本地研报库中找到以下相关文件: {', '.join(found_files[:5])}"
            else:
                return "本地知识库中未找到相关文档。"
                
        except Exception as e:
            return f"知识库检索失败: {e}"

    @staticmethod
    def get_table_schema(query: str = "") -> str:
        """
        获取数据库表结构，帮助 AI 编写正确的 SQL
        """
        try:
            conn = db_manager.get_connection()
            tables = conn.execute("SHOW TABLES").fetchall()
            schema_info = "当前数据库包含以下表:\n"
            
            target_tables = [t[0] for t in tables]
            # 如果指定了表名查询
            if query and query != "all":
                 target_tables = [t for t in target_tables if query in t]
            
            for table_name in target_tables:
                cols = conn.execute(f"DESCRIBE {table_name}").fetchall()
                col_names = [c[0] for c in cols]
                schema_info += f"- {table_name}: {', '.join(col_names)}\n"
                
            return schema_info
        except Exception as e:
            return f"获取表结构失败: {e}"

def get_tools():
    return [
        Tool(
            name="FinancialDB",
            func=ResearchTools.query_financial_data,
            description="执行 SQL 查询获取精确的财务或行情数据。输入: SELECT 语句。"
        ),
        Tool(
            name="TableSchema",
            func=ResearchTools.get_table_schema,
            description="获取数据库表结构和列名。当你不知道表名或字段名时使用。输入: 'all' 或特定表名片段。"
        ),
        Tool(
            name="NewsSearch",
            func=ResearchTools.search_news,
            description="搜索新闻和舆情。会同时检索本地新闻库和互联网。输入: 关键词。"
        ),
        Tool(
            name="KnowledgeBase",
            func=ResearchTools.search_knowledge_base,
            description="检索本地知识库(PDF研报/文档)。当用户询问特定研报内容或非公开数据时使用。输入: 关键词。"
        )
    ]
