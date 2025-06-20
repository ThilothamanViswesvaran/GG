ximport os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from langchain_community.document_loaders import AsyncHtmlLoader
from langchain_community.document_transformers import Html2TextTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_huggingface import HuggingFaceEndpoint
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_core.prompts import PromptTemplate
from huggingface_hub import login
import asyncio
import nest_asyncio
import uvicorn
from contextlib import asynccontextmanager

# ===== Configuration =====
BASE_URL = "https://www.ruraluniv.ac.in/"
EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
LLM_REPO_ID = "HuggingFaceH4/zephyr-7b-beta"
CACHE_DIR = "./cache"
VECTORSTORE_PATH = os.path.join(CACHE_DIR, "faiss_index")

# Set environment variables
os.environ['USER_AGENT'] = 'UniversityChatbot/1.0 (+https://github.com/yourusername/yourrepo)'
os.environ['HUGGINGFACEHUB_API_TOKEN'] = 'your_api_key'  # Replace with your actual token

# Initialize components
embeddings = None
llm = None
vectorstore = None
qa_chain = None

# Create cache directory if it doesn't exist
os.makedirs(CACHE_DIR, exist_ok=True)

# Security check for vectorstore
if os.path.exists(VECTORSTORE_PATH):
    print(f"Found existing vectorstore at {VECTORSTORE_PATH}")
    print("Auto-loading vectorstore without prompt")
else:
    print("No existing vectorstore found, will create new one")

# Apply nest_asyncio for async operations
nest_asyncio.apply()

# ===== Core Application Code =====
app = FastAPI()

# Updated prompt template with clearer formatting instructions
prompt_template = """
You are a helpful assistant for Rural University. Use the following context to answer the question directly.
Provide a clear, concise answer following these STRICT formatting rules:
- Each point must start with '•' and be on its own line
- There must be exactly one blank line between points
- Keep each point brief (1 sentence maximum)
- Do not let points run into each other
- Never use numbered lists, only bullet points
- Never combine multiple ideas in one bullet point

Context: {context}

Question: {question}

Answer in properly formatted bullet points:
"""
PROMPT = PromptTemplate(
    template=prompt_template, 
    input_variables=["context", "question"]
)


class QuestionRequest(BaseModel):
    question: str

class ScrapeRequest(BaseModel):
    urls: List[str]

def get_all_links(base_url: str) -> List[str]:
    """Get all links to scrape from university website"""
    common_pages = [
        "", "about-us", "academics", "departments", 
        "admissions", "examinations", "research",
        "facilities", "contact-us", "news-events",
    ]
    return [f"{base_url}{page}" for page in common_pages if not page.startswith("http")]

async def scrape_and_process(urls: List[str]) -> FAISS:
    """Scrape and process website content into vector store"""
    print(f"Scraping {len(urls)} URLs...")
    loader = AsyncHtmlLoader(urls)
    docs = await loader.load()
    
    html2text = Html2TextTransformer()
    docs_transformed = html2text.transform_documents(docs)
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=200
    )
    splits = text_splitter.split_documents(docs_transformed)
    
    return FAISS.from_documents(splits, embeddings)

def initialize_retriever(vstore):
    """Initialize the QA retrieval system"""
    retriever = vstore.as_retriever(search_kwargs={"k": 3})
    return RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=retriever,
        chain_type_kwargs={"prompt": PROMPT},
        return_source_documents=True
    )

async def startup_event():
    """Initialize all application components"""
    global embeddings, llm, vectorstore, qa_chain
    try:
        login(token=os.getenv("HUGGINGFACEHUB_API_TOKEN"))
        
        # Initialize embeddings and LLM
        embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        llm = HuggingFaceEndpoint(
    repo_id=LLM_REPO_ID,
    temperature=0.3,  # Lower temperature for more focused answers
    max_new_tokens=512,
    do_sample=True,
    top_k=50,
    top_p=0.9,
    repetition_penalty=1.1  # Helps avoid verbose responses
    )
        
        
        # Load or create vectorstore
        if os.path.exists(VECTORSTORE_PATH):
            vectorstore = FAISS.load_local(
                VECTORSTORE_PATH, 
                embeddings,
                allow_dangerous_deserialization=True
            )
            print("Loaded existing vectorstore from cache")
        else:
            print("Creating new vectorstore...")
            urls = get_all_links(BASE_URL)
            vectorstore = await scrape_and_process(urls)
            vectorstore.save_local(VECTORSTORE_PATH)
            print(f"Saved new vectorstore to {VECTORSTORE_PATH}")
        
        qa_chain = initialize_retriever(vectorstore)
        print("Application startup completed successfully")
        
    except Exception as e:
        print(f"Startup error: {str(e)}")
        raise RuntimeError(f"Failed to initialize: {str(e)}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    await startup_event()
    yield
    # Cleanup code would go here

app = FastAPI(lifespan=lifespan)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ask")
async def ask_question(request: QuestionRequest):
    """Handle user questions with bullet point formatting where:
    - Single points flow as paragraphs
    - New points start on new lines with bullets
    - Preserves original bullet characters"""
    
    if not qa_chain:
        raise HTTPException(
            status_code=503,
            detail="Service initializing. Please try again in 30 seconds."
        )

    try:
        # Input validation
        if not request.question.strip():
            raise HTTPException(status_code=422, detail="Question cannot be empty")
        
        print(f"Processing question: {request.question}")
        result = qa_chain.invoke({
            "query": request.question,
            "max_new_tokens": 500
        })

        # Process the answer for proper bullet point formatting
        answer = result["result"]
        
        # Split into logical points while preserving original bullets
        points = []
        current_point = []
        
        for line in answer.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            # Check if this is a new bullet point
            if line.startswith(('•', '-', '*')):
                if current_point:  # Save previous point
                    points.append(' '.join(current_point))
                    current_point = []
                # Add the bullet point (standardize to •)
                line = '• ' + line[1:].lstrip() if line[0] in '•-*' else '• ' + line
            current_point.append(line)
        
        # Add the last point if exists
        if current_point:
            points.append(' '.join(current_point))
        
        # Format final output with single newlines between points
        formatted_answer = '\n'.join(points)
        
        # Prepare response
        sources = []
        if "source_documents" in result:
            sources = [
                {
                    "source": doc.metadata.get("source", "Unknown"),
                    "content_preview": doc.page_content[:200] + "..."
                }
                for doc in result["source_documents"]
            ]

        return {
            "answer": formatted_answer,
            "sources": sources,
            "status": "success"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error processing question: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred: {str(e)}"
        )        
if __name__ == "__main__":
    uvicorn.run(
        "app:app",  # Use import string format for reload
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",
        timeout_keep_alive=120
    )
