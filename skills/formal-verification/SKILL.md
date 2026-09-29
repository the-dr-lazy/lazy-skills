---
name: formal-verification
description: Formal verification — choose the right rigor (types, properties, model checking, proofs, certifiers) and keep the verified part small, pure, and connected to running code. Use when failures are very expensive, when designing concurrent protocols, or when integrating proof-assistant output.
---

# Formal verification

> *Upstream status:* the functional-architecture.org pattern page is TODO. This skill is synthesized from FUNARCH experience reports and the other sources listed at the end.

Functional architecture makes verification *reachable*: pure functions obey equations, so they can be reasoned about with substitution (equational reasoning); explicit effects keep the verified part separate from the world; algebraic structure turns proofs about small pieces into proofs about large compositions. The architectural question is not "prove everything" but **what to verify, how rigorously, and how to keep the verified part small and connected to the running system**.

## The ladder of rigor

| Rung | Technique | Buys | Typical tools |
|---|---|---|---|
| Types | constructive types, typestate, GADTs | whole classes of errors impossible | GHC, TypeScript `strict`, C++ concepts |
| Properties | property-based / model-based tests | laws and invariants checked on many inputs | QuickCheck, Hedgehog, fast-check, RapidCheck |
| Model checking | exhaustive exploration of a model's state space | all interleavings of a concurrent protocol, within bounds | TLA+/PlusCal, Alloy, hand-rolled explorers |
| Proof | machine-checked proofs of a specification | correctness for all inputs | Rocq (Coq), Lean, Agda, Isabelle, F*, Liquid Haskell |
| Extraction | generate code from the proved artefact | the running code *is* the proved code | Rocq/Coq extraction to OCaml/Haskell |
| Certification | check each *output* of unverified code with a verified checker | assurance without verifying a fast-moving codebase | translation validation certifiers |

**Scale the rigor to the cost of the bug.** Learn TLA+ frames TLA+ as a formal specification language, "the software equivalent of a blueprint", from which a model checker verifies that a design has no critical bugs. Its opening example is a check-then-act race in a trading algorithm: an owner check before a transfer looks safe, but Alice can trade an item to herself while a parallel trade gives it to Bob, and the checker finds it because it explores every state and timeline. A model also scales by changing a constant (`People == {"alice", "bob", "eve"}`; several items at once). Formal methods are hard when the dangerous bug is "somebody dies"; when it is "customers get really mad and we lose two weeks", the small subset you need is much easier. The guide assumes you are an experienced programmer who knows testing and some math.

## Architectural moves (from the field)

- **Keep a small trusted kernel.** Factor effects out (free monads, functional core) so the part you reason about is pure; the impure residue is minimal and easy to audit.
- **Mix verified and unverified components deliberately.** A verified tool-path analyzer for 3D printing (FUNARCH 2024) moved from hand-written OCaml to extracted, verified components step by step; design module boundaries so verified pieces can be dropped in.
- **Certify instead of verifying when the code moves fast.** For the Plutus compiler, a separate, layered certifier validates each compiler run (translation validation) and develops largely independently of the main compiler; extraction lets the certifier run as an extra compiler check (FUNARCH 2025).
- **Run formal methods continuously.** Cardano applies formal specifications, functional architecture, and Haskell together, keeping the specification and the implementation connected as both evolve (FUNARCH 2024).
- **Model concurrency as data and explore it exhaustively.** Represent processes as state machines (PlusCal-style), combine them as Cartesian products, and check invariants over *every* reachable state.
- **Test the implementation against the verified model** with property-based testing: the model is the oracle.
- **Keep the clear version as an executable specification.** A rewrite into accumulator-passing or otherwise faster form is harder to read, so keep the original as the spec of the optimized one. Unit tests work in any language; in a proof assistant such as Lean you can also prove both return the same result for *all* inputs: function extensionality, then induction on the argument the recursion follows. When the induction hypothesis is too weak, generalize the statement over arbitrary initial accumulator values.

## Procedure

