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

## 3. Ghosts of departed proofs: proofs are programs the compiler checks

After `gdp`'s `Logic.Propositional`. Propositions are types, each inference rule is a function between proofs, and a derived rule is an ordinary function whose type is the theorem. A wrong step does not compile. Classical steps need a licence, so a proof that does not ask for one is constructive. None of this exists at run time; its use is to build the `Proof` arguments that an API like the one in [SKILL.md](SKILL.md) demands.

**Haskell**

```haskell
{-# LANGUAGE PolyKinds #-}
{-# LANGUAGE MultiParamTypeClasses #-}
{-# LANGUAGE RankNTypes #-}


data Proof p = QED -- no data: only the type matters

axiom :: Proof p -- private to the logic module
axiom = QED

-- Propositions are empty types; only their structure matters.
data And p q
data Or p q
data Implies p q
data Not p
data FALSE

-- Natural deduction (after gdp's Logic.Propositional): each rule is a function
-- between proofs, asserted once by the library.
introAnd :: Proof p -> Proof q -> Proof (And p q)
introAnd _ _ = axiom

elimAndL :: Proof (And p q) -> Proof p
elimAndL _ = axiom

elimAndR :: Proof (And p q) -> Proof q
elimAndR _ = axiom

introOrL :: Proof p -> Proof (Or p q)
introOrL _ = axiom

introOrR :: Proof q -> Proof (Or p q)
introOrR _ = axiom

elimOr :: (Proof p -> Proof r) -> (Proof q -> Proof r) -> Proof (Or p q) -> Proof r
elimOr _ _ _ = axiom

introImpl :: (Proof p -> Proof q) -> Proof (Implies p q)
introImpl _ = axiom

modusPonens :: Proof (Implies p q) -> Proof p -> Proof q
modusPonens _ _ = axiom

introNot :: (Proof p -> Proof FALSE) -> Proof (Not p)
introNot _ = axiom

contradicts :: Proof p -> Proof (Not p) -> Proof FALSE
contradicts _ _ = axiom

absurd :: Proof FALSE -> Proof p
absurd _ = axiom

-- Classical steps need an explicit licence; a proof without one is constructive.
class Classical

classically :: (Classical => Proof p) -> Proof p
classically _ = axiom

lem :: Classical => Proof (Or p (Not p))
lem = axiom

-- Client code: derived rules are ordinary functions, and a wrong step is a type error.
and2or :: Proof (And p q) -> Proof (Or p q)
and2or pq = introOrL (elimAndL pq)
-- and2or pq = introOrR (elimAndL pq) -- rejected: Proof (Or p p) is not Proof (Or p q)

modusTollens :: Proof (Implies p q) -> Proof (Not q) -> Proof (Not p)
modusTollens impl notQ = introNot (\p -> contradicts (modusPonens impl p) notQ)

deMorgan :: Proof (And (Not p) (Not q)) -> Proof (Not (Or p q))
deMorgan nn = introNot (elimOr (\p -> contradicts p (elimAndL nn)) (\q -> contradicts q (elimAndR nn)))

contradiction :: Classical => (Proof (Not p) -> Proof FALSE) -> Proof p
contradiction impl = elimOr id (absurd . impl) lem

elimNotNot :: Classical => Proof (Not (Not p)) -> Proof p
elimNotNot nnp = contradiction (\np -> contradicts np nnp)

-- Without the constraint in its own type, a caller discharges the licence visibly.
doubleNegation :: Proof (Not (Not p)) -> Proof p
doubleNegation nnp = classically (elimNotNot nnp)
```

**TypeScript** (each brand is invariant; with covariant brands `introNot<never>((p) => p)` would prove "not *X*" for every *X*)

