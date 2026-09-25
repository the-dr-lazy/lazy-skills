---
name: make-illegal-states-unrepresentable
description: Make illegal states unrepresentable — shape types so every value is a legal state (sum types, sum-of-products, enums, invariant-carrying structures, state machines). Use when designing or reviewing a data model with optional fields, status flags, "at least one of" rules, or invariants in comments.
---

# Make illegal states unrepresentable

A data model expresses intent. It captures intent adequately when **every value that makes sense is representable and no value that does not make sense is**. "Make illegal states unrepresentable" (Yaron Minsky, 2010) targets the second half; the first half ("make all legal states representable") matters just as much.

The shift in thinking: stop asking *"how do I rule out the bad values?"* (negative space, post-hoc restrictions) and ask *"how do I build only the good ones?"* (positive space, construction rules). A datatype is a set of axioms and inference rules; design those rules so that anything built from them is valid.

## Techniques, strongest first

1. **Sum of products instead of a flat product.** A record with a status tag and a pile of optional fields admits nonsense (a `Connecting` connection with a `when_disconnected` time). Give each state its own case carrying exactly the fields that exist in that state; keep fields common to all states in the outer record.
2. **Group fields that are present together.** Two options that are "both `Some` or both `None`" become one optional pair: `last_ping : (Time * int) option`.
3. **Enumerations instead of strings, ints, or several booleans.** Three booleans for a traffic light admit 8 states, 3 legal. An enum with 3 cases admits exactly the 3.
4. **Pick a structure with the invariant built in.** A `Map` has no duplicate keys; `NonEmpty` has a head; a list of pairs has even length; a function `Time -> Maybe Double` has no contradictory samples.
5. **"At least one of …" rules.** Enumerate the combinations; if they explode, look for the missing concept. *"A contact has an email or postal address or both"* is a 3-case sum. *"At least one of email, post, home phone, work phone"* is 15 combinations — the insight is a new `ContactMethod` sum, and "at least one" becomes `primary : ContactMethod; secondary : ContactMethod list`.
6. **Explicit state machines instead of flags.** `IsVerified: bool`, `Status` enums beside optional timestamps, and chains of `if x.IsSome` are implicit states. Make one case per state with its data; make each event a function from the whole machine to the whole machine.
7. **When a property resists structural encoding** (a number in a range, a regex-shaped string), fall back to an abstract type with a smart constructor — an extrinsic guarantee, weaker than a structural one (`smart-constructor`, `names-are-not-type-safety`). In a dynamically typed language, the same sum-of-products refactoring still applies, with constructor functions that assert at runtime.

## Procedure

1. Write down the business rules and invariants currently enforced by comments, validation code, or tribal knowledge.
2. Enumerate the legal states. Count the values the current type admits versus the legal ones; the difference is the bug surface.
3. Encode the legal states with the techniques above. Prefer a single source of truth; derived or duplicated fields are an illegal state waiting to happen (copies drifting apart).
4. Let the compiler find every consumer (pattern matches break); handle each case explicitly.
5. Delete the validation code, null checks, and "impossible" branches that the new type made dead.
6. Where permissive external formats (JSON, SQL, forms) meet the model, add one parse step — an anti-corruption layer (`parse-dont-validate`).

Done when: every value the type admits corresponds to a legal domain state (or the remainder is guarded by a single, named smart constructor), and no consumer contains a branch for a state the domain forbids.

## Example: connection state (after Minsky)

**Haskell**

```haskell
import Data.Time (UTCTime)

data Ping = Ping {pingTime :: UTCTime, pingId :: Int}

data ConnectionState
  = Connecting UTCTime -- when initiated
  | Connected (Maybe Ping) String -- last ping, if any; session id
  | Disconnected UTCTime -- when disconnected

data ConnectionInfo = ConnectionInfo {state :: ConnectionState, server :: String}

-- An event is a function from the whole state to the whole state.
receivedPing :: Ping -> ConnectionState -> ConnectionState
receivedPing ping (Connected _ session) = Connected (Just ping) session
receivedPing _ other = other -- a ping outside a session carries no information
```

**TypeScript**

