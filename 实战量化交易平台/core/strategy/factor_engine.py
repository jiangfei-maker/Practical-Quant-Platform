from loguru import logger
import polars as pl
from typing import List, Dict, Union, Optional

class FactorEngine:
    """
    高性能因子计算引擎 (基于 Polars)
    支持动态表达式与向量化计算
    """
    
    def __init__(self):
        self.factors = {}
        logger.info("FactorEngine 初始化完成")

    def register_factor(self, name: str, expr: pl.Expr):
        """
        注册因子表达式
        :param name: 因子名称
        :param expr: Polars 表达式
        """
        self.factors[name] = expr.alias(name)
        logger.debug(f"已注册因子: {name}")

    def load_default_factors(self):
        """加载默认因子库"""
        # 动量类
        self.register_factor("mom_1m", pl.col("close") / pl.col("close").shift(20) - 1)
        self.register_factor("mom_3m", pl.col("close") / pl.col("close").shift(60) - 1)
        
        # 波动率类
        self.register_factor("vol_1m", pl.col("close").rolling_std(window_size=20))
        
        # 均线类
        self.register_factor("ma_5", pl.col("close").rolling_mean(5))
        self.register_factor("ma_20", pl.col("close").rolling_mean(20))
        self.register_factor("bias_20", (pl.col("close") - pl.col("close").rolling_mean(20)) / pl.col("close").rolling_mean(20))
        
        # 趋势信号
        self.register_factor("trend_ma_cross", (pl.col("close") > pl.col("close").rolling_mean(60)).cast(pl.Int8))

        logger.info("默认因子库加载完成 (Momentum, Volatility, MA)")

    def calculate(self, df: pl.DataFrame, factor_names: Optional[List[str]] = None) -> pl.DataFrame:
        """
        执行因子计算
        :param df: 输入 DataFrame (必须包含 open, high, low, close, volume)
        :param factor_names: 指定计算的因子列表，None 表示全部
        :return: 包含因子列的 DataFrame
        """
        if df.is_empty():
            logger.warning("输入 DataFrame 为空，跳过计算")
            return df

        target_factors = []
        if factor_names:
            for name in factor_names:
                if name in self.factors:
                    target_factors.append(self.factors[name])
                else:
                    logger.warning(f"因子 {name} 未注册，已跳过")
        else:
            target_factors = list(self.factors.values())

        if not target_factors:
            logger.warning("没有需要计算的因子")
            return df

        logger.info(f"开始计算 {len(target_factors)} 个因子...")
        try:
            # 确保按时间排序，虽然 Polars 通常并行，但 rolling 依赖顺序
            # 假设输入数据已经是单只股票的时间序列，或者需要 groupby
            # 如果是多只股票混合，需要先 group_by("stock_code")
            
            if "stock_code" in df.columns:
                # 多标的模式：按股票代码分组计算
                # 注意：rolling 操作在 group_by 上下文中有效
                result = df.with_columns([
                    expr.over("stock_code").name.keep() for expr in target_factors
                ])
                # 注意：上面的 .over("stock_code") 适用于窗口函数，但 shift 等可能需要更仔细的处理
                # 更稳妥的方式是对 rolling/shift 显式指定 over，或者假定 factors 定义里已经处理了
                # 简单起见，这里假设 FactorEngine 的表达式是针对单序列的，
                # 所以我们使用 map_groups 或者 over
                
                # 修正：polars 的 shift/rolling 在 over 中表现良好
                # 我们重新构造表达式加上 over
                
                # 实际上 register_factor 接收的是 pl.col("close")... 
                # 当我们应用 .over("stock_code") 时，它会按组执行
                
                # 正确的做法：
                # result = df.with_columns([
                #     f.over("stock_code") for f in target_factors
                # ])
                # 但是 factors 已经是 Alias 了，所以可以直接用
                
                pass 
                
            else:
                # 单标的模式
                result = df.with_columns(target_factors)
                
            logger.success("因子计算完成")
            return result
            
        except Exception as e:
            logger.error(f"因子计算失败: {e}")
            raise

    def calculate_group_by(self, df: pl.DataFrame, group_col: str = "stock_code") -> pl.DataFrame:
        """
        针对多标的数据集的分组计算
        """
        if df.is_empty(): return df
        
        target_factors = list(self.factors.values())
        if not target_factors: return df
        
        logger.info(f"执行分组计算 (Group: {group_col})...")
        
        # 使用 over() 进行窗口计算，保持 DataFrame 形状
        # 注意：需要确保数据按时间排序
        df_sorted = df.sort(["date"]) # 假设有 date 列
        
        try:
            # 将所有注册的因子表达式应用 .over(group_col)
            # 这一步需要小心，因为 register 的表达式已经是 complete expr
            # 我们可以直接在 list comprehension 里加 over
            
            # 但是 expr.alias("name").over("code") 是合法的
            
            expressions = [f.over(group_col) for f in target_factors]
            
            result = df_sorted.with_columns(expressions)
            return result
        except Exception as e:
            logger.error(f"分组计算失败: {e}")
            raise e
