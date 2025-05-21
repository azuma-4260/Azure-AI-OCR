import base64
import concurrent.futures
import glob
import json
import os

import fitz
from openai import OpenAI
from tqdm import tqdm


def pdf2png(pdf_path, output_dir):
    # PDFファイルを開く
    pdf_document = fitz.open(pdf_path)

    # 各ページをPNGに変換
    for page_number in range(len(pdf_document)):
        page = pdf_document.load_page(page_number)  # ページを読み込む
        pix = page.get_pixmap()  # ページを画像に変換
        # 0埋め3桁にする
        output_path = os.path.join(output_dir, f"page_{page_number + 1:03}.png")
        pix.save(output_path)  # PNGとして保存

    print("変換が完了しました。")


# 画像をエンコードする関数
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def exract_main_statements(
    client: OpenAI, image_folder: str, max_files_to_process: int = 1000
):
    # フォルダ内のすべてのPNGファイルを取得
    image_paths = glob.glob(os.path.join(image_folder, "*.png"))

    # 最大処理数を制限
    image_paths = image_paths[:max_files_to_process]

    def process_image(image_path):
        base64_image = encode_image(image_path)
        prompt = """The attached image is a base-64 encoded PNG created from an English-language PDF financial statement.

        Carry out the steps below, in order, and follow every rule exactly.

        1. Detect every table that represents a MAIN STATEMENT on the page.
        - MAIN STATEMENTS are defined as the primary financial tables, such as balance sheets, income statements, and cash flow statements. These tables typically contain monetary values, column headers, and row labels that are essential for financial analysis.
        - If no such tables exist, return an empty list in the JSON described at step 4 and stop.

        2. For each detected table:

        a. Transcribe the table **verbatim**:
        - keep every column in its original left-to-right order
        - keep every row in its original top-to-bottom order
        - preserve all numbers, punctuation, footnotes, blank cells, and formatting exactly as they appear.

        b. Produce the table in **CSV format**:
        - use a plain comma (`,`) as the separator
        - separate rows with raw line breaks (`\n`)
        - if a cell contains a comma, wrap the cell value in double quotes and escape internal quotes by doubling them (`" → ""`)
        - do not add any column or row that did not exist in the source
        - keep all numeric formatting (commas, brackets, minus signs, currency symbols) exactly as in the source.

        3. If a table spans multiple PDF lines or pages, merge the parts into one continuous table **without changing the original order**.

        4. Return **only** the JSON object below—single line, no comments, no back-ticks:

        {
        "Tables": [
        {
            "TableName": "<table caption translated into Japanese, or an empty string>",
            "TableContent": "<CSV string with \n between rows>",
        },
        ...
        ]
        }

        Absolute rules (failure to obey any of them is an error):

        - Never reorder, add, delete, aggregate, or split any rows or columns.
        - Never alter numeric data in any way.
        - Output nothing except the single JSON object described above.

        Additional guidelines:
        - Pay special attention to tables with monetary values, ensuring no data is missed.
        - If a table contains a mix of monetary and non-monetary data, include the entire table.
        - Use contextual clues such as headers or footnotes to identify MAIN STATEMENTS.
        """
        try:
            response = client.chat.completions.create(
                model="openai.o4-mini-2025-04-16",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    },
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            return None

    # 並列処理を使用して画像を処理
    with concurrent.futures.ThreadPoolExecutor() as executor:
        all_responses = list(
            tqdm(executor.map(process_image, image_paths), total=len(image_paths))
        )

    return [response for response in all_responses if response is not None]


def postprocess_main_statements(client: OpenAI, main_statements: list):
    def process_statement(data):
        prompt_format = """You are given a JSON object produced by a previous step.
        Its structure is:

        {
            "Tables": [
                {
                    "TableName": "<English table caption>",
                    "TableContent": "<CSV string with \\n between rows>"
                },
                ...
            ]
        }

        Tables are MAIN STATEMENT in financial statement.

        Your tasks, applied to **each** table, are:

        1. Translate into Japanese:
        • the value of `TableName` (use the translation as the new table name)
        • every header in the first row of the CSV
        *Do not translate any numeric data, footnotes, or other cell contents, and do not include the English text anywhere in the output.*

        2. Identify every column that does **not** represent monetary amounts
        (e.g., text, dates, ratios, percentages).
        • Collect their Japanese header names in a list.

        3. Replace the original English headers in the CSV with their Japanese translations while keeping the CSV format unchanged otherwise.

        4. Return **only** the JSON object below — single line, no comments, no back-ticks:

        {
            "Tables": [
                {
                    "TableName": "<Japanese table caption, or an empty string>",
                    "TableContent": "<CSV string with \\n between rows — headers now in Japanese>",
                    "NonMonetaryColumns": ["<Japanese column name 1>", "<Japanese column name 2>", ...]
                },
                ...
            ]
        }

        Strict rules:
        - Keep every column and row in its original order.
        - Do not modify any numeric data.
        - Do not add or remove columns, rows, or headers.
        - Output nothing except the single JSON object described above.

        Thae tables you have to process are the below.

        <<MAIN_STATEMENT>>
        """
        prompt = prompt_format.replace("<<MAIN_STATEMENT>>", data)
        try:
            response = client.chat.completions.create(
                model="openai.o4-mini-2025-04-16",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant."},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    },
                ],
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"Error processing statement: {e}")
            return None

    # 並列処理を使用して後処理
    with concurrent.futures.ThreadPoolExecutor() as executor:
        all_responses = list(
            tqdm(
                executor.map(process_statement, main_statements),
                total=len(main_statements),
            )
        )

    return [response for response in all_responses if response is not None]


def main():
    BASE_URL = "aaa"
    API_KEY = "xxx"

    # OpenAIクライアントの設定（適切に設定してください）
    client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

    # PDFファイルと出力ディレクトリのパスを設定
    pdf_path = r"pdf\1_原文.pdf"
    output_dir = r"outputs"
    # pdfからpngにする必要があるか
    convert_png = False
    if convert_png:
        pdf2png(pdf_path, output_dir)

    # 本表を抽出する
    result_main_statements = exract_main_statements(client, output_dir)
    print("表抽出完了！")

    # テーブル名、行列名の翻訳と金額でない列の検出
    post_processed_main_statements = postprocess_main_statements(
        client, result_main_statements
    )
    print("表の後処理完了！")

    assert len(result_main_statements) == len(post_processed_main_statements), (
        "two lists must be the same length"
    )

    # 結果の表示と保存
    result_dir = "results"
    os.makedirs(result_dir, exist_ok=True)
    join = os.path.join
    for i in range(len(post_processed_main_statements)):
        print(
            f"Result for page {i + 1}:\nFirst step:\n{result_main_statements[i]}\nSecond step:\n{post_processed_main_statements[i]}\n"
        )
        result_first_step = json.loads(result_main_statements[i])
        result_second_step = json.loads(post_processed_main_statements[i])

        with open(
            join(result_dir, f"page{i + 1}_first_step.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(result_first_step, f, indent=4, ensure_ascii=False)

        with open(
            join(result_dir, f"page{i + 1}_second_step.json"), "w", encoding="utf-8"
        ) as f:
            json.dump(result_second_step, f, indent=4, ensure_ascii=False)


if __name__ == "__main__":
    main()
