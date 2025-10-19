from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_openai import OpenAIEmbeddings
from typing import List, Dict
import glob
import json
import os
import uvicorn


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

def process_json_files(input_directory, output_directory):
    os.makedirs(output_directory, exist_ok=True)

    # Process each JSON file and generate embeddings
    for json_file in glob.glob(f"{input_directory}/*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Combine all records into a single text for embedding
        combined_text = "\n".join(
            " ".join(f"{key}: {value}" for key, value in record.items()) for record in data
        )

        # Generate embeddings
        embedding_result = embeddings.embed_documents([combined_text])  # Use embed_documents for generating embeddings

        # Save embeddings to a new file
        output_file = os.path.join(output_directory, os.path.basename(json_file).replace(".json", "_embeddings.json"))
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(embedding_result, f, ensure_ascii=False, indent=4)

        print(f"Embeddings for file '{json_file}' saved to {output_file}")

@app.post("/process_json")
def process_json():
    """
    Endpoint para processar arquivos JSON e gerar embeddings.

    :param input_directory: Diretório de entrada para os arquivos JSON.
    :param output_directory: Diretório de saída para os arquivos de embeddings.
    """

    input_directory = f"C:/Users/Pessoal/Desktop/tcc/testes/output"
    output_directory = f"C:/Users/Pessoal/Desktop/tcc/testes/output_embeddings"

    process_json_files(input_directory, output_directory)
    return {"message": "Processamento de JSON concluído."}

def main():
    """Inicia a API utilizando Uvicorn."""
    uvicorn.run(app, host="0.0.0.0", port=8002)

if __name__ == "__main__":
    main()