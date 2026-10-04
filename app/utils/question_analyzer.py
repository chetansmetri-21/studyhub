import re
from difflib import SequenceMatcher
from collections import Counter, defaultdict


# ============================================================
# STOP WORDS
# ============================================================

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "if", "then",
    "is", "are", "was", "were", "be", "been", "being",
    "to", "of", "in", "on", "for", "from", "with", "by",
    "at", "as", "into", "through", "during", "about",
    "between", "after", "before", "above", "below",
    "up", "down", "out", "off", "over", "under",
    "again", "further", "once", "than", "that", "this",
    "these", "those", "what", "which", "who", "whom",
    "whose", "why", "how", "when", "where",

    "explain", "describe", "discuss", "write", "state",
    "define", "give", "mention", "list", "briefly",
    "following", "question", "questions",
    "answer", "answers", "marks", "mark"
}


# ============================================================
# WORD NORMALIZATION
# ============================================================

def normalize_word(word):

    word = word.lower().strip()

    if len(word) > 5 and word.endswith("ies"):
        word = word[:-3] + "y"

    elif len(word) > 5 and word.endswith("ing"):
        word = word[:-3]

    elif len(word) > 5 and word.endswith("ed"):
        word = word[:-2]

    elif len(word) > 5 and word.endswith("es"):
        word = word[:-2]

    elif len(word) > 4 and word.endswith("s"):
        word = word[:-1]

    return word


# ============================================================
# QUESTION NORMALIZATION
# ============================================================

def normalize_question(question):

    if not question:
        return ""

    text = str(question).lower()

    text = re.sub(
        r"\bq(?:uestion)?\s*\d+\s*[\.\):-]?",
        " ",
        text
    )

    text = re.sub(
        r"\b[a-h]\s*[\.\):-]",
        " ",
        text
    )

    text = re.sub(
        r"\b\d+\s*marks?\b",
        " ",
        text
    )

    noise_patterns = [

        r"\bmodule\s*\d+\b",
        r"\bunit\s*\d+\b",
        r"\bco\d+\b",
        r"\blo\d+\b",
        r"\bpart\s*[a-z0-9]+\b",
        r"\bsection\s*[a-z0-9]+\b",
        r"\bpage\s*\d+\b",
        r"\bfig(?:ure)?\.?\s*\d+\b"

    ]

    for pattern in noise_patterns:
        text = re.sub(
            pattern,
            " ",
            text
        )

    text = re.sub(
        r"[^a-z0-9\s]",
        " ",
        text
    )

    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    return text


# ============================================================
# KEYWORDS
# ============================================================

def extract_keywords(question):

    normalized = normalize_question(question)

    words = normalized.split()

    keywords = []

    for word in words:

        if len(word) < 3:
            continue

        if word in STOP_WORDS:
            continue

        normalized_word = normalize_word(word)

        if len(normalized_word) < 3:
            continue

        keywords.append(
            normalized_word
        )

    return keywords


def keyword_set(question):

    return set(
        extract_keywords(question)
    )


# ============================================================
# N-GRAMS
# ============================================================

def make_ngrams(words, n=2):

    if len(words) < n:
        return set()

    return {
        " ".join(
            words[i:i + n]
        )
        for i in range(
            len(words) - n + 1
        )
    }


# ============================================================
# QUESTION SIMILARITY
# ============================================================

def question_similarity(
    question1,
    question2
):

    if not question1 or not question2:
        return 0.0

    normalized1 = normalize_question(
        question1
    )

    normalized2 = normalize_question(
        question2
    )

    if not normalized1 or not normalized2:
        return 0.0

    if normalized1 == normalized2:
        return 1.0

    words1 = extract_keywords(
        question1
    )

    words2 = extract_keywords(
        question2
    )

    if not words1 or not words2:
        return 0.0

    set1 = set(words1)
    set2 = set(words2)

    intersection = (
        set1.intersection(set2)
    )

    union = (
        set1.union(set2)
    )

    if not union:
        return 0.0

    jaccard = (
        len(intersection)
        / len(union)
    )

    overlap1 = (
        len(intersection)
        / len(set1)
    )

    overlap2 = (
        len(intersection)
        / len(set2)
    )

    overlap = max(
        overlap1,
        overlap2
    )

    sequence_similarity = (
        SequenceMatcher(
            None,
            normalized1,
            normalized2
        ).ratio()
    )

    bigrams1 = make_ngrams(
        words1,
        2
    )

    bigrams2 = make_ngrams(
        words2,
        2
    )

    if bigrams1 and bigrams2:

        bigram_union = (
            bigrams1.union(
                bigrams2
            )
        )

        bigram_intersection = (
            bigrams1.intersection(
                bigrams2
            )
        )

        bigram_similarity = (
            len(
                bigram_intersection
            )
            / len(
                bigram_union
            )
        )

    else:

        bigram_similarity = 0.0

    score = (

        (jaccard * 0.35)

        + (overlap * 0.25)

        + (
            sequence_similarity
            * 0.25
        )

        + (
            bigram_similarity
            * 0.15
        )
    )

    if len(intersection) >= 2:

        score = max(
            score,
            0.48
            + (
                min(
                    len(intersection),
                    6
                ) * 0.05
            )
        )

    if len(intersection) >= 3:
        score = max(
            score,
            0.65
        )

    if len(intersection) >= 4:
        score = max(
            score,
            0.72
        )

    return round(
        min(
            score,
            1.0
        ),
        3
    )


