import streamlit as st
import json
import os
import random
from datetime import datetime, timedelta
import requests
import hashlib

# --- 页面配置 ---
st.set_page_config(page_title="日语单词卡", page_icon="🇯🇵", layout="centered")

# --- 百度翻译 API 配置（稍后替换） ---
BAIDU_APP_ID = "MQpV_d92vuh0la8ajim0bge10"        # 稍后替换
BAIDU_SECRET_KEY = "8N5LcJ3fPsSFSEkEHlzm"       # 稍后替换

def get_japanese_example(word):
    """调用百度翻译 API 获取日语单词的中文释义"""
    url = "https://fanyi-api.baidu.com/api/trans/vip/translate"
    salt = str(random.randint(32768, 65536))
    sign_str = BAIDU_APP_ID + word + salt + BAIDU_SECRET_KEY
    sign = hashlib.md5(sign_str.encode()).hexdigest()
    
    params = {
        "q": word,
        "from": "ja",
        "to": "zh",
        "appid": BAIDU_APP_ID,
        "salt": salt,
        "sign": sign
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        result = response.json()
        
        # 打印完整返回结果（调试用）
        print("API返回:", result)
        
        if "trans_result" in result:
            trans = result["trans_result"][0]["dst"]
            return f"📖 {trans}"
        elif "error_code" in result:
            # 百度翻译返回错误码
            error_msg = result.get("error_msg", "未知错误")
            return f"📖 API错误: {error_msg} (错误码: {result.get('error_code')})"
        else:
            return f"📖 未知返回: {result}"
            
    except Exception as e:
        return f"📖 请求失败: {str(e)}"

# --- 数据文件路径 ---
DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {"words": [], "progress": {}}
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
    
    if not words:
        st.warning("⚠️ 词库为空！请先添加单词。")
        return
    
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
            st.session_state.current_index = random.randint(0, len(words)-1)
            st.session_state.show_answer = False
            st.rerun()
    
    word = words[st.session_state.current_index]
    word_key = word["jp"]
    
    card = st.container()
    with card:
        st.markdown(f"""
        <div style="background-color:#f8f9fa; padding:2rem; border-radius:20px; text-align:center; border:1px solid #e9ecef;">
            <h1 style="font-size:4rem; margin-bottom:0.5rem;">{word["jp"]}</h1>
            <p style="font-size:1.5rem; color:#6c757d;">{word["kana"]}</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.session_state.show_answer:
            example = get_japanese_example(word["jp"])
            st.markdown(f"""
            <div style="background-color:#d4edda; padding:1.5rem; border-radius:15px; text-align:center; margin-top:1rem;">
                <h2 style="color:#155724;">{word["zh"]}</h2>
                <p style="color:#155724; margin-top:0.5rem; font-size:1.1rem;">
                    {example}
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

if __name__ == "__main__":
    main()