"""
🧠 艾宾浩斯复习调度器 (Ebbinghaus Review Scheduler)

职责：
- 根据用户对每张闪卡的反馈 (认识 / 模糊 / 忘记)，
  动态推算下一次的复习时间和熟悉度等级。
- 提供"今日待复习卡片"的查询入口，供 TUI 复习模式调用。

设计原则：
- 不直接修改 ORM 对象的内部细节，所有写入都通过新的 session 完成。
- 调度算法独立，方便后续替换为 SM-2 / FSRS 等更先进的算法。
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List

from src.db_models import SessionLocal, Flashcard


# 📐 艾宾浩斯遗忘曲线复习区间 (单位：天)
# 索引即 retention_score，分数越高复习间隔越长。
EBBINGHAUS_INTERVALS_DAYS = [1, 2, 4, 7, 15, 30, 60, 120, 240]


@dataclass
class ConfusingWordInfo:
    word: str
    meaning: str
    distinction: str


@dataclass
class ReviewCard:
    """Session 无关的纯 Python 卡片快照，可安全跨线程传递。"""
    id: int
    word: str
    phonetic: str
    translation: str
    example: str
    synonyms: str
    retention_score: int
    confusing_words: List[ConfusingWordInfo] = field(default_factory=list)

# ✨ 当 retention_score 达到此阈值，自动判定"已掌握" (彻底斩词)
MASTERY_THRESHOLD = len(EBBINGHAUS_INTERVALS_DAYS)


def _interval_for_score(score: int) -> timedelta:
    """根据熟悉度分数取对应的艾宾浩斯区间，越界时取最长间隔。"""
    idx = max(0, min(score, len(EBBINGHAUS_INTERVALS_DAYS) - 1))
    return timedelta(days=EBBINGHAUS_INTERVALS_DAYS[idx])


def get_due_flashcards(limit: int = 20) -> List[ReviewCard]:
    """
    拉取所有"今天到期、且尚未斩词"的闪卡，按到期时间升序。
    在 session 内部将 ORM 对象转为纯 Python dataclass，
    避免 session 关闭后访问懒加载关系触发 DetachedInstanceError。
    """
    now = datetime.now()
    results: List[ReviewCard] = []
    with SessionLocal() as session:
        rows = (
            session.query(Flashcard)
            .filter(Flashcard.is_mastered == False)  # noqa: E712
            .filter(Flashcard.next_review_date <= now)
            .order_by(Flashcard.next_review_date.asc())
            .limit(limit)
            .all()
        )
        for row in rows:
            cw_list = [
                ConfusingWordInfo(
                    word=cw.word or "",
                    meaning=cw.meaning or "",
                    distinction=cw.distinction or "",
                )
                for cw in row.confusing_words  # 在 session 内安全访问
            ]
            results.append(
                ReviewCard(
                    id=row.id,
                    word=row.word or "",
                    phonetic=row.phonetic or "",
                    translation=row.translation or "",
                    example=row.example or "",
                    synonyms=row.synonyms or "",
                    retention_score=row.retention_score or 0,
                    confusing_words=cw_list,
                )
            )
    return results


def apply_review_feedback(card_id: int, feedback: str) -> dict:
    """
    根据用户反馈更新闪卡的 retention_score 与 next_review_date。

    feedback 取值：
        "know"   认识 → 熟悉度 +1，按艾宾浩斯曲线推下一次。达到阈值则自动斩词。
        "fuzzy"  模糊 → 熟悉度不变，1 天后再复习。
        "forgot" 忘记 → 熟悉度 -1 (不低于 0)，4 小时后立刻打回重练。

    返回一个 dict，描述这张卡片调度后的新状态，方便 UI 提示。
    """
    if feedback not in {"know", "fuzzy", "forgot"}:
        raise ValueError(f"未知反馈类型: {feedback}")

    now = datetime.now()
    with SessionLocal() as session:
        card = session.get(Flashcard, card_id)
        if not card:
            return {"ok": False, "reason": "card_not_found"}

        if feedback == "know":
            card.retention_score = (card.retention_score or 0) + 1
            card.next_review_date = now + _interval_for_score(card.retention_score)
            if card.retention_score >= MASTERY_THRESHOLD:
                card.is_mastered = True

        elif feedback == "fuzzy":
            # 不动 retention_score，仅推迟到明天
            card.next_review_date = now + timedelta(days=1)

        else:  # forgot
            card.retention_score = max(0, (card.retention_score or 0) - 1)
            card.next_review_date = now + timedelta(hours=4)

        session.commit()

        return {
            "ok": True,
            "word": card.word,
            "retention_score": card.retention_score,
            "next_review_date": card.next_review_date,
            "is_mastered": card.is_mastered,
        }


def get_all_flashcards() -> List[ReviewCard]:
    """返回所有闪卡（按创建时间升序），用于词库查看界面。"""
    results: List[ReviewCard] = []
    with SessionLocal() as session:
        rows = (
            session.query(Flashcard)
            .order_by(Flashcard.created_at.asc())
            .all()
        )
        for row in rows:
            cw_list = [
                ConfusingWordInfo(
                    word=cw.word or "",
                    meaning=cw.meaning or "",
                    distinction=cw.distinction or "",
                )
                for cw in row.confusing_words
            ]
            results.append(
                ReviewCard(
                    id=row.id,
                    word=row.word or "",
                    phonetic=row.phonetic or "",
                    translation=row.translation or "",
                    example=row.example or "",
                    synonyms=row.synonyms or "",
                    retention_score=row.retention_score or 0,
                    confusing_words=cw_list,
                )
            )
    return results


def count_due_flashcards() -> int:
    """统计当前到期未掌握的闪卡数量，用于在 RSS 主页给个小提醒。"""
    now = datetime.now()
    with SessionLocal() as session:
        return (
            session.query(Flashcard)
            .filter(Flashcard.is_mastered == False)  # noqa: E712
            .filter(Flashcard.next_review_date <= now)
            .count()
        )


if __name__ == "__main__":
    # 简单的自检
    due = get_due_flashcards()
    print(f"📚 今日到期卡片数: {len(due)}")
    for c in due[:5]:
        print(f"  - {c.word} (score={c.retention_score}, next={c.next_review_date})")
