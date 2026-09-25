# Property-based testing — worked examples

Each example is given with QuickCheck (Haskell), fast-check (TypeScript), and RapidCheck (C++). Each block is self-contained and runnable; properties marked "EDFH" are *expected* to fail.

## 1. Addition, and the Enterprise Developer From Hell

Commutativity alone admits multiplication; "add 1 twice = add 2" admits subtraction; both admit `0`. Identity (`x + 0 = x`) forces the result to depend on the input. A malicious `add` that is correct below 10 slips past magic-number properties, but not past associativity.

**Haskell**

```haskell
import Test.QuickCheck

additionSpec :: (Int -> Int -> Int) -> Property
additionSpec add =
  conjoin
    [ counterexample "commutative" (property (\x y -> add x y == add y x))
    , counterexample "associative" (property (\x y z -> add x (add y z) == add (add x y) z))
    , counterexample "identity" (property (\x -> add x 0 == x))
    ]

edfhAdd :: Int -> Int -> Int
edfhAdd x y = if x < 10 || y < 10 then x + y else x * y -- right for small inputs only

main :: IO ()
main = do
  quickCheck (additionSpec (+))
  quickCheck (expectFailure (additionSpec (*))) -- EDFH: identity fails
  quickCheck (expectFailure (additionSpec (\_ _ -> 0))) -- EDFH: identity fails
  quickCheckWith stdArgs {maxSuccess = 1000} (expectFailure (additionSpec edfhAdd)) -- EDFH: associativity fails
```

**TypeScript**

```typescript
import fc from "fast-check";

type Add = (x: number, y: number) => number;
const int = fc.integer({ min: -1000, max: 1000 });

const passes = (add: Add) =>
  [
    fc.check(fc.property(int, int, (x, y) => add(x, y) === add(y, x)), { numRuns: 1000 }),
    fc.check(fc.property(int, int, int, (x, y, z) => add(x, add(y, z)) === add(add(x, y), z)), { numRuns: 1000 }),
    fc.check(fc.property(int, (x) => add(x, 0) === x), { numRuns: 1000 }),
  ].every((result) => !result.failed);

const edfhAdd: Add = (x, y) => (x < 10 || y < 10 ? x + y : x * y);

export const results = {
  correct: passes((x, y) => x + y), // true
  multiply: passes((x, y) => x * y), // false: identity
  zero: passes(() => 0), // false: identity
  edfh: passes(edfhAdd), // false: associativity
};
```

**C++**

```cpp
#include <rapidcheck.h>

#include <functional>
#include <iostream>

using Add = std::function<int(int, int)>;

bool additionSpec(const Add& add) {
  auto small = [] { return *rc::gen::inRange(-1000, 1000); };
  bool commutative = rc::check("commutative", [&] {
    int x = small(), y = small();
    RC_ASSERT(add(x, y) == add(y, x));
  });
  bool associative = rc::check("associative", [&] {
    int x = small(), y = small(), z = small();
    RC_ASSERT(add(x, add(y, z)) == add(add(x, y), z));
  });
  bool identity = rc::check("identity", [&] {
    int x = small();
    RC_ASSERT(add(x, 0) == x);
  });
  return commutative && associative && identity;
}

int main() {
  Add edfh = [](int x, int y) { return (x < 10 || y < 10) ? x + y : x * y; };
  std::cout << additionSpec(std::plus<int>()) << '\n';  // 1
  std::cout << additionSpec(edfh) << '\n';               // 0: associativity falsified
}
```

## 2. There and back again, with a custom generator: roman numerals

Two independent encoders (tally and bi-quinary) are checked against each other (oracle), and encoding is checked against a decoder (round trip). Inputs come from a generator restricted to the domain 1–3999 instead of a precondition that would discard almost everything. The boundary (0, 4000) gets explicit examples: random generation is not a good way to probe known edges.

**Haskell**

