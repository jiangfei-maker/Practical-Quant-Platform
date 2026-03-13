import pandas as pd
import numpy as np
from scipy.stats import norm
from typing import Tuple, Dict, Optional

class VolatilityPredictor:
    """
    波动率预测与风险评估引擎
    功能:
    1. 历史波动率计算 (Historical Volatility)
    2. EWMA 波动率预测 (Exponentially Weighted Moving Average)
    3. VaR (Value at Risk) 计算 (参数法 & 历史模拟法)
    """

    def __init__(self, df_hist: pd.DataFrame):
        """
        初始化
        :param df_hist: 历史行情 DataFrame, 必须包含 'close' 和 'date' 列
        """
        self.df = df_hist.sort_values('date').copy()
        # 计算对数收益率
        self.df['log_ret'] = np.log(self.df['close'] / self.df['close'].shift(1))
        self.df = self.df.dropna()

    def calculate_historical_volatility(self, window: int = 20) -> pd.Series:
        """
        计算滚动历史波动率 (年化)
        :param window: 滚动窗口
        :return: 年化波动率序列
        """
        # 每日收益率标准差 * sqrt(252)
        vol = self.df['log_ret'].rolling(window=window).std() * np.sqrt(252)
        return vol

    def calculate_ewma_volatility(self, lambda_param: float = 0.94) -> pd.Series:
        """
        计算 EWMA 波动率 (RiskMetrics 标准 lambda=0.94)
        :param lambda_param: 衰减因子
        :return: 年化波动率序列
        """
        # 使用 Pandas ewm 方法
        # span = (2 / (1 - lambda)) - 1 ? No, pandas uses alpha or span or com
        # alpha = 1 - lambda
        # var(t) = lambda * var(t-1) + (1-lambda) * r(t)^2
        
        # 简单实现：对平方收益率进行指数加权平均，然后开根号
        squared_ret = self.df['log_ret'] ** 2
        variance = squared_ret.ewm(alpha=(1 - lambda_param), adjust=False).mean()
        vol = np.sqrt(variance) * np.sqrt(252)
        return vol

    def calculate_var(self, confidence_level: float = 0.95, investment: float = 100000.0) -> Dict[str, float]:
        """
        计算当前的 VaR (风险价值)
        :param confidence_level: 置信度 (如 0.95)
        :param investment: 投资组合价值
        :return: 包含不同方法计算的 VaR 字典
        """
        if self.df.empty:
            return {}

        # 1. 参数法 VaR (Parametric VaR / Variance-Covariance Method)
        # 假设收益率服从正态分布
        # VaR = Position * Volatility * Z_score
        # 使用最近的 EWMA 波动率作为当前波动率估计
        current_vol_annual = self.calculate_ewma_volatility().iloc[-1]
        current_vol_daily = current_vol_annual / np.sqrt(252)
        
        z_score = norm.ppf(confidence_level) # 1.645 for 95%
        var_parametric = investment * current_vol_daily * z_score

        # 2. 历史模拟法 VaR (Historical Simulation VaR)
        # 直接使用历史收益率的分位数
        # Loss distribution is -returns
        historical_losses = -self.df['log_ret']
        var_historical_pct = np.percentile(historical_losses, confidence_level * 100)
        var_historical = investment * var_historical_pct

        return {
            "Parametric VaR (95%)": round(var_parametric, 2),
            "Historical VaR (95%)": round(var_historical, 2),
            "Current Volatility (Annualized)": round(current_vol_annual * 100, 2), # %
            "Z-Score": round(z_score, 2)
        }
    
    def get_volatility_cone_data(self) -> Dict[str, float]:
        """
        获取波动率锥数据 (Min, Max, Median, Current for different windows)
        用于展示波动率处于历史什么水平
        """
        windows = [20, 60, 120, 252] # 1月, 3月, 6月, 1年
        res = {}
        
        for w in windows:
            if len(self.df) < w:
                continue
            vol_series = self.calculate_historical_volatility(w)
            current = vol_series.iloc[-1]
            median = vol_series.median()
            max_v = vol_series.max()
            min_v = vol_series.min()
            
            # 百分位排名
            rank = (vol_series < current).mean() * 100
            
            res[f"W{w}"] = {
                "Current": current,
                "Median": median,
                "Max": max_v,
                "Min": min_v,
                "Rank": rank
            }
            
        return res
