---
name: property-based-testing
description: Property-based testing — properties that hold for all inputs, checked with generated inputs and shrunk counterexamples (QuickCheck, fast-check, RapidCheck). Use when writing or reviewing tests for functions, parsers, data structures, state machines, or laws, or when asked what properties to test.
---

# Property-based testing

An example-based test checks one input. A **property** states something that must be true for *every* input; the framework generates many inputs, and when one fails it **shrinks** it to a minimal counterexample. A set of properties is a **specification** — often shorter and less ambiguous than a pile of examples.

Test against the **Enterprise Developer From Hell** (EDFH): an implementer who writes the laziest code that passes your tests (`if x == 1 && y == 2 then 3 else 0`). Random inputs defeat hard-coded special cases; well-chosen properties defeat plausible-but-wrong implementations. Usually *you* are the EDFH, unintentionally — PBT surfaces the assumptions you did not know you made.

Treat PBT as a **design** activity: a property that a trivial implementation satisfies means something about the requirement is still unstated.

## Choosing properties

Most properties come from seven patterns (Wlaschin) plus algebraic laws:

| Pattern | Formal name | Examples |
|---|---|---|
| **Different paths, same destination** | commutative diagram | `sort (map negate xs) == reverse (map negate (sort xs))`; `create(start).map(f) == create(f(start))` |
| **There and back again** | inverse / round trip | `decode (encode x) == x` (serialization, roman numerals, `write`/`read`, `insert`/`contains`) |
| **Some things never change** | invariant | length and contents preserved by sort; tree stays balanced; roman numerals never contain `IIII` |
| **The more things change, the more they stay the same** | idempotence | `sort . sort == sort`; `distinct . distinct == distinct`; applying a message twice = once |
| **Solve a smaller problem first** | structural induction | a list is sorted if its head ≤ its second element and its tail is sorted |
| **Hard to prove, easy to verify** | checking a certificate | concatenating the tokens of a split gives the input back; a found path really connects the maze |
| **The test oracle / two heads are better than one** | differential / model-based testing | optimized sort vs insertion sort; parallel vs sequential; system vs simplified model |
| **Algebraic laws** | associativity, identity, commutativity, functor/monad/category laws | `add x (add y z) == add (add x y) z`; `x + 0 == x`; `fmap id == id` |

Then **run the EDFH check** on every property: *what wrong implementation still passes?* Returning `[]` satisfies "adjacent pairs are ordered"; repeating the first element satisfies "same length". Add a complementary property until only correct implementations survive — for sorting, "adjacent pairs ordered" **and** "is a permutation of the input" together specify sort.

### Which kinds of property find bugs (Hughes)

Hughes names five approaches for pure code: validity (invariants), postconditions, metamorphic properties, inductive properties, and model-based properties. He tested them against a binary search tree with eight planted bugs:

- **Validity alone is weak.** Validity properties missed five of the eight bugs, and equivalence-preservation and insertion-completeness properties also missed many; an implementation returning `nil` everywhere passes every validity check. Every bug was caught by at least one postcondition, one metamorphic property, and one model-based property.
- **Model-based properties give the best return per property.** One property per operation, comparing `toList (insert k v t)` with the same operation on the simple model (an ordered list), found every bug in that operation, in a mean of 5.8 tests against 56 for metamorphic properties and 77 for postconditions. For one `union` bug the postcondition needed about 50 tests and the model property 8.4: the model property checks the whole result, the postcondition one random key. The cost is the model, which can be expensive or so close to the implementation that both share bugs.
- **Metamorphic properties are the fallback and an idea source.** They relate two related calls (`insert k v (insert k' v' t)` against the swapped order), give O(n²) candidate properties from n operations, and together axiomatize the API, with no guarantee of completeness. Degenerate ones involving `nil`, and "weak" ones whose preconditions exclude tricky cases, miss bugs. First drafts are often false ("the last insertion wins"; tree shapes differ), and the counterexample shows what to fix, for instance by comparing through an equivalence such as `toList`.
- **With limited time:** model-based plus validity properties; metamorphic properties when the model is costly or too close to the implementation.
- **Construct outcomes you can predict** when an oracle is missing: `find k (insert k v t) === Just v` and `find k (delete k t) === Nothing` test `find` without reimplementing it. Check that every tree really has the form `insert …` or `delete …`, or those tests are narrower than they look.

