import os
from datetime import time
from pathlib import Path
from typing import Any

import pandas as pd
import uvicorn
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8003"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def process_ods_to_json_by_interval(file_path: str) -> list[dict[str, Any]]:
    generated_artifacts: list[dict[str, Any]] = []
    sheets = pd.read_excel(file_path, sheet_name=None, engine="odf")

    for sheet_name, data in sheets.items():
        data = data.dropna(how="all").dropna(axis=1, how="all")
        data = data.fillna("")

        data.columns = data.columns.str.lower()
        if "data" not in data.columns or "hora" not in data.columns:
            continue

        data["data"] = pd.to_datetime(data["data"], errors="coerce").dt.date
        data["hora"] = pd.to_datetime(data["hora"], format="%H:%M:%S", errors="coerce").dt.time

        def classify_interval(row):
            if pd.isna(row["hora"]):
                return None
            hora = row["hora"]
            if time(8, 0) <= hora < time(20, 0):
                return f"{row['data']} 08:00-20:00"
            next_date = row["data"] if hora < time(8, 0) else row["data"] + pd.Timedelta(days=1)
            return f"{next_date} 20:00-08:00"

        data["intervalo"] = data.apply(classify_interval, axis=1)
        unique_intervals = data["intervalo"].dropna().unique()

        for interval in unique_intervals:
            interval_data = data[data["intervalo"] == interval]
            interval_records = interval_data.drop(columns=["intervalo"]).to_dict(orient="records")

            for record in interval_records:
                if hasattr(record.get("data"), "strftime"):
                    record["data"] = record["data"].strftime("%Y-%m-%d")
                if isinstance(record.get("hora"), time):
                    record["hora"] = record["hora"].strftime("%H:%M:%S")

            interval_str = interval.replace(":", "-").replace(" ", "_")
            artifact_name = f"{sheet_name}_{interval_str}.json"
            generated_artifacts.append(
                {
                    "sheet_name": sheet_name,
                    "interval": interval,
                    "artifact_name": artifact_name,
                    "records": interval_records,
                }
            )

    return generated_artifacts


@app.post("/process_ods")
async def process_ods(file: UploadFile = File(...)):
    temp_path = ""
    try:
        os.makedirs("temp", exist_ok=True)
        safe_filename = Path(file.filename or "arquivo.ods").name
        temp_path = f"temp/{safe_filename}"

        with open(temp_path, "wb") as buffer:
            buffer.write(await file.read())

        artifacts = process_ods_to_json_by_interval(temp_path)
        return {
            "message": "Processamento concluido com sucesso.",
            "source_file": safe_filename,
            "artifacts_count": len(artifacts),
            "artifacts": artifacts,
        }
    except Exception as exc:
        print("ERRO INTERNO:", exc)
        return {"error": str(exc)}
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def main():
    """Inicia a API utilizando Uvicorn."""
    uvicorn.run(app, host="0.0.0.0", port=8001)


if __name__ == "__main__":
    main()
