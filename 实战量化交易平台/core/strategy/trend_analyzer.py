import pandas as pd
from loguru import logger
from typing import List, Dict, Tuple
from collections import Counter
import re
import jieba

# 确保 jieba 不打印太多日志
import logging
jieba.setLogLevel(logging.INFO)

class TrendAnalyzer:
    """
    市场热点分析器
    负责:
    1. 统计板块涨跌幅排行
    2. 从新闻中提取热点关键词
    """
    
    def analyze_sector_rotation(self, df_sectors: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
        """
        分析板块轮动情况
        :param df_sectors: 板块行情数据 (columns: 板块名称, 涨跌幅, ...)
        :return: 涨幅前N和跌幅前N的板块
        """
        if df_sectors is None or df_sectors.empty:
            return pd.DataFrame()
            
        try:
            # 确保涨跌幅是数值类型
            if df_sectors['涨跌幅'].dtype == 'object':
                 df_sectors['涨跌幅'] = pd.to_numeric(df_sectors['涨跌幅'], errors='coerce')
            
            # Top Gainers
            gainers = df_sectors.nlargest(top_n, "涨跌幅")
            return gainers
        except Exception as e:
            logger.error(f"板块分析失败: {e}")
            return pd.DataFrame()

    def extract_keywords_from_list(self, text_list: List[str], top_k: int = 20) -> List[Tuple[str, int]]:
        """
        从文本列表中提取热点关键词
        """
        if not text_list:
            return []
            
        try:
            text = " ".join([str(t) for t in text_list if t])
            
            # 清洗
            text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', ' ', text)
            
            # 分词
            words = jieba.lcut(text)
            
            # 停用词 (扩展)
            stop_words = {
                "的", "了", "在", "是", "我", "有", "和", "就", "不", "人", "都", "一", "一个", "上", "也", "很", "到", "说", "要", "去", "你", "会", "着", "没有", "看", "好", "自己", "这", "那", 
                "今日", "公布", "显示", "市场", "公司", "进行", "相关", "工作", "表示", "目前", "亿元", "同比", "增长", "下降", "指数", "收盘", "上涨", "下跌",
                "新闻", "中国", "关于", "对于", "以及", "除了", "虽然", "但是", "因为", "所以", "如果", "那么", "根据", "为了", "记者", "报道", "日", "月", "年", "我们", "你们", "他们"
            }
            
            filtered_words = [w for w in words if len(w) > 1 and w not in stop_words]
            
            # 统计词频
            counter = Counter(filtered_words)
            return counter.most_common(top_k)
            
        except Exception as e:
            logger.error(f"关键词提取失败: {e}")
            return []

    def extract_keywords_from_news(self, df_news: pd.DataFrame, top_k: int = 20) -> List[Tuple[str, int]]:
        """
        从新闻标题中提取热点关键词 (TF-IDF or Simple Frequency)
        :param df_news: 新闻数据 (columns: title, content, ...)
        """
        if df_news is None or df_news.empty:
            return []
            
        text_list = []
        if "title" in df_news.columns:
            text_list.extend(df_news["title"].astype(str).tolist())
        if "content" in df_news.columns:
            text_list.extend(df_news["content"].astype(str).tolist())
        if "标题" in df_news.columns:
            text_list.extend(df_news["标题"].astype(str).tolist())
        if "内容" in df_news.columns:
            text_list.extend(df_news["内容"].astype(str).tolist())
            
        return self.extract_keywords_from_list(text_list, top_k)

    def calculate_sentiment_score(self, text_list: List[str]) -> float:
        """
        计算文本列表的情绪得分 (-1.0 到 1.0)
        简单词典匹配法
        """
        if not text_list:
            return 0.0
            
        # 简单情感词典 (实际应用中应加载更完整的词典)
        pos_words = {
            "上涨", "大涨", "暴涨", "新高", "突破", "利好", "增长", "复苏", "盈利", "超预期", 
            "买入", "增持", "乐观", "积极", "支持", "落地", "成功", "领先", "优质", "回暖"
        }
        neg_words = {
            "下跌", "大跌", "暴跌", "新低", "破位", "利空", "下降", "衰退", "亏损", "不及预期",
            "卖出", "减持", "悲观", "消极", "打压", "失败", "风险", "警告", "违约", "调查"
        }
        
        pos_count = 0
        neg_count = 0
        total_words = 0
        
        text = " ".join([str(t) for t in text_list if t])
        words = jieba.lcut(text)
        
        for w in words:
            if w in pos_words:
                pos_count += 1
            elif w in neg_words:
                neg_count += 1
        
        total_sent_words = pos_count + neg_count
        if total_sent_words == 0:
            return 0.0
            
        # Score = (Pos - Neg) / (Pos + Neg)
        score = (pos_count - neg_count) / total_sent_words
        return score

if __name__ == "__main__":
    # Test
    analyzer = TrendAnalyzer()
    
    # Mock Data
    df_sec = pd.DataFrame({
        "板块名称": ["半导体", "白酒", "银行", "房地产", "光伏"],
        "涨跌幅": [2.5, -1.2, 0.5, -3.0, 1.8]
    })
    print("Top Sectors:")
    print(analyzer.analyze_sector_rotation(df_sec))
    
    df_news = pd.DataFrame({
        "title": ["人工智能发展迅速，AI算力需求大增", "新能源汽车销量创新高", "美联储加息预期降温"]
    })
    print("\nKeywords:")
    print(analyzer.extract_keywords_from_news(df_news))
