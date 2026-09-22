"""Six ways to squeeze more language out of Jev, measured against one baseline.

All six share the same premise that has worked every time in this project: convert
GENERATION into JUDGMENT, because judging supplied text is the only thing Jev is
reliably good at.

  baseline    greedy word-by-word over the grammar-filtered pool (current best simple)
  fragments   options are multi-word PHRASES carrying their own internal grammar, so
              Jev never has to assemble function words at all
  repair      draft freely, then code proposes single-word edits and Jev judges each
              with a Noul -- editing is judgment, not generation
  slots       one request asking subject / verb / object / modifier as INDEPENDENT
              parallel questions; code assembles. No sequential compounding at all
  consistency run the baseline N times and keep the answer that recurs
  cloze       Jev picks a sentence TEMPLATE, then fills its holes in parallel. Filling
              a gap in a complete sentence is a judgment about that sentence

Excluded from scoring: "confidence trace as voice" is a presentation format, not a
generation method, so it is demonstrated separately at the end rather than graded.

Usage:  python3 -m src.interview.methods
"""
from __future__ import annotations

import collections
import json
import math
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from src.interview.beam import (MISSING, STOP, distribution, grade_one,  # noqa: E402
                                select_by_nouls)
from src.interview.client import Jev  # noqa: E402
from src.interview.lexicon import LEX, candidates, resolve_pos  # noqa: E402

RESULTS = pathlib.Path(__file__).resolve().parents[2] / "results"

CLOSED = [
    "Why is the sky blue?",
    "What happens to water when it freezes?",
    "How does a caterpillar become a butterfly?",
    "Why do birds build nests?",
    "What do bees make?",
]
OPEN = [
    "What is intelligence?",
    "Will machines replace human workers?",
    "Should a machine be allowed to make moral decisions?",
    "Do machines understand language?",
    "What is the biggest risk of artificial intelligence?",
]

MAX_WORDS = 8


# --------------------------------------------------------------------- baseline
def m_baseline(jev: Jev, q: str) -> dict:
    words: list[str] = []
    pos: list[str] = []
    for _ in range(MAX_WORDS):
        pool, allowed = candidates(pos[-1] if pos else None)
        state = {"factual_question": q, "words_so_far": " ".join(words)}
        probs, _ = distribution(jev, state, pool)
        pick = max(probs, key=probs.get)
        if pick in (STOP, MISSING):
            break
        if pick in words and pick not in ("the", "a", "of", "to", "and"):
            probs.pop(pick)
            pick = max(probs, key=probs.get)
            if pick in (STOP, MISSING):
                break
        words.append(pick)
        pos.append(resolve_pos(pick, allowed))
    return {"answer": " ".join(words)}


# -------------------------------------------------------------------- fragments
FRAGMENTS = [
    # openers / stance
    "yes", "no", "sometimes", "it depends", "not really", "usually", "rarely",
    "always", "never", "probably", "probably not", "in part", "mostly",
    # subjects
    "it is", "they are", "the answer is", "the reason is", "this is", "that is",
    "the model is", "a machine is", "machines are", "people are", "humans are",
    "the sun is", "the air is", "the sky is", "water is", "ice is",
    "a caterpillar", "a butterfly", "a bird", "a bee", "a spider", "the tree",
    "the leaves", "the light", "the heat", "the cost", "the risk", "the danger",
    "intelligence is", "understanding is", "language is", "judgment is",
    # because-clauses
    "because it", "because they", "because the air", "because the sun",
    "because the light", "because the heat", "because the cost", "because people",
    "because machines", "because it cannot", "because they cannot",
    "because there is no", "because nobody",
    # verb phrases
    "scatters", "reflects", "absorbs", "turns into", "changes into", "becomes",
    "grows into", "melts into", "freezes into", "carries", "collects", "catches",
    "traps", "builds", "protects", "holds", "keeps warm", "lays eggs", "makes honey",
    "breathes through gills", "spins a web", "needs", "uses", "replaces", "creates",
    "destroys", "improves", "reduces", "raises", "hides", "depends on",
    "cannot explain", "cannot reason", "cannot be trusted", "can be useful",
    "does not understand", "does understand", "only predicts", "only measures",
    "merely matches patterns", "makes mistakes", "saves money", "costs more",
    # objects / complements
    "blue light", "sunlight", "the light", "a cocoon", "a hard shell", "its eggs",
    "its young", "pollen", "honey", "insects", "food", "water", "warm air",
    "the whole truth", "some jobs", "new jobs", "new roles", "many jobs",
    "human work", "human judgment", "real understanding", "the meaning",
    "the context", "the question", "good judgment", "fast judgment",
    "calibrated probability", "too much power", "too much trust", "bad decisions",
    "more demand", "more spending", "less cost", "great harm", "little harm",
    "a mistake", "a risk", "a danger",
    # connectors / tails
    "and then", "but not", "but also", "and also", "without reason",
    "without understanding", "in the end", "for now", "over time", "at scale",
    "in most cases", "in some cases", "if used carefully", "if trusted blindly",
    "more than people think", "less than people think",
]
assert len(FRAGMENTS) + 2 <= 255, len(FRAGMENTS) + 2

