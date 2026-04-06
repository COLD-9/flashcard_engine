import os
from datetime import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


# ==========================================
# 表 1：考研大纲词库表 (SyllabusWord)
# 作用：用于后续爬取文章后，快速做交集过滤
# ==========================================
class SyllabusWord(Base):
    __tablename__ = "syllabus_words"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(
        String(100), unique=True, index=True, nullable=False
    )  # index=True 加速查找
    is_kaoyan = Column(Boolean, default=True)


# ==========================================
# 表 2：闪卡主表 (Flashcard)
# 作用：存储 AI 解析后的完美数据，以及你的复习进度
# ==========================================
class Flashcard(Base):
    __tablename__ = "flashcards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(100), unique=True, index=True, nullable=False)
    phonetic = Column(String(100))
    translation = Column(String(500))
    example = Column(String(1000))
    synonyms = Column(String(500))
    # 🧠 记忆调度核心字段 (艾宾浩斯算法会用到它们)
    created_at = Column(DateTime, default=datetime.now)
    next_review_date = Column(DateTime, default=datetime.now)  # 决定你明天要不要复习它
    retention_score = Column(
        Integer, default=0
    )  # 记忆熟悉度 (0表示新词，数字越大越熟练)
    # 是否已彻底掌握 (斩词标记)。
    is_mastered = Column(Boolean, default=False)

    # 🔗 关联设置
    confusing_words = relationship(
        "ConfusingWord", back_populates="flashcard", cascade="all, delete-orphan"
    )


# ==========================================
# 表 3：易混淆词表 (ConfusingWord)
# 作用：单独存放大模型生成的避坑指南
# ==========================================
class ConfusingWord(Base):
    __tablename__ = "confusing_words"

    id = Column(Integer, primary_key=True, autoincrement=True)
    flashcard_id = Column(
        Integer, ForeignKey("flashcards.id")
    )  # 外键，指向 Flashcard 表的 id
    word = Column(String(100), nullable=False)
    meaning = Column(String(500))
    distinction = Column(String(500))  # 辨析诀窍

    # 反向关联回主表
    flashcard = relationship("Flashcard", back_populates="confusing_words")


# ==========================================
# 数据库引擎与会话初始化
# ==========================================
# 动态获取项目根目录，将数据库文件明确保存在 data 文件夹下
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "data", "flashcards.db")

# echo=False 表示不打印底层 SQL 语句，保持控制台清爽
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)

# SessionLocal 是工厂，我们在其他文件里存取数据时都要向它要一个 session(连接)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """初始化数据库，根据代码中的类自动创建物理表"""
    print("正在连接 SQLite 引擎并创建数据表结构...")
    Base.metadata.create_all(bind=engine)
    print(f"🎉 数据库初始化成功！物理文件位置: {DB_PATH}")


if __name__ == "__main__":
    # 当直接运行这个文件时，执行建库动作
    init_db()
