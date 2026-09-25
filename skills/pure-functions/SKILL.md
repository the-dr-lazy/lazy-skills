---
name: pure-functions
description: Pure functions — results depend only on arguments and the only output is the return value. Use when writing or reviewing domain logic, when spotting hidden side effects (a "calculate" that writes, a helper that mutates, a clock deep inside), or when deciding what belongs in the functional core.
---

# Pure functions

> *functional-architecture.org:* "A pure function transforms immutable values without performing any side effects." (Principle page upstream TODO.)

A **side effect** is anything a function does, while running, that is observable from outside other than its return value: writing a row, sending an email, mutating a global or an argument the caller still holds, printing, reading the clock, generating a random number, throwing an exception that escapes. A **pure** function has none, and given the same inputs always returns the same output.

**Referential transparency** follows: an expression can be replaced by its value anywhere without changing the program's meaning. That enables **equational reasoning** — substitute equals for equals, in both directions, to understand, refactor, and prove things about code — and makes tests a single equality assertion.

## Why it matters

- **Local reasoning.** A pure function's signature tells the whole story. `total_with_tax` can be read without knowing about the database, logger, cache, or email service. When it quietly writes a row, fires an event, and warms a cache, "the signature lies about the work."
- **Testing.** Pure code needs no mocks, fixtures, clocks, or teardown; property-based testing becomes natural (`property-based-testing`).
- **Change.** Pure code can be moved, renamed, cached, parallelized, and recomposed without disturbing external systems.
- **Laws survive.** Haskell separates *evaluation order* from *effect order*: evaluating an `IO` action does not run it, so algebraic equations keep holding even for effectful code (`composable-effects`). Evaluation-sensitive primitives such as `error` break this — prefer `throwIO`/`fail` in `IO` over `error`.

## Recognize impurity

- **Verbs of action in the name** (`save`, `send`, `write`, `publish`, `notify`, `log`, `commit`). Conversely a `compute`/`calculate`/`parse`/`format`/`to…` name with an effect inside is almost certainly a bug.
- **Returns `void`/`unit`.** It exists only for its effects: shell, not core.
- **Mutates its arguments.** Edits memory the caller did not ask to have edited.
- **Imports the world:** database clients, HTTP, file system, logger, clock, random.
- **Needs scaffolding to test.** If the test needs a fixture, a mock, an injected clock, a temp directory, the function is effectful whatever its signature says.

Three recurring failure modes: the **hidden effect** (a pure-looking function that mutates or emits), the **effect cascade** (effectful functions calling effectful functions, each part computation, part action), and the **effect at the wrong layer** (pricing, validation, scoring reaching out to infrastructure).

## Procedure: purify a function

1. List every input it reads besides its parameters (clock, config, globals, database) and every output besides its return value (writes, events, logs, mutations).
2. Turn each hidden input into a parameter (`now :: UTCTime`, `score :: Score`).
3. Turn each hidden output into part of the return value — a new value instead of a mutation, a description of the action instead of performing it (`[Action]`, an event, a command).
4. Move the fetching and performing into a caller at the edge (`functional-core-imperative-shell`).
5. Replace the integration test with direct equality and property tests of the pure function.

Done when: the function's result depends only on its parameters, it neither mutates nor performs I/O, and its tests are plain input/output assertions.

## Example: eligibility with the network call moved out

**Haskell**

```haskell
newtype CreditScore = CreditScore Int

data Applicant = Applicant {age :: Int, income :: Int}

data Decision = Approved | Declined String deriving (Eq, Show)

-- Pure: everything it needs is a parameter.
eligibility :: CreditScore -> Applicant -> Decision
eligibility (CreditScore s) a
  | age a < 18 = Declined "applicant must be an adult"
  | s < 600 = Declined "credit score below 600"
  | income a < 20000 = Declined "income below threshold"
  | otherwise = Approved

-- The shell fetches the score and calls the pure function.
decide :: (String -> IO CreditScore) -> String -> Applicant -> IO Decision
decide fetchScore applicantId applicant = do
  score <- fetchScore applicantId
  pure (eligibility score applicant)
```

**TypeScript**

```typescript
type Applicant = { readonly age: number; readonly income: number };
type Decision = { kind: "approved" } | { kind: "declined"; reason: string };

// Pure: everything it needs is a parameter.
export function eligibility(creditScore: number, a: Applicant): Decision {
  if (a.age < 18) return { kind: "declined", reason: "applicant must be an adult" };
  if (creditScore < 600) return { kind: "declined", reason: "credit score below 600" };
  if (a.income < 20000) return { kind: "declined", reason: "income below threshold" };
  return { kind: "approved" };
}

// The shell fetches the score and calls the pure function.
export async function decide(
  fetchScore: (applicantId: string) => Promise<number>,
  applicantId: string,
  applicant: Applicant,
): Promise<Decision> {
  return eligibility(await fetchScore(applicantId), applicant);
}
```

**C++**

```cpp
#include <functional>
#include <string>
#include <variant>

struct Applicant { int age; int income; };
struct Approved {};
struct Declined { std::string reason; };
using Decision = std::variant<Approved, Declined>;

// Pure: everything it needs is a parameter.
Decision eligibility(int creditScore, const Applicant& a) {
  if (a.age < 18) return Declined{"applicant must be an adult"};
  if (creditScore < 600) return Declined{"credit score below 600"};
  if (a.income < 20000) return Declined{"income below threshold"};
  return Approved{};
}

// The shell fetches the score and calls the pure function.
Decision decide(const std::function<int(const std::string&)>& fetchScore,
                const std::string& applicantId, const Applicant& applicant) {
  return eligibility(fetchScore(applicantId), applicant);
}
```

## In mainstream languages

Nothing enforces purity in TypeScript or C++, so make it a convention the code *shows*: pure functions take `readonly`/`const` inputs and return new values; they import nothing that touches the world; effectful functions are named with verbs and live in the shell. In C++, `constexpr` functions are checked pure-ish by the compiler; `[[nodiscard]]` on pure functions catches ignored results. When briefing an AI agent, "write a pure function that takes X and returns Y" is a far sharper target than "implement the feature".

## Related skills

`functional-core-imperative-shell` · `immutability` · `composable-effects` · `everything-as-a-value` · `property-based-testing` · `algebraic-modelling` (equational reasoning at scale)

## Sources

- functional-architecture.org, [Pure Functions](https://functional-architecture.org/pure_functions/) (principle page; upstream TODO).
- Wolf McNally, [Side Effect](https://aipatternbook.com/side-effect/), *Encyclopedia of Agentic Coding Patterns*.
- Gabriella Gonzalez, [Purify code using free monads](https://haskellforall.com/2012/07/purify-code-using-free-monads) (2012), [Equational reasoning](https://haskellforall.com/2013/12/equational-reasoning) (2013), [Algebraic side effects](https://haskellforall.com/2015/03/algebraic-side-effects) (2015), [Prefer to use fail for IO exceptions](https://haskellforall.com/2019/12/prefer-to-use-fail-for-io-exceptions) (2019), [Statements vs Expressions](https://haskellforall.com/2013/07/statements-vs-expressions) (2013), [Sometimes less is more in language design](https://haskellforall.com/2013/08/sometimes-less-is-more-in-language) (2013).
