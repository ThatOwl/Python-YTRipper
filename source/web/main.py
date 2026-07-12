from __future__ import annotations

from web.api_app import create_app

app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web.main:app", host="127.0.0.1", port=8000, reload=False)