_FRAG_CONTROL = {
    STOP: {"what": "The phrases already chosen form a correct answer a human reader "
                   "would understand. Nothing further is needed.",
           "not_for": "An answer that is still incomplete or unclear."},
    MISSING: {"what": "The phrase you want next is not present in this list.",
              "not_for": "A phrase that is present, even if not your first preference."},
}


def m_fragments(jev: Jev, q: str, max_parts: int = 4) -> dict:
    parts: list[str] = []
    for _ in range(max_parts):
        opts: dict[str, object] = {f: None for f in FRAGMENTS if f not in parts}
        opts.update(_FRAG_CONTROL)
        r = jev.ask({"question": q, "answer_so_far": " ".join(parts)}, {"p": {
            "type": "choice",
            "instructions": {
                "question": "Which phrase should come next in `answer_so_far` so it "
                            "becomes a correct answer to `question`?",
                "focus": "Each option is a complete phrase. Choose on meaning.",
            },
            "criteria": opts}})
        pick = r["answers"]["p"]["choice"]
        if pick in (STOP, MISSING):
            break
        parts.append(pick)
    return {"answer": " ".join(parts)}


# ----------------------------------------------------------------------- repair
INSERTS = ["it", "the", "a", "is", "are", "to", "of", "in", "and", "its", "they",
           "that", "does", "can"]


def m_repair(jev: Jev, q: str, rounds: int = 3) -> dict:
    cur = m_baseline(jev, q)["answer"]
    history = [cur]
    for _ in range(rounds):
        toks = cur.split()
        cands: list[str] = []
        for i in range(len(toks) + 1):
            for w in INSERTS:
                c = " ".join(toks[:i] + [w] + toks[i:])
                if c not in cands:
                    cands.append(c)
        cands = cands[:40]
        if not cands:
            break
        qs = {f"e{i}": {"type": "noul",
                        "instructions": {"edited": c, "current": cur,
                                         "question": "Is `edited` better English than "
                                                     "`current` while still answering "
                                                     "`question`?"}}
              for i, c in enumerate(cands)}
        r = jev.ask({"question": q}, qs)
        scored = [(r["answers"][f"e{i}"]["noul"], c) for i, c in enumerate(cands)]
        best_p, best = max(scored)
        if best_p <= 0.55 or best == cur:
            break
        cur = best
        history.append(cur)
    return {"answer": cur, "history": history}


# ------------------------------------------------------------------------ slots
SUBJECTS = ["it", "they", "the model", "a machine", "machines", "people", "humans",
            "the answer", "the reason", "the air", "the sun", "the sky", "water",
            "a caterpillar", "a bird", "a bee", "intelligence", "understanding",
            "language", "some jobs", "the risk", "the cost", "nobody", "everything"]
MODIFIERS = ["", "usually", "sometimes", "never", "always", "only", "mostly",
             "in most cases", "over time", "at scale"]


def m_slots(jev: Jev, q: str) -> dict:
    """One request: four independent slot questions evaluated in parallel."""
    r = jev.ask({"question": q}, {
        "subject": {"type": "choice",
                    "instructions": "Which subject should the answer to `question` be about?",
                    "criteria": {s: None for s in SUBJECTS}},
        "verb": {"type": "choice",
                 "instructions": "Which verb best states what the answer to `question` says?",
                 "criteria": {v: None for v in LEX["VERB_3SG"][:120]}},
        "object": {"type": "choice",
                   "instructions": "Which word best completes the answer to `question`?",
                   "criteria": {o: None for o in
                                (LEX["NOUN_MASS"] + LEX["ADJ"])[:150]}},
        "modifier": {"type": "choice",
                     "instructions": "Which qualifier, if any, belongs in the answer to "
                                     "`question`? Choose the empty option for none.",
                     "criteria": {m or "(none)": None for m in MODIFIERS}},
    })
    a = {k: r["answers"][k]["choice"] for k in ("subject", "verb", "object", "modifier")}
    mod = "" if a["modifier"] == "(none)" else a["modifier"] + " "
    return {"answer": f"{a['subject']} {mod}{a['verb']} {a['object']}".strip(),
            "slots": a}


# ------------------------------------------------------------------ consistency
def m_consistency(jev: Jev, q: str, n: int = 3) -> dict:
    runs = [m_baseline(jev, q)["answer"] for _ in range(n)]
    counts = collections.Counter(runs)
    top, freq = counts.most_common(1)[0]
    if freq > 1:
        return {"answer": top, "samples": runs, "resolved_by": f"majority {freq}/{n}"}
    winner, _ = select_by_nouls(jev, q, list(dict.fromkeys(runs)))
    return {"answer": winner, "samples": runs, "resolved_by": "noul tiebreak"}


