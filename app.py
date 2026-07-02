import streamlit as st
import json
import os
import random
from datetime import datetime, timedelta
import requests
import hashlib

# --- 页面配置 ---
st.set_page_config(page_title="日语单词卡", page_icon="🇯🇵", layout="centered")

# --- 百度翻译 API 配置 ---
BAIDU_APP_ID = "20260702002641453"
BAIDU_SECRET_KEY = "8N5LcJ3fPsSFSEkeEHlzm"

def get_japanese_translation(word):
    """调用百度翻译 API 获取日语单词的中文释义"""
    url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    salt = str(random.randint(32768, 65536))
    sign_str = BAIDU_APP_ID + word + salt + BAIDU_SECRET_KEY
    sign = hashlib.md5(sign_str.encode()).hexdigest()
    
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
        elif "error_code" in result:
            return f"API错误: {result.get('error_msg', '未知错误')}"
        else:
            return "翻译失败，请重试"
    except Exception as e:
        return f"请求失败: {str(e)}"

# --- 数据文件路径 ---
DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "words": [
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
                {"jp": "いる", "kana": "いる", "zh": "有（人/动）"}
            ],
            "progress": {}
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)
        return default_data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_next_review(quality, current_interval, ease_factor):
    if quality < 2:
        return 1, 1.3
    new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if new_ef < 1.3:
        new_ef = 1.3
    if current_interval == 1:
        new_interval = 1
    elif current_interval == 2:
        new_interval = 3
    else:
        new_interval = int(current_interval * new_ef)
    return new_interval, new_ef

