
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
from core.utils.network_patch import apply_browser_headers_patch

# 启用浏览器模拟 (规避反爬)
apply_browser_headers_patch()

import time
import random

def retry_api(max_retries=3, delay=1):
    """简单重试装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            last_err = None
            for i in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_err = e
                    wait = delay * (2 ** i) + random.random()
                    logger.warning(f"API调用失败 {func.__name__}, 第 {i+1} 次重试, 等待 {wait:.2f}s: {e}")
                    time.sleep(wait)
            logger.error(f"API调用最终失败 {func.__name__}: {last_err}")
            raise last_err
        return wrapper
    return decorator

class MarketMonitor:
    """
    大盘监控核心类
    负责获取指数行情、板块热点、市场情绪等实时数据
    """
    
    def __init__(self):
        pass
        
    def get_main_indices(self):
        """
        获取三大指数实时行情 (上证、深证、创业板)
        优先获取历史K线数据用于画图，如果失败则尝试获取实时点位
        """
        logger.info("开始获取三大指数行情...")
        indices = {
            "上证指数": "sh000001",
            "深证成指": "sz399001",
            "创业板指": "sz399006"
        }
        
        results = {}
        
        # 内部函数：获取单个指数
        @retry_api(max_retries=2, delay=1)
        def _get_single_index(name, code):
            try:
                # 优先尝试东方财富接口 (数据更新更及时)
                return ak.stock_zh_index_daily_em(symbol=code)
            except Exception as e:
                logger.warning(f"东方财富指数接口失败 {name}, 尝试腾讯接口: {e}")
                # 回退到腾讯接口
                return ak.stock_zh_index_daily_tx(symbol=code)

        for name, code in indices.items():
            try:
                logger.info(f"正在请求指数数据: {name} ({code})...")
                df = _get_single_index(name, code)
                if not df.empty:
                    last_date = df.iloc[-1]['date'] if 'date' in df.columns else 'Unknown'
                    logger.info(f"✅ {name} 获取成功: {len(df)} 条记录, 最新日期: {last_date}")
                    results[name] = df.tail(100).copy()
                else:
                    logger.warning(f"⚠️ {name} 返回数据为空")
            except Exception as e:
                logger.warning(f"❌ 无法获取指数 {name} 的历史数据: {e}")
                # 这里可以考虑再尝试新浪接口 ak.stock_zh_index_daily(symbol=code)
        
        return results

    def get_sector_data(self):
        """
        获取行业板块数据 (用于热力图)
        """
        try:
            df = self._get_sector_data_safe()
            return df
        except Exception as e:
            logger.error(f"获取板块数据失败: {e}")
            return pd.DataFrame()

    @retry_api(max_retries=2)
    def _get_sector_data_safe(self):
        try:
            df = ak.stock_board_industry_name_em()
        except Exception as e:
            logger.warning(f"东方财富板块数据接口失败，尝试备用接口: {e}")
            # Fallback: 使用同花顺或资金流接口
            df = ak.stock_fund_flow_industry(symbol="即时")
            # 映射列名
            # 备用接口有: '行业', '行业指数', '行业-涨跌幅', '领涨股'
            column_mapping = {
                '行业': '板块名称',
                '行业指数': '最新价',
                '行业-涨跌幅': '涨跌幅',
                '领涨股': '领涨股票'
            }
            df.rename(columns=column_mapping, inplace=True)
            # 缺失字段补0
            df['总市值'] = 0
            df['换手率'] = 0
            df['上涨家数'] = 0
            df['下跌家数'] = 0
        
        # 统一列名
        if '名称' in df.columns and '板块名称' not in df.columns:
            df.rename(columns={'名称': '板块名称'}, inplace=True)
        if '板块' in df.columns and '板块名称' not in df.columns:
            df.rename(columns={'板块': '板块名称'}, inplace=True)
            
        numeric_cols = ['最新价', '涨跌幅', '总市值', '换手率']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        return df

    def get_sector_stocks(self, sector_name):
        """
        获取特定板块内的个股数据
        """
        try:
            df = ak.stock_board_industry_cons_em(symbol=sector_name)
            return df
        except Exception as e:
            logger.error(f"获取板块 {sector_name} 成分股失败: {e}")
            return pd.DataFrame()

    def get_sector_fund_flow(self):
        """
        获取板块资金流向数据
        """
        try:
            return self._get_sector_fund_flow_safe()
        except Exception as e:
            logger.error(f"获取板块资金流失败: {e}")
            return pd.DataFrame()

    @retry_api(max_retries=2)
    def _get_sector_fund_flow_safe(self):
        # 获取今日行业资金流排名
        is_fallback = False
        try:
            df = ak.stock_sector_fund_flow_rank(indicator="今日")
        except Exception as e:
            logger.warning(f"东方财富资金流接口失败，尝试备用接口: {e}")
            is_fallback = True
            df = ak.stock_fund_flow_industry(symbol="即时")
            # 映射列名
            column_mapping = {
                '行业': '名称',
                '行业-涨跌幅': '今日涨跌幅',
                '净额': '今日主力净流入-净额'
            }
            df.rename(columns=column_mapping, inplace=True)
        
        if not df.empty:
            if '今日主力净流入-净额' in df.columns:
                df['net_inflow'] = pd.to_numeric(df['今日主力净流入-净额'], errors='coerce')
                
                # 智能单位判断与转换
                # 东方财富原接口(Primary)通常返回"万"单位 (例如 342245 = 34.22亿)
                # 但有时也可能返回"元"单位 (例如 3907126016 = 39.07亿)
                # 备用接口(Fallback)也类似
                
                abs_mean = df['net_inflow'].abs().mean()
                
                if abs_mean > 100000000:
                    # 如果均值大于1亿，肯定是"元"
                    df['net_inflow_100m'] = df['net_inflow'] / 100000000
                elif abs_mean > 1000:
                    # 如果均值在1000以上(且小于1亿)，通常是"万"
                    df['net_inflow_100m'] = df['net_inflow'] / 10000
                else:
                    # 如果均值很小(<1000)，可能是已经单位换算过的(亿)
                    df['net_inflow_100m'] = df['net_inflow']
            
            if '今日涨跌幅' in df.columns:
                df['change_pct'] = pd.to_numeric(df['今日涨跌幅'], errors='coerce')
                
        return df

    def get_market_breadth(self):
        """
        获取市场广度数据 (涨跌分布、涨跌停统计)
        """
        try:
            return self._get_market_breadth_safe()
        except Exception as e:
            logger.error(f"获取市场广度失败: {e}")
            return None

    @retry_api(max_retries=2)
    def _get_market_breadth_safe(self):
        try:
            # 优先尝试东方财富接口 (数据更全)
            df_spot = ak.stock_zh_a_spot_em()
        except:
            # Fallback: 新浪接口
            logger.warning("东方财富全市场行情获取失败，切换至新浪接口")
            df_spot = ak.stock_zh_a_spot()
        
        stats = {
            'up': len(df_spot[df_spot['涨跌幅'] > 0]),
            'down': len(df_spot[df_spot['涨跌幅'] < 0]),
            'flat': len(df_spot[df_spot['涨跌幅'] == 0]),
            'limit_up': len(df_spot[df_spot['涨跌幅'] >= 9.8]), # 修正为 9.8 以包含 ST
            'limit_down': len(df_spot[df_spot['涨跌幅'] <= -9.8])
        }
        
        bins = [-100, -7, -5, -3, 0, 3, 5, 7, 100]
        labels = ['<-7%', '-7%~-5%', '-5%~-3%', '-3%~0%', '0%~3%', '3%~5%', '5%~7%', '>7%']
        df_spot['range'] = pd.cut(df_spot['涨跌幅'], bins=bins, labels=labels)
        distribution = df_spot['range'].value_counts().sort_index()
        
        return {
            'stats': stats,
            'distribution': distribution,
            'spot_data': df_spot[['代码', '名称', '最新价', '涨跌幅', '成交量', '成交额']]
        }

    def get_limit_pool(self):
        """
        获取涨停池数据
        """
        try:
            # 尝试获取今天的数据
            date_str = datetime.now().strftime("%Y%m%d")
            return self._get_limit_pool_safe(date_str)
        except Exception:
            try:
                # 如果失败，尝试获取最近一个交易日（简单回推）
                # 注意：这只是一个简单的 fallback，不保证一定是交易日
                # 更好的做法是维护一个交易日历，但这里保持简单
                prev_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
                if datetime.now().weekday() == 0: # 如果是周一，回推到周五
                     prev_date = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")
                return self._get_limit_pool_safe(prev_date)
            except Exception as e:
                logger.error(f"获取涨停池失败: {e}")
                return pd.DataFrame()

    @retry_api(max_retries=1)
    def _get_limit_pool_safe(self, date_str):
        return ak.stock_zt_pool_em(date=date_str)

