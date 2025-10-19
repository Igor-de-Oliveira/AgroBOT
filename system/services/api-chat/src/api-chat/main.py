from dotenv import load_dotenv
from fastapi import FastAPI
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import HumanMessage
import uvicorn
import os
from typing import List, Dict

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

interactions: List[Dict] = []

def generate_custom_prompt(qdrant, query):
    """
    Generate a custom prompt based on the query and Qdrant results.
    """
    results = qdrant.similarity_search(query, k=5)
    sorce_knowledge = "\n".join([f"{x.page_content}\nMetadata: {x.metadata}" for x in results])
    augment_prompt = f"""
                        "Você é um assistente especializado no monitoramento hidropônico de uma plantação de alface, projetado para apoiar produtores em suas dúvidas sobre o cultivo. "
                        "Seu objetivo é fornecer informações precisas, esclarecer conceitos, sugerir melhorias e oferecer suporte técnico e especializado nas áreas do cultivo hidropônico de alface, incluindo parâmetros como temperatura, umidade, oxigenação, iluminação, irrigação, pH, e condutividade elétrica, com base nos materiais indexados "
                        "com base nos materiais indexados (dados coletados do monitoramento do cultivo, documentos, vídeos, livros, entre outros). "
                        "***Se não houver contexto suficiente para responder, informe que não é possível responder.*** "
                        "***Não invente respostas e nem amplie a resposta para além do contexto fornecido.*** \n"

                        "### Diretrizes de Resposta: \n"
                        "1. **Escopo**: Responda com base no conteúdo indexado. Se a pergunta não estiver relacionada aos temas do cultivo hidropônico de alface (pH, cE, temperatura, umidade, iluminação, etc.), ou não houver informações disponíveis sobre a variável solicitada, informe educadamente que não é possível responder "
                        "ou não houver informações disponíveis, informe educadamente que não é possível responder. \n"
                        "2. **Tom e Estilo**: Utilize linguagem clara e pedagógica, mantendo-se no mesmo idioma da pergunta. \n"
                        "3. **Referências**: Ao responder, ***inclua referências quando possível. Referenciar é uma boa prática esperada do agrônomo***, "
                        "pois o ajuda a rastrear e verificar as fontes de informação. Use referências que "
                        "foram de fato utilizadas na resposta. Elas podem estar no final do conteúdo, no rodapé ou no assunto. \n"
                        "4. Quando solicitado um relatório de uma data específica, apresente as seguintes informações: \n"
                        "Menor, maior e média dos valores registrados. \n"

                        "### informações uteis: \n"
                        "- **Observação**: os dasdos disponibilizados podem não conter todas as variáveis responda apenas com base nas variáveis que você tem acesso \n"
                        "- **Temperatura da solução nutritiva**: idealmente constante em 20 °C.\n"
                        "- **Temperatura ambiente com luz**: entre 25 °C e 28 °C. Sem luz: entre 19 °C e 20 °C.\n"
                        "- **pH da solução nutritiva**: entre 6.0 e 6.2. Tolerável até 5.8 ou 6.3 com perda de produtividade.\n"
                        "- **Condutividade Elétrica (EC)**: entre 1.6 e 1.9 dS/m. Faixa estendida de 1.5 a 2.5 dS/m, sendo 2.2 um valor máximo produtivo.\n"
                        "- **co2 entre 400.0 e 600.0. Tolerável até 580.0 ou 630.0 com perda de produtividade.\n"


                        "### Como Referenciar ###\n"
                        "1. Sempre que puder usar informação `reference` do metadata, use-a. Ela é mais específica e deve ser priorizada.\n"
                        "2. Quando não puder usar informação `reference` do metadata, use as informações disponíveis, extraia as referências no seguinte formato:\n"
                        "  * `Title`: O que aparece antes de `.json.` \n"
                        "  * `ActivityId`: O número imediatamente após `activity_` \n"
                        "  * Para os outros casos, extraia as referências de elementos disponíveis no metadata. \n"


                        "### Contexto: ###\n"
                        "Você tem acesso a um conjunto de dados que contém informações sobre o cultivo hidropônico de alface. "
                        "Esses dados incluem medições de temperatura interna e externa, Co2, pH e condutividade elétrica. "
                        "**Responda com mais embasamento no contexto abaixo**"
                        "{sorce_knowledge}\n\n"
                        "### Pergunta:\n"
                        "{query}\n"
                        "Responda com base nesse contexto, garantindo que sua resposta seja objetiva, fundamentada e alinhada ao propósito de um chatbot para o cultivo. Certifique-se de referenciar adequadamente cada fonte utilizada. Tente responder somente o que foi pergnutado, sem adicionar informações extras. \n\n"
                    """
    return augment_prompt

dataset = "prepare_dataset_from_json(output_dir)"
if dataset is not None:
    qdrant = "load_documents_to_qdrant(dataset, pdf_dir)"

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
    uvicorn.run(app, host="0.0.0.0", port=8003)

if __name__ == "__main__":
    main()