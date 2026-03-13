
import sys
import os
import pandas as pd
import numpy as np

# Add project root to path
# Assuming structure:
# root/
#   实战量化交易平台/
#     core/
#   tests/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../实战量化交易平台")))

from core.research.factor_lab import FactorLab

def test_factor_lab_upgrade():
    print("Testing FactorLab Upgrade...")
    
    # 1. Create Mock Data (Panel Data: 2 Stocks, 100 Days)
    dates = pd.date_range(start='2023-01-01', periods=100)
    data = []
    for code in ['000001', '000002']:
        price = 100
        for date in dates:
            price *= (1 + np.random.normal(0, 0.02)) # Random walk
            data.append({
                'trade_date': date,
                'stock_code': code,
                'open': price * (1 + np.random.normal(0, 0.01)),
                'high': price * (1 + abs(np.random.normal(0, 0.01))),
                'low': price * (1 - abs(np.random.normal(0, 0.01))),
                'close': price,
                'volume': np.random.randint(1000, 10000)
            })
    
    df = pd.DataFrame(data)
    print(f"Mock Data Created: {df.shape}")
    
    # 2. Initialize FactorLab
    lab = FactorLab()
    
    # 3. Test Factor Calculation
    factors = [
        "Momentum", "Volatility", "RSI", "MACD", 
        "SMA", "EMA", "Bollinger", "CCI", 
        "ROC", "KDJ", "ATR", "OBV", "VWAP"
    ]
    
    print(f"Calculating factors: {factors}")
    df_factors = lab.calculate_technical_factors(df, factors)
    
    # Check if columns exist
    expected_cols = [
        'factor_mom_5d', 'factor_vol_20d', 'factor_rsi_14', 
        'factor_macd_line', 'factor_sma_20', 'factor_ema_20',
        'factor_bb_upper', 'factor_cci_14', 'factor_roc_12',
        'factor_kdj_k', 'factor_atr_14', 'factor_obv', 'factor_vwap'
    ]
    
    missing = [col for col in expected_cols if col not in df_factors.columns]
    if missing:
        print(f"❌ Missing columns: {missing}")
    else:
        print("✅ All factor columns created successfully.")
        
    # 4. Prepare Target (Next Return) for IC Analysis
    df_factors['next_ret'] = df_factors.groupby('stock_code')['close'].transform(
        lambda x: x.shift(-5) / x - 1
    )
    
    # 5. Test Batch Analysis
    print("Testing Batch Analysis...")
    factor_cols = [c for c in df_factors.columns if c.startswith('factor_')]
    df_res = lab.evaluate_batch_factors(df_factors, factor_cols, 'next_ret')
    
    if not df_res.empty:
        print("✅ Batch analysis result:")
        print(df_res[['factor', 'ic_mean', 'icir']].head())
    else:
        print("❌ Batch analysis returned empty DataFrame")

if __name__ == "__main__":
    test_factor_lab_upgrade()
