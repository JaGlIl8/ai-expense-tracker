import os
from dotenv import load_dotenv
from fastapi import FastAPI
from mssql_python import connect
from datetime import date
from pydantic import BaseModel
from fastapi import HTTPException
from openai import OpenAI
from fastapi.responses import FileResponse

load_dotenv()  # reads the .env file
app = FastAPI()

ai = OpenAI(base_url=os.environ["AI_ENDPOINT"], api_key=os.environ["AI_KEY"])

SQL_PROMPT = """你是一個 SQL 助手。資料庫裡有一個資料表：
expenses (id INT, spent_on DATE, category NVARCHAR, amount INT, note NVARCHAR)
category 的值有：food, drinks, transport, fun。
使用者會用中文問問題，你只回傳一段 T-SQL SELECT 查詢，不要任何解釋。"""

def ask_ai(system, user):
    response = ai.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
    )
    return response.choices[0].message.content

def clean_sql(text):
    # 去掉 AI 加的 ```sql 和 ``` 外框
    return text.replace("```sql", "").replace("```", "").strip()

def get_conn():
    return connect(os.environ["SQL_CONNECTION_STRING"])

def get_reader_conn():
    return connect(os.environ["SQL_READER_CONNECTION_STRING"])

@app.get("/")
def home():
    return FileResponse("index.html")

@app.get("/expenses")
def list_expenses():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, spent_on, category, amount, note FROM expenses ORDER BY spent_on DESC"
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {"id": r[0], "spent_on": str(r[1]), "category": r[2], "amount": r[3], "note": r[4]}
        for r in rows
    ]

class NewExpense(BaseModel):
    spent_on: date
    category: str
    amount: int
    note: str = ""

@app.post("/expenses")
def add_expense(expense: NewExpense):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO expenses (spent_on, category, amount, note) VALUES (?, ?, ?, ?)",
        (expense.spent_on, expense.category, expense.amount, expense.note),
    )
    conn.commit()
    conn.close()
    return {"status": "added"}

class Question(BaseModel):
    question: str

@app.post("/ask")
def ask(q: Question):
    # ① AI 寫 SQL
    sql = clean_sql(ask_ai(SQL_PROMPT, q.question))

    # ② 安全檢查：只允許單一個 SELECT
    body = sql.rstrip(";")
    if not body.upper().startswith("SELECT") or ";" in body:
        raise HTTPException(status_code=400, detail=f"拒絕執行：{sql}")

    # ③ 執行
    conn = get_reader_conn()
    cursor = conn.cursor()
    cursor.execute(sql)
    rows = cursor.fetchall()
    conn.close()

    # ④ AI 解釋
    answer = ask_ai(
        "根據資料庫查詢結果，用一句繁體中文回答使用者的問題。",
        f"問題：{q.question}\nSQL：{sql}\n結果：{rows}",
    )
    return {"question": q.question, "sql": sql, "result": str(rows), "answer": answer}