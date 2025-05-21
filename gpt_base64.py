import base64
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()  # .env を読み込む

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# PDFファイルを読み込み、Base64エンコード
pdf_file_path = "Documents/Annual_Report_extracted.pdf"
with open(pdf_file_path, "rb") as f:
    pdf_data = f.read()
pdf_base64 = base64.b64encode(pdf_data).decode("utf-8")

prompt_text = """このPDFは英文の財務諸表です。
この中から本表にあたるテーブルが含まれているページだけを知りたいです。
加えて、本表にあたるテーブル全てをMarkdown形式で出力してください。ページをまたがっているものは別々に出力してください。
"""


response = client.responses.create(
    model="o4-mini",
    input=[
        {
            "role": "user",
            "content": [
                {
                    "type": "input_file",
                    "filename": "draconomicon.pdf",
                    "file_data": f"data:application/pdf;base64,{pdf_base64}",
                },
                {
                    "type": "input_text",
                    "text": prompt_text,
                },
            ],
        },
    ],
    reasoning={"effort": "medium"},
)

print(response.output_text)
