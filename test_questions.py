from app.utils.pdf_extractor import extract_text_from_pdf
from app.utils.question_parser import parse_questions


file_path = "uploads/BCS401-JUNE-JULY-2024.pdf"

text = extract_text_from_pdf(file_path)

questions = parse_questions(text)

print("========== QUESTIONS FOUND ==========")
print(f"Total questions: {len(questions)}")

for i, question in enumerate(questions, start=1):
    print(f"\nQuestion {i}:")
    print(question)