---
name: composable-error-handling
description: Composable error handling — failures as values (Maybe, Either/Result, std::expected) with flat short-circuiting, error accumulation, and per-layer error types; exceptions only in the shell. Use when writing validation or parsing, flattening nested error handling, or choosing exceptions versus results.
---

# Composable error handling

> *functional-architecture.org:* "Handle errors in a way that they can be composed, combined, and passed through different parts of your program predictably." (Pattern page upstream TODO.)

When failure is a **value** in the return type, the type checker makes every caller account for it, and ordinary combinators compose it. When failure is an exception thrown from anywhere, it is invisible in types, can strike at any point, and composes only through `try` blocks.

## The toolkit

| Need | Haskell | TypeScript | C++ |
|---|---|---|---|
| Absent, no reason needed | `Maybe a` | `T \| undefined` | `std::optional<T>` |
| Failure with a reason | `Either e a` | `Result<T, E>` union, or Effect's typed errors | `std::expected<T, E>` (C++23) |
| Sequence, stop at first failure | `do` / `>>=` | early `return` on `!ok`, or `andThen` | early `return`, or `.and_then` |
| Transform the success value | `fmap` / `<$>` | `map` | `.transform` |
| Translate the error at a boundary | `first` / `withExcept` | `mapError` | `.transform_error` |
| Recover | `either`, `catchError` | `if (!r.ok)` | `.or_else`, `.value_or` |
| Collect *all* independent errors | applicative `Validation` | accumulate into an array | accumulate into a vector |
| Unexpected infrastructure failure | `throwIO` / `fail` in `IO` (never `error`) | `throw` in the shell | exceptions in the shell |

Wlaschin's point about railway-oriented programming is that "just use `Either` with bind" is a tool, not a recipe. The recipe adds `map` for steps that cannot fail, "tee" for steps that return unit, an adapter that turns exceptions into error cases, and parallel combination for validation, so that "there is basically only one way to write the code".

## Rules

