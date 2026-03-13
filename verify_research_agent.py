import os
import sys
from pathlib import Path

# Add '实战量化交易平台' to sys.path
project_root = Path(__file__).parent / "实战量化交易平台"
sys.path.append(str(project_root))

from loguru import logger
from services.ai_research.tools import ResearchTools
from services.ai_research.research_agent import ResearchAgent

def verify_tools():
    logger.info(">>> Verifying Research Tools")
    
    # 1. Test FinancialDB Tool
    sql = "SELECT * FROM stock_basic LIMIT 1"
    logger.info(f"Testing FinancialDB with SQL: {sql}")
    try:
        result = ResearchTools.query_financial_data(sql)
        if "stock_code" in result or "Empty DataFrame" in result: # Expecting markdown table or indication of empty
            logger.success("FinancialDB Tool verified successfully")
        else:
            logger.warning(f"FinancialDB Tool returned unexpected result: {result[:100]}...")
    except Exception as e:
        logger.error(f"FinancialDB Tool failed: {e}")

    # 2. Test WebSearch Tool
    # Note: This depends on internet and duckduckgo-search package
    query = "OpenAI"
    logger.info(f"Testing WebSearch with query: {query}")
    try:
        result = ResearchTools.search_news(query)
        logger.success(f"WebSearch returned: {result[:100]}...")
    except Exception as e:
        logger.warning(f"WebSearch failed (expected if no internet/proxy): {e}")

def verify_agent():
    logger.info(">>> Verifying Research Agent")
    
    # Check if API key exists
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("OPENAI_API_KEY not found. Testing graceful degradation.")
        agent = ResearchAgent()
        response = agent.run("Hello")
        if "Missing API Key" in response:
            logger.success("Agent correctly handled missing API key")
        else:
            logger.error(f"Agent failed to handle missing key: {response}")
    else:
        logger.info("OPENAI_API_KEY found. Testing full agent flow (dry run).")
        try:
            agent = ResearchAgent()
            if agent.agent:
                logger.success("Agent initialized successfully")
                # Optional: Run a real query if you want to consume tokens
                # response = agent.run("Who are you?")
                # logger.info(f"Agent Response: {response}")
            else:
                logger.error("Agent initialization failed despite having API key")
        except Exception as e:
            logger.error(f"Agent instantiation failed: {e}")

if __name__ == "__main__":
    verify_tools()
    verify_agent()