# ============================================================
# OPTIMIZED GROUPING
# ============================================================

def group_similar_questions(
    questions,
    threshold=0.45
):

    if not questions:
        return []

    cleaned_questions = []

    for question in questions:

        if not question:
            continue

        question = str(
            question
        ).strip()

        if len(question) < 10:
            continue

        cleaned_questions.append(
            question
        )

    if not cleaned_questions:
        return []

    total = len(
        cleaned_questions
    )

    # --------------------------------------------------------
    # Pre-calculate normalized keywords
    # --------------------------------------------------------

    keyword_sets = []

    for question in cleaned_questions:

        keyword_sets.append(
            keyword_set(
                question
            )
        )

    # --------------------------------------------------------
    # Union-Find
    # --------------------------------------------------------

    parent = list(
        range(total)
    )

    def find(x):

        while parent[x] != x:

            parent[x] = parent[
                parent[x]
            ]

            x = parent[x]

        return x

    def union(x, y):

        root_x = find(x)
        root_y = find(y)

        if root_x != root_y:

            parent[root_y] = root_x

    # --------------------------------------------------------
    # Candidate buckets
    #
    # Instead of comparing every question with every other
    # question, only compare questions sharing keywords.
    # --------------------------------------------------------

    keyword_index = defaultdict(
        set
    )

    for index, keywords in enumerate(
        keyword_sets
    ):

        for keyword in keywords:

            keyword_index[
                keyword
            ].add(index)

    candidate_pairs = set()

    for indexes in keyword_index.values():

        indexes = list(
            indexes
        )

        # Extremely common words should not create thousands
        # of unnecessary comparisons.
        if len(indexes) > 150:
            continue

        for position in range(
            len(indexes)
        ):

            for next_position in range(
                position + 1,
                len(indexes)
            ):

                a = indexes[
                    position
                ]

                b = indexes[
                    next_position
                ]

                if a == b:
                    continue

                if a > b:
                    a, b = b, a

                candidate_pairs.add(
                    (
                        a,
                        b
                    )
                )

    # --------------------------------------------------------
    # Compare only candidates
    # --------------------------------------------------------

    for i, j in candidate_pairs:

        set1 = keyword_sets[i]
        set2 = keyword_sets[j]

        if not set1 or not set2:
            continue

        shared_keywords = (
            set1.intersection(
                set2
            )
        )

        # Two shared keywords are generally enough to make
        # the expensive similarity calculation worthwhile.
        if len(shared_keywords) < 2:
            continue

        score = question_similarity(
            cleaned_questions[i],
            cleaned_questions[j]
        )

        if score >= threshold:

            union(
                i,
                j
            )

    # --------------------------------------------------------
    # Build groups
    # --------------------------------------------------------

    groups = {}

    for index, question in enumerate(
        cleaned_questions
    ):

        root = find(
            index
        )

        groups.setdefault(
            root,
            []
        ).append(
            question
        )

    return list(
        groups.values()
    )


# ============================================================
# TOPIC KEYWORDS
# ============================================================

