from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.portfolio import router as portfolio_router
from api.accounts import router as accounts_router
from api.chat import router as chat_router

app = FastAPI(title="Revenue Intelligence Agent", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(portfolio_router)
app.include_router(accounts_router)
app.include_router(chat_router)

INDEX = Path(__file__).parent / "templates" / "index.html"


@app.get("/{full_path:path}")
async def spa(full_path: str = ""):
    return FileResponse(INDEX, media_type="text/html")
