"""A local chat page for talking to Jev.

Serves a ChatGPT-style page on http://127.0.0.1:8455 and answers each message with
speak.py, the project's default method: Jev picks phrases one at a time from a
hand-written list until it chooses STOP. In the single-list modes every phrase is
coloured by the turn that produced it; in wide-conversation mode phrases are coloured
by the TOPIC that produced them, the topic index is shown under the header, and each
answer carries chips of the topics it drew from. Hover a phrase for its pick
probability and confidence.

Free chat mode (on by default) sends the past exchanges along as a
`conversation_so_far` transcript in the state — a sliding window of the last 8 — so
follow-ups have context. Untick it to ask each question cold, which is how the
published interview was run (results quoted from this page should say which mode was
used).

Local only: binds 127.0.0.1 and has no authentication; do not expose it. Each message
costs a fraction of a cent (the running total is shown in the footer).

Usage:  python3 -m src.interview.chat        # then open http://127.0.0.1:8455
"""
from __future__ import annotations

import json
import pathlib
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from src.interview.client import Jev  # noqa: E402
from src.interview.fragment_bank import IDENTITY_PHRASES, MORAL_PHRASES, bank  # noqa: E402
from src.interview.speak import BASE_FOCUS, LONG_FOCUS, compose  # noqa: E402
from src.interview.topics import TOPICS, TOTAL_PHRASES, compose_wide  # noqa: E402

HOST, PORT = "127.0.0.1", 8455
WIDE = "wide"
POOLS = {
    "identity": ("Interview (188 hand-written)", lambda: IDENTITY_PHRASES),
    "identity4x": ("Interview 4x (1,012 via tournament)", lambda: bank(4)),
    "moral": ("Moral dilemmas (79)", lambda: MORAL_PHRASES),
    WIDE: (f"Wide conversation ({len(TOPICS)} topics, {TOTAL_PHRASES} phrases, "
           f"2x calls)", None),
}
JEV = Jev()

MAX_HISTORY = 8           # exchanges kept in the sliding window sent to Jev


