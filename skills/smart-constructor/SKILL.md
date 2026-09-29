---
name: smart-constructor
description: Smart constructors — a factory that normalizes, parses, or validates and is the only way to build an opaque type. Use when wrapping constrained primitives (emails, zip codes, bounded strings, quantities), hiding a raw constructor, or choosing how construction failure is reported.
---

# Smart constructor

A smart constructor semantically behaves like an ordinary constructor, but performs useful computation on the way in — **preprocessing, normalization, parsing, or validation** — and it is the *only* way to obtain a value of its type. It is the standard tool for invariants that are impractical to express structurally ("a string of at most 50 characters", "an integer between 1 and 99"). It makes a validator look like a parser.

The guarantee is **extrinsic**: it holds because the constructor is hidden and its code is correct, not because the type rules bad values out. When a constructive encoding is practical, prefer it (`correctness-by-construction`); see `names-are-not-type-safety` for the difference.

## Procedure

1. **Hide the raw constructor.** Haskell: omit it from the export list. F#/OCaml: a signature file or `private` union. TypeScript: a class with a `private constructor` and `#private` state (a brand minted in one module is weaker — `as` casts forge it). C++: a private constructor and a static factory.
2. **Canonicalize, then validate.** Trim, collapse whitespace, fix case (`"ca"` → `"CA"`) before checking, so equal things compare equal and validation sees one form.
3. **Return the refined type, with a failure channel that fits the caller:**
   - `Maybe` / `optional` / `undefined` when there is one obvious reason to fail;
   - `Either` / `Result` / `std::expected` with an error value when the reason matters;
   - accumulate *all* errors (applicative validation) for forms — see `composable-error-handling`;
   - or take `success` and `failure` continuations and let the caller decide; every other style can be recovered from this one.
   Throwing is the least composable choice.
4. **Expose read-only access** (`value`, or `apply f` to run a function on the contents). No setters: a value is immutable after construction, so validation at construction holds forever.
5. **Construct at the boundary, unwrap at the boundary.** Wrap in the UI, API, or persistence layer (the edges of a hexagonal architecture); pass the opaque value through the domain whole; unwrap only when writing to a database, a view model, or the wire. Callers use the constructor instead of re-implementing its check.
6. **Close the holes.** No derived `Read`/`Generic`/JSON decoders that bypass the factory, no public fields, no default constructor, no unchecked `as`. In Haskell, expose an `unPassword` function, not a record field: a field allows record-update syntax to change the inner value. Hide the constructor too, since an exported one lets `coerce` forge values.
7. **Name the test-only escape hatch for what it is** (`unsafePassword`), so a use in application code stands out in review or to tooling. Do not just export the raw constructor under a scary name.
8. **Test the trusted module.** Its API is the whole attack surface. Properties: every produced value satisfies the predicate; `create (value x) == Just x`; canonicalization is idempotent (`property-based-testing`).

Done when: the only path to a value of the type goes through the factory, every consumer relies on the invariant without re-checking it, and the factory has property tests.

## Design notes

