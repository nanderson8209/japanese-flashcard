import streamlit as st
import json
import os
import random
from datetime import datetime, timedelta

# --- 页面配置 ---
st.set_page_config(page_title="日语单词卡", page_icon="🇯🇵", layout="centered")

# --- 数据文件路径 ---
DATA_FILE = "data.json"

# --- 初始化数据 ---
def load_data():
    """从 data.json 加载数据，如果文件不存在则用默认数据创建"""
    if not os.path.exists(DATA_FILE):
        # 这里提供了一个最简默认数据，实际使用时会用你上面的完整数据
        # 但为了保险，如果文件缺失，会尝试创建并写入默认数据
        default_data = {
            "words": [
                {"jp": "食べる", "kana": "たべる", "zh": "吃"},
                {"jp": "飲む", "kana": "のむ", "zh": "喝"}
            ],
            "progress": {}
        }
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)
        return default_data
    
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    """保存数据到 data.json"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- SM-2 算法辅助函数 ---
def get_next_review(quality, current_interval, ease_factor):
    """
    基于 SM-2 算法计算下次复习间隔
    quality: 0-5 (0: 完全忘记, 5: 完美记住)
    """
    if quality < 2:  # 忘记，重置
        return 1, 1.3  # 1天后复习，难度系数降低
    
    # 更新难度系数 EF
    new_ef = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    if new_ef < 1.3:
        new_ef = 1.3
    
    # 计算新间隔
    if current_interval == 1:
        new_interval = 1
    elif current_interval == 2:
        new_interval = 3
    else:
        new_interval = int(current_interval * new_ef)
    
    return new_interval, new_ef

# --- 主程序 ---
def main():
    st.title("🇯🇵 日语单词卡")
    st.caption("自由翻阅模式 · 数据自动保存")
    
    # 加载数据
    data = load_data()
    words = data["words"]
    progress = data.get("progress", {})
    
    # 初始化 session_state
    if "current_index" not in st.session_state:
        # 优先显示待复习的词（复习间隔已到）
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
    
    # --- 侧边栏：进度统计 ---
    with st.sidebar:
        st.header("📊 学习进度")
        total = len(words)
        learned = len([w for w in progress if progress[w].get("interval", 0) > 5])  # 间隔>5天视为掌握
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
    
    # --- 主界面：单词卡片 ---
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
        
        # 释义区域
        if st.session_state.show_answer:
            st.markdown(f"""
            <div style="background-color:#d4edda; padding:1.5rem; border-radius:15px; text-align:center; margin-top:1rem;">
                <h2 style="color:#155724;">{word["zh"]}</h2>
            </div>
            """, unsafe_allow_html=True)
        else:
            if st.button("💡 显示释义", use_container_width=True):
                st.session_state.show_answer = True
                st.rerun()
        
        # --- 操作按钮 ---
        if st.session_state.show_answer:
            col1, col2, col3 = st.columns(3)
            
            # 忘记
            if col1.button("😵 忘记", use_container_width=True):
                progress[word_key] = {
                    "interval": 1,
                    "ease_factor": 1.3,
                    "next_review": (datetime.now() + timedelta(days=1)).isoformat()
                }
                data["progress"] = progress
                save_data(data)
                st.session_state.current_index = random.randint(0, len(words)-1)
                st.session_state.show_answer = False
                st.rerun()
            
            # 模糊
            if col2.button("🤔 模糊", use_container_width=True):
                p = progress.get(word_key, {"interval": 1, "ease_factor": 1.3})
                interval = p.get("interval", 1)
                ef = p.get("ease_factor", 1.3)
                new_interval, new_ef = get_next_review(3, interval, ef)
                progress[word_key] = {
                    "interval": new_interval,
                    "ease_factor": new_ef,
                    "next_review": (datetime.now() + timedelta(days=new_interval)).isoformat()
                }
                data["progress"] = progress
                save_data(data)
                st.session_state.current_index = random.randint(0, len(words)-1)
                st.session_state.show_answer = False
                st.rerun()
            
            # 记住
            if col3.button("✅ 记住", use_container_width=True):
                p = progress.get(word_key, {"interval": 1, "ease_factor": 1.3})
                interval = p.get("interval", 1)
                ef = p.get("ease_factor", 1.3)
                new_interval, new_ef = get_next_review(5, interval, ef)
                progress[word_key] = {
                    "interval": new_interval,
                    "ease_factor": new_ef,
                    "next_review": (datetime.now() + timedelta(days=new_interval)).isoformat()
                }
                data["progress"] = progress
                save_data(data)
                st.session_state.current_index = random.randint(0, len(words)-1)
                st.session_state.show_answer = False
                st.rerun()
    
    # 显示当前词的位置
    st.caption(f"当前: {st.session_state.current_index + 1} / {len(words)}")

if __name__ == "__main__":
    main()