1. **Classify the failure first** (Wlaschin). *Domain errors* are expected by the business process, modeled in the types, and need no diagnostics: `Result` as a glorified boolean. *Panics* leave the system in an unknown state (out of memory, divide by zero, a programmer's oversight); abandon the workflow with an exception caught and logged at the highest level (`functional-core-imperative-shell`). *Infrastructure errors* (a network timeout, an authentication failure) are expected by the architecture but not by the business: sometimes model them, sometimes treat them as panics, and "if in doubt, ask a domain expert". Karpov's rule of thumb agrees: the more common a failure is, and the more attention you want to draw to it, the more it belongs in the type; otherwise an exception works like an implicit short-circuiting monad that nobody has to think about until they need to.
2. **Name errors with a sum type per operation or boundary** (`data ParseError = InvalidAge | NegativeAge | InvalidAlive`), not strings — callers can match on them, and adding a case breaks the right code. Do not grow it into one application-wide sum (next section).
3. **Keep the happy path flat.** Bind each step's result in sequence instead of nesting `case`s. In Haskell: a `case` expression can *return a value* inside `do`, and `Left`/`throw` has a polymorphic result type, so the failing branch type-checks as any type (the "trick to avoid deeply-nested error-handling code"). Helper combinators like ``maybe `orDie` "message"`` make it read like prose.
4. **Short-circuit dependent steps; accumulate independent ones.** Parsing an age before checking it is negative is dependent (monadic). Validating the name and the email of a form is independent — report both (applicative validation).
5. **Translate at boundaries.** Each module exposes its own error type; convert with `mapError` when crossing into the next layer so internals do not leak (`airtight-abstractions`).
6. **Let the caller choose the strategy** when you cannot: return `Either`, or take `success`/`failure` continuations (`smart-constructor`), instead of throwing.
7. **Early exit from loops** is just `Either`/`ExceptT` short-circuiting — no continuations required.

Done when: every domain failure appears in a return type, nested `case`/`if` pyramids are flattened into sequential binds, independent validations report all errors, and exceptions are caught in exactly one layer.

## The trouble with one big error type

Parsons' argument, in Haskell terms. Chaining `head`, `lookup`, and `parse` needs one `Either` error type, and the tempting answer is an application-wide `AllErrorsEver`. Its problems:

- **The type is too large.** `foo` claims it can fail with `FileNotFound` although it cannot do I/O.
- **Handling is brittle.** A `case` over the sum needs a `_ -> error "impossible?!"` arm, and a new constructor added elsewhere silently changes what `foo` may return.
- **Partial handling is invisible.** After `bar` handles `AllParseError` and passes the rest on, its type still contains `AllParseError`; the compiler cannot tell.
- **Nothing stops the wrong constructor.** `head [] = Left (AllLookupError …)` type-checks.

His conclusion: error types should have a single constructor, combined per function through something open. The options he walks through: nested `Either` with `mapLeft` (order-dependent, boilerplate); classy prisms (`AsHeadError err => …`), which compose but do not decompose, so you cannot remove one handled case; open variants (PureScript, OCaml); and "plucking" constraints, his `plucky` package, which he calls the best approach in Haskell. His caveats: an `ExceptT e IO` stack costs at run time, asynchronous exceptions are not covered, he has not used it in a large codebase, and it assumes comfort with `lens`. In TypeScript, unions already give order-independent composition and decomposition: Effect tracks failures as a union in its error channel, `Data.TaggedError` adds a `_tag` discriminant, and `Effect.catchTag("HttpError", …)` removes the handled case from the type (`Effect<string, HttpError | ValidationError>` becomes `Effect<string, ValidationError>`). Unrecoverable *defects* (`Effect.die`) are a separate category: `catchAll` handles only recoverable errors, and `catchAllCause` also sees defects.

## When not to use `Result`

Wlaschin's "Against Railway-Oriented Programming" lists where it does harm, and it is the counterweight to rule 1:

- **You need diagnostics** (a stack trace, the location of the failure). `Result` is for *expected* control flow, so do not store an exception in one.
- **You are reinventing try/catch.** Some exceptions always leak, and you handle them at the top of the system anyway.
- **You need to fail fast.** If the workflow would end in an exception, do not thread a `Result` through it.
- **No one will see it.** Inside a private module or a small service, a local exception used for early exit (like Python's `StopIteration`) is often clearer than binds through a tree traversal, provided it never escapes the boundary.
- **No one cares why.** Return an `option` instead of a `FileError` sum that no consumer inspects.
- **I/O.** Model only the bare minimum the domain needs and let the rest become exceptions. If the I/O is separated from the business logic, the core rarely deals with exceptions anyway.
- **Performance** (measure first) and **interop** (do not make callers learn `Result`).

In the shell, catch only synchronous exceptions. In Haskell, `catch` at `SomeException` also catches asynchronous ones such as `ThreadKilled` and timeouts. Karpov's guidance, as implemented by `safe-exceptions` and `unliftio`: cleanup (`bracket`, `finally`) runs for both kinds and re-throws, while recovery catches only synchronous exceptions and re-throws the asynchronous ones. That relies on a convention (asynchronous exceptions are wrapped in `SomeAsyncException`), not on anything the compiler checks. Also, `error "foo" + error "bar"` has no defined order: which exception is thrown is unspecified.

## Example: flat, short-circuiting parsing

**Haskell**

```haskell
{-# LANGUAGE NamedFieldPuns #-}
import Text.Read (readMaybe)

data Person = Person {age :: Int, alive :: Bool} deriving (Show)

data PersonError = InvalidAge | NegativeAge | InvalidAlive deriving (Eq, Show)

orDie :: Maybe a -> e -> Either e a
Just a `orDie` _ = Right a
Nothing `orDie` e = Left e

parsePerson :: String -> String -> Either PersonError Person
parsePerson ageString aliveString = do
  age <- readMaybe ageString `orDie` InvalidAge
  if age < 0 then Left NegativeAge else pure () -- Left short-circuits; pure does not return early
  alive <- readMaybe aliveString `orDie` InvalidAlive
  pure Person {age, alive}

-- parsePerson "24" "True" == Right (Person 24 True);  parsePerson "-5" "True" == Left NegativeAge
```

**TypeScript**

```typescript
type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };
const ok = <T,>(value: T): Result<T, never> => ({ ok: true, value });
const err = <E,>(error: E): Result<never, E> => ({ ok: false, error });

type Person = { readonly age: number; readonly alive: boolean };
type PersonError = "invalidAge" | "negativeAge" | "invalidAlive";

const parseIntStrict = (s: string): number | undefined => (/^-?\d+$/.test(s) ? Number(s) : undefined);
const parseBool = (s: string): boolean | undefined => (s === "True" ? true : s === "False" ? false : undefined);

export function parsePerson(ageString: string, aliveString: string): Result<Person, PersonError> {
  const age = parseIntStrict(ageString);
  if (age === undefined) return err("invalidAge");
  if (age < 0) return err("negativeAge");
  const alive = parseBool(aliveString);
  if (alive === undefined) return err("invalidAlive");
  return ok({ age, alive }); // each step flat, each failure typed
}
```

**C++**

```cpp
#include <charconv>
#include <expected>
#include <optional>
#include <string>

struct Person { int age; bool alive; };
enum class PersonError { InvalidAge, NegativeAge, InvalidAlive };

std::optional<int> parseInt(const std::string& s) {
  int n = 0;
  auto [p, ec] = std::from_chars(s.data(), s.data() + s.size(), n);
  if (ec != std::errc() || p != s.data() + s.size()) return std::nullopt;
  return n;
}

std::optional<bool> parseBool(const std::string& s) {
  if (s == "True") return true;
  if (s == "False") return false;
  return std::nullopt;
}

template <typename T, typename E>
std::expected<T, E> orDie(std::optional<T> x, E e) {
  if (x) return *x;
  return std::unexpected(e);
}

std::expected<Person, PersonError> parsePerson(const std::string& ageString, const std::string& aliveString) {
  auto age = orDie(parseInt(ageString), PersonError::InvalidAge);
  if (!age) return std::unexpected(age.error());
  if (*age < 0) return std::unexpected(PersonError::NegativeAge);
  return orDie(parseBool(aliveString), PersonError::InvalidAlive)
      .transform([&](bool alive) { return Person{*age, alive}; });
}
```

Accumulating errors with applicative validation, translating errors between layers, and early exit from a loop — in three languages: [examples.md](examples.md).

## Related skills

`parse-dont-validate` · `smart-constructor` (choosing the failure channel) · `functional-core-imperative-shell` (where exceptions are caught) · `composable-effects` / `algebraic-effect-systems` (typed error effects, handler order) · `airtight-abstractions` · `continuations`

## Sources

- functional-architecture.org, [Composable Error Handling](https://functional-architecture.org/composable_error_handling/) (pattern page; upstream TODO).
- Gabriella Gonzalez, [The trick to avoid deeply-nested error-handling code](https://haskellforall.com/2021/05/the-trick-to-avoid-deeply-nested-error) (2021), [errors-1.0: Simplified error handling](https://haskellforall.com/2012/07/errors-10-simplified-error-handling) (2012), [Breaking from a loop](https://haskellforall.com/2012/07/breaking-from-loop) (2012), [Prefer to use fail for IO exceptions](https://haskellforall.com/2019/12/prefer-to-use-fail-for-io-exceptions) (2019), [Worst practices should be hard](https://haskellforall.com/2016/04/worst-practices-should-be-hard) (2016, on `error` and unchecked exceptions).
- Scott Wlaschin, [Railway Oriented Programming](https://fsharpforfunandprofit.com/rop/) (the talk page, including *Relationship to the Either monad and Kleisli composition*) and [Against Railway-Oriented Programming](https://fsharpforfunandprofit.com/posts/against-railway-oriented-programming/) (2019) (both read from the [site's source](https://github.com/swlaschin/fsharpforfunandprofit.com)) — the ROP recipe, the eight reasons not to use `Result`, and the domain error / panic / infrastructure error classification.
- Matt Parsons, [The Trouble with Typed Errors](https://www.parsonsmatt.org/2018/11/03/trouble_with_typed_errors.html) (2018, updated 2020; read from the [blog's source](https://github.com/parsonsmatt/parsonsmatt.github.io/blob/master/_posts/2018-11-03-trouble_with_typed_errors.markdown)) — why monolithic error types fail, and composing and decomposing error types.
- Mark Karpov, [Exceptions tutorial](https://markkarpov.com/tutorial/exceptions.html) (2019, updated 2026; read from the [site's source](https://github.com/mrkkrp/markkarpov.com/blob/master/tutorial/exceptions.md): *The motivation for exceptions*, *Asynchronous exceptions*, *How to avoid catching asynchronous exceptions*) — exceptions versus explicit errors, asynchronous exceptions, `safe-exceptions`.
- Effect documentation, [Expected Errors](https://effect.website/docs/error-management/expected-errors/) and [Unexpected Errors](https://effect.website/docs/error-management/unexpected-errors/) (read from the [website's source](https://github.com/Effect-TS/website), v3 pages) — error channel as a union, `Data.TaggedError`, `catchTag`, defects.
- Scott Wlaschin, [Designing with types: Single case union types](https://fsharpforfunandprofit.com/posts/designing-with-types-single-case-dus/) — option, result, and continuation-style failure handling; [Making state explicit](https://fsharpforfunandprofit.com/posts/designing-with-types-representing-states/) — replacing `failwith` with caller-driven handlers.
