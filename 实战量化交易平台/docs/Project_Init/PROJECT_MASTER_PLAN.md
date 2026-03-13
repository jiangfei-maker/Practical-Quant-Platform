# 实战量化交易平台 (Real-world Quant Platform) - Project Master Plan

## 1. 项目愿景 (Vision)
打造一个**高性能、AI驱动、全栈式**的个人量化交易平台。
专为**一人公司 (OPC)** 模式设计，强调**开发效率、运行稳定性与模型可解释性**。
整合过往项目（量子算法架构、AI风控、高性能因子研究、**同花顺数据爬虫**、**LLM投研系统**）的核心优势，构建闭环的量化投研与交易系统。

## 2. 核心设计原则 (Core Principles)
1.  **极简运维 (LowOps)**: 采用无服务器化或轻量级部署架构，减少基础设施维护成本。
2.  **极致性能 (High Performance)**: 全链路采用 **Polars** + **DuckDB** 替代传统的 Pandas 处理模式，实现 10-50倍 性能提升。
3.  **双轮驱动 (Fundamental + Technical)**: 坚持**基本面选股 + 技术面择时**的策略体系，数据源涵盖财务报表、研报舆情与高频行情。
4.  **AI 原生 (AI-Native)**: 内置机器学习/深度学习支持，从因子挖掘、研报生成到风控全流程集成 AI 能力。

## 3. 核心业务功能 (Core Business Features)

### 3.1 智能投研体系 (Smart Research)
*   **基本面数据中心 (Fundamental Data Hub)** (源自《同花顺爬虫》&《测试版本1.0.0》):
    *   **多源财务数据**: 集成 AkShare/同花顺接口，自动抓取资产负债表、利润表、现金流量表。
    *   **非结构化数据**: 抓取公司公告、研报、新闻舆情。
*   **AI 投研助理 (AI Research Assistant)** (源自《测试版本1.0.0》):
    *   **自动化研报生成**: 基于 LLM (Large Language Model) 自动生成个股深度研报、行业分析报告。
    *   **财务造假识别**: 基于 `EnhancedFinancialAnalyzer` 进行深度财务健康打分 (Z-Score, M-Score)。
*   **高性能因子实验室**:
    *   集成 **Polars** 表达式引擎，支持亿级数据秒级计算。
    *   **参数化因子系统**: 支持通过 UI 动态调整因子参数（窗口、权重等），实时预览结果。

### 3.2 市场热点与政策追踪 (Market Trends & Policy Tracking)
*   **政策风向标 (Policy Radar)**:
    *   **宏观政策监控**: 自动抓取政府官网（发改委、工信部、央行等）及核心官媒新闻。
    *   **智能解读**: 利用 NLP/LLM 提取政策关键词（如“新质生产力”、“设备更新”），自动匹配受益产业链与个股。
*   **全市场热力图 (Market Heatmap)**:
    *   **板块轮动监控**: 实时计算申万/中信一级行业涨跌幅，构建动态 Treemap 可视化。
    *   **资金流向追踪**: 监控主力资金（北向、机构）的板块流向，捕捉热点切换路径。
*   **题材挖掘机 (Concept Mining)**:
    *   **舆情共振**: 结合新闻、研报与社交媒体高频词，自动发现新兴概念（如“低空经济”、“合成生物”）。

### 3.3 策略与回测 (Strategy & Backtest)
*   **双模式回测引擎**:
    *   **向量化回测**: 基于 Polars 的超高速初筛，用于因子有效性验证。
    *   **高保真事件驱动回测**: 
        *   利用《同花顺爬虫》获取的 **Order Book (盘口)** 和 **Transactions (逐笔)** 数据。
        *   模拟真实市场微结构（滑点、冲击成本、挂单排队），确保回测结果可信度。
*   **量子/AI 策略集成**:
    *   支持 Pytorch/Tensorflow 模型热加载。
    *   强化学习 (RL) 资产组合优化接口（源自《风险管理》Phase 2）。

### 3.4 全局风控中心 (Global Risk Control)
*   **AI 风控引擎** (源自《风险管理》):
    *   **实时 VaR 计算**: 基于 GARCH/LSTM 的动态风险价值评估。
    *   **波动率预测**: 提前识别市场极端行情。
    *   **舆情崩盘预警**: 结合新闻情感分析与宏观数据，识别系统性风险。

### 3.5 交互式控制台 (Interactive Console)
*   **Streamlit 全栈管理**:
    *   **投研工作台**: 因子可视化、自动化研报展示、财务报表透视。
    *   **热点雷达**: 政策解读看板、板块热力图、题材挖掘报告。
    *   **交易驾驶舱**: 实时账户监控、手动干预接口。
    *   **系统监控**: 数据质量看板 (DataQualityGuard)、爬虫运行状态。

## 4. 系统架构 (System Architecture)

