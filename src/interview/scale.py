"""Two questions about the fragments method, measured.

A. VOCABULARY SIZE. Does giving Jev 4x or 10x more phrases to choose from help?
   Pools past 253 go through the sharded tournament (all shards in one parallel
   request, top 25% advance, runoff). 1x was the interview setup at the time; the
   outcome (4x + the "say more" prompt) is now the default in speak.py, which this
   script calls.

B. ANSWER LENGTH. Can it be pushed to say more? Three levers, none of which let a
   human write the answer:
     - a MIN_PARTS floor: STOP is simply withheld from the option list until the
       answer has N parts, so it must keep choosing content
     - a "say more" prompt: instructions ask for a full, developed answer
     - continuation prompt: after it stops, ask "what would you add?" and append

Every answer graded by Jev on coherence and readability, plus a Noul asking whether the
extra length actually added information rather than padding.

Usage:  python3 -m src.interview.scale
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from src.interview.beam import MISSING, STOP, grade_one  # noqa: E402
from src.interview.client import Jev  # noqa: E402
from src.interview.fragment_bank import bank  # noqa: E402
from src.interview.speak import BASE_FOCUS, LONG_FOCUS, next_phrase  # noqa: E402
from src.interview.speak import compose as _compose  # noqa: E402

RESULTS = pathlib.Path(__file__).resolve().parents[2] / "results"

QUESTIONS = [
    "Is being unable to speak a strength or a weakness for such a model?",
    "Who is responsible when such a model answers badly?",
    "What is the biggest risk of artificial intelligence?",
    "Is cheaper intelligence a saving or an illusion?",
    "What do people get wrong about machines?",
    "Will machines replace human workers?",
]

def compose(jev: Jev, q: str, pool: list[str], focus: str = BASE_FOCUS,
            min_parts: int = 0, max_parts: int = 6) -> dict:
    """The experiment's arms, expressed through speak.compose."""
    res = _compose(jev, {"question": q}, "question", pool, focus=focus,
                   min_parts=min_parts, max_parts=max_parts)
    return {"answer": res["answer"], "n_parts": len(res["parts"]), "ended": res["ended_by"],
            "requests": res["requests"]}


def continuation(jev: Jev, q: str, pool: list[str], first: str) -> dict:
    """After a natural stop, ask what it would add, once."""
    avail = [p for p in pool if p not in first.split()]
    state = {"question": q, "answer_so_far": first}
    step = next_phrase(
        jev, state, "question", avail,
        "The answer so far is complete. Which phrase would you ADD to make it fuller? "
        "Choose STOP if nothing would improve it.", allow_stop=True)
    pick, n = step["pick"], step["requests"]
    if pick in (STOP, MISSING):
        return {"answer": first, "added": None, "requests": n}
    return {"answer": f"{first} {pick}", "added": pick, "requests": n}


def grade_length(jev: Jev, q: str, short: str, long: str) -> dict:
    """Did the longer answer add information, or just words?"""
    r = jev.ask({"question": q, "short_answer": short, "long_answer": long}, {
        "adds_info": {"type": "noul",
                      "instructions": "Does `long_answer` contain a substantive point that "
                                      "`short_answer` lacks?"},
        "padding": {"type": "noul",
                    "instructions": "Is the extra material in `long_answer` mostly filler "
                                    "or repetition?"},
        "prefer_long": {"type": "noul",
                        "instructions": "Would a careful reader prefer `long_answer` over "
                                        "`short_answer` as a reply to `question`?"},
    })
    return {k: r["answers"][k]["noul"] for k in ("adds_info", "padding", "prefer_long")}


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    jev, t0 = Jev(), time.time()
    only_b = "--length-only" in sys.argv
    prior = (json.loads((RESULTS / "scale.json").read_text())
             if only_b and (RESULTS / "scale.json").exists() else {})
    out: dict = {"vocab": prior.get("vocab", []), "length": []}
    pools = {m: bank(m) for m in (1, 4, 10)}

    # ---------------------------------------------------------------- A: vocabulary
    if only_b:
        print(f"(skipping part A; {len(out['vocab'])} prior rows kept)")
    else:
        run_vocab(jev, pools, out)

    run_length(jev, pools[1], out)

    out.update(requests=jev.requests, cost_usd=jev.cost, seconds=round(time.time() - t0, 1))
    (RESULTS / "scale.json").write_text(json.dumps(out, indent=2))
    print(f"\n{jev.requests} requests, {out['seconds']}s, ${jev.cost:.5f}")


