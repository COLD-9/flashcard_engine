from src.db_models import SessionLocal, Flashcard, ConfusingWord, SyllabusWord


def load_syllabus_words() -> set[str]:
    """读取大纲词库，返回小写化的单词集合。表为空时返回空集合。"""
    with SessionLocal() as session:
        rows = session.query(SyllabusWord.word).all()
    return {row[0].lower() for row in rows if row[0]}


def save_flashcard_to_db(card_data: dict):
    """接收字典数据，执行查重和入库操作"""
    word_text = card_data.get("word", "").lower()
    if not word_text:
        print("数据无效")
        return False

    # 将传入字典分解
    translation = card_data.get("translation", "")
    phonetic = card_data.get("phonetic", "")
    example = card_data.get("example", "")
    synonyms_list = card_data.get("synonyms", [])
    synonyms_str = ", ".join(synonyms_list) if isinstance(synonyms_list, list) else ""
   

    confusing_words_data = card_data.get("confusing_words", [])

    # 开启数据库工作台
    with SessionLocal() as session:
        try:
            # 去数据库主表查一下，这个词是不是已经存在了？
            existing_card = session.query(Flashcard).filter_by(word=word_text).first()
            if existing_card:
                print(f"发现老词 '{word_text}'，正在更新最新例句和熟悉度...")
                existing_card.example = example
                existing_card.retention_score += 1
                session.commit()
                return True
            else:
                print(f"发现新词 '{word_text}'，正在装配入库...")
                # 1. 制造主干
                new_card = Flashcard(
                    word=word_text,
                    phonetic=phonetic,
                    translation=translation,
                    example=example,
                    synonyms=synonyms_str
                )

                # 2. 制造树枝并挂载
                for cw_data in confusing_words_data:
                    new_cw = ConfusingWord(
                        word=cw_data.get("word", ""),
                        meaning=cw_data.get("meaning", ""),
                        distinction=cw_data.get("distinction", "")
                    )
                    new_card.confusing_words.append(new_cw) # 魔法绑定

                # 3. 放入工作台并提交
                session.add(new_card)
                session.commit()
                print("完美入库！")
                return True
        except Exception as e:
            # 如果中间发生任何报错（如断电、字段超长），立刻清空工作台
            session.rollback()
            print(f"入库彻底失败: {e}")
            return False


if __name__ == "__main__":
    # 模拟大模型传回来的完美 JSON 字典
    mock_data = {
        "word": "ubiquitous",
        "phonetic": "[juːˈbɪkwɪtəs]",
        "translation": "无所不在的",
        "example": "Smartphones have become ubiquitous in our daily lives.",
        "synonyms": ["omnipresent", "universal"],
        "confusing_words": [
            {
                "word": "unique",
                "meaning": "独一无二的",
                "distinction": "ubiquitous是到处都有，unique是只有一个",
            }
        ],
    }

    print("🚀 开始模拟数据入库测试...")
    save_flashcard_to_db(mock_data)

    # 我们可以再调一次，测试“防重与更新”机制
    print("\n🚀 再次调用，测试老词更新机制...")
    save_flashcard_to_db(mock_data)
