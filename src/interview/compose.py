"""Word-level composition: can Jev build a sentence by choosing one word at a time?

Setup per the proposal:
  * a 255-word vocabulary (the documented per-Choice maximum)
  * state carries ONLY the question and the words chosen so far
  * NO context about what Jev is -- nothing self-referential
  * termination is a parallel Noul, never an option inside the Choice
    (an END option placed among content words competes with them and wins)

Two arms:
  naive   greedy argmax over the raw distribution
  guided  three code-side corrections, none of which invent content:
            1. debias against a context-free baseline, score = P_cond / P_base**GAMMA,
               measured by re-asking with the question blanked out
            2. ban immediate repetition
            3. cap any word at MAX_USES occurrences

Arm 2 exists because the letter experiment showed Jev's distribution is dominated
by a context-free prior. If the same is true of words, the common function words
will win every step regardless of the question, and dividing the prior out is what
exposes whatever conditional signal is underneath.

Usage:  python3 -m src.interview.compose
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from src.interview.client import Jev  # noqa: E402

RESULTS = pathlib.Path(__file__).resolve().parents[2] / "results"
GAMMA = 0.6
MAX_USES = 2
STOP_AT = 0.80
MAX_WORDS = 16

_RAW = """
i you it they we this that the a an my your its their some no any all
am is are was were be been being do does did can cannot could will would
should must may might have has had make makes made need needs want wants
know knows think thinks see sees say says give gives take takes use uses
work works help helps fail fails change changes mean means depend depends
matter matters seem seems become becomes remain remains exist exists
answer answers ask asks choose chooses decide decides judge judges
predict measure understand learn improve replace build break trust
model models language text words sentence sentences question questions
decision decisions judgment probability confidence uncertainty code
software system systems people person human humans machine machines
data context tool tools time speed cost risk value truth error errors
limit limits purpose mind thought view views opinion fact facts world
future intelligence reasoning meaning structure output input task tasks
user users developer developers power harm good bad better worse best
right wrong true false useful useless fast slow small large simple
complex clear certain uncertain honest new old real possible impossible
hard easy important different same own only more less very not never
always often sometimes still already too also just even well enough
and or but because so if when while than as of to in on for with
without from by about into over under between through at like instead
rather however therefore though yes maybe nothing something anything
everything nobody someone everyone here there now then what why how
who which where both neither each most many few one two
"""

# Trimmed to fit the 255-option ceiling. Dropped inflections that are redundant
# given another form of the same verb is already present.
_TRIM = {"were", "being", "been", "did", "could", "might", "thinks", "sees",
         "says", "gives", "takes", "helps", "fails", "becomes", "remains",
         "exists", "chooses", "judges", "asks"}

VOCAB: list[str] = [w for w in dict.fromkeys(_RAW.split()) if w not in _TRIM]
assert len(VOCAB) <= 255, f"Choice accepts at most 255 options, got {len(VOCAB)}"

BLANK_QUESTION = "(no question)"


def _questions(question: str, so_far: str, vocab: list[str]) -> dict:
    return {
        "next_word": {
            "type": "choice",
            "instructions": {
                "question": "Which word should come next in `words_so_far` so that it grows "
                            "into a good, grammatical answer to `interview_question`?",
                "focus": "Choose exactly one word that continues `words_so_far` naturally.",
            },
            "criteria": {w: None for w in vocab},
        },
        "complete": {
            "type": "noul",
            "instructions": "Is `words_so_far` already a complete, grammatical answer to "
                            "`interview_question` that needs no more words?",
        },
    }


def _state(question: str, so_far: str) -> dict:
    return {"interview_question": question, "words_so_far": so_far}


def compose(jev: Jev, question: str, guided: bool) -> dict:
    words: list[str] = []
    trace = []
    for i in range(MAX_WORDS):
        so_far = " ".join(words)
        r = jev.ask(_state(question, so_far), _questions(question, so_far, VOCAB))
        probs = r["answers"]["next_word"]["probabilities"]
        conf = r["answers"]["next_word"]["confidence"]
        done = r["answers"]["complete"]["noul"]

        if words and done >= STOP_AT:
            trace.append({"step": i, "stop": True, "complete": done})
            break

        if guided:
            b = jev.ask(_state(BLANK_QUESTION, so_far), _questions(BLANK_QUESTION, so_far, VOCAB))
            base = b["answers"]["next_word"]["probabilities"]
            scores = {w: probs[w] / ((base[w] + 1e-4) ** GAMMA) for w in VOCAB}
            banned = {w for w in VOCAB if words.count(w) >= MAX_USES}
            if words:
                banned.add(words[-1])
            pick = max((w for w in VOCAB if w not in banned), key=lambda w: scores[w])
            raw_pick = max(probs, key=probs.get)
        else:
            pick = raw_pick = max(probs, key=probs.get)

        words.append(pick)
        trace.append({
            "step": i, "pick": pick, "raw_argmax": raw_pick, "p": probs[pick],
            "confidence": conf, "complete": done,
            "top": sorted(probs.items(), key=lambda kv: -kv[1])[:5],
        })
    return {"question": question, "sentence": " ".join(words), "trace": trace}


TUNED_STOP = 0.45          # the Noul rated "depends" 0.55 complete; 0.80 was unreachable
CONF_FLOOR = 0.12          # below this the next-word distribution carries no signal


def compose_tuned(jev: Jev, question: str) -> dict:
    """No debiasing (at word level the prior IS grammar), lower stop threshold,
    bigram-loop ban, and a confidence floor: when Jev stops having a view about
    the next word, treat that as the end of the sentence rather than pushing on.
    """
    words: list[str] = []
    trace = []
    stop_reason = "max_words"
    for i in range(MAX_WORDS):
        so_far = " ".join(words)
        r = jev.ask(_state(question, so_far), _questions(question, so_far, VOCAB))
        probs = r["answers"]["next_word"]["probabilities"]
        conf = r["answers"]["next_word"]["confidence"]
        done = r["answers"]["complete"]["noul"]

        if words and done >= TUNED_STOP:
            stop_reason = f"complete={done:.2f}"
            trace.append({"step": i, "stop": stop_reason})
            break
        if len(words) >= 2 and conf < CONF_FLOOR:
            stop_reason = f"confidence collapsed to {conf:.2f}"
            trace.append({"step": i, "stop": stop_reason})
            break

        # Ban only what creates a loop: an immediate repeat, or a repeated bigram.
        banned = set()
        if words:
            banned.add(words[-1])
        if len(words) >= 3:
            for w in VOCAB:
                if [words[-1], w] == words[-3:-1]:
                    banned.add(w)
        pick = max((w for w in VOCAB if w not in banned), key=lambda w: probs[w])

        words.append(pick)
        trace.append({"step": i, "pick": pick, "p": probs[pick], "confidence": conf,
                      "complete": done,
                      "top": sorted(probs.items(), key=lambda kv: -kv[1])[:5]})
    return {"question": question, "sentence": " ".join(words),
            "stop_reason": stop_reason, "trace": trace}


QUESTIONS = [
    "What is the biggest risk of artificial intelligence?",
    "Should a machine be allowed to make moral decisions?",
    "What is intelligence?",
]

TUNED_QUESTIONS = QUESTIONS + [
    "Will artificial intelligence replace human workers?",
    "Is it wrong to lie?",
    "What do people get wrong about machines?",
    "Does a machine understand what it answers?",
]


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    jev, t0, out = Jev(), time.time(), {"vocab_size": len(VOCAB), "runs": []}
    print(f"vocabulary: {len(VOCAB)} words (max 255)\n")

    for q in QUESTIONS:
        for guided in (False, True):
            arm = "guided" if guided else "naive "
            res = compose(jev, q, guided)
            res["arm"] = arm.strip()
            out["runs"].append(res)
            print(f"[{arm}] {q}")
            for t in res["trace"]:
                if t.get("stop"):
                    print(f"    stop (complete={t['complete']:.2f})")
                    continue
                shift = "" if t["pick"] == t["raw_argmax"] else f"  (raw wanted {t['raw_argmax']!r})"
                print(f"    {t['step']:02d} {t['pick']:<12} p={t['p']:.3f} conf={t['confidence']:.2f} "
                      f"done={t['complete']:.2f}{shift}")
            print(f"    => {res['sentence']!r}\n")

    print("=" * 74)
    print("TUNED: no debias, stop at 0.45 complete or on confidence collapse")
    print("=" * 74)
    for q in TUNED_QUESTIONS:
        res = compose_tuned(jev, q)
        res["arm"] = "tuned"
        out["runs"].append(res)
        print(f"\nQ: {q}")
        for t in res["trace"]:
            if t.get("stop"):
                print(f"    -- {t['stop']}")
                continue
            print(f"    {t['step']:02d} {t['pick']:<12} p={t['p']:.3f} "
                  f"conf={t['confidence']:.2f} done={t['complete']:.2f}")
        print(f"    ANSWER: {res['sentence']!r}   [{res['stop_reason']}]")

    out.update(requests=jev.requests, cost_usd=jev.cost, seconds=round(time.time() - t0, 1),
               model=jev.model_seen)
    (RESULTS / "compose.json").write_text(json.dumps(out, indent=2))
    print(f"\n{jev.requests} requests, {out['seconds']}s, ${jev.cost:.5f}")


if __name__ == "__main__":
    main()
