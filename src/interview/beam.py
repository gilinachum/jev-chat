"""Beam search over a sharded tournament, with Jev making the final selection.

Three ideas composed:

1. SHARDED TOURNAMENT breaks the 255-option ceiling. The grammar-filtered pool now
   reaches 662 words, so it is split into shards of <=250. All shards go in ONE
   request as separate Choice questions -- questions in a request are evaluated in
   parallel against the same state -- then the top 25% of each shard advance to a
   runoff Choice. Two requests, not five. Shard probabilities are normalised within
   a shard and are not comparable across shards, which is exactly why a per-shard
   top-25% cut followed by a runoff is the right shape.

2. BEAM SEARCH fixes the variance found in guided.py, where "blue light" vs "light"
   came down to a 0.32-vs-0.48 coin flip. Keeping several partial answers alive lets
   a strong word later redeem a mediocre word now. Pruning uses mean log probability
   so longer beams are not crushed.

3. JEV PICKS THE WINNER. Generation log-probs are the weak signal; judging finished
   text is what Jev is good at. So the final choice among completed beams is one
   Choice question whose options are the candidate sentences.

Usage:  python3 -m src.interview.beam
"""
from __future__ import annotations

import json
import math
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from src.interview.client import Jev  # noqa: E402
from src.interview.lexicon import candidates, resolve_pos, stats  # noqa: E402

RESULTS = pathlib.Path(__file__).resolve().parents[2] / "results"

STOP = "[STOP - the answer is complete]"
MISSING = "[MISSING - my word is not on this list]"
SHARD_MAX = 250
ADVANCE = 0.25        # top fraction of each shard that reaches the runoff
BEAM_WIDTH = 4
EXPANSIONS = 3        # continuations taken from each live beam per step
MAX_WORDS = 9

CONTROL: dict[str, object] = {
    STOP: {"what": "The words already in `words_so_far` form a correct answer that a human "
                   "reader would understand. Nothing further is needed.",
           "not_for": "An answer that is still incomplete, ungrammatical, or unclear."},
    MISSING: {"what": "The word you would most like to use next is not present anywhere in "
                      "this list of options.",
              "not_for": "A word that is on the list, even if it is not your first preference."},
}

FOCUS = ("Choose one word that continues `words_so_far`. Every option offered is already "
         "grammatically valid here, so choose on meaning. Do not repeat words already in "
         "`words_so_far` unless grammar requires it.")


def _choice(options: dict[str, object], with_control: bool = True) -> dict:
    crit = dict(options)
    if with_control:
        crit.update(CONTROL)
    return {
        "type": "choice",
        "instructions": {
            "question": "Which word should come next in `words_so_far` to answer "
                        "`factual_question` correctly?",
            "focus": FOCUS,
        },
        "criteria": crit,
    }


def distribution(jev: Jev, state: dict, pool: list[str]) -> tuple[dict[str, float], dict]:
    """Probability over pool + control options, via a single Choice or a tournament."""
    meta: dict = {"pool": len(pool)}

    if len(pool) + len(CONTROL) <= 253:
        r = jev.ask(state, {"w": _choice({w: None for w in pool}),
                            "complete": {"type": "noul",
                                         "instructions": "Is `words_so_far` already a correct "
                                         "and understandable answer to `factual_question`?"}})
        meta.update(mode="single", requests=1)
        return r["answers"]["w"]["probabilities"], meta | {
            "complete": r["answers"]["complete"]["noul"]}

    # --- shard round: every shard in one request, evaluated in parallel
    shards = [pool[i:i + SHARD_MAX] for i in range(0, len(pool), SHARD_MAX)]
    qs: dict[str, dict] = {
        f"s{i}": _choice({w: None for w in sh}, with_control=False)
        for i, sh in enumerate(shards)
    }
    qs["complete"] = {"type": "noul",
                      "instructions": "Is `words_so_far` already a correct and understandable "
                                      "answer to `factual_question`?"}
    r = jev.ask(state, qs)
    done = r["answers"]["complete"]["noul"]

    survivors: list[str] = []
    per_shard = []
    for i, sh in enumerate(shards):
        p = r["answers"][f"s{i}"]["probabilities"]
        keep = max(2, int(len(sh) * ADVANCE))
        top = [w for w, _ in sorted(p.items(), key=lambda kv: -kv[1])[:keep]]
        survivors += top
        per_shard.append({"size": len(sh), "advanced": len(top), "best": top[:3]})

    # --- runoff over the survivors, trimmed to fit with the control options
    survivors = survivors[:253 - len(CONTROL)]
    r2 = jev.ask(state, {"w": _choice({w: None for w in survivors})})
    meta.update(mode="tournament", shards=per_shard, survivors=len(survivors), requests=2)
    return r2["answers"]["w"]["probabilities"], meta | {"complete": done}


