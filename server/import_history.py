import json
import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

client = MongoClient(os.getenv("MONGODB_URL"))
db     = client[os.getenv("MONGODB_DB", "tumour_detector")]
col    = db["chat_history"]

with open("conversation.json", encoding="utf-8") as f:
    data = json.load(f)

messages = data.get("messages", [])

col.replace_one(
    {"_id": "main"},
    {"_id": "main", "messages": messages},
    upsert=True
)

print(f"Imported {len(messages)} messages into MongoDB.")
