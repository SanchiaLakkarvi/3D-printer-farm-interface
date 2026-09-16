import asyncio

from fastapi import FastAPI

from .db import Base, engine
from .models import PrintJob
from .rabbitmq import consume_messages

Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.get("/")
def root():
    return {"message": "Printer backend is running"}


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(consume_messages())