```typescript
// A proof carries no data; its brand exists only in the type. (P) => P makes the
// brand invariant, so Proof<never> cannot stand in for every proposition.
declare const proves: unique symbol;
export type Proof<P> = { readonly [proves]: (p: P) => P };
const QED = {};
const axiom = <P,>(): Proof<P> => QED as Proof<P>; // not exported: only the rules below use it

// Propositions: phantom types, each with its own brand so they never unify structurally.
declare const and: unique symbol;
declare const or: unique symbol;
declare const implies: unique symbol;
declare const not: unique symbol;
declare const falsity: unique symbol;
export type And<P, Q> = { readonly [and]: (x: [P, Q]) => [P, Q] };
export type Or<P, Q> = { readonly [or]: (x: [P, Q]) => [P, Q] };
export type Implies<P, Q> = { readonly [implies]: (x: [P, Q]) => [P, Q] };
export type Not<P> = { readonly [not]: (x: P) => P };
export type FALSE = { readonly [falsity]: true };

// Natural deduction (after gdp's Logic.Propositional).
export const introAnd = <P, Q>(_p: Proof<P>, _q: Proof<Q>): Proof<And<P, Q>> => axiom();
export const elimAndL = <P, Q>(_pq: Proof<And<P, Q>>): Proof<P> => axiom();
export const elimAndR = <P, Q>(_pq: Proof<And<P, Q>>): Proof<Q> => axiom();
export const introOrL = <P, Q>(_p: Proof<P>): Proof<Or<P, Q>> => axiom();
export const introOrR = <P, Q>(_q: Proof<Q>): Proof<Or<P, Q>> => axiom();
export const elimOr = <P, Q, R>(_l: (p: Proof<P>) => Proof<R>, _r: (q: Proof<Q>) => Proof<R>, _pq: Proof<Or<P, Q>>): Proof<R> =>
  axiom();
export const introImpl = <P, Q>(_f: (p: Proof<P>) => Proof<Q>): Proof<Implies<P, Q>> => axiom();
export const modusPonens = <P, Q>(_i: Proof<Implies<P, Q>>, _p: Proof<P>): Proof<Q> => axiom();
export const introNot = <P,>(_f: (p: Proof<P>) => Proof<FALSE>): Proof<Not<P>> => axiom();
export const contradicts = <P,>(_p: Proof<P>, _np: Proof<Not<P>>): Proof<FALSE> => axiom();
export const absurd = <P,>(_f: Proof<FALSE>): Proof<P> => axiom();

// Classical steps need a licence token that only `classically` hands out.
declare const classicalTag: unique symbol;
export type Classical = { readonly [classicalTag]: true };
export const classically = <P,>(k: (c: Classical) => Proof<P>): Proof<P> => k({} as Classical);
export const lem = <P,>(_c: Classical): Proof<Or<P, Not<P>>> => axiom();

// Client code: derived rules are generic functions; a wrong step is a type error.
export const and2or = <P, Q>(pq: Proof<And<P, Q>>): Proof<Or<P, Q>> => introOrL(elimAndL(pq));
// introOrR(elimAndL(pq)) is rejected: Proof<Or<P, P>> is not Proof<Or<P, Q>>

export const modusTollens = <P, Q>(impl: Proof<Implies<P, Q>>, notQ: Proof<Not<Q>>): Proof<Not<P>> =>
  introNot((p: Proof<P>) => contradicts(modusPonens(impl, p), notQ));

export const deMorgan = <P, Q>(nn: Proof<And<Not<P>, Not<Q>>>): Proof<Not<Or<P, Q>>> =>
  introNot(
    (pq: Proof<Or<P, Q>>) =>
      elimOr((p: Proof<P>) => contradicts(p, elimAndL(nn)), (q: Proof<Q>) => contradicts(q, elimAndR(nn)), pq),
  );

export const contradiction = <P,>(c: Classical, impl: (np: Proof<Not<P>>) => Proof<FALSE>): Proof<P> =>
  elimOr((p: Proof<P>) => p, (np: Proof<Not<P>>) => absurd<P>(impl(np)), lem<P>(c));

export const elimNotNot = <P,>(nnp: Proof<Not<Not<P>>>): Proof<P> =>
  classically((c) => contradiction<P>(c, (np) => contradicts(np, nnp)));
```

**C++** (templates are checked when instantiated, so each derived rule is instantiated once with unrelated tag types)

