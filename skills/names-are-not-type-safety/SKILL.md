---
name: names-are-not-type-safety
description: Names are not type safety — distinguish intrinsic safety (constructive types) from extrinsic safety (a newtype, wrapper, or brand plus smart constructor behind a trust boundary). Use when introducing or reviewing a newtype, wrapper, branded or opaque type, or "type-safe" IDs and strings.
---

# Names are not type safety

A `newtype` (single-case union, branded type, wrapper class) declares a type that is nominally distinct from, but representationally the same as, the type it wraps. **On its own, it is just a name.** A name prevents some mix-ups; it does not make illegal values unrepresentable.

> Alexis King, *Names are not type safety* (2020): newtypes "can provide *some* value, and when coupled with a smart constructor and an encapsulation boundary, it can even provide some safety. But it is a meaningfully distinct *kind* of type safety … one that is far weaker."

## Intrinsic versus extrinsic safety

| | Constructive type | Wrapper + smart constructor |
|---|---|---|
| Example | `data OneToFive = One \| Two \| Three \| Four \| Five` | `newtype OneToFive = OneToFive Int` + `toOneToFive :: Int -> Maybe OneToFive` |
| Where the invariant lives | In the type declaration | In the smart constructor's code |
| What consumers see | Exactly the legal cases; exhaustiveness checking works | An `Int`; they need an `error "impossible"` branch |
| What you must trust | The typechecker | The defining module and every future edit to it |
| Adding a case | Every consumer fails to compile | Every consumer still compiles, then fails at runtime |

The smart constructor *validates*; the Boolean result is used for control flow and then thrown away. Downstream code cannot benefit from the restricted domain — it is functionally accepting `Int`s. Prefer the constructive form whenever it is practical (`correctness-by-construction`, `make-illegal-states-unrepresentable`).

## Newtypes as tokens: the legitimate safety story

An opaque wrapper (constructor not exported) turns its **home module** into a trust boundary. The module issues tokens through its constructors; tokens are worthless elsewhere and can only be redeemed through the module's accessors. Invariant violations can only originate inside that module, so its API is small enough to test thoroughly (property-based testing, fuzzing).

This safety is conditional. Holes appear easily:

- **Derived instances that construct values:** `deriving (Generic)`, `deriving (Read)`, JSON decoders that build the value directly, `Arbitrary` instances in production code.
- **TypeScript:** any `as Brand` cast anywhere forges a brand; structural typing lets a same-shaped object literal satisfy an interface. Prefer a class with `#private` fields if forgery matters.
- **C++:** public aggregate initialization, a public default constructor, a non-`explicit` converting constructor, `reinterpret_cast`/`memcpy`, and `enum class` values forged with `static_cast`.

Keep the trust boundary sound:

1. State every invariant to maintainers of the trusted module (comments are mandatory for non-trivial invariants).
2. Audit every change to the module for weakened invariants.
3. Refuse "unsafe" trapdoors that bypass the constructor.
4. Refactor periodically so the trusted surface stays small — responsibilities accumulate there over time, especially in churning application code. Libraries, which change less and get more scrutiny, are the natural home for this technique.

## Decision procedure

1. **Can the invariant be expressed by construction at acceptable cost?** (a closed set → sum type; non-empty → head + tail; unique keys → map.) Do that.
2. **Otherwise, is it a genuine invariant worth a trust boundary?** (a range, a checksum, a normalized string) → opaque type, smart constructor returning the refined type, no escape hatches, property tests for the module's API. Call it what it is: extrinsic safety.
3. **Is the goal only to keep same-representation values apart?** (`CustomerId` vs `OrderId`, `Distance` vs `Duration`, seconds vs milliseconds, UTC vs local time) → a transparent wrapper is fine and useful: it prevents *logical mistakes*, it does not *prevent misuse*. Make it ergonomic (derive `IsString`/`Num`/`Show` via the underlying type in Haskell) so nobody is tempted to strip it.
4. **Is it wrapped and unwrapped at will, with no mix-up risk and no invariant?** → delete it. It is a security blanket: "forcing programmers to jump through a few hoops is not type safety." If the label adds clarity, a type alias or a field name suffices.

Done when: every wrapper type in the change is either constructive, an opaque token with a named trust boundary and tests, or a deliberately transparent label — and nobody describes the third kind as validation.

Other legitimate newtype uses that are *not* about safety: selecting an alternative type-class instance (`Sum`, `Product`), rearranging type parameters (`Flip`), and discouraging accidental exposure (a secret key without a `Show` instance — which discourages, but does not prevent, misuse).