```haskell
import Data.List (isPrefixOf)
import Test.QuickCheck

replace :: String -> String -> String -> String
replace from to = go
  where
    go [] = []
    go s@(c : cs)
      | from `isPrefixOf` s = to <> go (drop (length from) s)
      | otherwise = c : go cs

tally :: Int -> String
tally n = foldl (\s (a, b) -> replace a b s) (replicate n 'I')
  [ ("IIIII", "V"), ("VV", "X"), ("XXXXX", "L"), ("LL", "C"), ("CCCCC", "D"), ("DD", "M")
  , ("IIII", "IV"), ("VIV", "IX"), ("XXXX", "XL"), ("LXL", "XC"), ("CCCC", "CD"), ("DCD", "CM") ]

biQuinary :: Int -> String
biQuinary n = digit 1000 ("M", "?", "?") <> digit 100 ("C", "D", "M") <> digit 10 ("X", "L", "C") <> digit 1 ("I", "V", "X")
  where
    digit place (u, f, t) = case n `mod` (10 * place) `div` place of
      0 -> ""
      4 -> u <> f
      9 -> u <> t
      d | d >= 5 -> f <> concat (replicate (d - 5) u)
        | otherwise -> concat (replicate d u)

decode :: String -> Int
decode s = length (foldl (\acc (a, b) -> replace a b acc) s
  [ ("CM", "DCD"), ("CD", "CCCC"), ("XC", "LXL"), ("XL", "XXXX"), ("IX", "VIV"), ("IV", "IIII")
  , ("M", "DD"), ("D", "CCCCC"), ("C", "LL"), ("L", "XXXXX"), ("X", "VV"), ("V", "IIIII") ])

arabic :: Gen Int
arabic = chooseInt (1, 3999) -- a generator for the domain, not a filter

main :: IO ()
main = do
  quickCheck (forAll arabic (\n -> tally n == biQuinary n)) -- oracle
  quickCheck (forAll arabic (\n -> decode (tally n) == n)) -- round trip
  print (tally 3999, biQuinary 3999) -- boundary examples, checked by eye or by assertion
```

**TypeScript**

```typescript
import fc from "fast-check";

const rules = (pairs: ReadonlyArray<readonly [string, string]>) => (s: string) =>
  pairs.reduce((acc, [a, b]) => acc.replaceAll(a, b), s);

const tally = (n: number) =>
  rules([
    ["IIIII", "V"], ["VV", "X"], ["XXXXX", "L"], ["LL", "C"], ["CCCCC", "D"], ["DD", "M"],
    ["IIII", "IV"], ["VIV", "IX"], ["XXXX", "XL"], ["LXL", "XC"], ["CCCC", "CD"], ["DCD", "CM"],
  ])("I".repeat(n));

const biQuinary = (n: number) => {
  const digit = (place: number, [u, f, t]: readonly [string, string, string]) => {
    const d = Math.floor((n % (10 * place)) / place);
    return d === 4 ? u + f : d === 9 ? u + t : d >= 5 ? f + u.repeat(d - 5) : u.repeat(d);
  };
  return digit(1000, ["M", "?", "?"]) + digit(100, ["C", "D", "M"]) + digit(10, ["X", "L", "C"]) + digit(1, ["I", "V", "X"]);
};

const decode = (s: string) =>
  rules([
    ["CM", "DCD"], ["CD", "CCCC"], ["XC", "LXL"], ["XL", "XXXX"], ["IX", "VIV"], ["IV", "IIII"],
    ["M", "DD"], ["D", "CCCCC"], ["C", "LL"], ["L", "XXXXX"], ["X", "VV"], ["V", "IIIII"],
  ])(s).length;

const arabic = fc.integer({ min: 1, max: 3999 }); // a generator for the domain, not a filter

fc.assert(fc.property(arabic, (n) => tally(n) === biQuinary(n))); // oracle
fc.assert(fc.property(arabic, (n) => decode(tally(n)) === n)); // round trip
export const boundary = [tally(3999), biQuinary(3999)]; // "MMMCMXCIX" twice
```

**C++**