def _transcript(history: list) -> str:
    """Past exchanges as a plain transcript, newest last, sliding window."""
    lines = []
    for turn in history[-MAX_HISTORY * 2:]:
        who = "Interviewer" if turn.get("role") == "user" else "You"
        text = str(turn.get("text", "")).strip()[:500]
        if text:
            lines.append(f"{who}: {text}")
    return "\n".join(lines)


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Talk to Jev</title>
<style>
  :root {
    --bg: #131318; --panel: #1e1e26; --panel2: #26262f; --border: #34343f;
    --text: #ececf1; --dim: #8f8f9d; --accent1: #22d3ee; --accent2: #a78bfa;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; color: var(--text); height: 100vh; display: flex; flex-direction: column;
    font: 16px/1.6 -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    background: var(--bg);
    background-image:
      radial-gradient(60rem 30rem at 15% -10%, rgba(34,211,238,.07), transparent 60%),
      radial-gradient(50rem 30rem at 90% 110%, rgba(167,139,250,.08), transparent 60%);
    background-attachment: fixed;
  }
  header { padding: 10px 16px; border-bottom: 1px solid var(--border);
           display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
           backdrop-filter: blur(6px); }
  .logo { width: 30px; height: 30px; border-radius: 50%; flex: none;
          background: conic-gradient(from 210deg, var(--accent1), var(--accent2), #f472b6, var(--accent1));
          display: flex; align-items: center; justify-content: center;
          font-weight: 800; font-size: 14px; color: #10101a;
          box-shadow: 0 0 14px rgba(34,211,238,.45); }
  header h1 { font-size: 16px; font-weight: 700; margin: 0;
    background: linear-gradient(90deg, var(--accent1), var(--accent2), #f472b6, var(--accent1));
    background-size: 300% 100%; -webkit-background-clip: text; background-clip: text;
    color: transparent; animation: shimmer 8s linear infinite; }
  @keyframes shimmer { to { background-position: 300% 0; } }
  header .sub { color: var(--dim); font-size: 12px; }
  select, label.opt { background: var(--panel); color: var(--text); font-size: 12px;
           border: 1px solid var(--border); border-radius: 8px; padding: 4px 8px; }
  select:hover, label.opt:hover { border-color: var(--accent1); }
  #reset { background: var(--panel); color: var(--text); font-size: 12px;
           border: 1px solid var(--border); border-radius: 8px; padding: 4px 10px;
           width: auto; height: auto; cursor: pointer; transition: all .2s;
           margin-left: auto; }
  #reset:hover { border-color: var(--accent2); color: var(--accent2);
                 box-shadow: 0 0 10px rgba(167,139,250,.25); }
  label.opt { display: flex; gap: 6px; align-items: center; cursor: pointer;
              transition: border-color .2s; }
  #topicbar { display: none; padding: 8px 16px; border-bottom: 1px solid var(--border);
              gap: 6px; flex-wrap: wrap; align-items: center; }
  #topicbar.show { display: flex; animation: fadeup .3s both; }
  #topicbar .tlabel { color: var(--dim); font-size: 11px; margin-right: 4px; }
  .chip { font-size: 11.5px; border-radius: 999px; padding: 2px 10px; cursor: help;
          border: 1px solid; transition: transform .15s, box-shadow .15s; }
  .chip:hover { transform: translateY(-1px); }
  .chip .n { opacity: .65; font-size: 10px; }
  #log { flex: 1; overflow-y: auto; scroll-behavior: smooth; }
  .col { max-width: 46rem; margin: 0 auto; padding: 0 16px; }
  .row { display: flex; margin: 20px 0; gap: 10px; animation: fadeup .35s both; }
  @keyframes fadeup { from { opacity: 0; transform: translateY(8px); } }
  .row.user { justify-content: flex-end; }
  .avatar { width: 28px; height: 28px; border-radius: 50%; flex: none; margin-top: 2px;
            background: conic-gradient(from 210deg, var(--accent1), var(--accent2), #f472b6, var(--accent1));
            display: flex; align-items: center; justify-content: center;
            font-weight: 800; font-size: 12px; color: #10101a; }
  .avatar.busy { animation: breathe 1.4s ease-in-out infinite; }
  @keyframes breathe { 50% { box-shadow: 0 0 16px rgba(167,139,250,.8);
                             transform: scale(1.12); } }
  .bubble { max-width: 85%; white-space: pre-wrap; word-wrap: break-word; }
  .user .bubble { background: linear-gradient(135deg, #2d3d55, #33344d);
                  border: 1px solid #3d4d66; border-radius: 18px 18px 4px 18px;
                  padding: 8px 16px; box-shadow: 0 2px 10px rgba(0,0,0,.3); }
  .jev .bubble { background: var(--panel); border: 1px solid var(--border);
                 border-radius: 4px 18px 18px 18px; padding: 10px 14px 8px;
                 box-shadow: 0 2px 10px rgba(0,0,0,.3); }
  .part { display: inline-block; border-radius: 8px; padding: 1px 7px; margin: 2px 2px;
          cursor: help; border: 1px solid transparent;
          animation: pop .35s cubic-bezier(.2,1.4,.4,1) both;
          transition: transform .15s, box-shadow .15s; }
  .part .pp { font-size: 9px; opacity: .55; margin-left: 4px; vertical-align: super; }
  .part:hover { transform: translateY(-2px); box-shadow: 0 3px 10px rgba(0,0,0,.45); }
  @keyframes pop { from { opacity: 0; transform: scale(.6); } }
  .meta { font-size: 11px; color: var(--dim); margin-top: 8px; }
  .chips { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 8px; }
  .silent { color: var(--dim); font-style: italic; }
  .dots { display: inline-flex; gap: 5px; padding: 6px 2px; }
  .dots i { width: 7px; height: 7px; border-radius: 50%; background: var(--accent2);
            animation: hop 1s infinite; }
  .dots i:nth-child(2) { animation-delay: .15s; background: var(--accent1); }
  .dots i:nth-child(3) { animation-delay: .3s; background: #f472b6; }
  @keyframes hop { 30% { transform: translateY(-6px); opacity: .5; } }
  #sugg { display: flex; flex-direction: column; gap: 8px; align-items: center;
          margin: 10vh 0 0; }
  #sugg .hello { color: var(--dim); font-size: 14px; margin-bottom: 8px;
                 text-align: center; }
  .sq { background: var(--panel); border: 1px solid var(--border); color: var(--text);
        width: auto; height: auto; border-radius: 999px; padding: 7px 16px;
        font-size: 13.5px; cursor: pointer; transition: all .2s; }
  .sq:hover { border-color: var(--accent1); transform: translateY(-1px);
              box-shadow: 0 3px 14px rgba(34,211,238,.15); }
  form { padding: 12px 16px 6px; }
  .inputwrap { max-width: 46rem; margin: 0 auto; display: flex; gap: 8px;
               background: var(--panel); border: 1px solid var(--border);
               border-radius: 26px; padding: 8px 8px 8px 20px; transition: all .25s; }
  .inputwrap:focus-within { border-color: var(--accent1);
               box-shadow: 0 0 18px rgba(34,211,238,.18); }
  input[type=text] { flex: 1; background: none; border: none; outline: none;
                     color: var(--text); font-size: 16px; }
  #send { background: linear-gradient(135deg, var(--accent1), var(--accent2));
          color: #10101a; border: none; width: 36px; height: 36px; border-radius: 50%;
          font-size: 17px; font-weight: 700; cursor: pointer; transition: all .2s; }
  #send:hover:not(:disabled) { transform: scale(1.1) rotate(8deg);
          box-shadow: 0 0 14px rgba(167,139,250,.5); }
  #send:disabled { opacity: 0.3; cursor: default; }
  footer { text-align: center; color: var(--dim); font-size: 11px; padding: 4px 0 10px; }
  footer .live { display: inline-block; width: 6px; height: 6px; border-radius: 50%;
                 background: #34d399; margin-right: 5px; animation: blink 2.4s infinite; }
  @keyframes blink { 50% { opacity: .25; } }
</style>
</head>
<body>
<header>
  <div class="logo">J</div>
  <h1>Talk to Jev</h1>
  <span class="sub">it never writes a word — every phrase is picked from a human-written
  list, one turn at a time</span>
  <select id="pool" title="Which phrase list Jev answers from">%OPTIONS%</select>
  <label class="opt" title="Ask in words for a claim, a reason and a qualification">
    <input type="checkbox" id="long"> developed answer</label>
  <label class="opt" title="Send past exchanges along as state, so follow-ups have context">
    <input type="checkbox" id="freechat" checked> free chat (remembers this conversation)</label>
  <button type="button" id="reset" title="Start a fresh conversation (clears Jev's memory of this one)">
    &#x21bb; new chat</button>
</header>
<div id="topicbar"><span class="tlabel">TOPIC INDEX — Jev routes every phrase through
one of these:</span></div>
<div id="log"><div class="col" id="msgs">
  <div id="sugg"><div class="hello">Jev answers by choosing, never by writing.<br>
  Try one of these, or ask your own:</div></div>
</div></div>
<form id="f">
  <div class="inputwrap">
    <input type="text" id="q" placeholder="Ask Jev anything…" autocomplete="off" autofocus>
    <button id="send" title="Send">&#8679;</button>
  </div>
</form>
<footer id="foot"><span class="live"></span>phrase-by-phrase selection &middot; $0.00000 this session</footer>
<script>
const TOPICS = %TOPICS%;
const COLORS = ["#7ec8ff","#ffb86c","#8fe388","#ff8fa3","#d0a9ff","#ffe066",
                "#7fdbca","#f4a4ff"];
const topicColor = {};
TOPICS.forEach((t, i) => topicColor[t.name] = COLORS[i % COLORS.length]);

const SUGGESTIONS = {   // openers proven in the salon runs (results/salon_round*.json)
  wide: ["What do people talk about too much?", "Tell me something true.",
         "What is the hardest part of building software?",
         "What breaks first in a person?", "Do machines deserve thanks?",
         "What is the point of being rich?", "What should never be automated?"],
  other: ["Is being unable to speak a strength or a weakness?",
          "Does a model understand the questions it answers?",
          "Who is responsible when a model answers badly?",
          "Will machines replace human workers?"],
};

const msgs = document.getElementById("msgs"), log = document.getElementById("log");
const form = document.getElementById("f"), input = document.getElementById("q");
const send = document.getElementById("send"), foot = document.getElementById("foot");
const poolSel = document.getElementById("pool"), topicbar = document.getElementById("topicbar");
const history = [];   // {role: "user"|"jev", text} for free chat mode

// ---- topic index bar (visible in wide mode) --------------------------------
TOPICS.forEach(t => {
  const c = document.createElement("span");
  c.className = "chip";
  const col = topicColor[t.name];
  c.style.color = col; c.style.borderColor = col + "55"; c.style.background = col + "14";
  c.title = t.desc;
  c.innerHTML = `${t.name} <span class="n">${t.count}</span>`;
  topicbar.appendChild(c);
});
function syncTopicbar() { topicbar.classList.toggle("show", poolSel.value === "wide"); }
poolSel.addEventListener("change", () => { syncTopicbar(); renderSuggestions(); });
syncTopicbar();

// ---- suggestion pills ------------------------------------------------------
function renderSuggestions() {
  const box = document.getElementById("sugg");
  if (!box) return;
  box.querySelectorAll(".sq").forEach(el => el.remove());
  const set = poolSel.value === "wide" ? SUGGESTIONS.wide : SUGGESTIONS.other;
  set.forEach(q => {
    const btn = document.createElement("button");
    btn.type = "button"; btn.className = "sq"; btn.textContent = q;
    btn.addEventListener("click", () => { input.value = q; form.requestSubmit(); });
    box.appendChild(btn);
  });
}
renderSuggestions();

// ---- new chat --------------------------------------------------------------
document.getElementById("reset").addEventListener("click", () => {
  if (send.disabled) return;   // not while Jev is mid-answer
  history.length = 0;
  msgs.innerHTML = '<div id="sugg"><div class="hello">Fresh start — Jev remembers ' +
    'nothing.<br>Try one of these, or ask your own:</div></div>';
  renderSuggestions();
  input.focus();
});

// ---- chat ------------------------------------------------------------------
function row(cls, withAvatar) {
  const r = document.createElement("div"); r.className = "row " + cls;
  let avatar = null;
  if (withAvatar) {
    avatar = document.createElement("div"); avatar.className = "avatar busy";
    avatar.textContent = "J"; r.appendChild(avatar);
  }
  const b = document.createElement("div"); b.className = "bubble";
  r.appendChild(b); msgs.appendChild(r); log.scrollTop = log.scrollHeight;
  return [b, avatar];
}

function partSpan(text, color, tooltip, delayMs, p) {
  const s = document.createElement("span");
  s.className = "part";
  s.style.background = color + "1f"; s.style.color = color;
  s.style.borderColor = color + "45";
  s.style.animationDelay = (delayMs / 1000) + "s";
  s.title = tooltip; s.textContent = text;
  if (p != null) {
    const pp = document.createElement("span"); pp.className = "pp";
    pp.textContent = p.toFixed(2).replace(/^0/, "");   // 0.31 -> .31
    s.appendChild(pp);
  }
  return s;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = input.value.trim();
  if (!q || send.disabled) return;
  input.value = "";
  const sugg = document.getElementById("sugg");
  if (sugg) sugg.remove();
  row("user")[0].textContent = q;
  const [b, avatar] = row("jev", true);
  const think = document.createElement("span");
  think.className = "dots"; think.innerHTML = "<i></i><i></i><i></i>";
  b.appendChild(think);
  send.disabled = true;
  const wide = poolSel.value === "wide";
  try {
    const free = document.getElementById("freechat").checked;
    const res = await fetch("/api/ask", {
      method: "POST", headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question: q, pool: poolSel.value,
                            long: document.getElementById("long").checked,
                            history: free ? history : []})});
    if (!res.ok) throw new Error(await res.text());
    const d = await res.json();
    think.remove();
    if (!d.parts.length) {
      const s = document.createElement("span"); s.className = "silent";
      s.textContent = d.ended_by === "missing"
        ? "(declined: the phrase it wanted is not on the list)"
        : "(said nothing)";
      b.appendChild(s);
    }
    const STEP = 240;   // staggered reveal: one phrase per beat
    d.parts.forEach((p, i) => {
      const t = d.trace[i];
      const color = (wide && t.topic) ? (topicColor[t.topic] || COLORS[0])
                                      : COLORS[i % COLORS.length];
      const tip = `turn ${i + 1} · p=${t.p} · confidence=${t.confidence} · ${t.mode}`
        + (t.topic ? ` · topic: ${t.topic} (p=${t.topic_p})` : "");
      b.appendChild(partSpan(p, color, tip, i * STEP, t.p));
    });
    // topics used by this answer, in order of first use
    if (wide) {
      const used = [];
      d.parts.forEach((p, i) => {
        const tp = d.trace[i].topic;
        const hit = used.find(u => u.name === tp);
        if (hit) hit.count++; else if (tp) used.push({name: tp, count: 1});
      });
      if (used.length) {
        const chips = document.createElement("div"); chips.className = "chips";
        used.forEach(u => {
          const c = document.createElement("span"); c.className = "chip";
          const col = topicColor[u.name] || COLORS[0];
          c.style.color = col; c.style.borderColor = col + "55";
          c.style.background = col + "14";
          c.innerHTML = `${u.name}${u.count > 1 ? ` <span class="n">&times;${u.count}</span>` : ""}`;
          const meta = TOPICS.find(t => t.name === u.name);
          if (meta) c.title = meta.desc;
          chips.appendChild(c);
        });
        b.appendChild(chips);
      }
    }
    const m = document.createElement("div"); m.className = "meta";
    m.textContent = `${d.parts.length} turns · ${d.requests} requests · ended by `
      + d.ended_by + ` · vocabulary ${d.method.vocab}`;
    b.appendChild(m);
    history.push({role: "user", text: q});
    history.push({role: "jev", text: d.answer || (d.ended_by === "missing"
      ? "(declined: the phrase I want is not on the list)" : "(said nothing)")});
    foot.innerHTML = `<span class="live"></span>phrase-by-phrase selection · $`
      + d.session_cost.toFixed(5) + " this session";
  } catch (err) {
    think.remove();
    const s = document.createElement("span"); s.className = "silent";
    s.textContent = "(error: " + err.message + ")";
    b.appendChild(s);
  }
  if (avatar) avatar.classList.remove("busy");
  send.disabled = false;
  log.scrollTop = log.scrollHeight;
  input.focus();
});
</script>
</body>
</html>
"""


def _page() -> bytes:
    opts = "".join(f'<option value="{k}"{" selected" if k == WIDE else ""}>{label}</option>'
                   for k, (label, _) in POOLS.items())
    topics = json.dumps([{"name": name, "desc": desc, "count": len(bag)}
                         for name, (desc, bag) in TOPICS.items()])
    return PAGE.replace("%OPTIONS%", opts).replace("%TOPICS%", topics).encode()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._send(200, _page(), "text/html; charset=utf-8")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/ask":
            self._send(404, b"not found", "text/plain")
            return
        try:
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            question = str(body["question"]).strip()[:500]
            pool_key = body.get("pool", "identity")
            if pool_key not in POOLS:
                pool_key = "identity"
            focus = LONG_FOCUS if body.get("long") else BASE_FOCUS
            if not question:
                raise ValueError("empty question")
            state: dict = {"question": question}
            transcript = _transcript(body.get("history") or [])
            if transcript:
                state["conversation_so_far"] = transcript
            if pool_key == WIDE:
                res = compose_wide(JEV, state, "question")
            else:
                pool = POOLS[pool_key][1]()
                res = compose(JEV, state, "question", pool, focus=focus)
            out = {"answer": res["answer"], "parts": res["parts"], "trace": res["trace"],
                   "ended_by": res["ended_by"], "requests": res["requests"],
                   "method": res["method"], "with_history": bool(transcript),
                   "session_cost": round(JEV.cost, 6)}
            self._send(200, json.dumps(out).encode(), "application/json")
        except Exception as e:  # surface the reason in the chat bubble
            self._send(500, str(e).encode(), "text/plain")

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"  {fmt % args}")


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Talking to Jev at http://{HOST}:{PORT}  (Ctrl-C to stop; local only, no auth)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n{JEV.requests} requests, ${JEV.cost:.5f} this session")


if __name__ == "__main__":
    main()
