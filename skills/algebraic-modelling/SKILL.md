---
name: algebraic-modelling
description: Algebraic modelling — find properties (associativity, identity, idempotency, …) and structures (monoids, semilattices, functors) in the domain, then derive implementation and tests from the laws. Use when designing combine/merge/aggregate operations, library APIs, map-reduce, or laws to property-test.
---

# Algebraic modelling

Algebraic modelling (algebra-driven design) lets you focus on understanding the problem instead of incidental implementation detail. Look for well-known **mathematical properties** in the problem; certain combinations of them form **algebraic structures**. These structures are exceptionally well studied, so recognizing one gives you — for free — a deep understanding, reusable library code and algorithms, a shared vocabulary, and the laws to test. What you share with others is not just an implementation, but the understanding of the problem.

## Properties to look for

| Property | Equation | Example in a domain |
|---|---|---|
| Associativity | `(a • b) • c = a • (b • c)` | merging two summaries, concatenating logs, combining permissions |
| Identity | `e • a = a = a • e` | the empty summary, no-op config overlay, "allow nothing" |
| Commutativity | `a • b = b • a` | adding counts, set union — order of arrival does not matter |
| Idempotency | `a • a = a` | set union, max, "mark as read", deduplicated messages |
| Invertibility | `a • a⁻¹ = e` | ledger entries and reversals, undo |
| Distributivity | `a ⊗ (b ⊕ c) = (a ⊗ b) ⊕ (a ⊗ c)` | streams in turtle's mathematical API: `(x + y) * z = x * z + y * z` (and on the left up to line order) |
| Annihilation | `z • a = z` | "deny" overrides everything; an empty stream in a product |

| Structure | Properties | You get |
|---|---|---|
| Semigroup / monoid | associative (+ identity) | `mconcat`/`reduce`, divide-and-conquer, parallel map-reduce, incremental aggregation |
| Commutative monoid | + commutative | order-insensitive aggregation (streams, distributed counters) |
| Semilattice | + idempotent | convergent replicated data (CRDTs), caches that merge safely |
| Group | + inverses | undo, diffs, reversible transactions |
| Functor / applicative / monad | mapping, combining, sequencing laws | uniform composition of effects, parsers, validation, queries |

## Procedure

1. **List the operations** of the domain: how are values combined, merged, overlaid, sequenced, compared?
2. **Test each operation against the property list** — on paper first, with small examples. Ask "what is the empty one?", "does grouping matter?", "does order matter?", "does repeating matter?".
3. **Name the structure** the properties form, and implement the standard interface (`Semigroup`/`Monoid`, a `combine`/`empty` pair, `operator+` with an identity).
4. **Turn the laws into property tests** (`property-based-testing`). Algebraic laws are the easiest properties to find and among the most powerful.
5. **Reuse the ecosystem**: `foldMap`, `mconcat`, parallel reduction, streaming folds, library algorithms that require the structure.
6. **When stuck, change the representation until the structure appears** — e.g. a mean is not a monoid, but a `(count, sum)` pair is, and the mean is derived at the end. Theorem provers can check that chosen properties combine sensibly.

Done when: every combining operation in the model is identified with a named structure, its laws are property-tested, and aggregations use the structure's generic operations instead of hand-written loops.

## Example: a mergeable summary statistic

A mean is not associative, but `(count, total, min, max)` is a monoid, so summaries can be computed per partition, per shard, per thread, or incrementally, and merged in any grouping.

**Haskell**

```haskell
import Test.QuickCheck

data Summary = Summary {count :: Int, total :: Integer, smallest :: Maybe Integer, largest :: Maybe Integer}
  deriving (Eq, Show)

instance Semigroup Summary where
  Summary c1 t1 lo1 hi1 <> Summary c2 t2 lo2 hi2 =
    Summary (c1 + c2) (t1 + t2) (pick min lo1 lo2) (pick max hi1 hi2)
    where
      pick f (Just a) (Just b) = Just (f a b)
      pick _ a Nothing = a
      pick _ Nothing b = b

instance Monoid Summary where
  mempty = Summary 0 0 Nothing Nothing

single :: Integer -> Summary
single x = Summary 1 x (Just x) (Just x)

mean :: Summary -> Maybe Double
mean (Summary 0 _ _ _) = Nothing
mean (Summary c t _ _) = Just (fromIntegral t / fromIntegral c)

-- The laws, as properties; plus "splitting the input anywhere gives the same result".
main :: IO ()
main = do
  quickCheck (\a b c -> let (x, y, z) = (single a, single b, single c) in (x <> y) <> z == x <> (y <> z))
  quickCheck (\a -> mempty <> single a == single a && single a <> mempty == single a)
  quickCheck (\xs ys -> foldMap single (xs <> ys) == foldMap single xs <> foldMap single (ys :: [Integer]))
```

