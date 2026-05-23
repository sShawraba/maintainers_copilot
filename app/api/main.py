from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.infra.vault import get_jwt_secret 
from app.api.routers.rag import router as rag_router
from app.api.routers.auth import router as auth_router
from app.api.routers.chat import router as chat_router
from app.api.routers.conversations import router as conversations_router
#from app.api.routers.widget import router as widget_router
from app.api.routers.auth import fastapi_users, auth_backend
from dotenv import load_dotenv

load_dotenv() 

app = FastAPI()

# Enable CORS for widget embedding
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    # Load JWT secret from Vault and store in app state
    secret = get_jwt_secret()
    app.state.JWT_SECRET = secret
    print("JWT secret loaded from Vault")
    print("API server started successfully")

app.include_router(rag_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(conversations_router)
#app.include_router(widget_router)

@app.get("/")
def root():
    return {"message": "Maintainer's Copilot API"}

@app.post("/api/chat")
async def chat(request: dict):
    """
    Simple chat endpoint for widget testing
    """
    try:
        message = request.get("message", "")
        conversation_id = request.get("conversationId", "default")
        
        if not message:
            return {
                "response": "Please provide a message",
                "sources": []
            }
        
        # For now, return a test response
        # In production, this would call your actual chat service
        return {
            "response": f"Test response to: {message}",
            "sources": [
                {
                    "title": "Widget Test",
                    "url": "http://localhost:8000"
                }
            ]
        }
    except Exception as e:
        return {
            "response": f"Error: {str(e)}",
            "sources": []
        }

