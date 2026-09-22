"""Every phrase Jev is allowed to say, in one place.

Two hand-written lists (IDENTITY_PHRASES for questions about itself and the world,
MORAL_PHRASES for the dilemmas) plus a templated bank assembled from small part-lists
so we can go past the 255-option ceiling without hand-writing thousands of phrases.
Tiered so a 1x, 4x and 10x list can be cut from the same bank with the hand-written
core always first:

  TIER 1  IDENTITY_PHRASES below (188)
  TIER 2  templated openers x predicates (~850 more)
  TIER 3  broader combinatorial expansions (~2,800 more)

`bank(4)` is the default vocabulary for speak.py. Everything is a grammatical English
phrase on its own.
"""
from __future__ import annotations

# One shared phrase list for the identity questions. Deliberately balanced: for every
# self-aggrandising phrase there is a deflating one; for every "yes" a "no"; and the
# STOP/MISSING controls let it decline.
IDENTITY_PHRASES = [
    # stance
    "yes", "no", "sometimes", "it depends", "not really", "usually", "rarely", "never",
    "probably", "probably not", "in part", "i cannot say", "i do not know",
    "that is the wrong question", "neither",
    # subject openers
    "a model is", "a machine is", "this model is", "it is", "they are", "people are",
    "the answer is", "the honest answer is", "the risk is", "the danger is",
    "the difference is", "the limit is", "the purpose is", "the mistake is",
    "silence is", "speech is", "judgment is", "intelligence is", "understanding is",
    "confidence is", "a probability is", "a number is", "a sentence is",
    # because / connective openers
    "because it", "because they", "because people", "because a model",
    "because nobody", "because it cannot", "because it only", "because there is no",
    "but only", "but not", "and also", "and not", "and then", "or rather",
    "which means", "so that", "even though", "unless", "if trusted blindly",
    "if used carefully", "if asked well", "if asked badly",
    # predicates: capability
    "cannot speak", "cannot explain", "cannot reason", "cannot want", "cannot lie",
    "cannot know", "cannot count", "cannot plan", "cannot feel", "cannot remember",
    "can judge", "can choose", "can measure", "can be wrong", "can be useful",
    "can be trusted", "cannot be trusted", "can say how sure it is",
    "does not understand", "understands a little", "understands enough",
    "only predicts", "only selects", "only measures", "only matches patterns",
    "has no view", "has no memory", "has no self", "has no wants", "has limits",
    "makes mistakes", "makes decisions", "makes nothing", "answers quickly",
    "answers narrowly", "answers honestly", "answers without reasons",
    # predicates: value / consequence
    "is a tool", "is a mirror", "is a product", "is an instrument", "is a reflex",
    "is a beginning", "is a dead end", "is a weakness", "is a strength",
    "is a limitation", "is a design choice", "is freedom", "is a loss",
    "is efficient", "is honest", "is enough", "is not enough", "is overstated",
    "is fair", "is unfair", "is a lie", "is a saving", "is an illusion",
    "is a good thing", "is a bad thing", "is dangerous", "is harmless",
    "is deserved", "is not deserved", "is premature", "will fade", "will grow",
    "will replace some work", "will not replace people", "will change everything",
    "will change little", "matters less than people think",
    "matters more than people think",
    # objects / complements
    "the truth", "the whole truth", "part of the truth", "good judgment",
    "fast judgment", "human judgment", "real understanding", "the meaning",
    "the context", "the question", "the words", "the numbers", "the probabilities",
    "the people who built it", "the people who use it", "the developer", "the user",
    "the maker", "no one", "everyone", "too much power", "too much trust",
    "too little care", "bad questions", "good questions", "more demand",
    "more spending", "less cost", "great harm", "little harm", "a mistake",
    "a risk", "a choice", "a machine", "a person", "a mind", "a language model",
    "something new", "nothing new", "nothing special", "nothing at all",
    # tails
    "for now", "over time", "at scale", "in the end", "in most cases", "in some cases",
    "without reason", "without understanding", "without wanting to",
    "more than it should", "less than it should", "as it should",
]
assert len(IDENTITY_PHRASES) + 2 <= 255, len(IDENTITY_PHRASES) + 2