def main():
    st.title("🇯🇵 日语单词卡")
    st.caption("自由翻阅模式 · 数据自动保存")
    
    data = load_data()
    words = data["words"]
    progress = data.get("progress", {})
    
    # ==================== 侧边栏 ====================
    with st.sidebar:
        st.header("📊 学习进度")
        total = len(words)
        learned = len([w for w in progress if progress[w].get("interval", 0) > 5])
        due_count = len([w for w in progress if datetime.fromisoformat(progress[w].get("next_review", "2000-01-01")) <= datetime.now()])
        
        col1, col2, col3 = st.columns(3)
        col1.metric("总词数", total)
        col2.metric("已掌握", learned)
        col3.metric("待复习", due_count)
        
        st.divider()
        if st.button("🔄 随机切换", use_container_width=True):
            if words:
                st.session_state.current_index = random.randint(0, len(words)-1)
                st.session_state.show_answer = False
                st.rerun()
    
    # ==================== 功能四：随机挑战 ====================
    with st.sidebar:
        st.divider()
        st.header("🎯 随机挑战")
        if st.button("⚡ 开始挑战", use_container_width=True):
            if len(words) >= 4:
                # 随机选4个词作为选项
                challenge_words = random.sample(words, min(4, len(words)))
                # 随机选一个作为正确答案
                correct = random.choice(challenge_words)
                st.session_state.challenge_active = True
                st.session_state.challenge_words = challenge_words
                st.session_state.challenge_correct = correct
                st.session_state.challenge_answered = False
                st.rerun()
            else:
                st.warning("词库至少需要4个单词才能挑战！")
        
        # 显示挑战状态
        if st.session_state.get("challenge_active", False) and not st.session_state.get("challenge_answered", True):
            st.info("在下方选择正确的中文释义 👇")
    
    # ==================== 主界面 ====================
    if not words:
        st.warning("⚠️ 词库为空！请添加单词。")
        return
    
    # --- 随机挑战逻辑 ---
    if st.session_state.get("challenge_active", False) and not st.session_state.get("challenge_answered", False):
        st.subheader("🎯 请选择正确的中文释义")
        st.caption(f"日语单词：**{st.session_state.challenge_correct['jp']}**（{st.session_state.challenge_correct['kana']}）")
        
        # 打乱选项顺序
        options = st.session_state.challenge_words.copy()
        random.shuffle(options)
        
        cols = st.columns(2)
        for i, opt in enumerate(options):
            with cols[i % 2]:
                if st.button(f"{opt['zh']}", key=f"ch_{i}", use_container_width=True):
                    if opt['jp'] == st.session_state.challenge_correct['jp']:
                        st.balloons()
                        st.success(f"✅ 正确！{opt['jp']} = {opt['zh']}")
                        st.session_state.challenge_answered = True
                    else:
                        st.error(f"❌ 错误！正确答案是：{st.session_state.challenge_correct['zh']}")
                        st.session_state.challenge_answered = True
                    st.rerun()
        
        if st.button("🔄 换一组挑战", use_container_width=True):
            st.session_state.challenge_active = False
            st.session_state.challenge_answered = False
            st.rerun()
        
        # 显示占位，避免与下方卡片冲突
        st.divider()
    
    # --- 正常单词卡片（只在非挑战模式或挑战结束后显示） ---
    if not st.session_state.get("challenge_active", False) or st.session_state.get("challenge_answered", True):
        if "current_index" not in st.session_state:
            due_words = []
            for idx, w in enumerate(words):
                word_key = w["jp"]
                if word_key in progress:
                    p = progress[word_key]
                    next_review = datetime.fromisoformat(p.get("next_review", "2000-01-01"))
                    if next_review <= datetime.now():
                        due_words.append(idx)
            if due_words:
                st.session_state.current_index = random.choice(due_words)
            else:
                st.session_state.current_index = random.randint(0, len(words)-1)
        
        if "show_answer" not in st.session_state:
            st.session_state.show_answer = False
        
        word = words[st.session_state.current_index]
        word_key = word["jp"]
        
        # 卡片容器
        card = st.container()
        with card:
            st.markdown(f"""
            <div style="background-color:#f8f9fa; padding:2rem; border-radius:20px; text-align:center; border:1px solid #e9ecef;">
                <h1 style="font-size:4rem; margin-bottom:0.5rem;">{word["jp"]}</h1>
                <p style="font-size:1.5rem; color:#6c757d;">{word["kana"]}</p>
            </div>
            """, unsafe_allow_html=True)
            
            if st.session_state.show_answer:
                # 调用 API 获取释义
                trans = get_japanese_translation(word["jp"])
                # 如果有内置例句则显示
                example = word.get("example", "")
                example_text = f"📖 {example}" if example else ""
                
                st.markdown(f"""
                <div style="background-color:#d4edda; padding:1.5rem; border-radius:15px; text-align:center; margin-top:1rem;">
                    <h2 style="color:#155724;">{trans}</h2>
                    <p style="color:#155724; margin-top:0.5rem; font-size:1.1rem;">
                        {example_text}
                    </p>
                </div>
                """, unsafe_allow_html=True)
            else:
                if st.button("💡 显示释义", use_container_width=True):
                    st.session_state.show_answer = True
                    st.rerun()
            
            if st.session_state.show_answer:
                col1, col2, col3 = st.columns(3)
                if col1.button("😵 忘记", use_container_width=True):
                    progress[word_key] = {"interval": 1, "ease_factor": 1.3, "next_review": (datetime.now() + timedelta(days=1)).isoformat()}
                    data["progress"] = progress
                    save_data(data)
                    st.session_state.current_index = random.randint(0, len(words)-1)
                    st.session_state.show_answer = False
                    st.rerun()
                if col2.button("🤔 模糊", use_container_width=True):
                    p = progress.get(word_key, {"interval": 1, "ease_factor": 1.3})
                    interval = p.get("interval", 1)
                    ef = p.get("ease_factor", 1.3)
                    new_interval, new_ef = get_next_review(3, interval, ef)
                    progress[word_key] = {"interval": new_interval, "ease_factor": new_ef, "next_review": (datetime.now() + timedelta(days=new_interval)).isoformat()}
                    data["progress"] = progress
                    save_data(data)
                    st.session_state.current_index = random.randint(0, len(words)-1)
                    st.session_state.show_answer = False
                    st.rerun()
                if col3.button("✅ 记住", use_container_width=True):
                    p = progress.get(word_key, {"interval": 1, "ease_factor": 1.3})
                    interval = p.get("interval", 1)
                    ef = p.get("ease_factor", 1.3)
                    new_interval, new_ef = get_next_review(5, interval, ef)
                    progress[word_key] = {"interval": new_interval, "ease_factor": new_ef, "next_review": (datetime.now() + timedelta(days=new_interval)).isoformat()}
                    data["progress"] = progress
                    save_data(data)
                    st.session_state.current_index = random.randint(0, len(words)-1)
                    st.session_state.show_answer = False
                    st.rerun()
        
        st.caption(f"当前: {st.session_state.current_index + 1} / {len(words)}")
    
    # ==================== 功能一：生词查询 ====================
    with st.expander("🔍 查询生词"):
        col1, col2 = st.columns([3, 1])
        with col1:
            query = st.text_input("输入日语单词", placeholder="例：勉強", key="query_input")
        with col2:
            st.write("")
            st.write("")
            if st.button("🔍 查询", use_container_width=True):
                if query.strip():
                    with st.spinner("查询中..."):
                        result = get_japanese_translation(query.strip())
                    st.success(f"📖 {query.strip()} → {result}")
                else:
                    st.warning("请输入要查询的单词")
    
    # ==================== 功能二：添加新词 ====================
    with st.expander("➕ 添加新词"):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_jp = st.text_input("日语", placeholder="例：勉強")
        with col2:
            new_kana = st.text_input("假名", placeholder="例：べんきょう")
        with col3:
            new_zh = st.text_input("中文释义", placeholder="例：学习")
        
        # 可选例句
        new_example = st.text_input("例句（可选）", placeholder="例：毎日日本語を勉強します。")
        
        if st.button("✅ 添加单词", use_container_width=True):
            if new_jp and new_kana and new_zh:
                # 检查是否已存在
                exists = any(w["jp"] == new_jp for w in words)
                if exists:
                    st.error(f"⚠️ 单词「{new_jp}」已存在！")
                else:
                    new_word = {"jp": new_jp, "kana": new_kana, "zh": new_zh}
                    if new_example:
                        new_word["example"] = new_example
                    words.append(new_word)
                    data["words"] = words
                    save_data(data)
                    st.success(f"✅ 已添加：{new_jp}（{new_kana}）→ {new_zh}")
                    st.rerun()
            else:
                st.warning("⚠️ 请填写日语、假名和中文释义！")

if __name__ == "__main__":
    main()