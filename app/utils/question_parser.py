import re


# ============================================================
# BASIC TEXT CLEANING
# ============================================================

def clean_question_text(text):
    """
    Light cleanup for question text.

    IMPORTANT:
    This function intentionally avoids aggressive rewriting.
    The question wording should remain as close as possible
    to the original extracted/OCR text.
    """

    if not text:
        return ""

    text = str(text)

    # Remove common OCR separator characters
    text = text.replace("¦", " ")
    text = text.replace("|", " ")

    # Remove obvious page/header artifacts
    text = re.sub(
        r"(?i)\bPage\s*\d+\s*(?:of|/)\s*\d+\b",
        " ",
        text
    )

    # Remove repeated spaces
    text = re.sub(r"[ \t]+", " ", text)

    # Normalize excessive blank lines
    text = re.sub(r"\n\s*\n+", "\n", text)

    return text.strip()


# ============================================================
# SUB-QUESTION SPLITTING
# ============================================================

def split_sub_questions(block):
    """
    Split a question into a/b/c style sub-questions.

    The original wording is preserved as much as possible.
    """

    if not block:
        return []

    block = block.strip()

    pattern = re.compile(
        r"(?is)"
        r"(?:^|\n|\s)"
        r"\(?([a-z])\)?"
        r"\s*[\.:)]\s*"
    )

    matches = list(pattern.finditer(block))

    if not matches:
        return [block]

    questions = []

    for index, match in enumerate(matches):

        start = match.end()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(block)

        content = block[start:end].strip()

        if content:
            questions.append(
                f"{match.group(1).lower()}: {content}"
            )

    return questions


# ============================================================
# QUESTION CLEANUP
# ============================================================

def cleanup_question(question):
    """
    Minimal cleanup only.

    Do NOT remove actual question wording.
    """

    if not question:
        return ""

    question = clean_question_text(question)

    # Remove obvious trailing OCR noise
    question = re.sub(
        r"\s+(?:Fig|Figure)\s*\d+\s*$",
        "",
        question,
        flags=re.IGNORECASE
    )

    # Remove repeated punctuation at the end
    question = re.sub(
        r"[.]{3,}\s*$",
        ".",
        question
    )

    question = re.sub(
        r"\s+([,.;:?)])",
        r"\1",
        question
    )

    question = re.sub(
        r"([(:])\s+",
        r"\1 ",
        question
    )

    question = re.sub(
        r"[ \t]+",
        " ",
        question
    )

    return question.strip()


# ============================================================
# MAIN QUESTION PARSER
# ============================================================

def parse_questions(text):
    """
    Extract questions from extracted PDF/OCR text.

    The parser tries to preserve the actual wording instead
    of aggressively modifying it.

    Returned format remains a list of strings so it remains
    compatible with the existing database.
    """

    if not text:
        return []

    text = str(text)

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # --------------------------------------------------------
    # Find main questions
    # --------------------------------------------------------

    main_pattern = re.compile(
        r"(?im)"
        r"^\s*"
        r"(?:Q\s*\.?\s*|Question\s*)"
        r"(\d{1,2})"
        r"\s*[\.:)]?\s*"
    )

    matches = list(main_pattern.finditer(text))

    if not matches:
        return []

    questions = []

    for index, match in enumerate(matches):

        question_number = match.group(1)

        start = match.end()

        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = len(text)

        block = text[start:end].strip()

        if not block:
            continue

        # ----------------------------------------------------
        # Remove obvious metadata that occurs AFTER the
        # question but does not belong to its wording.
        # ----------------------------------------------------

        block = re.sub(
            r"(?im)"
            r"\n\s*(?:Marks?|CO|Bloom'?s?|Module|Unit)"
            r"\s*[:\-]?\s*.*$",
            "",
            block
        )

        block = cleanup_question(block)

        if len(block) < 5:
            continue

        # ----------------------------------------------------
        # Detect subquestions
        # ----------------------------------------------------

        sub_questions = split_sub_questions(block)

        if len(sub_questions) > 1:

            for sub_question in sub_questions:

                sub_question = cleanup_question(
                    sub_question
                )

                if len(sub_question) < 5:
                    continue

                questions.append(
                    f"Q{question_number}({sub_question[0]}): "
                    f"{sub_question[3:].strip()}"
                )

        else:

            questions.append(
                f"Q{question_number}: {block}"
            )

    return questions


# ============================================================
# DISPLAY QUESTION
# ============================================================

def get_display_question(question):
    """
    Return the question text for displaying to students.

    This deliberately does NOT normalize the wording.
    """

    if not question:
        return ""

    return str(question).strip()


# ============================================================
# ANALYSIS QUESTION
# ============================================================

def get_analysis_question(question):
    """
    Produce a lightweight version for analysis.

    The actual displayed question is NOT modified.
    """

    if not question:
        return ""

    text = str(question)

    # Remove question number only for analysis
    text = re.sub(
        r"(?i)^\s*Q\s*\d+(?:\([a-z]\))?\s*[:.)-]?\s*",
        "",
        text
    )

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()