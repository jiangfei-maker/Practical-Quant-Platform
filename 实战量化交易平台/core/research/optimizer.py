import optuna
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from loguru import logger
from core.research.factor_lab import FactorLab

class StrategyOptimizer:
    """
    策略/因子参数优化器
    基于 Optuna 实现贝叶斯超参数寻优
    """
    
    def __init__(self):
        self.factor_lab = FactorLab()

    def optimize_single_factor(self, 
                             df_daily: pd.DataFrame, 
                             factor_name: str, 
                             search_space: Dict[str, Dict[str, Any]], 
                             target_metric: str = 'rank_ic', 
                             forward_period: int = 5,
                             n_trials: int = 20) -> Dict:
        """
        对单因子的计算参数进行优化
        
        :param df_daily: 日线数据
        :param factor_name: 因子名称 (e.g. 'Momentum')
        :param search_space: 搜索空间配置 
               Example: {'mom_window': {'type': 'int', 'min': 3, 'max': 60}}
        :param target_metric: 优化目标 ('ic', 'rank_ic')
        :param forward_period: 未来收益计算周期
        :param n_trials: 试验次数
        :return: 最佳参数组合
        """
        
        # 预先计算未来收益率 (避免在每次 trial 中重复计算)
        df = df_daily.copy()
        df['next_ret'] = df['close'].shift(-forward_period) / df['close'] - 1
        # 清除最后几行无收益率的数据
        df = df.dropna(subset=['next_ret'])
        
        def objective(trial):
            # 1. 解析参数
            params = {}
            for param_key, config in search_space.items():
                p_type = config.get('type', 'int')
                if p_type == 'int':
                    params[param_key] = trial.suggest_int(param_key, config['min'], config['max'], step=config.get('step', 1))
                elif p_type == 'float':
                    params[param_key] = trial.suggest_float(param_key, config['min'], config['max'], step=config.get('step', None), log=config.get('log', False))
                elif p_type == 'categorical':
                    params[param_key] = trial.suggest_categorical(param_key, config['choices'])

            # 2. 计算因子
            # 注意: calculate_technical_factors 会返回包含因子的完整 DF
            # 为了性能，我们可能希望 FactorLab 只计算那一列
            try:
                # 传入 copy 避免修改原始 df
                df_calc = self.factor_lab.calculate_technical_factors(df.copy(), [factor_name], **params)
                
                # 3. 识别因子列名 (假设以 factor_ 开头)
                factor_cols = [c for c in df_calc.columns if c.startswith('factor_')]
                if not factor_cols:
                    return -999.0
                
                # 取最后一个生成的因子列 (假设本次只生成了一个)
                target_col = factor_cols[-1]
                
                # 4. 计算 IC
                ic_res = self.factor_lab.evaluate_factor_ic(df_calc, target_col, 'next_ret')
                
                score = ic_res.get(target_metric, -999.0)
                if np.isnan(score):
                    return -999.0
                    
                return score
                
            except Exception as e:
                # logger.warning(f"Trial failed: {e}")
                return -999.0

        # 创建 Study
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)
        
        return {
            "best_params": study.best_params,
            "best_value": study.best_value,
            "trials": len(study.trials)
        }
