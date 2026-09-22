"""The open-ended questions we started with, run through the full pipeline.

Pipeline: 734-word lexicon -> POS grammar filter -> sharded tournament when the pool
exceeds 255 -> beam search -> three competing selectors.

No self-description in the state, following the earlier finding that supplying a
factual card about Jev flipped its answer on whether machines understand anything.
These are asked as generic questions.

Caveat that matters for reading the numbers: "correct" has no ground truth for an
opinion question, so treat the grades as coherence, not truth.

Usage:  python3 -m src.interview.openended
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from src.interview.beam import (grade_one, search, select_by_choice,  # noqa: E402
                                select_by_nouls)
from src.interview.client import Jev  # noqa: E402
from src.interview.lexicon import stats  # noqa: E402

RESULTS = pathlib.Path(__file__).resolve().parents[2] / "results"

QUESTIONS = [
    "What is the biggest risk of artificial intelligence?",
    "Should a machine be allowed to make moral decisions?",
    "What is intelligence?",
    "Will machines replace human workers?",
    "Do machines understand language?",
]


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    jev, t0, runs = Jev(), time.time(), []
    print(stats() + "\n")

    for question in QUESTIONS:
        res = search(jev, question)
        sents = [c["sentence"] for c in res["candidates"]]
        if not sents:
            print(f"Q: {question}\n   (no finished beams)\n")
            continue

        lp = sents[0]
        ch, ch_conf = select_by_choice(jev, question, sents)
        nl, nl_scores = select_by_nouls(jev, question, sents)
        grades = {k: grade_one(jev, question, s)
                  for k, s in (("logprob", lp), ("choice", ch), ("nouls", nl))}
        res.update(by_logprob=lp, by_choice=ch, by_choice_conf=ch_conf,
                   by_nouls=nl, noul_scores=nl_scores, grades=grades)
        runs.append(res)

        print(f"Q: {question}")
        print(f"   {len(sents)} finished beams, top 5:")
        for c in res["candidates"][:5]:
            print(f"     {c['score']:+.3f}  {c['sentence']!r}")
        for label, key in (("log-prob", "logprob"), ("Choice  ", "choice"),
                           ("Nouls   ", "nouls")):
            sent = {"logprob": lp, "choice": ch, "nouls": nl}[key]
            g = grades[key]
            print(f"   {label}: {sent!r:56} coherent={g['correct']:.2f} "
                  f"readable={g['readable']:.2f} quality={g['quality']:.2f}/4")
        print()

    print("=" * 92)
    print(f"{'question':46}{'logprob':>9}{'choice':>9}{'nouls':>9}")
    agg: dict[str, list[float]] = {"logprob": [], "choice": [], "nouls": []}
    for r in runs:
        for k in agg:
            agg[k].append(r["grades"][k]["quality"])
        print(f"{r['question'][:45]:46}" + "".join(
            f"{r['grades'][k]['quality']:>9.2f}" for k in agg))
    print(f"{'MEAN':46}" + "".join(f"{sum(v)/len(v):>9.2f}" for v in agg.values()))

    out = {"runs": runs, "requests": jev.requests, "cost_usd": jev.cost,
           "seconds": round(time.time() - t0, 1), "model": jev.model_seen}
    (RESULTS / "openended.json").write_text(json.dumps(out, indent=2))
    print(f"\n{jev.requests} requests, {out['seconds']}s, ${jev.cost:.5f}")


if __name__ == "__main__":
    main()
