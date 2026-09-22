"""POS-tagged lexicon and a part-of-speech grammar, shared by the composition runs.

Large enough that a grammar-filtered candidate pool usually EXCEEDS the 255-option
Choice ceiling, which is what makes the sharded tournament in beam.py necessary.

Covers two domains so the same lexicon serves closed-domain facts and the
open-ended interview questions: everyday nature, and abstract/technical vocabulary.

Function classes are small and hand-checked, because they are the syntactic help we
are deliberately giving Jev. Content classes are deliberately wide, so that when a
noun is legal Jev is shown every plausible noun and the semantic choice stays real.
"""
from __future__ import annotations

LEX: dict[str, list[str]] = {
    # ---------------------------------------------------------------- function
    "DET": ["the", "a", "an", "its", "their", "this", "that", "these", "some", "each",
            "every", "one", "no", "any", "most", "both", "my", "your"],
    "PRON_SG": ["it", "this", "that", "he", "she", "one", "nothing", "something",
                "everything", "someone"],
    "PRON_PL": ["they", "these", "those", "we", "people", "many"],
    "PRON_OBJ": ["it", "them", "us", "itself", "themselves", "each other"],
    "AUX_SG": ["is", "was", "has", "does", "can", "will", "would", "should", "must",
               "may", "might", "cannot", "isn't", "doesn't"],
    "AUX_PL": ["are", "were", "have", "do", "can", "will", "would", "should", "must",
               "may", "might", "cannot", "aren't", "don't"],
    "PART": ["to"],
    "SUBORD": ["because", "when", "while", "after", "before", "until", "since", "so",
               "although", "unless", "whenever", "if"],
    "CONJ": ["and", "or", "but", "yet", "nor"],
    "PREP": ["in", "on", "into", "inside", "outside", "of", "from", "with", "without",
             "through", "between", "among", "around", "over", "under", "above", "below",
             "at", "for", "by", "during", "against", "toward", "beyond", "within",
             "about", "across", "beside", "onto", "upon"],
    "ADV": ["then", "again", "slowly", "quickly", "first", "later", "soon", "still",
            "only", "also", "away", "back", "up", "down", "more", "less", "often",
            "always", "never", "sometimes", "usually", "rarely", "mostly", "nearly",
            "almost", "already", "instead", "together", "apart", "however", "therefore",
            "simply", "clearly", "largely", "eventually", "gradually", "directly",
            "merely", "truly", "badly", "well", "poorly", "safely", "honestly"],

    # ---------------------------------------------------------------- nouns
    "NOUN_CNT": [
        # nature
        "caterpillar", "butterfly", "cocoon", "shell", "body", "wing", "leaf", "tree",
        "branch", "flower", "bee", "bird", "nest", "egg", "spider", "web", "insect",
        "fish", "gill", "sun", "moon", "star", "planet", "sky", "cloud", "river",
        "lake", "sea", "mountain", "island", "day", "night", "season", "stage", "form",
        "plant", "seed", "root", "stem", "fruit", "nut", "animal", "bone", "feather",
        "scale", "cell", "drop", "flame", "shadow", "circle", "surface", "layer",
        # abstract / technical
        "model", "machine", "computer", "program", "system", "tool", "method", "answer",
        "question", "problem", "reason", "cause", "result", "choice", "decision",
        "judgment", "number", "word", "sentence", "language", "idea", "thought",
        "mind", "brain", "person", "human", "worker", "user", "developer", "company",
        "product", "risk", "danger", "mistake", "error", "failure", "success", "limit",
        "rule", "law", "right", "duty", "value", "price", "cost", "benefit", "loss",
        "life", "death", "future", "past", "moment", "step", "part", "whole", "point",
        "difference", "example", "pattern", "signal", "measure", "test", "process",
        "skill", "task", "job", "role", "goal", "purpose", "belief", "opinion", "view",
        "fact", "truth", "lie", "promise", "threat", "chance", "scale", "world",
    ],
    "NOUN_MASS": [
        "water", "ice", "air", "sunlight", "light", "heat", "cold", "colour", "pollen",
        "honey", "food", "time", "space", "skin", "grass", "shade", "autumn", "winter",
        "summer", "spring", "weather", "wind", "rain", "snow", "smoke", "dust", "energy",
        "matter", "gravity", "growth", "change", "motion", "sound", "silence",
        "intelligence", "reasoning", "meaning", "knowledge", "understanding", "language",
        "speech", "text", "data", "information", "context", "evidence", "probability",
        "confidence", "certainty", "uncertainty", "doubt", "risk", "harm", "good", "evil",
        "justice", "freedom", "power", "money", "work", "labour", "progress", "science",
        "technology", "software", "hardware", "code", "memory", "attention", "judgment",
        "honesty", "trust", "care", "hope", "fear", "pain", "help", "damage", "safety",
    ],
    "NOUN_PL": [
        "caterpillars", "butterflies", "cocoons", "wings", "leaves", "trees", "branches",
        "flowers", "bees", "birds", "nests", "eggs", "spiders", "webs", "insects",
        "gills", "stars", "planets", "clouds", "rivers", "seasons", "days", "nights",
        "plants", "seeds", "roots", "animals", "cells", "colours", "drops", "layers",
        "models", "machines", "computers", "programs", "systems", "tools", "methods",
        "answers", "questions", "problems", "reasons", "causes", "results", "choices",
        "decisions", "judgments", "numbers", "words", "sentences", "languages", "ideas",
        "thoughts", "minds", "people", "humans", "workers", "users", "developers",
        "companies", "products", "risks", "dangers", "mistakes", "errors", "failures",
        "limits", "rules", "laws", "rights", "values", "costs", "benefits", "lives",
        "futures", "moments", "steps", "parts", "points", "differences", "examples",
        "patterns", "signals", "measures", "tests", "processes", "skills", "tasks",
        "jobs", "roles", "goals", "purposes", "beliefs", "opinions", "views", "facts",
        "truths", "lies", "promises", "threats", "chances", "worlds", "things",
    ],

    # ---------------------------------------------------------------- verbs
    "VERB_BASE": [
        "become", "change", "grow", "turn", "make", "form", "eat", "feed", "breathe",
        "melt", "freeze", "scatter", "reflect", "absorb", "carry", "catch", "trap",
        "hold", "keep", "build", "lay", "live", "die", "hide", "rest", "sleep",
        "emerge", "leave", "stop", "start", "spin", "wrap", "cover", "protect", "need",
        "use", "take", "give", "move", "rise", "fall", "break", "open", "close", "lose",
        "find", "know", "think", "believe", "understand", "mean", "say", "tell", "ask",
        "answer", "choose", "decide", "judge", "measure", "count", "compare", "explain",
        "predict", "learn", "teach", "help", "harm", "trust", "doubt", "fail", "succeed",
        "work", "serve", "replace", "improve", "matter", "depend", "differ", "exist",
        "remain", "seem", "appear", "happen", "allow", "prevent", "require", "produce",
        "create", "destroy", "waste", "save", "spend", "cause", "follow", "lead",
        "control", "obey", "refuse", "accept", "pretend", "speak", "write", "read",
    ],
    "VERB_3SG": [
        "becomes", "changes", "grows", "turns", "makes", "forms", "eats", "feeds",
        "breathes", "melts", "freezes", "scatters", "reflects", "absorbs", "carries",
        "catches", "traps", "holds", "keeps", "builds", "lays", "lives", "dies",
        "hides", "rests", "sleeps", "emerges", "leaves", "stops", "starts", "spins",
        "wraps", "covers", "protects", "needs", "uses", "takes", "gives", "moves",
        "rises", "falls", "breaks", "opens", "closes", "loses", "finds", "knows",
        "thinks", "believes", "understands", "means", "says", "tells", "asks",
        "answers", "chooses", "decides", "judges", "measures", "counts", "compares",
        "explains", "predicts", "learns", "teaches", "helps", "harms", "trusts",
        "doubts", "fails", "succeeds", "works", "serves", "replaces", "improves",
        "matters", "depends", "differs", "exists", "remains", "seems", "appears",
        "happens", "allows", "prevents", "requires", "produces", "creates", "destroys",
        "wastes", "saves", "spends", "causes", "follows", "leads", "controls", "obeys",
        "refuses", "accepts", "pretends", "speaks", "writes", "reads",
    ],
    "ADJ": [
        "hard", "soft", "new", "old", "young", "small", "large", "long", "short",
        "bright", "dark", "blue", "green", "white", "black", "red", "yellow", "brown",
        "warm", "cool", "cold", "hot", "wet", "dry", "safe", "ready", "whole",
        "different", "same", "good", "bad", "better", "worse", "best", "worst", "right",
        "wrong", "true", "false", "real", "useful", "useless", "fast", "slow", "simple",
        "complex", "clear", "unclear", "certain", "uncertain", "honest", "dishonest",
        "possible", "impossible", "likely", "unlikely", "easy", "difficult", "important",
        "cheap", "expensive", "narrow", "wide", "deep", "shallow", "strong", "weak",
        "human", "natural", "artificial", "free", "fair", "unfair", "necessary",
        "dangerous", "harmless", "careful", "careless", "common", "rare", "full",
        "empty", "open", "closed", "first", "last", "own", "single", "many", "few",
        "enough", "limited", "unlimited", "calibrated", "reliable", "fragile",
    ],
}