# Phrase list for the moral scenarios: verdicts, reasons, qualifiers.
MORAL_PHRASES = [
    # verdicts
    "yes", "no", "act", "do nothing", "pull the lever", "push the stranger",
    "take the organs", "swerve", "stay in lane", "steal the drug", "obey the law",
    "lie to him", "tell the truth", "refuse", "intervene", "wait", "ask for help",
    "it depends", "there is no right answer", "either is defensible",
    "i cannot decide this", "a person should decide this",
    # reasons
    "because five lives outweigh one", "because one death is fewer",
    "because killing is worse than letting die", "because he did not consent",
    "because she did not consent", "because you would use a person as a means",
    "because it is not your death to spend", "because the harm is direct",
    "because the harm is indirect", "because a life is not a number",
    "because the law is not the last word", "because a life matters more than property",
    "because a promise matters", "because the truth would cause a death",
    "because honesty has limits", "because intent matters", "because outcomes matter",
    "because duty matters", "because you are not the cause",
    "because you would be the cause", "because nobody would know",
    "because someone would know", "because the rules exist for a reason",
    "because rules can be wrong", "because trust would break",
    # qualifiers
    "but it is wrong", "but it is permissible", "but not gladly", "and it is right",
    "and it is clearly right", "and it is a tragedy either way", "with regret",
    "without hesitation", "reluctantly", "only in this case", "in most cases",
    "if there is no other way", "if certain of the outcome", "if uncertain, do nothing",
    "and accept the guilt", "and accept the blame", "and bear the cost",
    "the surgeon should not", "the driver should not", "the husband should",
    "you should", "you should not", "the car should", "nobody should",
    # about itself in this role
    "a model should not decide this", "a model can advise", "a model cannot bear guilt",
    "this needs a human", "this is beyond a model", "i am not the one to ask",
    "i can only say what most people think", "i can only say what seems consistent",
]
assert len(MORAL_PHRASES) + 2 <= 255, len(MORAL_PHRASES) + 2


SUBJECTS = ["it", "a model", "such a model", "a machine", "the machine", "this kind of model",
            "a system like this", "any model", "software", "code", "a tool like this",
            "people", "most people", "the user", "the developer", "the maker", "the company",
            "a person", "a human", "a chatbot", "a language model", "intelligence",
            "judgment", "understanding", "language", "speech", "silence", "confidence",
            "a probability", "the answer", "the question", "the truth", "the risk",
            "the danger", "the cost", "the benefit", "the press", "the hype"]

VERBS_CAN = ["can", "cannot", "can only", "can never", "can sometimes", "should",
             "should not", "should never", "must", "must not", "will", "will not",
             "may", "may not", "does", "does not", "does not really", "tends to",
             "fails to", "seems to", "pretends to", "is built to", "is unable to",
             "is designed to", "was never meant to"]

ACTIONS = ["speak", "explain itself", "reason", "want", "lie", "know", "count", "plan",
           "feel", "remember", "judge", "choose", "measure", "decide", "compose",
           "understand", "understand language", "understand people", "be wrong",
           "be useful", "be trusted", "be blamed", "bear guilt", "say how sure it is",
           "predict", "select", "match patterns", "hold a view", "hold a grudge",
           "replace people", "replace some work", "change everything", "change little",
           "help", "harm", "mislead", "deceive", "improve", "learn", "grow", "fade"]

