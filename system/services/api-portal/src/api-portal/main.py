from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import uvicorn
import os
from fastapi.staticfiles import StaticFiles

app = FastAPI()

dirname = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(dirname, "templates"))

@app.get("/", response_class=HTMLResponse)
async def tela(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

app.mount("/static", StaticFiles(directory=os.path.join(dirname, "static")), name="static")


@app.get("/arquivos", response_class=HTMLResponse)
async def process_ods(request: Request):
    return templates.TemplateResponse("Arquivos.html", {"request": request})

@app.get("/procesamento_arquivos", response_class=HTMLResponse)
async def processamento_arquivos(request: Request):
    return templates.TemplateResponse("procesamento_arquivos.html", {"request": request})

def main():
    """Inicia a API utilizando Uvicorn."""
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()