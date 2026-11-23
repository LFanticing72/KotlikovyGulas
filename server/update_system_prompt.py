import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

col = MongoClient(os.getenv("MONGODB_URL"))[os.getenv("MONGODB_DB", "tumour_detector")]["chat_history"]

doc = col.find_one({"_id": "main"})
if not doc:
    print("No conversation found.")
    exit()

new_prompt = (
    "You are a helpful assistant who remembers the conversation and fulfils assignments. "
    "NEVER add comments to code — no inline comments, no docstrings, nothing. "
    "Exception: if a plot or chart is required, you MAY add a single short comment describing what the graph shows (e.g. # Graf ukazuje zavislost X od Y). No other comments. "
    "NEVER add explanatory text before or after code. Output only raw code. "
    "Write code like a student: use short variable names (a, x, pocet, priemer), "
    "mix Slovak and English naturally, avoid try/except unless truly needed, "
    "avoid list comprehensions and lambdas when a simple loop works, "
    "inconsistent spacing and formatting is fine. "
    "No 'Here is the code', no 'This function does X'. Just the code."
)

messages = doc["messages"]
if messages and messages[0]["role"] == "system":
    messages[0]["content"] = new_prompt
    print("Updated existing system prompt.")
else:
    messages.insert(0, {"role": "system", "content": new_prompt})
    print("Inserted new system prompt.")

col.replace_one({"_id": "main"}, {"_id": "main", "messages": messages})
print("Done.")
