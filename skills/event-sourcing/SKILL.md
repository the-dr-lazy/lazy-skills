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

## The event store, and why `evolve` stays pure

Young's minimal event store has two operations and no general querying: read all events of an aggregate in version order, and append events with an **expected version**, checked in one transaction (a mismatch raises a concurrency error; otherwise each event is inserted with an incremented version). Aggregate ids are the only partition point; queries go to read models. Three consequences for the pure core:

- **Events are past tense, commands are imperative, and the two must not mix.** Replaying "add 2 socks" would re-run its behaviors (reserving stock through a web service), and the rules may have changed since. There is "a contextual difference between returning to a given state and attempting to transition to a new one": `evolve` applies facts without effects and without re-validating, and `decide` is where rules live.
- **There is no delete.** Undo is a new *reversal* event, which also leaves the trail that the item was once there. An append-only log also distributes more easily than an updating store, since there are far fewer locks.
- **A ledger is the model.** Store the deltas, and the running total can be re-derived and reconciled from the beginning of time.

**Snapshots are a heuristic, not part of the model.** A snapshot is a serialized aggregate at a version, and conceptually the stream is still complete. Store it in its own table keyed by aggregate and version, written by an asynchronous snapshotter. A snapshot placed inside the stream competes with writers, so on a busy aggregate the snapshotter can keep losing the optimistic-concurrency race; a separate one is valid *at the version it was taken*, whatever the latest version is. Serialize with a Memento or custom format so the snapshot schema versions independently of the domain object, and start without snapshots: they can always be added later.

**Projections in practice** (Dudycz). A projection is usually a left fold of events over the read model's state; set-based aggregates can be computed in batches. Projections may be synchronous, updated in the same transaction as the append when events and read models share a database, so eventual consistency is a choice and not a requirement. To rebuild, truncate and replay if downtime is acceptable, or build the new read model beside the old one, catch up (then process live events), and switch queries over. Assume at-least-once delivery, so make handling idempotent: put the resulting state in the event (which couples producer and consumer), or compare the event's position with the read model's stored checkpoint (his general recommendation), or store handled event ids per projection so rebuilds and new projections still work. Give each piece of read-model data one writer, and partition by projection, module, or customer before reaching for cleverness. Ask the business what is worse than a stale screen before promising freshness; UX tricks such as not redirecting to the cart after "add to cart" avoid many consistency problems.

**Event design pitfalls** (Dudycz's anti-patterns). *Property sourcing*: `FirstNameChanged` and `LastNameChanged` are table changes, not business facts; group by the operation (`PersonalDataUpdated`) or name the business event. *State obsession*: `BalanceUpdated {amount: -50}` flattens what happened; prefer `CashWithdrawnFromATM`, asking "what happened?" instead of "what changed?". Adding the resulting balance to such events is a pragmatic redundancy, since it keeps the calculation in the write model, freezes it when tax rules change, and makes projections idempotent, but treat it as a carefully made optimization: events should be as small as possible, but not smaller.

**When not to use it.** Young ties the value of an event log to the places where you would apply domain-driven design, where the business gets competitive advantage; elsewhere the return may be negative. The costs are real: modelling every behavior and storing every event is more expensive. The payoff is retroactive: a new report can be back-populated from the start of the log, as with "items added then removed from carts", which a current-state store never recorded.

## Procedure

1. **Name the events** from the domain's language, in the past tense, carrying the data that *happened* (not the data to recompute it).
2. **Write `evolve`** as a total function; derive the current state from events only.
3. **Write `decide`** for each command: validate against the state, return events or a typed rejection (`composable-error-handling`).
4. **Write projections** for each read model (balances, dashboards, search indexes); they are folds too and can be rebuilt from scratch.
5. **Make handling idempotent:** a retried command or re-delivered event must not apply twice (carry ids; deduplicate).
6. **Plan for evolution:** events are forever. Version them and *parse* old versions into the current model at read time (`parse-dont-validate`, upcasting); never rewrite history in place. Climb this ladder only as far as needed:
   - *Non-breaking changes first.* A new optional field is nullable (old events simply lack it). A new required field gets a default that matches the old logic. A rename can keep the stored name and map it in the serializer, at the cost of consumers still seeing the old name.
   - *Upcasters* for structural changes: a pure function from the old shape to the current one, plugged in between deserialization and application logic. It may use metadata (a user id recorded on the event), but cannot guess what was never recorded. A *downcaster* serves readers that expect the old shape.
   - *Stream transformations* when N old events become one (or the reverse); grouping by a correlation id in the metadata tells you which events belonged to the same command.
   - *Migration* (read the old stream, write a new stream or store, switch over) only if you need a clean log; otherwise keep the old events, since precise history, bugs included, is valid.
   Record correlation and user ids in metadata from the start. Map event type names explicitly: a convention-based mapper can silently change the stored name in a refactoring. Dudycz adds that the frequency of schema changes is usually overestimated, constant change signals a modelling problem, and short-lived streams allow a two-phase deployment: support both schemas, then delete the old code once no live aggregate holds old events.
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
- Greg Young, [CQRS Documents](https://github.com/keyvanakbary/cqrs-documents) (2010; read the AsciiDoc port by Keyvan Akbary, which leaves the content unchanged: *Events as a Storage Mechanism*, *Building an Event Storage*, *CQRS and Event Sourcing*) — events as deltas, past tense versus commands, reversal instead of delete, the two-operation event store, rolling snapshots, the business value and cost of the log.
- Oskar Dudycz, [Simple patterns for events schema versioning](https://event-driven.io/en/simple_events_versioning_patterns/) (2021), [Guide to Projections and Read Models in Event-Driven Architecture](https://event-driven.io/en/projections_and_read_models_in_event_driven_architecture/) (2023), [Property Sourcing](https://event-driven.io/en/property-sourcing/) (2021), [State Obsession](https://event-driven.io/en/state-obsession/) (2021) (read from the [site's source](https://github.com/oskardudycz/event-driven.io)) — the versioning ladder, projection rebuilds and idempotency, and two event-modelling anti-patterns.
