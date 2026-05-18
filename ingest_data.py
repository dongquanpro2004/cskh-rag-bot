import pandas as pd
import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from pinecone import Pinecone

load_dotenv()

def ingest():
    print("1. Đang nạp file Excel...")
    df = pd.read_excel("data/CS_Mock_Data_RAG_Expanded.xlsx")
    
    docs = [
        Document(
            page_content=f"Chủ đề: {row['Chủ đề']}\nNội dung: {row['Ngữ cảnh (Context)']}", 
            metadata={"doc_id": row["Mã tài liệu"]}
        ) for _, row in df.iterrows()
    ]

    print("2. Đang khởi tạo Embeddings...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    print("3. Đang đẩy dữ liệu lên Pinecone...")
    index_name = "cskh-index"
    PineconeVectorStore.from_documents(
        docs, 
        embeddings, 
        index_name=index_name
    )
    print("-> Xong! Dữ liệu đã nằm an toàn trên Pinecone.")

if __name__ == "__main__":
    ingest()