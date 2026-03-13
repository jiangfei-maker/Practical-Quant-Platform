# 实战量化交易平台 (Real-world Quant Platform)

专为 **一人公司 (OPC)** 打造的高性能、AI 驱动的全栈量化交易平台。

## 🚀 项目愿景

整合 **Polars** (极速计算)、**DuckDB** (高效存储) 与 **LLM** (AI 投研)，构建一套从数据采集、因子挖掘、回测验证到实盘交易的完整闭环系统。

## 📚 核心文档

*   [项目主计划 (Project Master Plan)](docs/Project_Init/PROJECT_MASTER_PLAN.md)
*   [技术规格书 (Technical Specifications)](docs/Project_Init/TECHNICAL_SPECIFICATIONS.md)
*   [数据源清单 (Data Sources)](docs/Project_Init/DATA_SOURCES.md)

## 🛠️ 快速开始

### 1. 环境准备

确保已安装 Python 3.9+。

```bash
# 创建虚拟环境
python -m venv .venv

# 激活环境 (Windows)
.venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 目录结构

```
实战量化交易平台/
├── app/                # Streamlit 前端应用
│   ├── pages/          # 功能页面
│   └── components/     # UI 组件
├── core/               # 核心领域逻辑
│   ├── data/           # 数据获取与清洗
│   ├── research/       # 因子与研报生成
│   └── strategy/       # 回测与交易引擎
├── data/               # 本地数据存储
│   ├── db/             # DuckDB 数据库
│   └── market_depth/   # Parquet 高频数据
├── services/           # 后台调度服务
└── config/             # 系统配置
```

### 3. 运行平台

```bash
# 启动 Web 控制台
streamlit run app/main.py
```

## ⚠️ 风险提示

本平台仅供学习与研究使用，不构成任何投资建议。量化交易存在风险，实盘需谨慎。
