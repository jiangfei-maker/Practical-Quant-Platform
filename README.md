# 实战量化交易平台 (Practical Quant Trading Platform) v2.0

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![DuckDB](https://img.shields.io/badge/DuckDB-FFF000?style=for-the-badge&logo=duckdb&logoColor=black)
![Polars](https://img.shields.io/badge/Polars-CD793D?style=for-the-badge&logo=polars&logoColor=white)
![AI Powered](https://img.shields.io/badge/AI-LLM%20Agent-00A67E?style=for-the-badge)

专为 **一人公司 (One-Person Company)** 打造的高性能、AI 驱动的全栈量化交易平台。本项目整合了 **Polars** (极速计算)、**DuckDB** (高效存储) 与 **LLM** (AI 投研)，构建了一套从数据采集、因子挖掘、回测验证到实盘交易的完整闭环系统。

## 🌟 核心亮点

### 1. 高性能数据引擎
- **DuckDB + Parquet**: 采用列式存储，支持亿级行情的秒级查询。
- **Polars**: 替代 Pandas 进行因子计算，速度提升 10-100 倍。
- **全市场覆盖**: 支持 A 股、港股、美股、期货等实时与历史数据 (基于 AkShare)。

### 2. AI 智能投研 (AI Research Agent)
- **LLM 驱动**: 集成 ZhipuAI (GLM-4) 等大模型，支持自然语言交互。
- **RAG 架构**: 结合本地金融数据库与网络搜索 (DuckDuckGo)，提供有理有据的研报生成。
- **智能工具链**: AI 可自主调用 SQL 查询、新闻搜索、财报分析等工具回答复杂问题。

### 3. 全功能量化闭环
- **实时行情**: 毫秒级快照监控，支持自定义自选股池。
- **财务分析**: 深度集成杜邦分析、财务风险预警模型。
- **策略回测**: 内置高性能回测引擎，支持向量化回测与事件驱动回测。
- **风控中心**: 实时监控账户风险，支持 VaR (在险价值) 计算与仓位管理。
- **模拟交易**: 提供逼真的模拟撮合环境，验证策略有效性。

## 🏗️ 系统架构

```
实战量化交易平台/
├── app/                # Streamlit 前端应用
│   ├── pages/          # 功能页面 (行情, 财务, 回测, AI投研等)
│   └── components/     # UI 组件
├── core/               # 核心领域逻辑
│   ├── data/           # 数据获取 (AkShare) 与清洗 (Polars)
│   ├── research/       # 因子挖掘与 AI 研报生成
│   ├── strategy/       # 策略引擎与回测框架
│   ├── risk/           # 风控模型
│   └── trading/        # 交易执行与撮合
├── services/           # 后台服务 (AI Agent, 调度任务)
├── data/               # 本地数据存储 (DuckDB, Parquet)
└── config/             # 系统配置
```

## 🚀 快速开始

### 1. 环境准备
确保已安装 Python 3.9 或更高版本。

```bash
# 克隆仓库
git clone https://github.com/jiangfei-maker/-.git Practical-Quant-Platform
cd Practical-Quant-Platform

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r 实战量化交易平台/requirements.txt
```

### 2. 配置 API Key (可选)
如需使用 AI 投研功能，请在环境变量或 `.streamlit/secrets.toml` 中配置：
```toml
# .streamlit/secrets.toml
ZHIPUAI_API_KEY = "your_zhipuai_key"
OPENAI_API_KEY = "your_openai_key"  # 如果使用 OpenAI
```

### 3. 启动平台
进入项目目录并启动 Streamlit：

```bash
streamlit run 实战量化交易平台/app/首页.py
```
访问浏览器 `http://localhost:8501` 即可使用。

## 📊 功能模块预览

| 模块 | 功能描述 |
| --- | --- |
| **📈 实时行情** | 全市场监控、分时/K线图表、主力资金流向 |
| **💰 财务分析** | 智能财报解读、杜邦分析可视化、估值模型 |
| **🧪 策略回测** | 多因子策略、网格交易、技术指标回测 |
| **🛡️ 风控中心** | 组合风险监控、个股黑名单管理 |
| **🧠 AI 投研** | 智能问答、自动生成每日复盘报告、行业研究 |
| **⚙️ 系统管理** | 数据同步任务调度、系统日志监控 |

## ⚠️ 免责声明

本平台仅供量化交易学习与研究使用，**不构成任何投资建议**。
- 市场有风险，投资需谨慎。
- 请勿直接将未经验证的策略用于实盘交易。
- 开发者不对因使用本软件造成的任何资金损失负责。

## 📄 许可证

MIT License