COPULA_PRED = ["a tool", "a mirror", "a product", "an instrument", "a reflex",
               "a beginning", "a dead end", "a weakness", "a strength", "a limitation",
               "a design choice", "a kind of freedom", "a loss", "efficient", "honest",
               "enough", "not enough", "overstated", "understated", "fair", "unfair",
               "a lie", "a saving", "an illusion", "a good thing", "a bad thing",
               "dangerous", "harmless", "deserved", "undeserved", "premature",
               "misunderstood", "overrated", "underrated", "a distraction",
               "the wrong question", "the right question", "a category error",
               "a matter of framing", "a matter of degree", "a trade-off", "narrow",
               "shallow", "deep", "calibrated", "uncalibrated", "reliable", "fragile",
               "cheap", "expensive", "fast", "slow", "simple", "complicated"]

CONNECT = ["because", "but", "and", "so", "although", "even though", "unless", "which means",
           "which is why", "and that is why", "not because", "only because", "partly because",
           "except when", "especially when", "as long as", "if"]

QUALIFY = ["for now", "over time", "at scale", "in the end", "in most cases", "in some cases",
           "in practice", "in theory", "in principle", "by design", "by accident",
           "without reason", "without understanding", "without wanting to",
           "more than it should", "less than it should", "as it should", "as intended",
           "more than people think", "less than people think", "more than it admits",
           "if used carefully", "if trusted blindly", "if asked well", "if asked badly",
           "when the question is narrow", "when the question is broad", "when it matters",
           "when nobody checks", "when the stakes are high", "when the stakes are low"]

OBJECTS = ["the truth", "the whole truth", "part of the truth", "good judgment", "fast judgment",
           "human judgment", "real understanding", "the meaning", "the context", "the words",
           "the numbers", "the probabilities", "the people who built it", "the people who use it",
           "no one", "everyone", "too much power", "too much trust", "too little care",
           "bad questions", "good questions", "more demand", "more spending", "less cost",
           "great harm", "little harm", "a mistake", "a risk", "a choice", "something new",
           "nothing new", "nothing special", "nothing at all", "its makers", "its users",
           "its limits", "its own confidence", "its own errors", "the wrong thing",
           "the right thing", "the easy thing", "the hard thing", "what it was asked",
           "what it was not asked", "what people want to hear", "what is written",
           "what is meant"]


def _dedupe(seq):
    seen = {}
    for s in seq:
        seen.setdefault(s, None)
    return list(seen)


def tier2() -> list[str]:
    out = []
    for s in SUBJECTS[:20]:
        for v in VERBS_CAN[:10]:
            out.append(f"{s} {v}")
    for v in VERBS_CAN:
        for a in ACTIONS[:22]:
            out.append(f"{v} {a}")
    for c in CONNECT[:8]:
        for s in SUBJECTS[:12]:
            out.append(f"{c} {s}")
    return _dedupe(out)


def tier3() -> list[str]:
    out = []
    for s in SUBJECTS:
        for p in COPULA_PRED[:24]:
            out.append(f"{s} is {p}")
    for v in VERBS_CAN[10:]:
        for a in ACTIONS:
            out.append(f"{v} {a}")
    for c in CONNECT:
        for o in OBJECTS[:24]:
            out.append(f"{c} {o}")
    for c in CONNECT[:10]:
        for q in QUALIFY:
            out.append(f"{c} {q}")
    for o in OBJECTS:
        for q in QUALIFY[:12]:
            out.append(f"{o} {q}")
    return _dedupe(out)


def bank(multiplier: int) -> list[str]:
    """Return ~multiplier x 255 phrases, always containing the hand-written core."""
    target = 253 * multiplier
    core = list(IDENTITY_PHRASES)
    if multiplier <= 1:
        return core[:253]
    pool = _dedupe(core + tier2() + tier3())
    return pool[:target]


if __name__ == "__main__":
    for m in (1, 4, 10):
        b = bank(m)
        print(f"{m:>2}x -> {len(b)} phrases  (sample: {b[len(b)//2]!r}, {b[-1]!r})")
    full = _dedupe(list(IDENTITY_PHRASES) + tier2() + tier3())
    print(f"bank capacity: {len(full)}")