def search(jev: Jev, question: str) -> dict:
    """Beam search. Each beam is (words, pos_seq, cumulative log-prob)."""
    live = [{"words": [], "pos": [], "logp": 0.0}]
    finished: list[dict] = []
    log: list[dict] = []

    for step in range(MAX_WORDS):
        if not live:
            break
        pool_expansions: list[dict] = []
        for beam in live:
            pool, allowed = candidates(beam["pos"][-1] if beam["pos"] else None)
            state = {"factual_question": question, "words_so_far": " ".join(beam["words"])}
            probs, meta = distribution(jev, state, pool)
            log.append({"step": step, "beam": " ".join(beam["words"]), **{
                k: v for k, v in meta.items() if k in ("mode", "pool", "survivors", "complete")}})

            ranked = sorted(probs.items(), key=lambda kv: -kv[1])
            taken = 0
            for word, p in ranked:
                if taken >= EXPANSIONS or p <= 0:
                    break
                if word == MISSING:
                    continue
                if word == STOP:
                    if beam["words"]:
                        finished.append({**beam, "stop_p": p,
                                         "score": beam["logp"] / max(1, len(beam["words"]))})
                        taken += 1
                    continue
                if word in beam["words"] and word not in ("the", "a", "of", "to", "and"):
                    continue
                pool_expansions.append({
                    "words": beam["words"] + [word],
                    "pos": beam["pos"] + [resolve_pos(word, allowed)],
                    "logp": beam["logp"] + math.log(p),
                })
                taken += 1

        # prune by mean log prob so long beams are not penalised into oblivion
        pool_expansions.sort(key=lambda b: -b["logp"] / max(1, len(b["words"])))
        live = pool_expansions[:BEAM_WIDTH]

    for beam in live:
        finished.append({**beam, "stop_p": None,
                         "score": beam["logp"] / max(1, len(beam["words"]))})

    # dedupe, keep the best-scoring version of each distinct sentence
    best: dict[str, dict] = {}
    for b in finished:
        s = " ".join(b["words"])
        if s and (s not in best or b["score"] > best[s]["score"]):
            best[s] = b
    ranked = sorted(best.values(), key=lambda b: -b["score"])[:12]
    return {"question": question,
            "candidates": [{"sentence": " ".join(b["words"]), "score": round(b["score"], 3)}
                           for b in ranked],
            "log": log}


GRADE_LEVELS = ["Wrong or meaningless.",
                "Related to the topic but does not answer it.",
                "Partly correct but incomplete or garbled.",
                "Correct but awkwardly worded.",
                "Correct and clearly worded."]


def grade_one(jev: Jev, question: str, answer: str) -> dict:
    g = jev.ask({"question": question, "answer": answer}, {
        "correct": {"type": "noul", "instructions": "Does `answer` correctly answer `question`?"},
        "readable": {"type": "noul", "instructions": "Is `answer` grammatical English that a "
                                                    "person would understand?"},
        "quality": {"type": "score", "instructions": "How good is `answer` as a reply to "
                                                    "`question`?", "criteria": GRADE_LEVELS},
    })
    return {"correct": g["answers"]["correct"]["noul"],
            "readable": g["answers"]["readable"]["noul"],
            "quality": g["answers"]["quality"]["score"]}


def select_by_choice(jev: Jev, question: str, sentences: list[str]) -> tuple[str, float]:
    """Relative selection: one Choice whose options are the candidate sentences."""
    r = jev.ask({"question": question, "candidate_answers": sentences}, {
        "best": {"type": "choice",
                 "instructions": {"question": "Which candidate answer best answers `question`?",
                                  "focus": "Judge correctness first, then clarity."},
                 "criteria": {s: None for s in sentences}},
    })
    a = r["answers"]["best"]
    return a["choice"], a["confidence"]


