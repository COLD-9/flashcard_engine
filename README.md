🧠 AI-Powered Flashcard Engine (智能外刊阅读与记忆引擎) V2.0
🚀 “拒绝被动填鸭，掌控学习主权。”
这是一个基于 Python 终端引擎 (Textual) 构建的极客风沉浸式英语学习系统。它巧妙融合了 RSS 资讯阅读、大模型 (LLM) 语境解析 与 本地 SQLite 记忆调度，专为考研及高阶英语学习者打造。

✨ 核心亮点 (Features)
📰 活水资讯源 (RSS Feeds): 告别死板词库，系统启动即拉取顶级外刊（如 The Economist, BBC）最新头条，打造个性化终端阅读器。

🎯 智能交集与漏斗 (Smart Filter): 自动提取文章正文，剥离广告，并与内置考研/四六级大纲词库取交集，只为你呈现“值得背的高频生词”。

🕹️ 全键盘交互 (TUI Shuttle Box): 抛弃简陋的命令行输入，采用高级的终端双栏穿梭 UI。使用 W/S/A/D 和 Space 键在沉浸状态下完成生词挑选，极客体验拉满。

🤖 AI 语境级解析 (Contextual LLM): 告别传统词典的生搬硬套。调用大模型，基于生词所在的真实句子，生成“音标 + 精准释义 + 形近词避坑指南”的结构化知识包。

📈 科学记忆库 (Local Memory DB): 结合 SQLAlchemy 与本地轻量级 SQLite，记录每一张闪卡的状态，支持“一键斩词 (彻底掌握)”，为后续接入艾宾浩斯复习算法提供坚实的数据底座。

🛠️ 技术栈选型 (Tech Stack)
编程语言: Python 3.10+

前端 UI 引擎: Textual (构建现代复杂的终端界面 TUI)

数据持久化: SQLite + SQLAlchemy (ORM 对象关系映射)

网络与爬虫: requests / newspaper3k (RSS 拉取与正文静默提取)

AI 引擎: 兼容 OpenAI 格式的大语言模型接口 (如 DeepSeek-Chat)

配置管理: python-dotenv

文件结构
flashcard_engine/
│
├── data/                      # 本地数据大本营
│   └── flashcards.db          # SQLite 物理数据库文件 (自动生成)
│
├── src/                       # 核心源代码目录
│   ├── __init__.py
│   ├── tui_app.py             # 终端 UI 引擎 (Textual 界面渲染与按键调度)
│   ├── nlp_core.py            # AI 大脑 (负责与大模型通信，Prompt 工程)
│   ├── db_models.py           # 数据库架构 (定义 SQLAlchemy 表结构与外键关联)
│   └── crud.py                # 仓管员 (负责处理数据的增删改查、防重与更新)
│
├── .env                       # 环境变量文件 (存放 API Key，绝对不上传 Git)
├── .gitignore                 # Git 忽略配置
├── requirements.txt           # 项目依赖包清单
├── main.py                    # ✅ 系统总指挥 (FlashcardEngineApp 全链路状态机)
└── README.md                  # 项目说明文档

 📅 开发进度与路线图 (Roadmap)
我们采用了敏捷开发的模式，将系统拆解为独立的模块并逐步组装：
[x] Phase 1: 基础设施构建

[x] 搭建隔离的虚拟环境，配置安全防线 .env。

[x] Phase 2: AI 大脑与数据仓库

[x] nlp_core.py: 跑通 API 调用，利用 response_format 强制大模型输出标准 JSON (包含音标、释义、易混淆词)。

[x] db_models.py: 设计并落地 Flashcard 与 ConfusingWord 的一对多关系数据库，引入 is_mastered 斩词状态。

[x] crud.py: 实现安全入库流水线，包含防御性字段提取与“老词新遇”的自动更新逻辑。

[x] Phase 3: 沉浸式终端 UI (TUI) 引擎

[x] tui_app.py: 攻克终端焦点控制难点，实现高颜值的“双栏穿梭选词 (Shuttle Box)”界面。

[x] 劫持并重写 W/S/A/D 与 Space 按键绑定，实现丝滑的元素搬运与光标继承。

[x] Phase 4: 全链路串联 (DONE)

[x] 接入 RSS 新闻源，实现首页 Dashboard 的动态信息流展示。

[x] 结合 newspaper3k 实现后台静默文章提取（强抓 + HTML 注入绕反爬）。

[x] 彻底打通前台 UI 与后台引擎：RSS 列表 → 沉浸式阅读视图 → 双栏穿梭选词 → AI 解析入库，全链路异步消息驱动。

[x] 接入大纲词库交集过滤（syllabus_words 表非空时自动按考研/四六级词库过筛，否则回退截断模式）。

[ ] Phase 5: 复习调度系统

[ ] 开发复习模式的 UI 界面。

[ ] 根据用户反馈 (认识/模糊/忘记) 动态更新下一次复习日期。

核心工作流解析 (How it works)
Read (输入): 系统拉取 RSS 标题 $\rightarrow$ 用户敲击回车选中 $\rightarrow$ 后台爬取并清洗正文 $\rightarrow$ 全屏显示供用户沉浸阅读。

Select (挑选): 阅读完毕，UI 瞬间切换为双栏模式。系统将正文生词罗列在左侧，用户通过空格键将想要记忆的词“搬运”至右侧备忘录。

Process (加工): 用户按下 Enter 提交。UI 冻结并展示 Loading，系统后台将生词打包发给 AI 获取结构化语境解析。

Store (存储): 解析结果交给 ORM，自动处理数据冲突、建立树枝关联，落盘至 SQLite。