# ------------------------------------------------------------------------ cloze
TEMPLATES = [
    "<S> is <O>",
    "<S> <V> <O>",
    "because <S> <V> <O>",
    "yes, because <S> <V> <O>",
    "no, because <S> <V> <O>",
    "it depends on <O>",
    "<S> <V> <O> but not <O2>",
    "sometimes, when <S> <V> <O>",
    "no, <S> only <V> <O>",
    "<S> <V> <O> over time",
]


def m_cloze(jev: Jev, q: str) -> dict:
    r = jev.ask({"question": q}, {"t": {
        "type": "choice",
        "instructions": {"question": "Which sentence shape best fits a correct answer to "
                                     "`question`?",
                         "focus": "<S> is a subject, <V> a verb, <O> a completion."},
        "criteria": {t: None for t in TEMPLATES}}})
    tmpl = r["answers"]["t"]["choice"]

    need = {s for s in ("<S>", "<V>", "<O>", "<O2>") if s in tmpl}
    qs: dict[str, dict] = {}
    if "<S>" in need:
        qs["S"] = {"type": "choice",
                   "instructions": {"sentence_shape": tmpl,
                                    "question": "Which subject fills <S> so the shape "
                                                "answers `question`?"},
                   "criteria": {s: None for s in SUBJECTS}}
    if "<V>" in need:
        qs["V"] = {"type": "choice",
                   "instructions": {"sentence_shape": tmpl,
                                    "question": "Which verb fills <V> so the shape "
                                                "answers `question`?"},
                   "criteria": {v: None for v in LEX["VERB_3SG"][:120]}}
    for slot in ("<O>", "<O2>"):
        if slot in need:
            qs[slot.strip("<>")] = {
                "type": "choice",
                "instructions": {"sentence_shape": tmpl,
                                 "question": f"Which word fills {slot} so the shape "
                                             f"answers `question`?"},
                "criteria": {o: None for o in (LEX["NOUN_MASS"] + LEX["ADJ"])[:150]}}
    r2 = jev.ask({"question": q}, qs)
    out = tmpl
    for key, ans in r2["answers"].items():
        out = out.replace(f"<{key}>", ans["choice"])
    return {"answer": out, "template": tmpl}


METHODS = {
    "baseline": m_baseline,
    "fragments": m_fragments,
    "repair": m_repair,
    "slots": m_slots,
    "consistency": m_consistency,
    "cloze": m_cloze,
}


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    jev, t0 = Jev(), time.time()
    table: dict[str, dict[str, list[float]]] = {m: {"closed": [], "open": []}
                                                for m in METHODS}
    detail: list[dict] = []

    for label, qs in (("closed", CLOSED), ("open", OPEN)):
        print("\n" + "=" * 94)
        print(f"{label.upper()}-ENDED QUESTIONS")
        print("=" * 94)
        for q in qs:
            print(f"\nQ: {q}")
            for name, fn in METHODS.items():
                before = jev.requests
                try:
                    res = fn(jev, q)
                except Exception as e:  # keep the matrix going
                    print(f"   {name:12} ERROR {e}")
                    continue
                g = grade_one(jev, q, res["answer"] or "(no answer)")
                table[name][label].append(g["quality"])
                detail.append({"set": label, "question": q, "method": name,
                               "answer": res["answer"], "grade": g,
                               "requests": jev.requests - before})
                print(f"   {name:12} {res['answer']!r:52} q={g['quality']:.2f}/4 "
                      f"c={g['correct']:.2f} r={g['readable']:.2f} "
                      f"[{jev.requests - before} req]")

    print("\n" + "=" * 94)
    print(f"{'method':14}{'closed':>10}{'open':>10}{'overall':>10}{'req/answer':>13}")
    rows = []
    for name in METHODS:
        c, o = table[name]["closed"], table[name]["open"]
        allq = c + o
        reqs = [d["requests"] for d in detail if d["method"] == name]
        rows.append((sum(allq) / len(allq), name, sum(c) / len(c), sum(o) / len(o),
                     sum(reqs) / len(reqs)))
    for overall, name, c, o, rq in sorted(rows, reverse=True):
        print(f"{name:14}{c:>10.2f}{o:>10.2f}{overall:>10.2f}{rq:>13.1f}")

    out = {"table": table, "detail": detail, "requests": jev.requests,
           "cost_usd": jev.cost, "seconds": round(time.time() - t0, 1)}
    (RESULTS / "methods.json").write_text(json.dumps(out, indent=2))
    print(f"\n{jev.requests} requests, {out['seconds']}s, ${jev.cost:.5f}")


if __name__ == "__main__":
    main()
