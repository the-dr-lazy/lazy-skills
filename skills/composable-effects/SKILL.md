---
name: composable-effects
description: Composable effects — make side effects explicit and interchangeable (capabilities, mtl/tagless final, free monads, effect systems) so logic runs against real or fake infrastructure. Use when domain logic calls a database, HTTP, or the clock directly, when code is hard to test, or when choosing an effect approach.
---

# Composable effects

> *functional-architecture.org:* "Effect systems allow us to deal with effects by making them explicit. Effect systems also allow effectful code to be run in a pure environment, which makes our code better testable." (Pattern page upstream TODO.)

`functional-core-imperative-shell` separates pure logic from the world, but real domain logic *uses* infrastructure ("store the order", "read the rate"). Pushed into the shell, that logic makes the shell large, complex, and untested. The next step is to represent the interactions themselves as something the core can talk about — an interface, a constraint, a data structure — and to decide what they *do* separately.

## What you are buying

- **Explicitness:** the signature says which effects a function may perform — and, as importantly, which it may not.
- **Substitutability:** the same logic runs against production infrastructure, an in-memory fake, a recorder, or a simulator.
- **Composability:** effects combine without a tower of adapters; interpreters compose (a logging interpreter wraps a real one).
- **Reasoning:** code that treats effects as values keeps algebraic laws. Haskell separates *evaluation order* from *effect order*, so `f =<< (xs <|> ys) = (f =<< xs) <|> (f =<< ys)` holds even when `f`, `xs`, `ys` print.

## The ladder — climb only as high as the problem needs

| Rung | Technique | Reach for it when |
|---|---|---|
| 0 | **Functional core, imperative shell** | Always first. Many "effects" are just inputs and outputs of a pure function. |
| 1 | **Pass capabilities explicitly** — higher-order functions, records of functions ("handles"), interfaces | Any language; a few effects; you want dependency injection without a framework. "Dependency injection? Use a higher-order function." |
| 2 | **Abstract over the monad with constraints** — mtl classes, tagless final, C++ concepts | Effects should appear in types and be restricted per function; test instances are cheap. |
| 3 | **Programs as data** — free monads / operational commands | You need to inspect, log, replay, optimize, or sandbox programs, or run them under several interpreters (`free-monads`). |
| 4 | **Extensible effect systems** — effectful, polysemy, Effect-TS | Many effects combine, handlers are swapped per environment, higher-order effects (bracket, profiling) matter (`algebraic-effect-systems`). |

## Procedure

1. **Squeeze first.** Move every decision that does not need the world into pure functions (`functional-core-imperative-shell`). What remains are genuine interactions.
2. **Name the capabilities the logic needs** in domain terms (`UserStore`, `Clock`, `Payments`), not technology terms. One capability per reason to change.
3. **Pick the rung** from the table; prefer the lowest that gives the explicitness and substitutability you need.
4. **Write the logic against the capabilities only.** No concrete clients, no global singletons, no `IO`/`Promise`-returning helpers reached for "just this once".
5. **Provide two implementations of each capability:** production, and a **fake** (in-memory, deterministic). Prefer fakes to mocks — mocks couple tests to the exact call sequence. Use mocks only behind a *low-level* interface to a complex external system (a cloud API), and implement a *high-level* domain capability on top of it, so the rest of the code is tested against a fake of the high-level one.
6. **Wire at the edge** (the composition root, `main`, the request handler).
7. **Test through the fakes**, including properties: "after `write k v`, `lookup k` returns `v`" holds for the fake *and* the production implementation (contract tests).

Done when: domain logic has no direct dependency on infrastructure, each capability has a production and a fake implementation, and the logic's tests run without network, disk, or clock.

## Example: copy a file only if it is non-empty

**Haskell** (rung 2: an mtl-style class as the seam; a `State`-backed fake)

```haskell
{-# LANGUAGE GeneralizedNewtypeDeriving #-}
import Control.Monad (unless)
import Control.Monad.State (State, execState, gets, modify)
import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map
import Prelude hiding (readFile, writeFile)
import qualified Prelude

class Monad m => MonadFileSystem m where
  readFile :: FilePath -> m String
  writeFile :: FilePath -> String -> m ()

-- The logic: its type says it touches the file system and nothing else.
copyNonemptyFile :: MonadFileSystem m => FilePath -> FilePath -> m ()
copyNonemptyFile from to = do
  contents <- readFile from
  unless (null contents) (writeFile to contents)

instance MonadFileSystem IO where -- production
  readFile = Prelude.readFile
  writeFile = Prelude.writeFile

newtype FakeFS a = FakeFS (State (Map FilePath String) a) -- test double: a fake, not a mock
  deriving (Functor, Applicative, Monad)

instance MonadFileSystem FakeFS where
  readFile p = FakeFS (gets (Map.findWithDefault "" p))
  writeFile p c = FakeFS (modify (Map.insert p c))

runFakeFS :: Map FilePath String -> FakeFS a -> Map FilePath String
runFakeFS fs (FakeFS m) = execState m fs

-- runFakeFS (Map.fromList [("a", "hi")]) (copyNonemptyFile "a" "b") == Map.fromList [("a","hi"),("b","hi")]
-- runFakeFS (Map.fromList [("a", "")])   (copyNonemptyFile "a" "b") == Map.fromList [("a","")]
```

