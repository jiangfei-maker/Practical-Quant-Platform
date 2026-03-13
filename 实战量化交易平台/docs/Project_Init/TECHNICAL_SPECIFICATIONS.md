# 实战量化交易平台 - 技术规格说明书 (Technical Specifications)

本文档旨在为 `PROJECT_MASTER_PLAN.md` 提供具体的技术实现细节，指导开发落地。

## 1. 数据架构详解 (Data Architecture)

### 1.1 混合存储策略 (Hybrid Storage Strategy)
采用 **DuckDB + Parquet** 的分层存储架构，兼顾分析性能与写入吞吐量。

| 数据类型 | 存储引擎 | 文件格式 | 存储路径规则 | 典型查询场景 |
| :--- | :--- | :--- | :--- | :--- |
| **基础数据** (日线/财务/因子) | **DuckDB** | `.db` (本地文件) | `data/db/quant_core.duckdb` | 选股SQL、财务分析、多因子关联 |
| **高频数据** (Tick/OrderBook) | **Parquet** | `.parquet` (Snappy压缩) | `data/market_depth/{YYYY}/{MM}/{code}_{date}.parquet` | 逐笔回测、微结构分析 |
| **非结构化数据** (新闻/研报) | **SQLite** (FTS5) | `.db` | `data/db/news_corpus.db` | 全文检索、LLM 上下文提取 |

### 1.2 DuckDB 核心 Schema 设计

#### (1) 财务报表主表 (`financial_statements`)
用于存储清洗后的三大表核心字段。
```sql
CREATE TABLE financial_statements (
    stock_code VARCHAR,          -- 股票代码
    report_date DATE,            -- 报告期 (2023-12-31)
    publish_date DATE,           -- 发布日 (用于避免未来函数)
    revenue DOUBLE,              -- 营业收入
    net_profit DOUBLE,           -- 净利润
    cash_flow_op DOUBLE,         -- 经营性现金流
    total_assets DOUBLE,         -- 总资产
    total_liabilities DOUBLE,    -- 总负债
    roe DOUBLE,                  -- 净资产收益率
    -- ... 扩展至 50+ 核心字段
    PRIMARY KEY (stock_code, report_date)
);
```

#### (2) 因子库 (`factor_exposure`)
采用长表存储，便于新增因子。
```sql
CREATE TABLE factor_exposure (
    trade_date DATE,
    stock_code VARCHAR,
    factor_name VARCHAR,         -- 因子名称 (如 'pe_ttm', 'macd_cross')
    factor_value DOUBLE,         -- 因子值
    updated_at TIMESTAMP,
    PRIMARY KEY (trade_date, stock_code, factor_name)
);
```

### 1.3 数据管道实现 (ETL Pipeline)
*   **采集层**:
    *   **AkShare**: 用于日线、财务数据。
    *   **Custom Crawler**: 使用 `playwright` 抓取同花顺/东财的高频数据（需处理滑块验证）。
*   **清洗层 (`DataQualityGuard`)**:
    *   **Pydantic 模型**: 定义数据契约，自动校验字段类型和范围。
    *   **异常检测**: Z-Score 过滤偏离度 > 3σ 的异常价格。
*   **入库层**:
    *   使用 `duckdb.appender` 实现批量高速写入。
    *   Parquet 文件写入使用 `polars.write_parquet(use_pyarrow=True)`。

---

## 2. 核心算法实现 (Core Algorithms)

### 2.1 高性能因子引擎 (`FactorEngine`)
基于 **Polars** 表达式实现向量化计算，替代 Pandas 循环。

```python
import polars as pl

def calculate_factors(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns([
        # 动量因子: 20日收益率
        (pl.col("close") / pl.col("close").shift(20) - 1).alias("mom_20d"),
        # 波动率因子: 20日标准差
        pl.col("close").rolling_std(window_size=20).alias("vol_20d"),
        # 均线交叉
        (pl.col("close") > pl.col("close").rolling_mean(60)).alias("above_ma60")
    ])
```

### 2.2 高保真回测引擎 (`MatchingEngine`)
事件驱动架构，模拟真实交易所撮合逻辑。

