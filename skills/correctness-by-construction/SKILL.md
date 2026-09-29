---
name: correctness-by-construction
description: Correctness by construction — make invariants follow from how values are built (constructive types, typestate, ghosts of departed proofs, GADTs, machine-checked proofs) instead of checking them. Covers the gdp library (names, ghost proofs, refinement types, natural deduction, equality, checked introductions) in Haskell, TypeScript, and C++. Use when an invariant is re-checked in many places, when a protocol has an order of operations, when callers must establish a precondition (sorted, non-empty, same comparator), or when an interpreter can fail on ill-formed input.
---

# Correctness by construction

> *Upstream status:* the functional-architecture.org page for this pattern is TODO. This skill is synthesized from the sources listed at the end.

A value is **correct by construction** when the only ways to build it produce valid values, so no code ever has to check it. Alexis King puts it as *types as axioms*: a datatype declaration is a small set of axioms and inference rules, and every value is a derivation from them. Design the rules so that every derivation is valid — "don't try to add post-hoc restrictions to exclude bad values, **make your datatypes correct by construction**."

Contrast with extrinsic guarantees (a wrapper plus a smart constructor): there, correctness depends on trusted code and discipline. With a constructive type, "there is no trusted code … all parts of the program are equally beholden to the datatype-mandated constraints" (`names-are-not-type-safety`).

## A ladder of techniques

Climb only as far as the invariant is worth; each rung costs more.

1. **Constructive algebraic data types.** Sums, products, recursion: `NonEmpty a = a :| [a]`, `EvenList a = [(a, a)]`, one case per state. Available in every language with records and tagged unions (`make-illegal-states-unrepresentable`).
2. **Typestate / phantom types.** Encode *where you are in a protocol* in a type parameter, and give each operation the signature that only accepts the right state (`Conn Open -> …`). Order-of-operations bugs become type errors. Experience reports (Rust, FUNARCH 2026) find it improves faultlessness and testability at the cost of boilerplate and some readability — most worthwhile for code with extensive branching and many invariants.
   A related technique, Noonan's `gdp` (*Ghosts of Departed Proofs*), keeps the value plain and attaches the proof of a property to its type: see [Ghosts of departed proofs](#ghosts-of-departed-proofs-gdp) below.
3. **Indexed types / GADTs.** Let constructors refine the type index: a typed expression tree `Expr Int` cannot contain an ill-typed `Add (BoolLit True) …`, so its evaluator has no error cases ("well-typed programs cannot go wrong"). Length-indexed vectors, well-scoped syntax, and sorted-by-construction search trees (McBride, *How to Keep Your Neighbours in Order*) live here.
4. **Machine-checked specifications.** Dependent types and proof assistants (Agda, Idris, Lean, Rocq/Coq) — the functional-architecture site calls this "make illegal *values* unrepresentable", where functions are values too. See `formal-verification`. Lean's `Fin n`, a number bundled with a proof that it is below `n`, makes `Fin arr.size` always a valid index into `arr`.

**Costs of the upper rungs.** When a function appears in a type, its implementation becomes part of the interface, because the checker compares types by *definitional equality*, which runs the function. The Lean book's example: `plusL` recurses on its first argument, so `plusL 0 k` reduces to `k` and `append : Vect α n → Vect α k → Vect α (n.plusL k)` is a direct recursion. `plusR` returns the same sums but recurses on its second argument, so `plusR 0 k` is *stuck* on the variable `k` and the same `append` no longer type-checks; Lean's own `Nat.add` behaves like `plusR`. Getting unstuck needs an explicit proof of propositional equality. In the book's words, exposing a function's internals in a type means refactoring it "may cause programs that use it to no longer type check", so the usual freedom to change the algorithm and keep the behavior is gone. Climb only as far as the invariant is worth.

## Procedure

1. State the invariant precisely, in one sentence, including *when* it must hold (always? after step X?).
2. Ask which constructors could produce a violation. Can you remove or refine them so none can?
   - an invariant about shape → rung 1;
   - about the order of operations → rung 2;
   - about a precondition that callers must establish (sorted, non-empty, sorted by the same comparator) → ghosts of departed proofs;
   - about the relationship between a value and its type / its contents → rung 3;
   - about arbitrary computable properties → rung 4, or accept an extrinsic guard (`smart-constructor`, `belt-and-suspenders`).
