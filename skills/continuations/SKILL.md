---
name: continuations
description: Continuations — the rest of a computation as a value (callbacks, CPS, delimited continuations, generators) to suspend, resume, or write multi-step workflows as straight-line code. Use for interactive web or survey flows, composing callback APIs, or choosing between continuations and state machines.
---

# Continuations

> *Upstream status:* the functional-architecture.org pattern page is TODO. This skill is synthesized from the sources listed at the end.

A **continuation** is the rest of a computation, reified as a value: a function that says what to do with a result. You already use them as callbacks — "here is what to do when the data arrives". Making them explicit lets you:

- **complete it later:** write code that someone else finishes by supplying the continuation (frameworks with callbacks, game-scripting hooks, a smart constructor taking `success`/`failure` handlers);
- **compose callback APIs** with the continuation monad (`ContT`), so nested callbacks read as sequential code;
- **suspend and resume:** a *delimited* continuation captures "the rest of this workflow" up to a boundary, so a multi-page web interaction can be written as a straight-line program that pauses at each page and resumes when the user answers.

## Architecture: workflows written as straight-line code

The Congame platform (economic studies with multi-round, branching participant flows) manages each participant's path through a study with **delimited continuations** (FUNARCH 2024). Positives: the study is ordinary sequential code, with branching and loops, instead of a hand-written state machine spread over request handlers. Challenges they report: **persisting data across requests**, **dynamic variables**, **memory leaks** from retained continuations, and **debugging** captured control flow. Those challenges are the decision criteria:

| Option | Readable as sequential code | Survives restarts / scales out | Inspectable |
|---|---|---|---|
| Native delimited continuations (Racket, Scheme, OCaml 5 effects) | yes | only if continuations can be serialized | poorly |
| Generators / async / coroutines (TS `function*`, C++20 coroutines) | yes | no (state lives in memory) | poorly |
| Continuations as data (a command tree / free monad, `Ask q (Answer -> Flow)`) | nearly | replay answers from a log to rebuild | yes |
| Explicit state machine | no | yes (state is a value) | yes |

A common robust design: write the workflow in continuation style, persist the *answers* (events), and rebuild the continuation by replaying them — continuations for readability, `event-sourcing` for durability.

## Lessons from a continuation-based web app (Racket's Continue tutorial)

- **A link can carry its own future.** `send/suspend/dispatch` hands the page generator `embed/url`, which turns a handler (a request-consuming closure) into a URL. Visiting it resumes the application at that handler, not at `start`. Because the handler is a local closure it sees the variables in scope: `show-counter n` links to a handler that calls `show-counter (+ n 1)`, so an interaction accumulates state without a session table, and the Back button falls back to an earlier phase. It also removes the "traffic cop" `start` function that dispatches on the kind of request.
- **State in closures is per continuation.** In the tutorial's first blog each browser window kept its own blog value; sharing required moving the blog into a mutable model shared by every session. Keep shared state out of the closures.
- **Persist the model, not the continuations.** The tutorial separates the model behind a module boundary ("we have no long-term interest in things like requests. What we do care about saving is our model"), makes its structures serializable (`#:prefab`), and later moves them into SQL. This matches the durable option in the table above: data outlives the run, continuations are rebuilt.
- **Resuming re-runs effects.** Reloading a page that mutated state repeats the mutation, the well-known "double-submit" problem. The fix is `redirect/get` after any state-changing request, so a reload lands on a safe URL. Treat every resumption point as one that can be entered again (Back, reload, a duplicated tab): make its effects idempotent or keep them out of the resumable part.

## Procedure

1. Identify the points where control must leave and later come back (a page, a message round-trip, a user decision, a callback).
2. Write the workflow sequentially against an interface that captures "ask and continue" (`Ask prompt (Answer -> Flow)`, `yield`, `await`, `ContT`).
3. Choose the runtime representation from the table: in-memory continuations for short-lived interactions; data + replay for durable ones; explicit state machines where inspection and migration matter most.
4. Bound resource use: expire suspended continuations; never capture large environments by accident.
5. For early exit alone, use `Either`/`ExceptT` or `return` — continuations are overkill there (`composable-error-handling`).

Done when: each interactive workflow reads top to bottom, each suspension point is explicit, and the chosen representation meets the durability requirement (restart, scale-out) or deliberately documents that it does not.

## Example: a branching survey that suspends at every question

The "server" stores each session's continuation and resumes it with the next answer.

**Haskell** (continuations as data)

