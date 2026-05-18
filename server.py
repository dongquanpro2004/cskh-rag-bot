import os
import uuid # <-- Thêm thư viện này để tạo mã ID tự động
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv
from contextlib import asynccontextmanager

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_groq import ChatGroq
from langchain_mongodb.chat_message_histories import MongoDBChatMessageHistory
from langchain_core.documents import Document # <-- Thêm Document

from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_history_aware_retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

load_dotenv()
if not os.environ.get("MONGO_URI"):
    raise ValueError("Thiếu MONGO_URI trong file .env")

# Khai báo biến toàn cục
rag_chain = None
pinecone_store = None # <-- Thêm biến này để lưu kết nối Pinecone

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_chain, pinecone_store
    print("Đang khởi động Server và kết nối Cloud Databases...")
    
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    pinecone_store = PineconeVectorStore(index_name="cskh-index", embedding=embeddings)
    
    reranker_model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-v2-m3")
    compressor = CrossEncoderReranker(model=reranker_model, top_n=2)
    retriever = ContextualCompressionRetriever(
        base_compressor=compressor, 
        base_retriever=pinecone_store.as_retriever(search_kwargs={"k": 10})
    )

    llm = ChatGroq(model_name="llama-3.3-70b-versatile", temperature=0)

    contextualize_q_prompt = ChatPromptTemplate.from_messages([
        ("system", "Dựa trên lịch sử chat, hãy viết lại câu hỏi mới thành một câu hỏi độc lập. Chỉ viết lại, không trả lời."),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    history_aware_retriever = create_history_aware_retriever(llm, retriever, contextualize_q_prompt)

    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", "Bạn là trợ lý ảo CSKH chuyên nghiệp. CHỈ SỬ DỤNG Context dưới đây để trả lời. Không tự bịa thông tin.\n\nContext:\n{context}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ])
    
    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    
    print("-> Server Production đã sẵn sàng phục vụ!")
    yield

app = FastAPI(title="RAG CSKH Production API", lifespan=lifespan)

class ChatRequest(BaseModel):
    question: str
    session_id: str

# --- API MỚI: Dành cho Admin thêm luật CSKH ---
class DocumentPayload(BaseModel):
    topic: str
    context: str

@app.post("/add-document")
async def add_document(payload: DocumentPayload):
    if not pinecone_store:
        return {"error": "Database chưa sẵn sàng"}

    # Đóng gói kiến thức mới y hệt như cấu trúc lúc đọc Excel
    new_doc = Document(
        page_content=f"Chủ đề: {payload.topic}\nNội dung: {payload.context}",
        metadata={"doc_id": f"CUSTOM_{uuid.uuid4().hex[:8]}"} # Tạo mã tài liệu ngẫu nhiên
    )

    # Đẩy thẳng Vector lên Pinecone (Tính năng Incremental Update)
    pinecone_store.add_documents([new_doc])

    return {"status": "success", "message": "Đã cập nhật kiến thức mới lên Pinecone!"}
# ----------------------------------------------

@app.post("/chat")
async def chat_endpoint(req: ChatRequest):
    chat_history_db = MongoDBChatMessageHistory(
        session_id=req.session_id,
        connection_string=os.environ.get("MONGO_URI"),
        database_name="cskh_bot_db",
        collection_name="chat_histories"
    )

    history_messages = chat_history_db.messages
    
    response = rag_chain.invoke({
        "input": req.question,
        "chat_history": history_messages
    })
    
    chat_history_db.add_user_message(req.question)
    chat_history_db.add_ai_message(response["answer"])
    
    return {"answer": response["answer"]}