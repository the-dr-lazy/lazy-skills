---
name: composable-error-handling
description: Composable error handling — failures as values, open variants first (one type per error; each function's error type is the union of exactly what it raises; handling an error removes it from the type), with flat short-circuiting, error accumulation, and exceptions only in the shell. Haskell (plucky, Excepts), TypeScript (tagged unions, Effect), C++ (std::expected over std::variant). Use when designing error types, writing validation or parsing, flattening nested error handling, or choosing exceptions versus results.
---

# Composable error handling

> *functional-architecture.org:* "Handle errors in a way that they can be composed, combined, and passed through different parts of your program predictably." (Pattern page upstream TODO.)

When failure is a **value** in the return type, the type checker makes every caller account for it, and ordinary combinators compose it. When failure is an exception thrown from anywhere, it is invisible in types, can strike at any point, and composes only through `try` blocks.

## The toolkit

| Need | Haskell | TypeScript | C++ |
|---|---|---|---|
| Absent, no reason needed | `Maybe a` | `T \| undefined` | `std::optional<T>` |
| Failure with a reason (first approach: `e` is an open union of one-constructor errors) | `Either e a` with `OneOf e '[E1, E2]` (plucky), or `Excepts '[E1, E2] m a` | `Result<T, E1 \| E2>` with tagged errors, or Effect's error channel | `std::expected<T, std::variant<E1, E2>>` (C++23) |
| Handle one error, keep the rest | `catchOne` (plucky), `catchE` (`Excepts`) | `catchTag` (Effect, or a small helper) | a `catchOne<E>` template (below) |
| Sequence, stop at first failure | `do` / `>>=` | early `return` on `!ok`, or `andThen` | early `return`, or `.and_then` |
| Transform the success value | `fmap` / `<$>` | `map` | `.transform` |
| Translate the error at a boundary | `first` / `withExcept` | `mapError` | `.transform_error` |
| Recover | `either`, `catchError` | `if (!r.ok)` | `.or_else`, `.value_or` |
| Collect *all* independent errors | applicative `Validation` | accumulate into an array | accumulate into a vector |
| Unexpected infrastructure failure | `throwIO` / `fail` in `IO` (never `error`) | `throw` in the shell | exceptions in the shell |

Wlaschin's point about railway-oriented programming is that "just use `Either` with bind" is a tool, not a recipe. The recipe adds `map` for steps that cannot fail, "tee" for steps that return unit, an adapter that turns exceptions into error cases, and parallel combination for validation, so that "there is basically only one way to write the code".

## First approach: open variants

Give each error **its own type with a single constructor**, let each function's error type be the **union of exactly the errors it can raise**, and let **handling an error remove it from the type**. When nothing is left, the type says the computation cannot fail.

Why not one big sum type? Parsons' argument, in Haskell terms. Chaining `head`, `lookup`, and `parse` needs one `Either` error type, and the tempting answer is an application-wide `AllErrorsEver`. Its problems:

- **The type is too large.** `foo` claims it can fail with `FileNotFound` although it cannot do I/O.
- **Handling is brittle.** A `case` over the sum needs a `_ -> error "impossible?!"` arm, and a new constructor added elsewhere silently changes what `foo` may return.
- **Partial handling is invisible.** After `bar` handles `AllParseError` and passes the rest on, its type still contains `AllParseError`; the compiler cannot tell.
- **Nothing stops the wrong constructor.** `head [] = Left (AllLookupError …)` type-checks.

His conclusion: "All error types should have a single constructor", combined per function through something open. He wants the combination to be order-independent, free of boilerplate, and easy to compose *and* decompose. Nested `Either` with `mapLeft` composes but is order-dependent and noisy. Classy prisms (`AsHeadError err => …`) compose but do not decompose, so you cannot remove one handled case. Open variants do all four; PureScript and OCaml have them natively.

**Haskell** has no built-in open variants, so use a library or the twenty-line encoding in the example below.

- Parsons' `plucky` *plucks* one constraint at a time. `three :: OneOf e '[A, B, C] => Either e String` may throw any of the three errors, and `catchOne three (\A -> …)` has type `OneOf e '[B, C] => Either e String`. GHC builds the nested `Either` from the handlers you write, so their order is free. He calls it the best approach he knows in Haskell. Its documentation promises no production-readiness and notes that it does not work with `mtl`'s `MonadError` (the functional dependency), so use it with `Either` or `ExceptT`.
- `haskus-utils-variant` has a real open sum, `V '[A, B]`, matched by type with the `V` pattern, and a transformer `Excepts es m a`. `throwE` requires the error to be in `es` (`e :< es`), `catchE` leaves `Remove e es`, and `evalE` accepts only `Excepts '[] m a`, a computation with no errors left.

**TypeScript** has open variants built in: union types. Sequencing widens `E` to `E | F` with no mapping, and handling narrows with `Exclude`. Give each error a literal `_tag`, because unions are structural and two errors with the same shape would otherwise merge. Effect's `Data.TaggedError` adds the tag, and Effect tracks the union in its error channel: `Effect.catchTag("HttpError", …)` turns `Effect<string, HttpError | ValidationError>` into `Effect<string, ValidationError>`, `catchTags` handles several at once, and when all are handled the error type is `never`. Unrecoverable *defects* (`Effect.die`) are a separate category: `catchAll` handles only recoverable errors, and `catchAllCause` also sees defects.

**C++** has only closed variants. `std::variant<HeadError, LookupError>` must be spelled out, and its alternatives are ordered, so the same errors in a different order form a different type (Parsons' order problem again). Use `std::expected<T, std::variant<Es...>>`. Each step returns its single error, which converts into the function's variant; `std::unexpected<FooErrors>(e)` compiles only if `e`'s type is listed. One `catchOne<E>` template removes `E`, and when the last error is removed it returns a plain `T`.

**Costs.** Parsons' caveats: `ExceptT e IO` costs at run time, asynchronous exceptions are not covered, and he had not tried the technique in a large codebase. Type errors come from type-level machinery; plucky's catch-all instance still carries a placeholder message. Keep each union to what the function really raises, and translate at module boundaries (rule 5) so a public API does not expose every internal error.

## Rules

1. **Classify the failure first** (Wlaschin). *Domain errors* are expected by the business process, modeled in the types, and need no diagnostics: `Result` as a glorified boolean. *Panics* leave the system in an unknown state (out of memory, divide by zero, a programmer's oversight); abandon the workflow with an exception caught and logged at the highest level (`functional-core-imperative-shell`). *Infrastructure errors* (a network timeout, an authentication failure) are expected by the architecture but not by the business: sometimes model them, sometimes treat them as panics, and "if in doubt, ask a domain expert". Karpov's rule of thumb agrees: the more common a failure is, and the more attention you want to draw to it, the more it belongs in the type; otherwise an exception works like an implicit short-circuiting monad that nobody has to think about until they need to.
2. **One type per error, one union per function** (the first approach, above): `data HeadError = HeadError`, never strings and never an application-wide sum. A function's error type lists exactly what it can raise, and each handler removes one entry. Where no workable open union exists, fall back to a closed sum per operation or boundary (`data ParseError = InvalidAge | NegativeAge | InvalidAlive`), which callers can still match on.
3. **Keep the happy path flat.** Bind each step's result in sequence instead of nesting `case`s. In Haskell: a `case` expression can *return a value* inside `do`, and `Left`/`throw` has a polymorphic result type, so the failing branch type-checks as any type (the "trick to avoid deeply-nested error-handling code"). Helper combinators like ``maybe `orDie` "message"`` make it read like prose.
4. **Short-circuit dependent steps; accumulate independent ones.** Parsing an age before checking it is negative is dependent (monadic). Validating the name and the email of a form is independent — report both (applicative validation).
5. **Translate at boundaries.** Each module exposes its own error type; convert with `mapError` when crossing into the next layer so internals do not leak (`airtight-abstractions`).
6. **Let the caller choose the strategy** when you cannot: return `Either`, or take `success`/`failure` continuations (`smart-constructor`), instead of throwing.
7. **Early exit from loops** is just `Either`/`ExceptT` short-circuiting — no continuations required.

Done when: every domain failure appears in a return type, each function's error type lists exactly the errors it can raise, nested `case`/`if` pyramids are flattened into sequential binds, independent validations report all errors, and exceptions are caught in exactly one layer.

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

## Example: handle one error, pass on the rest

Parsons' scenario with open variants. `foo` chains `head`, `lookup`, and `parse`; its error type is exactly `HeadError`, `LookupError`, and `ParseError`. `bar` handles `ParseError`, and its type loses it. `total` handles the other two, in either order, and its type says it cannot fail. In all three languages, three mistakes fail to compile: throwing an error the function does not declare, declaring fewer errors than the body raises, and forgetting a handler before claiming the result cannot fail.

**Haskell**

```haskell
{-# LANGUAGE ConstraintKinds #-}
{-# LANGUAGE DataKinds #-}
{-# LANGUAGE FlexibleContexts #-}
{-# LANGUAGE FlexibleInstances #-}
{-# LANGUAGE MultiParamTypeClasses #-}
{-# LANGUAGE TypeFamilies #-}
{-# LANGUAGE TypeOperators #-}
{-# LANGUAGE UndecidableInstances #-}
import Data.Kind (Constraint, Type)
import qualified Data.Map as Map
import Data.Void (Void, absurd)
import Text.Read (readMaybe)

-- The machinery (Parsons' "plucking" technique from plucky, inlined): an open
-- union is a nested Either whose shape GHC picks from the handlers you write.
class Inject big e where inject :: e -> big
instance {-# OVERLAPPABLE #-} Inject e e where inject = id
instance {-# OVERLAPPING #-} Inject (Either e rest) e where inject = Left
instance {-# OVERLAPPABLE #-} Inject rest e => Inject (Either x rest) e where inject = Right . inject

type family OneOf big (es :: [Type]) :: Constraint where
  OneOf big '[] = ()
  OneOf big (e ': es) = (Inject big e, OneOf big es)

throw :: Inject big e => e -> Either big a
throw = Left . inject

-- Handle exactly one error; the rest stay in the type.
catchOne :: Either (Either e rest) a -> (e -> Either rest a) -> Either rest a
catchOne (Right a) _ = Right a
catchOne (Left (Left e)) handle = handle e
catchOne (Left (Right rest)) _ = Left rest

-- One type per error, each with a single constructor.
data HeadError = HeadError deriving (Show)
newtype LookupError = LookupError String deriving (Show)
newtype ParseError = ParseError String deriving (Show)

type Table = Map.Map String String

safeHead :: Inject e HeadError => String -> Either e Char
safeHead (c : _) = Right c
safeHead [] = throw HeadError -- throw (LookupError "") would not compile: not in the constraint

lookupKey :: Inject e LookupError => Table -> String -> Either e String
lookupKey table key = maybe (throw (LookupError key)) Right (Map.lookup key table)

parse :: Inject e ParseError => String -> Either e Integer
parse s = maybe (throw (ParseError s)) Right (readMaybe s)

-- The error set is the union of the steps' errors; no mapLeft, no order to keep.
foo :: OneOf e '[HeadError, LookupError, ParseError] => Table -> String -> Either e Integer
foo table key = do
  c <- safeHead key
  rest <- lookupKey table key
  parse (c : rest)

-- Handling ParseError removes it from the type.
bar :: OneOf e '[HeadError, LookupError] => Table -> String -> Either e Integer
bar table key = foo table key `catchOne` \(ParseError _) -> Right 0

-- Handle the rest, in any order; nothing is left, so the error type is Void.
total :: Table -> String -> Integer
total table key = either absurd id handled
  where
    handled :: Either Void Integer
    handled =
      bar table key
        `catchOne` (\(LookupError _) -> Right (-2))
        `catchOne` (\HeadError -> Right (-1))

-- With t = Map.fromList [("12", "34"), ("7x", "y")]:
-- map (total t) ["12", "", "99", "7x"] == [134, -1, -2, 0]
```

**TypeScript**

```typescript
type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };
const ok = <T,>(value: T): Result<T, never> => ({ ok: true, value });
const fail = <E,>(error: E): Result<never, E> => ({ ok: false, error });

// Sequencing widens the error type to a union: nothing to map, no order to keep.
const andThen = <T, E, U, F>(r: Result<T, E>, next: (t: T) => Result<U, F>): Result<U, E | F> =>
  r.ok ? next(r.value) : r;

// Handle exactly one tag; the rest stay in the type.
type Tagged = { readonly _tag: string };
function catchTag<T, E extends Tagged, K extends E["_tag"]>(
  r: Result<T, E>,
  tag: K,
  handle: (e: Extract<E, { _tag: K }>) => T,
): Result<T, Exclude<E, { _tag: K }>> {
  if (r.ok) return r;
  // The one unchecked step, confined to this helper: TypeScript does not narrow a generic E by its tag.
  return r.error._tag === tag
    ? ok(handle(r.error as Extract<E, { _tag: K }>))
    : fail(r.error as Exclude<E, { _tag: K }>);
}

const absurd = (x: never): never => x;

// One type per error, each with a literal tag (structurally equal errors would otherwise merge).
type HeadError = { readonly _tag: "HeadError" };
type LookupError = { readonly _tag: "LookupError"; readonly key: string };
type ParseError = { readonly _tag: "ParseError"; readonly input: string };

type Table = ReadonlyMap<string, string>;

const head = (s: string): Result<string, HeadError> =>
  s.length > 0 ? ok(s.charAt(0)) : fail({ _tag: "HeadError" }); // a LookupError here would not compile

const lookup = (table: Table, key: string): Result<string, LookupError> => {
  const v = table.get(key);
  return v === undefined ? fail({ _tag: "LookupError", key }) : ok(v);
};

const parse = (input: string): Result<number, ParseError> =>
  /^-?\d+$/.test(input) ? ok(Number(input)) : fail({ _tag: "ParseError", input });

// The error set is the union of the steps' errors.
export const foo = (table: Table, key: string): Result<number, HeadError | LookupError | ParseError> =>
  andThen(head(key), (c) => andThen(lookup(table, key), (rest) => parse(c + rest)));

// Handling ParseError removes it from the type.
export const bar = (table: Table, key: string): Result<number, HeadError | LookupError> =>
  catchTag(foo(table, key), "ParseError", () => 0);

// Handle the rest, in any order; the error type is now never, so this cannot fail.
export const total = (table: Table, key: string): number => {
  const r = catchTag(catchTag(bar(table, key), "LookupError", () => -2), "HeadError", () => -1);
  return r.ok ? r.value : absurd(r.error);
};
```

**C++**

```cpp
#include <charconv>
#include <expected>
#include <map>
#include <string>
#include <type_traits>
#include <utility>
#include <variant>

// The machinery: a type list, removal of one type, and "what is left" as a result type.
template <typename...> struct List {};

template <typename E, typename L, typename Kept = List<>> struct Remove { using type = Kept; };
template <typename E, typename X, typename... Xs, typename... Kept>
struct Remove<E, List<X, Xs...>, List<Kept...>>
    : Remove<E, List<Xs...>, std::conditional_t<std::is_same_v<E, X>, List<Kept...>, List<Kept..., X>>> {};

template <typename T, typename L> struct ResultOf;
template <typename T> struct ResultOf<T, List<>> { using type = T; };  // nothing left: cannot fail
template <typename T, typename... Es> struct ResultOf<T, List<Es...>> {
  using type = std::expected<T, std::variant<Es...>>;
};

// Handle exactly one error type; the rest stay in the type.
template <typename E, typename T, typename... Es, typename Handler>
auto catchOne(std::expected<T, std::variant<Es...>> r, Handler handle) {
  using Out = typename ResultOf<T, typename Remove<E, List<Es...>>::type>::type;
  if (r) return Out(std::move(*r));
  return std::visit(
      [&](auto&& e) -> Out {
        using X = std::decay_t<decltype(e)>;
        if constexpr (std::is_same_v<X, E>) return handle(e);
        else return std::unexpected<typename Out::error_type>(std::forward<decltype(e)>(e));
      },
      std::move(r.error()));
}

// One type per error.
struct HeadError {};
struct LookupError { std::string key; };
struct ParseError { std::string input; };

using Table = std::map<std::string, std::string>;

std::expected<char, HeadError> head(const std::string& s) {
  if (s.empty()) return std::unexpected(HeadError{});
  return s.front();
}

std::expected<std::string, LookupError> lookup(const Table& t, const std::string& key) {
  auto it = t.find(key);
  if (it == t.end()) return std::unexpected(LookupError{key});
  return it->second;
}

std::expected<long, ParseError> parse(const std::string& s) {
  long n = 0;
  auto [p, ec] = std::from_chars(s.data(), s.data() + s.size(), n);
  if (ec != std::errc() || p != s.data() + s.size()) return std::unexpected(ParseError{s});
  return n;
}

// The error set is spelled out once; each step's error converts into it.
using FooErrors = std::variant<HeadError, LookupError, ParseError>;

std::expected<long, FooErrors> foo(const Table& t, const std::string& key) {
  auto c = head(key);
  if (!c) return std::unexpected<FooErrors>(c.error());
  auto rest = lookup(t, key);
  if (!rest) return std::unexpected<FooErrors>(rest.error());
  auto n = parse(*c + *rest);
  if (!n) return std::unexpected<FooErrors>(n.error());
  return *n;
}

// Handling ParseError removes it from the type.
std::expected<long, std::variant<HeadError, LookupError>> bar(const Table& t, const std::string& key) {
  return catchOne<ParseError>(foo(t, key), [](const ParseError&) { return 0L; });
}

// Handle the rest, in any order; the result is a plain long because nothing can fail.
long total(const Table& t, const std::string& key) {
  return catchOne<HeadError>(catchOne<LookupError>(bar(t, key), [](const LookupError&) { return -2L; }),
                             [](const HeadError&) { return -1L; });
}
```

Libraries save writing the machinery: `plucky` or `haskus-utils-variant`'s `Excepts` in Haskell, and Effect's tagged errors in TypeScript. The C++ helper is this collection's own; it needs only `std::expected` and `std::variant`.

## Example: flat, short-circuiting parsing

The flat happy path of rule 3, here with the closed per-boundary fallback of rule 2 (`PersonError`).

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
- Matt Parsons, [The Trouble with Typed Errors](https://www.parsonsmatt.org/2018/11/03/trouble_with_typed_errors.html) (2018, updated 2020; read from the [blog's source](https://github.com/parsonsmatt/parsonsmatt.github.io/blob/master/_posts/2018-11-03-trouble_with_typed_errors.markdown)) — why monolithic error types fail, single-constructor errors, the four requirements (order independence, no boilerplate, composition, decomposition), and open variants.
- Matt Parsons, [Plucking Constraints](https://www.parsonsmatt.org/2020/01/03/plucking_constraints.html) (2020; read from the [blog's source](https://github.com/parsonsmatt/parsonsmatt.github.io/blob/master/_posts/2020-01-03-plucking_constraints.markdown)) and [`plucky`](https://hackage.haskell.org/package/plucky) (0.0.0.1; read the source and documentation of `Data.Either.Plucky`) — plucking one error constraint at a time, `OneOf`, `throw`, `catchOne`, and the library's own caveats.
- Sylvain Henry, [`haskus-utils-variant`](https://hackage.haskell.org/package/haskus-utils-variant) (3.5, July 2024; read the source of `Haskus.Utils.Variant` and `Haskus.Utils.Variant.Excepts`) — the open sum `V`, the `V` pattern, `Excepts`, `throwE`, `catchE`, `evalE`.
- Mark Karpov, [Exceptions tutorial](https://markkarpov.com/tutorial/exceptions.html) (2019, updated 2026; read from the [site's source](https://github.com/mrkkrp/markkarpov.com/blob/master/tutorial/exceptions.md): *The motivation for exceptions*, *Asynchronous exceptions*, *How to avoid catching asynchronous exceptions*) — exceptions versus explicit errors, asynchronous exceptions, `safe-exceptions`.
- Effect documentation, [Expected Errors](https://effect.website/docs/error-management/expected-errors/) and [Unexpected Errors](https://effect.website/docs/error-management/unexpected-errors/) (read from the [website's source](https://github.com/Effect-TS/website), v3 pages) — error channel as a union, `Data.TaggedError` (a tag that keeps TypeScript from unifying error types), `catchTag`, `catchTags`, defects.
- The TypeScript `catchTag` helper and the C++ `catchOne` template in the open-variant example are this collection's own encodings.
- Scott Wlaschin, [Designing with types: Single case union types](https://fsharpforfunandprofit.com/posts/designing-with-types-single-case-dus/) — option, result, and continuation-style failure handling; [Making state explicit](https://fsharpforfunandprofit.com/posts/designing-with-types-representing-states/) — replacing `failwith` with caller-driven handlers.