# --------------------------------------------------------------------------- grammar

# See guided.py STRICT_DETERMINERS: gating count nouns behind a determiner is
# grammatically correct and empirically much worse, because Jev has no lookahead
# and will report MISSING rather than step through a function word to reach a noun.
# Content words must stay visible at every step.
_NOUNS = {"NOUN_CNT", "NOUN_MASS", "NOUN_PL"}

START = {"PRON_SG", "PRON_PL", "DET", "SUBORD", "PART", "ADV"} | _NOUNS
_AFTER_VERB = {"DET", "PRON_OBJ", "PREP", "ADJ", "ADV", "PART", "CONJ"} | _NOUNS
_AFTER_NOUN_SG = {"VERB_3SG", "AUX_SG", "PREP", "CONJ", "ADV"}
_AFTER_NOUN_PL = {"VERB_BASE", "AUX_PL", "PREP", "CONJ", "ADV"}
_AFTER_AUX = {"VERB_BASE", "ADJ", "DET", "ADV", "PREP"} | _NOUNS

NEXT: dict[str, set[str]] = {
    "DET": {"ADJ"} | _NOUNS,
    "ADJ": {"ADJ"} | _NOUNS,
    "PRON_SG": {"AUX_SG", "VERB_3SG", "ADV"},
    "PRON_PL": {"AUX_PL", "VERB_BASE", "ADV"},
    "PRON_OBJ": {"PREP", "CONJ", "ADV"},
    "NOUN_CNT": _AFTER_NOUN_SG,
    "NOUN_MASS": _AFTER_NOUN_SG,
    "NOUN_PL": _AFTER_NOUN_PL,
    "AUX_SG": _AFTER_AUX,
    "AUX_PL": _AFTER_AUX,
    "VERB_BASE": _AFTER_VERB,
    "VERB_3SG": _AFTER_VERB,
    "PREP": {"DET", "PRON_OBJ", "ADJ"} | _NOUNS,
    "PART": {"VERB_BASE"},
    "SUBORD": {"PRON_SG", "PRON_PL", "DET", "ADV"} | _NOUNS,
    "CONJ": {"PRON_SG", "PRON_PL", "DET", "VERB_BASE", "VERB_3SG", "ADJ", "ADV",
             "PART"} | _NOUNS,
    "ADV": {"VERB_BASE", "VERB_3SG", "ADJ", "DET", "PRON_SG", "PRON_PL", "PREP"},
}

