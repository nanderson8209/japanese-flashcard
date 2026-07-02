import streamlit as st
import json
import os
import random
import requests
import hashlib

# --- 页面配置 ---
st.set_page_config(page_title="日语闯关测试", page_icon="🎮", layout="centered")

# --- 百度翻译 API 配置 ---
BAIDU_APP_ID = "20260702002641453"
BAIDU_SECRET_KEY = "8N5LcJ3fPsSFSEkeEHlzm"

def get_japanese_translation(word):
    """调用百度翻译 API 获取日语单词的中文释义（备用）"""
    url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    salt = str(random.randint(32768, 65536))
    sign_str = BAIDU_APP_ID + word + salt + BAIDU_SECRET_KEY
    sign = hashlib.md5(sign_str.encode('utf-8')).hexdigest()
    
    params = {
        "q": word,
        "from": "jp",
        "to": "zh",
        "appid": BAIDU_APP_ID,
        "salt": salt,
        "sign": sign
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        result = response.json()
        if "trans_result" in result:
            return result["trans_result"][0]["dst"]
        else:
            return "翻译失败"
    except:
        return "翻译失败"

# --- 数据文件 ---
DATA_FILE = "words.json"
ERROR_FILE = "errors.json"

def load_words():
    """加载词库"""
    if not os.path.exists(DATA_FILE):
        default_words = [
            {"jp": "友達", "kana": "ともだち", "zh": "朋友"},
            {"jp": "食べる", "kana": "たべる", "zh": "吃"},
            {"jp": "飲む", "kana": "のむ", "zh": "喝"},
            {"jp": "見る", "kana": "みる", "zh": "看"},
            {"jp": "聞く", "kana": "きく", "zh": "听；问"},
            {"jp": "読む", "kana": "よむ", "zh": "读"},
            {"jp": "書く", "kana": "かく", "zh": "写"},
            {"jp": "行く", "kana": "いく", "zh": "去"},
            {"jp": "来る", "kana": "くる", "zh": "来"},
            {"jp": "する", "kana": "する", "zh": "做"},
            {"jp": "ある", "kana": "ある", "zh": "有（物）"},
            {"jp": "いる", "kana": "いる", "zh": "有（人/动）"},
            {"jp": "勉強", "kana": "べんきょう", "zh": "学习"},
            {"jp": "仕事", "kana": "しごと", "zh": "工作"},
            {"jp": "時間", "kana": "じかん", "zh": "时间"}
        ]
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default_words, f, ensure_ascii=False, indent=2)
        return default_words
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_errors():
    """加载错词本"""
    if not os.path.exists(ERROR_FILE):
        return []
    with open(ERROR_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_errors(errors):
    """保存错词本"""
    with open(ERROR_FILE, "w", encoding="utf-8") as f:
        json.dump(errors, f, ensure_ascii=False, indent=2)

def generate_question(words, used_indices):
    """生成一道题目"""
    # 过滤掉已经用过的词（如果词库不够大，允许重复）
    available = [i for i in range(len(words)) if i not in used_indices]
    if not available:
        available = list(range(len(words)))  # 词库用完则重置
    
    correct_idx = random.choice(available)
    correct_word = words[correct_idx]
    
    # 随机决定方向：True=日→中，False=中→日
    direction = random.choice([True, False])
    
    # 生成干扰项
    other_words = [w for i, w in enumerate(words) if i != correct_idx]
    distractors = random.sample(other_words, min(3, len(other_words)))
    
    # 如果干扰项不够，用随机词补全（实际不会发生）
    while len(distractors) < 3:
        distractors.append({"jp": "ダミー", "kana": "だみー", "zh": "占位"})
    
    # 构建选项
    if direction:
        # 日→中：显示日语，选中文
        question_text = f"「{correct_word['jp']}」是什么意思？"
        correct_answer = correct_word['zh']
        options = [correct_answer] + [d['zh'] for d in distractors[:3]]
    else:
        # 中→日：显示中文，选日语
        question_text = f"「{correct_word['zh']}」的日语是什么？"
        correct_answer = correct_word['jp']
        options = [correct_answer] + [d['jp'] for d in distractors[:3]]
    
    random.shuffle(options)
    
    return {
        "question": question_text,
        "correct": correct_answer,
        "options": options,
        "correct_word": correct_word,
        "direction": direction,
        "correct_idx": correct_idx
    }

def main():
    st.title("🎮 日语闯关测试")
    st.caption("随机出题 · 四选一 · 答错自动收录到错词本")
    
    # 初始化 session_state
    if "words" not in st.session_state:
        st.session_state.words = load_words()
        st.session_state.errors = load_errors()
        st.session_state.score = 0
        st.session_state.total = 0
        st.session_state.used_indices = []
        st.session_state.question = None
        st.session_state.answered = False
        st.session_state.game_over = False
    
    words = st.session_state.words
    errors = st.session_state.errors
    
    # --- 侧边栏：统计 ---
    with st.sidebar:
        st.header("📊 统计")
        col1, col2 = st.columns(2)
        col1.metric("✅ 答对", st.session_state.score)
        col2.metric("📝 总题", st.session_state.total)
        st.metric("❌ 错词本", len(errors))
        
        st.divider()
        if st.button("🔄 重置游戏", use_container_width=True):
            st.session_state.score = 0
            st.session_state.total = 0
            st.session_state.used_indices = []
            st.session_state.question = None
            st.session_state.answered = False
            st.session_state.game_over = False
            st.rerun()
        
        if st.button("📖 查看错词本", use_container_width=True):
            st.session_state.show_errors = not st.session_state.get("show_errors", False)
            st.rerun()
    
    # --- 显示错词本 ---
    if st.session_state.get("show_errors", False):
        st.subheader("❌ 错词本")
        if errors:
            for e in errors:
                st.write(f"**{e['jp']}**（{e['kana']}）→ {e['zh']}")
            if st.button("🗑️ 清空错词本"):
                st.session_state.errors = []
                save_errors([])
                st.rerun()
        else:
            st.info("🎉 错词本是空的，继续加油！")
        st.divider()
    
    # --- 游戏结束 ---
    if st.session_state.game_over:
        st.success(f"🎉 闯关完成！共答 {st.session_state.total} 题，正确 {st.session_state.score} 题")
        if st.button("🔄 再来一局"):
            st.session_state.score = 0
            st.session_state.total = 0
            st.session_state.used_indices = []
            st.session_state.question = None
            st.session_state.answered = False
            st.session_state.game_over = False
            st.rerun()
        return
    
    # --- 生成题目 ---
    if st.session_state.question is None:
        st.session_state.question = generate_question(words, st.session_state.used_indices)
        st.session_state.answered = False
    
    q = st.session_state.question
    
    # --- 显示题目 ---
    st.subheader("📝 " + q["question"])
    
    # 显示四个选项
    cols = st.columns(2)
    for i, option in enumerate(q["options"]):
        with cols[i % 2]:
            if st.button(f"{option}", key=f"opt_{i}", use_container_width=True, disabled=st.session_state.answered):
                st.session_state.total += 1
                if option == q["correct"]:
                    st.session_state.score += 1
                    st.session_state.used_indices.append(q["correct_idx"])
                    st.success("✅ 正确！")
                else:
                    # 记录错词
                    wrong_word = q["correct_word"]
                    if not any(e["jp"] == wrong_word["jp"] for e in errors):
                        errors.append(wrong_word)
                        save_errors(errors)
                        st.session_state.errors = errors
                    st.error(f"❌ 错误！正确答案是：{q['correct']}")
                
                st.session_state.answered = True
                st.rerun()
    
    # --- 下一题按钮 ---
    if st.session_state.answered:
        if st.button("➡️ 下一题", use_container_width=True):
            # 检查是否所有词都出过了
            if len(st.session_state.used_indices) >= len(words):
                st.session_state.game_over = True
            else:
                st.session_state.question = None
                st.session_state.answered = False
            st.rerun()
    
    # --- 进度条 ---
    progress = len(st.session_state.used_indices) / len(words)
    st.progress(progress, text=f"进度：{len(st.session_state.used_indices)}/{len(words)}")

if __name__ == "__main__":
    main()