*   **OrderBook 重建**: 维护 `Dict[Price, Volume]` 结构的买卖盘口。
*   **撮合逻辑**:
    1.  **限价单 (Limit Order)**: 检查当前 Tick 的 `High/Low` 是否穿过委托价。
    2.  **市价单 (Market Order)**: 根据 OrderBook 深度计算加权平均成交价 (VWAP)，模拟冲击成本。
    3.  **成交量限制**: 单笔成交不超过当前 Tick 总量的 10%。

### 2.3 财务健康打分 (Z-Score & M-Score)
移植自《测试版本1.0.0》的 `EnhancedFinancialAnalyzer`。

*   **Altman Z-Score**: 预测破产风险。
    $$Z = 1.2X_1 + 1.4X_2 + 3.3X_3 + 0.6X_4 + 1.0X_5$$
*   **Beneish M-Score**: 识别财务造假。
    *   关注指标：DSRI (应收账款指数), GMI (毛利率指数), AQI (资产质量指数)。

---

## 3. AI 系统落地 (AI System Implementation)

### 3.1 投研助理 (`ResearchAgent`)
基于 **LangChain** 的 ReAct 架构。

*   **Tools**:
    *   `SearchTool`: 搜索 DuckDB 中的财务数据。
    *   `NewsTool`: 查询 SQLite 中的新闻摘要。
    *   `WebSearch`: Google/Bing 搜索实时信息。
*   **Prompt Template**:
    ```text
    你是一位专业的证券分析师。请基于以下提供的财务数据和新闻，生成一份关于 {stock_name} 的简报。
    
    [财务数据]
    {financial_data}
    
    [近期新闻]
    {news_summary}
    
    要求：
    1. 分析营收和利润增长趋势。
    2. 结合新闻判断未来催化剂。
    3. 给出 "买入/持有/卖出" 评级并说明理由。
    ```

### 3.2 政策风向标 (`PolicyRadar`)
*   **数据源**: 发改委、工信部、中国政府网。
*   **NLP 流程**:
    1.  HTML 清洗 -> 提取正文。
    2.  TextRank 提取关键词 (Top 10)。
    3.  使用 LLM (如 DeepSeek/GPT-4) 进行分类：`{"category": "新能源", "sentiment": "positive", "impact_level": "high"}`。

---

## 4. 应用架构 (Application Architecture)

### 4.1 Streamlit 全栈设计
*   **目录结构**:
    ```
    app/
    ├── main.py             # 入口
    ├── pages/              # 多页面路由
    │   ├── 1_📊_Dashboard.py
    │   ├── 2_🧪_Research.py
    │   └── 3_⚙️_Settings.py
    ├── components/         # 可复用组件 (Sidebar, Charts)
    └── session_state.py    # 状态管理封装
    ```
*   **性能优化**:
    *   `@st.cache_data`: 缓存 DuckDB 查询结果。
    *   `@st.cache_resource`: 缓存加载的 AI 模型 (PyTorch/Transformers)。

### 4.2 交互组件
*   **AgGrid**: 用于展示可排序、筛选的股票列表。
*   **Plotly Charts**: 用于绘制交互式 K 线图和热力图。
*   **Chat Interface**: `st.chat_message` 用于与 AI 投研助理对话。

---

## 5. 部署与运维 (Deployment & Ops)

### 5.1 本地化部署 (Local First)
鉴于 OPC 模式，优先支持 Windows 本地一键启动。

*   **启动脚本 (`run_platform.bat`)**:
    ```bat
    @echo off
    call .venv\Scripts\activate
    start "Data Service" python services/scheduler.py
    start "Web UI" streamlit run app/main.py
    ```

### 5.2 依赖管理
使用 **Poetry** 锁定版本，确保环境一致性。
```toml
[tool.poetry.dependencies]
python = ">=3.9,<3.12"
polars = "^0.20.0"
duckdb = "^0.9.2"
streamlit = "^1.30.0"
langchain = "^0.1.0"
akshare = "^1.12.0"
```
