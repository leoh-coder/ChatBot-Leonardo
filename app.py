from typing import Dict, List, Any
import os
import sqlite3
import threading
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory

# Env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
if not GEMINI_API_KEY:
    raise RuntimeError("Defina GEMINI_API_KEY no arquivo .env")

# FastAPI
app = FastAPI(title="ChatBot-Leonardo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SQLite
conn = sqlite3.connect("chat.db", check_same_thread=False)
conn.row_factory = sqlite3.Row
DB_LOCK = threading.Lock()

with DB_LOCK:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS conversations(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS messages(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      conversation_id INTEGER NOT NULL,
      role TEXT CHECK(role IN ('user','assistant')),
      content TEXT NOT NULL,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(conversation_id) REFERENCES conversations(id)
    )""")
    conn.commit()

def db_exec(sql: str, params: tuple = ()) -> sqlite3.Cursor:
    with DB_LOCK:
        cur = conn.execute(sql, params)
        conn.commit()
        return cur

def db_query(sql: str, params: tuple = ()) -> List[sqlite3.Row]:
    with DB_LOCK:
        return conn.execute(sql, params).fetchall()

#Pydantic
class NewConversation(BaseModel):
    title: str

class SendMsg(BaseModel):
    conversation_id: int
    message: str

# LLM + Prompt + Memória
llm = ChatGoogleGenerativeAI(
    model=GEMINI_MODEL,
    google_api_key=GEMINI_API_KEY,
    temperature=0.7,
)

prompt = ChatPromptTemplate.from_messages([
    ("system", "Você é um assistente técnico, educado e direto. Responda em português do Brasil."),
    MessagesPlaceholder("history"),
    ("human", "{human_input}")
])

core_chain = prompt | llm | StrOutputParser()

_HISTORIES: Dict[int, InMemoryChatMessageHistory] = {}

def _get_history(conversation_id: int) -> InMemoryChatMessageHistory:
    if conversation_id not in _HISTORIES:
        _HISTORIES[conversation_id] = InMemoryChatMessageHistory()
    return _HISTORIES[conversation_id]

def hydrate_history_from_db(conversation_id: int, k: int = 20) -> None:
    hist = _get_history(conversation_id)
    if getattr(hist, "messages", None):
        return 
    rows = db_query("""
        SELECT role, content FROM messages
        WHERE conversation_id=? ORDER BY id DESC LIMIT ?
    """, (conversation_id, k))
    for r in reversed(rows):
        if r["role"] == "user":
            hist.add_user_message(r["content"])
        else:
            hist.add_ai_message(r["content"])

def get_chat_chain(conversation_id: int) -> RunnableWithMessageHistory:
    hydrate_history_from_db(conversation_id, k=20)
    return RunnableWithMessageHistory(
        core_chain,
        lambda session_id: _get_history(int(session_id)),
        input_messages_key="human_input",
        history_messages_key="history",
    )

def ensure_conversation(cid: int) -> None:
    if not db_query("SELECT id FROM conversations WHERE id=?", (cid,)):
        raise HTTPException(status_code=404, detail="Conversation not found")

#
@app.get("/ping")
def ping() -> Dict[str, str]:
    return {"status": "ok"}

@app.post("/conversations")
def create_conversation(payload: NewConversation) -> Dict[str, Any]:
    db_exec("INSERT INTO conversations(title) VALUES (?)", (payload.title,))
    new_id = db_query("SELECT last_insert_rowid() AS id")[0]["id"]
    return {"id": new_id, "title": payload.title}

@app.patch("/conversations/{cid}")
def update_conversation_title(cid: int, payload: NewConversation) -> Dict[str, Any]:
    ensure_conversation(cid)
    db_exec("UPDATE conversations SET title=? WHERE id=?", (payload.title, cid))
    return {"id": cid, "title": payload.title, "message": "Título atualizado com sucesso"}

@app.delete("/conversations/{cid}")
def delete_conversation(cid: int) -> Dict[str, str]:
    ensure_conversation(cid)
    try:
        db_exec("DELETE FROM messages WHERE conversation_id=?", (cid,))
        db_exec("DELETE FROM conversations WHERE id=?", (cid,))
        _HISTORIES.pop(cid, None)
        return {"message": f"Conversa {cid} e todas as suas mensagens foram deletadas."}
    except Exception:
        raise HTTPException(status_code=500, detail="Falha ao deletar no banco de dados.")

@app.get("/conversations")
def list_conversations() -> List[Dict[str, Any]]:
    rows = db_query("SELECT id, title, created_at FROM conversations ORDER BY id DESC")
    return [{"id": r["id"], "title": r["title"], "created_at": r["created_at"]} for r in rows]

@app.get("/conversations/{cid}/messages")
def get_messages(cid: int) -> List[Dict[str, str]]:
    ensure_conversation(cid)
    rows = db_query("""
        SELECT role, content, created_at
        FROM messages
        WHERE conversation_id=?
        ORDER BY id
    """, (cid,))
    return [{"role": r["role"], "content": r["content"], "created_at": r["created_at"]} for r in rows]

@app.post("/chat/send")
def chat_send(payload: SendMsg) -> Dict[str, str]:
    ensure_conversation(payload.conversation_id)
    chain = get_chat_chain(payload.conversation_id)

    try:
        reply = chain.invoke(
            {"human_input": payload.message},
            config={"configurable": {"session_id": str(payload.conversation_id)}}
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Falha ao consultar o modelo. Tente novamente.")

    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    db_exec(
        "INSERT INTO messages(conversation_id, role, content, created_at) VALUES (?,?,?,?)",
        (payload.conversation_id, "user", payload.message, now)
    )
    db_exec(
        "INSERT INTO messages(conversation_id, role, content, created_at) VALUES (?,?,?,?)",
        (payload.conversation_id, "assistant", reply, now)
    )
    return {"reply": reply}
