import streamlit as st
import requests
import uuid

API_URL = "http://127.0.0.1:8000/chat"
ADMIN_API_URL = "http://127.0.0.1:8000/add-document"

st.set_page_config(page_title="CSKH Bot Production", page_icon="🤖", layout="wide")

# --- KHU VỰC DÀNH CHO ADMIN (Thanh bên trái) ---
with st.sidebar:
    st.header("🛠️ Admin: Nạp kiến thức")
    st.info("Nhập chính sách mới vào đây, Bot sẽ học được ngay lập tức!")
    
    new_topic = st.text_input("Chủ đề mới:")
    new_context = st.text_area("Nội dung chi tiết:")
    
    if st.button("Đẩy lên Pinecone", type="primary"):
        if new_topic and new_context:
            with st.spinner("Đang biến thành Vector và đưa lên mây..."):
                try:
                    res = requests.post(ADMIN_API_URL, json={"topic": new_topic, "context": new_context})
                    if res.status_code == 200:
                        st.success("Tải lên thành công! Bot đã học xong.")
                    else:
                        st.error("Lỗi khi tải lên Server.")
                except Exception as e:
                    st.error("Không kết nối được Server.")
        else:
            st.warning("Vui lòng nhập đủ Chủ đề và Nội dung!")
# ----------------------------------------------

# --- KHU VỰC CHAT CỦA KHÁCH HÀNG (Màn hình chính) ---
st.title("🤖 Trợ lý CSKH (Tự động học hỏi)")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.chat_history = []

st.caption(f"Mã phiên làm việc (Session ID): {st.session_state.session_id}")

for msg in st.session_state.chat_history:
    st.chat_message(msg["role"]).write(msg["content"])

if user_input := st.chat_input("Nhập câu hỏi tra cứu..."):
    st.chat_message("user").write(user_input)
    
    payload = {
        "question": user_input,
        "session_id": st.session_state.session_id
    }
    
    with st.spinner("Bot đang suy nghĩ..."):
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                bot_reply = response.json()["answer"]
                st.chat_message("assistant").write(bot_reply)
                
                st.session_state.chat_history.append({"role": "user", "content": user_input})
                st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
            else:
                st.error(f"Lỗi Server: {response.status_code}")
        except Exception as e:
            st.error("Không kết nối được Server")