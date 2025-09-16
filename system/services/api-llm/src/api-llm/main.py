from fastapi import FastAPI, UploadFile, File
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Qdrant
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


@app.get("/chat")
def chat(string: str):
    """
    Endpoint para interagir com o modelo de linguagem.

    :param string: Texto de entrada para o modelo.
    :return: Resposta do modelo.
    """
    try:
        query = string
        # Certifique-se de que o Qdrant foi inicializado
        if 'qdrant' not in globals():
            return {"error": "Qdrant não foi inicializado. Certifique-se de processar o dataset primeiro."}

        prompt = generate_custom_prompt(qdrant, query)
        chat = ChatOpenAI(
            model=Config.MODEL_NAME,
            temperature=Config.TEMPERATURE,
            openai_api_key=Config.API_KEY
        )
        message = [HumanMessage(content=prompt)]
        response = chat(message)

        print(response.content)

        # Ensure retrieved_contexts is always included
        retrieved_contexts = [doc.page_content for doc in qdrant.similarity_search(query, k=5)]

        interactions.append({
            "question": query,
            "answer": response.content,
            "retrieved_contexts": retrieved_contexts,  # Ensure this key is always present
            "contexts": retrieved_contexts  # Keep contexts for compatibility
        })

        return {"response": response.content}
    except Exception as e:
        return {"error": str(e)}



def main():
    """Inicia a API utilizando Uvicorn."""
    uvicorn.run(app, host="0.0.0.0", port=8002)

if __name__ == "__main__":
    main()