```mermaid
graph TD
    subgraph "前端表现层 (Presentation Layer)"
        StreamlitApp[Streamlit 交互式控制台]
        TrendDashboard[热点雷达看板]
        ReportUI[研报生成与展示界面]
        ConfigUI[动态参数配置器]
    end

    subgraph "应用服务层 (Application Layer)"
        TrendService[热点追踪服务]
        ResearchService[投研服务 (因子/模型/LLM)]
        BacktestService[回测服务]
        RiskService[风控服务 (AI-Guard)]
        TradeService[交易执行服务]
    end

    subgraph "核心领域层 (Domain Layer)"
        TrendAnalyzer[热点/政策分析器]
        FactorEngine[高性能因子引擎 (Polars)]
        LLMAgent[LLM 投研助理 (LangChain)]
        MatchingEngine[高保真撮合引擎 (Tick级)]
        FinancialCore[财务分析核心 (EnhancedAnalyzer)]
    end

    subgraph "数据获取与存储层 (Data Layer)"
        DuckDB[(DuckDB - 财务/因子/日线)]
        TickStore[(Parquet - 盘口/逐笔数据)]
        NewsStore[(NoSQL/JSON - 新闻/政策)]
        Crawler[多源爬虫 (同花顺/东方财富/政府官网)]
        DataGuard[数据清洗 (DataQualityGuard)]
    end

    StreamlitApp --> TrendService & ResearchService & BacktestService & RiskService & TradeService
    TrendService --> TrendAnalyzer & LLMAgent
    ResearchService --> FactorEngine & FinancialCore & LLMAgent
    BacktestService --> MatchingEngine
    
    Crawler --> DataGuard --> DuckDB & TickStore & NewsStore
    TrendAnalyzer -.-> NewsStore
    FactorEngine -.-> DuckDB
    MatchingEngine -.-> TickStore
    FinancialCore -.-> DuckDB
```

## 5. 技术栈选型 (Technology Stack)

*   **编程语言**: Python 3.9+
*   **数据分析**: **Polars** (核心), NumPy, Pandas (兼容)
*   **数据采集**: **AkShare** (核心), Requests, BeautifulSoup, Selenium (辅助)
*   **存储引擎**: **DuckDB** (OLAP), Parquet (高频数据), Redis (缓存), JSON/NoSQL (非结构化数据)
*   **AI/LLM**: **LangChain** (流程编排), OpenAI/DeepSeek API (文本生成), PyTorch (量化模型)
*   **Web 框架**: **Streamlit** (全栈 UI)
*   **开发工具**: Trae (IDE), Poetry (依赖管理), Pytest (测试)

## 6. 执行计划 (Execution Plan)

### Phase 1: 基础设施与数据底座 (Infrastructure & Data)
*   **目标**: 构建基于 Polars + DuckDB 的高性能数据管道，打通基本面与高频数据获取链路。
*   **任务**:
    *   [ ] 初始化项目结构与 Poetry 依赖。
    *   [ ] 移植 `FinancialDataFetcher`，实现多源财务数据（资产负债/利润/现金流）的自动抓取与入库。
    *   [ ] 移植 `同花顺爬虫` 逻辑，实现 Order Book 和 逐笔成交数据的定时抓取与存储 (Parquet)。
    *   [ ] 实现 `DataQualityGuard` 数据清洗与验证模块。

### Phase 2: 核心引擎与投研系统 (Core Engine & Research)
*   **目标**: 移植并优化《因子研究》、《测试版本1.0.0》与《量子算法》核心逻辑。
*   **任务**:
    *   [ ] 开发 `FactorEngine`，支持动态表达式与参数化配置。
    *   [ ] 移植 `CompanyResearch` 与 `LLMQueryProcessor`，实现 AI 自动化研报生成。
    *   [ ] 集成 `EnhancedFinancialAnalyzer`，实现财务健康度自动打分。
    *   [ ] 实现基础事件驱动回测框架，接入高频数据接口。

### Phase 3: 市场热点与风控集成 (Trends & Risk)
*   **目标**: 引入政策追踪与高级风控模型。
*   **任务**:
    *   [ ] 开发 `TrendService`，集成政府官网爬虫与 LLM 政策解读。
    *   [ ] 实现板块热力图与资金流向监控功能。
    *   [ ] 实现 `VolatilityPredictor` (波动率预测模型) 与实时 VaR 计算。
    *   [ ] 完善事件驱动回测，实现基于 Order Book 的高保真撮合模拟。

### Phase 4: 全栈可视化与交付 (Visualization & Delivery)
*   **目标**: 构建 Streamlit 交互式控制台，实现 OPC 闭环。
*   **任务**:
    *   [ ] 开发 Streamlit 主界面框架（Sidebar, Navigation）。
    *   [ ] 实现投研工作台与热点雷达看板。
    *   [ ] 实现回测报告页面与交易驾驶舱。
    *   [ ] 编写部署脚本与用户手册。

## 7. 风险管理 (Risk Management)
*   **数据源风险**: 依赖第三方接口（如同花顺、东财），需建立多源互备与反爬策略。
*   **模型风险**: 避免过度拟合，强制样本外测试 (Out-of-Sample Testing)。
*   **合规风险**: 严格遵守相关法律法规，爬虫策略需符合 `robots.txt` 规范，避免高频请求。

## 8. 详细技术规格 (Detailed Specifications)

为了确保开发过程中的技术一致性，具体的数据库 Schema 设计、核心算法实现逻辑（因子计算、回测引擎）、AI 系统 Prompt 模板及 Streamlit 应用架构细节，请详细参考配套的技术文档：

👉 **[技术规格说明书 (Technical Specifications)](TECHNICAL_SPECIFICATIONS.md)**

该文档涵盖了：
*   **DuckDB + Parquet** 混合存储的具体表结构设计。
*   **Polars** 因子计算引擎的代码实现范式。
*   **LangChain** 投研助理的 Prompt 模板。
*   **Streamlit** 多页面架构与状态管理方案。

---
*Created by Trae AI Assistant based on user's portfolio integration strategy.*
