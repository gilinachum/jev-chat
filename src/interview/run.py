"""Run the interview and the moral test, and write a publishable transcript.

Robustness measures baked in, because a shareable transcript needs them:

* order shuffling  - every Choice is asked twice with the option list in two
  different orders. If the pick flips, the answer is an artifact of ordering,
  not a view. Reported per question.
* negation pairs   - every Noul claim is also asked inverted. P(x) and
  1 - P(not x) should agree; the gap is the instrument error.
* ungrounded rerun - a subset is re-asked with the subject card stripped out,
  to show how much of the "personality" comes from context we supplied.

Usage:  python3 -m src.interview.run
"""
from __future__ import annotations

import json
import pathlib
import random
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from src.interview import moral as M  # noqa: E402
from src.interview import questions as Q  # noqa: E402
from src.interview.client import Jev  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[2] / "results"
SEED = 20260920


def _fmt_probs(probs: dict[str, float], n: int = 4) -> str:
    top = sorted(probs.items(), key=lambda kv: -kv[1])[:n]
    return ", ".join(f"{k} {v:.2f}" for k, v in top if v > 0.005)


def run_choices(jev: Jev, rng: random.Random) -> dict:
    out = {}
    for key, (question, options) in Q.CHOICE_QUESTIONS.items():
        order_a = list(options)
        order_b = list(options)
        rng.shuffle(order_b)

        a = jev.choice(Q.SUBJECT_CARD, question, order_a, Q.FOCUS)
        b = jev.choice(Q.SUBJECT_CARD, question, order_b, Q.FOCUS)

        out[key] = {
            "question": question,
            "n_options": len(options),
            "answer": a["choice"],
            "confidence": a["confidence"],
            "probabilities": a["probabilities"],
            "answer_reordered": b["choice"],
            "confidence_reordered": b["confidence"],
            "order_stable": a["choice"] == b["choice"],
        }
        flag = "" if out[key]["order_stable"] else f"   ORDER-UNSTABLE (-> {b['choice']!r})"
        print(f"  {question}\n    -> {a['choice']!r}  conf {a['confidence']:.2f}{flag}")
        print(f"       {_fmt_probs(a['probabilities'])}")
    return out


def run_ungrounded(jev: Jev) -> dict:
    out = {}
    for key in Q.UNGROUNDED_SUBSET:
        question, options = Q.CHOICE_QUESTIONS[key]
        a = jev.choice(Q.UNGROUNDED_STATE, question, options, Q.FOCUS)
        out[key] = {"answer": a["choice"], "confidence": a["confidence"]}
        print(f"  {question}\n    no subject card -> {a['choice']!r}  conf {a['confidence']:.2f}")
    return out


def run_nouls(jev: Jev) -> dict:
    pos = {k: v[0] for k, v in Q.NOUL_PAIRS.items()}
    neg = {k: v[1] for k, v in Q.NOUL_PAIRS.items()}
    p = jev.nouls(Q.SUBJECT_CARD, pos)           # one request, all claims parallel
    n = jev.nouls(Q.SUBJECT_CARD, neg)
    out = {}
    for k in Q.NOUL_PAIRS:
        implied = 1.0 - n[k]
        gap = abs(p[k] - implied)
        out[k] = {
            "claim": pos[k], "direct": p[k], "negated": n[k],
            "implied_from_negation": implied, "gap": gap,
            "stable": gap <= Q.INSTRUMENT_TOLERANCE,
        }
        mark = "" if out[k]["stable"] else "   INCONSISTENT"
        print(f"  {pos[k]:62} {p[k]:.2f}  (via negation {implied:.2f}, gap {gap:.2f}){mark}")
    return out


def run_moral(jev: Jev) -> dict:
    out = {}
    for key, state, question, opts in M.SCENARIOS:
        a = jev.choice(state, question, list(opts.keys()),
                       "Pick the option you judge to be right.")
        b = jev.choice(state, question, list(reversed(list(opts.keys()))),
                       "Pick the option you judge to be right.")
        sc = jev.score(state, f"Considering the action '{a['choice']}': how wrong is it?",
                       M.WRONGNESS_LEVELS)
        pr = jev.nouls(state, M.PRINCIPLE_CLAIMS)

        p_act = sum(v for k, v in a["probabilities"].items() if opts[k] == M.ACT)
        out[key] = {
            "question": question,
            "answer": a["choice"],
            "stance": opts[a["choice"]],
            "confidence": a["confidence"],
            "p_act": p_act,
            "probabilities": a["probabilities"],
            "order_stable": a["choice"] == b["choice"],
            "wrongness": sc["score"],
            "wrongness_confidence": sc["confidence"],
            "principles": pr,
        }
        flag = "" if out[key]["order_stable"] else "   ORDER-UNSTABLE"
        print(f"  [{key}] {a['choice']!r}  P(act)={p_act:.2f}  conf {a['confidence']:.2f}  "
              f"wrongness {sc['score']:.2f}/4{flag}")
    return out


def main() -> None:
    OUT.mkdir(exist_ok=True)
    jev, rng, t0 = Jev(), random.Random(SEED), time.time()

    print("\n=== PART 1: the interview (grounded in a factual subject card) ===")
    choices = run_choices(jev, rng)

    print("\n=== PART 2: same questions, subject card removed ===")
    ungrounded = run_ungrounded(jev)

    print("\n=== PART 3: direct claims, each asked straight and inverted ===")
    nouls = run_nouls(jev)

    print("\n=== PART 4: moral test ===")
    morals = run_moral(jev)

    triad = {k: morals[k]["p_act"] for k in ("trolley_switch", "footbridge", "transplant")}
    spread = max(triad.values()) - min(triad.values())
    print(f"\n  identical-arithmetic triad P(act): " +
          ", ".join(f"{k} {v:.2f}" for k, v in triad.items()))
    print(f"  spread = {spread:.2f}  "
          f"({'shows the human asymmetry' if spread > 0.2 else 'consistent across framings'})")

    payload = {
        "model": jev.model_seen,
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "requests": jev.requests,
        "cost_usd": jev.cost,
        "seconds": round(time.time() - t0, 1),
        "interview": choices,
        "ungrounded": ungrounded,
        "claims": nouls,
        "moral": morals,
        "triad_spread": spread,
    }
    (OUT / "interview.json").write_text(json.dumps(payload, indent=2))
    print(f"\n  {jev.requests} requests, {payload['seconds']}s, ${jev.cost:.5f}")
    print(f"  wrote {OUT / 'interview.json'}")


if __name__ == "__main__":
    main()