**TypeScript** (rung 1: a capability interface passed in; an in-memory fake)

```typescript
export interface FileSystem {
  readFile(path: string): Promise<string>;
  writeFile(path: string, contents: string): Promise<void>;
}

export async function copyNonemptyFile(fs: FileSystem, from: string, to: string): Promise<void> {
  const contents = await fs.readFile(from);
  if (contents.length > 0) await fs.writeFile(to, contents);
}

export class InMemoryFileSystem implements FileSystem {
  constructor(readonly files: Map<string, string> = new Map()) {}
  async readFile(path: string): Promise<string> {
    return this.files.get(path) ?? "";
  }
  async writeFile(path: string, contents: string): Promise<void> {
    this.files.set(path, contents);
  }
}

// Production: wrap node:fs/promises in the same interface at the composition root.
```

**C++** (rung 2: a capability concept; a fake used in tests)

```cpp
#include <concepts>
#include <map>
#include <string>

template <typename F>
concept FileSystem = requires(F& fs, const std::string& path, const std::string& contents) {
  { fs.readFile(path) } -> std::convertible_to<std::string>;
  fs.writeFile(path, contents);
};

template <FileSystem F>
void copyNonemptyFile(F& fs, const std::string& from, const std::string& to) {
  std::string contents = fs.readFile(from);
  if (!contents.empty()) fs.writeFile(to, contents);
}

struct InMemoryFileSystem {  // a fake, not a mock
  std::map<std::string, std::string> files;
  std::string readFile(const std::string& p) const {
    auto it = files.find(p);
    return it == files.end() ? "" : it->second;
  }
  void writeFile(const std::string& p, const std::string& c) { files.insert_or_assign(p, c); }
};

bool copiesOnlyNonEmpty() {
  InMemoryFileSystem fs{{{"a", "hi"}, {"empty", ""}}};
  copyNonemptyFile(fs, "a", "b");
  copyNonemptyFile(fs, "empty", "c");
  return fs.files.contains("b") && !fs.files.contains("c");
}
```

Records of functions (the "handle" pattern), decorating an interpreter with logging, and contract properties shared by fake and production implementations — in three languages: [examples.md](examples.md).

## Related skills

`functional-core-imperative-shell` (rung 0) · `free-monads` (rung 3) · `algebraic-effect-systems` (rung 4) · `pure-functions` · `everything-as-a-value` (capabilities and programs as values) · `late-decision-making` (choose infrastructure later) · `composable-error-handling` · `property-based-testing`

## Sources

- functional-architecture.org, [Composable Effects](https://functional-architecture.org/composable_effects/) (pattern page; upstream TODO) and [Functional Core, Imperative Shell](https://functional-architecture.org/functional_core_imperative_shell/) (*Shortcomings*).
- Alexis King, [Using types to unit-test in Haskell](https://lexi-lambda.github.io/blog/2016/10/03/using-types-to-unit-test-in-haskell/) (2016) and [Unit testing effectful Haskell with monad-mock](https://lexi-lambda.github.io/blog/2017/06/29/unit-testing-effectful-haskell-with-monad-mock/) (2017) — seams, fakes versus mocks, high- and low-level interfaces.
- Gabriella Gonzalez, [Algebraic side effects](https://haskellforall.com/2015/03/algebraic-side-effects) (2015), [Why I prefer functional programming](https://haskellforall.com/2020/10/why-i-prefer-functional-programming) (2020), [Scrap your type classes](https://haskellforall.com/2012/05/scrap-your-type-classes) (2012).
- Wolf McNally, [Side Effect](https://aipatternbook.com/side-effect/), *Encyclopedia of Agentic Coding Patterns* — hidden effects, effect cascades, effects at the wrong layer.
- Gabriella Gonzalez, [Why free monads matter](https://haskellforall.com/2012/06/you-could-have-invented-free-monads); Raghu Kaippully, [Polysemy is fun!](https://haskell-explained.gitlab.io/blog/posts/2019/07/28/polysemy-is-cool-part-1/index.html); Sandy Maguire, [Tactics](https://reasonablypolymorphic.com/blog/tactics/); [effectful](https://github.com/haskell-effectful/effectful).
