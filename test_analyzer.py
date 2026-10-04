from app.utils.pdf_extractor import extract_text_from_pdf
from app.utils.question_analyzer import group_similar_questions
from app.utils.question_parser import parse_questions
import app.utils.question_analyzer


file_path = "uploads/BCS401-JUNE-JULY-2024.pdf"

text = extract_text_from_pdf(file_path)

questions = parse_questions(text)


# ============================================================
# SIMILARITY CHECK
# ============================================================

print("\n========== SIMILARITY CHECK ==========")

for i in range(len(questions)):
    for j in range(i + 1, len(questions)):

        similarity = app.utils.question_analyzer.question_similarity(
            questions[i],
            questions[j]
        )

        if similarity is None:
            print("None found between:")
            print("Q1:", questions[i])
            print("Q2:", questions[j])
            raise SystemExit

print("No None similarity values found.")


# ============================================================
# PYQ ANALYSIS
# ============================================================

groups = app.utils.question_analyzer.group_similar_questions(
    questions,
    threshold=0.50
)

print("\n========== PYQ ANALYSIS ==========")

print(f"\nQuestions extracted: {len(questions)}")
print(f"Question groups: {len(groups)}")


for index, group in enumerate(groups, start=1):

    print(f"\n========== GROUP {index} ==========")

    print(f"Questions in group: {len(group)}")

    for question in group:
        print("-", question)


# ============================================================
# AVL vs 2-3 TREE DEBUG
# ============================================================

print("\n========== AVL vs 2-3 TREE DEBUG ==========")

q1 = questions[8]
q2 = questions[10]

print("AVL keywords:")
print(app.utils.question_analyzer.get_keywords(q1))

print("\n2-3 Tree keywords:")
print(app.utils.question_analyzer.get_keywords(q2))

print("\nSimilarity:")
print(app.utils.question_analyzer.question_similarity(q1, q2))


# ============================================================
# SIMILAR QUESTION TEST
# ============================================================

print("\n========== SIMILAR QUESTION TEST ==========")

test_questions = [
    "Explain asymptotic notations with examples.",
    "Describe asymptotic notations and explain their types with examples.",
    "What are the different asymptotic notations? Explain with suitable examples.",
    "Explain the working of quick sort algorithm.",
    "Develop quick sort algorithm and analyze its best case."
]

test_groups = app.utils.question_analyzer.group_similar_questions(
    test_questions,
    threshold=0.50
)

print("Test groups:", len(test_groups))


for index, group in enumerate(test_groups, start=1):

    print(f"\nGroup {index}:")

    for question in group:
        print("-", question)


# ============================================================
# QUICK SORT DEBUG
# ============================================================

print("\n========== QUICK SORT DEBUG ==========")

q1 = test_questions[3]
q2 = test_questions[4]

print("Quick Sort Q1 keywords:")
print(app.utils.question_analyzer.get_keywords(q1))

print("\nQuick Sort Q2 keywords:")
print(app.utils.question_analyzer.get_keywords(q2))

print("\nSimilarity:")
print(app.utils.question_analyzer.question_similarity(q1, q2))