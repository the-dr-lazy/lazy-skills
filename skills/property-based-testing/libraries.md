# Property-based testing libraries — reference

What to reach for in each language, and the handful of knobs that matter. The concepts are shared: **generators** (arbitraries) produce inputs whose size grows during a run, **shrinkers** reduce a failing input to a minimal one, a **seed** replays a run, and **preconditions** discard inputs.

## Haskell

- **QuickCheck** (Claessen & Hughes) — the original. Type-directed generation through `Arbitrary`; `forAll gen prop` for custom generators; `==>` preconditions; `counterexample`, `label`, `classify`, `cover`/`checkCoverage` to see what was tested; `Fun a b` with the `Fn f` pattern to generate functions; `quickCheckWith stdArgs {maxSuccess = n, maxSize = m}`; `expectFailure` for properties that must fail. Test monadic code with `Test.QuickCheck.Monadic`.
- **Hedgehog** — generators are explicit values with *integrated shrinking* (shrinks always respect how the value was generated, so invariants of the generator survive shrinking); ranges (`Range.linear`) make the size distribution explicit; built-in state-machine testing.
- **falsify** (Well-Typed; covered in *The Haskell Unfolder*, episode 4) — internal, sample-tree-based shrinking in the Hypothesis tradition.

```haskell
import Test.QuickCheck

newtype Arabic = Arabic Int deriving (Show)

instance Arbitrary Arabic where
  arbitrary = Arabic <$> chooseInt (1, 3999)
  shrink (Arabic n) = [Arabic m | m <- shrink n, m >= 1, m <= 3999]

prop_inRange :: Arabic -> Property
prop_inRange (Arabic n) = classify (n > 1000) "large" (n >= 1 && n <= 3999)

main :: IO ()
main = quickCheckWith stdArgs {maxSuccess = 1000} prop_inRange
```

## TypeScript

- **fast-check** — `fc.assert(fc.property(arbs..., predicate), { numRuns, seed, path })`; `fc.asyncProperty` for promises; `fc.pre(cond)` preconditions; arbitraries for primitives, records, unions (`fc.oneof`), recursive structures (`fc.letrec`), functions (`fc.func`); `.filter`/`.map`/`.chain` to derive arbitraries; model-based testing with `fc.commands` + `fc.modelRun`; `fc.check` returns details instead of throwing. Integrates with any test runner (Vitest, Jest, node:test).

```typescript
import fc from "fast-check";

const arabic = fc.integer({ min: 1, max: 3999 });

fc.assert(
  fc.property(arabic, (n) => n >= 1 && n <= 3999),
  { numRuns: 1000 }, // replay a failure with { seed, path } printed in the report
);
```

## C++

- **RapidCheck** — `rc::check("name", [](const T& x) { RC_ASSERT(...); })` with type-directed generation for standard types; `*rc::gen::inRange(a, b)` (half-open) and other combinators inside the property to draw values; `RC_PRE` preconditions; `RC_CLASSIFY`/`RC_TAG` for distribution; stateful/model-based testing with `rc::state`; integrations for Google Test, Catch, Boost.Test. Configure with the `RC_PARAMS` environment variable (`seed=…`, `max_success=…`, `max_size=…`, `verbose_progress=1`).

```cpp
#include <rapidcheck.h>

int main() {
  rc::check("arabic numbers are in range", [] {
    const int n = *rc::gen::inRange(1, 4000);
    RC_CLASSIFY(n > 1000, "large");
    RC_ASSERT(n >= 1 && n < 4000);
  });
}
```

## Other ecosystems

F# / C#: **FsCheck** (the library used throughout Wlaschin's series: `Check.Quick`, `Check.Verbose`, `Config` with `MaxTest`, `StartSize`, `EndSize`, `Replay`; `Prop.forAll`, `==>`, `.&.`, `|@` labels; `[<Property>]` for NUnit/xUnit). Python: **Hypothesis**. Rust: **proptest**, **quickcheck**. JVM: **jqwik**, ScalaCheck. Erlang/Elixir: **PropEr**, Quviq QuickCheck, StreamData.

## Configuration lessons (from Wlaschin's *Understanding FsCheck*)

- Sizes start small and grow; default integers cluster around zero. A property false only above 80 passed 1,000 runs and failed only after raising the maximum size — **understand the domain and configure the generator for it**.
- Shrinking walks each argument down in turn; the reported counterexample is a local minimum (`25, 1, 26` exposed an EDFH boundary at 25 exactly).
- Verbose mode and custom printers show what was generated; a printed seed replays a run exactly.
- Preconditions that reject most inputs make runs slow and thin; write a generator instead.
- Name properties so reports read well (`prop_…` in Haskell, descriptive strings in fast-check/RapidCheck, `…Property` in .NET), group them into a specification, and keep a few example-based tests alongside as documentation.
