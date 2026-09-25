# Algebraic modelling — worked examples

Each example is given in Haskell, TypeScript, and C++. Each block is self-contained.

## 1. A semilattice converges: a replicated counter

Replicas of a counter exchange state in any order, any number of times. If `merge` is associative, commutative, **and idempotent** (a join-semilattice), every replica converges to the same value no matter how messages are reordered or duplicated. A grow-only counter stores one count per node and merges with a pointwise maximum.

**Haskell**

```haskell
import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map
import Test.QuickCheck

newtype GCounter = GCounter (Map String Int) deriving (Eq, Show)

instance Semigroup GCounter where
  GCounter a <> GCounter b = GCounter (Map.unionWith max a b)

instance Monoid GCounter where
  mempty = GCounter Map.empty

increment :: String -> GCounter -> GCounter
increment node (GCounter m) = GCounter (Map.insertWith (+) node 1 m)

value :: GCounter -> Int
value (GCounter m) = sum m

counter :: Gen GCounter
counter = GCounter . Map.fromList <$> listOf ((,) <$> elements ["a", "b", "c"] <*> chooseInt (0, 100))

main :: IO ()
main = do
  quickCheck (forAll counter (\x -> x <> x == x)) -- idempotent: duplicates are harmless
  quickCheck (forAll counter (\x -> forAll counter (\y -> x <> y == y <> x))) -- commutative: order is irrelevant
  quickCheck (forAll counter (\x -> forAll counter (\y -> forAll counter (\z -> (x <> y) <> z == x <> (y <> z)))))
```

**TypeScript**

```typescript
import fc from "fast-check";

type GCounter = ReadonlyMap<string, number>;

export const merge = (a: GCounter, b: GCounter): GCounter => {
  const out = new Map(a);
  for (const [k, v] of b) out.set(k, Math.max(out.get(k) ?? 0, v));
  return out;
};
export const increment = (node: string, c: GCounter): GCounter => new Map(c).set(node, (c.get(node) ?? 0) + 1);
export const value = (c: GCounter) => [...c.values()].reduce((a, b) => a + b, 0);

const canon = (c: GCounter) => JSON.stringify([...c].sort(([a], [b]) => a.localeCompare(b)));
const counter = fc
  .array(fc.tuple(fc.constantFrom("a", "b", "c"), fc.nat(100)))
  .map((kvs) => kvs.reduce<GCounter>((acc, [k, v]) => merge(acc, new Map([[k, v]])), new Map()));

fc.assert(fc.property(counter, (x) => canon(merge(x, x)) === canon(x)));
fc.assert(fc.property(counter, counter, (x, y) => canon(merge(x, y)) === canon(merge(y, x))));
fc.assert(fc.property(counter, counter, counter, (x, y, z) => canon(merge(merge(x, y), z)) === canon(merge(x, merge(y, z)))));
```

**C++**

```cpp
#include <rapidcheck.h>

#include <algorithm>
#include <map>
#include <string>

using GCounter = std::map<std::string, int>;

GCounter merge(GCounter a, const GCounter& b) {
  for (const auto& [k, v] : b) a[k] = std::max(a[k], v);
  return a;
}

GCounter increment(const std::string& node, GCounter c) { ++c[node]; return c; }

int value(const GCounter& c) {
  int sum = 0;
  for (const auto& [k, v] : c) sum += v;
  return sum;
}

int main() {
  auto counter = [] {
    GCounter c;
    for (std::string node : {"a", "b", "c"})
      if (*rc::gen::arbitrary<bool>()) c[node] = *rc::gen::inRange(0, 101);
    return c;
  };
  rc::check("idempotent", [&] { auto x = counter(); RC_ASSERT(merge(x, x) == x); });
  rc::check("commutative", [&] { auto x = counter(), y = counter(); RC_ASSERT(merge(x, y) == merge(y, x)); });
  rc::check("associative", [&] {
    auto x = counter(), y = counter(), z = counter();
    RC_ASSERT(merge(merge(x, y), z) == merge(x, merge(y, z)));
  });
}
```

