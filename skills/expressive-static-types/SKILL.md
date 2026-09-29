---
name: expressive-static-types
description: Expressive static types — direct the type system as a tool (sum types, generics, precise return types, exhaustiveness, strict settings) instead of appeasing it with casts and any. Use when choosing compiler strictness, when tempted by any or casts, or when a type "cannot express" a requirement.
---

# Expressive static type systems

> *functional-architecture.org:* "Type systems allow you to enrich your code with descriptions of properties and requirements, which can be statically checked and enforced." (Pattern page upstream TODO.)

Two ways to see a type system:

- **Types as restrictions:** the checker is an oracle that predicts values and rejects programs it "cannot figure out". Every rejection feels like a limitation; the fix is a cast or `any`. In gradually typed languages this becomes a vicious cycle: the checker is overridden so often in the connective tissue of the program that it rarely catches anything interesting, which confirms it is useless.
- **Types as axioms:** declarations *create* values and rules; the programmer decides what the checker proves. "You do not serve the typechecker; the typechecker serves *you*." A type system does not come with a fixed list of things it "can prove" — restructuring data (`correctness-by-construction`) moves new properties within reach.

Name the property, not "strong" or "weak" typing: Smith says those words have "nearly no meaning at all", and that static and dynamic "types" are two different mechanisms whose goals only partly overlap. Ask instead whether the system is static or dynamic, *sound* (it gives a guarantee), explicit or implicit (declarations versus inference), and structural or nominal. A type system is, in Pierce's definition as Smith quotes it, "a tractable syntactic method for proving the absence of certain program behaviors by classifying phrases according to the kinds of values they compute". What it proves is left open, and that is the opening for types as axioms: Smith's examples include array bounds, security policies, and keeping unescaped strings out of SQL.

Static types are not about classifying the whole world either: they let each component state *exactly how much it needs to know* about its inputs and ignore the rest (`decoupled-by-default`, `parse-dont-validate`). And they report errors *relevantly* — before a program has half-executed and destroyed data, as a dynamically detected type error in the middle of a file rewrite does.

## Procedure

1. **Turn the checker all the way up** and keep it there: TypeScript `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noImplicitReturns`; C++ `-Wall -Wextra -Werror` (incl. `-Wswitch`, `-Wreturn-type`), `[[nodiscard]]`; GHC `-Wall` (incomplete patterns, partial functions).
2. **Write down the types first** for public functions: they state requirements, bound how much context a reader needs, and are documentation that cannot go stale.
3. **Express properties with the types you have:** sum types for alternatives, generics for "works for any", `readonly`/`const` for immutability, precise return types (overloads, generics, conditional types) instead of unions the caller must re-check, exhaustiveness checks (`never`, `std::visit`, `-Wincomplete-patterns`).
4. **When the checker "cannot" express something, change the data representation** before reaching for a cast (`make-illegal-states-unrepresentable`).
5. **Contain escape hatches** (`any`, `as`, `unsafeCoerce`, `reinterpret_cast`) in small, audited leaf modules; each one is a hard stop for type information flowing through the program.
6. **Know the limits at scale:** types stop at process and service boundaries; across them, parse at the edges, and let architecture (events, contracts, DDD) carry correctness (FUNARCH 2024 keynote).

7. **For arithmetic predicates, add a refinement layer.** Ordinary types cannot say "the divisor is non-zero" or "the index is in bounds". LiquidHaskell decorates types with predicates from logics that SMT solvers decide, e.g. `{v : Int | v /= 0}`, and checks contracts at compile time. It is a restricted form of dependent types: less expressive, far more automatic. It needs an SMT solver (Z3 is recommended), and it checks termination by default. Returning `Maybe` instead "merely kicks the can down the road", because the caller must eventually extract the value. Without such a layer, fall back to a smart constructor (`smart-constructor`).

Done when: the build fails on type warnings, escape hatches are confined to named boundary modules, and each "the type system can't do this" has been answered by a representation change or a documented extrinsic guard.

## What a type checker guarantees, and what people get wrong

- **It is a conservative prover.** If it accepts a program, the checked property holds. If it rejects, the property may or may not hold: by Rice's theorem no checker can decide such properties, and one that never rejects a correct program is impossible. Testing is the mirror image, since it never fails a correct program but can accept a broken one. Smith puts it as testing bounding correctness from above and proof from below. The checker's edge is that it re-proves the property after every change, where hand-kept proofs fall behind a codebase that changes daily.
- **Types reduce testing, not replace it.** Smith argues, and calls it controversial, that it does not make sense to do the same exhaustive unit testing in Haskell as in Ruby or Smalltalk; he says to scale it back a little, not to drop it. He also notes that types "can't check nearly as many properties of code as testing can" (`property-based-testing`).
- **Fallacies to avoid in either direction.** Static types do not imply type declarations (inference exists; the complaint is about *explicit* types), longer code, or up-front design (C and C++ header files are the culprit there, not typing). Dynamically typed languages are not weakly typed. Smith ranks the benefits from least to most significant: performance (a "red herring"), documentation that cannot go stale, tools that can analyze code, and correctness.

