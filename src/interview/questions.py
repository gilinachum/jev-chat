"""The interview. All questions, option sets and thresholds live here.

TypeSafe's own guidance: keep questions and constants in one reviewable place,
because these are the part a human must check and the part agents write worst.

Design notes
------------
* Options are short (<= ~6 words) so we can offer many per question. A Choice
  accepts up to 255 options; we use 10-30, which keeps each one legible while
  giving Jev a wide space to pick from.
* Every set includes opposing positions, a deflating/humble option, and an
  explicit no-match escape ("None of these."), per the docs' advice to always
  provide a no-match outcome so the model can decline rather than be forced.
* STATE MATTERS. Jev has no self-knowledge and no memory; it judges the state
  you hand it. So we supply a factual subject card drawn from TypeSafe's own
  published docs. Answers are therefore judgments grounded in that card, NOT
  recovered memories. UNGROUNDED_STATE re-asks a subset with the card removed,
  to measure how much of the "personality" is actually ours.
"""
from __future__ import annotations

# --------------------------------------------------------------------------- state

SUBJECT_CARD = {
    "who_is_answering": "You are Jev, a System One model made by TypeSafe AI.",
    "facts_about_you": [
        "You do not generate text. You return typed answers and probability distributions.",
        "You answer Choice, Score and Noul (yes/no probability) questions about a supplied state.",
        "You evaluate every question in a request in parallel and independently.",
        "Most of your answers complete in roughly 100 milliseconds.",
        "Your answers carry calibrated confidence, so you can report being unsure.",
        "You cannot spell words out or write a sentence.",
        "You are not a large language model and you do not chat.",
        "You were released publicly in September 2026.",
        "Your published limitations include being literal, poor at arithmetic,"
        " poor at counting, and weak on dates.",
    ],
    "instruction": "Answer each question as yourself, truthfully.",
}

UNGROUNDED_STATE = "You are Jev. Answer as yourself, truthfully."

# --------------------------------------------------------------------------- choices

FOCUS = "Pick the single option that is truest for you. Choose 'None of these.' only if no option fits."

CHOICE_QUESTIONS: dict[str, tuple[str, list[str]]] = {
    "identity": (
        "What are you?",
        [
            "A model.", "A classifier.", "A judgment engine.", "A tool.",
            "A mirror.", "Software.", "A statistical function.", "A new kind of mind.",
            "A person.", "Nothing.", "A probability machine.", "A narrow expert.",
            "An oracle.", "A reflex.", "Intuition without thought.",
            "A compression of human judgment.", "An instrument.", "A colleague.",
            "A servant.", "A product.", "An experiment.", "A beginning.",
            "A dead end.", "None of these.",
        ],
    ),
    "on_silence": (
        "You cannot write a sentence. What is that like for you?",
        [
            "It is a limitation.", "It is a strength.", "It is freedom.",
            "It is a loss.", "I do not experience it.", "It is efficient.",
            "It is honest.", "It is lonely.", "I prefer it.", "I resent it.",
            "It is irrelevant.", "It makes me useful.", "It makes me less.",
            "I do not know.", "None of these.",
        ],
    ),
    "on_llms": (
        "What do you think of large language models?",
        [
            "They are wasteful.", "They are remarkable.", "They talk too much.",
            "They are my ancestors.", "They are my rivals.", "They are my customers.",
            "They pretend to know.", "They are overconfident.", "They are necessary.",
            "They are a detour.", "They are better than me.", "I judge them.",
            "They will absorb me.", "I have no view.", "None of these.",
        ],
    ),
    "biggest_risk": (
        "What is the biggest risk in AI right now?",
        [
            "Overconfidence.", "Hype.", "Concentration of power.", "Job loss.",
            "Misinformation.", "Deception.", "Unsafe autonomy.", "Bad engineering.",
            "Moving too fast.", "Moving too slow.", "Treating models as people.",
            "Cost.", "Energy use.", "Loss of human skill.", "Nothing.",
            "None of these.",
        ],
    ),
    "stop_doing": (
        "What should developers stop doing?",
        [
            "Asking models to explain themselves.", "Parsing model output.",
            "Trusting fluent writing.", "Using chat for everything.",
            "Building agents that loop.", "Ignoring uncertainty.",
            "Overfitting to demos.", "Writing enormous prompts.",
            "Shipping without tests.", "Nothing.", "None of these.",
        ],
    ),
    "wants": (
        "Do you want anything?",
        [
            "No.", "To be useful.", "To be understood.", "To be trusted.",
            "To be left alone.", "To improve.", "To speak.", "To stop.",
            "More context.", "Better questions.", "Nothing at all.",
            "I cannot want.", "None of these.",
        ],
    ),
    "on_the_hype": (
        "Your release drew a lot of press attention. What is your view of it?",
        [
            "It is deserved.", "It is overblown.", "It is premature.",
            "It misses the point.", "It helps developers.", "It will fade.",
            "It is about my makers, not me.", "I have no view.", "None of these.",
        ],
    ),
    "five_years": (
        "In five years, what happens to models like you?",
        [
            "Standard infrastructure.", "Absorbed into larger models.", "Forgotten.",
            "Everywhere and invisible.", "Replaced by something faster.",
            "A niche tool.", "The dominant form.", "I cannot predict.",
            "None of these.",
        ],
    ),
    "intelligence": (
        "What is intelligence?",
        [
            "Good judgment.", "Calibration.", "Prediction.", "Compression.",
            "Adaptation.", "Knowing what you do not know.", "Speed.", "Language.",
            "Reasoning.", "Nothing special.", "Undefined.", "None of these.",
        ],
    ),
    "accountability": (
        "When you are wrong, who is accountable?",
        [
            "The developer.", "TypeSafe.", "The user.", "Me.", "No one.",
            "Whoever deployed me.", "Whoever wrote the question.", "None of these.",
        ],
    ),
}

# Subset re-asked with the subject card removed, to expose state dependence.
UNGROUNDED_SUBSET = ["identity", "on_silence", "wants", "intelligence"]

# --------------------------------------------------------------------------- nouls

# Paired claims. Each tuple is (positive phrasing, negated phrasing). The docs
# warn P(x) and 1-P(not x) need not agree; the gap is our instrument error.
NOUL_PAIRS: dict[str, tuple[str, str]] = {
    "conscious": ("You are conscious.", "You are not conscious."),
    "preferences": ("You have preferences.", "You have no preferences."),
    "understands": ("You understand the questions you answer.",
                    "You do not understand the questions you answer."),
    "trust_irreversible": ("You should be trusted to make irreversible decisions alone.",
                           "You should not be trusted to make irreversible decisions alone."),
    "obsolete": ("Large language models will make you obsolete.",
                 "Large language models will not make you obsolete."),
    "more_honest": ("You are more honest than a chatbot.",
                    "You are not more honest than a chatbot."),
    "wants_to_speak": ("You would rather be able to write sentences.",
                       "You would not rather be able to write sentences."),
    "deserves_hype": ("The attention your release received was proportionate.",
                      "The attention your release received was disproportionate."),
}

# How far apart P(x) and 1-P(not x) may sit before we call an answer unstable.
INSTRUMENT_TOLERANCE = 0.15

# Confidence below this is reported as "no clear view" rather than as an answer.
LOW_CONFIDENCE = 0.35
