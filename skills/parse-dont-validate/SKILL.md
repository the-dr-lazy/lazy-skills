---
name: parse-dont-validate
description: Parse, don't validate — turn less-structured input into precise types once, at the boundary, so downstream code never re-checks. Use when handling untrusted input (JSON, CLI, env, DB rows, forms), when validators return void/bool, or when code carries "impossible" branches or repeated checks.
---

# Parse, don't validate

A **parser** is a function from less-structured input to more-structured output. It is partial by nature, so it can fail. A **validator** performs the same check and then throws the knowledge away. Parse, and let the return type carry what you learned.

<!-- check:skip -->
```haskell
validateNonEmpty :: [a] -> IO ()          -- checks, then forgets
parseNonEmpty    :: [a] -> IO (NonEmpty a) -- checks, and remembers
```

> Alexis King, *Parse, don't validate* (2019): "the difference between validation and parsing lies almost entirely in how information is preserved."

## When to reach for it

- Data crosses a boundary: HTTP, files, env, CLI, database, queues, UI forms, foreign APIs.
- A function returns `()` / `void` / `bool` and exists mainly to raise an error.
- Code contains `error "impossible"`, `!`, `as`, `.Value`, `assert(false)` after a check that "already happened" elsewhere.
- Two places check the same invariant, or a check is easy to forget because nothing consumes its result.

## Core moves

1. **Strengthen the argument, don't weaken the result.** A partial `head :: [a] -> a` can be made total two ways: return `Maybe a` (pushes the problem to every caller) or accept `NonEmpty a` (pushes the proof to where the data is created). Prefer the second; the first is recoverable from it (`fmap head . nonEmpty`), never the reverse. Parsons calls this pushing responsibility *back* rather than *forward*, and it ripples: code tends to demand what the code it calls demands, so a `NonEmpty` parameter breeds `NonEmpty` parameters until the requirement reaches the edge, where the data is parsed (`make-illegal-states-unrepresentable`).
2. **Focus on the datatypes.** Write the function on the representation you *wish* you had. Change its signature to the precise type, follow the compiler errors up the call chain, and stop where the value is created — install the parser there.
3. **Parse at the boundary, before acting.** Mixing checks into processing is *shotgun parsing* (LangSec): the program may act on a valid prefix of input and then discover an invalid suffix. Stratify into a parse phase and an execution phase; failure due to bad input lives only in the first.
4. **Push the burden of proof upward as far as possible, but no further.** If only one branch needs a more precise representation, parse into it as soon as that branch is selected. Sum types let the datatypes follow control flow.

Done when: every value that crosses the boundary has a precise type, no downstream function re-checks an invariant the type already guarantees, and removing the check at the boundary would break compilation.

## Rules of thumb

- **Treat functions returning `m ()` / `void` whose purpose is to throw with deep suspicion.** Return the refined value instead (`checkNoDuplicateKeys :: [(k,v)] -> m (Map k v)`), so the check cannot be omitted.
- **Let datatypes inform code.** Resist adding a `Bool` field because the function you are writing needs it; model the state (see `make-illegal-states-unrepresentable`, `boolean-blindness`).
- **Parse in multiple passes** when useful: using part of the input to decide how to parse the rest is fine; acting on it before it is fully parsed is not.
- **Avoid denormalized data**, especially mutable. Duplicates create a trivially representable illegal state: the copies drifting apart. If you must denormalize, hide it behind an abstraction boundary with a small trusted module.
- **When a property is impractical to encode constructively** (an `Int` in a range), use an abstract type with a smart constructor to make a validator "look like" a parser — and know that this is a weaker, extrinsic guarantee (see `smart-constructor`, `names-are-not-type-safety`).
- **Parse only what you use.** A type describes what *your* component needs, not the whole world. Ignore unknown events explicitly, keep pass-through payloads as an opaque generic value (`Value`, `unknown`, a JSON DOM), and wrap foreign identifiers in opaque types instead of assuming their representation. Static types are not "less open" than dynamic ones; they make the assumptions the dynamic code already makes visible.
- Authorization before parsing is fine (to avoid DoS); it should have a small surface and not mutate state.

## Example: configuration directories

**Haskell**

```haskell
import Control.Exception (throwIO)
import Data.List.NonEmpty (NonEmpty (..), nonEmpty)
import System.Environment (getEnv)

getConfigurationDirectories :: IO (NonEmpty FilePath)
getConfigurationDirectories = do
  raw <- getEnv "CONFIG_DIRS"
  case nonEmpty (filter (not . null) (splitOn ',' raw)) of
    Just dirs -> pure dirs
    Nothing   -> throwIO (userError "CONFIG_DIRS cannot be empty")

main :: IO ()
main = do
  cacheDir :| _ <- getConfigurationDirectories -- total: a NonEmpty always has a head
  putStrLn ("initializing cache in " <> cacheDir)

splitOn :: Char -> String -> [String]
splitOn c s = case break (== c) s of
  (chunk, [])       -> [chunk]
  (chunk, _ : rest) -> chunk : splitOn c rest
```

**TypeScript**

```typescript
type NonEmptyArray<T> = readonly [T, ...T[]];
type Result<T, E = string> = { ok: true; value: T } | { ok: false; error: E };

const isNonEmpty = <T,>(xs: readonly T[]): xs is NonEmptyArray<T> => xs.length > 0;

function getConfigurationDirectories(
  env: Readonly<Record<string, string | undefined>>,
): Result<NonEmptyArray<string>> {
  const dirs = (env["CONFIG_DIRS"] ?? "").split(",").filter((d) => d.length > 0);
  return isNonEmpty(dirs)
    ? { ok: true, value: dirs }
    : { ok: false, error: "CONFIG_DIRS cannot be empty" };
}

const head = <T,>(xs: NonEmptyArray<T>): T => xs[0]; // total

export function main(env: Readonly<Record<string, string | undefined>>): void {
  const dirs = getConfigurationDirectories(env);
  if (!dirs.ok) throw new Error(dirs.error);
  console.log(`initializing cache in ${head(dirs.value)}`);
}
```