## 2. A mathematical API: streams with `+` and `*`

Gonzalez's `turtle` lets streams of lines behave like numbers: `+` concatenates streams, `*` pairs every element of the left with every element of the right (concatenating the strings), `0` is the empty stream, `1` the stream of one empty line. Users can then *reason* with school algebra: `(a + b) * ", " * (c + d)` expands to four lines by distributivity.

Property tests sharpen the claim. `*` distributes over `+` **exactly on the right**, `(a + b) * c = a * c + b * c`, but **only up to the order of lines on the left**: `a * (b + c)` and `a * b + a * c` contain the same lines in a different order (counterexample: `a = ["", ""]`, `b = [""]`, `c = ["a"]`). Streams are a semiring if you read them as bags of lines, not as sequences — exactly the kind of fact algebraic modelling wants stated.

**Haskell**

```haskell
{-# LANGUAGE OverloadedStrings #-}
import Data.List (sort)
import Data.String (IsString (..))
import Test.QuickCheck

newtype Stream = Stream [String] deriving (Eq, Show)

instance IsString Stream where
  fromString s = Stream [s]

instance Num Stream where
  Stream xs + Stream ys = Stream (xs <> ys)
  Stream xs * Stream ys = Stream [x <> y | x <- xs, y <- ys]
  fromInteger n = Stream (replicate (fromInteger n) "")
  abs = id
  signum = id
  negate = id

example :: Stream
example = ("Line 1" + "Line 2") * ", " * ("Line A" + "Line B")
-- Stream ["Line 1, Line A","Line 1, Line B","Line 2, Line A","Line 2, Line B"]

main :: IO ()
main = do
  print example
  quickCheck (\a b c -> (Stream a + Stream b) * Stream c == Stream a * Stream c + Stream b * Stream c) -- exact
  quickCheck (\a b c -> bag (Stream a * (Stream b + Stream c)) == bag (Stream a * Stream b + Stream a * Stream c)) -- as bags
  quickCheck (\a -> Stream a * 1 == Stream a && Stream a * 0 == 0)
  where
    bag (Stream xs) = sort xs
```

**TypeScript**

```typescript
import fc from "fast-check";

type Stream = readonly string[];
const add = (xs: Stream, ys: Stream): Stream => [...xs, ...ys];
const mul = (xs: Stream, ys: Stream): Stream => xs.flatMap((x) => ys.map((y) => x + y));
const zero: Stream = [];
const one: Stream = [""];

export const example = mul(mul(add(["Line 1"], ["Line 2"]), [", "]), add(["Line A"], ["Line B"]));

const same = (a: Stream, b: Stream) => JSON.stringify(a) === JSON.stringify(b);
const bag = (a: Stream) => [...a].sort();
const stream = fc.array(fc.string(), { maxLength: 5 });
fc.assert(fc.property(stream, stream, stream, (a, b, c) => same(mul(add(a, b), c), add(mul(a, c), mul(b, c))))); // exact
fc.assert(fc.property(stream, stream, stream, (a, b, c) => same(bag(mul(a, add(b, c))), bag(add(mul(a, b), mul(a, c)))))); // as bags
fc.assert(fc.property(stream, (a) => same(mul(a, one), a) && same(mul(a, zero), zero)));
```

**C++**