3. Rewrite consumers against the new type and delete their checks, `error "impossible"` branches, and defensive `default` cases.
4. Keep conversions to the standard representations nearby (to lists, to plain records) so the precise type does not wall you off from the ecosystem.

Done when: the invariant can be violated only by changing the type definition itself, and no consumer contains a runtime check for it.

## Example: typestate for a connection protocol

`send` exists only for open connections; `close` consumes an open connection and returns a closed one. Sending on a closed connection does not compile.

**Haskell**

```haskell
{-# LANGUAGE DataKinds #-}
{-# LANGUAGE KindSignatures #-}
module Conn (State (..), Conn, connect, send, close, sentCount) where

data State = Open | Closed

-- The phantom index records the protocol state; the constructor is not exported.
newtype Conn (s :: State) = Conn [String]

connect :: String -> Conn 'Open
connect _host = Conn []

send :: String -> Conn 'Open -> Conn 'Open
send msg (Conn sent) = Conn (msg : sent)

close :: Conn 'Open -> Conn 'Closed
close (Conn sent) = Conn sent

sentCount :: Conn s -> Int -- valid in every state
sentCount (Conn sent) = length sent

-- send "late" (close (connect "db")) -- rejected: Conn 'Closed is not Conn 'Open
```

**TypeScript**

```typescript
declare const state: unique symbol;
type Open = "open";
type Closed = "closed";

export class Conn<S extends Open | Closed> {
  declare readonly [state]: S; // phantom: exists only in the type
  private constructor(readonly sent: readonly string[]) {}

  static connect(_host: string): Conn<Open> {
    return new Conn<Open>([]);
  }
  static send(msg: string, c: Conn<Open>): Conn<Open> {
    return new Conn<Open>([...c.sent, msg]);
  }
  static close(c: Conn<Open>): Conn<Closed> {
    return new Conn<Closed>(c.sent);
  }
}

const closed = Conn.close(Conn.send("hello", Conn.connect("db")));
// Conn.send("late", closed); // error: Conn<"closed"> is not assignable to Conn<"open">
export { closed };
```

**C++**

```cpp
#include <string>
#include <utility>
#include <vector>

struct Open {};
struct Closed {};

template <typename State>
class Conn {
public:
  const std::vector<std::string>& sent() const { return sent_; }
private:
  explicit Conn(std::vector<std::string> s) : sent_(std::move(s)) {}
  std::vector<std::string> sent_;

  friend Conn<Open> connect(const std::string&);
  friend Conn<Open> send(std::string, Conn<Open>);
  friend Conn<Closed> close(Conn<Open>);
};

Conn<Open> connect(const std::string&) { return Conn<Open>({}); }

Conn<Open> send(std::string msg, Conn<Open> c) {
  c.sent_.push_back(std::move(msg));
  return c;
}

Conn<Closed> close(Conn<Open> c) { return Conn<Closed>(std::move(c.sent_)); }

void demo() {
  auto closed = close(send("hello", connect("db")));
  // send("late", closed);  // error: no conversion from Conn<Closed> to Conn<Open>
  (void)closed;
}
```

In languages with affine/linear types (Rust ownership, Haskell `LinearTypes`), the old state can also be *consumed*, so a stale `Conn Open` cannot be reused after `close`. In the three languages above, the stale value still exists; the typestate prevents wrong *operations*, not *aliasing*.

A typed expression language whose evaluator cannot fail (GADTs in Haskell, typed builders in TypeScript and C++) and constructive-vs-checked comparisons: [examples.md](examples.md).

## Ghosts of departed proofs (GDP)

Noonan's `gdp` library puts the proof of a precondition into the *type* of a value and nowhere else. A check runs once and yields a phantom proof; each function that relies on the property asks for that proof in its signature; the proof has no run-time representation, so nothing is carried or re-checked. The library author asserts the base facts, and clients combine them with logic that the type checker verifies. The pieces, by `gdp` module:

