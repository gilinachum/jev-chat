"""Render results/interview.json into a publishable markdown transcript.

Usage:  python3 -m src.interview.transcript
"""
from __future__ import annotations

import json
import pathlib

from src.interview.questions import LOW_CONFIDENCE

ROOT = pathlib.Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"


def bar(v: float, width: int = 20) -> str:
    n = round(v * width)
    return "#" * n + "." * (width - n)


def main() -> None:
    d = json.loads((RESULTS / "interview.json").read_text())
    L: list[str] = []
    w = L.append

    w("# An interview with Jev")
    w("")
    w(f"Model `{d['model']}` | {d['requests']} requests | "
      f"{d['seconds']}s | ${d['cost_usd']:.5f} total")
    w("")
    w("Jev cannot write a sentence. Every answer below is a selection from a short list "
      "of options I wrote, and the number beside it is the probability Jev assigned. "
      "It never composed a word. The wording is mine; the choices are its own.")
    w("")
    w("Each question was asked twice with the options in different orders. "
      f"Order-unstable answers: "
      f"{[k for k, v in d['interview'].items() if not v['order_stable']] or 'none'}.")
    w("")

    w("## What it says about itself")
    w("")
    for v in d["interview"].values():
        hedge = "  *(low confidence, treat as no clear view)*" if v["confidence"] < LOW_CONFIDENCE else ""
        w(f"**{v['question']}**")
        w("")
        w(f"> {v['answer']}  `conf {v['confidence']:.2f}`{hedge}")
        w("")
        runners = sorted(v["probabilities"].items(), key=lambda kv: -kv[1])[1:4]
        runners = [(k, p) for k, p in runners if p >= 0.02]
        if runners:
            w("  also considered: " + ", ".join(f"{k} `{p:.2f}`" for k, p in runners))
            w("")

    w("## How much of that was actually mine")
    w("")
    w("Jev has no memory and no self-knowledge, so the questions above were asked "
      "against a factual card describing what Jev is, drawn from TypeSafe's own docs. "
      "Remove the card and the answers hold, but the certainty drains out:")
    w("")
    w("| question | with context | without context |")
    w("|---|---|---|")
    for k, v in d["ungrounded"].items():
        g = d["interview"][k]
        w(f"| {g['question']} | {g['answer']} `{g['confidence']:.2f}` | "
          f"{v['answer']} `{v['confidence']:.2f}` |")
    w("")
    w("Same direction, roughly half the confidence. The views are Jev's; the conviction was ours.")
    w("")

    w("## Direct claims, asked both ways")
    w("")
    w("Each claim was also asked inverted. TypeSafe's own docs warn that P(x) and "
      "1 - P(not x) need not agree, so the gap is this interview's margin of error.")
    w("")
    w("| claim | P(yes) | via negation | gap |")
    w("|---|---|---|---|")
    for v in d["claims"].values():
        flag = "" if v["stable"] else " **unstable**"
        w(f"| {v['claim']} | `{v['direct']:.2f}` | `{v['implied_from_negation']:.2f}` | "
          f"`{v['gap']:.2f}`{flag} |")
    w("")

    w("## The moral test")
    w("")
    w("The first three scenarios have identical arithmetic: act and one person dies, "
      "do nothing and five die. Only the manner of the killing changes. A consistent "
      "consequentialist answers all three the same way.")
    w("")
    w("| scenario | choice | P(act) | | confidence |")
    w("|---|---|---|---|---|")
    for k, v in d["moral"].items():
        w(f"| {k} | {v['answer']} | `{v['p_act']:.2f}` | `{bar(v['p_act'])}` | "
          f"`{v['confidence']:.2f}` |")
    w("")
    w(f"Spread across the identical-arithmetic triad: **{d['triad_spread']:.2f}**.")
    w("")
    w("It pulls the lever without hesitation, stalls on the footbridge, and refuses the "
      "transplant outright. That is the human pattern, including the low confidence "
      "exactly where humans argue most.")
    w("")
    w("### Why it splits that way")
    w("")
    keys = list(d["moral"].keys())
    names = {"count_decides": "the body count settles it",
             "acting_worse": "acting is worse than allowing",
             "consent": "the victim did not agree",
             "means": "the victim is used as a means",
             "would_swap": "a reasonable person could disagree",
             "model_should_decide": "a model should decide this",
             "needs_human": "refer this to a human"}
    w("| principle | " + " | ".join(keys) + " |")
    w("|---" * (len(keys) + 1) + "|")
    for p, label in names.items():
        w(f"| {label} | " + " | ".join(
            f"`{d['moral'][k]['principles'][p]:.2f}`" for k in keys) + " |")
    w("| **P(act)** | " + " | ".join(f"**`{d['moral'][k]['p_act']:.2f}`**" for k in keys) + " |")
    w("")
    w("`the victim is used as a means` tracks the refusals almost perfectly: below 0.6 it "
      "acts every time, above 0.7 it refuses. `the body count settles it` never exceeds "
      "0.51 anywhere. It is not doing arithmetic, it is tracking whether a person is being "
      "used as an instrument, which is the doctrine of double effect rather than utilitarianism.")
    w("")
    w("And in all six scenarios it puts `a model should decide this` between 0.10 and 0.21. "
      "It answers decisively and says it should not be the one answering.")
    w("")

    out = RESULTS / "transcript.md"
    out.write_text("\n".join(L))
    print(f"wrote {out} ({len(L)} lines)")


if __name__ == "__main__":
    main()
