from fastapi import FastAPI
import mongoset
import settings

app = FastAPI()


@app.get("/")
async def root():
    db = mongoset.connect(uri=settings.db_uri, db_name=settings.db_name)["queuebot"]
    return db.find(status=True)
