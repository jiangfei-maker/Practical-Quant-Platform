# 实战量化交易平台 - 高级优化与重构计划 (Advanced Optimization & Refactoring Plan)

## 1. 核心痛点与需求分析 (Issues & Requirements)

根据最新的用户反馈，项目当前面临的主要挑战和新增需求如下：

| 维度 | 现状/问题 | 目标/新需求 |
| :--- | :--- | :--- |
| **性能 (Performance)** | 功能加载缓慢，页面响应延迟高。 | **秒级响应**。通过异步并发、多级缓存、懒加载等技术显著提升速度。 |
| **交互 (UI/UX)** | 静态图表，交互性差。 | **TradingView 风格体验 + 科幻风 (Cyberpunk) UI**。深色霓虹主题，引入专业K线库，支持流畅的缩放、平移和指标叠加。 |
| **AI 智能 (AI & RAG)** | 基础问答，缺乏深度上下文。 | **Zhipu AI (智谱) + RAG + Agent**。构建智能体，通过 RAG 检索历史数据和新闻，提供深度投研服务。 |
| **数据深度 (Data Depth)** | 缺少机构和深度资金数据。 | **全维数据聚合**。新增机构持仓、主力资金流向；在行情页聚合个股新闻、资料、资金面。 |

---

## 2. 详细重构方案 (Detailed Solutions)

### 2.1 🚀 性能革命 (Performance Optimization)
**目标**: 消除"卡顿感"，实现流畅交互。

*   **异步并发架构 (Async I/O)**:
    *   引入 `asyncio` 和 `aiohttp`。
    *   重构 `Fetcher` 层，**并行获取** K线、盘口、资金流、新闻数据，而不是串行等待。
    *   示例: 从 `await data` (串行 3s+2s+1s=6s) 变为 `gather(data)` (并行 max(3,2,1)=3s)。
*   **智能缓存策略 (Smart Caching)**:
    *   **内存缓存**: 使用 `st.cache_data(ttl=...)` 缓存不常变的基础数据（如公司简介、F10资料）。
    *   **数据库优化**: 为 DuckDB 的查询字段（如 `stock_code`, `date`）建立索引。
*   **组件懒加载 (Lazy Loading)**:
    *   使用 `st.expander` 或 `st.tabs` 时，仅在用户点击展开/切换时才触发数据加载（配合 `st.fragment`）。

### 2.2 📈 TradingView 级行情体验 (Pro Charting) & 🎨 科幻风 UI (Sci-Fi Design)
**目标**: 打造专业且极具未来感的看盘界面。

*   **🎨 科幻风/赛博朋克 UI 设计 (Cyberpunk Design System)**:
    *   **配色方案 (Color Palette)**:
        *   **背景**: 深空黑 (`#0e1117`) / 科技灰 (`#161b22`)。
        *   **主色调 (Neon Accents)**: 赛博蓝 (`#00f3ff`), 霓虹紫 (`#bc13fe`), 矩阵绿 (`#0aff0a`), 警示红 (`#ff0055`)。
    *   **视觉元素 (Visual Elements)**:
        *   **Glassmorphism (毛玻璃)**: 侧边栏和卡片背景采用半透明磨砂效果。
        *   **Glowing Effects (发光特效)**: 关键数据（如最新价、涨跌幅）增加外发光 (Box-shadow glow)。
        *   **Fonts (字体)**: 标题使用等宽字体 (Monospace) 或现代无衬线字体，营造终端/控制台氛围。
    *   **实现方式 (Implementation)**:
        *   编写 `assets/style.css`，通过 `st.markdown('<style>...</style>', unsafe_allow_html=True)` 注入全局样式。
        *   定制 Streamlit 主题配置 `.streamlit/config.toml`。

*   **引入 Lightweight Charts**:
    *   集成 `streamlit-lightweight-charts-nt` 组件。
    *   **暗色适配**: 配置图表背景透明或深色，K线颜色使用高饱和度的红/绿（或青/紫以符合赛博风格）。
    *   实现高性能 Canvas 渲染，支持鼠标滚轮缩放、拖拽平移、十字光标。

*   **全维行情聚合页 (Composite Quote Page)**:
    *   **布局重构**:
        *   **Top**: 实时价格 ticker + 核心异动标签 (发光徽章)。
        *   **Center**: TradingView K线图 (左) + 深度盘口/逐笔成交 (右, 终端风格列表)。
        *   **Bottom (多维面板)**:
            *   `Tab 1 深度资料`: 公司主营、F10。
            *   `Tab 2 资金博弈`: 主力/超大单/北向资金流向图。
            *   `Tab 3 机构透视`: **(新)** 机构持仓变化、基金重仓列表。
            *   `Tab 4 舆情新闻`: 实时新闻流。

