import os
from pathlib import Path

import pandas as pd
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

# === Azureの設定 ===
from dotenv import load_dotenv

load_dotenv()  # .env を読み込む

AZURE_ENDPOINT = os.getenv("AZURE_ENDPOINT")
AZURE_KEY = os.getenv("AZURE_KEY")

# === 入力PDFと出力Excel ===
input_pdf_path = Path("Documents/NYSE_ETN_2023_extracted.pdf")
output_excel_path = Path("outputs") / (input_pdf_path.stem + ".xlsx")
os.makedirs(output_excel_path.parent, exist_ok=True)

# === クライアントの初期化 ===
client = DocumentAnalysisClient(
    endpoint=AZURE_ENDPOINT, credential=AzureKeyCredential(AZURE_KEY)
)

# === PDF送信 & 結果取得 ===
with open(input_pdf_path, "rb") as f:
    poller = client.begin_analyze_document("prebuilt-layout", document=f)
    result = poller.result()

# === テーブルごとにDataFrame化 & Excel出力 ===
tables = result.tables

with pd.ExcelWriter(output_excel_path, engine="openpyxl") as writer:
    for idx, table in enumerate(tables):
        max_row = max(cell.row_index for cell in table.cells) + 1
        max_col = max(cell.column_index for cell in table.cells) + 1

        data = [["" for _ in range(max_col)] for _ in range(max_row)]

        for cell in table.cells:
            data[cell.row_index][cell.column_index] = cell.content

        df = pd.DataFrame(data)
        sheet_name = f"Table_{idx + 1}"
        df.to_excel(writer, index=False, sheet_name=sheet_name)

print(f"✅ テーブル抽出が完了し、Excelに保存されました: {output_excel_path}")