TOPIC_KEYWORDS = {

    "Probability": {
        "probability",
        "random",
        "event",
        "distribution",
        "bayes"
    },

    "Statistics": {
        "statistics",
        "mean",
        "median",
        "mode",
        "variance",
        "standard",
        "deviation",
        "correlation",
        "regression"
    },

    "Matrices": {
        "matrix",
        "matrices",
        "determinant",
        "eigenvalue",
        "eigenvector"
    },

    "Calculus": {
        "derivative",
        "differentiation",
        "integral",
        "integration",
        "limit",
        "continuity",
        "differentiable"
    },

    "Vectors": {
        "vector",
        "scalar",
        "magnitude",
        "direction",
        "dot",
        "cross"
    },

    "Optics": {
        "optics",
        "lens",
        "mirror",
        "refraction",
        "reflection",
        "interference",
        "diffraction",
        "polarization"
    },

    "Electromagnetism": {
        "electric",
        "electricity",
        "magnetic",
        "magnetism",
        "field",
        "potential",
        "current",
        "charge",
        "capacitor"
    },

    "Modern Physics": {
        "quantum",
        "photoelectric",
        "photon",
        "nuclear",
        "atom",
        "atomic",
        "radioactivity",
        "debroglie",
        "bohr"
    },

    "Semiconductors": {
        "semiconductor",
        "diode",
        "transistor",
        "junction",
        "rectifier",
        "logic"
    },

    "Organic Chemistry": {
        "organic",
        "alkane",
        "alkene",
        "alkyne",
        "alcohol",
        "aldehyde",
        "ketone",
        "amine",
        "benzene",
        "hydrocarbon"
    },

    "Chemical Bonding": {
        "bond",
        "bonding",
        "hybridization",
        "molecular",
        "orbital",
        "ionic",
        "covalent"
    },

    "Thermodynamics": {
        "thermodynamics",
        "enthalpy",
        "entropy",
        "gibbs",
        "heat",
        "energy"
    },

    "Electrochemistry": {
        "electrochemistry",
        "electrode",
        "electrolysis",
        "cell",
        "conductance",
        "oxidation",
        "reduction"
    },

    "Genetics": {
        "genetics",
        "gene",
        "genes",
        "dna",
        "rna",
        "chromosome",
        "inheritance",
        "mendel",
        "mutation"
    },

    "Cell Biology": {
        "cell",
        "mitosis",
        "meiosis",
        "organelle",
        "membrane",
        "cytoplasm",
        "nucleus"
    },

    "Reproduction": {
        "reproduction",
        "fertilization",
        "gamete",
        "embryo",
        "pregnancy",
        "menstrual",
        "pollination"
    },

    "Ecology": {
        "ecology",
        "ecosystem",
        "biodiversity",
        "population",
        "environment",
        "food",
        "chain",
        "conservation"
    },

    "Photosynthesis": {
        "photosynthesis",
        "chlorophyll",
        "light",
        "calvin",
        "carbon",
        "stomata"
    },

    "Respiration": {
        "respiration",
        "glycolysis",
        "krebs",
        "atp",
        "mitochondria",
        "oxidative"
    },

    "Data Structures": {
        "data",
        "structure",
        "array",
        "stack",
        "queue",
        "linked",
        "list",
        "tree",
        "heap"
    },

    "Algorithms": {
        "algorithm",
        "sorting",
        "searching",
        "complexity",
        "recursion",
        "divide",
        "conquer"
    },

    "Database Management": {
        "database",
        "dbms",
        "sql",
        "normalization",
        "transaction",
        "query",
        "relational"
    },

    "Operating Systems": {
        "operating",
        "system",
        "process",
        "deadlock",
        "scheduling",
        "memory",
        "paging",
        "segmentation"
    },

    "Computer Networks": {
        "network",
        "tcp",
        "ip",
        "http",
        "routing",
        "protocol",
        "ethernet",
        "osi"
    },

    "Artificial Intelligence": {
        "artificial",
        "intelligence",
        "machine",
        "learning",
        "neural",
        "classification",
        "regression",
        "clustering"
    },

    "Software Engineering": {
        "software",
        "engineering",
        "agile",
        "waterfall",
        "testing",
        "requirements",
        "design",
        "maintenance"
    }
}


# ============================================================
# TOPIC IDENTIFICATION
# ============================================================

def identify_topic(question):

    keywords = set(
        extract_keywords(
            question
        )
    )

    if not keywords:

        return {
            "name": "General",
            "matched_keywords": []
        }

    best_topic = None
    best_matches = []

    for topic_name, topic_words in (
        TOPIC_KEYWORDS.items()
    ):

        matches = (
            keywords.intersection(
                topic_words
            )
        )

        if len(matches) > len(
            best_matches
        ):

            best_topic = topic_name
            best_matches = list(
                matches
            )

    if best_topic:

        return {
            "name": best_topic,
            "matched_keywords": best_matches
        }

    common_words = [
        word
        for word, count in (
            Counter(
                keywords
            ).most_common(5)
        )
        if count >= 1
    ]

    if common_words:

        topic_name = " / ".join(
            word.title()
            for word in common_words[:3]
        )

        return {
            "name": topic_name,
            "matched_keywords": common_words
        }

    return {
        "name": "General",
        "matched_keywords": []
    }


# ============================================================
# GROUP TOPIC
# ============================================================

def get_group_topic(group):

    if not group:

        return {
            "name": "General",
            "matched_keywords": []
        }

    topic_counter = Counter()
    keyword_counter = Counter()

    for question in group:

        topic = identify_topic(
            question
        )

        topic_counter[
            topic["name"]
        ] += 1

        for keyword in topic.get(
            "matched_keywords",
            []
        ):

            keyword_counter[
                keyword
            ] += 1

    if topic_counter:

        best_topic, _ = (
            topic_counter.most_common(
                1
            )[0]
        )

        matched_keywords = [
            word
            for word, _ in (
                keyword_counter.most_common(
                    5
                )
            )
        ]

        return {
            "name": best_topic,
            "matched_keywords": matched_keywords
        }

    return {
        "name": "General",
        "matched_keywords": []
    }