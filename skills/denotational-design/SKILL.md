---
name: denotational-design
description: Denotational design — define what an abstraction means (a mathematical model per type, a meaning per operation) before implementing it, then test the implementation against the meaning. Use when designing a library or core domain abstraction, or when an API's semantics are fuzzy.
---

# Denotational design

> *functional-architecture.org:* "Denotational Design is a software design methodology which tries to extract the essence of a domain's problem and describe it formally in machine-checkable code. Denotational design affords software designers to be absolutely precise in *what* they want to achieve before they talk about *how* they plan to achieve it. Denotational Design informs both the use and the implementation of a unit of software without coupling them. Denotational Design is therefore a methodology to build airtight abstraction barriers." (Pattern page: short description; long form upstream TODO. Method below after Conal Elliott.)

The **denotation** of a type is what its values *mean* — a simple mathematical object, independent of representation. A time series *means* a function `Time → Maybe Double`; an image means `Point → Color`; a set of integers means a predicate `Int → Bool`. Representations (arrays, trees, intervals, caches) are implementation choices; users reason with the meaning, implementers are free to optimize, and the meaning is the contract between them.

## Procedure

1. **Choose the model.** For the abstraction `T`, pick the simplest precise mathematical type `⟦T⟧` that captures what users care about (functions, sets, sequences, products, sums). Prefer total, representation-free models.
2. **Define each operation by its meaning.** For every operation `op`, write `⟦op x y⟧ = op′ ⟦x⟧ ⟦y⟧` — what it does to meanings.
3. **Let instances follow the model** (*type class morphism* principle): if `T` is a `Monoid`/`Functor`/`Applicative`, its instance means the model's instance: `⟦a <> b⟧ = ⟦a⟧ <> ⟦b⟧`. Laws then hold *for free*, inherited from the model.
4. **Implement** with any representation, as efficiently as needed.
5. **Test the implementation against the meaning:** a property per operation, `meaning (op x y) == op' (meaning x) (meaning y)` (`property-based-testing`). Expose only operations with meanings; hide the representation (`airtight-abstractions`).
6. **Revisit the model when requirements change**, not the representation first; a new requirement that has no meaning in the model means the model was wrong. A failing meaning-equation can also blame the model. In Hughes' search-tree experiment, `Data.List.insert` as the abstract `insert` allowed duplicate keys while the tree did not, and the fix was to correct the model (delete the key first), not the tree.

The equation in step 5 is Hoare's 1972 commuting diagram for data representations: the concrete operation followed by the abstraction function agrees with the abstract operation applied to the abstracted input (`toList (insert k v t) == abstractInsert k v (toList t)`). Hughes calls the abstract type the *model* and uses one such property per operation as a **model-based** property. Together they form a complete specification of the operations, and in his eight-bug experiment they found every bug fastest (`property-based-testing`). The cost is the model itself, which can be expensive or resemble the implementation more than is healthy. Equations *between* operations are the complementary, algebraic specification: Hughes, citing Guttag and Horning, notes that operations returning the type of interest can be specified relative to the observations that return other types, and that such a specification is *sufficiently complete* when it determines the value of every observation.

Done when: every public type has a stated denotation, every public operation has a semantic equation, and each equation is a passing property test against the implementation.

## Example: a set of integers meaning a predicate, implemented with intervals

Meaning: `⟦s⟧ :: Int -> Bool` (membership). Operations: `⟦empty⟧ = const False`, `⟦range lo hi⟧ = \x -> lo <= x && x < hi`, `⟦a ∪ b⟧ = \x -> ⟦a⟧ x || ⟦b⟧ x`. Implementation: sorted, disjoint, half-open intervals, merged on union. The properties are the meaning equations.

**Haskell**

```haskell
import Data.List (sortOn)
import Test.QuickCheck

newtype IntSet = IntSet [(Int, Int)] deriving (Show) -- sorted, disjoint [lo, hi)

-- The denotation.
member :: IntSet -> Int -> Bool
member (IntSet is) x = any (\(lo, hi) -> lo <= x && x < hi) is

empty :: IntSet
empty = IntSet []

range :: Int -> Int -> IntSet
range lo hi = if lo < hi then IntSet [(lo, hi)] else empty

union :: IntSet -> IntSet -> IntSet
union (IntSet a) (IntSet b) = IntSet (merge (sortOn fst (a <> b)))
  where
    merge ((l1, h1) : (l2, h2) : rest)
      | l2 <= h1 = merge ((l1, max h1 h2) : rest)
      | otherwise = (l1, h1) : merge ((l2, h2) : rest)
    merge xs = xs

instance Semigroup IntSet where (<>) = union -- its meaning: pointwise (||)
instance Monoid IntSet where mempty = empty -- its meaning: const False

genSet :: Gen IntSet
genSet = mconcat <$> listOf (range <$> chooseInt (-50, 50) <*> chooseInt (-50, 50))

main :: IO ()
main = do
  quickCheck (\lo hi x -> member (range lo hi) x == (lo <= x && x < hi))
  quickCheck (forAll genSet $ \a -> forAll genSet $ \b -> \x -> member (a <> b) x == (member a x || member b x))
  quickCheck (\x -> not (member mempty x))
```

