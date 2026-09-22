"""Wide conversation: topic-routed phrase selection. POC.

The single-list method caps what Jev can talk about at 253 phrases of one topic.
This mode holds several topic bags and takes each step in two calls:

  call 1  a Choice over an INDEX of topics — each option described, with sample
          phrases, per the finding that described options discriminate (+0.29) and
          bare sentinels do not. STOP and MISSING live in this index, so "nothing
          comes next" and "no bag has my phrase" are routing answers.
  call 2  a Choice over the chosen bag (already-used phrases removed, plus a
          MISSING escape).

2x the requests of the single-list method, in exchange for breadth: ~600 phrases
across 7 topics, any of which can be reached at any step, so an answer can open with
glue ("first"), continue in one bag ("gather the requirements") and qualify from
another ("it takes time").

The risk this POC measures: Jev has no lookahead. Routing asks it to name the topic
of a phrase it has not seen yet. If that fails the way hiding nouns behind
determiners failed, the index step will misroute or MISSING at step 0.

Usage:  python3 -m src.interview.topics     # runs the demo questions, writes
                                            # results/topics_poc.json
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from src.interview.beam import MISSING, STOP, grade_one  # noqa: E402
from src.interview.client import Jev  # noqa: E402
from src.interview.fragment_bank import IDENTITY_PHRASES, MORAL_PHRASES  # noqa: E402
from src.interview.speak import DEFAULT_MAX_PARTS  # noqa: E402

RESULTS = pathlib.Path(__file__).resolve().parents[2] / "results"

GENERAL = [
    "yes", "no", "sometimes", "it depends", "probably", "probably not", "of course",
    "not really", "i do not know", "i cannot say", "that is the wrong question",
    "first", "second", "then", "next", "finally", "at the end", "step by step",
    "one at a time", "because", "but", "and also", "and then", "so", "which means",
    "for example", "usually", "rarely", "always", "never", "in most cases",
    "in some cases", "more or less", "a little", "a lot", "too much", "not enough",
    "the answer is", "the honest answer is", "the short answer is", "it starts with",
    "it ends with", "there are many", "there are a few", "it is simple",
    "it is complicated", "it takes time", "it never ends", "in the end", "over time",
    "if done well", "if done badly", "carefully", "quickly", "slowly",
]

SOFTWARE = [
    "software", "the code", "a program", "a plan", "a design", "a bug", "a test",
    "a team", "the user", "the users", "the requirements", "a deadline",
    "a prototype", "version one", "an architecture", "a database", "an interface",
    "a code review", "technical debt", "legacy code", "open source", "good tools",
    "understand the problem", "gather the requirements", "talk to the users",
    "define what to build", "plan the work", "design the solution",
    "choose the tools", "write the code", "build a prototype", "test it",
    "test everything", "find the bugs", "fix the bugs", "review the code",
    "improve the design", "refactor", "document it", "release it", "ship it",
    "deploy it", "watch it run", "listen to feedback", "maintain it", "update it",
    "start again", "repeat",
    "design comes before code", "testing never ends", "requirements change",
    "users surprise you", "plans change", "software is never finished",
    "small steps are safer", "big rewrites fail", "keep it simple",
    "make it work first", "then make it fast", "write less code",
    "delete old code", "name things well", "measure before optimizing",
    "work with others", "ask for help", "read the error", "debug it",
    "think before typing", "the hard part is people", "the easy part is typing",
    "a working demo", "clean code", "with discipline", "without a plan",
    "under pressure", "on schedule", "late", "over budget",
]

EVERYDAY = [
    "food", "a meal", "breakfast", "dinner", "coffee", "bread", "fruit",
    "home", "a house", "a room", "a bed", "sleep", "rest", "exercise", "a walk",
    "the weather", "a cold day", "a warm day", "money", "a job", "a salary",
    "the rent", "savings", "a budget", "time", "free time", "a habit", "a routine",
    "the city", "the countryside", "travel", "a holiday", "music", "a book",
    "a movie", "a game", "health", "a doctor", "medicine",
    "eat well", "sleep enough", "drink water", "move your body", "see people",
    "go outside", "turn off the phone", "cook at home",
    "spend less than you earn", "save a little every month", "plan the week",
    "clean as you go", "fix it before it breaks", "ask a professional",
    "start small", "do it every day", "enjoy it", "share it",
    "slowly and often", "when tired, rest", "when hungry, eat",
    "with people you love", "costs money", "saves money", "takes practice",
]

NATURE = [
    "the sun", "the moon", "the stars", "the sky", "the sea", "a river",
    "a mountain", "a forest", "a tree", "a leaf", "a flower", "a seed", "the rain",
    "the wind", "the clouds", "snow", "ice", "fire", "light", "heat", "cold",
    "air", "water", "soil", "a bird", "a fish", "a bee", "an insect", "an animal",
    "a plant", "energy", "gravity", "the earth", "the seasons", "spring", "summer",
    "autumn", "winter", "day and night",
    "plants need light", "animals need food", "water becomes ice when cold",
    "water becomes steam when hot", "the air scatters blue light",
    "bees make honey", "birds fly south in winter", "leaves fall in autumn",
    "seeds grow into plants", "the moon pulls the tides",
    "the earth circles the sun", "nothing lives alone",
    "everything is connected", "nature recycles everything",
    "slowly over millions of years", "in cycles", "by natural selection",
    "because of the sun", "because of gravity", "because energy flows",
    "adapts", "grows", "dies", "returns to the soil", "balances itself",
    "is older than us", "is worth protecting",
]

PEOPLE = [
    "love", "friendship", "trust", "respect", "kindness", "honesty", "patience",
    "fear", "anger", "joy", "sadness", "hope", "loneliness", "courage",
    "a friend", "a partner", "a stranger", "a child", "a parent", "people",
    "most people", "everyone", "no one",
    "listen first", "speak less", "ask questions", "tell the truth",
    "keep your promises", "say sorry", "forgive", "be kind", "be patient",
    "be honest", "show up", "give time", "give attention",
    "people need each other", "people change", "people make mistakes",
    "everyone is afraid sometimes", "trust takes time to build",
    "trust breaks in a moment", "love is a choice", "love is attention",
    "friendship needs care", "words matter", "small things matter",
    "listening is rare", "being heard heals", "respect is earned",
    "kindness costs nothing", "anger passes", "feelings are information",
    "talk about it", "together", "alone", "with time", "with honesty",
    "from the heart", "without judgment", "more than words",
]

MONEY = [
    "money", "a salary", "a job", "work", "a career", "savings", "a debt",
    "a budget", "the rent", "a raise", "a pension", "a business", "the market",
    "a bargain", "a scam", "the price", "the bill", "a meeting", "the boss",
    "a colleague", "a customer", "retirement", "a promotion", "unemployment",
    "money is a tool", "money is stored time", "money buys options",
    "money cannot buy taste", "money follows attention", "wealth is quiet",
    "debt is a promise", "a salary buys your hours", "work fills the time it is given",
    "meetings breed meetings", "the best things are not for sale",
    "spend on experiences", "spend on your bed", "buy once, buy well",
    "cheap is expensive", "own less", "earn more or want less",
    "pay yourself first", "avoid debt", "invest early", "compound interest",
    "do work worth doing", "work to live", "never only for the money",
    "ask for more", "know your worth", "quit slowly", "rest is not a reward",
    "enough is a decision", "more is never enough", "the ladder has no top",
    "with interest", "off the books", "on payday", "before taxes", "after taxes",
    "per hour", "for free", "at a discount", "at full price",
]

TIME_AGE = [
    "time", "the past", "the future", "the present", "a moment", "a lifetime",
    "childhood", "youth", "old age", "a birthday", "a decade", "a season of life",
    "a deadline", "a memory", "a regret", "a beginning", "an ending", "a habit",
    "a milestone", "a second chance", "the right moment", "a wasted year",
    "time passes either way", "time is attention", "time heals most things",
    "time reveals everything", "the days are long", "the years are short",
    "youth is wasted on the young", "old age is not for cowards",
    "every age has its gift", "growing old is a privilege",
    "regret fades, lessons stay", "the past is a story", "the future is a guess",
    "now is all there is", "later never comes", "start before you are ready",
    "it is never too late", "it is later than you think", "slow down",
    "hurry ruins it", "wait for it", "do not wait", "one day at a time",
    "count the mornings", "remember this", "you will forget this",
    "nothing lasts", "some things last", "this too shall pass",
    "when you are young", "when you are old", "in hindsight", "at the time",
    "sooner than expected", "later than promised", "for a while", "forever",
]

BIG_QUESTIONS = [
    "the meaning of life", "a purpose", "a reason", "a mystery", "a miracle",
    "the universe", "infinity", "eternity", "the void", "a soul", "a god",
    "faith", "doubt", "death", "birth", "luck", "fate", "free will", "chance",
    "consciousness", "a question", "an answer", "the unknown",
    "meaning is made, not found", "purpose is a direction, not a place",
    "the question is the answer", "nobody knows", "no one has come back to say",
    "death gives life its shape", "we are small and that is fine",
    "the universe owes no explanation", "existence needs no permission",
    "wonder is the beginning", "certainty is the end of thought",
    "faith fills the gap", "doubt keeps faith honest", "luck favours the prepared",
    "fate is what happened", "choice is what happens next",
    "we are the universe asking", "stardust either way",
    "live as if it matters", "it matters because it ends",
    "the answer changes with the asker", "ask a better question",
    "some questions are doors", "some questions are walls",
    "beyond words", "before language", "after everything", "in the end",
    "since the beginning", "for no reason", "for every reason", "perhaps",
]

ART = [
    "art", "beauty", "a song", "a story", "a poem", "a picture", "a film",
    "music", "a melody", "a rhythm", "silence", "a museum", "a stage",
    "a book", "a sentence", "a colour", "a shadow", "a portrait", "a joke",
    "taste", "style", "craft", "talent", "practice", "an audience", "a critic",
    "art is attention made visible", "beauty needs no reason",
    "every song is about time", "every story is about change",
    "art is a lie that tells the truth", "taste is autobiography",
    "craft is love made repeatable", "talent starts it, practice finishes it",
    "the frame makes the picture", "silence is part of the music",
    "beauty hides in the ordinary", "ugliness is honest too",
    "a critic explains, art does not", "good art asks, bad art answers",
    "style is what you cannot help", "make it anyway", "finish it",
    "steal like an artist", "the audience completes the work",
    "art outlives the artist", "beauty is a kind of mercy",
    "sing badly, but sing", "everyone is creative at five",
    "in the eye of the beholder", "for its own sake", "without permission",
    "from nothing", "out of practice", "beyond explanation",
]

FOOD = [
    "food", "a meal", "breakfast", "lunch", "dinner", "a snack", "dessert",
    "bread", "soup", "salt", "sugar", "spice", "coffee", "tea", "wine",
    "a recipe", "an ingredient", "a kitchen", "a table", "leftovers",
    "a home-cooked meal", "street food", "comfort food", "a feast", "a diet",
    "hunger is the best spice", "salt fixes most things",
    "fresh beats fancy", "simple food, done well", "cook with what you have",
    "a recipe is a suggestion", "taste as you go", "sharp knives are safer",
    "the first pancake is for the cook", "bread makes a home smell right",
    "soup forgives everything", "dessert is for the soul",
    "eat together", "food is love you can taste", "a full table, a full heart",
    "cooking is patience you can eat", "the secret ingredient is time",
    "eat breakfast like a king", "everything in moderation",
    "you are what you eat", "hungry people are angry people",
    "the best meal is the shared one", "leftovers taste better tomorrow",
    "with butter", "with garlic", "slow cooked", "overcooked", "underrated",
    "straight from the oven", "on a cold day", "in good company",
]

# name -> (description for the index, sample phrases shown in the index, bag)
TOPICS: dict[str, tuple[str, list[str]]] = {
    "general": ("stance, structure and glue: yes/no, it depends, first/then, "
                "because, qualifiers", GENERAL),
    "software": ("building software and working on it: requirements, design, code, "
                 "tests, shipping, teams", SOFTWARE),
    "everyday life": ("food, home, sleep, money, health, habits and daily advice",
                      EVERYDAY),
    "nature and science": ("sun, water, seasons, plants, animals and why nature "
                           "does what it does", NATURE),
    "people and feelings": ("love, friendship, trust, emotions and how to treat "
                            "people", PEOPLE),
    "machines and AI": ("models, machines, intelligence, understanding, trust in "
                        "AI and its limits", IDENTITY_PHRASES),
    "morality and choices": ("verdicts, moral reasons and qualifications for "
                             "dilemmas and hard choices", MORAL_PHRASES),
    "money and work": ("salaries, savings, spending, careers, bosses, meetings "
                       "and what money is for", MONEY),
    "time and age": ("youth, old age, memory, regret, patience and how time "
                     "treats people", TIME_AGE),
    "big questions": ("meaning, death, fate, faith, the universe and other "
                      "unanswerables — with positions, not just shrugs", BIG_QUESTIONS),
    "art and beauty": ("music, stories, taste, craft and why beauty matters", ART),
    "food and cooking": ("meals, ingredients, recipes, taste and eating together",
                         FOOD),
}
for _name, (_d, _bag) in TOPICS.items():
    assert len(_bag) + 1 <= 255, (_name, len(_bag))

TOTAL_PHRASES = sum(len(b) for _, b in TOPICS.values())

INDEX_CONTROL: dict[str, object] = {
    STOP: {"what": "The phrases already in `answer_so_far` form a complete answer a "
                   "human reader would understand. Nothing further is needed.",
           "not_for": "An answer that is still incomplete or unclear."},
    MISSING: {"what": "No topic here could contain the phrase you want next.",
              "not_for": "A topic that fits, even if it is not a perfect fit."},
}


def _index_options() -> dict[str, object]:
    opts: dict[str, object] = {}
    for name, (desc, bag) in TOPICS.items():
        opts[name] = {"what": desc, "sample_phrases": ", ".join(bag[:6])}
    opts.update(INDEX_CONTROL)
    return opts


def _summarise(answer: dict) -> tuple[str, float, float, list]:
    probs = answer["probabilities"]
    top = sorted(probs.items(), key=lambda kv: -kv[1])[:3]
    return (answer["choice"], round(probs[answer["choice"]], 3),
            round(answer["confidence"], 3), [(k, round(v, 3)) for k, v in top])


def route_step(jev: Jev, state: dict, question_key: str, used: list[str]) -> dict:
    """One step, two calls: pick a topic from the index, then a phrase from its bag."""
    r = jev.ask(state, {"t": {
        "type": "choice",
        "instructions": {
            "question": f"Your next phrase will be appended to `answer_so_far` to "
                        f"answer `{question_key}`. Which topic contains that phrase?",
            "focus": "Choose the topic of your NEXT phrase, not the topic of the "
                     "question. Choose the STOP option as soon as the answer is "
                     "complete.",
        },
        "criteria": _index_options()}})
    topic, tp, tconf, ttop = _summarise(r["answers"]["t"])
    step = {"topic": topic, "topic_p": tp, "topic_conf": tconf, "topic_top3": ttop,
            "requests": 1, "mode": "routed"}
    if topic in (STOP, MISSING):
        return {**step, "pick": topic, "p": tp, "confidence": tconf, "top3": ttop}

    bag = [p for p in TOPICS[topic][1] if p not in used]
    opts: dict[str, object] = {p: None for p in bag}
    opts[MISSING] = {"what": "The phrase you want next is not in this topic's list.",
                     "not_for": "A phrase that is present, even if not your first "
                                "preference."}
    r2 = jev.ask(state, {"p": {
        "type": "choice",
        "instructions": {
            "question": f"Which phrase from the `{topic}` list should come next in "
                        f"`answer_so_far` so that it becomes a truthful answer to "
                        f"`{question_key}`?",
            "focus": "Each option is a complete phrase. Choose on meaning.",
        },
        "criteria": opts}})
    pick, p, conf, top = _summarise(r2["answers"]["p"])
    return {**step, "pick": pick, "p": p, "confidence": conf, "top3": top,
            "requests": 2}


def compose_wide(jev: Jev, state: dict, question_key: str,
                 max_parts: int = DEFAULT_MAX_PARTS) -> dict:
    """speak.compose's contract, answered across all topic bags via routing."""
    parts: list[str] = []
    trace: list[dict] = []
    requests = 0
    ended_by = "max_parts"
    for _ in range(max_parts):
        step = route_step(jev, {**state, "answer_so_far": " ".join(parts)},
                          question_key, parts)
        trace.append(step)
        requests += step["requests"]
        if step["pick"] == STOP:
            ended_by = "stop"
            break
        if step["pick"] == MISSING:
            ended_by = "missing" if step["topic"] == MISSING else "missing_in_topic"
            break
        parts.append(step["pick"])
    return {"answer": " ".join(parts), "parts": parts, "trace": trace,
            "ended_by": ended_by, "requests": requests,
            "method": {"vocab": f"wide: {len(TOPICS)} topics, {TOTAL_PHRASES} phrases",
                       "focus": "routed", "max_parts": max_parts, "min_parts": 0}}


