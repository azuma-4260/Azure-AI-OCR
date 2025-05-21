from pathlib import Path

import PyPDF2

# 入力PDFファイルのパスと出力PDFファイルのパスを指定します
documents_path = Path("Documents")  # ドキュメントフォルダのパス
input_pdf_path = documents_path / "Annual_Report.pdf"  # 対象のPDFファイル
# 入力ファイルの名前に "_extracted" を追加した出力ファイルパスを作成
output_pdf_path = input_pdf_path.with_stem(input_pdf_path.stem + "_extracted")

# 抽出するページの範囲を設定します（例：1ページ目〜5ページ目）
# ※ PyPDF2ではページ番号は0からカウントされるため、実際のページ番号から1を引いて調整します。
start_page = 1  # 人間が数えるページ番号（1ページ目）
end_page = 50  # 終了ページ（このページも含む）

# PDFファイルをバイナリ読み込みモードで開きます
with open(input_pdf_path, "rb") as infile:
    # PdfReaderオブジェクトを作成してPDF全体の情報を読み込みます
    reader = PyPDF2.PdfReader(infile)
    writer = PyPDF2.PdfWriter()

    # PDF全体のページ数を取得します
    num_pages = len(reader.pages)

    # ページ番号の範囲が正しいかチェックします
    if start_page < 1 or end_page > num_pages or start_page > end_page:
        raise ValueError(
            f"指定されたページ番号がPDFの範囲外です。PDF全体のページ数: {num_pages}"
        )

    # 指定したページ（開始ページ〜終了ページ）を PdfWriter に追加します
    for page_num in range(start_page - 1, end_page):
        writer.add_page(reader.pages[page_num])

    # 新たなPDFファイルとして保存します
    with open(output_pdf_path, "wb") as outfile:
        writer.write(outfile)

print("PDFの抽出・保存が完了しました。")
