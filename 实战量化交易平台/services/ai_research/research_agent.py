from zhipuai import ZhipuAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from services.ai_research.tools import get_tools
from loguru import logger
import os
import json

class ResearchAgent:
    """
    智能投研助理 (基于 Zhipu AI GLM-4)
    """
    
    def __init__(self, model_name="glm-4", temperature=0.1):
        self.tools = get_tools()
        
        # 从环境变量获取 Key
        api_key = os.getenv("ZHIPUAI_API_KEY")
        
        if not api_key:
            # 尝试从 Streamlit secrets 或硬编码 (不推荐) 获取，这里仅做警告
            logger.warning("未检测到 ZHIPUAI_API_KEY，AI 功能将不可用")
            self.client = None
        else:
            self.client = ZhipuAI(api_key=api_key)
            
        self.model_name = model_name
        self.temperature = temperature
        self.history = [] # 简单的历史记录

        logger.info(f"ResearchAgent 初始化完成 (Model: {model_name})")

    def run(self, prompt: str) -> str:
        if not self.client:
            return "AI 服务未配置: 请设置 ZHIPUAI_API_KEY 环境变量。"
            
        try:
            logger.info(f"AI Agent 接收任务: {prompt}")
            
            # 1. 构建消息上下文
            system_prompt = """你是一个专业的量化金融研究助理。你可以使用工具查询数据库和搜索网络。
            
            可用数据库表结构提示:
            1. stock_daily_data (日线行情): stock_code, trade_date, open, close, high, low, volume, pct_change, turnover_rate
            2. stock_basic (基础信息): code, name, industry, area, pe, pb, total_assets (总市值/总资产)
            3. stock_financial_indicators (财务选股指标): stock_code, report_date, eps, revenue, revenue_growth (营收增长率), net_profit, net_profit_growth (净利增长率), roe, bps
            4. financial_statements (详细财报): stock_code, report_date, revenue, net_profit, total_assets, roe 等
            5. stock_news (新闻舆情): title, content, publish_time
            
            请根据用户的问题，先思考是否需要使用工具。
            - 如果涉及选股 (如"选出科技股"、"市值大于100亿")，请使用 FinancialDB 并联合 stock_basic 表查询。
            - 如果涉及财务指标选股 (如"ROE大于15%"、"净利增长大于20%")，请优先使用 FinancialDB 并查询 stock_financial_indicators 表。
              示例: `SELECT T1.code, T1.name, T2.roe, T2.net_profit_growth FROM stock_basic T1 JOIN stock_financial_indicators T2 ON T1.code = T2.stock_code WHERE T2.roe > 15 AND T2.net_profit_growth > 20 ORDER BY T2.roe DESC LIMIT 20`
            - 如果涉及历史行情、财务数据，请优先使用 FinancialDB 工具编写 SQL 查询 (注意: 日期请使用 'YYYY-MM-DD' 格式)。
            - 如果涉及最新资讯或模糊概念，请使用 NewsSearch。
            - 如果涉及具体的研报内容、非公开文档或深度分析，请使用 KnowledgeBase。
            - 如果不确定表结构，可先使用 TableSchema。
            
            如果不需要工具，直接回答。回答请专业、客观、数据驱动。"""

            messages = [
                {"role": "system", "content": system_prompt}
            ]
            
            # 添加历史记录 (限制最近 5 轮以节省 token)
            messages.extend(self.history[-10:])
            messages.append({"role": "user", "content": prompt})
            
            # 2. 定义工具描述 (GLM-4 格式)
            tools_desc = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "查询语句或搜索关键词"
                                }
                            },
                            "required": ["query"]
                        }
                    }
                } for tool in self.tools
            ]
            
            # 3. 第一轮调用 (思考与工具选择)
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools_desc,
                tool_choice="auto",
                temperature=self.temperature
            )
            
            msg = response.choices[0].message
            
            # 4. 处理工具调用
            if msg.tool_calls:
                # 将 AI 的回复 (包含工具调用) 加入历史
                messages.append(msg.model_dump())
                
                # 执行工具
                for tool_call in msg.tool_calls:
                    func_name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    logger.info(f"调用工具: {func_name} Args: {args}")
                    
                    # 查找对应工具函数
                    tool_result = f"Error: Tool {func_name} not found"
                    for t in self.tools:
                        if t.name == func_name:
                            try:
                                tool_result = t.func(args['query'])
                            except Exception as e:
                                tool_result = f"工具执行错误: {str(e)}"
                            break
                    
                    # 将工具结果加入消息
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(tool_result)
                    })
                
                # 5. 第二轮调用 (根据工具结果生成最终回答)
                final_response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature
                )
                answer = final_response.choices[0].message.content
            else:
                # 无需工具，直接回答
                answer = msg.content
                
            # 更新历史
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": answer})
            
            return answer
            
        except Exception as e:
            logger.error(f"AI 执行失败: {e}")
            return f"执行出错: {str(e)}"

# 单例模式
research_agent = ResearchAgent()
