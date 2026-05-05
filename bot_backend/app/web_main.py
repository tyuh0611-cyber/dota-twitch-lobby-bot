from .db import init_db
from .web import app


@app.on_event('startup')
async def startup() -> None:
    await init_db()
