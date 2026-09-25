---
name: event-sourcing
description: Event sourcing — an append-only log of domain events as the source of truth, pure decide/evolve functions, and projections as folds (CQRS). Use for audit trails, temporal queries, undo or replay, replica synchronization, or workflow state machines.
---

# Event sourcing

> *functional-architecture.org:* "Event Sourcing (ES) is an architectural pattern where the application's state is not stored directly, but is determined by an immutable, ordered sequence of domain events saved in an append-only event store. This sequence, or event log, becomes the single source of truth and allows for state reconstruction to any point in the past, enabling powerful auditability and temporal queries. Event Sourcing is often a great fit for functional architecture as events are immutable facts and application state is derived by applying a pure function (a reducer or projector) that folds these events over a starting state, ensuring a deterministic and traceable business logic." (Pattern page: short description only; long form upstream TODO.)

## The functional shape

- **Events** are immutable facts in the past tense (`Deposited`, `Withdrawn`), a sum type.
- **`evolve :: State -> Event -> State`** applies one fact. Pure, total, never fails — the fact already happened.
- **`decide :: Command -> State -> Either Rejection [Event]`** checks a request against the current state and returns the facts to record. Pure; all business rules live here.
- **State = `foldl evolve initial events`.** Any past state is a prefix fold; any read model is another fold (a **projection**).
- **The shell** loads the stream, folds, calls `decide`, appends the new events *conditionally on the expected version* (optimistic concurrency), and publishes them.

This is `functional-core-imperative-shell` with time made explicit: the core never touches storage, and replaying the log is running the core again.

## Procedure

1. **Name the events** from the domain's language, in the past tense, carrying the data that *happened* (not the data to recompute it).
2. **Write `evolve`** as a total function; derive the current state from events only.
3. **Write `decide`** for each command: validate against the state, return events or a typed rejection (`composable-error-handling`).
4. **Write projections** for each read model (balances, dashboards, search indexes); they are folds too and can be rebuilt from scratch.
5. **Make handling idempotent:** a retried command or re-delivered event must not apply twice (carry ids; deduplicate).
6. **Plan for evolution:** events are forever. Version them and *parse* old versions into the current model at read time (`parse-dont-validate`, upcasting); never rewrite history in place.
7. **Test with given/when/then on the pure functions:** *given* past events, *when* a command, *then* these events or this rejection; and property-test that replaying any valid history never violates invariants.

Done when: all state is derived from the log by pure folds, every command is decided by a pure function over that state, appends are conditional on the stream version, and read models can be rebuilt from the log.

## Example: an account

**Haskell**

```haskell
data Event = Opened String | Deposited Int | Withdrawn Int deriving (Eq, Show)

data Command = Open String | Deposit Int | Withdraw Int

data State = NotOpened | Active String Int -- owner, balance
  deriving (Eq, Show)

data Rejection = AlreadyOpen | NotOpen | NonPositiveAmount | InsufficientFunds deriving (Eq, Show)

evolve :: State -> Event -> State -- total: facts are not up for debate
evolve _ (Opened who) = Active who 0
evolve (Active who b) (Deposited n) = Active who (b + n)
evolve (Active who b) (Withdrawn n) = Active who (b - n)
evolve NotOpened _ = NotOpened -- cannot occur in a log produced by `decide`

decide :: Command -> State -> Either Rejection [Event]
decide (Open who) NotOpened = Right [Opened who]
decide (Open _) (Active _ _) = Left AlreadyOpen
decide _ NotOpened = Left NotOpen
decide (Deposit n) (Active _ _)
  | n <= 0 = Left NonPositiveAmount
  | otherwise = Right [Deposited n]
decide (Withdraw n) (Active _ balance)
  | n <= 0 = Left NonPositiveAmount
  | n > balance = Left InsufficientFunds
  | otherwise = Right [Withdrawn n]

replay :: [Event] -> State
replay = foldl evolve NotOpened

-- A projection: a different fold over the same log.
totalDeposited :: [Event] -> Int
totalDeposited es = sum [n | Deposited n <- es]

-- given [Opened "alyssa", Deposited 100], when Withdraw 150, then Left InsufficientFunds
example :: Either Rejection [Event]
example = decide (Withdraw 150) (replay [Opened "alyssa", Deposited 100])
```

**TypeScript**