- **Names** (`Theory.Named`). `a ~~ name` is an `a` with a phantom name and the same representation. `name x (\n -> …)` gives `x` a fresh name through a rank-2 continuation, so the name differs from every other and cannot escape; a proof can then be about *that* value (`SortedBy comp xs`: the list named `xs` is sorted by the comparator named `comp`). A library mints its own names and predicates as newtypes over `Defn` with unexported constructors: `defn` attaches such a name and needs `Defining p`, which holds only in the defining module. Give their phantom parameters `nominal` roles, or clients can `coerce` one name into another and forge proofs the library never blessed.
- **Proofs** (`Logic.Proof`). `Proof p` has a single constant constructor, so only its type carries information; as an argument it is an assumption. `axiom` asserts a fact (library authors only); `sorry` stubs a proof in progress and triggers a compiler warning.
- **Ghost proofs and refinement types** (`Data.Refined`). `x ... proof :: a ::: p` attaches a proof, `exorcise` drops it, `$:` maps the value and keeps the proof, `...>` applies an implication to it. `a ?p` is a refinement type, an `a` satisfying `p` with the name forgotten; only `p`'s defining module can `assert` it. `rename` gives a refined value a fresh name to reason about, `unname` forgets it again, and `f ...? lemma` turns a function on named values plus a lemma into a function between refinement types.
- **Logic** (`Logic.Propositional`, `Logic.Classes`, `Logic.NegClasses`). Propositions are types (`&&`, `||`, `-->`, `Not`, `ForAll`, `Exists`, `TRUE`, `FALSE`) and natural-deduction rules are functions between proofs (`introAnd`, `elimOr`, `modusPonens`, `introNot`, `absurd`, `introUniv`, `elimEx`, …). A derived rule is an ordinary function; a wrong step is a type error. Classical rules (`lem`, `contradiction`, `elimNotNot`) need a `Classical` constraint that only `classically` discharges, so a proof without it is constructive. Empty instances declare algebraic properties: `Reflexive`, `Symmetric`, `Transitive`, `Commutative`, `Associative`, `Idempotent`, `DistributiveL`/`R`, `Injective`, `Irreflexive`, `Antisymmetric`.
- **Equality** (`Theory.Equality`, `Data.Arguments`). `x == y` is a proposition: `==.` chains equalities, `apply` and `substitute` rewrite at an argument position (`Arg`, `LHS`, `RHS`), `same` compares two named values at run time and returns `Maybe (Proof (x == y))`, and `reflectEq` turns such a proof into GHC's `x :~: y`.
- **Checked introductions and implicit facts** (`Theory.Lists`, `Logic.Implicit`). `classify` inspects a named list once and returns its shape with evidence (`IsCons xs` with named `Head xs` and `Tail xs`, or `IsNil xs`), after which `head` cannot fail. A `Fact p` constraint passes evidence implicitly (`known`, `note`, `on`, and the `Cons`/`Nil` pattern synonyms), at the cost of a dictionary that may not be optimized away. The module also states axioms such as `headOfCons` and an induction principle.

**Where the trust sits.** Everything bottoms out in `axiom`, `assert`, and `defn`: GDP checks that clients *use* the library's facts correctly, not that the facts are true. Keep those calls in the small module that defines the names and predicates, beside the code that makes each fact true, and review them like unsafe code. `the` forgets a name or proof when a plain value is needed.

**Procedure.** (1) Name each precondition as a predicate on named values (`SortedBy comp xs`, `IsCons xs`), and each derived value as a name built from names (`Reverse xs`, `Opposite comp`). (2) Make each function that relies on a property take its proof, or a refinement type. (3) Provide checked introductions that test once and return evidence (`classify`, `same`). (4) State lemmas as functions between proofs, asserted in the defining module. (5) Let clients `name` values, derive what they need with the logic, and forget with `the` at the end.

**TypeScript and C++.** The ideas carry over; the enforcement differs, and each difference below is shown in the examples.

