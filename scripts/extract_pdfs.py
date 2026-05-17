from pathlib import Path
from pypdf import PdfReader

PDF_DIR = Path("docs/papers")
OUT_DIR = Path("docs/context/extracted")
OUT_DIR.mkdir(parents=True, exist_ok=True)

for pdf_path in PDF_DIR.glob("*.pdf"):
    try:
        reader = PdfReader(str(pdf_path))
        chunks = []
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            chunks.append(f"\n\n===== PAGE {i} =====\n{text}")
        out_path = OUT_DIR / (pdf_path.stem + ".txt")
        out_path.write_text("\n".join(chunks), encoding="utf-8")
        print(f"OK: {pdf_path.name} -> {out_path}")
    except Exception as e:
        print(f"ERROR: {pdf_path.name}: {e}")