```haskell
import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map
import Text.Read (readMaybe)

data Flow = Ask String (String -> Flow) | Done String

study :: Flow -- straight-line, branching code
study = Ask "How old are you?" $ \age ->
  case readMaybe age :: Maybe Int of
    Nothing -> Done "Please restart and enter a number."
    Just n | n < 18 -> Done "Thanks! This study is for adults."
    Just _ -> Ask "Favourite colour?" $ \colour ->
      Done ("Thanks! You chose " <> colour <> ".")

type Sessions = Map Int (String -> Flow) -- suspended continuations

start :: Int -> Sessions -> (Sessions, String)
start sid sessions = suspend sid study sessions

answer :: Int -> String -> Sessions -> (Sessions, String)
answer sid a sessions = case Map.lookup sid sessions of
  Nothing -> (sessions, "unknown session")
  Just k -> suspend sid (k a) sessions

suspend :: Int -> Flow -> Sessions -> (Sessions, String)
suspend sid (Ask q k) sessions = (Map.insert sid k sessions, q)
suspend sid (Done msg) sessions = (Map.delete sid sessions, msg)
```

**TypeScript** (generators are delimited continuations)

```typescript
type Flow = Generator<string, string, string>; // yields questions, receives answers, returns a message

function* study(): Flow {
  const age = Number(yield "How old are you?");
  if (!Number.isInteger(age)) return "Please restart and enter a number.";
  if (age < 18) return "Thanks! This study is for adults.";
  const colour = yield "Favourite colour?";
  return `Thanks! You chose ${colour}.`;
}

const sessions = new Map<number, Flow>(); // in memory: lost on restart

export function start(sid: number): string {
  const flow = study();
  sessions.set(sid, flow);
  return flow.next("").value; // the first question
}

export function answer(sid: number, a: string): string {
  const flow = sessions.get(sid);
  if (!flow) return "unknown session";
  const step = flow.next(a);
  if (step.done) sessions.delete(sid);
  return step.value;
}
```

**C++** (continuation-passing style with closures)

```cpp
#include <functional>
#include <map>
#include <memory>
#include <string>

struct Flow;
using Continuation = std::function<Flow(const std::string&)>;
struct Flow {
  std::string text;  // a question, or the final message
  Continuation next;  // empty when done
};

Flow study() {
  return {"How old are you?", [](const std::string& age) -> Flow {
            int n = 0;
            try { n = std::stoi(age); } catch (...) { return {"Please restart and enter a number.", nullptr}; }
            if (n < 18) return {"Thanks! This study is for adults.", nullptr};
            return {"Favourite colour?", [](const std::string& colour) -> Flow {
                      return {"Thanks! You chose " + colour + ".", nullptr};
                    }};
          }};
}

class Server {
public:
  std::string start(int sid) { return suspend(sid, study()); }
  std::string answer(int sid, const std::string& a) {
    auto it = sessions_.find(sid);
    if (it == sessions_.end()) return "unknown session";
    Continuation k = it->second;
    return suspend(sid, k(a));
  }
private:
  std::string suspend(int sid, Flow f) {
    if (f.next) sessions_[sid] = f.next;
    else sessions_.erase(sid);
    return f.text;
  }
  std::map<int, Continuation> sessions_;  // suspended continuations
};
```

## Related skills

`free-monads` (commands carrying continuations) · `event-sourcing` (durable replay of answers) · `composable-error-handling` (early exit without continuations) · `smart-constructor` (continuation-style success/failure handlers) · `everything-as-a-value` · `functional-core-imperative-shell`

## Sources

- functional-architecture.org, [Continuations](https://functional-architecture.org/continuations/) (pattern page; upstream TODO).
- Marc Kaufmann, Bogdan Popa, [Continuations: what have they ever done for us?](https://dl.acm.org/doi/10.1145/3677998.3678223) (FUNARCH 2024, experience report on Congame).
- Danny Yoo, Jay McCarthy, [Continue: Web Applications in Racket](https://docs.racket-lang.org/continue/) (read from the tutorial's Scribble source in [racket/web-server](https://github.com/racket/web-server/blob/master/web-server-doc/web-server/scribblings/tutorial/continue.scrbl): *Advanced Control Flow*, *Share and Share Alike*, *The Double Submit Error*, *Abstracting the Model*, *A Persistent Model*) — links bound to handlers, per-window state, the persistent model, `redirect/get`.
- Gabriella Gonzalez, [The Continuation Monad](https://haskellforall.com/2012/12/the-continuation-monad) (2012), [How the continuation monad works](https://haskellforall.com/2014/04/how-continuation-monad-works) (2014), [Breaking from a loop](https://haskellforall.com/2012/07/breaking-from-loop) (2012), [The visitor pattern is essentially the same thing as Church encoding](https://haskellforall.com/2021/01/the-visitor-pattern-is-essentially-same) (2021).
- Scott Wlaschin, [Designing with types: Single case union types](https://fsharpforfunandprofit.com/posts/designing-with-types-single-case-dus/) — constructors taking success and failure continuations.
