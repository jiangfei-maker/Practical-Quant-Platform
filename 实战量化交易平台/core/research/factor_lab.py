import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Union
from loguru import logger
from .quant_tools import QuantTools

class FactorLab:
    """
    因子实验室核心引擎
    负责因子的计算、清洗、存储和提取
    支持单只股票和多只股票(Panel Data)的因子计算
    """
    
    def __init__(self):
        self.qt = QuantTools()

    def process_factors_pipeline(self, df: pd.DataFrame, factor_cols: List[str], 
                               do_winsorize=True, do_standardize=True, do_neutralize=True,
                               industry_col='industry') -> pd.DataFrame:
        """
        因子处理流水线：去极值 -> 标准化 -> 中性化 (Performance Optimized)
        """
        df = df.copy()
        valid_cols = [c for c in factor_cols if c in df.columns]
        
        # 1. 去极值 & 标准化 (向量化处理)
        for col in valid_cols:
            if do_winsorize:
                # 按日期分组处理，避免不同时间点分布差异干扰
                df[col] = df.groupby('trade_date')[col].transform(
                    lambda x: self.qt.winsorize(x, method='mad')
                )
            if do_standardize:
                df[col] = df.groupby('trade_date')[col].transform(
                    lambda x: self.qt.standardize(x)
                )
                
        # 2. 中性化 (批量处理 - 减少 concat 和 get_dummies 次数)
        if do_neutralize and industry_col in df.columns:
            dates = df['trade_date'].unique()
            results = []
            
            for date in dates:
                day_slice = df[df['trade_date'] == date].copy()
                if day_slice.empty: 
                    continue
                    
                # 仅当行业数据有效且有多样性时才中性化
                if day_slice[industry_col].nunique() > 1:
                    dummies = pd.get_dummies(day_slice[industry_col], prefix='ind')
                    dummies.index = day_slice.index
                    
                    # 批量中性化当前日期的所有因子
                    for col in valid_cols:
                        day_slice[col] = self.qt.neutralize(day_slice[col], dummies)
                
                results.append(day_slice)
            
            if results:
                df = pd.concat(results)
                    
        return df

        
    def calculate_technical_factors(self, df_price: pd.DataFrame, factors: List[str], **kwargs) -> pd.DataFrame:
        """
        计算技术类因子
        :param df_price: 包含 open, high, low, close, volume 的 DataFrame
        :param factors: 因子名称列表，如 ['MACD', 'RSI', 'MOM']
        :param kwargs: 动态参数，如 mom_window=10, vol_window=30
        """
        df = df_price.copy()
        
        # Ensure data is sorted by date for correct rolling/shift operations
        if 'trade_date' in df.columns:
            if 'stock_code' in df.columns:
                df = df.sort_values(['stock_code', 'trade_date'])
            else:
                df = df.sort_values('trade_date')
        
        # 检查是否包含多只股票 (如果有 stock_code 列)
        if 'stock_code' in df.columns and df['stock_code'].nunique() > 1:
            # 使用 groupby 进行分组计算
            # 优化: 使用循环替代 apply 以避免 FutureWarning 并提高稳定性
            results = []
            for _, group in df.groupby('stock_code'):
                results.append(self._calculate_single_stock(group.copy(), factors, **kwargs))
            return pd.concat(results)
        else:
            return self._calculate_single_stock(df, factors, **kwargs)

    def calculate_fundamental_factors(self, df_price: pd.DataFrame, df_fin: pd.DataFrame) -> pd.DataFrame:
        """
        计算基本面因子 (通过合并财务数据)
        :param df_price: 日线行情 (trade_date, stock_code, close, ...)
        :param df_fin: 财务数据 (report_date, stock_code, ...)
        """
        try:
            df = df_price.copy()
            df_f = df_fin.copy()
            
            # 1. 预处理财务数据
            # 确保有 date 列用于合并 (通常 report_date 或 publish_date)
            # 这里假设 report_date 是财报日期
            date_col = 'report_date' if 'report_date' in df_f.columns else 'date'
            if date_col not in df_f.columns:
                logger.warning("财务数据缺少日期列，无法合并")
                return df
                
            # 转换为 datetime
            if 'trade_date' in df.columns:
                df['trade_date'] = pd.to_datetime(df['trade_date'])
            if date_col in df_f.columns:
                df_f[date_col] = pd.to_datetime(df_f[date_col])
                
            # 2. 合并
            # 由于财务数据是低频的，我们需要将最近的财报数据填充到日线上
            # 方法: 对每只股票分别 merge_asof
            
            results = []
            
            # 确保列名不冲突，重命名财务数据的列 (除了 key cols)
            # 识别基本面因子列 (非 key cols)
            key_cols = ['stock_code', date_col, 'symbol']
            fin_cols = [c for c in df_f.columns if c not in key_cols]
            
            # 重命名为 factor_ 前缀以便识别
            rename_map = {c: f"factor_{c}" for c in fin_cols if not c.startswith('factor_')}
            df_f = df_f.rename(columns=rename_map)
            
            # 更新 fin_cols
            fin_cols = list(rename_map.values())
            
            groups_price = df.groupby('stock_code')
            
            # 建立 fast lookup for fin data
            # 既然是 loop price groups，不如直接 loop stocks present in price
            for stock_code, group_price in groups_price:
                group_price = group_price.sort_values('trade_date')
                
                # 找到对应的财务数据
                group_fin = df_f[df_f['stock_code'] == stock_code].sort_values(date_col)
                
                if not group_fin.empty:
                    # merge_asof: direction='backward' (默认), 找到 trade_date 之前最近的 report_date
                    merged = pd.merge_asof(
                        group_price,
                        group_fin[[date_col] + fin_cols],
                        left_on='trade_date',
                        right_on=date_col,
                        direction='backward'
                    )
                    
                    # 计算衍生因子 (如果数据存在)
                    # PE = close / eps (假设 factor_eps 存在)
                    # PB = close / bps (假设 factor_bps 存在)
                    # 注意: 这里的 eps/bps 是财务报表原始值，可能需要年化处理，这里简化处理
                    
                    # 示例: 动态计算估值因子
                    if 'factor_basic_earnings_per_share' in merged.columns and 'close' in merged.columns:
                        # 避免除以0
                        merged['factor_PE'] = merged['close'] / merged['factor_basic_earnings_per_share'].replace(0, np.nan)
                        
                    if 'factor_total_owners_equity' in merged.columns and 'factor_total_shares' in merged.columns:
                        # BPS = Equity / Shares
                        bps = merged['factor_total_owners_equity'] / merged['factor_total_shares'].replace(0, np.nan)
                        merged['factor_PB'] = merged['close'] / bps.replace(0, np.nan)
                        
                    results.append(merged)
                else:
                    results.append(group_price)
            
            if results:
                return pd.concat(results)
            return df
            
        except Exception as e:
            logger.error(f"计算基本面因子失败: {e}")
            return df_price

    def calculate_future_returns(self, df: pd.DataFrame, periods: List[int] = [1, 5, 20]) -> pd.DataFrame:
        """
        计算未来收益率 (Target)
        :param df: 包含 close, stock_code 的 DataFrame
        :param periods: 收益率周期列表，如 [1, 5, 20]
        """
        df_ret = df.copy()
        
        # 必须按股票分组计算
        if 'stock_code' in df_ret.columns and df_ret['stock_code'].nunique() > 1:
            for p in periods:
                col_name = f'next_ret_{p}d'
                # shift(-p) 取未来 p 天的价格
                # (future_price / current_price) - 1
                df_ret[col_name] = df_ret.groupby('stock_code')['close'].transform(
                    lambda x: x.shift(-p) / x - 1
                )
        else:
            # 单只股票
            for p in periods:
                col_name = f'next_ret_{p}d'
                df_ret[col_name] = df_ret['close'].shift(-p) / df_ret['close'] - 1
                
        return df_ret

    def neutralize_industry(self, df: pd.DataFrame, factor_cols: List[str], industry_map: Dict[str, str] = None) -> pd.DataFrame:
        """
        行业中性化 (Industry Neutralization)
        剔除行业 Beta 影响，保留 Alpha
        :param industry_map: 股票代码 -> 行业名称 的映射字典 (可选，如果 df 中已有 industry 列则不需要)
        """
        if df.empty:
            return df
            
        df_neu = df.copy()
        
        # 1. 确保有 industry 列
        if 'industry' not in df_neu.columns:
            if industry_map:
                df_neu['industry'] = df_neu['stock_code'].map(industry_map)
            else:
                # 尝试从 stock_basic 表获取 (如果有连接)
                # 这里假设调用方负责准备好 industry 列，或者传入 map
                logger.warning("未找到 industry 列且未传入映射，无法进行行业中性化")
                return df
                
        # 填充未知行业
        df_neu['industry'] = df_neu['industry'].fillna('Unknown')
        
        logger.info(f"开始行业中性化处理 (因子数: {len(factor_cols)})...")
        
        # 2. 按日期和行业分组，计算行业均值并减去
        # Factor_Residual = Factor - Mean(Factor)_Industry
        # 更严谨的做法是做回归取残差，但减去行业均值是常用的简化方法 (相当于仅含截距项的回归)
        
        for col in factor_cols:
            if col not in df_neu.columns:
                continue
                
            try:
                # 简单的行业去均值 (Industry Demeaning)
                # transform('mean') 会计算该股票所属日期+行业的均值
                ind_mean = df_neu.groupby(['trade_date', 'industry'])[col].transform('mean')
                df_neu[col] = df_neu[col] - ind_mean
            except Exception as e:
                logger.error(f"因子 {col} 行业中性化失败: {e}")
                
        return df_neu

    def winsorize(self, df: pd.DataFrame, factor_cols: List[str], limits: tuple = (0.01, 0.01)) -> pd.DataFrame:
        """
        去极值 (Winsorization)
        :param limits: (lower_percentile, upper_percentile), e.g., (0.01, 0.01) for 1% and 99%
        """
        df_win = df.copy()
        for col in factor_cols:
            if col not in df_win.columns: continue
            try:
                # Group by date to winsorize cross-sectionally
                # This is important: outliers are defined relative to the cross-section of that day
                def _winsorize_series(x):
                    lower = x.quantile(limits[0])
                    upper = x.quantile(1 - limits[1])
                    return x.clip(lower, upper)
                
                if 'trade_date' in df_win.columns:
                    df_win[col] = df_win.groupby('trade_date')[col].transform(_winsorize_series)
                else:
                    df_win[col] = _winsorize_series(df_win[col])
            except Exception as e:
                logger.error(f"因子 {col} 去极值失败: {e}")
        return df_win

    def standardize(self, df: pd.DataFrame, factor_cols: List[str]) -> pd.DataFrame:
        """
        标准化 (Z-Score Standardization)
        (X - Mean) / Std
        """
        df_std = df.copy()
        for col in factor_cols:
            if col not in df_std.columns: continue
            try:
                # Cross-sectional standardization by date
                if 'trade_date' in df_std.columns:
                    # 使用 transform 保持形状
                    means = df_std.groupby('trade_date')[col].transform('mean')
                    stds = df_std.groupby('trade_date')[col].transform('std')
                    # Handle zero std
                    stds = stds.replace(0, 1)
                    df_std[col] = (df_std[col] - means) / stds
                else:
                    mean = df_std[col].mean()
                    std = df_std[col].std()
                    df_std[col] = (df_std[col] - mean) / (std if std != 0 else 1)
            except Exception as e:
                logger.error(f"因子 {col} 标准化失败: {e}")
        return df_std

    def analyze_factor_performance(self, df: pd.DataFrame, factor_col: str, forward_return_col: str, quantiles: int = 5) -> Dict:
        """
        分析因子表现 (Professional Alphalens-style Analysis)
        计算 IC, Rank IC, 分层收益
        """
        if df.empty or factor_col not in df.columns or forward_return_col not in df.columns:
            return {}
            
        try:
            # Drop NaNs
            data = df[[factor_col, forward_return_col, 'trade_date']].dropna().copy()
            
            # 1. IC (Information Coefficient)
            # Pearson Correlation per day
            ic_series = data.groupby('trade_date').apply(lambda x: x[factor_col].corr(x[forward_return_col]))
            
            # Rank IC (Spearman Correlation per day)
            rank_ic_series = data.groupby('trade_date').apply(lambda x: x[factor_col].corr(x[forward_return_col], method='spearman'))
            
            # 2. Quantile Analysis (分层回测)
            # Assign quantile per day
            def _assign_quantile(x):
                try:
                    return pd.qcut(x, quantiles, labels=False, duplicates='drop')
                except:
                    return np.zeros(len(x)) # fallback
            
            data['quantile'] = data.groupby('trade_date')[factor_col].transform(_assign_quantile)
            
            # Calculate mean return per quantile per day
            quantile_ret_daily = data.groupby(['trade_date', 'quantile'])[forward_return_col].mean().reset_index()
            
            # Cumulative return per quantile
            # We pivot to have quantiles as columns
            pivot_ret = quantile_ret_daily.pivot(index='trade_date', columns='quantile', values=forward_return_col)
            cum_ret = (1 + pivot_ret).cumprod()
            
            # 3. Long-Short Return (Top - Bottom)
            # Assuming highest quantile is best (or lowest depending on factor direction)
            # We check correlation sign to determine direction
            ic_mean = ic_series.mean()
            direction = 1 if ic_mean > 0 else -1
            
            if direction > 0:
                top_q = pivot_ret.columns.max()
                bottom_q = pivot_ret.columns.min()
            else:
                top_q = pivot_ret.columns.min()
                bottom_q = pivot_ret.columns.max()
                
            ls_ret = pivot_ret[top_q] - pivot_ret[bottom_q]
            cum_ls_ret = (1 + ls_ret).cumprod()
            
            return {
                "ic_series": ic_series,
                "rank_ic_series": rank_ic_series,
                "ic_mean": ic_series.mean(),
                "ic_std": ic_series.std(),
                "ic_ir": ic_series.mean() / ic_series.std() if ic_series.std() != 0 else 0,
                "quantile_returns": pivot_ret,
                "cumulative_returns": cum_ret,
                "long_short_returns": ls_ret,
                "cumulative_long_short": cum_ls_ret
            }
            
        except Exception as e:
            logger.error(f"因子绩效分析失败: {e}")
            return {}


    def _calculate_single_stock(self, df: pd.DataFrame, factors: List[str], **kwargs) -> pd.DataFrame:
        """单只股票的因子计算逻辑"""
        # 1. Momentum (动量)
        if 'Momentum' in factors:
            try:
                window = kwargs.get('mom_window', 5)
                col_name = f'factor_mom_{window}d'
                df[col_name] = df['close'] / df['close'].shift(window) - 1
            except Exception as e:
                logger.error(f"Momentum Calculation Error: {e}")
            
        # 2. Volatility (波动率)
        if 'Volatility' in factors:
            try:
                window = kwargs.get('vol_window', 20)
                col_name = f'factor_vol_{window}d'
                # 年化波动率: std * sqrt(252)
                df[col_name] = df['close'].pct_change().rolling(window).std() * np.sqrt(252)
            except Exception as e:
                logger.error(f"Volatility Calculation Error: {e}")
        
        # 3. RSI (相对强弱指标)
        if 'RSI' in factors:
            try:
                window = kwargs.get('rsi_window', 14)
                col_name = f'factor_rsi_{window}'
                
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
                
                rs = gain / loss
                df[col_name] = 100 - (100 / (1 + rs))
            except Exception as e:
                logger.error(f"RSI Calculation Error: {e}")
            
        # 4. MACD
        if 'MACD' in factors:
            try:
                # 标准参数 12, 26, 9
                fast_period = kwargs.get('macd_fast', 12)
                slow_period = kwargs.get('macd_slow', 26)
                signal_period = kwargs.get('macd_signal', 9)
                
                ema_fast = df['close'].ewm(span=fast_period, adjust=False).mean()
                ema_slow = df['close'].ewm(span=slow_period, adjust=False).mean()
                
                df['factor_macd_line'] = ema_fast - ema_slow
                df['factor_macd_signal'] = df['factor_macd_line'].ewm(span=signal_period, adjust=False).mean()
                df['factor_macd_hist'] = df['factor_macd_line'] - df['factor_macd_signal']
            except Exception as e:
                logger.error(f"MACD Calculation Error: {e}")
            
        # 5. SMA (简单移动平均)
        if 'SMA' in factors:
            try:
                window = kwargs.get('sma_window', 20)
                df[f'factor_sma_{window}'] = df['close'].rolling(window=window).mean()
                # 衍生：价格乖离率 (Price / SMA - 1)
                df[f'factor_bias_{window}'] = df['close'] / df[f'factor_sma_{window}'] - 1
            except Exception as e:
                logger.error(f"SMA Calculation Error: {e}")

        # 6. EMA (指数移动平均)
        if 'EMA' in factors:
            try:
                window = kwargs.get('ema_window', 20)
                df[f'factor_ema_{window}'] = df['close'].ewm(span=window, adjust=False).mean()
            except Exception as e:
                logger.error(f"EMA Calculation Error: {e}")
            
        # 7. Bollinger Bands (布林带)
        if 'Bollinger' in factors:
            try:
                window = kwargs.get('bb_window', 20)
                std_dev = kwargs.get('bb_std', 2)
                sma = df['close'].rolling(window=window).mean()
                std = df['close'].rolling(window=window).std()
                
                df['factor_bb_upper'] = sma + (std * std_dev)
                df['factor_bb_lower'] = sma - (std * std_dev)
                # 布林带宽 (Bandwidth)
                df['factor_bb_width'] = (df['factor_bb_upper'] - df['factor_bb_lower']) / sma
                # 价格在布林带的位置 (%B)
                df['factor_bb_pctb'] = (df['close'] - df['factor_bb_lower']) / (df['factor_bb_upper'] - df['factor_bb_lower'])
            except Exception as e:
                logger.error(f"Bollinger Calculation Error: {e}")

        # 8. CCI (顺势指标)
        if 'CCI' in factors:
            try:
                window = kwargs.get('cci_window', 14)
                tp = (df['high'] + df['low'] + df['close']) / 3
                sma_tp = tp.rolling(window=window).mean()
                mad = tp.rolling(window=window).apply(lambda x: np.abs(x - x.mean()).mean())
                # 避免除以0
                mad = mad.replace(0, 1e-9)
                df[f'factor_cci_{window}'] = (tp - sma_tp) / (0.015 * mad)
            except Exception as e:
                logger.error(f"CCI Calculation Error: {e}")

        # 9. ROC (变动率)
        if 'ROC' in factors:
            try:
                window = kwargs.get('roc_window', 12)
                df[f'factor_roc_{window}'] = df['close'].pct_change(periods=window) * 100
            except Exception as e:
                logger.error(f"ROC Calculation Error: {e}")

        # 10. KDJ (随机指标)
        if 'KDJ' in factors:
            try:
                window = kwargs.get('kdj_window', 9)
                low_min = df['low'].rolling(window=window).min()
                high_max = df['high'].rolling(window=window).max()
                
                # RSV
                rsv = (df['close'] - low_min) / (high_max - low_min) * 100
                # K, D, J (使用 EMA 平滑，alpha=1/3)
                df['factor_kdj_k'] = rsv.ewm(com=2, adjust=False).mean()
                df['factor_kdj_d'] = df['factor_kdj_k'].ewm(com=2, adjust=False).mean()
                df['factor_kdj_j'] = 3 * df['factor_kdj_k'] - 2 * df['factor_kdj_d']
            except Exception as e:
                logger.error(f"KDJ Calculation Error: {e}")

        # 11. ATR (平均真实波幅)
        if 'ATR' in factors:
            try:
                window = kwargs.get('atr_window', 14)
                high_low = df['high'] - df['low']
                high_close = np.abs(df['high'] - df['close'].shift())
                low_close = np.abs(df['low'] - df['close'].shift())
                
                tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                df[f'factor_atr_{window}'] = tr.rolling(window=window).mean()
                # 归一化 ATR (NATR)
                df[f'factor_natr_{window}'] = df[f'factor_atr_{window}'] / df['close'] * 100
            except Exception as e:
                logger.error(f"ATR Calculation Error: {e}")

        # 12. OBV (能量潮) - 需要 volume
        if 'OBV' in factors and 'volume' in df.columns:
            try:
                obv_change = pd.Series(0, index=df.index)
                obv_change[df['close'] > df['close'].shift()] = df['volume']
                obv_change[df['close'] < df['close'].shift()] = -df['volume']
                df['factor_obv'] = obv_change.cumsum()
            except Exception as e:
                logger.error(f"OBV Calculation Error: {e}")

        # 13. VWAP (成交量加权均价) - 需要 volume 和 amount (或估算)
        if 'VWAP' in factors and 'volume' in df.columns:
            try:
                # 简单估算：使用 (H+L+C)/3 * Vol 作为成交额近似
                typical_price = (df['high'] + df['low'] + df['close']) / 3
                cum_vol = df['volume'].cumsum()
                cum_amount = (typical_price * df['volume']).cumsum()
                df['factor_vwap'] = cum_amount / cum_vol
                # 价格相对于 VWAP 的位置
                df['factor_price_vwap_ratio'] = df['close'] / df['factor_vwap']
            except Exception as e:
                logger.error(f"VWAP Calculation Error: {e}")

        # 14. Mean Reversion (均值回归/反转)
        if 'MeanReversion' in factors:
            try:
                window = kwargs.get('mr_window', 20)
                # 简单反转因子: 过去 N 日收益率的相反数
                # 逻辑: 涨多了会跌，跌多了会涨
                df[f'factor_rev_{window}'] = -1 * df['close'].pct_change(periods=window)
            except Exception as e:
                logger.error(f"MeanReversion Calculation Error: {e}")

        # --- Alpha101 Factors (Sample) ---
        # 15. Alpha006: (-1 * Correlation(Open, Volume, 10))
        if 'Alpha006' in factors:
            try:
                # 简单的相关性计算
                df['factor_alpha006'] = -1 * df['open'].rolling(10).corr(df['volume'])
            except Exception as e:
                logger.error(f"Alpha006 Calculation Error: {e}")

        # 16. Alpha012: Sign(Delta(Volume, 1)) * (-1 * Delta(Close, 1))
        if 'Alpha012' in factors:
            try:
                delta_vol = df['volume'].diff()
                delta_close = df['close'].diff()
                df['factor_alpha012'] = np.sign(delta_vol) * (-1 * delta_close)
            except Exception as e:
                logger.error(f"Alpha012 Calculation Error: {e}")
                
        # 17. Alpha101: ((Close - Open) / ((High - Low) + 0.001))
        if 'Alpha101' in factors:
            try:
                df['factor_alpha101'] = (df['close'] - df['open']) / ((df['high'] - df['low']) + 0.001)
            except Exception as e:
                logger.error(f"Alpha101 Calculation Error: {e}")

        # 17.1. Alpha001: (rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5)) - 0.5)
        # Simplified: Rank of 5-day ArgMax of something. Here we use a simplified version:
        # Rank(Close)
        if 'Alpha001' in factors:
            try:
                # Alpha001 approx: Rank(Ts_ArgMax(SignedPower(((returns < 0) ? stddev(returns, 20) : close), 2.), 5))
                # This is complex to implement exactly without a vector engine. 
                # We implement a simplified momentum-like version: Rank of 5-day max return index? No.
                # Let's use Alpha009: (0 < ts_min(delta(close, 1), 5)) ? delta(close, 1) : ((ts_max(delta(close, 1), 5) < 0) ? delta(close, 1) : (-1 * delta(close, 1)))
                # Or Alpha004: (-1 * Ts_Rank(rank(low), 9))
                
                # Alpha004: Low price rank over 9 days
                df['factor_alpha004'] = -1 * df['low'].rolling(9).rank()
            except Exception as e:
                logger.error(f"Alpha004 Calculation Error: {e}")

        # 17.2 Alpha009: 
        if 'Alpha009' in factors:
            try:
                # Simplified: if price rising consistently, follow trend, else mean revert
                delta_close = df['close'].diff()
                cond_min = delta_close.rolling(5).min() > 0
                cond_max = delta_close.rolling(5).max() < 0
                
                df['factor_alpha009'] = delta_close.copy()
                df.loc[cond_min, 'factor_alpha009'] = delta_close[cond_min]
                df.loc[cond_max, 'factor_alpha009'] = delta_close[cond_max]
                df.loc[~(cond_min | cond_max), 'factor_alpha009'] = -1 * delta_close[~(cond_min | cond_max)]
            except Exception as e:
                 logger.error(f"Alpha009 Calculation Error: {e}")

        # 17.3 Alpha054: ((-1 * ((low - close) * (open^5))) / ((low - high) * (close^5)))
        # Simplified: ((Low - Close) * (Open^5)) / ((Low - High) * (Close^5)) -> (Low - Close)/(Low - High) * (Open/Close)^5
        if 'Alpha054' in factors:
            try:
                # Avoid division by zero
                denom = (df['low'] - df['high']).replace(0, -0.0001)
                term1 = (df['low'] - df['close']) / denom
                term2 = (df['open'] / df['close']) ** 5
                df['factor_alpha054'] = -1 * term1 * term2
            except Exception as e:
                 logger.error(f"Alpha054 Calculation Error: {e}")

        # --- Money Flow Factors ---
        # 18. MFI (Money Flow Index)
        if 'MFI' in factors:
            try:
                window = kwargs.get('mfi_window', 14)
                # Typical Price
                tp = (df['high'] + df['low'] + df['close']) / 3
                # Raw Money Flow
                rmf = tp * df['volume']
                
                # Positive/Negative Money Flow
                pmf = pd.Series(0.0, index=df.index)
                nmf = pd.Series(0.0, index=df.index)
                
                tp_diff = tp.diff()
                pmf[tp_diff > 0] = rmf[tp_diff > 0]
                nmf[tp_diff < 0] = rmf[tp_diff < 0]
                
                # Money Flow Ratio
                mfr = pmf.rolling(window).sum() / nmf.rolling(window).sum()
                
                df[f'factor_mfi_{window}'] = 100 - (100 / (1 + mfr))
            except Exception as e:
                logger.error(f"MFI Calculation Error: {e}")

        # 19. CMF (Chaikin Money Flow)
        if 'CMF' in factors:
            try:
                window = kwargs.get('cmf_window', 20)
                # Money Flow Multiplier
                mfm = ((df['close'] - df['low']) - (df['high'] - df['close'])) / (df['high'] - df['low'])
                mfm = mfm.fillna(0) # handle high==low
                # Money Flow Volume
                mfv = mfm * df['volume']
                
                df[f'factor_cmf_{window}'] = mfv.rolling(window).sum() / df['volume'].rolling(window).sum()
            except Exception as e:
                logger.error(f"CMF Calculation Error: {e}")

        return df

    def calculate_fundamental_factors(self, df_price: pd.DataFrame, df_fin: pd.DataFrame) -> pd.DataFrame:
        """
        计算基本面因子 (需结合日频量价和季度财务数据)
        :param df_price: 日频量价数据 (需包含 stock_code, trade_date, close)
        :param df_fin: 财务数据 (需包含 stock_code, report_date, eps, bps, etc.)
        """
        if df_fin is None or df_fin.empty:
            logger.warning("财务数据为空，跳过基本面因子计算")
            return df_price
            
        df_p = df_price.copy()
        df_f = df_fin.copy()
        
        # 1. 格式化日期
        if 'trade_date' in df_p.columns:
            df_p['trade_date'] = pd.to_datetime(df_p['trade_date'])
        if 'report_date' in df_f.columns:
            df_f['report_date'] = pd.to_datetime(df_f['report_date'])
            
        # 2. 模拟公告日期 (为了减少前视偏差，假设财报在报告期后 45 天发布)
        # Q1(3.31)->4.30, Q2(6.30)->8.30, Q3(9.30)->10.30, Q4(12.31)->4.30
        # 这里统一加 60 天作为安全边际 (Safe Margin)
        df_f['publish_date_sim'] = df_f['report_date'] + pd.Timedelta(days=60)
            
        # 3. 按股票合并计算
        results = []
        codes = df_p['stock_code'].unique() if 'stock_code' in df_p.columns else ['Unknown']
        
        # 如果 df_p 没有 stock_code，假设是单只股票且 df_f 也是该股票
        if 'stock_code' not in df_p.columns:
             codes = [df_f['stock_code'].iloc[0]] if 'stock_code' in df_f.columns else ['Unknown']
             df_p['stock_code'] = codes[0]

        for code in codes:
            # 提取该股票数据
            sub_p = df_p[df_p['stock_code'] == code].sort_values('trade_date')
            sub_f = df_f[df_f['stock_code'] == code].sort_values('publish_date_sim')
            
            if sub_f.empty:
                results.append(sub_p)
                continue
                
            # Merge asof using simulated publish date
            # left_on=trade_date, right_on=publish_date_sim
            merged = pd.merge_asof(
                sub_p,
                sub_f,
                left_on='trade_date',
                right_on='publish_date_sim',
                direction='backward',
                suffixes=('', '_fin')
            )
            
            # 计算估值因子
            # PE = Close / EPS
            if 'eps' in merged.columns:
                merged['factor_pe'] = merged['close'] / merged['eps'].replace(0, np.nan)
            
            # PB = Close / BPS
            if 'bps' in merged.columns:
                merged['factor_pb'] = merged['close'] / merged['bps'].replace(0, np.nan)
                
            # PS (Price to Sales) = Close / (Revenue / TotalShares) 
            # 近似: MarketCap / Revenue (但这里没 MarketCap)
            # 使用: factor_ps = factor_pe * eps / (revenue_per_share) -> 复杂
            # 暂略
            
            # 直接映射财务指标
            direct_factors = ['roe', 'net_margin', 'gross_margin', 'debt_to_assets', 
                              'total_assets', 'inventory', 'revenue', 'net_profit']
            for col in direct_factors:
                if col in merged.columns:
                    merged[f'factor_{col}'] = merged[col]
            
            # 营运能力
            if 'factor_revenue' in merged.columns and 'factor_total_assets' in merged.columns:
                merged['factor_asset_turnover'] = merged['factor_revenue'] / merged['factor_total_assets'].replace(0, np.nan)
                
            if 'cogs' in merged.columns and 'factor_inventory' in merged.columns:
                merged['factor_inv_turnover'] = merged['cogs'] / merged['factor_inventory'].replace(0, np.nan)
            
            # 清理临时列
            cols_to_drop = ['publish_date_sim', 'report_date'] + [c for c in sub_f.columns if c not in ['publish_date_sim', 'report_date'] and c in merged.columns and not c.startswith('factor_')]
            # merged = merged.drop(columns=cols_to_drop, errors='ignore')
            # 保留 original price columns + factor columns
            
            results.append(merged)
            
        if not results:
            return df_p
            
        final_df = pd.concat(results)
        return final_df

    def preprocess_panel_data(self, df: pd.DataFrame, factor_cols: List[str]) -> pd.DataFrame:
        """
        因子数据预处理管线
        流程: 去极值 (Winsorization) -> 标准化 (Standardization) -> 缺失值填充 (Fillna)
        针对 Panel Data (多只股票多日数据)，按 trade_date 进行截面处理
        """
        if df.empty or 'trade_date' not in df.columns:
            return df

        df_clean = df.copy()
        
        logger.info("开始因子数据预处理 (Winsorization + Standardization)...")
        
        for col in factor_cols:
            if col not in df_clean.columns:
                continue
                
            try:
                # 1. 去极值 (MAD 法: Median Absolute Deviation)
                # 相比 3-Sigma，MAD 对异常值更鲁棒
                def clip_mad(x):
                    median = x.median()
                    mad = (x - median).abs().median()
                    # 1.4826 is the consistency constant for normal distribution
                    threshold = 3 * 1.4826 * mad 
                    upper = median + threshold
                    lower = median - threshold
                    return x.clip(lower=lower, upper=upper)

                df_clean[col] = df_clean.groupby('trade_date')[col].transform(clip_mad)
                
                # 2. 标准化 (Z-Score)
                # (x - mean) / std
                def z_score(x):
                    std = x.std()
                    if std == 0:
                        return 0
                    return (x - x.mean()) / std
                    
                df_clean[col] = df_clean.groupby('trade_date')[col].transform(z_score)
                
                # 3. 缺失值处理 (填0，即行业/市场平均水平)
                df_clean[col] = df_clean[col].fillna(0)
                
            except Exception as e:
                logger.error(f"因子 {col} 预处理失败: {e}")
        
        return df_clean

    def evaluate_batch_factors(self, factor_data: pd.DataFrame, factor_cols: List[str], forward_returns_col: str = 'next_ret') -> pd.DataFrame:
        """
        批量评估因子有效性
        :return: DataFrame 包含每个因子的 IC Mean, IC Std, ICIR, Rank IC Mean 等指标
        """
        results = []
        
        for factor in factor_cols:
            res = self.evaluate_factor_ic(factor_data, factor, forward_returns_col)
            
            if "error" not in res:
                # 区分 Panel 和 Time-Series 返回结构
                if "ic_series" in res:
                    # Panel Data
                    results.append({
                        "factor": factor,
                        "ic_mean": res['ic_mean'],
                        "ic_std": res['ic_std'],
                        "icir": res['icir'],
                        "obs_dates": res['obs_dates'],
                        "type": "Panel"
                    })
                else:
                    # Time Series Data
                    results.append({
                        "factor": factor,
                        "ic_mean": res['rank_ic'], # 使用 Rank IC 作为主要指标
                        "ic_std": 0.0, # 时序数据无截面标准差
                        "icir": 0.0,
                        "obs_dates": res['obs_count'],
                        "type": "Time-Series"
                    })
        
        if not results:
            return pd.DataFrame()
            
        df_res = pd.DataFrame(results)
        # 按 ICIR 绝对值排序
        df_res['abs_icir'] = df_res['icir'].abs()
        df_res = df_res.sort_values('abs_icir', ascending=False).drop(columns=['abs_icir'])
        
        return df_res

    def evaluate_factor_ic(self, factor_data: pd.DataFrame, factor_col: str, forward_returns_col: str = 'next_ret') -> Dict:
        """
        计算因子的 IC (Information Coefficient) 分析指标
        支持横截面 IC (Cross-Sectional IC)
        :param factor_data: 包含因子值、收益率和日期(trade_date)的 DataFrame
        """
        try:
            # 必需列检查
            required_cols = [factor_col, forward_returns_col]
            if 'trade_date' in factor_data.columns:
                is_panel = True
                required_cols.append('trade_date')
            else:
                is_panel = False
                
            df = factor_data[required_cols].dropna()
            
            if df.empty:
                return {}
            
            if is_panel and df['trade_date'].nunique() > 1:
                # --- Cross-Sectional IC (每日截面 IC) ---
                # 按日期分组，计算当天的 Rank IC
                def calc_daily_ic(group):
                    if len(group) < 2: # 至少需要2个样本才能计算相关性
                        return np.nan
                    return group[factor_col].corr(group[forward_returns_col], method='spearman')
                
                ic_dict = {}
                for date, group in df.groupby('trade_date'):
                    ic_dict[date] = calc_daily_ic(group)
                ic_series = pd.Series(ic_dict)
                ic_series.index.name = 'trade_date'
                ic_series = ic_series.dropna()
                
                if ic_series.empty:
                     return {"error": "样本不足，无法计算截面 IC"}

                ic_mean = ic_series.mean()
                ic_std = ic_series.std()
                icir = ic_mean / ic_std if ic_std != 0 else 0
                
                # 计算累计 IC
                ic_cumsum = ic_series.cumsum()
                
                return {
                    "ic_series": ic_series, # Series with index=date
                    "ic_cumsum": ic_cumsum,
                    "ic_mean": ic_mean,
                    "ic_std": ic_std,
                    "icir": icir,
                    "obs_dates": len(ic_series)
                }
            else:
                # --- Time-Series IC (单只股票或不区分日期的全局 IC) ---
                ic = df[factor_col].corr(df[forward_returns_col])
                rank_ic = df[factor_col].corr(df[forward_returns_col], method='spearman')
                
                return {
                    "ic": ic,
                    "rank_ic": rank_ic,
                    "obs_count": len(df),
                    "note": "全局/时序 IC (非截面)"
                }
            
        except Exception as e:
            logger.error(f"IC 计算失败: {e}")
            return {"error": str(e)}

    def get_quantile_returns(self, factor_data: pd.DataFrame, factor_col: str, forward_returns_col: str = 'next_ret', quantiles: int = 5) -> pd.DataFrame:
        """
        计算分层回测收益 (Quantile Returns)
        :param quantiles: 分层数量，例如 5 表示分为 5 组 (Top 20% ... Bottom 20%)
        """
        try:
            df = factor_data[[factor_col, forward_returns_col, 'trade_date']].dropna().copy()
            
            # 每日分组
            def get_group(x):
                if len(x) < quantiles:
                    return pd.Series([np.nan] * len(x), index=x.index)
                try:
                    return pd.qcut(x, quantiles, labels=False, duplicates='drop') + 1
                except:
                    return pd.Series([np.nan] * len(x), index=x.index)

            df['group'] = df.groupby('trade_date')[factor_col].transform(get_group)
            df = df.dropna(subset=['group'])
            
            # 计算每组每日平均收益
            group_ret = df.groupby(['trade_date', 'group'])[forward_returns_col].mean().unstack()
            
            # 计算累计收益
            group_cum_ret = (1 + group_ret).cumprod() - 1
            
            return group_cum_ret
            
        except Exception as e:
            logger.error(f"分层回测失败: {e}")
            return pd.DataFrame()
