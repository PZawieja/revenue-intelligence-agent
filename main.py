from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from api.portfolio import router as portfolio_router
from api.accounts import router as accounts_router
from api.chat import router as chat_router

app = FastAPI(title="Revenue Intelligence Agent", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(portfolio_router)
app.include_router(accounts_router)
app.include_router(chat_router)


@app.get("/{full_path:path}", response_class=HTMLResponse)
async def spa(request: Request, full_path: str = ""):
    return templates.TemplateResponse("index.html", {"request": request})
