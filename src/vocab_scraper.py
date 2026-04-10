"""
考研英语大纲词汇在线爬取器

数据来源：ECDICT（skywind3000）—— 一个开源英汉词典数据库，
其 tag 字段用 'ky' 标记官方考研大纲词汇（约 5500 词）。
项目地址：https://github.com/skywind3000/ECDICT

运行方式（命令行一次性导入）：
    python -m src.vocab_scraper

或从 TUI 内按 I 键触发后台导入。
"""
import csv
import io
import requests
from typing import Callable, Optional

from src.db_models import SessionLocal, SyllabusWord

ECDICT_URL = (
    "https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv"
)


def fetch_kaoyan_words(
    progress_cb: Optional[Callable[[str], None]] = None,
) -> list[str]:
    """
    流式下载 ECDICT，提取所有 tag='ky' 的考研词汇（纯英文单词列表）。

    progress_cb：可选回调，参数为进度说明字符串，供 TUI 用来刷新状态。
    返回：去重后的小写单词列表。
    """
    if progress_cb:
        progress_cb("正在连接 ECDICT 数据库…")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
    }

    resp = requests.get(ECDICT_URL, headers=headers, stream=True, timeout=30)
    resp.raise_for_status()

    ky_words: list[str] = []
    buf = ""
    downloaded_mb = 0
    total_rows = 0
    first_row = True

    for chunk in resp.iter_content(chunk_size=131_072, decode_unicode=True):
        buf += chunk
        downloaded_mb += len(chunk.encode("utf-8")) / (1024 * 1024)

        # 切出完整行，留下末尾不完整的片段
        lines = buf.split("\n")
        buf = lines[-1]

        for line in lines[:-1]:
            if first_row:
                first_row = False
                continue  # 跳过 header
            total_rows += 1

            # 每下载约 10MB 汇报一次进度
            if progress_cb and total_rows % 30_000 == 0:
                progress_cb(
                    f"已下载 {downloaded_mb:.0f} MB，"
                    f"扫描 {total_rows:,} 行，"
                    f"找到 {len(ky_words)} 个考研词…"
                )

            # 正确处理 CSV 引号
            try:
                row = next(csv.reader(io.StringIO(line)))
            except StopIteration:
                continue

            if len(row) < 8:
                continue

            word = row[0].strip().strip("'\"").lower()
            tag = row[7].strip()

            # tag 字段以空格分隔，e.g. "cet4 ky" 或 "ky gre"
            if "ky" in tag.split() and word.isalpha() and len(word) >= 3:
                ky_words.append(word)

    # 处理最后一行（如果有）
    if buf.strip():
        try:
            row = next(csv.reader(io.StringIO(buf)))
            if len(row) >= 8:
                word = row[0].strip().lower()
                tag = row[7].strip()
                if "ky" in tag.split() and word.isalpha() and len(word) >= 3:
                    ky_words.append(word)
        except Exception:
            pass

    # 去重
    return list(dict.fromkeys(ky_words))


def save_words_to_db(
    words: list[str],
    progress_cb: Optional[Callable[[str], None]] = None,
) -> int:
    """
    将单词列表写入 syllabus_words 表（清空旧数据后全量导入）。
    返回实际写入条数。
    """
    if progress_cb:
        progress_cb(f"正在写入数据库（共 {len(words)} 词）…")

    with SessionLocal() as session:
        # 清空旧数据（无论来自 seeder 还是上次爬取）
        session.query(SyllabusWord).delete()
        session.flush()

        for i, word in enumerate(words):
            session.add(SyllabusWord(word=word.lower(), is_kaoyan=True))
            if i % 500 == 0 and progress_cb:
                progress_cb(f"写入中… {i}/{len(words)}")

        session.commit()

    return len(words)


def run_import(
    progress_cb: Optional[Callable[[str], None]] = None,
) -> dict:
    """
    完整导入流程：爬取 → 写库。
    返回 {"ok": bool, "count": int, "error": str}
    """
    try:
        words = fetch_kaoyan_words(progress_cb)
        if not words:
            return {"ok": False, "count": 0, "error": "未能获取词汇，请检查网络"}
        count = save_words_to_db(words, progress_cb)
        return {"ok": True, "count": count, "error": ""}
    except Exception as e:
        return {"ok": False, "count": 0, "error": str(e)}


if __name__ == "__main__":
    def _print_progress(msg: str) -> None:
        print(f"\r  {msg}                    ", end="", flush=True)

    print("🚀 开始从网络导入考研大纲词汇…\n")
    result = run_import(_print_progress)
    print()
    if result["ok"]:
        print(f"✅ 导入完成！共写入 {result['count']} 个考研词汇到数据库。")
    else:
        print(f"❌ 导入失败: {result['error']}")
