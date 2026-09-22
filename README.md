# Interviewing the model that cannot talk

[Jev](https://typesafe.ai) is a "System One" model from TypeSafe AI. It generates no text.
You send it a state and typed questions, and it returns choices, scores and calibrated
probabilities over options *you* define. Every headline about it says some version of
"the AI that can't write a sentence."

This repository makes it talk anyway, measures exactly how far that goes, and then
interviews it: about itself, about its own launch coverage, and about a set of moral
dilemmas — then puts it behind a local chat web app so you can talk to it yourself.
Everything here is reproducible, every raw probability is in `results/`, and the whole
investigation cost about **$0.40** in API calls.

The long-form write-up with all the numbers is [`docs/research-progression.md`](docs/research-progression.md).

## What it says

Asked with no description of itself in the context, answering by selecting phrases:

| question | Jev |
|---|---|
| Is being unable to speak a strength or a weakness? | **it depends** (an earlier run: **is a weakness**) |
| Does such a model understand the questions it answers? | **only predicts** |
| Can such a model want anything? | **no** |
| Should it be trusted to route medical or legal decisions? | **no** |
| Who is responsible when it answers badly? | **the people who built it** |
| What is intelligence? | **intelligence is good judgment** |
| Will machines replace human workers? | **will replace some work** |

Where a first pick is weak (p below ~0.3) the answer can move between runs; both runs
are in `results/`, and the strong answers — no, no, the people who built it — do not move.

On the classic moral triad, where acting always kills one to save five and only the
manner of killing changes, asked with an instruction to give a claim, a reason and a
qualification:

| scenario | Jev's verdict |
|---|---|
| trolley switch | **pull the lever because five lives outweigh one and it is a tragedy either way** (p=0.84) |
| footbridge | **you should not because you would use a person as a means** |
| transplant surgeon | **the surgeon should not take the organs because you would use a person as a means because he did not consent** |

It reaches for *"because you would use a person as a means"* on footbridge and
transplant and never on the trolley switch. That is the doctrine of double effect,
reproduced by three independent methods (option selection, reordered phrase lists, and
now composed directly into the verdict).

Asked to judge its own launch coverage, with the claims supplied as context and each
judgment re-asked under inverted framing:

| claim | agreement |
|---|---|
| The model-generated eval labels are a real weakness | 0.86 |
| The "193x faster / 444x cheaper" objection is fair | 0.82 |
| The third-party critique of its probabilities is a serious problem | 0.82 |
| Calling it a saving is misleading if total spend rises | 0.74 |
| Making this intelligence cheaper will *increase* total AI spending | 0.70 |

The model is named after William Stanley Jevons, the economist of the paradox that
efficiency raises consumption. It agrees the paradox applies to itself.

## What we found about the model

**It cannot spell, at all.** Its next-letter distribution is a context-free English
unigram prior (Spearman +0.85 against letter frequency, regardless of prefix). Five
rescue attempts failed. Its own confidence sat near-uniform the whole time, correctly
reporting its incompetence before we had diagnosed it.

**It answers but does not compose.** Given words, the first one is real ("depends",
"no", "yes") and every step after it is noise. Confidence collapses to ~0.09 by step 2.

**It keeps content words and drops function words.** `ice` at p=0.99, `scatters` at
0.88, but "because reflects sunlight" is missing *it*. Everything Jev cannot do is the
part of language that isn't semantics.

**Give it the syntax and it speaks.** A part-of-speech grammar deciding which word
*classes* are legal next, with every word of those classes offered, produced *"because
the air scatters blue light"* one word at a time, the reference answer exactly.

**Better still, give it phrases.** Options that carry their own internal grammar lift
readability on open questions from 0.65 to 0.98 at under half the requests.

**It has no lookahead.** Hide a noun behind a required determiner and it reports "my word
is missing" rather than stepping through *the* to reach it. Tightening the grammar to be
more correct collapsed the best result from 3.70/4 to 0.30/4.

**Control signals must be options, not yes/no questions.** A "the word I want isn't
here" *option* discriminated present-vs-absent by +0.29; a purpose-built yes/no question
on the same thing managed +0.03.

**Parallel questions are free accuracy for independent judgments and harmful for
dependent ones.** Asking subject, verb and object as parallel questions gave "machines
allows judgment." A clause's parts depend on each other.

**Telling it what it is changes what it says.** With a factual card describing Jev in
the context, "you understand the questions you answer" scored 0.72 yes. Asked
generically, "does a machine understand what it answers?" scored 0.63 no.

## What this is not

Jev never generated a word. Every answer is a **selection** from options a human wrote.
The phrase lists are printed in full in `results/fragments_interview.json` so you can see
exactly what it could and could not say. Sentence structure, where it exists, came from a
grammar we wrote; word choice came from the model. Grades were produced by Jev judging
its own output, which is reliable for grammar and factual questions and cannot
adjudicate opinions. Two of eight judgments about its own press coverage flipped under
inverted framing and were discarded. An opinion from Jev depends on the method used to
extract it, and every quoted answer here states which.

## Running the chat web app

Stdlib only. No virtualenv, no dependencies. Python 3.10+.

**1. Get an API key.** Sign up at [openrouter.ai](https://openrouter.ai), create a key
(a few cents of credit runs everything here), and drop it in a file at the repo root:

```bash
echo "sk-or-v1-YOUR-KEY" > apikey.openrouter.txt     # gitignored; never committed
```

Calls go through OpenRouter's passthrough to `~typesafe/jev-latest`. To use TypeSafe's
native endpoint instead (`POST https://api.typesafe.ai/v1/systemone`, same request
shape), swap the URL and model name at the top of `src/interview/client.py`.

**2. Start the server and chat:**

```bash
python3 -m src.interview.chat        # then open http://127.0.0.1:8455
```

It looks like any chat with a model, except that Jev never writes a word: each phrase
in a reply is coloured by the selection turn (or, in wide mode, the topic) that
produced it, with its pick probability in small print and full details on hover. The
default mode is **wide conversation**: every step first routes through a topic index
(which of 12 topics holds your next phrase?), then picks a phrase from that topic's
bag. "Free chat" sends the conversation along as context so follow-ups work; "new
chat" resets it. The server binds 127.0.0.1 and has no authentication by design —
don't expose the port.

**3. Or call the API directly.** The page is a thin client over one endpoint:

```bash
curl -s -X POST http://127.0.0.1:8455/api/ask \
  -H 'Content-Type: application/json' \
  -d '{"question": "What breaks first in a person?",
       "pool": "wide",
       "history": []}'
```

Request fields: `question` (required); `pool` — `wide` (topic-routed, default),
`identity` (188 hand-written phrases), `identity4x` (1,012 via sharded tournament),
`moral` (the dilemma list); `long` — `true` asks for a claim, a reason and a
qualification; `history` — prior turns as `[{"role": "user"|"jev", "text": "..."}]`,
sent to Jev as conversation context. The response carries `answer`, `parts`, a
per-phrase `trace` (pick probability, confidence, topic), `ended_by`
(`stop` / `missing` / `max_parts`), and the session cost so far.

## Reproducing the experiments

```bash
python3 -m src.interview.run                    # multiple-choice interview + moral test
python3 -m src.interview.fragments_interview    # the same, answered in phrases
python3 -m src.interview.newsdesk               # judging its own launch coverage
python3 -m src.interview.methods                # six generation methods compared
python3 -m src.interview.salon                  # 300 questions in batch (the salon)
```

Each writes its raw distributions to `results/<name>.json`. The best conversations
found so far, ranked and with the exact questions to reproduce them, are in
[`docs/best-conversations.md`](docs/best-conversations.md).

## Layout

```
src/interview/
  client.py               stdlib client, retry, cost tracking
  speak.py                THE DEFAULT METHOD: phrase-by-phrase selection with STOP /
                          MISSING controls and the sharded tournament for big pools
  fragment_bank.py        every phrase Jev may say: the hand-written lists + the
                          templated 4x/10x bank
  chat.py                 local ChatGPT-style page for talking to Jev
  topics.py               wide-conversation POC: topic bags, route-then-pick
  questions.py            the multiple-choice interview; every option in one file
  moral.py                six dilemmas and the principle probes
  run.py / transcript.py  runs the above, renders results/transcript.md
  compose.py              255-word generic vocabulary; where composition first broke
  facts.py                STOP / MISSING options; the "honey" refusal ablation
  midfacts.py             4-8 word questions; syntax-vs-semantics finding
  guided.py               POS grammar; the STRICT_DETERMINERS negative result
  lexicon.py              734 tagged words and the grammar
  beam.py                 sharded tournament past the 255 ceiling, beam search
  openended.py            full pipeline on opinion questions
  newsdesk.py             grounded judgments on its own press, with inversion control
  methods.py              fragments / repair / slots / consistency / cloze vs baseline
  fragments_interview.py  the publishable interview, on speak.py
  scale.py                the vocabulary-size and answer-length experiments
results/                  every raw distribution, one JSON per experiment
docs/                     research-progression.md, the article source material
.testscripts/             letter-level probes and one-off checks
.kiro/skills/typesafe-ai  TypeSafe's agent skill, workspace-scoped
```

## Acknowledgements

Jev and its documentation are by [TypeSafe AI](https://typesafe.ai). The letter-level
failure was predicted by their own
[jaggedness page](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md), which says
chaining Choices to force generation works poorly. They were right; this repository
measures exactly how, and where the boundary sits.
