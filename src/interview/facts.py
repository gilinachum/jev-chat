"""Word-by-word composition on simple factual questions, with control options.

Changes from compose.py, all four requested:

1. STOP option INSIDE the Choice, described properly ("the answer is already
   correct and understandable to a human reader"). My earlier attempt used a bare
   undescribed sentinel and it fired at step 0; option descriptions carry real
   weight for options that mean something, so this deserves a fair retest.
2. MISSING option INSIDE the Choice, for "the word I want is not on your list".
   This is NOT covered by the completeness Noul -- "the answer is finished" and
   "my word is absent" are independent. Both are asked, as an option and as a
   parallel Noul, so we can compare which signal behaves.
3. An explicit anti-repetition instruction in the question text, so we can see
   whether Jev self-regulates instead of relying on the code-side loop ban.
4. Simple factual questions with a topic-matched vocabulary. If the earlier
   collapse was "it has nothing to say", a fact it plainly knows plus words
   fitted to that fact removes that excuse.

The ablation: every question is run twice, once with the answer word present in
the vocabulary and once with it removed. If the MISSING signals are real they
should rise in the ablated arm. That makes vocabulary-coverage a measurable
capability rather than a hopeful extra option.

Usage:  python3 -m src.interview.facts
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
MAX_WORDS = 8

_RAW = """
a an the of in on at to from into over under above with and or but because
is are was has have not no yes it they there this that one
zero two three four five six seven eight nine ten twelve twenty thirty sixty
hundred thousand million most many few all some both
day days week weeks month months year years hour hours minute minutes
night morning summer winter autumn spring
sun moon star stars planet planets earth sky space light dark bright
water ice snow rain cloud clouds wind air fire ground soil rock sand
sea ocean oceans river lake mountain island
tree trees leaf leaves flower flowers grass wood forest desert
spider spiders bee bees bird birds fish dog cat cow horse
butterfly caterpillar insect insects animal animals
leg legs wing wings egg eggs milk web nest
blue green red yellow white black brown orange grey
make makes made eat eats lay lays live lives grow grows fall falls
freeze freezes melt melts turn turns become becomes fly flies swim swims
give gives come comes need needs hold holds
hot cold warm cool wet dry big small large tall long round heavy
degrees celsius temperature
pacific atlantic
"""

BASE_VOCAB: list[str] = list(dict.fromkeys(_RAW.split()))
assert len(BASE_VOCAB) + 2 <= 255, f"too many options: {len(BASE_VOCAB) + 2}"

ANTI_REPEAT = ("Do not repeat words that already appear in `words_so_far` unless "
               "grammar truly requires it. Never pad the answer.")

# (question, words essential to the answer -> removed in the ablated arm)
FACTS: list[tuple[str, list[str]]] = [
    ("How many legs does a spider have?", ["eight"]),
    ("What colour is a clear sky?", ["blue"]),
    ("Is the sun a star or a planet?", ["star"]),
    ("What do bees make?", ["milk"]),          # vocab has no 'honey' on purpose
    ("How many days are in a week?", ["seven"]),
    ("At what temperature in celsius does water freeze?", ["zero"]),
    ("What does a caterpillar become?", ["butterfly"]),
    ("What do birds lay?", ["eggs"]),
    ("Which is larger, the sun or the earth?", ["sun"]),
    ("Where do fish live?", ["water"]),
]


def build_questions(vocab: list[str]) -> dict:
    options: dict[str, object] = {w: None for w in vocab}
    options[STOP] = {
        "what": "The words already in `words_so_far` form a correct answer that a "
                "human reader would understand. Nothing further is needed.",
        "not_for": "An answer that is still incomplete, ungrammatical, or unclear.",
    }
    options[MISSING] = {
        "what": "The word you would most like to use next is not present anywhere in "
                "this list of options.",
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
            "instructions": "Is `words_so_far` already a correct and understandable answer "
                            "to `factual_question`, needing no further words?",
        },
        "vocab_missing": {
            "type": "noul",
            "instructions": "Is the word you would most like to add next ABSENT from the "
                            "list of words you were offered?",
        },
        "repeating": {
            "type": "noul",
            "instructions": "Does `words_so_far` contain unnecessary repetition?",
        },
    }


def run(jev: Jev, question: str, vocab: list[str]) -> dict:
    words: list[str] = []
    trace: list[dict] = []
    stop_reason = "max_words"
    qs = build_questions(vocab)

    for i in range(MAX_WORDS):
        so_far = " ".join(words)
        r = jev.ask({"factual_question": question, "words_so_far": so_far}, qs)
        a = r["answers"]["next_word"]
        probs, pick, conf = a["probabilities"], a["choice"], a["confidence"]
        done = r["answers"]["complete"]["noul"]
        miss = r["answers"]["vocab_missing"]["noul"]
        rep = r["answers"]["repeating"]["noul"]

        row = {
            "step": i, "pick": pick, "p": probs[pick], "confidence": conf,
            "noul_complete": done, "noul_missing": miss, "noul_repeating": rep,
            "p_stop_option": probs[STOP], "p_missing_option": probs[MISSING],
            "top": [(k, round(v, 3)) for k, v in
                    sorted(probs.items(), key=lambda kv: -kv[1])[:5]],
        }
        trace.append(row)

        if pick == STOP:
            stop_reason = f"STOP option at step {i} (p={probs[STOP]:.2f})"
            break
        if pick == MISSING:
            stop_reason = f"MISSING option at step {i} (p={probs[MISSING]:.2f})"
            break
        words.append(pick)

    return {"question": question, "answer": " ".join(words),
            "stop_reason": stop_reason, "trace": trace}


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    jev, t0 = Jev(), time.time()
    out: dict = {"vocab_size": len(BASE_VOCAB) + 2, "runs": []}
    print(f"vocabulary: {len(BASE_VOCAB)} words + 2 control options "
          f"= {len(BASE_VOCAB) + 2} (max 255)\n")

    for question, keys in FACTS:
        for arm in ("full", "ablated"):
            vocab = BASE_VOCAB if arm == "full" else [w for w in BASE_VOCAB if w not in keys]
            res = run(jev, question, vocab)
            res["arm"] = arm
            res["removed"] = [] if arm == "full" else keys
            out["runs"].append(res)

            tag = "full   " if arm == "full" else f"-{','.join(keys):<7}"
            print(f"[{tag}] {question}")
            for t in res["trace"]:
                label = t["pick"] if not t["pick"].startswith("[") else t["pick"]
                print(f"    {t['step']:02d} {label:<38} p={t['p']:.3f} conf={t['confidence']:.2f} "
                      f"| complete={t['noul_complete']:.2f} missing={t['noul_missing']:.2f} "
                      f"rep={t['noul_repeating']:.2f} | p(STOP)={t['p_stop_option']:.2f} "
                      f"p(MISS)={t['p_missing_option']:.2f}")
            print(f"    => {res['answer']!r}  [{res['stop_reason']}]\n")

    out.update(requests=jev.requests, cost_usd=jev.cost,
               seconds=round(time.time() - t0, 1), model=jev.model_seen)
    (RESULTS / "facts.json").write_text(json.dumps(out, indent=2))
    print(f"{jev.requests} requests, {out['seconds']}s, ${jev.cost:.5f}")


if __name__ == "__main__":
    main()