```cpp
#include <type_traits>

// A proof carries no data (an empty class); only the rules in Logic can make one.
struct Logic;
template <typename P>
class Proof {
  Proof() = default;
  friend struct Logic;
};

// Propositions: empty tag templates.
template <typename P, typename Q> struct And {};
template <typename P, typename Q> struct Or {};
template <typename P, typename Q> struct Implies {};
template <typename P> struct Not {};
struct FALSE {};

// A licence for classical steps; only Logic::classically hands one out.
class Classical {
  Classical() = default;
  friend struct Logic;
};

// Natural deduction (after gdp's Logic.Propositional). C++ cannot infer a
// proposition from the expected result, so callers name it: introOrL<P, Q>.
struct Logic {
  template <typename P, typename Q> static Proof<And<P, Q>> introAnd(Proof<P>, Proof<Q>) { return {}; }
  template <typename P, typename Q> static Proof<P> elimAndL(Proof<And<P, Q>>) { return {}; }
  template <typename P, typename Q> static Proof<Q> elimAndR(Proof<And<P, Q>>) { return {}; }
  template <typename P, typename Q> static Proof<Or<P, Q>> introOrL(Proof<P>) { return {}; }
  template <typename P, typename Q> static Proof<Or<P, Q>> introOrR(Proof<Q>) { return {}; }
  template <typename R, typename P, typename Q, typename L, typename F>
    requires std::is_invocable_r_v<Proof<R>, L, Proof<P>> && std::is_invocable_r_v<Proof<R>, F, Proof<Q>>
  static Proof<R> elimOr(L, F, Proof<Or<P, Q>>) { return {}; }
  template <typename P, typename Q> static Proof<Q> modusPonens(Proof<Implies<P, Q>>, Proof<P>) { return {}; }
  template <typename P, typename F>
    requires std::is_invocable_r_v<Proof<FALSE>, F, Proof<P>>
  static Proof<Not<P>> introNot(F) { return {}; }
  template <typename P> static Proof<FALSE> contradicts(Proof<P>, Proof<Not<P>>) { return {}; }
  template <typename P> static Proof<P> absurd(Proof<FALSE>) { return {}; }
  template <typename F> static auto classically(F k) { return k(Classical{}); }
  template <typename P> static Proof<Or<P, Not<P>>> lem(Classical) { return {}; }
};

// Client code: derived rules are templates built only from the rules above.
template <typename P, typename Q>
Proof<Or<P, Q>> and2or(Proof<And<P, Q>> pq) {
  return Logic::introOrL<P, Q>(Logic::elimAndL(pq));
  // return Logic::introOrR<P, Q>(Logic::elimAndL(pq));  // rejected once instantiated: Proof<P> is not Proof<Q>
}

template <typename P, typename Q>
Proof<Not<P>> modusTollens(Proof<Implies<P, Q>> impl, Proof<Not<Q>> notQ) {
  return Logic::introNot<P>([=](Proof<P> p) { return Logic::contradicts(Logic::modusPonens(impl, p), notQ); });
}

template <typename P, typename F>
Proof<P> contradiction(Classical c, F impl) {  // F: Proof<Not<P>> -> Proof<FALSE>
  return Logic::elimOr<P>([](Proof<P> p) { return p; }, [=](Proof<Not<P>> np) { return Logic::absurd<P>(impl(np)); },
                          Logic::lem<P>(c));
}

template <typename P>
Proof<P> elimNotNot(Proof<Not<Not<P>>> nnp) {  // classical: asks for the licence
  return Logic::classically(
      [=](Classical c) { return contradiction<P>(c, [=](Proof<Not<P>> np) { return Logic::contradicts(np, nnp); }); });
}

// Templates are checked only when instantiated, so check each derived rule
// once with fresh, unrelated propositions: the C++ stand-in for rigid type variables.
struct A {};
struct B {};
template Proof<Or<A, B>> and2or<A, B>(Proof<And<A, B>>);
template Proof<Not<A>> modusTollens<A, B>(Proof<Implies<A, B>>, Proof<Not<B>>);
template Proof<A> elimNotNot<A>(Proof<Not<Not<A>>>);
```

## 4. Ghosts of departed proofs: a checked introduction for list shapes