- **Constraints belong in the model.** Maximum lengths look like physical details, but the same `PersonalName` flows through the web app, the database, the message queue, and the CRM. If the model does not state that a first name is at most 50 characters, each system decides separately — silently truncating in the database layer is the typical symptom. Decide once, at creation.
- **Generalize the boilerplate** with one helper `create canonicalize isValid wrap` and define each type in one line ([examples.md](examples.md)).
- **Decisions move up front.** Concatenating a `String50` and a `String100` forces the question "what if the result is too long?" at design time. That is annoying and good.
- **Wrappers versus units of measure:** units (F# `<ms>`, `std::chrono`) are better for arithmetic-heavy code; wrappers add encapsulation and constraints. Units cannot enforce a range.
- **Costs and variants.** Extra code; a choice among `Maybe`, `Either`, and an accumulating `Validation`, and among pattern synonyms and plain functions (the Haskell community has no single "true way"); and in Haskell you cannot define instances for the type outside its module. Statically known values can be checked at compile time (Template Haskell), so a literal gets errors at build time and needs no unsafe function.
- **Smart constructors compose.** A list of validated parts is built with `traverse mkTag`, and a type made of validated parts (`NonEmpty Tag`) needs no second check: `mkTagsList` is `TagsList <$> liftA2 (:|) (mkTag t) (traverse mkTag ts)`.
- **They are a boundary technique.** Checking at the edge works for values that arrive from outside. Values computed *inside* the system from checked ones (a `length`, a concatenation) need another fallible construction unless the type tracks what is already known. Karpov's design records established properties in a phantom list and derives implied ones without failure, for instance a text known to be `NotEmpty` yields its `NonEmpty` projection purely. He admits he does not know how it feels at scale. The lighter alternatives he names are the `refined` library and Liquid Haskell. Constraints on arguments also make consumers total and pure: `myDivide :: Int -> GreaterThanFive -> Int` cannot divide by zero.

## Example: a bounded, canonical email address

**Haskell**

```haskell
module EmailAddress (EmailAddress, EmailError (..), mkEmailAddress, emailText) where

import Data.Char (isSpace, toLower)

newtype EmailAddress = EmailAddress String -- constructor not exported
  deriving (Eq, Ord, Show)

data EmailError = Empty | TooLong | MissingAt
  deriving (Eq, Show)

mkEmailAddress :: String -> Either EmailError EmailAddress
mkEmailAddress raw
  | null s = Left Empty
  | length s > 100 = Left TooLong
  | '@' `notElem` s = Left MissingAt
  | otherwise = Right (EmailAddress s)
  where
    s = map toLower (trim raw) -- canonicalize first
    trim = dropWhileEnd' isSpace . dropWhile isSpace
    dropWhileEnd' p = reverse . dropWhile p . reverse

emailText :: EmailAddress -> String
emailText (EmailAddress s) = s
```

**TypeScript**

```typescript
export type EmailError = "empty" | "tooLong" | "missingAt";
type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };

export class EmailAddress {
  readonly #value: string;
  private constructor(value: string) {
    this.#value = value;
  }
  static create(raw: string): Result<EmailAddress, EmailError> {
    const s = raw.trim().toLowerCase(); // canonicalize first
    if (s.length === 0) return { ok: false, error: "empty" };
    if (s.length > 100) return { ok: false, error: "tooLong" };
    if (!s.includes("@")) return { ok: false, error: "missingAt" };
    return { ok: true, value: new EmailAddress(s) };
  }
  get value(): string {
    return this.#value;
  }
  equals(other: EmailAddress): boolean {
    return this.#value === other.#value;
  }
}
```

**C++**

```cpp
#include <algorithm>
#include <cctype>
#include <expected>
#include <string>

enum class EmailError { Empty, TooLong, MissingAt };

class EmailAddress {
public:
  static std::expected<EmailAddress, EmailError> create(std::string raw) {
    auto notSpace = [](unsigned char c) { return !std::isspace(c); };
    raw.erase(raw.begin(), std::find_if(raw.begin(), raw.end(), notSpace));
    raw.erase(std::find_if(raw.rbegin(), raw.rend(), notSpace).base(), raw.end());
    std::transform(raw.begin(), raw.end(), raw.begin(),
                   [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    if (raw.empty()) return std::unexpected(EmailError::Empty);
    if (raw.size() > 100) return std::unexpected(EmailError::TooLong);
    if (raw.find('@') == std::string::npos) return std::unexpected(EmailError::MissingAt);
    return EmailAddress(std::move(raw));
  }
  const std::string& value() const { return value_; }
  bool operator==(const EmailAddress&) const = default;

private:
  explicit EmailAddress(std::string v) : value_(std::move(v)) {}
  std::string value_;
};
```

More: a generic wrapped-string helper, continuation-style construction, bounded quantities and safe dates, boundary usage, and property tests for a smart constructor — all in three languages: [examples.md](examples.md).

## Related skills

`names-are-not-type-safety` (what the guarantee is worth) · `parse-dont-validate` · `correctness-by-construction` · `make-illegal-states-unrepresentable` · `designing-with-types` · `composable-error-handling` · `property-based-testing` · `airtight-abstractions`

## Sources

- functional-architecture.org, [Smart constructor](https://functional-architecture.org/smart_constructor/) (pattern page; upstream TODO) and the Clojure smart constructors in [Make Illegal States Unrepresentable](https://functional-architecture.org/make_illegal_states_unrepresentable/).
- Scott Wlaschin, [Designing with types: Single case union types](https://fsharpforfunandprofit.com/posts/designing-with-types-single-case-dus/), [Constrained strings](https://fsharpforfunandprofit.com/posts/designing-with-types-more-semantic-types/), [Non-string types](https://fsharpforfunandprofit.com/posts/designing-with-types-non-strings/) (2013).
- Alexis King, [Parse, don't validate](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/) ("use abstract datatypes to make validators look like parsers") and **[Names are not type safety](https://lexi-lambda.github.io/blog/2020/11/01/names-are-not-type-safety/)**.
- Wolf McNally, [Make Illegal States Unrepresentable](https://aipatternbook.com/make-illegal-states-unrepresentable) ("enforce invariants through constructors").
- Kowainik, [Haskell mini-patterns handbook](https://kowainik.github.io/posts/haskell-mini-patterns) (2020; read from the [site's source](https://github.com/kowainik/kowainik.github.io/blob/develop/posts/2020-08-17-haskell-mini-patterns.md)) — the *Smart constructor* pattern: when to use it, costs, no record selector, `coerce`, the `unsafe` test helper, variants, compile-time checks, `traverse` composition.
- Mark Karpov, [Smart constructors that cannot fail](https://markkarpov.com/post/smart-constructors-that-cannot-fail.html) (2018; read from the [site's source](https://github.com/mrkkrp/markkarpov.com/blob/master/post/smart-constructors-that-cannot-fail.md)) — why refinement types are underused, checks at the boundary versus values produced inside, tracking established properties in the type.