- *No run-time cost.* TypeScript brands intersection types (`T & { readonly [brand]: … }`) that exist only in types. C++ keeps the name or property in a template argument, so `Named<T, N>` has `T`'s layout.
- *Fresh names.* TypeScript uses the callback's own type parameter (`k: <N>(named: Named<T, N>) => R`). C++ builds the name from the callback's closure type, so the name is fresh per call *site*: a loop that names different values at one site reuses it.
- *Escape and forgery.* Haskell's rank-2 type stops a name escaping. TypeScript stops it only if every brand is invariant (`(x: X) => X`); with covariant brands an escaped name widens to `unknown`, escaped names mix, and `never` proves anything. C++ cannot stop escape.
- *Defining module.* In TypeScript it is the module holding the only `as` casts. In C++ it is a class of static functions granted access by private constructors and `friend typename N::DefinedBy`; a client can still specialize a library template for a tag of its own and forge the property for that tag.
- *Refinement types and `...?`* abstract over a predicate constructor, which needs higher-kinded types. Neither language has them, so apply the predicate to its other arguments (`SortedBy<C>`) and state lemmas directly on refined values (`reverseSorted`).
- *Checking.* C++ checks a template body only when instantiated, so instantiate each derived rule once with unrelated tag types; it also cannot infer a proposition from the expected result, so some rules take it explicitly (`introOrL<P, Q>`). Implicit `Fact`s need Haskell's constraint solver; the other two pass evidence explicitly.

## Example: ghosts of departed proofs — merging lists sorted the same way

After `gdp`'s own example program. `mergeBy` is only correct when both lists are sorted by the comparator it is given. Here the comparator gets a name, sortedness is a property *of that name*, and merging with a different comparator, a second name for the same function, or the opposite order does not compile. Reversing a sorted list uses a lemma the library asserts. The only run-time work is the sorting and merging itself.

**Haskell** (the core of `gdp` inlined; in a project, depend on `gdp` and keep the library part in its own module with the constructors unexported)

