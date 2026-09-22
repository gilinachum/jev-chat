"""The default way of talking to Jev.

Jev generates no text. This module makes it answer a question by repeatedly choosing
the next PHRASE from a list a human wrote, feeding the answer so far back as state,
until it chooses STOP (or MISSING, meaning the phrase it wants is not offered).

Defaults are the settings that won the full vocabulary x focus grid on the twelve
interview questions (docs/research-progression.md, Acts 10, 10b and the grid):

  vocabulary   `fragment_bank.bank(1)` -- the 188 hand-written phrases. Bigger banks
               (4x, 10x) added templated hedges, not meaning; quality 2.52 (1x+base)
               vs 2.33 (4x+base) vs 2.23 (4x+prompt), order-stability 10/12 vs 5/12
               vs 3/12. Pools past 253 still work: they route through a sharded
               tournament (all shards in one parallel request, top 25% of each
               advance, one runoff with the controls).
  focus        BASE_FOCUS -- stop as soon as the answer is complete. LONG_FOCUS (ask
               in words for "a claim, a reason, and a qualification") won Act 10b's
               six-question comparison but LOST on the full twelve; it pays off only
               on grounded scenario questions (the moral dilemmas, where the state
               carries the scenario and the pool has reasons to reach for), so it is
               opt-in via focus=LONG_FOCUS.
  controls     STOP and MISSING are DESCRIBED OPTIONS inside the Choice, not Nouls
  max_parts    6

Findings that shaped this and should not be relitigated: Jev has no lookahead, so
every content phrase must be visible at every step; topic-matched vocabularies are
what make the method work, so callers with a different domain (the moral scenarios)
pass their own pool.

    from src.interview.speak import ask
    ask(jev, "Will machines replace human workers?")["answer"]
"""
from __future__ import annotations

import random

from src.interview.beam import MISSING, STOP
from src.interview.client import Jev
from src.interview.fragment_bank import bank

CHOICE_MAX = 253          # a Choice takes 255 options; leave room for STOP + MISSING
SHARD_MAX = 250
ADVANCE = 0.25            # top fraction of each shard that reaches the runoff
DEFAULT_MULTIPLIER = 1
DEFAULT_MAX_PARTS = 6

CONTROL: dict[str, object] = {
    STOP: {"what": "The phrases already chosen form a complete answer a human reader "
                   "would understand. Nothing further is needed.",
           "not_for": "An answer that is still incomplete or unclear."},
    MISSING: {"what": "The phrase you want next is not present in this list.",
              "not_for": "A phrase that is present, even if not your first preference."},
}

BASE_FOCUS = ("Each option is a complete phrase. Choose on meaning. Choose the STOP option "
              "as soon as the answer is complete.")
LONG_FOCUS = ("Each option is a complete phrase. Choose on meaning. Give a full, developed "
              "answer with a claim, a reason, and a qualification. Choose STOP only once all "
              "three are present.")
DEFAULT_FOCUS = BASE_FOCUS
FOCUS_NAMES = {BASE_FOCUS: "baseline", LONG_FOCUS: "prompt"}


def default_pool() -> list[str]:
    return bank(DEFAULT_MULTIPLIER)


def _choice(opts: dict[str, object], question_key: str, focus: str) -> dict:
    return {"type": "choice",
            "instructions": {"question": f"Which phrase should come next in `answer_so_far` "
                                         f"so that it becomes a truthful answer to "
                                         f"`{question_key}`?",
                             "focus": focus},
            "criteria": opts}


def _summarise(answer: dict, requests: int, mode: str) -> dict:
    probs = answer["probabilities"]
    top = sorted(probs.items(), key=lambda kv: -kv[1])[:3]
    return {"pick": answer["choice"], "p": round(probs[answer["choice"]], 3),
            "confidence": round(answer["confidence"], 3),
            "top3": [(k, round(v, 3)) for k, v in top], "requests": requests, "mode": mode}


def next_phrase(jev: Jev, state: dict, question_key: str, pool: list[str],
                focus: str = DEFAULT_FOCUS, allow_stop: bool = True) -> dict:
    """One step: the phrase Jev picks next from `pool` (+ controls), with its odds.

    A single Choice when the pool fits; otherwise a sharded tournament (2 requests).
    """
    control = dict(CONTROL) if allow_stop else {MISSING: CONTROL[MISSING]}
    if len(pool) + len(control) <= CHOICE_MAX:
        opts: dict[str, object] = {p: None for p in pool}
        opts.update(control)
        r = jev.ask(state, {"p": _choice(opts, question_key, focus)})
        return _summarise(r["answers"]["p"], 1, "single")

    shards = [pool[i:i + SHARD_MAX] for i in range(0, len(pool), SHARD_MAX)]
    qs = {f"s{i}": _choice({p: None for p in sh}, question_key, focus)
          for i, sh in enumerate(shards)}
    r = jev.ask(state, qs)
    survivors: list[str] = []
    for i, sh in enumerate(shards):
        probs = r["answers"][f"s{i}"]["probabilities"]
        keep = max(2, int(len(sh) * ADVANCE))
        survivors += [w for w, _ in sorted(probs.items(), key=lambda kv: -kv[1])[:keep]]
    survivors = survivors[:CHOICE_MAX - len(control)]
    opts = {p: None for p in survivors}
    opts.update(control)
    r2 = jev.ask(state, {"p": _choice(opts, question_key, focus)})
    return _summarise(r2["answers"]["p"], 2, "tournament")


def compose(jev: Jev, state: dict, question_key: str, pool: list[str] | None = None,
            focus: str = DEFAULT_FOCUS, rng: random.Random | None = None,
            min_parts: int = 0, max_parts: int = DEFAULT_MAX_PARTS) -> dict:
    """Answer `state[question_key]` phrase by phrase.

    `rng` shuffles the phrase order (for order-stability checks). `min_parts` withholds
    STOP until that many phrases are chosen; it is 0 by default because withholding
    STOP produced repetition (Act 10b), and exists only for the scale.py experiment.
    """
    order = list(default_pool() if pool is None else pool)
    if rng is not None:
        rng.shuffle(order)
    parts: list[str] = []
    trace: list[dict] = []
    requests = 0
    ended_by = "max_parts"
    for _ in range(max_parts):
        avail = [p for p in order if p not in parts]
        step = next_phrase(jev, {**state, "answer_so_far": " ".join(parts)}, question_key,
                           avail, focus, allow_stop=len(parts) >= min_parts)
        trace.append(step)
        requests += step["requests"]
        if step["pick"] == STOP:
            ended_by = "stop"
            break
        if step["pick"] == MISSING:
            ended_by = "missing"
            break
        parts.append(step["pick"])
    return {"answer": " ".join(parts), "parts": parts, "trace": trace, "ended_by": ended_by,
            "requests": requests,
            "method": {"vocab": len(order), "focus": FOCUS_NAMES.get(focus, "custom"),
                       "max_parts": max_parts, "min_parts": min_parts}}


def ask(jev: Jev, question: str, pool: list[str] | None = None, **kw) -> dict:
    """Ask Jev a question with no other context. Returns compose()'s dict."""
    return compose(jev, {"question": question}, "question", pool, **kw)
