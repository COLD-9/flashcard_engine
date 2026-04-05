import os
import json
import requests
from dotenv import load_dotenv

# 读取.env文件并获取API_KEY
load_dotenv()
API_KEY = os.getenv("DEEPSEEK_API_KEY")


def generate_flashcard_data(word: str, context_sentence: str = "") -> dict:
    """
    核心业务函数：传入一个单词和语境，返回结构化的闪卡字典。
    """
    # API调用地址url和通行证headers
    url = "https://api.deepseek.com/chat/completions"  
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

    # 提示词工程 (Prompt Engineering)：用极其严苛的指令框定 AI
    system_prompt = """
    你是一个严谨的英语考研词汇专家。
    请严格按照以下 JSON 格式返回单词的解析，绝对不要输出任何 markdown 标记、问候语或其他解释文字：
    {
        "word": "单词本身",
        "phonetic": "音标",
        "translation": "精准的中文释义（请结合提供的语境）",
        "example": "包含该单词的高级英文例句",
        "synonyms": ["近义词1", "近义词2"],
        "confusing_words": [
            {
                "word": "形近词/易混淆词",
                "meaning": "该形近词的中文释义",
                "distinction": "一句话点破它们在拼写或词根上的核心区别与记忆诀窍"
            }
        ]
    }
    """

    # 组装用户真实问题
    user_prompt = f"请解析单词：'{word}'。它出现的语境是：'{context_sentence}'"

    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        # 这是一个高阶技巧：强制告诉模型我们要的结果是 JSON 对象 (DeepSeek/OpenAI 支持)
        "response_format": {"type": "json_object"},
    }

    try:
        # 发送请求若失败抛出异常
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        # 拿到大模型返回的纯文本流
        answer_text = response.json()["choices"][0]["message"]["content"]

        # 反序列化：把 JSON 字符串转换成 Python 可以直接操作的字典
        flashcard_dict = json.loads(answer_text)
        return flashcard_dict

    except Exception as e:
        print(f"❌ 解析单词 '{word}' 时出错: {e}")
        return None


# 本地测试逻辑
if __name__ == "__main__":
    # 我们换一个考研英语中极其经典的易混淆词作为测试
    test_word = "complement"
    test_context = "A fine wine is a perfect complement to the meal."

    print(f"正在为 '{test_word}' 呼叫 AI 生成结构化数据（包含易混淆词）...\n")

    result = generate_flashcard_data(test_word, test_context)

    if result:
        print("🎉 成功获取升级版字典！\n")

        # 优雅地打印易混淆词模块，体验一下未来的终端界面效果
        print("=" * 50)
        print(f"📚 单词: {result['word']} [{result['phonetic']}]")
        print(f"💡 释义: {result['translation']}")
        print("=" * 50)

        if "confusing_words" in result and result["confusing_words"]:
            print("👀 【易混淆词避坑指南】")
            for cw in result["confusing_words"]:
                print(f"   ⚠️ {cw['word']} ({cw['meaning']})")
                print(f"   👉 诀窍: {cw['distinction']}\n")
        print("=" * 50)