After `gdp`'s `Theory.Lists`. `classify` is the only run-time check: it inspects a named list and returns evidence of its shape. `safeHead` demands that evidence, and `safeLast` is derived from `safeHead`, `rev`, and a lemma without checking again. `gdp` can also pass such evidence implicitly, as a `Fact (IsCons xs)` constraint brought into scope by its `Cons` and `Nil` pattern synonyms; that needs Haskell's constraint solver, so all three versions here pass it explicitly.

**Haskell**

```haskell
{-# LANGUAGE ConstraintKinds #-}
{-# LANGUAGE FlexibleContexts #-}
{-# LANGUAGE PolyKinds #-}
{-# LANGUAGE RankNTypes #-}
{-# LANGUAGE RoleAnnotations #-}
{-# LANGUAGE TypeOperators #-}
import Data.Coerce (Coercible, coerce)

-- The core from the GDP example in SKILL.md: names, library-minted names, proofs.
newtype Named name a = Named a
type role Named nominal nominal
type a ~~ name = Named name a

name :: a -> (forall name. (a ~~ name) -> t) -> t
name x k = k (coerce x)

the :: (a ~~ name) -> a
the = coerce

data Defn = Defn
type Defining p = (Coercible p Defn, Coercible Defn p)

defn :: Defining f => a -> (a ~~ f)
defn = coerce

data Proof p = QED

axiom :: Proof p
axiom = QED

-- The library (after gdp's Theory.Lists): a predicate, a name, and a checked introduction.
data IsCons xs -- "the list named xs is non-empty"

newtype Reverse xs = Reverse Defn
type role Reverse nominal

-- The one run-time check: inspect the list and hand back evidence.
data ListCase xs = Cons (Proof (IsCons xs)) | Nil

classify :: ([a] ~~ xs) -> ListCase xs
classify xs = case the xs of
  _ : _ -> Cons axiom
  [] -> Nil

-- Demands the evidence, so callers cannot reach the empty case.
safeHead :: Proof (IsCons xs) -> ([a] ~~ xs) -> a
safeHead _ xs = case the xs of
  x : _ -> x
  [] -> error "unreachable: the proof rules out the empty list" -- trusted library code

rev :: ([a] ~~ xs) -> ([a] ~~ Reverse xs)
rev xs = defn (reverse (the xs))

revCons :: Proof (IsCons xs) -> Proof (IsCons (Reverse xs)) -- a lemma the library asserts
revCons _ = axiom

-- Client code: a safe last from safeHead, rev, and the lemma; no new check.
safeLast :: Proof (IsCons xs) -> ([a] ~~ xs) -> a
safeLast p xs = safeHead (revCons p) (rev xs)

describe :: [Int] -> String
describe input = name input $ \xs -> case classify xs of
  Cons p -> "from " ++ show (safeHead p xs) ++ " to " ++ show (safeLast p xs)
  Nil -> "empty"

-- safeHead p (rev xs)            -- rejected: p is about xs, not about Reverse xs
-- name other $ \ys -> safeHead p ys -- rejected: p is about xs, not ys
```

**TypeScript**