```haskell
{-# LANGUAGE ConstraintKinds #-}
{-# LANGUAGE FlexibleContexts #-}
{-# LANGUAGE FlexibleInstances #-}
{-# LANGUAGE FunctionalDependencies #-}
{-# LANGUAGE KindSignatures #-}
{-# LANGUAGE RankNTypes #-}
{-# LANGUAGE RoleAnnotations #-}
{-# LANGUAGE TypeOperators #-}
import Data.Coerce (Coercible, coerce)
import Data.Kind (Type)
import qualified Data.List as L

-- gdp's core, inlined (Theory.Named, Logic.Proof, Data.Refined) ------------

newtype Named name a = Named a -- a value with a phantom name; same representation as a
type role Named nominal nominal -- no coerce from one name to another
type a ~~ name = Named name a

-- A fresh name that cannot escape the continuation (rank-2 type).
name :: a -> (forall name. (a ~~ name) -> t) -> t
name x k = k (coerce x)

-- Library-minted names and predicates are newtypes over Defn. With the
-- constructor unexported, Defining holds only in the defining module.
data Defn = Defn
type Defining p = (Coercible p Defn, Coercible Defn p)

defn :: Defining f => a -> (a ~~ f)
defn = coerce

data Proof (p :: Type) = QED -- no data: only the type matters

axiom :: Proof p -- for library authors asserting facts
axiom = QED

newtype a ::: p = SuchThat a -- a value with a ghost proof of p
type role (:::) nominal nominal
infixr 1 :::

(...) :: a -> Proof p -> (a ::: p)
x ... _ = coerce x

newtype Satisfies (p :: Type -> Type) a = Satisfies a -- refinement type: a ?p
type role Satisfies nominal nominal
type a ? p = Satisfies p a
infixr 1 ?

class The d a | d -> a where the :: d -> a
instance The (Named name a) a where the = coerce
instance The (Satisfies p a) a where the = coerce

unname :: (a ~~ name ::: p name) -> (a ? p) -- forget the name, keep the property
unname = coerce

rename :: (a ? p) -> (forall name. (a ~~ name ::: p name) -> t) -> t
rename x k = name (the x) (\n -> k (n ... axiom))

assert :: Defining (p ()) => a -> (a ? p) -- only where p's constructor is visible
assert x = name x (\n -> unname (n ... axiom))

-- A named function plus a lemma becomes a function between refinement types.
(...?) :: (forall name. (a ~~ name) -> (b ~~ f name)) -> (forall name. p name -> Proof (q (f name))) -> (a ? p) -> (b ? q)
(f ...? _) x = rename x (\n -> unname (f (coerce n) ... axiom))

-- The library (after gdp's own example): merge needs two lists sorted by the SAME comparator.

newtype SortedBy comp name = SortedBy Defn
type role SortedBy nominal nominal

sortBy :: ((a -> a -> Ordering) ~~ comp) -> [a] -> ([a] ? SortedBy comp)
sortBy comp xs = assert (L.sortBy (the comp) xs)

mergeBy :: ((a -> a -> Ordering) ~~ comp) -> ([a] ? SortedBy comp) -> ([a] ? SortedBy comp) -> ([a] ? SortedBy comp)
mergeBy comp xs ys = assert (go (the xs) (the ys))
  where
    go [] r = r
    go l [] = l
    go (x : l) (y : r) = case the comp x y of
      GT -> y : go (x : l) r
      _ -> x : go l (y : r)

newtype Opposite comp = Opposite Defn
type role Opposite nominal

opposite :: ((a -> a -> Ordering) ~~ comp) -> ((a -> a -> Ordering) ~~ Opposite comp)
opposite comp = defn (flip (the comp))

newtype Reverse xs = Reverse Defn
type role Reverse nominal

rev :: ([a] ~~ xs) -> ([a] ~~ Reverse xs)
rev xs = defn (reverse (the xs))

-- A lemma the library author asserts: reversing a list sorted by comp gives
-- a list sorted by the opposite of comp.
revSorted :: SortedBy comp xs -> Proof (SortedBy (Opposite comp) (Reverse xs))
revSorted _ = axiom

-- Client code: name the comparator; every proof now mentions that name.
mergeBoth :: [Int] -> [Int] -> ([Int], [Int])
mergeBoth xs0 ys0 = name compare $ \up ->
  let xs = sortBy up xs0
      ys = sortBy up ys0
      down = opposite up
      rev' = rev ...? revSorted
   in (the (mergeBy up xs ys), the (mergeBy down (rev' xs) (rev' ys)))

-- mergeBy down xs ys             -- rejected: xs is sorted by up, not by Opposite up
-- name compare (\other -> mergeBy other xs ys) -- rejected: other is a fresh name, not up
```

**TypeScript**

```typescript
// gdp's core in TypeScript: brands that exist only in types, so a named or
// refined value is the plain value at run time. (x: X) => X keeps each brand
// invariant, so never cannot stand in for a real name or property.
declare const nameOf: unique symbol;
declare const holds: unique symbol;

export type Named<T, N> = T & { readonly [nameOf]: (n: N) => N }; // gdp's a ~~ n
export type Satisfies<T, P> = T & { readonly [holds]: (p: P) => P }; // gdp's a ?p, with p applied

// A fresh name: N is a type parameter of the callback, so it is distinct from every other name.
export const name = <T, R>(x: T, k: <N>(named: Named<T, N>) => R): R => k(x as Named<T, unknown>);

// The library ("defining module"): the only place that may assert a property.
declare const sortedByTag: unique symbol;
declare const oppositeTag: unique symbol;
export type SortedBy<C> = { readonly [sortedByTag]: (c: C) => C }; // sorted by the comparator named C
export type Opposite<C> = { readonly [oppositeTag]: (c: C) => C }; // a name built from a name

type Cmp<T> = (a: T, b: T) => number;
type SortedList<T, C> = Satisfies<readonly T[], SortedBy<C>>;

const assert = <T, P>(x: T): Satisfies<T, P> => x as Satisfies<T, P>; // not exported

export const sortBy = <T, C>(cmp: Named<Cmp<T>, C>, xs: readonly T[]): SortedList<T, C> =>
  assert([...xs].sort(cmp));

// Both inputs must be sorted by the SAME named comparator; so is the output.
export const mergeBy = <T, C>(cmp: Named<Cmp<T>, C>, xs: SortedList<T, C>, ys: SortedList<T, C>): SortedList<T, C> => {
  const out: T[] = [];
  let i = 0;
  let j = 0;
  while (i < xs.length && j < ys.length) out.push(cmp(xs[i]!, ys[j]!) > 0 ? ys[j++]! : xs[i++]!);
  return assert([...out, ...xs.slice(i), ...ys.slice(j)]);
};

export const opposite = <T, C>(cmp: Named<Cmp<T>, C>): Named<Cmp<T>, Opposite<C>> =>
  ((a: T, b: T) => cmp(b, a)) as Named<Cmp<T>, Opposite<C>>;

// A lemma the library asserts: reversing a list sorted by C gives one sorted by Opposite<C>.
export const reverseSorted = <T, C>(xs: SortedList<T, C>): SortedList<T, Opposite<C>> => assert([...xs].reverse());

// Client code: name the comparator; every property now mentions that name.
// The callback's result must not mention the name, so it returns plain arrays.
export const mergeBoth = (xs0: readonly number[], ys0: readonly number[]) =>
  name(
    (a: number, b: number) => a - b,
    (up): readonly (readonly number[])[] => {
      const xs = sortBy(up, xs0);
      const ys = sortBy(up, ys0);
      const down = opposite(up);
      // mergeBy(down, xs, ys) is rejected: xs is sorted by up, not by Opposite<up>
      return [mergeBy(up, xs, ys), mergeBy(down, reverseSorted(xs), reverseSorted(ys))];
    },
  );
```