## Example: an integer from 1 to 5

**Haskell**

```haskell
-- Intrinsic: the declaration is the invariant.
data OneToFive = One | Two | Three | Four | Five

ordinal :: OneToFive -> String
ordinal One = "first"
ordinal Two = "second"
ordinal Three = "third"
ordinal Four = "fourth"
ordinal Five = "fifth" -- exhaustive; a sixth constructor would be flagged here

-- Extrinsic: the invariant lives in toRanged; consumers still see an Int.
newtype Ranged = Ranged Int

toRanged :: Int -> Maybe Ranged
toRanged n
  | n >= 1 && n <= 5 = Just (Ranged n)
  | otherwise = Nothing

ordinalRanged :: Ranged -> String
ordinalRanged (Ranged n) = case n of
  1 -> "first"
  2 -> "second"
  3 -> "third"
  4 -> "fourth"
  5 -> "fifth"
  _ -> error "impossible: bad Ranged value" -- a hole punched through the type system
```

**TypeScript**

```typescript
// Intrinsic: a closed union of literals.
type OneToFive = 1 | 2 | 3 | 4 | 5;

export function ordinal(n: OneToFive): string {
  switch (n) {
    case 1: return "first";
    case 2: return "second";
    case 3: return "third";
    case 4: return "fourth";
    case 5: return "fifth";
  }
}

// Extrinsic: a brand is only a name; `42 as Ranged` forges one anywhere.
type Ranged = number & { readonly __brand: "Ranged" };

export const toRanged = (n: number): Ranged | undefined =>
  Number.isInteger(n) && n >= 1 && n <= 5 ? (n as Ranged) : undefined;

export function ordinalRanged(n: Ranged): string {
  const names = ["first", "second", "third", "fourth", "fifth"];
  const name = names[n - 1];
  if (name === undefined) throw new Error("impossible: bad Ranged value");
  return name;
}
```

**C++**

```cpp
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>

// Closed in intent, but not intrinsically: static_cast<OneToFive>(6) compiles.
enum class OneToFive { One = 1, Two, Three, Four, Five };

std::string ordinal(OneToFive n) {
  switch (n) {  // -Wswitch flags a missing enumerator ...
    case OneToFive::One: return "first";
    case OneToFive::Two: return "second";
    case OneToFive::Three: return "third";
    case OneToFive::Four: return "fourth";
    case OneToFive::Five: return "fifth";
  }
  std::unreachable();  // ... but the compiler still needs this: enums are open
}

// Extrinsic: an opaque token issued by a trusted class.
class Ranged {
public:
  static std::optional<Ranged> make(int n) {
    if (n < 1 || n > 5) return std::nullopt;
    return Ranged(n);
  }
  int value() const { return n_; }
private:
  explicit Ranged(int n) : n_(n) {}
  int n_;
};

std::string ordinalRanged(Ranged r) {
  static const char* names[] = {"first", "second", "third", "fourth", "fifth"};
  if (r.value() < 1 || r.value() > 5) throw std::logic_error("impossible: bad Ranged value");
  return names[r.value() - 1];
}
```

More examples — a non-empty list as a trusted token vs a constructive type, the holes that forge tokens, labels that prevent mix-ups, and newtype noise — in all three languages: [examples.md](examples.md).

## Related skills

`correctness-by-construction` · `smart-constructor` · `make-illegal-states-unrepresentable` · `parse-dont-validate` · `airtight-abstractions` (trust boundaries) · `property-based-testing` (testing a trusted module's API) · `boolean-blindness`

## Sources

- **Alexis King, [Names are not type safety](https://lexi-lambda.github.io/blog/2020/11/01/names-are-not-type-safety/) (2020).**
- Alexis King, [Types as axioms, or: playing god with static types](https://lexi-lambda.github.io/blog/2020/08/13/types-as-axioms-or-playing-god-with-static-types/) (2020).
- Gabriella Gonzalez, [Ergonomic newtypes for Haskell strings and numbers](https://haskellforall.com/2023/04/ergonomic-newtypes-for-haskell-strings) (2023).
- Scott Wlaschin, [Designing with types: Single case union types](https://fsharpforfunandprofit.com/posts/designing-with-types-single-case-dus/) and [Non-string types](https://fsharpforfunandprofit.com/posts/designing-with-types-non-strings/) (2013).
- David Luposchainsky (quchen), [Algebraic blindness](https://github.com/quchen/articles/blob/master/algebraic-blindness.md).
- Further reading cited by the source: Freckle, *Tagged is not a Newtype* (2020).