```typescript
type Ping = { readonly at: Date; readonly id: number };

type ConnectionState =
  | { readonly tag: "connecting"; readonly whenInitiated: Date }
  | { readonly tag: "connected"; readonly lastPing: Ping | null; readonly sessionId: string }
  | { readonly tag: "disconnected"; readonly whenDisconnected: Date };

type ConnectionInfo = { readonly state: ConnectionState; readonly server: string };

const absurd = (x: never): never => {
  throw new Error(`unreachable: ${JSON.stringify(x)}`);
};

export function receivedPing(ping: Ping, s: ConnectionState): ConnectionState {
  switch (s.tag) {
    case "connected":
      return { ...s, lastPing: ping };
    case "connecting":
    case "disconnected":
      return s;
    default:
      return absurd(s); // adding a state breaks compilation here
  }
}

export const describe = (c: ConnectionInfo): string => `${c.server}: ${c.state.tag}`;
```

**C++**

```cpp
#include <chrono>
#include <optional>
#include <string>
#include <type_traits>
#include <variant>

using Time = std::chrono::system_clock::time_point;

struct Ping { Time at; int id; };
struct Connecting { Time whenInitiated; };
struct Connected { std::optional<Ping> lastPing; std::string sessionId; };
struct Disconnected { Time whenDisconnected; };

using ConnectionState = std::variant<Connecting, Connected, Disconnected>;

struct ConnectionInfo { ConnectionState state; std::string server; };

ConnectionState receivedPing(const Ping& ping, ConnectionState s) {
  return std::visit(
      [&](auto&& st) -> ConnectionState {
        using S = std::decay_t<decltype(st)>;
        if constexpr (std::is_same_v<S, Connected>) return Connected{ping, st.sessionId};
        else return st;
      },
      s);
}
```

The flat "before" version, the contact-method refactoring, a shopping-cart state machine, time series as maps and functions, and constructive "even list" / Peano types, all in three languages: [examples.md](examples.md).

## When not to

- The states carry no different behaviour in the domain (a blog post's Draft/Published when only the display layer filters). A tag is enough.
- Transitions happen outside the application (a nightly job reclassifies customers). Model the states; skip the machine.
- Business rules change faster than you can recompile. Consider data-driven rules or a rules engine.
- The precise type loses a standard API you rely on heavily (a bespoke `EvenList` needs its own `map`). Weigh the boilerplate (`boolean-blindness` discusses the trade-off).

## Why it matters architecturally

- **Simplicity:** fewer representable values leave less to reason about, and there is little one can do wrong with, say, a function.
- **Robustness:** every representable value must be handled *consistently by every consumer*. A time series as a list of pairs forces all consumers to agree on out-of-order, duplicate, and contradictory entries; a map defines the question away.
- **Decoupling:** invariants that are not in the type must be honoured by convention, which is implicit coupling between producer and every consumer.
- **Agentic coding:** an agent generating code against a tight type writes exhaustive matches; against a string or a bag of optionals it writes defensive branches, each a new place for bugs.

## Related skills

`parse-dont-validate` · `designing-with-types` (step-by-step refactoring of a whole model) · `boolean-blindness` · `smart-constructor` · `correctness-by-construction` · `names-are-not-type-safety` · `belt-and-suspenders` (the fallback when structure cannot rule a failure out) · `algebraic-modelling`

## Sources

- functional-architecture.org, [Make Illegal States Unrepresentable](https://functional-architecture.org/make_illegal_states_unrepresentable/) (principle page; sections *Smart constructors* and *Decoupling* are upstream TODO).
- Scott Wlaschin, [Designing with types: Making illegal states unrepresentable](https://fsharpforfunandprofit.com/posts/designing-with-types-making-illegal-states-unrepresentable/), [Discovering new concepts](https://fsharpforfunandprofit.com/posts/designing-with-types-discovering-the-domain/), [Making state explicit](https://fsharpforfunandprofit.com/posts/designing-with-types-representing-states/) (2013).
- Alexis King, [Types as axioms, or: playing god with static types](https://lexi-lambda.github.io/blog/2020/08/13/types-as-axioms-or-playing-god-with-static-types/) (2020).
- Wolf McNally, [Make Illegal States Unrepresentable](https://aipatternbook.com/make-illegal-states-unrepresentable), *Encyclopedia of Agentic Coding Patterns*.
- Yaron Minsky, [Effective ML Revisited](https://blog.janestreet.com/effective-ml-revisited/) (Jane Street), origin of the slogan; Richard Feldman, *Making Impossible States Impossible* (elm-conf 2016).