```typescript
type Event = { type: "opened"; owner: string } | { type: "deposited"; amount: number } | { type: "withdrawn"; amount: number };
type Command = { type: "open"; owner: string } | { type: "deposit"; amount: number } | { type: "withdraw"; amount: number };
type State = { status: "notOpened" } | { status: "open"; owner: string; balance: number };
type Rejection = "alreadyOpen" | "notOpen" | "nonPositiveAmount" | "insufficientFunds";

export function evolve(s: State, e: Event): State {
  switch (e.type) {
    case "opened": return { status: "open", owner: e.owner, balance: 0 };
    case "deposited": return s.status === "open" ? { ...s, balance: s.balance + e.amount } : s;
    case "withdrawn": return s.status === "open" ? { ...s, balance: s.balance - e.amount } : s;
  }
}

export function decide(c: Command, s: State): { ok: true; events: Event[] } | { ok: false; rejection: Rejection } {
  const reject = (rejection: Rejection) => ({ ok: false as const, rejection });
  if (c.type === "open") return s.status === "notOpened" ? { ok: true, events: [{ type: "opened", owner: c.owner }] } : reject("alreadyOpen");
  if (s.status !== "open") return reject("notOpen");
  if (c.amount <= 0) return reject("nonPositiveAmount");
  if (c.type === "withdraw" && c.amount > s.balance) return reject("insufficientFunds");
  return { ok: true, events: [c.type === "deposit" ? { type: "deposited", amount: c.amount } : { type: "withdrawn", amount: c.amount }] };
}

export const replay = (events: readonly Event[]): State => events.reduce(evolve, { status: "notOpened" });

export const totalDeposited = (events: readonly Event[]) =>
  events.reduce((sum, e) => (e.type === "deposited" ? sum + e.amount : sum), 0);
```

**C++**

```cpp
#include <expected>
#include <numeric>
#include <string>
#include <type_traits>
#include <variant>
#include <vector>

struct Opened { std::string owner; };
struct Deposited { int amount; };
struct Withdrawn { int amount; };
using Event = std::variant<Opened, Deposited, Withdrawn>;

struct Open { std::string owner; };
struct Deposit { int amount; };
struct Withdraw { int amount; };
using Command = std::variant<Open, Deposit, Withdraw>;

struct State { bool opened = false; std::string owner; int balance = 0; };
enum class Rejection { AlreadyOpen, NotOpen, NonPositiveAmount, InsufficientFunds };

State evolve(State s, const Event& e) {
  std::visit([&](const auto& ev) {
    using E = std::decay_t<decltype(ev)>;
    if constexpr (std::is_same_v<E, Opened>) s = State{true, ev.owner, 0};
    else if constexpr (std::is_same_v<E, Deposited>) s.balance += ev.amount;
    else s.balance -= ev.amount;
  }, e);
  return s;
}

std::expected<std::vector<Event>, Rejection> decide(const Command& c, const State& s) {
  using R = std::expected<std::vector<Event>, Rejection>;
  return std::visit([&](const auto& cmd) -> R {
    using C = std::decay_t<decltype(cmd)>;
    if constexpr (std::is_same_v<C, Open>) {
      if (s.opened) return std::unexpected(Rejection::AlreadyOpen);
      return std::vector<Event>{Opened{cmd.owner}};
    } else {
      if (!s.opened) return std::unexpected(Rejection::NotOpen);
      if (cmd.amount <= 0) return std::unexpected(Rejection::NonPositiveAmount);
      if constexpr (std::is_same_v<C, Withdraw>) {
        if (cmd.amount > s.balance) return std::unexpected(Rejection::InsufficientFunds);
        return std::vector<Event>{Withdrawn{cmd.amount}};
      } else {
        return std::vector<Event>{Deposited{cmd.amount}};
      }
    }
  }, c);
}

State replay(const std::vector<Event>& events) {
  return std::accumulate(events.begin(), events.end(), State{}, evolve);
}
```

## When not to, and what to watch

- Plain CRUD with no need for history, audit, or temporal questions: a table is simpler.
- Read models are eventually consistent with the log; design the UI and processes for that.
- Deleting personal data from an immutable log needs a plan (crypto-shredding, separate stores).
- Events are an API to your future self and to other services: version them deliberately. Experience from the field: event-based architectures made later requirements (undoing configuration changes, database thinning, peer-to-peer synchronization) feasible — and early event-design mistakes lived for a decade.
- Making time explicit in a *model* does not require event-sourcing the *implementation* (`late-decision-making`).

## Related skills

`functional-core-imperative-shell` · `immutability` · `algebraic-modelling` (projections as folds/monoids) · `make-illegal-states-unrepresentable` (state machines) · `property-based-testing` · `parse-dont-validate` (reading old event versions) · `late-decision-making`

## Sources

- functional-architecture.org, [Event Sourcing](https://functional-architecture.org/event_sourcing/) (pattern; short description, long form upstream TODO).
- Marco Sampellegrini, [Architecting Functional Programs](https://dl.acm.org/doi/10.1145/3677998.3678219) (FUNARCH 2024 keynote) — event sourcing, CQRS, and Domain-Driven Design for large systems.
- Michael Sperber, experience report on *Lokalisierung*, a 10-year event-based, peer-to-peer configuration system ([FUNARCH 2026](https://functional-architecture.org/events/funarch-2026/)).
- functional-architecture.org, [Late Decision Making](https://functional-architecture.org/late/) (draft) — explicit time in the model versus event sourcing in the implementation.
- Scott Wlaschin, [Choosing properties in practice, part 1](https://fsharpforfunandprofit.com/posts/property-based-testing-3/) — idempotence for message-based systems.
