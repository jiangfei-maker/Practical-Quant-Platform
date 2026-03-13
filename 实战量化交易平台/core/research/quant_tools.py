import pandas as pd
import numpy as np
from scipy import stats
import statsmodels.api as sm
import logging

logger = logging.getLogger(__name__)

class QuantTools:
    """
    专业量化工具箱
    包含：去极值、标准化、中性化、IC分析、分层回测、组合优化
    """

    @staticmethod
    def winsorize(series: pd.Series, method='mad', limits=(0.01, 0.01), n=3) -> pd.Series:
        """
        去极值处理
        :param method: 'mad' (中位数绝对偏差) 或 'percentile' (百分位)
        :param limits: percentiles limits (min, max) for 'percentile' method
        :param n: n * MAD for 'mad' method
        """
        series = series.copy()
        if method == 'mad':
            median = series.median()
            mad = (series - median).abs().median()
            upper_limit = median + n * mad
            lower_limit = median - n * mad
        elif method == 'percentile':
            lower_limit = series.quantile(limits[0])
            upper_limit = series.quantile(1 - limits[1])
        else:
            raise ValueError(f"Unknown method: {method}")
        
        series = series.clip(lower=lower_limit, upper=upper_limit)
        return series

    @staticmethod
    def standardize(series: pd.Series) -> pd.Series:
        """
        Z-Score 标准化
        """
        return (series - series.mean()) / series.std()

    @staticmethod
    def neutralize(series: pd.Series, risk_factors: pd.DataFrame) -> pd.Series:
        """
        中性化处理 (剔除风险因子的影响，如行业、市值)
        :param series: 因子值 Series
        :param risk_factors: 风险因子 DataFrame (如行业哑变量、对数市值)
        """
        # 对齐数据
        common_index = series.index.intersection(risk_factors.index)
        if len(common_index) == 0:
            logger.warning("No common index for neutralization")
            return series
            
        y = series.loc[common_index]
        X = risk_factors.loc[common_index]
        
        # 添加截距项
        X = sm.add_constant(X)
        
        # OLS 回归取残差
        model = sm.OLS(y, X, missing='drop')
        results = model.fit()
        resid = results.resid
        
        # 还原索引
        out = pd.Series(index=series.index, dtype=float)
        out.loc[resid.index] = resid
        return out

    @staticmethod
    def calculate_ic(factor_data: pd.DataFrame, factor_col: str, forward_returns_col: str, method='rank') -> dict:
        """
        计算 IC (Information Coefficient)
        :param method: 'rank' (Spearman) or 'normal' (Pearson)
        """
        clean_data = factor_data[[factor_col, forward_returns_col]].dropna()
        if len(clean_data) < 10:
            return {'ic': 0, 'p_value': 1}
            
        if method == 'rank':
            corr, p_value = stats.spearmanr(clean_data[factor_col], clean_data[forward_returns_col])
        else:
            corr, p_value = stats.pearsonr(clean_data[factor_col], clean_data[forward_returns_col])
            
        return {'ic': corr, 'p_value': p_value}

    @staticmethod
    def get_factor_performance(factor_df: pd.DataFrame, factor_col: str, return_col: str, groups=5) -> dict:
        """
        因子分层回测分析
        :param factor_df: 包含因子值、下期收益率的 DataFrame
        :return: 包含 IC 序列、分层收益等统计数据
        """
        # 1. 计算 IC
        ic_data = []
        dates = factor_df['trade_date'].unique()
        dates.sort()
        
        for date in dates:
            day_data = factor_df[factor_df['trade_date'] == date]
            res = QuantTools.calculate_ic(day_data, factor_col, return_col)
            ic_data.append({'trade_date': date, 'ic': res['ic']})
            
        ic_df = pd.DataFrame(ic_data)
        ic_mean = ic_df['ic'].mean()
        ic_std = ic_df['ic'].std()
        icir = ic_mean / ic_std if ic_std != 0 else 0
        
        # 2. 分层收益
        # 按日期分组，对每日因子进行分组
        def get_group(x, n_groups):
            try:
                # qcut 可能因为数据重复报错，改用 rank + cut
                return pd.qcut(x, n_groups, labels=False, duplicates='drop')
            except:
                return pd.cut(x.rank(method='first'), n_groups, labels=False)

        factor_df['group'] = factor_df.groupby('trade_date')[factor_col].transform(lambda x: get_group(x, groups))
        
        group_ret = factor_df.groupby(['trade_date', 'group'])[return_col].mean().unstack()
        
        # 累积收益
        cum_ret = (1 + group_ret).cumprod()
        
        # 多空收益 (Top - Bottom)
        long_short_ret = group_ret[groups-1] - group_ret[0]
        long_short_cum = (1 + long_short_ret).cumprod()
        
        return {
            'ic_series': ic_df,
            'ic_stats': {'mean': ic_mean, 'std': ic_std, 'icir': icir},
            'group_returns': group_ret,
            'cum_returns': cum_ret,
            'long_short_cum': long_short_cum
        }

    @staticmethod
    def optimize_portfolio(returns_df: pd.DataFrame, method='risk_parity') -> pd.Series:
        """
        组合优化
        :param returns_df: 资产历史收益率矩阵 (index=date, columns=asset)
        :param method: 'risk_parity' (波动率倒数), 'mean_variance' (均值方差-简化版), 'equal' (等权)
        """
        assets = returns_df.columns
        n = len(assets)
        
        if method == 'equal':
            return pd.Series(1/n, index=assets)
            
        elif method == 'risk_parity':
            # 波动率倒数加权
            vols = returns_df.std()
            inv_vols = 1 / vols
            weights = inv_vols / inv_vols.sum()
            return weights
            
        elif method == 'market_cap':
            # 需要外部市值数据，此处暂不支持，退化为等权
            logger.warning("Market cap data not provided inside returns_df, using equal weight")
            return pd.Series(1/n, index=assets)
            
        return pd.Series(1/n, index=assets)
