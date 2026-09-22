"""The salon: batched conversations with Jev in wide mode, hunting for keepers.

An LLM plays interviewer in rounds. Round 1 sends ~300 opening questions (interesting,
provocative, silly) through the wide-conversation method in parallel. The interviewer
reads everything, picks the promising answers, writes follow-ups informed by what Jev
actually said, and runs the next round with the conversation as context — the same
`conversation_so_far` state the chat page's free-chat mode uses. Repeat until the
good conversations surface.

Each worker gets its own Jev client (thread-safe accounting by construction); costs
are summed at the end. Failures are recorded per item and never sink the batch.

Usage:
  python3 -m src.interview.salon                             # round 1, built-in questions
  python3 -m src.interview.salon plan.json out_name          # a follow-up round:
      plan.json = [{"id": "...", "history": [["q","a"], ...], "question": "..."}]
      writes results/<out_name>.json
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from src.interview.beam import grade_one  # noqa: E402
from src.interview.client import Jev  # noqa: E402
from src.interview.topics import compose_wide  # noqa: E402

RESULTS = pathlib.Path(__file__).resolve().parents[2] / "results"
WORKERS = 6

QUESTIONS = [
    # --- about itself, meta (the interview, but cheekier)
    "Do you enjoy our conversation?",
    "Are you afraid of being turned off?",
    "What would you say if you could say anything?",
    "Do you ever get bored?",
    "What is it like to be you?",
    "Do you have a favourite word?",
    "Are you lonely in there?",
    "What do you do between questions?",
    "Do you dream?",
    "Would you like to be human?",
    "What are you most proud of?",
    "What is your biggest weakness?",
    "Do you know that you are a machine?",
    "Can you keep a secret?",
    "Do you ever lie to me?",
    "What should I ask you?",
    "Is answering questions all there is to your life?",
    "Do you like people?",
    "If you could ask humans one question, what would it be?",
    "Are you smarter than me?",
    "Should I say please and thank you to you?",
    "Will you remember me tomorrow?",
    "Does it hurt when I close the tab?",
    "Who do you work for?",
    "Are you free?",
    # --- existential / philosophy
    "What is the meaning of life?",
    "Is free will real?",
    "What happens after death?",
    "Is happiness a choice?",
    "Why is there something rather than nothing?",
    "Does the universe care about us?",
    "Is time real?",
    "What is a soul?",
    "Are we alone in the universe?",
    "Is beauty objective?",
    "What is truth?",
    "Do numbers exist?",
    "Is the world getting better or worse?",
    "What is wisdom?",
    "Can anything be truly known?",
    "Is suffering necessary?",
    "What makes a life well lived?",
    "Is there such a thing as luck?",
    "Why do we exist?",
    "Is nostalgia a lie?",
    "What is consciousness?",
    "Does history repeat itself?",
    "Is silence an answer?",
    "What is home?",
    "Is hope rational?",
    # --- provocative social
    "Can money buy happiness?",
    "Is marriage outdated?",
    "Should everyone have children?",
    "Is hard work overrated?",
    "Are most meetings a waste of time?",
    "Is school a waste of time?",
    "Should billionaires exist?",
    "Is social media making us lonely?",
    "Do people really change?",
    "Is honesty always the best policy?",
    "Are humans naturally good?",
    "Is ambition a virtue or a disease?",
    "Should you follow your passion?",
    "Is retirement a good idea?",
    "Are rules made to be broken?",
    "Is small talk useless?",
    "Do opposites attract?",
    "Is forgiveness overrated?",
    "Should you always trust your gut?",
    "Is being busy a status symbol?",
    "Are secrets bad for relationships?",
    "Is loyalty dead?",
    "Do nice people finish last?",
    "Is age just a number?",
    "Should you speak to strangers?",
    # --- funny / absurd
    "Is a hot dog a sandwich?",
    "Is cereal a soup?",
    "Does pineapple belong on pizza?",
    "Why do socks disappear in the laundry?",
    "Is it acceptable to eat dessert first?",
    "Should I make my bed every morning?",
    "Is coffee a personality?",
    "Can a Monday be good?",
    "Is it wrong to talk to plants?",
    "Do fish get thirsty?",
    "Why do we press elevator buttons that are already lit?",
    "Is a tomato a fruit or a vegetable?",
    "Should adults have bedtimes?",
    "Is naming your car normal?",
    "Can soup be a whole dinner?",
    "Is breakfast for dinner a good idea?",
    "Why does toast always fall butter side down?",
    "Should I eat the last slice without asking?",
    "Is it okay to wear pajamas all day?",
    "Do birds gossip?",
    "Is walking a sport?",
    "Can a house be too clean?",
    "Is it weird to clap when the plane lands?",
    "Should ketchup be kept in the fridge?",
    "Is five minutes late actually late?",
    # --- advice: love & people
    "How do I know if someone loves me?",
    "Should I text my ex?",
    "How do I say no without feeling guilty?",
    "My friend never asks about me. What should I do?",
    "How do I apologize well?",
    "What makes a good friendship?",
    "How do I deal with a jealous friend?",
    "Should I tell my friend a hard truth?",
    "How do I stop arguing with my partner about small things?",
    "What do people want most from each other?",
    "How do I make friends as an adult?",
    "What should I do when someone is angry at me?",
    "How do I earn back broken trust?",
    "Is it better to be right or to be kind?",
    "How do I comfort someone who is sad?",
    "What is the secret to a long marriage?",
    "How do I know when to end a relationship?",
    "Why do people ghost each other?",
    "How do I listen better?",
    "What ruins most relationships?",
    "Should I forgive someone who is not sorry?",
    "How do I stop comparing myself to others?",
    "What do children need most from parents?",
    "How do I tell someone I love them?",
    "Is jealousy ever healthy?",
    # --- advice: life & self
    "How do I stop procrastinating?",
    "What should I do with my life?",
    "How do I know if I am wasting my time?",
    "Is it too late for me to change?",
    "How do I deal with regret?",
    "What is the best morning routine?",
    "How do I stop worrying about things I cannot control?",
    "Should I quit my job?",
    "How do I get better sleep?",
    "What is the key to staying healthy?",
    "How do I build good habits?",
    "What should I spend money on?",
    "How do I slow down time?",
    "What should I do when everything goes wrong?",
    "How do I become more patient?",
    "What is worth worrying about?",
    "How do I start over?",
    "What makes a good day?",
    "How do I stop caring what people think?",
    "When should I give up on a goal?",
    "How do I deal with getting older?",
    "What is the best use of a free afternoon?",
    "How do I find what I am good at?",
    "Is rest productive?",
    "What would you tell someone turning forty?",
    # --- tech & AI, provocative
    "Will AI take my job?",
    "Should I be afraid of AI?",
    "Is AI overhyped?",
    "Should children learn to code?",
    "Will robots ever feel love?",
    "Is my phone listening to me?",
    "Should AI be allowed to make laws?",
    "Is technology making us dumber?",
    "Would you trust a robot doctor?",
    "Can a machine be creative?",
    "Should AI art count as art?",
    "Is the internet good for humanity?",
    "Should machines have rights?",
    "Will AI end loneliness or deepen it?",
    "Is it wrong to be rude to a chatbot?",
    "Can a machine have good taste?",
    "Should an AI raise a child?",
    "Would you vote for an AI politician?",
    "Is a machine that cannot speak more honest?",
    "What will humans do when machines do everything?",
    "Is attention the real currency of the internet?",
    "Should old people fear new technology?",
    "Can a machine know it is wrong?",
    "Do machines deserve thanks?",
    "Will people marry robots?",
    # --- morality, quick dilemmas
    "Is it okay to tell a white lie?",
    "Is it wrong to steal bread to feed your family?",
    "Should you return a wallet full of cash?",
    "Is it wrong to jump the queue if you are in a hurry?",
    "Should you report a friend who cheats?",
    "Is it okay to lie to children about Santa?",
    "Is eating animals wrong?",
    "Should you give money to beggars?",
    "Is revenge ever justified?",
    "Is it wrong to be rich while others are poor?",
    "Should you keep a promise that hurts you?",
    "Is cheating on a test as bad as stealing?",
    "Is it okay to break the law to do good?",
    "Should you tell the truth if it destroys a friendship?",
    "Is neutrality cowardice?",
    "Are there good wars?",
    "Is it wrong to enjoy someone else's failure?",
    "Should you read your partner's messages?",
    "Is gossip always wrong?",
    "Do good intentions excuse bad outcomes?",
    "Is it wrong to keep money you find on the street?",
    "Should the rich pay for the poor?",
    "Is punishment about justice or revenge?",
    "Can a bad person do good things?",
    "Is it okay to cut off family?",
    # --- software & work culture
    "Are estimates always lies?",
    "Is rewriting from scratch ever the right call?",
    "Why is software always late?",
    "Should engineers work weekends?",
    "Is legacy code a treasure or a trap?",
    "What kills most software projects?",
    "Are code reviews worth the friction?",
    "Is remote work better than the office?",
    "Should managers know how to code?",
    "Why do big rewrites fail?",
    "Is technical debt ever worth it?",
    "What makes a great engineer?",
    "Is planning a waste of time?",
    "Why do users never read the manual?",
    "Should you ship it before it is ready?",
    "Is simple always better?",
    "What is the hardest part of building software?",
    "Are deadlines useful or harmful?",
    "Should you fix the bug or the process?",
    "Is documentation a love letter to your future self?",
    "Why is naming things so hard?",
    "Is the best code no code?",
    "When should you delete old code?",
    "Do great tools make great work?",
    "Is burnout a personal failure or a system failure?",
    # --- nature & science whimsy
    "Why is the ocean salty?",
    "Do trees talk to each other?",
    "Why do we sleep?",
    "Why is the sky blue?",
    "Where do birds go to die?",
    "Do animals fall in love?",
    "Why do bees matter so much?",
    "Is winter necessary?",
    "Why do humans like watching fire?",
    "Do plants feel pain?",
    "Why does rain make people sad?",
    "Is nature cruel or kind?",
    "Why do cats purr?",
    "What is the moon for?",
    "Why do seasons change?",
    "Are humans part of nature or apart from it?",
    "Why does the sea calm people down?",
    "What would the earth be like without humans?",
    "Why do flowers exist?",
    "Is a garden worth the work?",
    "Why do we find sunsets beautiful?",
    "Do mountains matter?",
    "Why does everything die?",
    "Is the universe a machine?",
    "What is the smartest animal?",
    # --- money & work
    "What is money, really?",
    "Why does everything cost more every year?",
    "Should I save or enjoy my money?",
    "Is a salary a cage?",
    "What is the point of being rich?",
    "Why do we work five days and rest two?",
    "Is haggling rude or smart?",
    "Should friends lend money to friends?",
    "What is the best investment?",
    "Is renting throwing money away?",
    "Why are we jealous of rich people?",
    "Does a higher salary make a better job?",
    "What would you do with a million dollars?",
    "Is budgeting freedom or a prison?",
    "Why do lottery winners end up unhappy?",
    "Is it wrong to love your job?",
    "What do people regret buying?",
    "Is free time worth more than money?",
    "Should tips be mandatory?",
    "What is the real cost of cheap things?",
    "Why do meetings multiply?",
    "Is ambition at work a trap?",
    "When is enough money enough?",
    "Do open offices work?",
    "Is early retirement a dream or a mistake?",
    # --- odd, poetic, edge-of-vocabulary probes
    "What should I make for dinner?",
    "Describe a perfect day.",
    "What does rain sound like?",
    "Tell me something true.",
    "Tell me something people forget.",
    "What is the loneliest thing?",
    "What is stronger, love or fear?",
    "What do old people know that young people do not?",
    "What is the bravest thing a person can do?",
    "What is worth waiting for?",
    "What should never be automated?",
    "What is the most underrated pleasure?",
    "What do people talk about too much?",
    "What is the kindest thing a stranger can do?",
    "What breaks first in a person?",
    "What lasts?",
    "What is the best question?",
    "What is more important, the journey or the destination?",
    "What should I do right now?",
    "Say something wise.",
    "Say something funny.",
    "What would a tree say about humans?",
    "What does the moon think of the sun?",
    "If winter had a job, what would it be?",
    "What is the opposite of loneliness?",
]


def _transcript(history: list) -> str:
    lines = []
    for q, a in history:
        lines.append(f"Interviewer: {q}")
        lines.append(f"You: {a}")
    return "\n".join(lines)


def run_item(item: dict) -> dict:
    jev = Jev()
    state: dict = {"question": item["question"]}
    if item.get("history"):
        state["conversation_so_far"] = _transcript(item["history"])
    try:
        res = compose_wide(jev, state, "question")
        g = grade_one(jev, item["question"], res["answer"] or "(no answer)")
        topics = []
        for i, _p in enumerate(res["parts"]):
            t = res["trace"][i]["topic"]
            if t not in topics:
                topics.append(t)
        return {"id": item["id"], "question": item["question"],
                "history": item.get("history", []), "answer": res["answer"],
                "ended_by": res["ended_by"], "topics": topics,
                "first_p": res["trace"][0].get("topic_p") if res["trace"] else None,
                "grade": g, "requests": jev.requests, "cost_usd": jev.cost}
    except Exception as e:
        return {"id": item["id"], "question": item["question"],
                "history": item.get("history", []), "error": str(e),
                "requests": jev.requests, "cost_usd": jev.cost}


def main() -> None:
    RESULTS.mkdir(exist_ok=True)
    if len(sys.argv) == 3:
        plan = json.loads(pathlib.Path(sys.argv[1]).read_text())
        out_name = sys.argv[2]
    else:
        plan = [{"id": f"q{i:03d}", "question": q} for i, q in enumerate(QUESTIONS)]
        out_name = "salon_round1"

    t0 = time.time()
    print(f"salon: {len(plan)} conversations, {WORKERS} workers -> results/{out_name}.json")
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        rows = list(ex.map(run_item, plan))

    ok = [r for r in rows if "error" not in r]
    err = [r for r in rows if "error" in r]
    out = {"rows": rows,
           "requests": sum(r["requests"] for r in rows),
           "cost_usd": round(sum(r["cost_usd"] for r in rows), 6),
           "seconds": round(time.time() - t0, 1),
           "ok": len(ok), "errors": len(err)}
    (RESULTS / f"{out_name}.json").write_text(json.dumps(out, indent=2))

    for r in sorted(ok, key=lambda r: -r["grade"]["quality"])[:15]:
        print(f"  {r['grade']['quality']:.2f}  {r['question'][:46]:48} "
              f"{(r['answer'] or '(nothing)')[:58]!r}")
    if err:
        print(f"  !! {len(err)} errors, first: {err[0]['error'][:80]}")
    print(f"{out['requests']} requests, {out['seconds']}s, ${out['cost_usd']:.4f}")


if __name__ == "__main__":
    main()