PRIORITY = ["PART", "SUBORD", "CONJ", "PREP", "DET", "PRON_SG", "PRON_PL", "PRON_OBJ",
            "AUX_SG", "AUX_PL", "ADV", "VERB_3SG", "VERB_BASE", "ADJ", "NOUN_PL",
            "NOUN_MASS", "NOUN_CNT"]


def candidates(last_pos: str | None) -> tuple[list[str], set[str]]:
    """Every word whose class may legally follow last_pos. May exceed 255."""
    allowed = START if last_pos is None else NEXT[last_pos]
    seen: dict[str, None] = {}
    for pos in sorted(allowed):
        for w in LEX[pos]:
            seen.setdefault(w, None)
    return list(seen), allowed


def resolve_pos(word: str, allowed: set[str]) -> str:
    for pos in PRIORITY:
        if pos in allowed and word in LEX[pos]:
            return pos
    raise AssertionError(f"{word!r} in no allowed class {sorted(allowed)}")


def stats() -> str:
    total = len({w for ws in LEX.values() for w in ws})
    sizes = {p: len(candidates(p)[0]) for p in list(NEXT) + ["START"] if p != "START"}
    sizes["START"] = len(candidates(None)[0])
    worst = max(sizes.values())
    return (f"{total} distinct words across {len(LEX)} classes; "
            f"filtered pool per step {min(sizes.values())}-{worst} "
            f"({'tournament needed' if worst > 253 else 'fits in one Choice'})")
