from llm import llm
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.prompts import PromptTemplate


def load_and_split_pdfs(pdf_paths):
    all_documents = []
    for path in pdf_paths:
        loader = PyPDFLoader(path)  # Load each PDF
        documents = loader.load()  # Load the PDF
        all_documents.extend(documents)  # Combine all documents
    return all_documents

pdf_paths = ["resources/CSE-Catalog.pdf", "resources/Math-Catalog.pdf"]  # Replace with your PDF file paths
documents = load_and_split_pdfs(pdf_paths)

# Step 2: Split text into manageable chunks
text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
chunks = text_splitter.split_documents(documents)

# Step 3: Generate embeddings for all chunks
embeddings = OpenAIEmbeddings(model="text-embedding-ada-002", openai_api_key=st.secrets["OPENAI_API_KEY"])  # Use OpenAI's embedding model
vector_store = FAISS.from_documents(chunks, embeddings)  # Store embeddings in FAISS

# Step 4: Create a retrieval-based QA tool
retriever = vector_store.as_retriever()

# Create the RetrievalQA chain with the correct parameters
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True,
    chain_type_kwargs={
        "prompt": PromptTemplate.from_template("""Answer the following question based on the provided context:

Context: {context}

Question: {question}

Answer: """)
    }
)

# Define a tool for retrieving answers from the PDF knowledge base
def pdf_qa_tool(query):
    return qa_chain.run(query)