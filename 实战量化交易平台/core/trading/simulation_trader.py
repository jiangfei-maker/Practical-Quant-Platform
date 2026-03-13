import pandas as pd
import uuid
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
from core.data.db_manager import db_manager

class SimulationTrader:
    """
    模拟交易执行引擎
    负责管理模拟账户、订单执行和持仓更新
    """
    
    def __init__(self, user_id: str = "admin"):
        self.user_id = user_id
        self.db = db_manager
        self._ensure_account()

    def _ensure_account(self):
        """确保账户存在，如果不存在则初始化"""
        conn = self.db.get_connection()
        res = conn.execute(f"SELECT * FROM sim_account WHERE user_id = '{self.user_id}'").fetchall()
        
        if not res:
            logger.info(f"初始化模拟账户: {self.user_id}")
            conn.execute(f"""
                INSERT INTO sim_account (user_id, cash_balance, total_assets, updated_at)
                VALUES ('{self.user_id}', 1000000.0, 1000000.0, now())
            """)

    def get_account_summary(self) -> Dict:
        """获取账户摘要"""
        conn = self.db.get_connection()
        # 更新持仓市值需要实时价格，这里先返回记录的值，UI层负责刷新
        res = conn.execute(f"SELECT cash_balance, total_assets FROM sim_account WHERE user_id = '{self.user_id}'").fetchone()
        
        if res:
            return {
                "cash": res[0],
                "total_assets": res[1]
            }
        return {"cash": 0.0, "total_assets": 0.0}

    def get_positions(self) -> pd.DataFrame:
        """获取当前持仓"""
        conn = self.db.get_connection()
        df = conn.execute(f"SELECT * FROM sim_positions WHERE user_id = '{self.user_id}'").fetchdf()
        return df

    def get_orders(self) -> pd.DataFrame:
        """获取订单历史"""
        conn = self.db.get_connection()
        df = conn.execute(f"SELECT * FROM sim_orders WHERE user_id = '{self.user_id}' ORDER BY created_at DESC").fetchdf()
        return df

    def place_order(self, stock_code: str, action: str, price: float, quantity: int, stock_name: str = "") -> Dict:
        """
        下达模拟订单
        :param action: 'BUY' or 'SELL'
        """
        if quantity <= 0 or price <= 0:
            return {"status": "error", "message": "价格和数量必须大于0"}
            
        amount = price * quantity
        conn = self.db.get_connection()
        
        try:
            # 1. 检查资金或持仓
            account = self.get_account_summary()
            
            if action == 'BUY':
                if account['cash'] < amount:
                    return {"status": "error", "message": "资金不足"}
                
                # 扣除资金
                new_cash = account['cash'] - amount
                conn.execute(f"UPDATE sim_account SET cash_balance = {new_cash} WHERE user_id = '{self.user_id}'")
                
                # 增加持仓
                # 检查是否存在持仓
                pos = conn.execute(f"SELECT quantity, avg_cost FROM sim_positions WHERE user_id = '{self.user_id}' AND stock_code = '{stock_code}'").fetchone()
                
                if pos:
                    old_qty = pos[0]
                    old_cost = pos[1]
                    new_qty = old_qty + quantity
                    new_cost = (old_qty * old_cost + amount) / new_qty
                    
                    conn.execute(f"""
                        UPDATE sim_positions 
                        SET quantity = {new_qty}, avg_cost = {new_cost}, updated_at = now()
                        WHERE user_id = '{self.user_id}' AND stock_code = '{stock_code}'
                    """)
                else:
                    conn.execute(f"""
                        INSERT INTO sim_positions (user_id, stock_code, stock_name, quantity, avg_cost, updated_at)
                        VALUES ('{self.user_id}', '{stock_code}', '{stock_name}', {quantity}, {price}, now())
                    """)
                    
            elif action == 'SELL':
                pos = conn.execute(f"SELECT quantity FROM sim_positions WHERE user_id = '{self.user_id}' AND stock_code = '{stock_code}'").fetchone()
                
                if not pos or pos[0] < quantity:
                    return {"status": "error", "message": "持仓不足"}
                
                # 增加资金
                new_cash = account['cash'] + amount
                conn.execute(f"UPDATE sim_account SET cash_balance = {new_cash} WHERE user_id = '{self.user_id}'")
                
                # 减少持仓
                new_qty = pos[0] - quantity
                if new_qty == 0:
                    conn.execute(f"DELETE FROM sim_positions WHERE user_id = '{self.user_id}' AND stock_code = '{stock_code}'")
                else:
                    conn.execute(f"""
                        UPDATE sim_positions 
                        SET quantity = {new_qty}, updated_at = now()
                        WHERE user_id = '{self.user_id}' AND stock_code = '{stock_code}'
                    """)
            
            # 2. 记录订单
            order_id = str(uuid.uuid4())
            conn.execute(f"""
                INSERT INTO sim_orders (order_id, user_id, stock_code, action, price, quantity, amount, status, created_at)
                VALUES ('{order_id}', '{self.user_id}', '{stock_code}', '{action}', {price}, {quantity}, {amount}, 'FILLED', now())
            """)
            
            return {"status": "success", "order_id": order_id}
            
        except Exception as e:
            logger.error(f"下单失败: {e}")
            return {"status": "error", "message": str(e)}

    def reset_account(self):
        """重置账户"""
        conn = self.db.get_connection()
        conn.execute(f"DELETE FROM sim_positions WHERE user_id = '{self.user_id}'")
        conn.execute(f"DELETE FROM sim_orders WHERE user_id = '{self.user_id}'")
        conn.execute(f"UPDATE sim_account SET cash_balance = 1000000.0, total_assets = 1000000.0 WHERE user_id = '{self.user_id}'")