## Example: a return type that depends on the argument

`emptyLike(42) * 10` fails in TypeScript if `emptyLike` returns `number | string`: the signature throws away the relationship between input and output. Say what you mean instead.

**Haskell**

```haskell
{-# LANGUAGE TypeApplications #-}
-- The relationship between input and output type is the type class's job.
class EmptyLike a where
  emptyLike :: a -> a

instance EmptyLike Int where emptyLike _ = 0
instance EmptyLike [b] where emptyLike _ = []

example :: Int
example = emptyLike (42 :: Int) * 10 -- the checker knows this is an Int

-- Exhaustiveness is on by default with -Wall: adding a constructor flags every incomplete match.
data Season = Spring | Summer | Fall | Winter

containsChristmas :: Season -> Bool
containsChristmas Summer = True -- southern hemisphere
containsChristmas Winter = True -- northern hemisphere
containsChristmas Spring = False
containsChristmas Fall = False
```

**TypeScript**

```typescript
// Before: function emptyLike(v: number | string): number | string  — callers must re-check.
export function emptyLike<T extends number | string>(v: T): T extends number ? number : string;
export function emptyLike(v: number | string): number | string {
  return typeof v === "number" ? 0 : "";
}

export const example: number = emptyLike(42) * 10; // checks: the result is known to be a number

type Season = "spring" | "summer" | "fall" | "winter";

const absurd = (x: never): never => {
  throw new Error(`unhandled: ${String(x)}`);
};

export function containsChristmas(s: Season): boolean {
  switch (s) {
    case "summer": // southern hemisphere
    case "winter": // northern hemisphere
      return true;
    case "spring":
    case "fall":
      return false;
    default:
      return absurd(s); // a new season is a compile error here
  }
}
```

**C++**

```cpp
#include <string>
#include <type_traits>
#include <variant>

// The return type follows the argument type.
template <typename T>
  requires std::is_same_v<T, int> || std::is_same_v<T, std::string>
T emptyLike(const T&) { return T{}; }

const int example = emptyLike(42) * 10;

// Exhaustiveness via std::visit: each alternative must be handled or it fails to compile.
struct Spring {};
struct Summer {};
struct Fall {};
struct Winter {};
using Season = std::variant<Spring, Summer, Fall, Winter>;

template <class... Fs> struct overloaded : Fs... { using Fs::operator()...; };

bool containsChristmas(const Season& s) {
  return std::visit(overloaded{
                        [](Summer) { return true; },  // southern hemisphere
                        [](Winter) { return true; },  // northern hemisphere
                        [](Spring) { return false; },
                        [](Fall) { return false; },
                    },
                    s);
}
```

## Related skills

`correctness-by-construction` · `make-illegal-states-unrepresentable` · `parse-dont-validate` · `names-are-not-type-safety` · `decoupled-by-default` · `functional-programming-languages`

## Sources

- functional-architecture.org, [Expressive static type systems](https://functional-architecture.org/static_types/) (pattern page; upstream TODO).
- Alexis King, [Types as axioms, or: playing god with static types](https://lexi-lambda.github.io/blog/2020/08/13/types-as-axioms-or-playing-god-with-static-types/) (2020) and [No, dynamic type systems are not inherently more open](https://lexi-lambda.github.io/blog/2020/01/19/no-dynamic-type-systems-are-not-inherently-more-open/) (2020).
- Gabriella Gonzalez, [Dynamic type errors lack relevance](https://haskellforall.com/2021/01/dynamic-type-errors-lack-relevance) (2021), [Sometimes less is more in language design](https://haskellforall.com/2013/08/sometimes-less-is-more-in-language) (2013), [Worst practices should be hard](https://haskellforall.com/2016/04/worst-practices-should-be-hard) (2016).
- Chris Smith, [What To Know Before Debating Type Systems](http://blog.steveklabnik.com/posts/2010-07-17-what-to-know-before-debating-type-systems) (2010; read from the [reprint's source](https://github.com/steveklabnik/blog/blob/master/posts/2010-07-17-what-to-know-before-debating-type-systems.md)) — vocabulary, Pierce's definition, the conservative-prover trade-off, fallacies about static typing, the ranked benefits.
- Ranjit Jhala, Eric Seidel, Niki Vazou, [Programming with Refinement Types: An Introduction to LiquidHaskell](https://ucsd-progsys.github.io/liquidhaskell-tutorial/) (tutorial; chapter 1 read from the [repository](https://github.com/ucsd-progsys/liquidhaskell-tutorial/blob/main/src/Tutorial_01_Introduction.lhs)) — why "well-typed programs do go wrong", refinement types versus dependent types, SMT requirements.
- Marco Sampellegrini, [Architecting Functional Programs](https://dl.acm.org/doi/10.1145/3677998.3678219) (FUNARCH 2024 keynote) — the value of static types across service boundaries, and where architecture must take over.
