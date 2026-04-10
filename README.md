# flashcard_engine

一个跑在终端里的英语单词学习工具。打开一篇外刊文章，挑出生词，调大模型生成释义和例句，存进本地数据库，之后按艾宾浩斯间隔复习。

整个流程不离开终端，没有广告，数据全在本地。

---

## 它能做什么

1. **拉取外刊** — 从 BBC、The Guardian、The Verge、NPR 等 RSS 源获取最新文章，按 F 可切换源
2. **阅读 + 挑词** — 正文提取后全屏显示，Enter 进入选词模式，Space 把单词移进备忘录
3. **AI 解析** — 把选好的词打包发给大模型，返回音标、中文释义、例句、易混淆词
4. **本地存储** — 所有闪卡存进 SQLite，不依赖任何云服务
5. **间隔复习** — 按艾宾浩斯曲线调度复习时间，1/2/3 分别对应认识/模糊/忘记
6. **词库查看** — 按 L 可以翻看所有已保存的单词

生词过滤默认对照考研大纲词汇（约 4800 词，首次使用按 I 联网导入）。

---

## 环境要求

- Python 3.9+
- 能访问 DeepSeek API（或其他 OpenAI 接口兼容的模型）

---

## 部署步骤

### 1. 克隆项目

```bash
git clone <repo_url>
cd flashcard_engine
```

### 2. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置 API Key

在项目根目录创建 `.env` 文件：

```bash
touch .env
```

写入你的 API Key：

```
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**获取 DeepSeek API Key：** 前往 [platform.deepseek.com](https://platform.deepseek.com) 注册，在「API Keys」页面创建密钥。DeepSeek 按 token 计费，解析几十个单词的花费可以忽略不计。

如果你想用其他模型（比如 GPT-4、Kimi、Qwen），修改 `src/nlp_core.py` 里的 `url` 和 `model` 字段即可，接口是 OpenAI 标准格式。

### 5. 初始化数据库

```bash
python -m src.db_models
```

### 6. 导入考研词库（可选但推荐）

首次运行时，按 I 键会自动从网络下载考研大纲词汇（约 4800 词，来源：ECDICT 开源词典）。

或者直接在命令行跑：

```bash
python -m src.vocab_scraper
```

### 7. 启动

```bash
python main.py
```

---

## 按键说明

| 按键 | 场景 | 功能 |
|------|------|------|
| Enter | 新闻列表 | 打开文章 |
| Enter | 阅读视图 | 进入选词模式 |
| Enter | 选词模式 | 提交给 AI 解析 |
| Space | 选词模式 | 把当前词移入/移出备忘录 |
| W / S | 各处 | 上移 / 下移 |
| A / D | 选词模式 | 切换左右栏 |
| Esc | 各处 | 返回上一级 |
| R | 主页 | 进入复习模式 |
| Space | 复习 | 预览答案 |
| 1 / 2 / 3 | 复习 | 认识 / 模糊 / 忘记（同时揭示答案） |
| L | 主页 | 查看词库 |
| F | 主页 | 切换 RSS 源并刷新 |
| I | 主页 | 从网络导入考研词库 |
| Q | 各处 | 退出 |

---

## 项目结构

```
flashcard_engine/
├── main.py              # 主程序，TUI 状态机
├── src/
│   ├── db_models.py     # 数据库表结构（SQLAlchemy）
│   ├── crud.py          # 数据库读写
│   ├── nlp_core.py      # 调用大模型生成闪卡
│   ├── scheduler.py     # 艾宾浩斯复习调度
│   └── vocab_scraper.py # 考研词库爬虫（ECDICT）
├── data/
│   └── flashcards.db    # 本地数据库（自动生成）
├── .env                 # API Key（不提交 git）
└── requirements.txt
```

---

## 关于词库过滤

文章正文提取完毕后，程序会从中找出所有 5 字母以上的英文词，然后和考研大纲词库取交集，最多取 15 个候选词推入选词界面。

如果词库为空（没有导入过），会直接取正文前 15 个长词作为候选，不做过滤。

---

## 常见问题

**文章提取失败 / 403 错误**

部分网站有反爬保护。换一篇文章试试，或者按 F 换个 RSS 源。

**大模型返回格式不对**

`nlp_core.py` 用了 `response_format: json_object` 强制结构化输出，DeepSeek 支持这个参数。如果换用其他模型遇到问题，把这行去掉，解析逻辑可能需要调整。

**复习界面没有单词释义**

确认大模型 API 正常，检查 `data/flashcards.db` 里相应单词的 `translation` 字段是否有内容。
