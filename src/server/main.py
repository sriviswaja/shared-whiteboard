from fastapi import FastAPI

app = FastAPI(title="Shared Whiteboard")


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
