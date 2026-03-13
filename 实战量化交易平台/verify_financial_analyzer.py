import polars as pl
from loguru import logger
from core.strategy.financial_analyzer import EnhancedFinancialAnalyzer

def test_financial_analyzer():
    logger.info(">>> 开始测试: EnhancedFinancialAnalyzer (Z-Score)")
    
    # 构造模拟财务数据
    data = {
        "stock_code": ["600519", "ST001"],
        "total_assets": [1000.0, 500.0],
        "total_liabilities": [200.0, 450.0],
        "total_current_assets": [800.0, 100.0],
        "total_current_liabilities": [150.0, 400.0],
        "retained_earnings": [500.0, -50.0],
        "ebit": [300.0, 10.0],
        "market_cap": [2000.0, 100.0],
        "revenue": [400.0, 50.0]
    }
    
    df = pl.DataFrame(data)
    logger.info(f"输入数据:\n{df}")
    
    # 计算 Z-Score
    result = EnhancedFinancialAnalyzer.calculate_z_score(df)
    
    # 验证
    if "z_score" in result.columns and "z_score_rating" in result.columns:
        logger.success("✅ Z-Score 列已生成")
        logger.info(f"计算结果:\n{result.select(['stock_code', 'z_score', 'z_score_rating'])}")
        
        # 验证逻辑
        safe_stock = result.filter(pl.col("stock_code") == "600519")["z_score_rating"][0]
        distress_stock = result.filter(pl.col("stock_code") == "ST001")["z_score_rating"][0]
        
        if safe_stock == "Safe":
            logger.success("✅ 600519 评级正确 (Safe)")
        else:
            logger.warning(f"⚠️ 600519 评级异常: {safe_stock}")
            
        if distress_stock == "Distress" or distress_stock == "Grey":
             logger.success(f"✅ ST001 评级正确 ({distress_stock})")
        else:
             logger.warning(f"⚠️ ST001 评级异常: {distress_stock}")
             
    else:
        logger.error("❌ Z-Score 计算失败，列缺失")

if __name__ == "__main__":
    test_financial_analyzer()
