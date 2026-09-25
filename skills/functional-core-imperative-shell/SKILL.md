---
name: functional-core-imperative-shell
description: Functional core, imperative shell — pure domain logic in a large core, with I/O and error handling in a thin shell that calls it. Use when designing a service, CLI, UI, or job, or when business logic is tangled with database, HTTP, or clock calls and hard to test.
---

# Functional core, imperative shell

Structure software into two parts:

- **The functional core:** pure functions that depend only on their inputs to produce their outputs. This is *what* the software does — the domain logic.
- **The imperative shell:** impure code that interacts with the outside world. It takes input from the world (user input, requests, files, clocks), feeds pure values into the core, and applies the core's results as effects (writes, responses, messages). It handles errors, non-determinism, and exceptions in one place.

**The shell calls the core; the core never calls the shell.** Separating the two is *always possible*: every function can be refactored into the part that supplies input impurely, the part that turns input into output purely, and the part that consumes output impurely.

## When to reach for it

Always. It improves separation of concerns, testability, and maintainability, and it keeps infrastructure details swappable without touching the domain logic. The only exception: profiling proves that the separation itself costs too much in a hot path (memoization or an in-place algorithm must be inlined) — almost never the case.

## Procedure

1. **Find the decisions.** In an entangled function, mark every line as *reading the world*, *deciding*, or *acting on the world*.
2. **Extract the deciding part** into a pure function whose parameters are everything it read and whose return value describes everything it would do — a value, a new state, or a list of actions/events.
3. **Make the shell a flat orchestration:** read, call the core, act. It contains no business `if`s; branching on the core's result to pick an effect is fine.
4. **Test the core directly** with example and property tests; test the shell with a few integration tests or fakes.
5. **Repeat outward** as the shell grows: when the shell starts to contain domain logic of its own ("store it only if…"), represent those interactions as values too (`composable-effects`).

Done when: the core imports nothing that touches the world, the shell contains no domain decisions, and the core's tests need no mocks.

## Example: read, increment, print (from functional-architecture.org)

The original couples input, logic, and output: `print(read() + 1)`.

**Haskell**

```haskell
-- Core: pure, single responsibility.
increment :: Integer -> Integer
increment n = n + 1

-- Shell: supplies input, consumes output.
input :: IO Integer
input = readLn

output :: Integer -> IO ()
output = print

main :: IO ()
main = do
  n <- input
  output (increment n)
```

**TypeScript**

```typescript
import { createInterface } from "node:readline/promises";

// Core
export const increment = (n: number): number => n + 1;

// Shell
async function input(): Promise<number> {
  const rl = createInterface({ input: process.stdin });
  const line = await rl.question("");
  rl.close();
  return Number(line);
}

const output = (n: number): void => console.log(n);

export async function main(): Promise<void> {
  output(increment(await input()));
}
```

**C++**

```cpp
#include <iostream>

// Core
constexpr long long increment(long long n) { return n + 1; }
static_assert(increment(41) == 42);  // the core is testable at compile time

// Shell
long long input() {
  long long n = 0;
  std::cin >> n;
  return n;
}

void output(long long n) { std::cout << n << '\n'; }

int main() { output(increment(input())); }
```

What this small example shows scales: see [examples.md](examples.md) for order processing where the core returns the *actions* to perform, and for an interactive program whose entire logic is a pure state machine driven by a shell loop (the `mvc` architecture), each in three languages.

## Shortcomings, and what comes next

The pattern separates pure from impure, but not necessarily **domain logic from infrastructure**: using infrastructure is often part of the domain ("store the order, then notify the warehouse"). In large programs the shell collects that logic and becomes complex and hard to maintain. The natural evolution is to make even more of it pure by **representing effectful interactions as values** and separating their evaluation and execution from their pure representation — `composable-effects`, `free-monads`, `algebraic-effect-systems`. Error handling and non-determinism can be coordinated in the shell and made compositional with `composable-error-handling`.

## Related skills

`pure-functions` · `composable-effects` · `composable-error-handling` · `composable-guis` (functional shells around imperative toolkits) · `event-sourcing` (the core as a fold over events) · `decoupled-by-default`

## Sources

- functional-architecture.org, [Functional Core, Imperative Shell](https://functional-architecture.org/functional_core_imperative_shell/) (published pattern page).
- Wolf McNally, [Side Effect](https://aipatternbook.com/side-effect/) — the pure calculator returning `(total, actions)` plus a thin orchestrator; attribution of the name to Gary Bernhardt's *Destroy All Software* screencast (2012) and the relation to Hexagonal Architecture (Cockburn) and Clean Architecture.
- Gabriella Gonzalez, [Model-view-controller, Haskell-style](https://haskellforall.com/2014/04/model-view-controller-haskell-style) (2014) — a pure `Model` with all effects in combined `View`/`Controller` values.
- Ben Knoble, Bogdan Popa, [Functional Shell and Reusable Components for Easy GUIs](https://defn.io/papers/fungui-funarch23.pdf) (FUNARCH 2023).
- Alexis King, [Unit testing effectful Haskell with monad-mock](https://lexi-lambda.github.io/blog/2017/06/29/unit-testing-effectful-haskell-with-monad-mock/) ("a 'pure core, impure shell' approach to system design").
