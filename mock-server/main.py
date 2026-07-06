# mock-server/main.py
from fastapi import FastAPI
import time

app = FastAPI(title="Kaggle GPU Mock Serving")

@app.post("/embed")
def embed(data: dict):
    texts = data.get("texts", [])
    # Return 384-dimensional embeddings (SentenceTransformer bge-small-en-v1.5 vector size)
    embeddings = [[0.1] * 384 for _ in texts]
    return {"embeddings": embeddings}

@app.post("/v1/chat/completions")
def chat_completions(data: dict):
    return {
        "choices": [
            {
                "message": {
                    "content": "This is a mock response from the platform engineering team. We are live on local!"
                }
            }
        ],
        "model": "Qwen/Qwen2.5-7B-Instruct-GPTQ-Int4"
    }

@app.get("/health")
def health():
    return {"status": "ok"}
