import pandas as pd
import numpy as np

class IndicatorCalculator:
    """
    技术指标计算器
    支持: MACD, RSI, KDJ, BOLL, MA
    """

    @staticmethod
    def calculate_ma(df: pd.DataFrame, window: int = 5) -> pd.Series:
        return df['close'].rolling(window=window).mean()

    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9):
        """
        计算 MACD
        返回: dif, dea, macd_hist
        """
        exp1 = df['close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['close'].ewm(span=slow, adjust=False).mean()
        dif = exp1 - exp2
        dea = dif.ewm(span=signal, adjust=False).mean()
        macd_hist = (dif - dea) * 2
        return dif, dea, macd_hist

    @staticmethod
    def calculate_kdj(df: pd.DataFrame, n: int = 9, k_smooth: int = 3, d_smooth: int = 3):
        """
        计算 KDJ
        """
        low_list = df['low'].rolling(window=n, min_periods=n).min()
        high_list = df['high'].rolling(window=n, min_periods=n).max()
        
        rsv = (df['close'] - low_list) / (high_list - low_list) * 100
        # 处理 NaN
        rsv = rsv.fillna(50)
        
        # 计算 K, D, J
        k = pd.Series(0.0, index=df.index)
        d = pd.Series(0.0, index=df.index)
        
        # 递归计算需要循环，或者使用 ewm 模拟
        # K = 2/3 * PrevK + 1/3 * RSV
        # D = 2/3 * PrevD + 1/3 * K
        
        k_values = []
        d_values = []
        k_curr = 50.0
        d_curr = 50.0
        
        for val in rsv:
            k_curr = (2/3) * k_curr + (1/3) * val
            d_curr = (2/3) * d_curr + (1/3) * k_curr
            k_values.append(k_curr)
            d_values.append(d_curr)
            
        k = pd.Series(k_values, index=df.index)
        d = pd.Series(d_values, index=df.index)
        j = 3 * k - 2 * d
        
        return k, d, j

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """
        计算 RSI
        """
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50) # Fill NaN with 50

    @staticmethod
    def calculate_boll(df: pd.DataFrame, window: int = 20, num_std: int = 2):
        """
        计算布林带
        """
        rolling_mean = df['close'].rolling(window=window).mean()
        rolling_std = df['close'].rolling(window=window).std()
        
        upper_band = rolling_mean + (rolling_std * num_std)
        lower_band = rolling_mean - (rolling_std * num_std)
        
        return upper_band, rolling_mean, lower_band
