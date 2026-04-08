from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label
from textual.containers import Horizontal, Vertical


class FlashcardUI(App):
    """升级版双栏穿梭 UI，彻底修复光标与按键逻辑"""

    # 🎨 核心视觉修复：利用 CSS 伪类解决光标视觉污染
    CSS = """
    Horizontal {
        height: 100%;
    }
    
    /* 默认状态：暗色边框 */
    .column {
        width: 1fr;
        height: 100%;
        border: round #555555; 
        padding: 1;
    }
    
    /* 🎯 视觉魔法：当列获得焦点时，边框变粗且变成极客绿 */
    .column:focus-within {
        border: thick #00ff00;
    }
    
    .col-title {
        content-align: center middle;
        text-style: bold;
        width: 100%;
        margin-bottom: 1;
        background: #333333;
    }
    
    ListView {
        height: 1fr;
    }
    
    /* 🎯 视觉魔法：默认隐藏所有选中光标的背景色 */
    ListView > ListItem.--highlight {
        background: transparent;
    }
    
    /* 只有当 ListView 真正处于焦点状态时，才显示蓝色的选中光标 */
    ListView:focus > ListItem.--highlight {
        background: #3273f6; 
        text-style: bold;
    }
    """

    # ⌨️ 全局按键映射重构 (严格符合你的要求)
    BINDINGS = [
        ("q", "quit", "退出"),
        ("a", "focus_left", "← 移至左侧"),
        ("left", "focus_left", "← 移至左侧"),
        ("d", "focus_right", "→ 移至右侧"),
        ("right", "focus_right", "→ 移至右侧"),
        ("w", "cursor_up", "↑ 上移"),
        ("s", "cursor_down", "↓ 下移"),
        ("space", "transfer_word", "🔁 转移单词 (Space)"),
        ("enter", "submit_words", "✅ 确认提交 (Enter)"),
    ]

    def compose(self) -> ComposeResult:
        """UI 布局渲染"""
        yield Header(show_clock=True)

        with Horizontal():
            with Vertical(classes="column"):
                yield Label("📚 待挑生词库", classes="col-title")
                yield ListView(id="source_list")

            with Vertical(classes="column"):
                yield Label("📥 入库备忘录", classes="col-title")
                yield ListView(id="pending_list")

        yield Footer()

    def on_mount(self) -> None:
        """初始化加载数据"""
        mock_words = ["ubiquitous", "flourish", "coherent", "deprive", "evaluate"]
        source_list = self.query_one("#source_list", ListView)

        for word in mock_words:
            source_list.append(ListItem(Label(word), id=f"item_{word}"))

        source_list.focus()

    # ================== 核心交互逻辑重构 ==================

    def action_focus_left(self) -> None:
        """A 键 / 左箭头：强行锁定左侧焦点"""
        self.query_one("#source_list").focus()

    def action_focus_right(self) -> None:
        """D 键 / 右箭头：强行锁定右侧焦点"""
        self.query_one("#pending_list").focus()

    def action_cursor_up(self) -> None:
        """W 键：拦截并转换为向上移动光标"""
        if isinstance(self.focused, ListView):
            self.focused.action_cursor_up()

    def action_cursor_down(self) -> None:
        """S 键：拦截并转换为向下移动光标"""
        if isinstance(self.focused, ListView):
            self.focused.action_cursor_down()

    def action_transfer_word(self) -> None:
        """Space 键：执行单词在左右两栏的搬运，并优雅继承光标"""
        active_list = self.focused
        if not isinstance(active_list, ListView):
            return

        highlighted_item = active_list.highlighted_child
        if not highlighted_item:
            return

        # 🌟 核心修复 1：在元素被销毁前，记住光标当前的行号 (Index)
        current_index = active_list.index

        # 提取单词并移动
        word_text = highlighted_item.query_one(Label).renderable
        source_list = self.query_one("#source_list", ListView)
        pending_list = self.query_one("#pending_list", ListView)

        if active_list.id == "source_list":
            pending_list.append(ListItem(Label(word_text), id=f"item_{word_text}"))
        elif active_list.id == "pending_list":
            source_list.append(ListItem(Label(word_text), id=f"item_{word_text}"))

        # 销毁原列表中的元素
        highlighted_item.remove()

        # 🌟 核心修复 2：强行分配光标的继承权
        # (len - 2 是因为 remove() 是异步的，此时旧元素还未完全从 children 数组中剥离)
        max_index = max(0, len(active_list.children) - 2)

        if max_index >= 0:
            # 如果删的是最后一个词，光标退一格；否则光标留在原地，顶替新上来的词
            active_list.index = min(current_index, max_index) 

    def action_submit_words(self) -> None:
        """Enter 键：最终全局确认提交"""
        pending_list = self.query_one("#pending_list", ListView)
        words_to_save = [
            item.query_one(Label).renderable for item in pending_list.children
        ]

        if not words_to_save:
            self.notify(
                "❌ 备忘录为空，请按 Space 键挑选单词后再按 Enter 提交！",
                severity="error",
            )
            return

        self.notify(
            f"✅ 成功截获入库指令！包含单词: {', '.join(words_to_save)}",
            severity="information",
        )
        # TODO: 退出 UI 并将 words_to_save 传递给 main.py 进行大模型处理


if __name__ == "__main__":
    app = FlashcardUI()
    app.run()