**Test your tests.** Test the generator and the shrinker separately from the operations: `prop ArbitraryValid t = valid t`, `prop ShrinkValid t = valid t ==> all valid (shrink t)`. A generator built from a buggy `insert` produced invalid trees and made unrelated properties fail with false positives; when `ArbitraryValid` fails, ignore the rest. A shrinker can break the invariant too (fix: `shrink = filter valid . genericShrink`). Also test completeness of the generator, that `delete` and `union` cannot build trees `insert` cannot, which justifies generating trees by insertions alone. For equivalence-preservation, two independent random trees are almost never equivalent, so generate equivalent pairs together (the same entries inserted in different orders).

## Procedure

1. Write down what the unit must do in words; turn each sentence into a candidate property using the table.
2. For each property, name a wrong implementation that passes it; add properties until none does.
3. Choose generators: the default ones for unconstrained inputs, **custom generators** for constrained domains (valid roman-numeral inputs 1–3999). Use preconditions (`==>`, `fc.pre`, `RC_PRE`) only to discard a *small* fraction of inputs.
4. Check the generator's distribution. Default integer generators cluster near zero; a property that fails only above 80 may never be exercised until you raise the size. Label/classify when unsure. When a property relates independently generated values, measure how often they are actually related: a random key was present in an independently generated tree only 21% of the time, and drawing keys from a smaller range raised that to 55%. Collisions are important cases: `x /= y` for two default `Int`s fails in about 3.3% of runs, with the smaller key type in 9.3%, and with uniform 64-bit integers practically never. falsify's `getContext`/`sized` lets a property start with small ranges and widen them as the run proceeds.
5. Keep each property fast — it runs hundreds of times, more when shrinking. Beware hidden exponential work (enumerating permutations).
6. Add example-based tests for known boundaries (0, max, 3999/4000) and as readable documentation. If the domain is small, test it exhaustively.
7. Record failing seeds and turn important counterexamples into regression examples.

Done when: every stated requirement is covered by a property, every property has survived the EDFH check, known boundaries have explicit examples, and the suite runs in seconds.

## Example: the two properties that specify sorting

**Haskell** (QuickCheck)

```haskell
import Data.List (delete, sort)
import Test.QuickCheck

adjacentPairsOrdered :: ([Int] -> [Int]) -> [Int] -> Bool
adjacentPairsOrdered sortFn xs = and (zipWith (<=) ys (drop 1 ys))
  where ys = sortFn xs

isPermutationOf :: [Int] -> [Int] -> Bool
isPermutationOf [] ys = null ys
isPermutationOf (x : xs) ys = x `elem` ys && isPermutationOf xs (delete x ys)

prop_sorts :: ([Int] -> [Int]) -> [Int] -> Property
prop_sorts sortFn xs =
  counterexample "adjacent pairs ordered" (adjacentPairsOrdered sortFn xs)
    .&&. counterexample "permutation of input" (sortFn xs `isPermutationOf` xs)

main :: IO ()
main = do
  quickCheck (prop_sorts sort) -- passes
  quickCheck (expectFailure (prop_sorts (const []))) -- EDFH #1: ordered, but loses elements
  quickCheck (expectFailure (prop_sorts (\xs -> map (const (minimum' xs)) xs))) -- EDFH #2
  where minimum' xs = if null xs then 0 else minimum xs
```

**TypeScript** (fast-check)

```typescript
import fc from "fast-check";

const adjacentPairsOrdered = (ys: readonly number[]) => ys.every((y, i) => i === 0 || ys[i - 1]! <= y);

const isPermutationOf = (xs: readonly number[], ys: readonly number[]) => {
  const counts = new Map<number, number>();
  for (const x of xs) counts.set(x, (counts.get(x) ?? 0) + 1);
  for (const y of ys) counts.set(y, (counts.get(y) ?? 0) - 1);
  return [...counts.values()].every((c) => c === 0);
};

const sorts = (sortFn: (xs: number[]) => number[]) =>
  fc.property(fc.array(fc.integer()), (xs) => {
    const ys = sortFn([...xs]);
    return adjacentPairsOrdered(ys) && isPermutationOf(xs, ys);
  });

fc.assert(sorts((xs) => xs.sort((a, b) => a - b))); // passes
// fc.assert(sorts(() => []));                        // EDFH: fails with counterexample [0]
```

**C++** (RapidCheck)

```cpp
#include <rapidcheck.h>

#include <algorithm>
#include <functional>
#include <vector>

bool adjacentPairsOrdered(const std::vector<int>& ys) { return std::is_sorted(ys.begin(), ys.end()); }

bool isPermutationOf(const std::vector<int>& xs, const std::vector<int>& ys) {
  return std::is_permutation(xs.begin(), xs.end(), ys.begin(), ys.end());
}

void checkSorts(const std::function<std::vector<int>(std::vector<int>)>& sortFn) {
  rc::check("sort: ordered and a permutation", [&](const std::vector<int>& xs) {
    auto ys = sortFn(xs);
    RC_ASSERT(adjacentPairsOrdered(ys));
    RC_ASSERT(isPermutationOf(xs, ys));
  });
}

int main() {
  checkSorts([](std::vector<int> xs) { std::sort(xs.begin(), xs.end()); return xs; });
  // checkSorts([](std::vector<int>) { return std::vector<int>{}; });  // EDFH: falsified by [0]
}
```

