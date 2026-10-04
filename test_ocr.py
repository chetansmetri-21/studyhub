from app.utils.pdf_extractor import extract_text_from_pdf

file_path = "uploads/BCS401-JUNE-JULY-2024.pdf"

text = extract_text_from_pdf(file_path)

print("========== OCR EXTRACTED TEXT ==========")
print(text[:10000])

print("\n========== CHARACTER COUNT ==========")
print(len(text))
print("\n========== Q9 RAW TEXT ==========")

start = text.find("Q9")

print(text[start:start + 600])