**TypeScript**

```typescript
import fc from "fast-check";

type Interval = readonly [number, number]; // [lo, hi)
export type IntSet = readonly Interval[]; // sorted, disjoint

export const member = (s: IntSet, x: number): boolean => s.some(([lo, hi]) => lo <= x && x < hi); // the denotation

export const empty: IntSet = [];
export const range = (lo: number, hi: number): IntSet => (lo < hi ? [[lo, hi]] : empty);

export function union(a: IntSet, b: IntSet): IntSet {
  const sorted = [...a, ...b].sort((p, q) => p[0] - q[0]);
  const out: Interval[] = [];
  for (const [lo, hi] of sorted) {
    const last = out[out.length - 1];
    if (last && lo <= last[1]) out[out.length - 1] = [last[0], Math.max(last[1], hi)];
    else out.push([lo, hi]);
  }
  return out;
}

const int = fc.integer({ min: -50, max: 50 });
const set = fc.array(fc.tuple(int, int)).map((rs) => rs.reduce<IntSet>((acc, [l, h]) => union(acc, range(l, h)), empty));

fc.assert(fc.property(int, int, int, (lo, hi, x) => member(range(lo, hi), x) === (lo <= x && x < hi)));
fc.assert(fc.property(set, set, int, (a, b, x) => member(union(a, b), x) === (member(a, x) || member(b, x))));
fc.assert(fc.property(int, (x) => !member(empty, x)));
```

**C++**

```cpp
#include <rapidcheck.h>

#include <algorithm>
#include <utility>
#include <vector>

using IntSet = std::vector<std::pair<int, int>>;  // sorted, disjoint [lo, hi)

bool member(const IntSet& s, int x) {  // the denotation
  return std::any_of(s.begin(), s.end(), [x](const auto& iv) { return iv.first <= x && x < iv.second; });
}

IntSet range(int lo, int hi) { return lo < hi ? IntSet{{lo, hi}} : IntSet{}; }

IntSet unite(IntSet a, const IntSet& b) {
  a.insert(a.end(), b.begin(), b.end());
  std::sort(a.begin(), a.end());
  IntSet out;
  for (const auto& [lo, hi] : a) {
    if (!out.empty() && lo <= out.back().second) out.back().second = std::max(out.back().second, hi);
    else out.emplace_back(lo, hi);
  }
  return out;
}

int main() {
  auto small = [] { return *rc::gen::inRange(-50, 51); };
  auto set = [&] {
    IntSet s;
    for (int n = *rc::gen::inRange(0, 6); n > 0; --n) s = unite(s, range(small(), small()));
    return s;
  };
  rc::check("range means an interval", [&] {
    int lo = small(), hi = small(), x = small();
    RC_ASSERT(member(range(lo, hi), x) == (lo <= x && x < hi));
  });
  rc::check("union means (||)", [&] {
    IntSet a = set(), b = set();
    int x = small();
    RC_ASSERT(member(unite(a, b), x) == (member(a, x) || member(b, x)));
  });
}
```

## Related skills

`airtight-abstractions` · `algebraic-modelling` · `property-based-testing` · `make-illegal-states-unrepresentable` (the time-series-as-function model) · `late-decision-making` (model before representation) · `formal-verification` · `embedded-dsl`

## Sources

- functional-architecture.org, [Denotational Design](https://functional-architecture.org/denotational_design/) (pattern; short description, long form upstream TODO) and the time-series-as-function model in [Make Illegal States Unrepresentable](https://functional-architecture.org/make_illegal_states_unrepresentable/).
- John Hughes, [How to Specify It!](https://research.chalmers.se/publication/517894/file/517894_Fulltext.pdf) (2019; read from the author-authorized preprint in Johannes Link's [jqwik port](https://github.com/jlink/how-to-specify-it)), sections 4.5 and 6 — model-based properties as Hoare's abstraction-function diagram; the model as a specification and its costs; algebraic specification and sufficient completeness.
- Gabriella Gonzalez, [Why do our programs need to read input and write output?](https://haskellforall.com/2017/10/why-do-our-programs-need-to-read-input) (2017) — restating Conal Elliott's case for denotation-first composition.
- Further reading (not in the provided source list): Conal Elliott, *Denotational design with type class morphisms* (2009) and *Symbolic and Automatic Differentiation of Languages* (cited by the functional-architecture.org MISU page).
