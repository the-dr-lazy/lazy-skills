---
name: algebraic-effect-systems
description: Algebraic effect systems — effects as declared operations, logic written against effect constraints, handlers chosen at the edge (Haskell effectful/polysemy/mtl, Effect-TS, C++ capability concepts). Use when choosing or using an effect library, writing handlers, handling higher-order effects, or debugging handler order.
---

# Algebraic effect systems

An effect system turns "what a function may do to the world" into something you can **declare, compose, and interpret**:

1. An **effect** is a set of operations declared as data (a GADT of constructors, an interface, a service tag).
2. Business logic runs in one monad (`Eff es`, `Sem r`, `Effect<A, E, R>`) and lists the effects it needs as constraints (`CryptoHash :> es`). The type says exactly which effects it can perform — and which it cannot.
3. **Handlers / interpreters** give each effect meaning — real IO, an in-memory fake, a logging decorator — and are chosen at the program's edge. The same logic runs in production and in a pure test.

This is the heavyweight end of `composable-effects`. It pays off when many effects must combine, when several interpretations of the same logic are needed, and when the type-level effect list is valued as documentation and enforcement.

## Procedure

1. **Name each effect by capability, not by technology:** `UserStore`, not `Postgres`. Keep effects small and cohesive; a high-level domain effect can be interpreted in terms of low-level ones (`reinterpret`).
2. **Declare operations** (one constructor each) and their `send`/`makeEffect` wrappers.
3. **Write the logic against constraints only.** It should read like the specification.
4. **Write at least two handlers:** the production one (at the edge, may use `IOE`/`IO`) and a pure one (state, map, list) for tests. A handler that needs private state uses `reinterpret` so the state is invisible outside.
5. **Choose the interpretation order deliberately** and test it: whether a caught error rolls back state, whether a logger sees aborted work, whether resources are released, depends on the order and the library.
6. **Keep effect-system code at the seams.** Pure functions stay pure (`functional-core-imperative-shell`); an effect is for talking to the world, not for every helper.

Done when: logic functions mention only effect constraints (no concrete monad or `IO`), each effect has a production and a pure handler, and a test runs the logic through the pure handlers.

## Example: a password store (after *Polysemy is fun!*)

**Haskell** (effectful, dynamic dispatch)

```haskell
{-# LANGUAGE DataKinds #-}
{-# LANGUAGE GADTs #-}
{-# LANGUAGE LambdaCase #-}
{-# LANGUAGE TypeFamilies #-}
import Data.IORef (IORef, modifyIORef', newIORef, readIORef)
import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map
import Effectful
import Effectful.Dispatch.Dynamic (interpret_, reinterpret_, send)
import Effectful.State.Static.Local (evalState, gets, modify)

newtype Username = Username String deriving (Eq, Ord, Show)
newtype Password = Password String
newtype PasswordHash = PasswordHash String deriving (Eq, Show)

-- Effects are data: one constructor per operation.
data CryptoHash :: Effect where
  MakeHash :: Password -> CryptoHash m PasswordHash
  ValidateHash :: Password -> PasswordHash -> CryptoHash m Bool

type instance DispatchOf CryptoHash = Dynamic

data KVStore k v :: Effect where
  WriteKV :: k -> v -> KVStore k v m ()
  LookupKV :: k -> KVStore k v m (Maybe v)

type instance DispatchOf (KVStore k v) = Dynamic

makeHash :: CryptoHash :> es => Password -> Eff es PasswordHash
makeHash p = send (MakeHash p)

validateHash :: CryptoHash :> es => Password -> PasswordHash -> Eff es Bool
validateHash p h = send (ValidateHash p h)

writeKV :: KVStore k v :> es => k -> v -> Eff es ()
writeKV k v = send (WriteKV k v)

lookupKV :: KVStore k v :> es => k -> Eff es (Maybe v)
lookupKV k = send (LookupKV k)

-- Business logic reads like the spec; the constraints list every effect it may perform.
addUser :: (CryptoHash :> es, KVStore Username PasswordHash :> es) => Username -> Password -> Eff es ()
addUser user password = do
  hashed <- makeHash password
  writeKV user hashed

validatePassword :: (CryptoHash :> es, KVStore Username PasswordHash :> es) => Username -> Password -> Eff es Bool
validatePassword user password = do
  stored <- lookupKV user
  case stored of
    Just h -> validateHash password h
    Nothing -> pure False

-- Handlers are chosen at the edge.
runCryptoHashFake :: Eff (CryptoHash : es) a -> Eff es a -- a test double, NOT a real hash
runCryptoHashFake = interpret_ $ \case
  MakeHash (Password p) -> pure (PasswordHash (reverse p))
  ValidateHash (Password p) h -> pure (PasswordHash (reverse p) == h)

runKVStorePure :: Ord k => Map k v -> Eff (KVStore k v : es) a -> Eff es a
runKVStorePure initial = reinterpret_ (evalState initial) $ \case -- private state
  WriteKV k v -> modify (Map.insert k v)
  LookupKV k -> gets (Map.lookup k)

runKVStoreIORef :: (IOE :> es, Ord k) => IORef (Map k v) -> Eff (KVStore k v : es) a -> Eff es a
runKVStoreIORef ref = interpret_ $ \case
  WriteKV k v -> liftIO (modifyIORef' ref (Map.insert k v))
  LookupKV k -> liftIO (Map.lookup k <$> readIORef ref)

scenario :: (CryptoHash :> es, KVStore Username PasswordHash :> es) => Eff es Bool
scenario = do
  addUser (Username "alyssa") (Password "hunter2")
  validatePassword (Username "alyssa") (Password "hunter2")

main :: IO ()
main = do
  let noUsers = Map.empty :: Map Username PasswordHash -- pins the polymorphic KVStore k v
  print (runPureEff (runKVStorePure noUsers (runCryptoHashFake scenario))) -- pure test run
  ref <- newIORef noUsers
  print =<< runEff (runKVStoreIORef ref (runCryptoHashFake scenario)) -- IO run
```