```cpp
#include <rapidcheck.h>

#include <array>
#include <string>
#include <utility>

std::string replaceAll(std::string s, const std::string& from, const std::string& to) {
  for (std::size_t pos = 0; (pos = s.find(from, pos)) != std::string::npos; pos += to.size())
    s.replace(pos, from.size(), to);
  return s;
}

template <std::size_t N>
std::string rewrite(std::string s, const std::array<std::pair<const char*, const char*>, N>& rules) {
  for (const auto& [a, b] : rules) s = replaceAll(std::move(s), a, b);
  return s;
}

std::string tally(int n) {
  static const std::array<std::pair<const char*, const char*>, 12> rules{{
      {"IIIII", "V"}, {"VV", "X"}, {"XXXXX", "L"}, {"LL", "C"}, {"CCCCC", "D"}, {"DD", "M"},
      {"IIII", "IV"}, {"VIV", "IX"}, {"XXXX", "XL"}, {"LXL", "XC"}, {"CCCC", "CD"}, {"DCD", "CM"}}};
  return rewrite(std::string(n, 'I'), rules);
}

std::string biQuinary(int n) {
  auto digit = [n](int place, const char* u, const char* f, const char* t) {
    int d = n % (10 * place) / place;
    std::string U = u, F = f, T = t, out;
    if (d == 4) return U + F;
    if (d == 9) return U + T;
    if (d >= 5) { out = F; d -= 5; }
    for (int i = 0; i < d; ++i) out += U;
    return out;
  };
  return digit(1000, "M", "?", "?") + digit(100, "C", "D", "M") + digit(10, "X", "L", "C") + digit(1, "I", "V", "X");
}

int decode(const std::string& s) {
  static const std::array<std::pair<const char*, const char*>, 12> rules{{
      {"CM", "DCD"}, {"CD", "CCCC"}, {"XC", "LXL"}, {"XL", "XXXX"}, {"IX", "VIV"}, {"IV", "IIII"},
      {"M", "DD"}, {"D", "CCCCC"}, {"C", "LL"}, {"L", "XXXXX"}, {"X", "VV"}, {"V", "IIIII"}}};
  return static_cast<int>(rewrite(s, rules).size());
}

int main() {
  auto arabic = [] { return *rc::gen::inRange(1, 4000); };  // [1, 4000): the domain, not a filter
  rc::check("tally == biquinary", [&] { int n = arabic(); RC_ASSERT(tally(n) == biQuinary(n)); });
  rc::check("decode . encode == id", [&] { int n = arabic(); RC_ASSERT(decode(tally(n)) == n); });
}
```

## 3. Invariants and idempotence: removing duplicates

"Some things never change" (membership) and "the more things change, the more they stay the same" (applying twice = once), plus the defining property (no duplicates in the output).

**Haskell**

```haskell
import Data.List (nub)
import Test.QuickCheck

distinct :: [Int] -> [Int]
distinct = nub

prop_idempotent :: [Int] -> Bool
prop_idempotent xs = distinct (distinct xs) == distinct xs

prop_sameMembers :: [Int] -> Bool
prop_sameMembers xs = all (`elem` distinct xs) xs && all (`elem` xs) (distinct xs)

prop_noDuplicates :: [Int] -> Bool
prop_noDuplicates xs = let ys = distinct xs in length ys == length (nub ys)

main :: IO ()
main = mapM_ quickCheck [prop_idempotent, prop_sameMembers, prop_noDuplicates]
```

**TypeScript**

```typescript
import fc from "fast-check";

const distinct = (xs: readonly number[]): number[] => [...new Set(xs)];
const ints = fc.array(fc.integer());

fc.assert(fc.property(ints, (xs) => JSON.stringify(distinct(distinct(xs))) === JSON.stringify(distinct(xs))));
fc.assert(fc.property(ints, (xs) => xs.every((x) => distinct(xs).includes(x)) && distinct(xs).every((y) => xs.includes(y))));
fc.assert(fc.property(ints, (xs) => new Set(distinct(xs)).size === distinct(xs).length));
```

**C++**

```cpp
#include <rapidcheck.h>

#include <algorithm>
#include <set>
#include <vector>

std::vector<int> distinct(const std::vector<int>& xs) {
  std::vector<int> out;
  std::set<int> seen;
  for (int x : xs) if (seen.insert(x).second) out.push_back(x);
  return out;
}

bool contains(const std::vector<int>& xs, int x) { return std::find(xs.begin(), xs.end(), x) != xs.end(); }

int main() {
  rc::check("idempotent", [](const std::vector<int>& xs) { RC_ASSERT(distinct(distinct(xs)) == distinct(xs)); });
  rc::check("same members", [](const std::vector<int>& xs) {
    auto ys = distinct(xs);
    for (int x : xs) RC_ASSERT(contains(ys, x));
    for (int y : ys) RC_ASSERT(contains(xs, y));
  });
  rc::check("no duplicates", [](const std::vector<int>& xs) {
    auto ys = distinct(xs);
    RC_ASSERT(std::set<int>(ys.begin(), ys.end()).size() == ys.size());
  });
}
```