**TypeScript**

```typescript
import fc from "fast-check";

type Summary = { count: number; total: number; min: number | null; max: number | null };

const empty: Summary = { count: 0, total: 0, min: null, max: null };
const pick = (f: (a: number, b: number) => number, a: number | null, b: number | null) =>
  a === null ? b : b === null ? a : f(a, b);
const combine = (x: Summary, y: Summary): Summary => ({
  count: x.count + y.count,
  total: x.total + y.total,
  min: pick(Math.min, x.min, y.min),
  max: pick(Math.max, x.max, y.max),
});
const single = (n: number): Summary => ({ count: 1, total: n, min: n, max: n });
const summarize = (xs: readonly number[]) => xs.map(single).reduce(combine, empty);
export const mean = (s: Summary) => (s.count === 0 ? null : s.total / s.count);

const eq = (a: Summary, b: Summary) => JSON.stringify(a) === JSON.stringify(b);
const int = fc.integer({ min: -1_000_000, max: 1_000_000 });

fc.assert(fc.property(int, int, int, (a, b, c) =>
  eq(combine(combine(single(a), single(b)), single(c)), combine(single(a), combine(single(b), single(c))))));
fc.assert(fc.property(int, (a) => eq(combine(empty, single(a)), single(a)) && eq(combine(single(a), empty), single(a))));
fc.assert(fc.property(fc.array(int), fc.array(int), (xs, ys) =>
  eq(summarize([...xs, ...ys]), combine(summarize(xs), summarize(ys)))));
```

**C++**

```cpp
#include <rapidcheck.h>

#include <algorithm>
#include <optional>
#include <vector>

struct Summary {
  long long count = 0, total = 0;
  std::optional<long long> min, max;
  bool operator==(const Summary&) const = default;
};

template <typename F>
std::optional<long long> pick(F f, std::optional<long long> a, std::optional<long long> b) {
  if (!a) return b;
  if (!b) return a;
  return f(*a, *b);
}

Summary operator+(const Summary& x, const Summary& y) {
  return {x.count + y.count, x.total + y.total,
          pick([](long long a, long long b) { return std::min(a, b); }, x.min, y.min),
          pick([](long long a, long long b) { return std::max(a, b); }, x.max, y.max)};
}

Summary single(long long x) { return {1, x, x, x}; }

Summary summarize(const std::vector<int>& xs) {
  Summary s;  // the identity
  for (int x : xs) s = s + single(x);
  return s;
}

int main() {
  rc::check("associative", [](int a, int b, int c) {
    RC_ASSERT((single(a) + single(b)) + single(c) == single(a) + (single(b) + single(c)));
  });
  rc::check("identity", [](int a) { RC_ASSERT(Summary{} + single(a) == single(a) && single(a) + Summary{} == single(a)); });
  rc::check("split anywhere", [](std::vector<int> xs, std::vector<int> ys) {
    auto all = xs;
    all.insert(all.end(), ys.begin(), ys.end());
    RC_ASSERT(summarize(all) == summarize(xs) + summarize(ys));
  });
}
```

More: [examples.md](examples.md) — a semilattice (convergent merge), a *mathematical API* whose `+` and `*` on streams follow the distributive law, and probability distributions as a monoid, in three languages.

## Related skills

`composition-and-closure` · `property-based-testing` · `denotational-design` · `everything-as-a-value` · `event-sourcing` (folds over events) · `formal-verification`

## Sources

- functional-architecture.org, [Algebraic Modelling](https://functional-architecture.org/algebra/) (published principle page), recommending Sandy Maguire, *Algebra-Driven Design* (Leanpub).
- Gabriella Gonzalez, [Mathematical APIs](https://haskellforall.com/2015/04/mathematical-apis) (2015), [Equational reasoning at scale](https://haskellforall.com/2014/07/equational-reasoning-at-scale) (2014), [Electoral vote distributions are Monoids](https://haskellforall.com/2016/10/electoral-vote-distributions-are-monoids) (2016), [From mathematics to map-reduce](https://haskellforall.com/2016/02/from-mathematics-to-map-reduce) (2016), [What does "isomorphic" mean (in Haskell)?](https://haskellforall.com/2022/10/what-does-isomorphic-mean-in-haskell) (2022), [The wizard monoid](https://haskellforall.com/2018/02/the-wizard-monoid) (2018).
- Scott Wlaschin, [The Enterprise Developer from Hell](https://fsharpforfunandprofit.com/posts/property-based-testing/) — addition *defined* by commutativity, associativity, and identity.
