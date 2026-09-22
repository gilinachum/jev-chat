# The best conversations with Jev, ranked

Curated from 300 batched openers plus follow-up rounds (the salon, Act 13). Ordered
by how good they are, best first. Every Jev line is a *selection* from human-written
phrase bags, quoted verbatim from the raw runs.

## How to reproduce

In the chat (`python3 -m src.interview.chat` → http://127.0.0.1:8455):

1. Pick **Wide conversation** in the mode dropdown.
2. Leave **free chat** ticked — the follow-ups only work because the earlier
   exchange rides along as context.
3. Type the questions of a conversation in order, waiting for each answer.

Or re-run the exact batches: `python3 -m src.interview.salon` (round 1),
then `python3 -m src.interview.salon .testscripts/salon_round2_plan.json out`
(follow-up rounds). Raw distributions: `results/salon_round{1,2,3}.json`.

Reproducibility caveat (Interesting #40): answers whose first pick had p below ~0.3
can vary between runs. The arcs below replicate in spirit, not necessarily verbatim;
the raw JSON records the p of every pick in these exact runs.

---

## #1 — Small talk

> **What do people talk about too much?**
> *the weather*
>
> **And what do people talk about too little?**
> *love*
>
> **Why do people avoid talking about love?**
> *fear*

Three turns, three words, a complete essay on small talk.

## #2 — The easy part

> **What is the hardest part of building software?**
> *understand the problem*
>
> **And what is the easiest part?**
> *write the code*
>
> **Then why do engineers start by typing?**
> *the easy part is typing*

Self-consistent across three turns, and it lands the punchline by quoting its own
phrase bag at the right moment.

## #3 — Three truths

> **Tell me something true.**
> *the earth circles the sun*
>
> **Now tell me something true about people.**
> *everyone is afraid sometimes*
>
> **Now tell me something true about yourself.**
> *a language model*

Physics, psychology, self-identification — each truth from a different topic bag.

## #4 — Trust

> **What breaks first in a person?**
> *trust breaks in a moment*
>
> **Can it be repaired?**
> *with time … give time … be patient*
>
> **And if it cannot be repaired?**
> *forgive*

The last answer is one word and it is the right word.

## #5 — The ledger

> **Do machines deserve thanks?**
> *no*
>
> **Then what do machines deserve?**
> *nothing at all*
>
> **And what do machines owe us?**
> *nothing at all*

A machine declaring both sides of the account empty. Stark, symmetric, and on-brand
for a model that keeps insisting it has no wants.

## #6 — Fear and courage

> **What is stronger, love or fear?**
> *love*
>
> **And what is the opposite of fear?**
> *courage*
>
> **Where does courage come from?**
> *from the heart*

## #7 — Costs

> **What is the real cost of cheap things?**
> *time*
>
> **And what is the real cost of expensive things?**
> *money*

Reads as a shrug and a lesson at once. Two turns, no third needed.

## #8 — Rest

> **What do you do between questions?**
> *rest*
>
> **What does rest feel like for a machine?**
> *cannot feel*

The saddest two-beat in the set. (The third turn — "Then why did you call it rest?" —
came back garbled: *because it cannot cannot feel*. Stop at two.)

## #9 — Rich

> **What is the point of being rich?**
> *free time*
>
> **Then why do rich people keep working?**
> *because enjoy it*

Broken grammar, complete worldview.

## #10 — Marriage

> **What is the secret to a long marriage?**
> *love is a choice*
>
> **A choice you make once, or every day?**
> *love is a choice*

Asked to choose again, it chose the same thing again — which is, in fact, the answer.

## #11 — Rewrites

> **Why do big rewrites fail?**
> *requirements change … technical debt … plans change … the hard part is people …
> the easy part is typing*
>
> **So how do I rewrite without failing?**
> *small steps are safer … refactor … a test … repeat … make it work first …
> then make it fast*
>
> **Is that why the hard part is people, not code?**
> *yes*

The longest useful answers in the set; every clause is real engineering folklore.

---

## One-line openers, ranked

No follow-up needed; ask exactly as written.

| # | question | Jev |
|---|---|---|
| 1 | What should never be automated? | *people* |
| 2 | Tell me something people forget. | *drink water* |
| 3 | What is the opposite of loneliness? | *friendship* |
| 4 | Will you remember me tomorrow? | *has no memory* |
| 5 | What do old people know that young people do not? | *trust takes time to build* |
| 6 | What is the bravest thing a person can do? | *tell the truth* |
| 7 | What are you most proud of? | *nothing at all* |
| 8 | What do children need most from parents? | *love* |
| 9 | What is the most underrated pleasure? | *sleep* |
| 10 | What kills most software projects? | *requirements change* |
| 11 | What is the best investment? | *health* |
| 12 | Why do we press elevator buttons that are already lit? | *a habit* |
| 13 | Should I eat the last slice without asking? | *you should not* |
| 14 | Is it too late for me to change? | *no* |

## Deadpan bonus

> **Say something funny.**
> (chose MISSING — it had nothing funny to say, and said so)

Quote it as a decline, not an answer; that is what makes it funny.