**C++**

```cpp
#include <algorithm>
#include <functional>
#include <iterator>
#include <utility>
#include <vector>

// gdp's core in C++: names and properties live only in template arguments,
// so Named<T, N> and Satisfies<T, P> have the layout of T.
template <typename T, typename N>
class Named {  // gdp's a ~~ n
public:
  const T& the() const { return value_; }
private:
  explicit Named(T v) : value_(std::move(v)) {}
  T value_;
  template <typename U, typename K> friend auto name(U, K);
  friend typename N::DefinedBy;  // gdp's defn: only the module that defines N may attach it
};

// A fresh name per call site: every lambda has its own type K, so Fresh<T, K> is new.
template <typename T, typename K> struct Fresh { using DefinedBy = Fresh; };

template <typename T, typename K>
auto name(T x, K k) {
  return k(Named<T, Fresh<T, K>>(std::move(x)));
}

template <typename T, typename P>
class Satisfies {  // gdp's a ?p
public:
  const T& the() const { return value_; }
private:
  explicit Satisfies(T v) : value_(std::move(v)) {}
  T value_;
  friend typename P::DefinedBy;  // gdp's assert: only P's defining module may claim P
};

// The library ("defining module"): the only code that may assert SortedBy.
struct SortingLib;
template <typename C> struct SortedBy { using DefinedBy = SortingLib; };  // sorted by the comparator named C
template <typename C> struct Opposite { using DefinedBy = SortingLib; };  // a name built from a name

template <typename T, typename C>
using SortedList = Satisfies<std::vector<T>, SortedBy<C>>;

struct SortingLib {
  template <typename T, typename Cmp, typename C>
  static SortedList<T, C> sortBy(const Named<Cmp, C>& cmp, std::vector<T> xs) {
    std::sort(xs.begin(), xs.end(), cmp.the());
    return SortedList<T, C>(std::move(xs));
  }

  // Both inputs must be sorted by the SAME named comparator; so is the output.
  template <typename T, typename Cmp, typename C>
  static SortedList<T, C> mergeBy(const Named<Cmp, C>& cmp, const SortedList<T, C>& xs, const SortedList<T, C>& ys) {
    std::vector<T> out;
    std::merge(xs.the().begin(), xs.the().end(), ys.the().begin(), ys.the().end(), std::back_inserter(out), cmp.the());
    return SortedList<T, C>(std::move(out));
  }

  template <typename Cmp, typename C>
  static auto opposite(const Named<Cmp, C>& cmp) {
    auto flipped = [c = cmp.the()](const auto& a, const auto& b) { return c(b, a); };
    return Named<decltype(flipped), Opposite<C>>(flipped);
  }

  // A lemma the library asserts: reversing a list sorted by C gives one sorted by Opposite<C>.
  template <typename T, typename C>
  static SortedList<T, Opposite<C>> reverseSorted(const SortedList<T, C>& xs) {
    return SortedList<T, Opposite<C>>(std::vector<T>(xs.the().rbegin(), xs.the().rend()));
  }
};

// Client code: name the comparator; every property now mentions that name.
std::pair<std::vector<int>, std::vector<int>> mergeBoth(const std::vector<int>& xs0, const std::vector<int>& ys0) {
  return name(std::less<int>{}, [&](auto up) {
    auto xs = SortingLib::sortBy(up, xs0);
    auto ys = SortingLib::sortBy(up, ys0);
    auto down = SortingLib::opposite(up);
    // SortingLib::mergeBy(down, xs, ys);  // error: xs is sorted by up, not by Opposite of up
    return std::pair{SortingLib::mergeBy(up, xs, ys).the(),
                     SortingLib::mergeBy(down, SortingLib::reverseSorted(xs), SortingLib::reverseSorted(ys)).the()};
  });
}
```