**TypeScript** (Effect: services are tags, handlers are layers)

```typescript
import { Context, Effect, Layer, Ref } from "effect";

type Username = string;
type Password = string;
type PasswordHash = string;

class CryptoHash extends Context.Tag("CryptoHash")<
  CryptoHash,
  {
    readonly makeHash: (p: Password) => Effect.Effect<PasswordHash>;
    readonly validateHash: (p: Password, h: PasswordHash) => Effect.Effect<boolean>;
  }
>() {}

class KVStore extends Context.Tag("KVStore")<
  KVStore,
  {
    readonly write: (k: Username, v: PasswordHash) => Effect.Effect<void>;
    readonly lookup: (k: Username) => Effect.Effect<PasswordHash | undefined>;
  }
>() {}

// Business logic: the R type parameter (CryptoHash | KVStore) lists every effect it needs.
export const addUser = (user: Username, password: Password) =>
  Effect.gen(function* () {
    const crypto = yield* CryptoHash;
    const store = yield* KVStore;
    yield* store.write(user, yield* crypto.makeHash(password));
  });

export const validatePassword = (user: Username, password: Password) =>
  Effect.gen(function* () {
    const crypto = yield* CryptoHash;
    const store = yield* KVStore;
    const stored = yield* store.lookup(user);
    return stored === undefined ? false : yield* crypto.validateHash(password, stored);
  });

// Handlers: chosen at the edge.
const CryptoHashFake = Layer.succeed(CryptoHash, {
  makeHash: (p) => Effect.succeed([...p].reverse().join("")), // a test double, NOT a real hash
  validateHash: (p, h) => Effect.succeed([...p].reverse().join("") === h),
});

const KVStoreInMemory = Layer.effect(
  KVStore,
  Effect.gen(function* () {
    const ref = yield* Ref.make(new Map<Username, PasswordHash>()); // private state
    return {
      write: (k, v) => Ref.update(ref, (m) => new Map(m).set(k, v)),
      lookup: (k) => Effect.map(Ref.get(ref), (m) => m.get(k)),
    };
  }),
);

const scenario = Effect.gen(function* () {
  yield* addUser("alyssa", "hunter2");
  return yield* validatePassword("alyssa", "hunter2");
});

export const result: boolean = Effect.runSync(
  scenario.pipe(Effect.provide(Layer.merge(CryptoHashFake, KVStoreInMemory))),
);
```

**C++** (capability concepts, static dispatch — "tagless final" without higher-kinded types)

```cpp
#include <concepts>
#include <map>
#include <optional>
#include <string>

using Username = std::string;
using Password = std::string;
using PasswordHash = std::string;

// Effects as capability concepts: what a component may do, not how.
template <typename C>
concept CryptoHash = requires(C& c, const Password& p, const PasswordHash& h) {
  { c.makeHash(p) } -> std::same_as<PasswordHash>;
  { c.validateHash(p, h) } -> std::same_as<bool>;
};

template <typename S>
concept KVStore = requires(S& s, const Username& k, const PasswordHash& v) {
  { s.write(k, v) } -> std::same_as<void>;
  { s.lookup(k) } -> std::same_as<std::optional<PasswordHash>>;
};

// Business logic: its template parameters list every effect it may perform.
template <CryptoHash C, KVStore S>
void addUser(C& crypto, S& store, const Username& user, const Password& password) {
  store.write(user, crypto.makeHash(password));
}

template <CryptoHash C, KVStore S>
bool validatePassword(C& crypto, S& store, const Username& user, const Password& password) {
  auto stored = store.lookup(user);
  return stored && crypto.validateHash(password, *stored);
}

// Handlers: chosen at the edge.
struct CryptoHashFake {  // a test double, NOT a real hash
  PasswordHash makeHash(const Password& p) { return {p.rbegin(), p.rend()}; }
  bool validateHash(const Password& p, const PasswordHash& h) { return makeHash(p) == h; }
};

struct KVStoreInMemory {
  std::map<Username, PasswordHash> data;
  void write(const Username& k, const PasswordHash& v) { data.insert_or_assign(k, v); }
  std::optional<PasswordHash> lookup(const Username& k) {
    if (auto it = data.find(k); it != data.end()) return it->second;
    return std::nullopt;
  }
};

bool scenario() {
  CryptoHashFake crypto;
  KVStoreInMemory store;
  addUser(crypto, store, "alyssa", "hunter2");
  return validatePassword(crypto, store, "alyssa", "hunter2");
}
```

