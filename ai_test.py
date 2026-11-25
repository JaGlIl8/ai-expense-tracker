import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(base_url=os.environ["AI_ENDPOINT"], api_key=os.environ["AI_KEY"])

SYSTEM_PROMPT = """你是一個 SQL 助手。資料庫裡有一個資料表：
expenses (id INT, spent_on DATE, category NVARCHAR, amount INT, note NVARCHAR)
category 的值有：food, drinks, transport, fun。
使用者會用中文問問題，你只回傳一段 T-SQL 查詢，不要任何解釋。"""

response = client.chat.completions.create(
    model="gpt-4.1-mini",
    messages=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "我這個月在吃的上面花了多少錢？"},
    ],
)

print(response.choices[0].message.content)