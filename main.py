from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

load_dotenv()

from api.portfolio import router as portfolio_router  # noqa: E402
from api.accounts import router as accounts_router  # noqa: E402
from api.chat import router as chat_router  # noqa: E402
from api.briefing import router as briefing_router  # noqa: E402
from api.aos import router as aos_router  # noqa: E402

app = FastAPI(title="Revenue Intelligence Agent", docs_url=None, redoc_url=None)

app.mount("/static", StaticFiles(directory="static"), name="static")

app.include_router(portfolio_router)
app.include_router(accounts_router)
app.include_router(chat_router)
app.include_router(briefing_router)
app.include_router(aos_router)

INDEX = Path(__file__).parent / "templates" / "index.html"


@app.get("/{full_path:path}")
async def spa(full_path: str = ""):
    return FileResponse(INDEX, media_type="text/html")