More worked properties — addition and the EDFH, round-tripping roman numerals with a custom generator, idempotence and invariants, "hard to prove, easy to verify", a test oracle and model-based testing of a queue, and generated *functions* as inputs — each in QuickCheck, fast-check, and RapidCheck: [examples.md](examples.md). Library notes and configuration: [libraries.md](libraries.md).

## PBT and design

- PBT pushes the domain model: Roman numerals broke on `0` and `4000`, which says the input is not an `int` but a `PositiveInteger` below 4000 (`smart-constructor`, `make-illegal-states-unrepresentable`).
- PBT improves APIs: testing `Dollar.times` and `Dollar.add` along two paths reveals the general operation `map`, and one property for `map` replaces many.
- PBT works best on pure code, so it pulls effects to the edge (`functional-core-imperative-shell`). For stateful and distributed systems, extract the logic into a model and test against it — John Hughes' team refactored a distributed store to make exactly this possible.
- Laws of abstractions (monoid, functor, category) are properties; test them whenever you write an instance (`algebraic-modelling`). To test laws for things you cannot compare or generate directly (pipes, parsers), generate random *programs* from the abstraction's own primitives and compare their observable behaviour.
- PBT tests the trusted module behind an extrinsic guarantee (`names-are-not-type-safety`).
- **Shrinking styles differ.** Hedgehog-style *integrated* shrinking derives the shrinker from the generator, so `filter even <$> genList` stays even while shrinking; hand-written shrinkers can break invariants (above). falsify adds Hypothesis-style *internal* shrinking, documented as correct even through monadic bind: in `do n <- genLength; replicateM n g`, `n` and the elements can shrink in any order.
- **Two equalities.** Structural equality distinguishes representations that should be equal outside the abstraction barrier, so export observational equivalence as `Eq` and keep structural equality for tests, in a hidden representation type behind an exported newtype or in an `Internals` module (`airtight-abstractions`). Validity properties depend on the representation (the implementor's view); metamorphic and model-based ones use only the exported API (the user's view).

## Related skills

`algebraic-modelling` · `pure-functions` · `functional-core-imperative-shell` · `smart-constructor` · `names-are-not-type-safety` · `formal-verification` (proofs where properties are not enough) · `composable-effects` (contract tests for fakes)

## Sources

Scott Wlaschin, *Property Based Testing* series (F# for Fun and Profit, 2014):
[1 The Enterprise Developer from Hell](https://fsharpforfunandprofit.com/posts/property-based-testing/) ·
[2 Understanding FsCheck](https://fsharpforfunandprofit.com/posts/property-based-testing-1/) ·
[3 Choosing properties for property-based testing](https://fsharpforfunandprofit.com/posts/property-based-testing-2/) ·
[4 Choosing properties in practice, part 1](https://fsharpforfunandprofit.com/posts/property-based-testing-3/) ·
[5 part 2](https://fsharpforfunandprofit.com/posts/property-based-testing-4/) ·
[6 part 3](https://fsharpforfunandprofit.com/posts/property-based-testing-5/).
John Hughes, [How to Specify It!](https://research.chalmers.se/publication/517894/file/517894_Fulltext.pdf) (2019; final version published by Springer, 2020) — the five kinds of property, the eight-bugs experiment, testing generators and shrinkers, distribution and collisions, the two equalities (read from the author-authorized CC-BY preprint of June 2020 in Johannes Link's [jqwik port](https://github.com/jlink/how-to-specify-it)); Well-Typed, [falsify](https://github.com/well-typed/falsify) (0.4.0; read the generator documentation and changelog in the repository, not the blog post or the Haskell Unfolder episode).
Also: functional-architecture.org, [Property-based testing](https://functional-architecture.org/property_based_testing/) (pattern page; upstream TODO); Gabriella Gonzalez, [Test stream programming using Haskell's QuickCheck](https://haskellforall.com/2013/11/test-stream-programming-using-haskells) (2013) and [Purify code using free monads](https://haskellforall.com/2012/07/purify-code-using-free-monads) (2012); Edsko de Vries & Andres Löh, *The Haskell Unfolder* (Well-Typed) episodes on falsify, laws, and testing without a reference implementation.