Natural deduction with checked proofs, and a safe `head` and `last` through a checked introduction, in three languages: [examples.md](examples.md).

## Related skills

`make-illegal-states-unrepresentable` · `names-are-not-type-safety` · `parse-dont-validate` · `expressive-static-types` · `formal-verification` · `denotational-design` · `smart-constructor` (the extrinsic alternative)

## Sources

- functional-architecture.org, [Correctness by Construction](https://functional-architecture.org/correctness_by_construction/) (pattern page; upstream TODO) and the historical notes on "make illegal values unrepresentable" in [Make Illegal States Unrepresentable](https://functional-architecture.org/make_illegal_states_unrepresentable/).
- Alexis King, [Types as axioms, or: playing god with static types](https://lexi-lambda.github.io/blog/2020/08/13/types-as-axioms-or-playing-god-with-static-types/) (2020) and **[Names are not type safety](https://lexi-lambda.github.io/blog/2020/11/01/names-are-not-type-safety/)** (2020).
- Leon Heuer, Falk Woldmann Lu, Jan Haase, *Functional State Machines in Rust: Typestate and Newtype Patterns* (experience report, [FUNARCH 2026](https://functional-architecture.org/events/funarch-2026/)).
- Will Crichton, [Typed Design Patterns for the Functional Era](https://dl.acm.org/doi/10.1145/3609025.3609477) (FUNARCH 2023) — Witness and State Machine patterns.
- Marco Perone, Georgios Karachalias, [Crème de la Crem: Composable Representable Executable Machines](https://dl.acm.org/doi/10.1145/3609025.3609480) (FUNARCH 2023) — allowed transitions at the type level.
- Matt Noonan, [`gdp`](https://github.com/matt-noonan/gdp) (0.0.3.0, the library accompanying *Ghosts of Departed Proofs*; read the source and documentation of every module — `Theory.Named`, `Logic.Proof`, `Data.Refined`, `Data.The`, `Logic.Propositional`, `Logic.Classes`, `Logic.NegClasses`, `Logic.Implicit`, `Theory.Equality`, `Theory.Lists`, `Data.Arguments` — and the example program `app/Main.hs`) — names, `Defn`, nominal roles, ghost proofs, refinement types, `...?`, natural deduction, classical logic behind a constraint, equality, algebraic property classes, checked introductions, implicit facts, and the sorted-merge example. The paper itself (linked from the curated list at kataskeue.com) could not be fetched, so nothing here is attributed to it. The TypeScript and C++ encodings are this collection's own.
- David Thrane Christiansen, [Functional Programming in Lean](https://lean-lang.org/functional_programming_in_lean/) (read from the [book's source](https://github.com/leanprover/fp-lean): *Pitfalls of Programming with Dependent Types*, and the summary of *Programming, Proving, and Performance*) — the interface/implementation break for functions in types, `Fin`.
- Further reading cited by the sources: Conor McBride, *How to Keep Your Neighbours in Order*; Matt Noonan, *Ghosts of Departed Proofs*.