DEMO_QUESTIONS = [
    "What are the stages of writing software?",
    "How do I stay healthy?",
    "Why do leaves fall in autumn?",
    "What makes a good friendship?",
    "Should a machine be trusted with moral decisions?",
    "What is a good breakfast?",
]


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    jev, t0 = Jev(), time.time()
    out: dict = {"topics": {k: len(b) for k, (_, b) in TOPICS.items()}, "answers": []}
    print("=" * 92)
    print(f"WIDE CONVERSATION POC  ({len(TOPICS)} topics, {TOTAL_PHRASES} phrases, "
          f"2 calls per step)")
    print("=" * 92)
    for q in DEMO_QUESTIONS:
        res = compose_wide(jev, {"question": q}, "question")
        g = grade_one(jev, q, res["answer"] or "(no answer)")
        route = " > ".join(f"{t['topic']}({t['topic_p']:.2f})" for t in res["trace"])
        out["answers"].append({"question": q, **res, "grade": g})
        print(f"\nQ: {q}\n   > {res['answer']!r}")
        print(f"     route: {route}")
        print(f"     ended_by={res['ended_by']} req={res['requests']} "
              f"q={g['quality']:.2f} c={g['correct']:.2f} r={g['readable']:.2f}")
    out.update(requests=jev.requests, cost_usd=jev.cost,
               seconds=round(time.time() - t0, 1), model=jev.model_seen)
    (RESULTS / "topics_poc.json").write_text(json.dumps(out, indent=2))
    print(f"\n{jev.requests} requests, {out['seconds']}s, ${jev.cost:.5f}")


if __name__ == "__main__":
    main()
