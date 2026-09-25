---
name: boolean-blindness
description: Boolean and algebraic blindness — replace Bool flags and context-dependent Maybe/Either/tuples with named types, and Boolean tests with functions that return a witness. Use when a function takes or returns a Bool, or a check is followed by a partial extraction (head, !, .value, *opt).
---

# Boolean and algebraic blindness

**Boolean blindness** (Robert Harper, 2011): what `True` *means* depends on context and cannot be read off the value. In `withFile True "file.txt" …`, is `True` read-only, write-only, truncate? Worse, two unrelated booleans look identical, so passing the red/blue flag where the read/write flag belongs compiles fine.

**Algebraic blindness** (David Luposchainsky): the same problem for every cheap, always-available type. `Maybe a` is as blind as `a`, plus one (is `Nothing` an error, "nothing unusual", or something else?). `Either a b` adds that `Left`/`Right` have no intrinsic meaning. A pair `(a, b)` is blind as `a` *times* `b`. GHCi once threaded a `Maybe Bool` meaning *no more input* / *last command succeeded* / *last command failed*.

**Learning by testing** (Conor McBride; *The Haskell Unfolder* episode 7): a Boolean test conveys one bit about its outcome and discards everything it discovered. A test that returns a **witness** — the refined value on success, and possibly evidence on failure — carries the knowledge forward, establishes a boundary, and cannot be run redundantly or forgotten. This is `parse-dont-validate` at the scale of a single function.

## Moves

1. **Boolean parameter → named enumeration.** `withFile ReadMode`, not `withFile True`. `data IOMode = ReadMode | WriteMode | AppendMode | ReadWriteMode` is also better than a clever `Either Bool Bool`. Alternatively, split the function in two.
2. **Several booleans describing one thing → one enumeration.** Three booleans for a traffic light have 8 combinations and 3 legal states (`make-illegal-states-unrepresentable`).
3. **Multi-meaning `Maybe`/`Either`/tuple → a sum type with named, documented cases.** `data CommandResult = NoMoreInput | Success | Failure` costs four lines, is searchable, and gives a type error in the wrong context.
4. **`a -> Bool` test → `a -> Maybe b` witness.** `filter :: (a -> Bool) -> [a] -> [a]` becomes `mapMaybe :: (a -> Maybe b) -> [a] -> [b]`. Implementing it with swapped cases does not type-check: `y` is only in scope in the `Just` branch.
5. **Two-way test → `a -> Either b c`.** `partition` returns a pair of lists that is easy to confuse; `partitionEithers` returns evidence on both sides.
6. **Test-then-extract → one pattern match.** `if null xs then … else f (head xs)` separates the question from the access; `case xs of [] -> …; x : rest -> …` answers the question *and* binds the evidence. Pattern matching *is* learning by testing.
7. **Primitive blindness → wrappers.** An `Int` port vs an `Int` timeout, a `String` host vs route: see `names-are-not-type-safety` for what a wrapper does and does not buy.

Renaming a Boolean (`data KeepOrDrop = Keep | Drop`) improves readability but still lets the branches be swapped and still establishes no boundary. Prefer a witness whenever later code uses what the test found.

## Procedure

1. List every `Bool` parameter and result, and every `Maybe`/`Either`/tuple whose meaning is not "optional value" / "error or result" / "plain pair".
2. For each, write the domain meaning of each value. If you need a comment to say it, it needs a type.
3. Introduce the new type at one use site and follow the compiler errors — the refactoring is type-safe because the new type clashes with nothing.
4. For tests that guard later access, change the test to return the witness and delete the later partial extraction.

Done when: no call site passes a bare literal `True`/`False` or a positional `Maybe`/`Either` whose meaning needs a comment, and no partial accessor follows a Boolean check of the same condition.

**Trade-off:** a new domain type loses the standard API of `Bool`/`Maybe`/lists (combinators, instances). Sometimes the boilerplate to get it back is not worth it; decide per case.

## Example: keep what the test learned

**Haskell**

```haskell
import Data.Maybe (mapMaybe)

newtype Email = Email String deriving (Show)

-- Blind: one bit out, and the caller must trust that "True" means "keep".
isEmail :: String -> Bool
isEmail = elem '@'

-- Witness: the evidence *is* the result.
parseEmail :: String -> Maybe Email
parseEmail s = if '@' `elem` s then Just (Email s) else Nothing

blind :: [String] -> [String]
blind = filter isEmail -- still Strings; the check can be forgotten or repeated

sighted :: [String] -> [Email]
sighted = mapMaybe parseEmail -- the boundary is in the type
```

**TypeScript**

```typescript
class Email {
  private constructor(readonly value: string) {}
  static parse(s: string): Email | undefined {
    return s.includes("@") ? new Email(s) : undefined;
  }
}

const isEmail = (s: string): boolean => s.includes("@");

export const blind = (xs: readonly string[]): string[] => xs.filter(isEmail);

export const sighted = (xs: readonly string[]): Email[] =>
  xs.flatMap((s) => {
    const e = Email.parse(s);
    return e === undefined ? [] : [e];
  });
```

**C++**

```cpp
#include <optional>
#include <string>
#include <vector>

class Email {
public:
  static std::optional<Email> parse(std::string s) {
    if (s.find('@') == std::string::npos) return std::nullopt;
    return Email(std::move(s));
  }
  const std::string& value() const { return v_; }
private:
  explicit Email(std::string v) : v_(std::move(v)) {}
  std::string v_;
};

bool isEmail(const std::string& s) { return s.find('@') != std::string::npos; }

std::vector<Email> sighted(const std::vector<std::string>& xs) {
  std::vector<Email> out;
  for (const auto& s : xs)
    if (auto e = Email::parse(s)) out.push_back(*e);  // test and evidence together
  return out;
}
```

More: flags to enumerations, the GHCi `Maybe Bool`, `partition` with evidence on both sides, parser `token` versus `satisfy`, and pattern matching as learning by testing — in three languages: [examples.md](examples.md).

## Related skills

`parse-dont-validate` · `make-illegal-states-unrepresentable` · `names-are-not-type-safety` · `designing-with-types` · `algebraic-modelling`

## Sources

- David Luposchainsky (quchen), [Algebraic blindness](https://github.com/quchen/articles/blob/master/algebraic-blindness.md).
- Edsko de Vries & Andres Löh, [The Haskell Unfolder, Episode 7: learning by testing](https://discourse.haskell.org/t/the-haskell-unfolder-episode-7-learning-by-testing/6979) (2023), with [code](https://github.com/well-typed/unfolder/tree/main/episode007-learning-by-testing). The episode credits Conor McBride ("learning by testing", 2005–2010), Robert Harper ("Boolean blindness", 2011), and Alexis King ("Parse, don't validate", 2019).
- Wolf McNally, [Make Illegal States Unrepresentable](https://aipatternbook.com/make-illegal-states-unrepresentable) (traffic light and role-string examples).
