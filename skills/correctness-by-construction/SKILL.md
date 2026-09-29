---
name: correctness-by-construction
description: Correctness by construction — make invariants follow from how values are built (constructive types, typestate, GADTs, proofs) instead of checking them. Use when an invariant is re-checked in many places, when a protocol has an order of operations, or when an interpreter can fail on ill-formed input.
---

# Correctness by construction

> *Upstream status:* the functional-architecture.org page for this pattern is TODO. This skill is synthesized from the sources listed at the end.

A value is **correct by construction** when the only ways to build it produce valid values, so no code ever has to check it. Alexis King puts it as *types as axioms*: a datatype declaration is a small set of axioms and inference rules, and every value is a derivation from them. Design the rules so that every derivation is valid — "don't try to add post-hoc restrictions to exclude bad values, **make your datatypes correct by construction**."

Contrast with extrinsic guarantees (a wrapper plus a smart constructor): there, correctness depends on trusted code and discipline. With a constructive type, "there is no trusted code … all parts of the program are equally beholden to the datatype-mandated constraints" (`names-are-not-type-safety`).

## A ladder of techniques

Climb only as far as the invariant is worth; each rung costs more.

1. **Constructive algebraic data types.** Sums, products, recursion: `NonEmpty a = a :| [a]`, `EvenList a = [(a, a)]`, one case per state. Available in every language with records and tagged unions (`make-illegal-states-unrepresentable`).
2. **Typestate / phantom types.** Encode *where you are in a protocol* in a type parameter, and give each operation the signature that only accepts the right state (`Conn Open -> …`). Order-of-operations bugs become type errors. Experience reports (Rust, FUNARCH 2026) find it improves faultlessness and testability at the cost of boilerplate and some readability — most worthwhile for code with extensive branching and many invariants.
   A related technique, from Noonan's `gdp` library (*Ghosts of Departed Proofs*), attaches a phantom **name** to a value (`a ~~ name`) or a **ghost proof** of a proposition (`a ::: p`). Both have the run-time representation of `a`, so the proof costs no space or time. A library mints names in one module, as a newtype over `Defn` whose constructor is not exported. Give the phantom parameters `nominal` roles: otherwise clients can `coerce` between names and forge proofs the library never blessed. Lemmas such as `NonEmpty xs -> Proof (NonEmpty (Reverse xs))` lift a plain function to one between refined types (`rev' = rev ...? rev_nonempty_lemma`). The library author still asserts the base facts (`assert`, `axiom`), so the guarantee is only as good as those modules.
3. **Indexed types / GADTs.** Let constructors refine the type index: a typed expression tree `Expr Int` cannot contain an ill-typed `Add (BoolLit True) …`, so its evaluator has no error cases ("well-typed programs cannot go wrong"). Length-indexed vectors, well-scoped syntax, and sorted-by-construction search trees (McBride, *How to Keep Your Neighbours in Order*) live here.
4. **Machine-checked specifications.** Dependent types and proof assistants (Agda, Idris, Lean, Rocq/Coq) — the functional-architecture site calls this "make illegal *values* unrepresentable", where functions are values too. See `formal-verification`. Lean's `Fin n`, a number bundled with a proof that it is below `n`, makes `Fin arr.size` always a valid index into `arr`.

**Costs of the upper rungs.** When a function appears in a type, its implementation becomes part of the interface, because the checker compares types by *definitional equality*, which runs the function. The Lean book's example: `plusL` recurses on its first argument, so `plusL 0 k` reduces to `k` and `append : Vect α n → Vect α k → Vect α (n.plusL k)` is a direct recursion. `plusR` returns the same sums but recurses on its second argument, so `plusR 0 k` is *stuck* on the variable `k` and the same `append` no longer type-checks; Lean's own `Nat.add` behaves like `plusR`. Getting unstuck needs an explicit proof of propositional equality. In the book's words, exposing a function's internals in a type means refactoring it "may cause programs that use it to no longer type check", so the usual freedom to change the algorithm and keep the behavior is gone. Climb only as far as the invariant is worth.

## Procedure

1. State the invariant precisely, in one sentence, including *when* it must hold (always? after step X?).
2. Ask which constructors could produce a violation. Can you remove or refine them so none can?
   - an invariant about shape → rung 1;
   - about the order of operations → rung 2;
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

## Related skills

`make-illegal-states-unrepresentable` · `names-are-not-type-safety` · `parse-dont-validate` · `expressive-static-types` · `formal-verification` · `denotational-design` · `smart-constructor` (the extrinsic alternative)

## Sources

- functional-architecture.org, [Correctness by Construction](https://functional-architecture.org/correctness_by_construction/) (pattern page; upstream TODO) and the historical notes on "make illegal values unrepresentable" in [Make Illegal States Unrepresentable](https://functional-architecture.org/make_illegal_states_unrepresentable/).
- Alexis King, [Types as axioms, or: playing god with static types](https://lexi-lambda.github.io/blog/2020/08/13/types-as-axioms-or-playing-god-with-static-types/) (2020) and **[Names are not type safety](https://lexi-lambda.github.io/blog/2020/11/01/names-are-not-type-safety/)** (2020).
- Leon Heuer, Falk Woldmann Lu, Jan Haase, *Functional State Machines in Rust: Typestate and Newtype Patterns* (experience report, [FUNARCH 2026](https://functional-architecture.org/events/funarch-2026/)).
- Will Crichton, [Typed Design Patterns for the Functional Era](https://dl.acm.org/doi/10.1145/3609025.3609477) (FUNARCH 2023) — Witness and State Machine patterns.
- Marco Perone, Georgios Karachalias, [Crème de la Crem: Composable Representable Executable Machines](https://dl.acm.org/doi/10.1145/3609025.3609480) (FUNARCH 2023) — allowed transitions at the type level.
- Matt Noonan, [`gdp`](https://github.com/matt-noonan/gdp) (the library accompanying *Ghosts of Departed Proofs*; read the source and documentation of `Theory.Named` and `Data.Refined`) — names, ghost proofs, refinement types, nominal roles. The paper itself (linked from the curated list at kataskeue.com) could not be fetched, so nothing here is attributed to it.
- David Thrane Christiansen, [Functional Programming in Lean](https://lean-lang.org/functional_programming_in_lean/) (read from the [book's source](https://github.com/leanprover/fp-lean): *Pitfalls of Programming with Dependent Types*, and the summary of *Programming, Proving, and Performance*) — the interface/implementation break for functions in types, `Fin`.
- Further reading cited by the sources: Conor McBride, *How to Keep Your Neighbours in Order*; Matt Noonan, *Ghosts of Departed Proofs*.
