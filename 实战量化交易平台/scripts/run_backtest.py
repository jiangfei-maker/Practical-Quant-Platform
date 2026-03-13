import sys
import os
from loguru import logger

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.strategy.backtest_engine import BacktestEngine
from core.strategy.strategies.dual_ma import DualMAStrategy

def main():
    logger.info("启动回测脚本...")
    
    # 参数设置
    symbol = "600519" # 贵州茅台
    start_date = "20230101"
    end_date = "20231231"
    initial_capital = 1000000.0 # 100万
    
    logger.info(f"回测标的: {symbol}")
    logger.info(f"回测区间: {start_date} - {end_date}")
    
    # 初始化引擎
    engine = BacktestEngine(start_date, end_date, initial_capital)
    
    # 初始化策略 (5日/20日均线)
    strategy = DualMAStrategy(short_window=5, long_window=20)
    
    # 加载策略
    engine.load_strategy(strategy)
    
    # 运行回测
    engine.run(symbol)

if __name__ == "__main__":
    main()
