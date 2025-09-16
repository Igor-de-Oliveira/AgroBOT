from fastapi import FastAPI, UploadFile, File
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import uvicorn
import os

app = FastAPI()

class Config:
    load_dotenv()  # Load environment variables from a .env file
    API_KEY = os.getenv("OPENAI_API_KEY")
    MODEL_NAME = "gpt-4o-mini"
    TEMPERATURE = 0.9
    MAX_TOKENS = 1000
    TIMEOUT = 10
    MODEL_EMBEDDING = 'text-embedding-ada-002'
    EMBEDDING_TYPE = os.getenv("EMBEDDING_TYPE", "openai")

if Config.EMBEDDING_TYPE == "openai":
    embeddings = OpenAIEmbeddings(
        model=Config.MODEL_EMBEDDING,
        openai_api_key=Config.API_KEY
        
    )

else:
    raise ValueError(f"Tipo de embedding '{Config.EMBEDDING_TYPE}' não suportado.")






def main():
    """Inicia a API utilizando Uvicorn."""
    uvicorn.run(app, host="0.0.0.0", port=8002)

if __name__ == "__main__":
    main()