def select_by_nouls(jev: Jev, question: str, sentences: list[str]) -> tuple[str, dict]:
    """Absolute selection: two Nouls per candidate, ALL in one parallel request.

    A Choice forces probability mass onto some option even when every candidate is
    poor. Independent Nouls can be low for all of them, so the winner is scored on
    its own merits rather than merely beating its neighbours.
    """
    qs: dict[str, dict] = {}
    for i, s in enumerate(sentences):
        qs[f"c{i}"] = {"type": "noul",
                       "instructions": {"candidate": s,
                                        "question": "Does `candidate` correctly answer "
                                                    "`question`?"}}
        qs[f"r{i}"] = {"type": "noul",
                       "instructions": {"candidate": s,
                                        "question": "Is `candidate` grammatical English that a "
                                                    "person would understand?"}}
    r = jev.ask({"question": question}, qs)
    scored = {}
    for i, s in enumerate(sentences):
        c = r["answers"][f"c{i}"]["noul"]
        g = r["answers"][f"r{i}"]["noul"]
        scored[s] = {"correct": c, "readable": g, "product": round(c * g, 3)}
    winner = max(scored, key=lambda s: scored[s]["product"])
    return winner, scored


def pick_and_grade(jev: Jev, question: str, sentences: list[str],
                   logprob_best: str) -> dict:
    """Compare three selectors over the same finished beams."""
    ch_win, ch_conf = select_by_choice(jev, question, sentences)
    nl_win, nl_scores = select_by_nouls(jev, question, sentences)
    out = {"by_logprob": logprob_best, "by_choice": ch_win, "by_choice_conf": ch_conf,
           "by_nouls": nl_win, "noul_scores": nl_scores}
    for label, sent in (("logprob", logprob_best), ("choice", ch_win), ("nouls", nl_win)):
        out[f"grade_{label}"] = grade_one(jev, question, sent)
    return out


CASES = [
    ("How does a caterpillar become a butterfly?", "it changes inside a hard cocoon", 2.11),
    ("Why do leaves change colour in autumn?", "the tree stops making green", 2.16),
    ("Why is the sky blue?", "the air scatters blue light", 3.16),
]


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    jev, t0, runs = Jev(), time.time(), []
    print(stats())
    print(f"beam width {BEAM_WIDTH}, {EXPANSIONS} expansions/beam, max {MAX_WORDS} words, "
          f"shards <={SHARD_MAX}, top {ADVANCE:.0%} advance\n")

    for question, reference, greedy_mean in CASES:
        res = search(jev, question)
        sents = [c["sentence"] for c in res["candidates"]]
        res["result"] = (pick_and_grade(jev, question, sents, sents[0])
                         if sents else {})
        res["reference"], res["greedy_mean_quality"] = reference, greedy_mean
        runs.append(res)

        print(f"Q: {question}")
        print(f"   reference: {reference!r}")
        print(f"   {len(sents)} finished beams, best {min(6, len(sents))} by mean log-prob:")
        for c in res["candidates"][:6]:
            print(f"     {c['score']:+.3f}  {c['sentence']!r}")
        w = res["result"]
        for label, key in (("log-prob top", "by_logprob"), ("Jev Choice ", "by_choice"),
                           ("Jev Nouls  ", "by_nouls")):
            g = w[f"grade_{label.split()[-1].strip().lower().replace('-','')}"] \
                if False else w["grade_" + {"by_logprob": "logprob", "by_choice": "choice",
                                            "by_nouls": "nouls"}[key]]
            print(f"   {label}: {w[key]!r:48} correct={g['correct']:.2f} "
                  f"readable={g['readable']:.2f} quality={g['quality']:.2f}/4")
        print(f"   (greedy baseline {greedy_mean:.2f}/4)\n")

    print("=" * 84)
    print(f"{'question':40}{'greedy':>8}{'logprob':>9}{'choice':>8}{'nouls':>8}")
    agg = {"logprob": [], "choice": [], "nouls": []}
    for r in runs:
        q = {k: r["result"][f"grade_{k}"]["quality"] for k in agg}
        for k in agg:
            agg[k].append(q[k])
        print(f"{r['question'][:39]:40}{r['greedy_mean_quality']:>8.2f}"
              f"{q['logprob']:>9.2f}{q['choice']:>8.2f}{q['nouls']:>8.2f}")
    print(f"{'MEAN':40}{sum(x['greedy_mean_quality'] for x in runs)/len(runs):>8.2f}"
          + "".join(f"{sum(v)/len(v):>9.2f}" if k == "logprob" else f"{sum(v)/len(v):>8.2f}"
                    for k, v in agg.items()))

    out = {"runs": runs, "beam_width": BEAM_WIDTH, "requests": jev.requests,
           "cost_usd": jev.cost, "seconds": round(time.time() - t0, 1), "model": jev.model_seen}
    (RESULTS / "beam.json").write_text(json.dumps(out, indent=2))
    print(f"\n{jev.requests} requests, {out['seconds']}s, ${jev.cost:.5f}")


if __name__ == "__main__":
    main()