def run_vocab(jev: Jev, pools: dict, out: dict) -> None:
    print("=" * 96)
    print("A. VOCABULARY SIZE  (1x = current interview; 4x and 10x via sharded tournament)")
    print("=" * 96)
    for m, pl in pools.items():
        print(f"  {m:>2}x = {len(pl)} phrases")
    agg = {m: {"q": [], "c": [], "r": [], "parts": [], "req": []} for m in pools}
    for q in QUESTIONS:
        print(f"\nQ: {q}")
        for m, pl in pools.items():
            res = compose(jev, q, pl)
            g = grade_one(jev, q, res["answer"] or "(no answer)")
            agg[m]["q"].append(g["quality"]); agg[m]["c"].append(g["correct"])
            agg[m]["r"].append(g["readable"]); agg[m]["parts"].append(res["n_parts"])
            agg[m]["req"].append(res["requests"])
            out["vocab"].append({"question": q, "mult": m, **res, "grade": g})
            print(f"   {m:>2}x  {res['answer']!r:60} q={g['quality']:.2f} "
                  f"c={g['correct']:.2f} r={g['readable']:.2f} [{res['requests']} req]")
    print(f"\n{'vocab':>7}{'quality':>9}{'coherent':>10}{'readable':>10}{'parts':>7}{'req':>6}")
    for m, a in agg.items():
        n = len(a["q"])
        print(f"{m:>6}x{sum(a['q'])/n:>9.2f}{sum(a['c'])/n:>10.2f}{sum(a['r'])/n:>10.2f}"
              f"{sum(a['parts'])/n:>7.1f}{sum(a['req'])/n:>6.1f}")


def run_length(jev: Jev, pool: list[str], out: dict) -> None:
    print("\n" + "=" * 96)
    print("B. ANSWER LENGTH  (1x vocabulary; three ways to push for more)")
    print("=" * 96)
    lagg = {k: {"parts": [], "q": [], "r": [], "adds": [], "pad": [], "prefer": []}
            for k in ("baseline", "floor3", "prompt", "continue")}
    for q in QUESTIONS:
        base = compose(jev, q, pool)
        floor = compose(jev, q, pool, min_parts=3)
        prompt = compose(jev, q, pool, focus=LONG_FOCUS)
        cont = continuation(jev, q, pool, base["answer"])
        rows = {"baseline": base["answer"], "floor3": floor["answer"],
                "prompt": prompt["answer"], "continue": cont["answer"]}
        print(f"\nQ: {q}")
        for k, ans in rows.items():
            g = grade_one(jev, q, ans or "(no answer)")
            lagg[k]["parts"].append(len(ans.split(" ")) if ans else 0)
            lagg[k]["q"].append(g["quality"]); lagg[k]["r"].append(g["readable"])
            line = f"   {k:9} {ans!r:66} q={g['quality']:.2f} r={g['readable']:.2f}"
            if k != "baseline" and ans != base["answer"]:
                lg = grade_length(jev, q, base["answer"], ans)
                lagg[k]["adds"].append(lg["adds_info"]); lagg[k]["pad"].append(lg["padding"])
                lagg[k]["prefer"].append(lg["prefer_long"])
                line += (f"  adds={lg['adds_info']:.2f} pad={lg['padding']:.2f} "
                         f"prefer={lg['prefer_long']:.2f}")
            print(line)
            out["length"].append({"question": q, "method": k, "answer": ans, "grade": g})
    print(f"\n{'method':>10}{'words':>7}{'quality':>9}{'readable':>10}{'adds info':>11}"
          f"{'padding':>9}{'prefer':>8}")
    for k, a in lagg.items():
        n = len(a["q"])
        extra = ("" if not a["adds"] else
                 f"{sum(a['adds'])/len(a['adds']):>11.2f}{sum(a['pad'])/len(a['pad']):>9.2f}"
                 f"{sum(a['prefer'])/len(a['prefer']):>8.2f}")
        print(f"{k:>10}{sum(a['parts'])/n:>7.1f}{sum(a['q'])/n:>9.2f}{sum(a['r'])/n:>10.2f}{extra}")


if __name__ == "__main__":
    main()