```typescript
// The core from the GDP example in SKILL.md: invariant phantom brands, fresh names, proofs.
declare const nameOf: unique symbol;
declare const proves: unique symbol;
type Named<T, N> = T & { readonly [nameOf]: (n: N) => N };
type Proof<P> = { readonly [proves]: (p: P) => P };
const QED = {};
const axiom = <P,>(): Proof<P> => QED as Proof<P>;
const name = <T, R>(x: T, k: <N>(named: Named<T, N>) => R): R => k(x as Named<T, unknown>);

// The library (after gdp's Theory.Lists): a predicate, a name, and a checked introduction.
declare const isConsTag: unique symbol;
declare const reverseTag: unique symbol;
type IsCons<Xs> = { readonly [isConsTag]: (xs: Xs) => Xs }; // "the list named Xs is non-empty"
type Reverse<Xs> = { readonly [reverseTag]: (xs: Xs) => Xs };

// The one run-time check: inspect the list and hand back evidence.
type ListCase<Xs> = { readonly tag: "cons"; readonly proof: Proof<IsCons<Xs>> } | { readonly tag: "nil" };
const classify = <T, Xs>(xs: Named<readonly T[], Xs>): ListCase<Xs> =>
  xs.length > 0 ? { tag: "cons", proof: axiom() } : { tag: "nil" };

// Demands the evidence, so callers cannot reach the empty case.
const safeHead = <T, Xs>(_: Proof<IsCons<Xs>>, xs: Named<readonly T[], Xs>): T => xs[0]!; // trusted: the proof rules out []

const rev = <T, Xs>(xs: Named<readonly T[], Xs>): Named<readonly T[], Reverse<Xs>> =>
  [...xs].reverse() as unknown as Named<readonly T[], Reverse<Xs>>;

const revCons = <Xs,>(_: Proof<IsCons<Xs>>): Proof<IsCons<Reverse<Xs>>> => axiom(); // a lemma the library asserts

// Client code: a safe last from safeHead, rev, and the lemma; no new check.
export const safeLast = <T, Xs>(p: Proof<IsCons<Xs>>, xs: Named<readonly T[], Xs>): T => safeHead(revCons(p), rev(xs));

export const describe = (input: readonly number[]): string =>
  name(input, (xs): string => {
    const c = classify(xs);
    // safeHead(c.proof, rev(xs)) would be rejected: the proof is about xs, not Reverse<xs>
    return c.tag === "cons" ? `from ${safeHead(c.proof, xs)} to ${safeLast(c.proof, xs)}` : "empty";
  });
```

**C++**

```cpp
#include <optional>
#include <string>
#include <utility>
#include <vector>

// The core from the GDP example in SKILL.md: names and proofs that exist only in types.
template <typename T, typename N>
class Named {
public:
  const T& the() const { return value_; }
private:
  explicit Named(T v) : value_(std::move(v)) {}
  T value_;
  template <typename U, typename K> friend auto name(U, K);
  friend typename N::DefinedBy;
};

template <typename T, typename K> struct Fresh { using DefinedBy = Fresh; };

template <typename T, typename K>
auto name(T x, K k) {
  return k(Named<T, Fresh<T, K>>(std::move(x)));
}

struct Lists;
template <typename P>
class Proof {
  Proof() = default;
  friend struct Lists;
};

// The library (after gdp's Theory.Lists): a predicate, a name, and a checked introduction.
template <typename Xs> struct IsCons {};                                // "the list named Xs is non-empty"
template <typename Xs> struct Reverse { using DefinedBy = Lists; };

struct Lists {
  // The one run-time check: inspect the list and hand back evidence.
  template <typename T, typename Xs>
  static std::optional<Proof<IsCons<Xs>>> classify(const Named<std::vector<T>, Xs>& xs) {
    if (xs.the().empty()) return std::nullopt;
    return Proof<IsCons<Xs>>{};
  }

  // Demands the evidence, so callers cannot reach the empty case.
  template <typename T, typename Xs>
  static T head(Proof<IsCons<Xs>>, const Named<std::vector<T>, Xs>& xs) {
    return xs.the().front();  // trusted: the proof rules out the empty vector
  }

  template <typename T, typename Xs>
  static Named<std::vector<T>, Reverse<Xs>> rev(const Named<std::vector<T>, Xs>& xs) {
    return Named<std::vector<T>, Reverse<Xs>>(std::vector<T>(xs.the().rbegin(), xs.the().rend()));
  }

  template <typename Xs>
  static Proof<IsCons<Reverse<Xs>>> revCons(Proof<IsCons<Xs>>) { return {}; }  // a lemma the library asserts
};

// Client code: a safe last from head, rev, and the lemma; no new check.
template <typename T, typename Xs>
T last(Proof<IsCons<Xs>> p, const Named<std::vector<T>, Xs>& xs) {
  return Lists::head(Lists::revCons(p), Lists::rev(xs));
}

std::string describe(std::vector<int> input) {
  return name(std::move(input), [](auto xs) -> std::string {
    auto p = Lists::classify(xs);
    if (!p) return "empty";
    // Lists::head(*p, Lists::rev(xs));  // error: the proof is about xs, not Reverse<xs>
    return "from " + std::to_string(Lists::head(*p, xs)) + " to " + std::to_string(last(*p, xs));
  });
}
```
