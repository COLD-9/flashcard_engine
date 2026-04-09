import time
import re
import requests
import feedparser
from newspaper import Article

from textual.app import App, ComposeResult
from textual.widgets import (
    Header,
    Footer,
    ListView,
    ListItem,
    Label,
    LoadingIndicator,
    Static,
)
from textual.containers import Horizontal, Vertical, Center, VerticalScroll
from textual import work
from textual.message import Message

# 🌟 核心修复 1：引入 dataclass 魔法
from dataclasses import dataclass

from src.nlp_core import generate_flashcard_data
from src.crud import save_flashcard_to_db, load_syllabus_words


# ==========================================
# 📡 定义系统信号弹 (使用优雅的 dataclass，彻底告别 __init__ 报错)
# ==========================================
@dataclass
class RssLoadedMessage(Message):
    """RSS 拉取完毕的信号"""

    feeds: list


@dataclass
class ArticleParsedMessage(Message):
    """文章爬取并过筛完毕的信号"""

    title: str
    content: str
    words: list


@dataclass
class DbTaskCompletedMessage(Message):
    """AI解析并入库完毕的信号"""

    success_count: int


# ==========================================
# 🖥️ 核心 UI 引擎与状态机
# ==========================================
class FlashcardEngineApp(App):
    """全链路智能外刊记忆引擎主程序"""

    CSS = """
    /* 界面布局样式 */
    #loading_zone { height: 100%; align: center middle; display: none; }
    #rss_zone { height: 100%; padding: 1 5; display: block; }
    #reading_zone { height: 100%; padding: 1 5; display: none; }
    #shuttle_zone { height: 100%; display: none; }

    #article_scroll { height: 1fr; border: round #555555; padding: 1 2; }
    #article_body { width: 100%; }
    #reading_hint { content-align: center middle; color: #00ff00; margin-top: 1; }

    .column { width: 1fr; height: 100%; border: round #555555; padding: 1; }
    .column:focus-within { border: thick #00ff00; }
    .col-title { content-align: center middle; text-style: bold; width: 100%; margin-bottom: 1; background: #333333; }
    ListView { height: 1fr; }
    ListView > ListItem.--highlight { background: transparent; }
    ListView:focus > ListItem.--highlight { background: #3273f6; text-style: bold; }

    .loading-text { text-style: bold; color: #00ff00; margin-top: 1; }
    .article-title { text-style: bold; color: yellow; margin-bottom: 1; }
    """

    BINDINGS = [
        ("q", "quit", "退出系统"),
        ("w", "cursor_up", "↑ 上移"),
        ("s", "cursor_down", "↓ 下移"),
        ("a", "focus_left", "← 左侧"),
        ("d", "focus_right", "→ 右侧"),
        ("space", "transfer_word", "🔁 转移单词"),
        ("enter", "confirm_action", "✅ 确认执行"),
        ("escape", "go_back", "↩️ 返回"),
    ]

    def __init__(self):
        super().__init__()
        # 记录当前处在哪个界面状态：'rss', 'reading', 'shuttle', 'processing'
        self.current_state = "rss"
        self.is_locked = False  # 全局锁，防误触
        self.rss_url_map: dict[str, str] = {}  # safe_id -> 真实 URL 的映射
        self.current_article_context: str = ""  # 当前文章标题，给 AI 当语境
        self.pending_target_words: list[str] = []  # 阅读视图下暂存待筛选的生词

    def compose(self) -> ComposeResult:
        """渲染 UI 骨架"""
        yield Header(show_clock=True)

        # 容器 1：加载动画区 (默认隐藏)
        with Center(id="loading_zone"):
            yield LoadingIndicator()
            yield Label(
                "⏳ 正在执行高维计算，请稍候...",
                id="loading_msg",
                classes="loading-text",
            )

        # 容器 2：RSS 新闻流区
        with Vertical(id="rss_zone"):
            yield Label("🌍 全球最新外刊信号截获", classes="col-title")
            yield ListView(id="rss_list")

        # 容器 3：沉浸式阅读区 (默认隐藏)
        with Vertical(id="reading_zone"):
            yield Label("📖 文章正文", id="article_title", classes="article-title")
            with VerticalScroll(id="article_scroll"):
                yield Static("", id="article_body")
            yield Label(
                "按 Enter 进入选词模式 ┊ Esc 返回新闻列表",
                id="reading_hint",
            )

        # 容器 4：双栏穿梭区 (默认隐藏)
        with Horizontal(id="shuttle_zone"):
            with Vertical(classes="column"):
                yield Label("📚 待挑生词库", classes="col-title")
                yield ListView(id="source_list")
            with Vertical(classes="column"):
                yield Label("📥 入库备忘录", classes="col-title")
                yield ListView(id="pending_list")

        yield Footer()

    def on_mount(self) -> None:
        """系统启动时：立刻派打工人去拉取 RSS"""
        self.fetch_rss_feeds()

    # ==========================================
    # 👷 后台打工人专区 (Asynchronous Workers)
    # ==========================================
    @work(exclusive=True, thread=True)
    def fetch_rss_feeds(self) -> None:
        """Worker A: 终极防弹版 RSS 抓取"""
        import requests

        # 推荐使用 The Verge 或 BBC
        url = "https://www.theverge.com/rss/index.xml"

        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            response = requests.get(url, headers=headers, timeout=8)
            response.raise_for_status()

            # 🌟 核心修复 2：强制使用 response.text (纯文本) 而不是 content
            feed = feedparser.parse(response.text)

            if not feed.entries:
                self.app.call_from_thread(
                    self.notify, "⚠️ RSS 源没有返回新闻。", severity="warning"
                )
                return

            results = [
                {"title": entry.title, "link": entry.link} for entry in feed.entries[:8]
            ]
            self.post_message(RssLoadedMessage(results))

        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"❌ RSS 抓取失败: {e}", severity="error"
            )

    @work(exclusive=True, thread=True)
    def parse_article(self, title: str, url: str) -> None:
        """Worker B: 终极解耦版正文爬虫 (Requests 强抓 + 源码注入)"""
        import requests
        from newspaper import Article
        import re

        try:
            # 🎭 终极伪装：不仅仅是 User-Agent，加上全套真实的浏览器头信息
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Referer": "https://news.ycombinator.com/",
            }

            # 1. 让 Requests 去硬刚反爬防火墙，拿下 HTML 源码
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()  # 遇到 403/404 直接抛异常
            raw_html = response.text

            # 2. 绕过 newspaper3k 的网络层，直接把源码注入给它清洗
            article = Article(url)  # 这里的 url 只是给它做基础参考，不发请求
            article.set_html(raw_html)  # 💉 核心魔法：直接注入 HTML 源码！
            article.parse()
            text = article.text

            if not text.strip():
                raise Exception(
                    "抓到了网页，但防爬墙太高导致正文无法提取，或者该页面全是视频/图片。"
                )

            # 词库过筛逻辑：先抽取所有 5 字母以上的英文单词
            raw_words = re.findall(r"\b[a-zA-Z]{5,}\b", text.lower())
            unique_words = list(dict.fromkeys(raw_words))  # 去重并保留首次出现顺序

            # 与考研/四六级大纲词库取交集；若大纲库为空则回退到截断模式
            syllabus = load_syllabus_words()
            if syllabus:
                filtered = [w for w in unique_words if w in syllabus]
                target_words = filtered[:15] if filtered else unique_words[:15]
            else:
                target_words = unique_words[:15]

            # 成功剥离！发射胜利信号
            self.post_message(ArticleParsedMessage(title, text, target_words))

        except requests.exceptions.Timeout:
            self.app.call_from_thread(
                self.notify,
                "❌ 目标网站响应太慢 (超时)，请换一篇尝试。",
                severity="error",
            )
            self.app.call_from_thread(self.reset_to_rss)
        except requests.exceptions.HTTPError as e:
            # 专门捕获 403 Forbidden 等状态码
            self.app.call_from_thread(
                self.notify,
                f"❌ 被目标网站的反爬虫系统拦截: HTTP {e.response.status_code}",
                severity="error",
            )
            self.app.call_from_thread(self.reset_to_rss)
        except Exception as e:
            self.app.call_from_thread(
                self.notify, f"❌ 解析失败: {str(e)[:40]}...", severity="error"
            )
            self.app.call_from_thread(self.reset_to_rss)

    @work(exclusive=True, thread=True)
    def process_and_save_words(self, words: list, context_sentence: str) -> None:
        """Worker C: 最重的工作，呼叫 AI 并存入数据库"""
        success_count = 0
        for word in words:
            # 1. 呼叫大模型 (这里的 context 简化传入了文章标题)
            flashcard_data = generate_flashcard_data(word, context_sentence)

            if flashcard_data:
                # 2. 呼叫仓管员存入数据库
                is_saved = save_flashcard_to_db(flashcard_data)
                if is_saved:
                    success_count += 1

            # 遵守 API 速率限制，温柔一点
            time.sleep(1)

        # 搞定！发射完工信号
        self.post_message(DbTaskCompletedMessage(success_count))

    # ==========================================
    # 📡 前台接收信号并更新 UI (Message Handlers)
    # ==========================================
    def on_rss_loaded_message(self, message: RssLoadedMessage) -> None:
        """收到 RSS 信号：安全渲染新闻列表"""
        rss_list = self.query_one("#rss_list", ListView)
        rss_list.clear()
        self.rss_url_map.clear()  # 清空旧映射

        # 🌟 核心修复：使用安全的数字 ID，把网址存到字典里
        for i, item in enumerate(message.feeds):
            safe_id = f"rss_item_{i}"
            self.rss_url_map[safe_id] = item["link"]  # 悄悄记录真实 URL

            list_item = ListItem(Label(f"📰 {item['title']}"), id=safe_id)
            rss_list.append(list_item)

        rss_list.focus()

    def on_article_parsed_message(self, message: ArticleParsedMessage) -> None:
        """收到文章爬取完毕信号：先进入沉浸式阅读视图"""
        self.hide_loading()
        self.current_state = "reading"

        # 隐藏 RSS 区，显示阅读区
        self.query_one("#rss_zone").display = False
        self.query_one("#reading_zone").display = True

        # 渲染标题与正文
        self.query_one("#article_title", Label).update(f"📖 {message.title}")
        self.query_one("#article_body", Static).update(message.content)
        self.query_one("#article_scroll").focus()

        # 暂存上下文与已过筛的生词，等用户按 Enter 才进选词
        self.current_article_context = message.title
        self.pending_target_words = message.words

    def on_db_task_completed_message(self, message: DbTaskCompletedMessage) -> None:
        """收到入库完毕信号：完结撒花，重置系统"""
        self.hide_loading()
        self.notify(
            f"🎉 太棒了！成功将 {message.success_count} 个生词封印进记忆库！",
            severity="information",
        )
        self.reset_to_rss()

    # ==========================================
    # 🕹️ 键盘交互与状态控制逻辑
    # ==========================================
    def show_loading(self, text: str) -> None:
        """开启全局锁，显示 Loading"""
        self.is_locked = True
        self.query_one("#rss_zone").display = False
        self.query_one("#reading_zone").display = False
        self.query_one("#shuttle_zone").display = False
        self.query_one("#loading_zone").display = True
        self.query_one("#loading_msg", Label).update(text)

    def hide_loading(self) -> None:
        """解除全局锁"""
        self.is_locked = False
        self.query_one("#loading_zone").display = False

    def reset_to_rss(self) -> None:
        """系统轮回：回到初始的主页状态"""
        self.hide_loading()
        self.current_state = "rss"
        self.query_one("#shuttle_zone").display = False
        self.query_one("#reading_zone").display = False
        self.query_one("#rss_zone").display = True

        # 清空之前的备忘录
        self.query_one("#pending_list", ListView).clear()
        self.query_one("#rss_list", ListView).focus()

    def enter_shuttle_mode(self) -> None:
        """从阅读视图切到双栏选词模式"""
        self.current_state = "shuttle"
        self.query_one("#reading_zone").display = False
        self.query_one("#shuttle_zone").display = True

        source_list = self.query_one("#source_list", ListView)
        source_list.clear()
        # 顺便清空右侧备忘录，避免上一篇文章的残留
        self.query_one("#pending_list", ListView).clear()
        for word in self.pending_target_words:
            source_list.append(ListItem(Label(word), id=f"word_{word}"))

        source_list.focus()

    # --- 按键动作重定向 ---
    def action_confirm_action(self) -> None:
        """全局 Enter 键处理器"""
        if self.is_locked:
            return

        if self.current_state == "rss":
            active_list = self.query_one("#rss_list", ListView)
            selected = active_list.highlighted_child
            if selected:
                # 🌟 核心修复：去字典里安全提取真实 URL
                url = self.rss_url_map.get(selected.id)
                if not url:
                    self.notify("❌ 无法定位文章链接", severity="error")
                    return
                # Rich Text → str，并剥掉装饰用的 📰 前缀
                raw_title = str(selected.query_one(Label).renderable)
                title = raw_title.removeprefix("📰 ").strip()

                self.show_loading("✂️ 正在提取正文，请稍候...")
                self.parse_article(title, url)

        elif self.current_state == "reading":
            # 阅读完毕，进入选词模式
            if not self.pending_target_words:
                self.notify("⚠️ 当前文章没有可挑选的生词", severity="warning")
                return
            self.enter_shuttle_mode()

        elif self.current_state == "shuttle":
            # 状态：在选词。提取右侧单词，呼叫大模型
            pending_list = self.query_one("#pending_list", ListView)
            words_to_save = [
                str(item.query_one(Label).renderable) for item in pending_list.children
            ]

            if not words_to_save:
                self.notify(
                    "❌ 备忘录为空，请按 Space 键挑选单词后再按 Enter 提交！",
                    severity="warning",
                )
                return

            self.show_loading(
                f"🧠 DeepSeek 正在为你深度解析 {len(words_to_save)} 个单词..."
            )
            self.process_and_save_words(
                words_to_save, self.current_article_context
            )  # 派打工人 C 去干活

    # (这部分保留你之前写好的左右焦点切换和上下移动代码)
    def action_focus_left(self) -> None:
        if not self.is_locked and self.current_state == "shuttle":
            self.query_one("#source_list").focus()

    def action_focus_right(self) -> None:
        if not self.is_locked and self.current_state == "shuttle":
            self.query_one("#pending_list").focus()

    def action_cursor_up(self) -> None:
        if not self.is_locked and isinstance(self.focused, ListView):
            self.focused.action_cursor_up()

    def action_cursor_down(self) -> None:
        if not self.is_locked and isinstance(self.focused, ListView):
            self.focused.action_cursor_down()

    def action_go_back(self) -> None:
        """Esc 键：根据当前状态返回上一级"""
        if self.is_locked:
            return
        if self.current_state == "reading":
            # 阅读视图 → 回到 RSS 列表
            self.reset_to_rss()
        elif self.current_state == "shuttle":
            # 选词视图 → 回到 RSS 列表
            self.reset_to_rss()

    def action_transfer_word(self) -> None:
        """全局 Space 键：左右搬运单词 (继承之前的完美光标逻辑)"""
        if self.is_locked or self.current_state != "shuttle":
            return

        active_list = self.focused
        if not isinstance(active_list, ListView):
            return
        highlighted_item = active_list.highlighted_child
        if not highlighted_item:
            return

        current_index = active_list.index
        word_text = str(highlighted_item.query_one(Label).renderable)
        source_list = self.query_one("#source_list", ListView)
        pending_list = self.query_one("#pending_list", ListView)

        if active_list.id == "source_list":
            pending_list.append(ListItem(Label(word_text), id=f"item_{word_text}"))
        elif active_list.id == "pending_list":
            source_list.append(ListItem(Label(word_text), id=f"item_{word_text}"))

        highlighted_item.remove()
        max_index = max(0, len(active_list.children) - 2)
        if max_index >= 0:
            active_list.index = min(current_index, max_index)


if __name__ == "__main__":
    app = FlashcardEngineApp()
    app.run()