The same program in polysemy, a higher-order effect (profiling a sub-computation), interpretation order changing observable results, and mtl-style testing seams: [examples.md](examples.md).

## Concepts that matter in practice

- **First-order vs higher-order effects.** `ReadFile :: FilePath -> FileSystem m String` never uses `m`: easy. `Profile :: String -> m a -> Profiling m a` takes a *computation*: the handler must run it in the caller's local environment (effectful `localSeqUnlift`, polysemy `runT`/`bindT` "Tactics"). Resource effects (`bracket`) are the classic hard case: other effects' state must be threaded through allocation, use, and release.
- **Interpretation order has semantics.** Error-then-state versus state-then-error decides whether you *observe* the state after a failure, and in some libraries whether a caught error rolls it back. Nondeterminism combined with other effects is where libraries disagree most ("semantics zoo"). Decide what you want, then pin it with a test.
- **Static vs dynamic dispatch.** Static (a concrete handler known at compile time) is fastest; dynamic (a handler chosen at run time) is what enables test doubles. effectful supports both; start dynamic.
- **Type inference with polymorphic effects** (`KVStore k v`) can be ambiguous; pin types at the call site or use the library's plugin (effectful-plugin, polysemy-plugin).

## Choosing a library (Haskell, 2019–2025 view)

| Approach | Strengths | Costs |
|---|---|---|
| **mtl-style classes** (`MonadDB m =>`) | Familiar; seams for tests; effects visible in types | n×m instance boilerplate (mitigate with default signatures); transformer semantics pitfalls; slower |
| **ReaderT-over-IO pattern** | Simple, fast, exception-safe | Not an effect system: no effect list in types |
| **effectful** | `ReaderT IO` "on steroids": fast, correct with runtime exceptions, integrates with `MonadUnliftIO`/`resourcet`/`exceptions`; static and dynamic dispatch | Cannot capture continuations: no `NonDet`/coroutine effects (use `conduit`, `list-t`) |
| **polysemy** | Very flexible handlers, low boilerplate | Slower; higher-order effects (Tactics) are intricate |
| **fused-effects**, **freer-simple**, **Bluefin** | Carrier-based / freer / capability-passing alternatives; Bluefin has replaced mtl in industrial tooling (Groq) | Smaller ecosystems |

In **TypeScript**, Effect (`Effect<A, E, R>`: success, typed error, requirements) is the mainstream effect system; lighter options are passing capability objects explicitly or `fp-ts`'s `ReaderTaskEither`. In **C++**, there is no mainstream effect system: use capability concepts (static) or abstract interfaces (dynamic), passed explicitly, and command variants when programs must be data (`free-monads`).

## Related skills

`composable-effects` (the decision above this one) · `free-monads` · `data-types-a-la-carte` (where extensible effects came from) · `functional-core-imperative-shell` · `late-decision-making` · `composable-error-handling` · `continuations`

## Sources

- Raghu Kaippully, [Polysemy is fun! — Part 1](https://haskell-explained.gitlab.io/blog/posts/2019/07/28/polysemy-is-cool-part-1/index.html) (2019).
- Sandy Maguire, [Polysemy Internals: The Effect-Interpreter Effect](https://reasonablypolymorphic.com/blog/tactics/) (2019).
- Andrzej Rybczak and contributors, [effectful](https://github.com/haskell-effectful/effectful) (README) and the [`Effectful.Dispatch.Dynamic`](https://hackage.haskell.org/package/effectful-core/docs/Effectful-Dispatch-Dynamic.html) documentation.
- Alexis King, [Using types to unit-test in Haskell](https://lexi-lambda.github.io/blog/2016/10/03/using-types-to-unit-test-in-haskell/) (2016), [Lifts for free: making mtl typeclasses derivable](https://lexi-lambda.github.io/blog/2017/04/28/lifts-for-free-making-mtl-typeclasses-derivable/) (2017), [Unit testing effectful Haskell with monad-mock](https://lexi-lambda.github.io/blog/2017/06/29/unit-testing-effectful-haskell-with-monad-mock/) (2017).
- Tom Ellis, *Bluefin in Industry* (lightning talk, [FUNARCH 2025](https://functional-architecture.org/events/funarch-2025/)).
- Wolf McNally, [Side Effect](https://aipatternbook.com/side-effect/), *Encyclopedia of Agentic Coding Patterns*.
- Further reading cited by the sources: Alexis King, *Effects for Less* (talk); Michael Snoyman, *ReaderT design pattern*.