```cpp
#include <rapidcheck.h>

#include <algorithm>
#include <iostream>
#include <string>
#include <vector>

struct Stream {
  std::vector<std::string> lines;
  bool operator==(const Stream&) const = default;
};

Stream operator+(const Stream& a, const Stream& b) {
  Stream out = a;
  out.lines.insert(out.lines.end(), b.lines.begin(), b.lines.end());
  return out;
}

Stream operator*(const Stream& a, const Stream& b) {
  Stream out;
  for (const auto& x : a.lines)
    for (const auto& y : b.lines) out.lines.push_back(x + y);
  return out;
}

Stream s(std::string line) { return Stream{{std::move(line)}}; }
const Stream zero{};
const Stream one{{""}};

int main() {
  for (const auto& l : ((s("Line 1") + s("Line 2")) * s(", ") * (s("Line A") + s("Line B"))).lines)
    std::cout << l << '\n';
  rc::check("right-distributive (exact)", [](std::vector<std::string> a, std::vector<std::string> b, std::vector<std::string> c) {
    Stream A{a}, B{b}, C{c};
    RC_ASSERT((A + B) * C == A * C + B * C);
  });
  rc::check("left-distributive (as bags)", [](std::vector<std::string> a, std::vector<std::string> b, std::vector<std::string> c) {
    Stream A{a}, B{b}, C{c};
    auto bag = [](Stream s) { std::sort(s.lines.begin(), s.lines.end()); return s; };
    RC_ASSERT(bag(A * (B + C)) == bag(A * B + A * C));
  });
  rc::check("identities", [](std::vector<std::string> a) {
    Stream A{a};
    RC_ASSERT(A * one == A && A * zero == zero);
  });
}
```

## 3. Probability distributions are a monoid

Gonzalez's electoral-vote exercise: each state contributes its electoral votes with some probability. A distribution over vote totals is a map from total to probability; combining two independent distributions is **convolution**, which is associative with the identity "0 votes with probability 1". The national distribution is then just `mconcat` over the states — and the computation can be split, parallelized, or done incrementally.

**Haskell**

```haskell
import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map

newtype Distribution = Distribution (Map Int Double) deriving (Show)

instance Semigroup Distribution where
  Distribution a <> Distribution b =
    Distribution (Map.fromListWith (+) [(x + y, p * q) | (x, p) <- Map.toList a, (y, q) <- Map.toList b])

instance Monoid Distribution where
  mempty = Distribution (Map.singleton 0 1)

state :: Double -> Int -> Distribution -- probability of winning, electoral votes
state p votes = Distribution (Map.fromListWith (+) [(votes, p), (0, 1 - p)])

chanceOfAtLeast :: Int -> Distribution -> Double
chanceOfAtLeast n (Distribution d) = sum [p | (votes, p) <- Map.toList d, votes >= n]

main :: IO ()
main = print (chanceOfAtLeast 30 (mconcat [state 0.9 20, state 0.5 10, state 0.3 15]))
```

**TypeScript**

```typescript
type Distribution = ReadonlyMap<number, number>;

const identity: Distribution = new Map([[0, 1]]);

const combine = (a: Distribution, b: Distribution): Distribution => {
  const out = new Map<number, number>();
  for (const [x, p] of a) for (const [y, q] of b) out.set(x + y, (out.get(x + y) ?? 0) + p * q);
  return out;
};

const state = (p: number, votes: number): Distribution =>
  votes === 0 ? identity : new Map([[votes, p], [0, 1 - p]]);

export const chanceOfAtLeast = (n: number, d: Distribution) =>
  [...d].filter(([votes]) => votes >= n).reduce((sum, [, p]) => sum + p, 0);

export const result = chanceOfAtLeast(30, [state(0.9, 20), state(0.5, 10), state(0.3, 15)].reduce(combine, identity));
```

**C++**

```cpp
#include <iostream>
#include <map>
#include <numeric>
#include <vector>

using Distribution = std::map<int, double>;

const Distribution identity{{0, 1.0}};

Distribution operator*(const Distribution& a, const Distribution& b) {  // convolution
  Distribution out;
  for (const auto& [x, p] : a)
    for (const auto& [y, q] : b) out[x + y] += p * q;
  return out;
}

Distribution state(double p, int votes) {
  Distribution d;
  d[votes] += p;
  d[0] += 1 - p;
  return d;
}

double chanceOfAtLeast(int n, const Distribution& d) {
  double sum = 0;
  for (const auto& [votes, p] : d) if (votes >= n) sum += p;
  return sum;
}

int main() {
  std::vector<Distribution> states{state(0.9, 20), state(0.5, 10), state(0.3, 15)};
  auto total = std::accumulate(states.begin(), states.end(), identity,
                               [](const Distribution& a, const Distribution& b) { return a * b; });
  std::cout << chanceOfAtLeast(30, total) << '\n';
}
```
