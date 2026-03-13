
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

class ValuationModel:
    """
    财务估值建模工具箱
    包含 DCF, 相对估值(PE/PB), PEG, 格雷厄姆公式等模型
    """
    
    @staticmethod
    def calculate_dcf(
        fcf_list: list, 
        terminal_growth_rate: float = 0.02, 
        wacc: float = 0.08, 
        net_debt: float = 0, 
        shares_outstanding: float = 1
    ) -> Dict[str, Any]:
        """
        现金流折现模型 (DCF)
        :param fcf_list: 未来几年的预测自由现金流列表 [Year1, Year2, ..., YearN]
        :param terminal_growth_rate: 永续增长率 (默认 2%)
        :param wacc: 加权平均资本成本 (默认 8%)
        :param net_debt: 净债务 (总债务 - 现金及等价物)
        :param shares_outstanding: 总股本
        :return: 合理股价及中间结果
        """
        if not fcf_list or wacc <= terminal_growth_rate:
            return {"error": "参数无效: 现金流为空或 WACC <= 永续增长率"}
            
        discounted_fcfs = []
        for i, fcf in enumerate(fcf_list):
            df = 1 / ((1 + wacc) ** (i + 1))
            discounted_fcfs.append(fcf * df)
            
        # 终值 (Terminal Value)
        last_fcf = fcf_list[-1]
        terminal_value = last_fcf * (1 + terminal_growth_rate) / (wacc - terminal_growth_rate)
        discounted_tv = terminal_value / ((1 + wacc) ** len(fcf_list))
        
        enterprise_value = sum(discounted_fcfs) + discounted_tv
        equity_value = enterprise_value - net_debt
        fair_price = equity_value / shares_outstanding
        
        return {
            "model": "DCF",
            "fair_price": round(fair_price, 2),
            "enterprise_value": round(enterprise_value, 2),
            "equity_value": round(equity_value, 2),
            "discounted_fcfs": [round(x, 2) for x in discounted_fcfs],
            "discounted_terminal_value": round(discounted_tv, 2)
        }

    @staticmethod
    def calculate_pe_valuation(eps: float, target_pe: float) -> float:
        """相对估值法 (PE)"""
        return round(eps * target_pe, 2)
        
    @staticmethod
    def calculate_peg_valuation(eps: float, growth_rate: float, peg_ratio: float = 1.0) -> float:
        """PEG 估值法: 合理PE = 增长率 * PEG"""
        # growth_rate is percent, e.g., 15 for 15%
        target_pe = growth_rate * peg_ratio
        return round(eps * target_pe, 2)

    @staticmethod
    def calculate_graham_number(eps: float, bps: float) -> float:
        """格雷厄姆数字 = Sqrt(22.5 * EPS * BVPS)"""
        if eps < 0 or bps < 0:
            return 0.0
        return round(np.sqrt(22.5 * eps * bps), 2)
        
    @staticmethod
    def get_growth_rate(historical_data: pd.Series, periods: int = 3) -> float:
        """计算复合增长率 (CAGR)"""
        if len(historical_data) < periods + 1:
            return 0.0
        
        try:
            end_val = historical_data.iloc[0] # Latest
            start_val = historical_data.iloc[periods] # Previous
            
            if start_val <= 0 or end_val <= 0:
                return 0.0
                
            cagr = (end_val / start_val) ** (1/periods) - 1
            return round(cagr * 100, 2)
        except:
            return 0.0

