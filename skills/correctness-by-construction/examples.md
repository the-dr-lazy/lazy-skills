# Correctness by construction — worked examples

Each example is given in Haskell, TypeScript, and C++. Each block is self-contained.

## 1. A typed expression language whose evaluator cannot fail

An untyped AST admits `Add (BoolLit True) (IntLit 1)`, so its evaluator needs error cases. Indexing the AST by the type of value it denotes makes ill-typed terms unconstructable, and evaluation total.

**Haskell** (GADTs)

```haskell
{-# LANGUAGE GADTs #-}
{-# LANGUAGE KindSignatures #-}
import Data.Kind (Type)

data Expr :: Type -> Type where
  IntLit :: Int -> Expr Int
  BoolLit :: Bool -> Expr Bool
  Add :: Expr Int -> Expr Int -> Expr Int
  Less :: Expr Int -> Expr Int -> Expr Bool
  If :: Expr Bool -> Expr a -> Expr a -> Expr a

eval :: Expr a -> a -- no Maybe, no error: ill-typed terms do not exist
eval (IntLit n) = n
eval (BoolLit b) = b
eval (Add x y) = eval x + eval y
eval (Less x y) = eval x < eval y
eval (If c t e) = if eval c then eval t else eval e

example :: Expr Int
example = If (Less (IntLit 1) (IntLit 2)) (Add (IntLit 40) (IntLit 2)) (IntLit 0)

-- rejected: Add (BoolLit True) (IntLit 1)
```

**TypeScript** (typed "final" encoding: a term *is* its interpretations)

```typescript
type Expr<T> = { readonly eval: () => T; readonly show: () => string };

const intLit = (n: number): Expr<number> => ({ eval: () => n, show: () => String(n) });
const boolLit = (b: boolean): Expr<boolean> => ({ eval: () => b, show: () => String(b) });
const add = (x: Expr<number>, y: Expr<number>): Expr<number> => ({
  eval: () => x.eval() + y.eval(),
  show: () => `(${x.show()} + ${y.show()})`,
});
const less = (x: Expr<number>, y: Expr<number>): Expr<boolean> => ({
  eval: () => x.eval() < y.eval(),
  show: () => `(${x.show()} < ${y.show()})`,
});
const ifE = <T,>(c: Expr<boolean>, t: Expr<T>, e: Expr<T>): Expr<T> => ({
  eval: () => (c.eval() ? t.eval() : e.eval()),
  show: () => `(if ${c.show()} then ${t.show()} else ${e.show()})`,
});

export const example = ifE(less(intLit(1), intLit(2)), add(intLit(40), intLit(2)), intLit(0));
export const answer: number = example.eval();
// add(boolLit(true), intLit(1)); // error: Expr<boolean> is not Expr<number>
export { boolLit };
```

**C++** (the type of each node is a template parameter)

```cpp
#include <functional>
#include <iostream>

template <typename T>
struct Expr {
  std::function<T()> eval;
};

Expr<int> intLit(int n) { return {[n] { return n; }}; }
Expr<bool> boolLit(bool b) { return {[b] { return b; }}; }
Expr<int> add(Expr<int> x, Expr<int> y) { return {[=] { return x.eval() + y.eval(); }}; }
Expr<bool> less(Expr<int> x, Expr<int> y) { return {[=] { return x.eval() < y.eval(); }}; }

template <typename T>
Expr<T> ifE(Expr<bool> c, Expr<T> t, Expr<T> e) {
  return {[=] { return c.eval() ? t.eval() : e.eval(); }};
}

int main() {
  auto example = ifE(less(intLit(1), intLit(2)), add(intLit(40), intLit(2)), intLit(0));
  std::cout << example.eval() << '\n';  // 42
  // add(boolLit(true), intLit(1));      // error: Expr<bool> is not Expr<int>
}
```

## 2. Constructive versus checked: one invariant, two designs

The invariant: *a batch contains at least one job, and every job has a positive priority.* The checked design validates a plain structure and must be trusted everywhere; the constructive design cannot express a violation of the first half, and confines the second half to one smart constructor.

**Haskell**

```haskell
import Data.List.NonEmpty (NonEmpty (..))

-- Checked: every consumer must remember that validate was called.
data BatchChecked = BatchChecked {jobs :: [(String, Int)]}

validate :: BatchChecked -> Bool
validate (BatchChecked js) = not (null js) && all ((> 0) . snd) js

-- Constructive for "non-empty", extrinsic (one smart constructor) for "positive".
newtype Priority = Priority Int

mkPriority :: Int -> Maybe Priority
mkPriority n = if n > 0 then Just (Priority n) else Nothing

data Job = Job {jobName :: String, jobPriority :: Priority}

newtype Batch = Batch (NonEmpty Job)

firstJob :: Batch -> Job -- total
firstJob (Batch (j :| _)) = j
```

**TypeScript**

```typescript
// Checked
type BatchChecked = { jobs: Array<[string, number]> };
export const validate = (b: BatchChecked): boolean => b.jobs.length > 0 && b.jobs.every(([, p]) => p > 0);

// Constructive for "non-empty", extrinsic for "positive"
export class Priority {
  private constructor(readonly value: number) {}
  static make(n: number): Priority | undefined {
    return Number.isInteger(n) && n > 0 ? new Priority(n) : undefined;
  }
}
type Job = { readonly name: string; readonly priority: Priority };
export type Batch = readonly [Job, ...Job[]];

export const firstJob = (b: Batch): Job => b[0]; // total
```

**C++**

```cpp
#include <optional>
#include <string>
#include <utility>
#include <vector>

// Checked
struct BatchChecked { std::vector<std::pair<std::string, int>> jobs; };
bool validate(const BatchChecked& b) {
  if (b.jobs.empty()) return false;
  for (const auto& [name, p] : b.jobs) if (p <= 0) return false;
  return true;
}

// Constructive for "non-empty", extrinsic for "positive"
class Priority {
public:
  static std::optional<Priority> make(int n) { return n > 0 ? std::optional(Priority(n)) : std::nullopt; }
  int value() const { return n_; }
private:
  explicit Priority(int n) : n_(n) {}
  int n_;
};

struct Job { std::string name; Priority priority; };
struct Batch { Job first; std::vector<Job> rest; };

const Job& firstJob(const Batch& b) { return b.first; }  // total
```