1. **Name the failure you cannot afford** and the property that rules it out.
2. **Pick the lowest rung that establishes it** with enough confidence; climb only for the parts that need it.
3. **Isolate the part to verify** behind a pure interface; everything else talks to it through that interface.
4. **Test before you prove.** Get the program right with tests, then prove. The Lean book's workflow for termination: write the function `partial`, debug it with tests, replace `partial` with `termination_by`, put each obligation Lean reports in a `have` proved by `sorry`, and once the program is accepted and still passes its tests, prove the obligations. That avoids proving that a buggy program terminates. (`partial` functions cannot be unfolded in proofs, so they stay out of anything you need to reason about.)
5. **Connect verification to the running code:** extraction, a certifier in the pipeline, or differential tests against the model — never a proof about code nobody runs.
6. **Run it in CI** so specification, proofs, and implementation cannot drift, and fail the build on provisional proofs. Lean's `sorry` is convenient during development but proves *any* statement, false ones included; proving `3 < 2` can let an out-of-bounds array access survive to run time. Lean warns whenever a proof depends on it.

Done when: each critical property names its rung and artefact (type, property suite, model, proof, certifier), that artefact runs in CI, and the verified part is connected to production code.

## Example: a tiny model checker finds a lost update

Two processes increment a shared counter by reading it into a local and writing `local + 1`. Exploring every interleaving shows a reachable final state where the counter is 1; making the increment atomic removes it.

**Haskell**

```haskell
import qualified Data.Set as Set

data Pc = Read | Write | Finished deriving (Eq, Ord, Show)

data St = St {pcs :: (Pc, Pc), locals :: (Int, Int), counter :: Int} deriving (Eq, Ord, Show)

initial :: St
initial = St (Read, Read) (0, 0) 0

-- Interleaving semantics: either process may take the next step.
next :: Bool -> St -> [St]
next atomic s = [s' | i <- [0, 1], Just s' <- [stepProc atomic i s]]

stepProc :: Bool -> Int -> St -> Maybe St
stepProc atomic i (St ps ls c) = case (get ps, atomic) of
  (Read, True) -> Just (St (set ps Finished) ls (c + 1)) -- atomic increment
  (Read, False) -> Just (St (set ps Write) (set ls c) c) -- read into local
  (Write, _) -> Just (St (set ps Finished) ls (get ls + 1)) -- write local + 1
  (Finished, _) -> Nothing
  where
    get (a, b) = if i == 0 then a else b
    set (a, b) x = if i == 0 then (x, b) else (a, x)

-- Visit every reachable state; report those violating the invariant.
check :: (St -> Bool) -> Bool -> [St]
check invariant atomic = go Set.empty [initial]
  where
    go _ [] = []
    go seen (s : rest)
      | s `Set.member` seen = go seen rest
      | otherwise = [s | not (invariant s)] <> go (Set.insert s seen) (next atomic s <> rest)

bothDoneMeansTwo :: St -> Bool
bothDoneMeansTwo s = pcs s /= (Finished, Finished) || counter s == 2

main :: IO ()
main = do
  print (check bothDoneMeansTwo False) -- [St {pcs = (Finished,Finished), locals = (0,0), counter = 1}]
  print (check bothDoneMeansTwo True) -- []
```

**TypeScript**

```typescript
type Pc = "read" | "write" | "finished";
type St = { pcs: [Pc, Pc]; locals: [number, number]; counter: number };

const initial: St = { pcs: ["read", "read"], locals: [0, 0], counter: 0 };

function stepProc(atomic: boolean, i: 0 | 1, s: St): St | undefined {
  const pcs: [Pc, Pc] = [...s.pcs];
  const locals: [number, number] = [...s.locals];
  switch (s.pcs[i]) {
    case "read":
      if (atomic) { pcs[i] = "finished"; return { pcs, locals, counter: s.counter + 1 }; }
      pcs[i] = "write"; locals[i] = s.counter; return { pcs, locals, counter: s.counter };
    case "write":
      pcs[i] = "finished"; return { pcs, locals, counter: s.locals[i] + 1 };
    case "finished":
      return undefined;
  }
}

const next = (atomic: boolean, s: St): St[] =>
  ([0, 1] as const).flatMap((i) => stepProc(atomic, i, s) ?? []);

export function check(invariant: (s: St) => boolean, atomic: boolean): St[] {
  const seen = new Set<string>();
  const stack: St[] = [initial];
  const violations: St[] = [];
  while (stack.length > 0) {
    const s = stack.pop()!;
    const key = JSON.stringify(s);
    if (seen.has(key)) continue;
    seen.add(key);
    if (!invariant(s)) violations.push(s);
    stack.push(...next(atomic, s));
  }
  return violations;
}

const bothDoneMeansTwo = (s: St) => !(s.pcs[0] === "finished" && s.pcs[1] === "finished") || s.counter === 2;

export const racy = check(bothDoneMeansTwo, false); // one violation: counter === 1
export const safe = check(bothDoneMeansTwo, true); // []
```

