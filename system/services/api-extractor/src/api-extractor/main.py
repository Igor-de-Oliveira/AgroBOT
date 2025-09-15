from fastapi import FastAPI, UploadFile, File
import uvicorn
import os
import pandas as pd
import json
from datetime import time

app = FastAPI()

def process_ods_to_json_by_interval(file_path, output_dir):
    try:
        # Lê todas as planilhas do arquivo .ods
        sheets = pd.read_excel(file_path, sheet_name=None, engine="odf")

        for sheet_name, data in sheets.items():
            # Remover linhas e colunas completamente vazias
            data = data.dropna(how='all').dropna(axis=1, how='all')

            # Preencher NaN com valores padrão, se necessário
            data = data.fillna("")

            # Garantir que a coluna de data esteja no formato datetime
            data.columns = data.columns.str.lower()  # Convert columns to lowercase
            if 'data' in data.columns and 'hora' in data.columns:
                data['data'] = pd.to_datetime(data['data'], errors='coerce').dt.date
                data['hora'] = pd.to_datetime(data['hora'], format='%H:%M:%S', errors='coerce').dt.time

                # Criar uma coluna para identificar os intervalos de 12 horas
                def classify_interval(row):
                    if pd.isna(row['hora']):
                        return None
                    hora = row['hora']
                    if time(8, 0) <= hora < time(20, 0):
                        return f"{row['data']} 08:00-20:00"
                    else:
                        # Para o intervalo das 20:00 às 08:00, associar ao dia seguinte
                        next_date = row['data'] if hora < time(8, 0) else row['data'] + pd.Timedelta(days=1)
                        return f"{next_date} 20:00-08:00"

                data['intervalo'] = data.apply(classify_interval, axis=1)

                # Filtrar dados por cada intervalo único
                unique_intervals = data['intervalo'].dropna().unique()

                for interval in unique_intervals:
                    interval_data = data[data['intervalo'] == interval]
                    interval_data_dict = interval_data.drop(columns=['intervalo']).to_dict(orient="records")

                    # Convert date and time objects to strings
                    for record in interval_data_dict:
                        record['data'] = record['data'].strftime('%Y-%m-%d')
                        if 'hora' in record and isinstance(record['hora'], time):
                            record['hora'] = record['hora'].strftime('%H:%M:%S')

                    # Gerar nome do arquivo JSON para o intervalo
                    interval_str = interval.replace(":", "-").replace(" ", "_")
                    output_file = f"{output_dir}/{sheet_name}_{interval_str}.json"

                    # Certificar-se de que o diretório de saída existe
                    os.makedirs(output_dir, exist_ok=True)

                    # Salvar os dados do intervalo como JSON
                    with open(output_file, "w", encoding="utf-8") as json_file:
                        json.dump(interval_data_dict, json_file, ensure_ascii=False, indent=4)
            else:
                print(f"A planilha '{sheet_name}' não contém as colunas 'data' e 'hora'.")

        print(f"Dados processados e salvos no diretório: {output_dir}")
    except Exception as e:
        print(f"Erro ao processar o arquivo: {e}")

@app.post("/process_ods")
def process_ods(
    file: UploadFile = File(None)
    ):
    """
    Endpoint para processar um arquivo ODS e salvar os dados em JSON por intervalo.

    :param file_path: Caminho para o arquivo ODS.
    :param output_dir: Diretório de saída para os arquivos JSON.
    """

    file_path = file
    output_dir = f"./system/services/api-extractor/arquivos-testes/output"

    process_ods_to_json_by_interval(file_path, output_dir)
    return {"message": "Processamento concluído."}

def main():
    """Inicia a API utilizando Uvicorn."""
    uvicorn.run(app, host="0.0.0.0", port=8001)

if __name__ == "__main__":
    main()