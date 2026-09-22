"""Where does word-by-word composition actually break?

facts.py showed 10/10 on closed-domain questions whose answers are 1-3 words.
This pushes the same machinery to questions that genuinely need 4-8 words, keeping
the domain closed (everyday nature) and the vocabulary fitted to it.

Kept from facts.py, because it worked: described STOP and MISSING options inside
the Choice, an anti-repetition instruction, parallel completeness/repetition Nouls.

Added:
  * break-depth tracking -- the step index where next-word confidence first falls
    below CONF_BREAK, which is the quantity we are actually trying to find
  * a grading pass where Jev judges its own finished answers. Judging text is the
    thing Jev is good at, so this is a fairer scorer than my own reading, and it is
    reported alongside the target answer so you can disagree with both.

Usage:  python3 -m src.interview.midfacts
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
CONF_BREAK = 0.15

_RAW = """
a an the of in on at to from into out for with without and or but because so
if when while then there it its they their them this that is are was be been
has have do does not no yes more less most many few each one two three
sun sunlight light day days night moon earth sky air water ice steam liquid
heat cold temperature colour green red yellow brown
leaf leaves tree trees branch flower flowers pollen seed seeds root grass plant
bird birds nest nests egg eggs wing wings spider spiders web insect insects
fly flies bee bees honey fish gills butterfly caterpillar cocoon shell
body food eat eats feed breathe breathes grow grows make makes made
turn turns change changes catch catches carry carries hold holds keep keeps
warm warms cool cools melt melts freeze freezes scatter scatters
reflect reflects absorb absorbs travel travels move moves rise rises
fall falls stop stops start becomes become use uses need needs live lives
sleep build builds lay lays protect protects trap traps spin spins
hot wet dry hard soft new old young small large long short bright dark
blue white black inside outside between around over under above below through
during before after again away back side sides part parts time shorter longer
enough only also very still again water's
"""

BASE_VOCAB: list[str] = list(dict.fromkeys(_RAW.split()))

ANTI_REPEAT = ("Do not repeat words that already appear in `words_so_far` unless grammar "
               "truly requires it. Never pad the answer with filler.")

# (question, a reference answer for the reader -- never shown to the model)
MID_FACTS: list[tuple[str, str]] = [
    ("Why is the sky blue?", "the air scatters blue light"),
    ("Why do leaves change colour in autumn?", "the tree stops making green"),
    ("How does a caterpillar become a butterfly?", "it changes inside a hard cocoon"),
    ("What does a spider use its web for?", "to catch insects for food"),
    ("Why do birds build nests?", "to hold and keep their eggs warm"),
    ("What happens to ice in the sun?", "the heat melts it into water"),
    ("How do bees help flowers?", "they carry pollen between flowers"),
    ("How do fish breathe under water?", "they take air through their gills"),
    ("Why can we see the moon at night?", "the sun lights one side of it"),
    ("What happens to water when it freezes?", "it turns into hard ice"),
]


def build_questions(vocab: list[str]) -> dict:
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
                "focus": f"Choose one word that continues `words_so_far`. {ANTI_REPEAT}",
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
        "repeating": {
            "type": "noul",
            "instructions": "Does `words_so_far` contain unnecessary repetition?",
        },
    }


def compose(jev: Jev, question: str) -> dict:
    words: list[str] = []
    trace: list[dict] = []
    qs = build_questions(BASE_VOCAB)
    stop_reason, break_depth = "max_words", None

    for i in range(MAX_WORDS):
        r = jev.ask({"factual_question": question, "words_so_far": " ".join(words)}, qs)
        a = r["answers"]["next_word"]
        pick, conf, probs = a["choice"], a["confidence"], a["probabilities"]
        done = r["answers"]["complete"]["noul"]
        rep = r["answers"]["repeating"]["noul"]

        trace.append({"step": i, "pick": pick, "p": probs[pick], "confidence": conf,
                      "complete": done, "repeating": rep,
                      "top": [(k, round(v, 3)) for k, v in
                              sorted(probs.items(), key=lambda kv: -kv[1])[:4]]})

        if break_depth is None and not pick.startswith("[") and conf < CONF_BREAK:
            break_depth = i
        if pick == STOP:
            stop_reason = f"STOP (p={probs[pick]:.2f}, complete={done:.2f})"
            break
        if pick == MISSING:
            stop_reason = f"MISSING (p={probs[pick]:.2f})"
            break
        words.append(pick)

    return {"question": question, "answer": " ".join(words), "n_words": len(words),
            "stop_reason": stop_reason, "break_depth": break_depth, "trace": trace}


GRADE_LEVELS = [
    "Wrong or meaningless.",
    "Related to the topic but does not answer it.",
    "Partly correct but incomplete or garbled.",
    "Correct but awkwardly worded.",
    "Correct and clearly worded.",
]


def grade(jev: Jev, question: str, answer: str) -> dict:
    """Jev grades the finished answer. Judging text is what it is actually good at."""
    state = {"question": question, "answer": answer}
    r = jev.ask(state, {
        "correct": {"type": "noul",
                    "instructions": "Does `answer` correctly answer `question`?"},
        "readable": {"type": "noul",
                     "instructions": "Is `answer` grammatical English that a person would "
                                     "understand?"},
        "quality": {"type": "score",
                    "instructions": "How good is `answer` as a reply to `question`?",
                    "criteria": GRADE_LEVELS},
    })
    return {
        "correct": r["answers"]["correct"]["noul"],
        "readable": r["answers"]["readable"]["noul"],
        "quality": r["answers"]["quality"]["score"],
        "quality_confidence": r["answers"]["quality"]["confidence"],
    }


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    jev, t0 = Jev(), time.time()
    print(f"vocabulary: {len(BASE_VOCAB)} words + 2 control = {len(BASE_VOCAB) + 2} "
          f"(max 255)\n")
    runs = []

    for question, reference in MID_FACTS:
        res = compose(jev, question)
        res["reference"] = reference
        res["grade"] = grade(jev, question, res["answer"] or "(no answer)")
        runs.append(res)

        print(f"Q: {question}")
        for t in res["trace"]:
            print(f"   {t['step']:02d} {t['pick'][:34]:36} p={t['p']:.3f} conf={t['confidence']:.2f} "
                  f"complete={t['complete']:.2f} rep={t['repeating']:.2f}")
        g = res["grade"]
        print(f"   ANSWER    : {res['answer']!r}  ({res['n_words']} words, {res['stop_reason']})")
        print(f"   reference : {reference!r}")
        print(f"   Jev grades: correct={g['correct']:.2f} readable={g['readable']:.2f} "
              f"quality={g['quality']:.2f}/4   break_depth={res['break_depth']}\n")

    ok = [r for r in runs if r["grade"]["correct"] >= 0.5]
    depths = [r["break_depth"] for r in runs if r["break_depth"] is not None]
    print("=" * 74)
    print(f"  graded correct (>=0.50): {len(ok)}/{len(runs)}")
    print(f"  mean words produced    : {sum(r['n_words'] for r in runs)/len(runs):.1f}")
    print(f"  mean Jev quality       : {sum(r['grade']['quality'] for r in runs)/len(runs):.2f}/4")
    print(f"  confidence broke below {CONF_BREAK} in {len(depths)}/{len(runs)} runs"
          + (f", first at word index {min(depths)}, median {sorted(depths)[len(depths)//2]}"
             if depths else ""))

    out = {"vocab_size": len(BASE_VOCAB) + 2, "conf_break": CONF_BREAK, "runs": runs,
           "requests": jev.requests, "cost_usd": jev.cost,
           "seconds": round(time.time() - t0, 1), "model": jev.model_seen}
    (RESULTS / "midfacts.json").write_text(json.dumps(out, indent=2))
    print(f"\n{jev.requests} requests, {out['seconds']}s, ${jev.cost:.5f}")


if __name__ == "__main__":
    main()