## 4. Hard to prove, easy to verify: splitting a string

Writing a second tokenizer to check the first duplicates the logic. Checking that the tokens reassemble into the input does not. Random strings rarely contain separators, so build the input *from* random tokens joined by the separator.

**Haskell**

```haskell
import Data.List (intercalate)
import Test.QuickCheck

splitOn :: Char -> String -> [String]
splitOn c s = case break (== c) s of
  (chunk, []) -> [chunk]
  (chunk, _ : rest) -> chunk : splitOn c rest

prop_splitThenJoin :: [String] -> Bool
prop_splitThenJoin tokens =
  let input = intercalate "," tokens
   in intercalate "," (splitOn ',' input) == input

main :: IO ()
main = quickCheck prop_splitThenJoin
```

**TypeScript**

```typescript
import fc from "fast-check";

const splitOn = (sep: string, s: string): string[] => s.split(sep);

fc.assert(
  fc.property(fc.array(fc.string()), (tokens) => {
    const input = tokens.join(",");
    return splitOn(",", input).join(",") === input;
  }),
);
```

**C++**

```cpp
#include <rapidcheck.h>

#include <string>
#include <vector>

std::vector<std::string> splitOn(char sep, const std::string& s) {
  std::vector<std::string> out{""};
  for (char c : s) {
    if (c == sep) out.emplace_back();
    else out.back() += c;
  }
  return out;
}

std::string join(char sep, const std::vector<std::string>& xs) {
  std::string out;
  for (std::size_t i = 0; i < xs.size(); ++i) out += (i ? std::string(1, sep) : "") + xs[i];
  return out;
}

int main() {
  rc::check("split then join", [](const std::vector<std::string>& tokens) {
    std::string input = join(',', tokens);
    RC_ASSERT(join(',', splitOn(',', input)) == input);
  });
}
```

## 5. The oracle, scaled up: model-based testing of a queue

Generate random *sequences of operations*, run them against the implementation and against a trivially correct model, and compare every observation. This is how stateful systems (caches, stores, protocols) are tested; the model is the oracle.

**Haskell**

```haskell
import Test.QuickCheck

-- Implementation: an amortized O(1) functional queue.
data Queue a = Queue [a] [a]

emptyQ :: Queue a
emptyQ = Queue [] []

push :: a -> Queue a -> Queue a
push x (Queue f b) = Queue f (x : b)

pop :: Queue a -> Maybe (a, Queue a)
pop (Queue [] []) = Nothing
pop (Queue [] b) = pop (Queue (reverse b) [])
pop (Queue (x : f) b) = Just (x, Queue f b)

data Cmd = Push Int | Pop deriving (Show)

instance Arbitrary Cmd where
  arbitrary = frequency [(3, Push <$> arbitrary), (2, pure Pop)]

runQueue :: [Cmd] -> [Maybe Int]
runQueue = go emptyQ
  where
    go _ [] = []
    go q (Push x : cs) = go (push x q) cs
    go q (Pop : cs) = case pop q of
      Nothing -> Nothing : go q cs
      Just (x, q') -> Just x : go q' cs

runModel :: [Cmd] -> [Maybe Int] -- the model: a plain list
runModel = go []
  where
    go _ [] = []
    go xs (Push x : cs) = go (xs ++ [x]) cs
    go [] (Pop : cs) = Nothing : go [] cs
    go (x : xs) (Pop : cs) = Just x : go xs cs

main :: IO ()
main = quickCheck (\cmds -> runQueue cmds == runModel cmds)
```

**TypeScript**

```typescript
import fc from "fast-check";

class Queue<A> {
  private constructor(private readonly front: readonly A[], private readonly back: readonly A[]) {}
  static empty<A>(): Queue<A> { return new Queue<A>([], []); }
  push(x: A): Queue<A> { return new Queue(this.front, [x, ...this.back]); }
  pop(): [A, Queue<A>] | undefined {
    if (this.front.length === 0 && this.back.length === 0) return undefined;
    if (this.front.length === 0) return new Queue([...this.back].reverse(), []).pop();
    const [x, ...rest] = this.front;
    return [x as A, new Queue(rest, this.back)];
  }
}

type Cmd = { tag: "push"; value: number } | { tag: "pop" };
const cmd: fc.Arbitrary<Cmd> = fc.oneof(
  fc.record({ tag: fc.constant("push" as const), value: fc.integer() }),
  fc.constant({ tag: "pop" as const }),
);

const runQueue = (cmds: readonly Cmd[]) => {
  let q = Queue.empty<number>();
  const out: Array<number | undefined> = [];
  for (const c of cmds) {
    if (c.tag === "push") { q = q.push(c.value); continue; }
    const r = q.pop();
    out.push(r?.[0]);
    if (r) q = r[1];
  }
  return out;
};

const runModel = (cmds: readonly Cmd[]) => {
  const xs: number[] = [];
  const out: Array<number | undefined> = [];
  for (const c of cmds) c.tag === "push" ? xs.push(c.value) : out.push(xs.shift());
  return out;
};

fc.assert(fc.property(fc.array(cmd), (cmds) => JSON.stringify(runQueue(cmds)) === JSON.stringify(runModel(cmds))));
```

