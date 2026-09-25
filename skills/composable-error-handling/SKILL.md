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

## Rules

1. **Domain failures are values; infrastructure failures may be exceptions** caught in the shell (`functional-core-imperative-shell`). A "declined payment" is data; "the disk vanished" is exceptional.
2. **Name errors with a sum type per layer** (`data ParseError = InvalidAge | NegativeAge | InvalidAlive`), not strings — callers can match on them, and adding a case breaks the right code.
3. **Keep the happy path flat.** Bind each step's result in sequence instead of nesting `case`s. In Haskell: a `case` expression can *return a value* inside `do`, and `Left`/`throw` has a polymorphic result type, so the failing branch type-checks as any type (the "trick to avoid deeply-nested error-handling code"). Helper combinators like ``maybe `orDie` "message"`` make it read like prose.
4. **Short-circuit dependent steps; accumulate independent ones.** Parsing an age before checking it is negative is dependent (monadic). Validating the name and the email of a form is independent — report both (applicative validation).
5. **Translate at boundaries.** Each module exposes its own error type; convert with `mapError` when crossing into the next layer so internals do not leak (`airtight-abstractions`).
6. **Let the caller choose the strategy** when you cannot: return `Either`, or take `success`/`failure` continuations (`smart-constructor`), instead of throwing.
7. **Early exit from loops** is just `Either`/`ExceptT` short-circuiting — no continuations required.

Done when: every domain failure appears in a return type, nested `case`/`if` pyramids are flattened into sequential binds, independent validations report all errors, and exceptions are caught in exactly one layer.

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
- Scott Wlaschin, [Designing with types: Single case union types](https://fsharpforfunandprofit.com/posts/designing-with-types-single-case-dus/) — option, result, and continuation-style failure handling; [Making state explicit](https://fsharpforfunandprofit.com/posts/designing-with-types-representing-states/) — replacing `failwith` with caller-driven handlers.