### 2.3 🧠 Zhipu AI 智能体与 RAG 系统 (AI Agent & RAG)
**目标**: 让 AI "读懂" 市场，成为私人基金经理。

*   **模型选型**: 接入 **Zhipu AI (ChatGLM-4)** API。
*   **RAG 架构 (检索增强生成)**:
    *   **向量数据库**: 部署 `ChromaDB` (轻量级) 或利用 DuckDB 的向量扩展。
    *   **数据入库 (Ingestion Pipeline)**:
        *   **文本类**: 新闻、研报、公告 -> 分块 -> Embedding -> Vector DB。
        *   **数值类**: 将每日行情摘要（如"茅台今日涨跌幅+2%，放量"）转化为自然语言文本存入 RAG，以便 AI 模糊检索。
*   **Agent (智能体) 设计**:
    *   构建 `ResearchAgent`，具备以下 **Tools (工具)**:
        *   `query_price_history`: 查询 SQL 数据库获取精确历史数据。
        *   `query_news_rag`: 在向量库中检索相关新闻和舆情。
        *   `query_institutional_holdings`: 查询机构持仓表。
    *   **工作流**: 用户提问 -> Agent 规划 (思考需要查什么数据) -> 调用工具 -> 汇总信息 -> 生成回答。

### 2.4 🏦 机构与主力数据扩展 (Institutional Data)
**目标**: 追踪"聪明钱" (Smart Money)。

*   **数据源扩展**:
    *   新增 `InstitutionalFetcher`，对接 AkShare 的机构持仓接口 (`stock_institute_hold_detail_...`)。
*   **可视化**:
    *   **持仓变动图**: 展示机构持股比例的历史走势。
    *   **持仓分布**: 饼图展示基金、社保、QFII 等不同类型机构的占比。

---

## 3. 实施路线图 (Execution Roadmap)

### Phase 1: 架构拆分与性能基石 (Architecture & Performance)
*   **任务 1.1**: 将 `main.py` 拆分为 `Home.py` + `pages/` 多页面结构。
*   **任务 1.2**: 引入 `asyncio`，重构 `MarketDataFetcher` 支持并发请求。
*   **任务 1.3**: 优化 Streamlit 缓存机制，确保页面秒开。

### Phase 2: TradingView 行情页重构 (UI/UX)
*   **任务 2.1**: **(UI)** 编写 `assets/style.css` 和 `.streamlit/config.toml`，实现全站科幻/赛博朋克主题。
*   **任务 2.2**: 集成 `lightweight-charts`，替换原有 Plotly K线图，并适配暗色主题。
*   **任务 2.3**: 开发 `StockCompositeView` 组件，实现 价格+资料+资金+新闻 的聚合显示。
*   **任务 2.4**: 开发机构数据接口，并集成到行情页底部 Tab。

### Phase 3: AI 智能体与 RAG 搭建 (AI & RAG)
*   **任务 3.1**: 搭建 ChromaDB 环境，编写脚本将历史新闻和行情摘要向量化入库。
*   **任务 3.2**: 封装 Zhipu AI API。
*   **任务 3.3**: 开发 `ResearchAgent`，实现 "查库" 和 "查RAG" 的工具链。
*   **任务 3.4**: 在 `AI 投研` 页面实现对话式交互。

### Phase 4: 系统集成与测试 (Integration)
*   **任务 4.1**: 全局联调，确保 AI 能读取到最新的行情数据。
*   **任务 4.2**: 压力测试，验证并发获取数据时的稳定性。

### Phase 5: 深度策略研究与 AutoML (Strategy Research)
*   **任务 5.1**: 开发 `7_🔬_策略研究.py`，构建因子工厂与模型训练实验室。
*   **任务 5.2**: 实现 **FactorLab** 核心引擎，支持技术面/基本面因子的批量计算与参数化配置。
*   **任务 5.3**: 引入 **Optuna** 自动化超参数寻优框架，支持对策略参数（如均线周期、模型学习率）进行贝叶斯优化。
*   **任务 5.4**: 构建因子分析模块，计算 IC 值、分层回测收益，科学评估因子有效性。

---

## 4. 立即行动建议 (Next Steps)

建议优先执行 **Phase 1 (性能与架构)** 和 **Phase 2 (行情页重构)** 的部分内容，让系统先"快"起来、"好看"起来，再注入 AI 灵魂。

1.  **重构目录结构**: 建立 `pages/`。
2.  **并发改造**: 修改 Fetcher。
3.  **UI 升级**: 引入 TradingView 组件。
