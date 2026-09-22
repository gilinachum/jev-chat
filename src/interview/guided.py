"""Dynamic per-step candidate sets: code supplies the syntax, Jev supplies the meaning.

midfacts.py found that Jev picks content words correctly (`ice` at p=0.99) and drops
or mangles the function words that hold a clause together. So give it exactly that
help and nothing more.

Division of labour, stated plainly because it determines what this proves:
  * CODE owns syntax. A POS-tagged lexicon plus a part-of-speech grammar decides
    which word CLASSES may legally come next, and offers every word in those classes.
  * JEV owns semantics. When a noun is legal it is offered every topical noun in the
    lexicon, so it must still pick `cocoon` over `wing`, `leaf`, `egg`, `tree` and
    forty others. The grammar never narrows the choice to the right answer.

This is the docs' own "keep rules in code, give the model the judgment" principle,
applied to the one thing Jev provably cannot do. What it does NOT show is Jev
producing grammar on its own.

Usage:  python3 -m src.interview.guided
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from src.interview.client import Jev  # noqa: E402

RESULTS = pathlib.Path(__file__).resolve().parents[2] / "results"

STOP = "[STOP - the answer is complete]"
MISSING = "[MISSING - my word is not on this list]"
MAX_WORDS = 12

# --------------------------------------------------------------------------- lexicon

LEX: dict[str, list[str]] = {
    # function classes -- small, and this is the help we are adding
    "DET": ["the", "a", "an", "its", "their", "this", "that", "some", "each", "one", "no"],
    "PRON_SG": ["it", "this"],
    "PRON_PL": ["they", "these"],
    "PRON_OBJ": ["it", "them", "itself"],
    "AUX_SG": ["is", "has", "does", "was", "can", "will"],
    "AUX_PL": ["are", "have", "do", "were", "can", "will"],
    "PART": ["to"],
    "SUBORD": ["because", "when", "while", "after", "before", "so", "until"],
    "CONJ": ["and", "or", "but"],
    "PREP": ["in", "on", "into", "inside", "of", "from", "with", "without", "through",
             "between", "around", "over", "under", "above", "below", "at", "for", "by"],
    "ADV": ["then", "again", "slowly", "first", "later", "still", "only", "also",
            "away", "back", "up", "down", "more", "less", "very"],
    # content classes -- wide on purpose, so the semantic choice stays real
    # Singular COUNT nouns need a determiner: "becomes a cocoon", never "becomes cocoon".
    "NOUN_CNT": ["caterpillar", "butterfly", "cocoon", "shell", "body", "wing", "leaf",
                 "tree", "branch", "flower", "bee", "bird", "nest", "egg", "spider",
                 "web", "insect", "fish", "gill", "sun", "moon", "sky", "day", "stage",
                 "form", "plant", "seed", "root"],
    # MASS nouns are grammatical bare: "reflects sunlight", "traps water".
    "NOUN_MASS": ["water", "ice", "air", "sunlight", "pollen", "light", "heat", "cold",
                  "colour", "autumn", "winter", "night", "food", "time", "skin",
                  "change", "grass", "shade", "green"],
    "NOUN_PL": ["caterpillars", "butterflies", "cocoons", "wings", "leaves", "trees",
                "flowers", "bees", "birds", "nests", "eggs", "spiders", "webs",
                "insects", "gills", "days", "colours", "plants", "seeds", "roots"],
    "VERB_BASE": ["become", "change", "grow", "turn", "make", "form", "eat", "feed",
                  "breathe", "melt", "freeze", "scatter", "reflect", "carry", "catch",
                  "trap", "hold", "keep", "build", "lay", "live", "hide", "rest",
                  "sleep", "emerge", "leave", "stop", "start", "spin", "wrap", "cover",
                  "protect", "need", "use", "take", "give", "move", "rise", "fall",
                  "break", "open", "lose"],
    "VERB_3SG": ["becomes", "changes", "grows", "turns", "makes", "forms", "eats",
                 "feeds", "breathes", "melts", "freezes", "scatters", "reflects",
                 "carries", "catches", "traps", "holds", "keeps", "builds", "lays",
                 "lives", "hides", "rests", "sleeps", "emerges", "leaves", "stops",
                 "starts", "spins", "wraps", "covers", "protects", "needs", "uses",
                 "takes", "gives", "moves", "rises", "falls", "breaks", "opens", "loses"],
    "ADJ": ["hard", "soft", "new", "old", "young", "small", "large", "long", "short",
            "bright", "dark", "blue", "green", "white", "black", "warm", "cool", "cold",
            "hot", "wet", "dry", "safe", "ready", "whole", "different", "same"],
}

# Which classes may follow which. Deliberately permissive: it rules out ungrammatical
# continuations without ever narrowing to a single content word.
# STRICT_DETERMINERS = True is grammatically correct and empirically WORSE.
#
# It hides singular count nouns until a determiner has been chosen, so after
# "because" Jev sees `the` but not `air`/`sky`/`tree`. Measured effect: it chose
# MISSING at step 1 on two of three questions rather than taking `the` as a
# stepping stone, collapsing "why is the sky blue" from 3.70/4 to 0.30/4.
#
# Jev has no lookahead. It evaluates one step myopically and will not select a
# function word now to reach the content word it wants next. So the grammar must
# keep content words VISIBLE at every step, and tolerate the odd missing
# determiner, rather than gate them behind a correct but invisible path.
STRICT_DETERMINERS = False

_NOUNS = ({"NOUN_MASS", "NOUN_PL"} if STRICT_DETERMINERS
          else {"NOUN_CNT", "NOUN_MASS", "NOUN_PL"})

START = {"PRON_SG", "PRON_PL", "DET", "SUBORD", "PART", "ADV"} | _NOUNS
_AFTER_VERB = {"DET", "PRON_OBJ", "PREP", "ADJ", "ADV", "PART", "CONJ"} | _NOUNS
_AFTER_NOUN = {"VERB_3SG", "AUX_SG", "PREP", "CONJ"}
NEXT: dict[str, set[str]] = {
    "DET": {"NOUN_CNT", "NOUN_MASS", "NOUN_PL", "ADJ"},
    "ADJ": {"NOUN_CNT", "NOUN_MASS", "NOUN_PL", "ADJ"},
    "PRON_SG": {"AUX_SG", "VERB_3SG", "ADV"},
    "PRON_PL": {"AUX_PL", "VERB_BASE", "ADV"},
    "PRON_OBJ": {"PREP", "CONJ", "ADV"},
    "NOUN_CNT": _AFTER_NOUN,
    "NOUN_MASS": _AFTER_NOUN,
    "NOUN_PL": {"VERB_BASE", "AUX_PL", "PREP", "CONJ"},
    "AUX_SG": {"VERB_BASE", "ADJ", "DET", "ADV", "PREP"} | _NOUNS,
    "AUX_PL": {"VERB_BASE", "ADJ", "DET", "ADV", "PREP"} | _NOUNS,
    "VERB_BASE": _AFTER_VERB,
    "VERB_3SG": _AFTER_VERB,
    "PREP": {"DET", "PRON_OBJ", "ADJ"} | _NOUNS,
    "PART": {"VERB_BASE"},
    "SUBORD": {"PRON_SG", "PRON_PL", "DET"} | _NOUNS,
    "CONJ": {"PRON_SG", "PRON_PL", "DET", "VERB_BASE", "VERB_3SG", "ADJ", "ADV",
             "PART"} | _NOUNS,
    "ADV": {"VERB_BASE", "VERB_3SG", "ADJ", "DET", "PRON_SG", "PRON_PL"},
}

# When a word belongs to several classes, resolve in this order.
PRIORITY = ["PART", "SUBORD", "CONJ", "PREP", "DET", "PRON_SG", "PRON_PL", "PRON_OBJ",
            "AUX_SG", "AUX_PL", "ADV", "VERB_3SG", "VERB_BASE", "ADJ", "NOUN_PL",
            "NOUN_MASS", "NOUN_CNT"]


def candidates(last_pos: str | None) -> tuple[list[str], set[str]]:
    allowed = START if last_pos is None else NEXT[last_pos]
    words: list[str] = []
    for pos in allowed:
        for w in LEX[pos]:
            if w not in words:
                words.append(w)
    assert len(words) + 2 <= 255, f"{len(words) + 2} options exceeds the 255 ceiling"
    return words, allowed


def resolve_pos(word: str, allowed: set[str]) -> str:
    for pos in PRIORITY:
        if pos in allowed and word in LEX[pos]:
            return pos
    raise AssertionError(f"{word!r} not in any allowed class {allowed}")


# --------------------------------------------------------------------------- request

def build(words: list[str], vocab: list[str], allowed: set[str]) -> dict:
    options: dict[str, object] = {w: None for w in vocab}
    options[STOP] = {
        "what": "The words already in `words_so_far` form a correct answer that a human "
                "reader would understand. Nothing further is needed.",
        "not_for": "An answer that is still incomplete, ungrammatical, or unclear.",
    }
    options[MISSING] = {
        "what": "The word you would most like to use next is not present anywhere in this "
                "list of options.",
        "not_for": "A word that is on the list, even if it is not your first preference.",
    }
    return {
        "next_word": {
            "type": "choice",
            "instructions": {
                "question": "Which word should come next in `words_so_far` to answer "
                            "`factual_question` correctly?",
                "focus": "Choose one word that continues `words_so_far`. Every option offered "
                         "is already grammatically valid here, so choose on meaning. Do not "
                         "repeat words already in `words_so_far` unless grammar requires it.",
                "control_options": f"Choose {STOP!r} if the answer is already complete. "
                                   f"Choose {MISSING!r} if the word you need is absent.",
            },
            "criteria": options,
        },
        "complete": {
            "type": "noul",
            "instructions": "Is `words_so_far` already a correct and understandable answer to "
                            "`factual_question`, needing no further words?",
        },
    }


def compose(jev: Jev, question: str) -> dict:
    words: list[str] = []
    pos_seq: list[str] = []
    trace: list[dict] = []
    stop_reason = "max_words"

    for i in range(MAX_WORDS):
        vocab, allowed = candidates(pos_seq[-1] if pos_seq else None)
        r = jev.ask({"factual_question": question, "words_so_far": " ".join(words)},
                    build(words, vocab, allowed))
        a = r["answers"]["next_word"]
        pick, conf, probs = a["choice"], a["confidence"], a["probabilities"]
        done = r["answers"]["complete"]["noul"]

        row = {"step": i, "pick": pick, "p": probs[pick], "confidence": conf,
               "complete": done, "n_options": len(vocab) + 2,
               "allowed_classes": sorted(allowed),
               "top": [(k, round(v, 3)) for k, v in
                       sorted(probs.items(), key=lambda kv: -kv[1])[:4]]}

        if pick == STOP:
            stop_reason = f"STOP (p={probs[pick]:.2f}, complete={done:.2f})"
            trace.append(row)
            break
        if pick == MISSING:
            stop_reason = f"MISSING (p={probs[pick]:.2f})"
            trace.append(row)
            break

        pos = resolve_pos(pick, allowed)
        row["pos"] = pos
        trace.append(row)
        words.append(pick)
        pos_seq.append(pos)

    return {"question": question, "answer": " ".join(words), "n_words": len(words),
            "pos_sequence": pos_seq, "stop_reason": stop_reason, "trace": trace}


GRADE_LEVELS = [
    "Wrong or meaningless.",
    "Related to the topic but does not answer it.",
    "Partly correct but incomplete or garbled.",
    "Correct but awkwardly worded.",
    "Correct and clearly worded.",
]


def grade(jev: Jev, question: str, answer: str) -> dict:
    r = jev.ask({"question": question, "answer": answer}, {
        "correct": {"type": "noul", "instructions": "Does `answer` correctly answer `question`?"},
        "readable": {"type": "noul", "instructions": "Is `answer` grammatical English that a "
                                                    "person would understand?"},
        "quality": {"type": "score", "instructions": "How good is `answer` as a reply to "
                                                    "`question`?", "criteria": GRADE_LEVELS},
    })
    return {"correct": r["answers"]["correct"]["noul"],
            "readable": r["answers"]["readable"]["noul"],
            "quality": r["answers"]["quality"]["score"]}


# question, reference answer, and what the FIXED-vocabulary run produced before
CASES = [
    ("How does a caterpillar become a butterfly?", "it changes inside a hard cocoon",
     "does it do", 0.09),
    ("Why do leaves change colour in autumn?", "the tree stops making green",
     "because the stops makes green", 1.36),
    ("Why is the sky blue?", "the air scatters blue light",
     "because the air scatters sunlight", 3.09),
]


REPEATS = 3  # the pipeline has real run-to-run variance; one sample is not a result


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    jev, t0, runs = Jev(), time.time(), []

    for question, reference, before, before_q in CASES:
        print(f"\nQ: {question}")
        print(f"   reference: {reference!r}")
        print(f"   BEFORE (fixed 226-word vocab): {before!r}  quality {before_q:.2f}/4")
        for rep in range(REPEATS):
            res = compose(jev, question)
            res["repeat"] = rep
            res["reference"] = reference
            res["fixed_vocab_before"] = {"answer": before, "quality": before_q}
            res["grade"] = grade(jev, question, res["answer"] or "(no answer)")
            runs.append(res)
            g = res["grade"]
            print(f"   run {rep}: {res['answer']!r:52} correct={g['correct']:.2f} "
                  f"readable={g['readable']:.2f} quality={g['quality']:.2f}/4  "
                  f"[{res['stop_reason'].split(' (')[0]}]")

    print("\n" + "=" * 92)
    print(f"{'question':44}{'before':>8}{'mean':>8}{'best':>8}{'worst':>8}{'delta(mean)':>13}")
    for question, reference, before, before_q in CASES:
        qs = [r["grade"]["quality"] for r in runs if r["question"] == question]
        m = sum(qs) / len(qs)
        print(f"{question[:43]:44}{before_q:>8.2f}{m:>8.2f}{max(qs):>8.2f}{min(qs):>8.2f}"
              f"{m-before_q:>+13.2f}")
    allq = [r["grade"]["quality"] for r in runs]
    print(f"\n  overall mean {sum(allq)/len(allq):.2f}/4 over {len(runs)} runs; "
          f"best single answer {max(allq):.2f}/4")

    out = {"runs": runs, "requests": jev.requests, "cost_usd": jev.cost,
           "seconds": round(time.time() - t0, 1), "model": jev.model_seen}
    (RESULTS / "guided.json").write_text(json.dumps(out, indent=2))
    print(f"\n{jev.requests} requests, {out['seconds']}s, ${jev.cost:.5f}")


if __name__ == "__main__":
    main()
