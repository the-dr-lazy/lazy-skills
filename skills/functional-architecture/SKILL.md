---
name: functional-architecture
description: Functional software architecture overview — values, principles, and patterns of functional-architecture.org mapped to the skills in this collection, for any language. Use when designing or reviewing an architecture functionally, when unsure which pattern applies, or when evaluating a technology against functional principles.
---

# Functional software architecture

> *functional-architecture.org:* "*Functional Software Architecture* refers to methods of construction and structure of large and long-lived software projects that are implemented in functional languages and released to real users, typically in industry." — functional programming in the large.

The ideas are not confined to functional languages. Every pattern here has been used — natively or by encoding — in TypeScript and C++ as well as Haskell, and each skill shows all three. What changes between languages is how much the compiler enforces and how much becomes convention (`functional-programming-languages`).

## Values → principles → patterns

- **Values** are ends in themselves and somewhat subjective.
- **Principles** are more objective: *if* you value X, *then* follow Y. A principle is also a **yardstick for new technology**: instead of following your gut about the latest framework, check it against composability, abstraction, coupling, and modelling.
- **Patterns** are the techniques that realize principles. A pattern cannot live entirely in a library: a mechanical part may (lenses for bidirectional transformations), but *when to use it and when not* cannot.

### Values

| Value | Meaning |
|---|---|
| Simplicity | Problem domains are complex enough; solutions should be as simple as possible. |
| Domain insight | Software development is as much about gaining insight into a domain as about running software. |
| Maintainability | Maintainability and malleability enable the whole creation process; since uncertainty is greatest at the start, build so decisions can be made later. |
| Correctness | Correct in the small and in the large. |
| Performance | Software has to be both correct and fast. |

### Principles → skills

| Principle | Skill |
|---|---|
| Immutability | `immutability` |
| Pure functions | `pure-functions` |
| Everything as a value | `everything-as-a-value` |
| Composition and closure | `composition-and-closure` |
| Algebraic modelling | `algebraic-modelling` |
| Airtight abstractions | `airtight-abstractions` |
| Architecture as code | `architecture-as-code` |
| Decoupled by default | `decoupled-by-default` |
| Late decision making | `late-decision-making` |
| Modularization | `modularization` |
| Make illegal states unrepresentable | `make-illegal-states-unrepresentable` |

### Patterns, tools, and techniques → skills

| Pattern | Skill |
|---|---|
| Functional core, imperative shell | `functional-core-imperative-shell` |
| Zipper | `zipper` |
| Continuations | `continuations` |
| Use of functional programming languages | `functional-programming-languages` |
| Expressive static type systems | `expressive-static-types` |
| Event sourcing | `event-sourcing` |
| Bidirectional data transformations | `bidirectional-data-transformations` |
| Embedded domain-specific languages | `embedded-dsl` |
| Composable effects | `composable-effects` (with `free-monads`, `algebraic-effect-systems`) |
| Composable error handling | `composable-error-handling` |
| Composable GUI libraries | `composable-guis` |
| Property-based testing | `property-based-testing` |
| Formal verification | `formal-verification` |
| Denotational design | `denotational-design` |
| Parse, don't validate | `parse-dont-validate` |
| Trees that grow | `trees-that-grow` |
| Data types à la carte | `data-types-a-la-carte` |
| Smart constructor | `smart-constructor` |
| Correctness by construction | `correctness-by-construction` |

Beyond the site's list, this collection adds domain-modeling skills — `designing-with-types`, `names-are-not-type-safety`, `boolean-blindness`, `belt-and-suspenders` — and the effect skills `free-monads` and `algebraic-effect-systems`.

## Where to start, by situation

| Situation | Reach for |
|---|---|
| Designing a new service, job, CLI, or UI | `functional-core-imperative-shell`, then `make-illegal-states-unrepresentable`, `parse-dont-validate` |
| Domain model full of strings, flags, and nullables | `designing-with-types` → `make-illegal-states-unrepresentable`, `smart-constructor`, `boolean-blindness` |
| "Type-safe" wrappers that do not seem to help | `names-are-not-type-safety` |
| Untrusted input at a boundary | `parse-dont-validate`, `belt-and-suspenders` |
| Logic tangled with DB/HTTP/clock; hard to test | `pure-functions`, `functional-core-imperative-shell`, `composable-effects` |
| Choosing an effect approach or library | `composable-effects` → `free-monads` / `algebraic-effect-systems` |
| Nested or scattered error handling | `composable-error-handling` |
| Many requirements still unknown | `late-decision-making`, `decoupled-by-default` |
| Combining, merging, aggregating values | `algebraic-modelling`, `composition-and-closure` |
| Designing a library/module API | `denotational-design`, `airtight-abstractions`, `modularization` |
| Audit trails, temporal queries, replay | `event-sourcing` |
| Mapping domain ↔ DTO ↔ storage | `bidirectional-data-transformations` |
| Domain rules as a language | `embedded-dsl`, `data-types-a-la-carte` |
| One AST through several phases | `trees-that-grow` |
| Multi-step interactive workflows | `continuations` |
| Cursors and focus in immutable structures | `zipper` |
| UI state management | `composable-guis` |
| Writing tests | `property-based-testing` |
| Very expensive failures | `formal-verification`, `correctness-by-construction`, `belt-and-suspenders` |
| Applying all this in TypeScript/C++/Java | `functional-programming-languages`, `expressive-static-types` |

## Evaluating a technology or pattern against the principles

1. What does it compose with, and is the composite the same kind of thing? (`composition-and-closure`)
2. What does it couple — shared mutable state, hidden effects, implicit invariants? (`decoupled-by-default`)
3. Can its behaviour be stated as a model with laws? (`denotational-design`, `algebraic-modelling`)
4. Does it keep effects explicit and at the edge? (`pure-functions`, `composable-effects`)
5. Does it keep decisions reversible? (`late-decision-making`)
6. Which illegal states does it let you represent? (`make-illegal-states-unrepresentable`)

Done when: each question has an answer grounded in the relevant skill, and the adoption decision names the principles it trades off.

## Open questions (upstream FAQ, unanswered on the site)

- *Is there a class of domains where functional software architecture works exceptionally well, or fails?* Upstream answer: "No (TODO)".
- *External systems usually don't follow these principles — how do you interface with them?* Upstream: TODO. Pointers from this collection: parse at the boundary into your model (anti-corruption layer; `parse-dont-validate`), keep foreign data opaque, wrap the system in a capability with a fake for tests (`composable-effects`), and keep uncertain integration choices swappable (`late-decision-making`).

## Publications

The FUNARCH workshop papers (2023–2026), each summarized with the skills it informs: [publications.md](publications.md).

## Sources

- [functional-architecture.org](https://functional-architecture.org/) and its source repository [functional-architecture/functional-architecture.github.io](https://github.com/functional-architecture/functional-architecture.github.io) (Active Group GmbH and contributors): values (`lib/values.ml`), principles (`lib/principles.ml`, `principles/*.md`), patterns (`lib/patterns.ml`, `patterns/*.md`), FAQ (`lib/faqs.ml`), the definitions of value/principle/pattern (`README.org`), [events](https://functional-architecture.org/events/), and [publications](https://functional-architecture.org/publications/).