fast-check also offers `fc.commands` / `fc.modelRun` for richer model-based tests with shrinking of command sequences; RapidCheck offers `rc::state`; Hedgehog has state-machine testing.

**C++**

```cpp
#include <rapidcheck.h>

#include <algorithm>
#include <deque>
#include <optional>
#include <utility>
#include <vector>

class Queue {  // implementation under test: two stacks
public:
  void push(int x) { back_.push_back(x); }
  std::optional<int> pop() {
    if (front_.empty()) {
      std::reverse(back_.begin(), back_.end());
      std::swap(front_, back_);
    }
    if (front_.empty()) return std::nullopt;
    int x = front_.back();
    front_.pop_back();
    return x;
  }
private:
  std::vector<int> front_, back_;  // front_ is stored reversed
};

int main() {
  // A command is (isPush, value); the model is std::deque.
  rc::check("queue matches model", [](const std::vector<std::pair<bool, int>>& cmds) {
    Queue q;
    std::deque<int> model;
    for (const auto& [isPush, value] : cmds) {
      if (isPush) { q.push(value); model.push_back(value); continue; }
      std::optional<int> expected;
      if (!model.empty()) { expected = model.front(); model.pop_front(); }
      RC_ASSERT(q.pop() == expected);
    }
  });
}
```

## 6. Generated functions: one property for `map` replaces many

Testing `times` and `add` along two paths each duplicates arithmetic in the tests; noticing they are both "transform the amount" leads to a `map` operation and one property quantified over *all* functions — which the frameworks can generate.

**Haskell**

```haskell
import Test.QuickCheck

newtype Dollar = Dollar {amount :: Int} deriving (Eq, Show)

mapDollar :: (Int -> Int) -> Dollar -> Dollar
mapDollar f (Dollar a) = Dollar (f a)

times, add :: Int -> Dollar -> Dollar
times k = mapDollar (* k)
add k = mapDollar (+ k)

-- "Create then map" equals "map then create", for every function f.
prop_mapCommutes :: Int -> Fun Int Int -> Bool
prop_mapCommutes start (Fn f) = mapDollar f (Dollar start) == Dollar (f start)

main :: IO ()
main = quickCheck prop_mapCommutes -- failing cases print the generated function as a table
```

**TypeScript**

```typescript
import fc from "fast-check";

type Dollar = { readonly amount: number };
const create = (amount: number): Dollar => ({ amount });
const map = (f: (a: number) => number, d: Dollar): Dollar => create(f(d.amount));
export const times = (k: number, d: Dollar) => map((a) => a * k, d);
export const add = (k: number, d: Dollar) => map((a) => a + k, d);

fc.assert(
  fc.property(fc.integer(), fc.func(fc.integer()), (start, f) => map(f, create(start)).amount === create(f(start)).amount),
);
```

**C++** (RapidCheck does not generate `std::function`s, so generate a finite table and a default)

```cpp
#include <rapidcheck.h>

#include <functional>
#include <map>

struct Dollar {
  int amount;
  bool operator==(const Dollar&) const = default;
};

Dollar mapDollar(const std::function<int(int)>& f, Dollar d) { return Dollar{f(d.amount)}; }

int main() {
  rc::check("create then map == map then create",
            [](int start, const std::map<int, int>& table, int fallback) {
              std::function<int(int)> f = [&](int x) {
                auto it = table.find(x);
                return it == table.end() ? fallback : it->second;
              };
              RC_ASSERT(mapDollar(f, Dollar{start}) == Dollar{f(start)});
            });
}
```
