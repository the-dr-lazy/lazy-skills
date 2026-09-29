---
name: architecture-as-code
description: Architecture as code — encode architectural decisions (layers, dependencies, effect permissions, protocols) in types and code, and generate diagrams from the code. Use when documenting or enforcing an architecture, when diagrams drift from code, or when adding architecture checks to CI.
---

# Architecture as code

> *functional-architecture.org:* "Functional Software Architecture allows many architectural decisions to be expressed in code. We may still use diagrams and descriptions as supporting documentation, but the source of truth is always to be found in the code." (Principle page upstream TODO.)

Diagrams and wiki pages describe the architecture you intended; code is the architecture you have. When decisions live only in documents, they drift. Functional programming offers many ways to make decisions **checkable** by the compiler or a test, and to **derive** documentation from the code instead of the other way round.

## What can live in code

| Decision | Expressed as | Checked by |
|---|---|---|
| Which component may do which effects (DB, network, clock) | effect constraints, capability parameters (`UserStore :> es`, `MonadDB m`) | the type checker (`composable-effects`) |
| Pure core vs shell; single entry and exit | types that only accept pure models (`mvc`'s `runMVC :: s -> Model s a b -> Managed (View b, Controller a) -> IO s`) | the type checker (`functional-core-imperative-shell`) |
| Protocols, workflows, lifecycles | state machines as data; typestate (`Conn Open`) | the type checker; generated diagrams (`correctness-by-construction`) |
| Module boundaries and dependency direction | export lists, package boundaries, vertical module organization | the compiler; dependency-rule tests in CI (e.g. dependency-cruiser, ArchUnit-style checks) |
| Domain rules | types that make illegal states unrepresentable | the type checker (`make-illegal-states-unrepresentable`) |
| Data flow between representations | bidirectional transformations (lenses) declared once | the type checker, round-trip properties (`bidirectional-data-transformations`) |
| Systems, containers, components, and their relationships | a C4 model in a text DSL (Structurizr): one model, many generated views | `validate` and `inspect` in CI (the latter's return code counts the violations shown); diagrams exported to PlantUML, Mermaid, SVG |

A model in a diagram DSL is a *description*, not a check: nothing ties it to the code by default. Structurizr's own "as code" rationale lists drift detection between code and model as a workflow for an AI agent, not as something the tool does. So the last row is the weakest in the table. Keep it honest by generating the model from the code (as in the example below) or by pairing it with the dependency-rule tests above. What the DSL does give: plain text in version control, so diffs and pull requests work, and a clean split between the *model* (content) and *views* (presentation), which makes versions easier to diff. Architecture decision records can live beside it (`!adrs` imports adr-tools, MADR, and log4brains formats). Costs: a steeper learning curve than a drawing tool, and non-coding architects are shut out.

A caution from the other direction: "a sufficiently detailed spec is code." Specifications precise enough to generate systems from have the complexity of code; put the precision into the code and generate the *documentation* from it, not the code from documents.

## Procedure

1. **List the architectural decisions** that matter (boundaries, allowed dependencies, effect permissions, protocols, invariants).
2. **For each, pick the strongest mechanism available:** types > compiler-checked module boundaries > automated tests over the code structure > generated documentation > prose.
3. **Make one representation the source of truth** (a transition table, a capability list, a module map) and derive everything else from it — implementation, diagrams, docs.
4. **Fail the build on violation** (type errors, dependency tests), not a review comment.
5. **Keep a short prose record of *why*** (ADRs) next to the code; the code says *what*.

Done when: each listed decision is either enforced by the compiler/CI or generated from code, and no diagram in the repository is hand-maintained for something the code already states.

## Example: one transition table, a checked state machine, and a generated diagram

**Haskell**

```haskell
import Data.List (intercalate)

data State = Draft | Submitted | Approved | Rejected deriving (Eq, Show, Enum, Bounded)
data Event = Submit | Approve | Reject | Revise deriving (Eq, Show, Enum, Bounded)

-- The single source of truth.
transitions :: [(State, Event, State)]
transitions =
  [ (Draft, Submit, Submitted)
  , (Submitted, Approve, Approved)
  , (Submitted, Reject, Rejected)
  , (Rejected, Revise, Draft)
  ]

-- Derived behaviour.
step :: State -> Event -> Maybe State
step s e = case [t | (from, ev, t) <- transitions, from == s, ev == e] of
  t : _ -> Just t
  [] -> Nothing

-- Derived documentation (Graphviz), which can never disagree with `step`.
toDot :: String
toDot =
  "digraph workflow {\n"
    <> intercalate "\n" ["  " <> show from <> " -> " <> show to <> " [label=" <> show (show ev) <> "];" | (from, ev, to) <- transitions]
    <> "\n}\n"
```

**TypeScript**

```typescript
const states = ["draft", "submitted", "approved", "rejected"] as const;
type State = (typeof states)[number];
type Event = "submit" | "approve" | "reject" | "revise";

// The single source of truth.
const transitions: ReadonlyArray<readonly [State, Event, State]> = [
  ["draft", "submit", "submitted"],
  ["submitted", "approve", "approved"],
  ["submitted", "reject", "rejected"],
  ["rejected", "revise", "draft"],
];

// Derived behaviour.
export const step = (s: State, e: Event): State | undefined =>
  transitions.find(([from, ev]) => from === s && ev === e)?.[2];

// Derived documentation (Graphviz).
export const toDot = (): string =>
  `digraph workflow {\n${transitions.map(([from, ev, to]) => `  ${from} -> ${to} [label="${ev}"];`).join("\n")}\n}\n`;
```

**C++**

```cpp
#include <array>
#include <optional>
#include <string>
#include <tuple>

enum class State { Draft, Submitted, Approved, Rejected };
enum class Event { Submit, Approve, Reject, Revise };

constexpr const char* name(State s) {
  constexpr const char* names[] = {"Draft", "Submitted", "Approved", "Rejected"};
  return names[static_cast<int>(s)];
}
constexpr const char* name(Event e) {
  constexpr const char* names[] = {"Submit", "Approve", "Reject", "Revise"};
  return names[static_cast<int>(e)];
}

// The single source of truth.
constexpr std::array<std::tuple<State, Event, State>, 4> transitions{{
    {State::Draft, Event::Submit, State::Submitted},
    {State::Submitted, Event::Approve, State::Approved},
    {State::Submitted, Event::Reject, State::Rejected},
    {State::Rejected, Event::Revise, State::Draft},
}};

// Derived behaviour, checkable at compile time.
constexpr std::optional<State> step(State s, Event e) {
  for (const auto& [from, ev, to] : transitions)
    if (from == s && ev == e) return to;
  return std::nullopt;
}
static_assert(step(State::Draft, Event::Approve) == std::nullopt);  // no skipping review

// Derived documentation (Graphviz).
std::string toDot() {
  std::string out = "digraph workflow {\n";
  for (const auto& [from, ev, to] : transitions)
    out += std::string("  ") + name(from) + " -> " + name(to) + " [label=\"" + name(ev) + "\"];\n";
  return out + "}\n";
}
```

## Related skills

`correctness-by-construction` · `composable-effects` · `functional-core-imperative-shell` · `modularization` · `everything-as-a-value` (a state machine as a value) · `decoupled-by-default` · `formal-verification`

## Sources

- functional-architecture.org, [Architecture as Code](https://functional-architecture.org/aac/) (principle page; upstream TODO).
- Simon Brown et al., Structurizr documentation: [Why "as code"?](https://docs.structurizr.com/as-code), [ADRs](https://docs.structurizr.com/dsl/adrs), and the CLI pages for [`validate`](https://docs.structurizr.com/cli/validate) and [`inspect`](https://docs.structurizr.com/cli/inspect) (read from the site's [source repository](https://github.com/structurizr/structurizr.github.io)) — models as code for the C4 model, model/view separation, CI validation, and the limits of a hand-written model.
- Marco Perone, Georgios Karachalias, [Crème de la Crem: Composable Representable Executable Machines](https://dl.acm.org/doi/10.1145/3609025.3609480) (FUNARCH 2023) — state machines that are both executable and representable, generating diagrams from the implementation.
- Gabriella Gonzalez, [Model-view-controller, Haskell-style](https://haskellforall.com/2014/04/model-view-controller-haskell-style) (2014) — the architecture enforced by one type signature; [Module organization guidelines for Haskell projects](https://haskellforall.com/2021/05/module-organization-guidelines-for) (2021); [A sufficiently detailed spec is code](https://haskellforall.com/2026/03/a-sufficiently-detailed-spec-is-code) (2026).
- Will Crichton, [Typed Design Patterns for the Functional Era](https://dl.acm.org/doi/10.1145/3609025.3609477) (FUNARCH 2023).