**C++**

```cpp
#include <cstdlib>
#include <expected>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

template <typename T>
class NonEmpty {  // constructive: there is no way to build an empty one
public:
  NonEmpty(T head, std::vector<T> tail) : head_(std::move(head)), tail_(std::move(tail)) {}
  static std::expected<NonEmpty, std::string> parse(std::vector<T> xs) {
    if (xs.empty()) return std::unexpected(std::string("list cannot be empty"));
    T first = std::move(xs.front());
    xs.erase(xs.begin());
    return NonEmpty(std::move(first), std::move(xs));
  }
  const T& head() const { return head_; }  // total: no emptiness check needed
  const std::vector<T>& tail() const { return tail_; }
private:
  T head_;
  std::vector<T> tail_;
};

std::vector<std::string> splitNonEmpty(const std::string& s, char sep) {
  std::vector<std::string> out;
  std::stringstream in(s);
  for (std::string item; std::getline(in, item, sep);)
    if (!item.empty()) out.push_back(item);
  return out;
}

int main() {
  const char* raw = std::getenv("CONFIG_DIRS");
  auto dirs = NonEmpty<std::string>::parse(splitNonEmpty(raw ? raw : "", ','));
  if (!dirs) { std::cerr << "CONFIG_DIRS cannot be empty\n"; return 1; }
  std::cout << "initializing cache in " << dirs->head() << '\n';
}
```

More worked examples (duplicate keys → map, open-world event handling, opaque foreign identifiers), each in all three languages: [examples.md](examples.md).

## Beyond Haskell

The technique needs only a way to define a type whose values can come from nowhere but the parser.

- **TypeScript:** discriminated unions, readonly tuples (`[T, ...T[]]`), type predicates, and `#private` class fields. Annotate `JSON.parse` results as `unknown` at once and let the parser take over. Name the raw and the trusted shapes separately (`UnvalidatedUser` with `unknown` fields, `ValidUser` with branded ones), so the boundary is a function. Boundary parsing libraries (Zod, Valibot, io-ts, `effect/Schema`) return typed values from `unknown`, and Zod's `.brand()` is purely type-level.
  - A branded type only helps if the brand is minted in one module. A `unique symbol` brand that the module does not export cannot even be spelled elsewhere, whereas a string-literal `__brand` field can be forged. The cast (`raw as Email`) belongs inside the parser and nowhere else: treat any other `as Brand` as a bug, and consider a lint rule. The brand is one-way, so an `Email` still passes as a `string`: nominal on the way in, structural on the way out. A template-literal type such as `` `${string}@${string}` `` is not enough on its own.
  - Libraries make the discipline cheaper, not optional: you must still parse at every boundary and resist casting past an error. Hand-written early returns get repetitive; Effect, neverthrow, and fp-ts clean that up. Prefer a string discriminant (`"ok" | "err"`) over `success: boolean`, which cannot grow a third case.
- **C++:** private constructors plus a static factory returning `std::optional` / `std::expected` (C++23); `std::variant` for sum types. A class holding the proof (`NonEmpty` above) beats a class holding a flag.

## Related skills

`make-illegal-states-unrepresentable` (choose the target type) · `smart-constructor` (when the property is not structurally expressible) · `names-are-not-type-safety` (why a bare wrapper is not a parser) · `boolean-blindness` (return witnesses, not booleans) · `correctness-by-construction` · `composable-error-handling` (combining many parsers) · `belt-and-suspenders` (when a second check at a boundary is justified)

## Sources

- Alexis King, [Parse, don't validate](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/) (2019).
- Alexis King, [No, dynamic type systems are not inherently more open](https://lexi-lambda.github.io/blog/2020/01/19/no-dynamic-type-systems-are-not-inherently-more-open/) (2020).
- Gabriella Gonzalez, [The golden rule of software quality](https://haskellforall.com/2020/07/the-golden-rule-of-software-quality) (2020) — "prefer to push fixes upstream".
- Edsko de Vries & Andres Löh, [The Haskell Unfolder, Episode 7: learning by testing](https://discourse.haskell.org/t/the-haskell-unfolder-episode-7-learning-by-testing/6979) (2023).
- functional-architecture.org, [Parse, don't validate](https://functional-architecture.org/parse_dont_validate/) (pattern page, upstream TODO).
- Matt Parsons, [Type Safety Back and Forth](https://www.parsonsmatt.org/2017/10/11/type_safety_back_and_forth.html) (2017; read from the [blog's source](https://github.com/parsonsmatt/parsonsmatt.github.io/blob/master/_posts/2017-10-11-type_safety_back_and_forth.markdown)) — pushing responsibility back to the caller, and the ripple effect towards the edge.
- Christian Ekrem, [Parse, Don't Validate — In a Language That Doesn't Want You To](https://cekrem.github.io/posts/parse-dont-validate-typescript/) (2026; read from the [site's source](https://github.com/cekrem/cekrem.github.io/blob/master/content/posts/parse-dont-validate-typescript.md)) — branded types, one-module casts, `unknown` at the boundary, and what Zod does and does not change.
- Further reading cited by the sources: Matt Noonan, *Ghosts of Departed Proofs*; Momot et al., *The Seven Turrets of Babel* (LangSec).
