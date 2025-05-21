import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # .env を読み込む

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# PDFファイルをアップロード
file = client.files.create(
    file=open("Documents/Annual_Report_extracted.pdf", "rb"),
    purpose="user_data",
)

response = client.responses.create(
    model="o4-mini",
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_file",
                    "file_id": file.id,
                },
                {
                    "type": "input_text",
                    "text": "このPDFは英文の財務諸表です。\nこの中から本表にあたるテーブルが含まれているページだけを知りたいです。\n加えて、本表にあたるテーブル全てをMarkdown形式で出力してください。ページをまたがっているものは別々に出力してください。",
                },
            ],
        }
    ],
    reasoning={"effort": "medium"},
)

print(response.output_text)