**C++**

```cpp
#include <array>
#include <iostream>
#include <optional>
#include <set>
#include <tuple>
#include <vector>

enum class Pc { Read, Write, Finished };

struct St {
  std::array<Pc, 2> pcs{Pc::Read, Pc::Read};
  std::array<int, 2> locals{0, 0};
  int counter = 0;
  auto operator<=>(const St&) const = default;
};

std::optional<St> stepProc(bool atomic, int i, St s) {
  switch (s.pcs[i]) {
    case Pc::Read:
      if (atomic) { s.pcs[i] = Pc::Finished; ++s.counter; return s; }
      s.pcs[i] = Pc::Write; s.locals[i] = s.counter; return s;
    case Pc::Write:
      s.pcs[i] = Pc::Finished; s.counter = s.locals[i] + 1; return s;
    case Pc::Finished:
      return std::nullopt;
  }
  return std::nullopt;
}

template <typename Invariant>
std::vector<St> check(Invariant invariant, bool atomic) {
  std::set<St> seen;
  std::vector<St> stack{St{}}, violations;
  while (!stack.empty()) {
    St s = stack.back();
    stack.pop_back();
    if (!seen.insert(s).second) continue;
    if (!invariant(s)) violations.push_back(s);
    for (int i : {0, 1})
      if (auto t = stepProc(atomic, i, s)) stack.push_back(*t);
  }
  return violations;
}

int main() {
  auto bothDoneMeansTwo = [](const St& s) {
    return !(s.pcs[0] == Pc::Finished && s.pcs[1] == Pc::Finished) || s.counter == 2;
  };
  std::cout << check(bothDoneMeansTwo, false).size() << ' '   // 1: the lost update
            << check(bothDoneMeansTwo, true).size() << '\n';  // 0
}
```

## Related skills

`property-based-testing` · `correctness-by-construction` · `algebraic-modelling` (equational reasoning) · `pure-functions` · `free-monads` (a trusted kernel plus a minimal interpreter) · `belt-and-suspenders` (certifiers as independent guards) · `denotational-design`

## Sources

- functional-architecture.org, [Formal Verification](https://functional-architecture.org/formal_verification/) (pattern page; upstream TODO).
- Hillel Wayne, [Learn TLA+](https://learntla.com/) (read from the guide's [repository](https://github.com/hwayne/learntla), default branch: the older PlusCal/Toolbox edition, *Introduction* and *About this guide*) — what TLA+ is for, the trade race found by exhaustive exploration, scaling a model by changing constants, and how much rigor is worth it.
- David Thrane Christiansen, [Functional Programming in Lean](https://lean-lang.org/functional_programming_in_lean/) (read from the [book's source](https://github.com/leanprover/fp-lean), chapter *Programming, Proving, and Performance*, summary section) — executable specifications proved equal by induction, provisional proofs with `sorry`, the test-first termination workflow, `Fin` for safe indexing.
- Matthew Sottile, Mohit Tekriwal, [Design and implementation of a verified interpreter for additive manufacturing programs](https://dl.acm.org/doi/10.1145/3677998.3678221) (FUNARCH 2024).
- James Chapman, Arnaud Bailly, Polina Vinogradova, [Applying Continuous Formal Methods to Cardano](https://dl.acm.org/doi/10.1145/3677998.3678222) (FUNARCH 2024).
- Jacco Krijnen, Wouter Swierstra, Gabriele Keller, Manuel Chakravarty, Joris Dral, [A Layered Certifying Compiler Architecture](https://dl.acm.org/doi/10.1145/3759163.3760427) (FUNARCH 2025).
- Gabriella Gonzalez, [Modeling PlusCal in Haskell using Cartesian products of NFAs](https://haskellforall.com/2022/03/modeling-pluscal-in-haskell-using) (2022), [Equational reasoning](https://haskellforall.com/2013/12/equational-reasoning) (2013), [Equational reasoning at scale](https://haskellforall.com/2014/07/equational-reasoning-at-scale) (2014), [Purify code using free monads](https://haskellforall.com/2012/07/purify-code-using-free-monads) (2012), [The Curry-Howard correspondence between programs and proofs](https://haskellforall.com/2017/02/the-curry-howard-correspondence-between) (2017).
