import polars as pl
import numpy as np
import pandas as pd
from loguru import logger
from core.strategy.factor_engine import FactorEngine
from datetime import datetime, timedelta

def generate_mock_data(stock_code: str, days: int = 100) -> pl.DataFrame:
    dates = [datetime(2023, 1, 1) + timedelta(days=i) for i in range(days)]
    # Random walk
    prices = [100.0]
    for _ in range(days - 1):
        change = np.random.normal(0, 1)
        prices.append(prices[-1] + change)
    
    df = pl.DataFrame({
        "date": dates,
        "stock_code": [stock_code] * days,
        "open": prices,
        "high": [p + abs(np.random.normal(0, 0.5)) for p in prices],
        "low": [p - abs(np.random.normal(0, 0.5)) for p in prices],
        "close": prices,
        "volume": np.random.randint(1000, 10000, days)
    })
    return df

def test_factor_engine():
    logger.info(">>> 开始测试: FactorEngine")
    
    # 1. 准备数据
    df1 = generate_mock_data("000001", 100)
    df2 = generate_mock_data("600519", 100)
    df = pl.concat([df1, df2])
    
    logger.info(f"生成测试数据: {df.shape} (包含 000001, 600519)")
    
    # 2. 初始化引擎
    engine = FactorEngine()
    engine.load_default_factors()
    
    # 3. 注册自定义因子 (测试动态扩展)
    # 例如：收盘价 / 开盘价 - 1
    engine.register_factor("daily_return", pl.col("close") / pl.col("open") - 1)
    
    # 4. 执行计算
    try:
        result = engine.calculate_group_by(df, group_col="stock_code")
        
        # 5. 验证结果
        logger.info(f"计算结果列: {result.columns}")
        
        # 检查关键因子是否存在
        expected_factors = ["mom_1m", "vol_1m", "ma_20", "daily_return"]
        for f in expected_factors:
            if f not in result.columns:
                logger.error(f"❌ 缺少因子列: {f}")
            else:
                # 检查是否有非空值 (前20行可能是 null 因为 rolling)
                non_null = result.select(pl.col(f).drop_nulls().count()).item()
                if non_null > 0:
                    logger.success(f"✅ 因子 {f} 计算成功 (非空记录: {non_null})")
                else:
                    logger.warning(f"⚠️ 因子 {f} 全为空值")
        
        # 展示部分数据
        logger.info("数据采样 (Head 5):")
        print(result.head(5))
        
        logger.info("数据采样 (Tail 5):")
        print(result.tail(5))
        
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    test_factor_engine()
