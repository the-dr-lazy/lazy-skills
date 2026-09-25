# Algebraic effect systems — worked examples

Examples are given in Haskell, TypeScript, and C++ where the concept carries over; each block is self-contained.

## 1. The same password store in polysemy

Polysemy uses `Sem r` with a type-level list of effects `r` and `Member`/`Members` constraints. Compare with the effectful version in [SKILL.md](SKILL.md); the TypeScript and C++ equivalents there apply unchanged.

**Haskell** (polysemy)

```haskell
{-# LANGUAGE DataKinds #-}
{-# LANGUAGE FlexibleContexts #-}
{-# LANGUAGE GADTs #-}
{-# LANGUAGE LambdaCase #-}
{-# LANGUAGE PolyKinds #-}
{-# LANGUAGE RankNTypes #-}
{-# LANGUAGE ScopedTypeVariables #-}
{-# LANGUAGE TypeApplications #-}
{-# LANGUAGE TypeOperators #-}
import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map
import Polysemy
import Polysemy.State (evalState, gets, modify)

newtype Username = Username String deriving (Eq, Ord, Show)
newtype Password = Password String
newtype PasswordHash = PasswordHash String deriving (Eq, Show)

data CryptoHash m a where
  MakeHash :: Password -> CryptoHash m PasswordHash
  ValidateHash :: Password -> PasswordHash -> CryptoHash m Bool

data UserStore m a where
  WriteUser :: Username -> PasswordHash -> UserStore m ()
  LookupUser :: Username -> UserStore m (Maybe PasswordHash)

-- `makeSem ''CryptoHash` (Template Haskell) generates these four wrappers.
makeHash :: Member CryptoHash r => Password -> Sem r PasswordHash
makeHash p = send (MakeHash p)

validateHash :: Member CryptoHash r => Password -> PasswordHash -> Sem r Bool
validateHash p h = send (ValidateHash p h)

writeUser :: Member UserStore r => Username -> PasswordHash -> Sem r ()
writeUser u h = send (WriteUser u h)

lookupUser :: Member UserStore r => Username -> Sem r (Maybe PasswordHash)
lookupUser u = send (LookupUser u)

addUser :: Members '[CryptoHash, UserStore] r => Username -> Password -> Sem r ()
addUser user password = makeHash password >>= writeUser user

validatePassword :: Members '[CryptoHash, UserStore] r => Username -> Password -> Sem r Bool
validatePassword user password =
  lookupUser user >>= maybe (pure False) (validateHash password)

runCryptoHashFake :: Sem (CryptoHash ': r) a -> Sem r a
runCryptoHashFake = interpret $ \case
  MakeHash (Password p) -> pure (PasswordHash (reverse p)) -- a test double, NOT a real hash
  ValidateHash (Password p) h -> pure (PasswordHash (reverse p) == h)

runUserStorePure :: Map Username PasswordHash -> Sem (UserStore ': r) a -> Sem r a
runUserStorePure initial = evalState initial . reinterpret (\case
  WriteUser u h -> modify (Map.insert u h)
  LookupUser u -> gets (Map.lookup u))

main :: IO ()
main = print . run . runUserStorePure Map.empty . runCryptoHashFake $ do
  addUser (Username "alyssa") (Password "hunter2")
  validatePassword (Username "alyssa") (Password "hunter2") -- True
```

## 2. A higher-order effect: profiling a sub-computation

`Profile :: String -> m a -> Profiling m a` takes a *computation*. The handler must run it in the caller's environment — in effectful through the `LocalEnv` and an unlift function; in polysemy through `Tactics` (`runT`/`bindT`). Swapping the handler turns profiling off without touching callers.

**Haskell** (effectful)

```haskell
{-# LANGUAGE DataKinds #-}
{-# LANGUAGE GADTs #-}
{-# LANGUAGE LambdaCase #-}
{-# LANGUAGE TypeFamilies #-}
import Effectful
import Effectful.Dispatch.Dynamic (interpret, localSeqUnlift, localSeqUnliftIO, send)
import GHC.Clock (getMonotonicTime)

data Profiling :: Effect where
  Profile :: String -> m a -> Profiling m a

type instance DispatchOf Profiling = Dynamic

profile :: Profiling :> es => String -> Eff es a -> Eff es a
profile label action = send (Profile label action)

runProfiling :: IOE :> es => Eff (Profiling : es) a -> Eff es a
runProfiling = interpret $ \env -> \case
  Profile label action -> localSeqUnliftIO env $ \unlift -> do
    t1 <- getMonotonicTime
    r <- unlift action -- run the caller's computation in the caller's environment
    t2 <- getMonotonicTime
    putStrLn ("Action '" <> label <> "' took " <> show (t2 - t1) <> " seconds.")
    pure r

runNoProfiling :: Eff (Profiling : es) a -> Eff es a
runNoProfiling = interpret $ \env -> \case
  Profile _ action -> localSeqUnlift env $ \unlift -> unlift action

work :: (Profiling :> es, IOE :> es) => Eff es Int
work = profile "sum" (liftIO (pure $! sum [1 .. 1000000 :: Int]))

main :: IO ()
main = do
  print =<< runEff (runProfiling work)
  print =<< runEff (runNoProfiling work)
```

**TypeScript** (Effect: a service with a generic, higher-order method)

```typescript
import { Clock, Context, Effect, Layer } from "effect";

class Profiling extends Context.Tag("Profiling")<
  Profiling,
  { readonly profile: <A, E, R>(label: string, eff: Effect.Effect<A, E, R>) => Effect.Effect<A, E, R> }
>() {}

const ProfilingLive = Layer.succeed(Profiling, {
  profile: (label, eff) =>
    Effect.gen(function* () {
      const t1 = yield* Clock.currentTimeMillis;
      const r = yield* eff;
      const t2 = yield* Clock.currentTimeMillis;
      yield* Effect.log(`Action '${label}' took ${t2 - t1} ms`);
      return r;
    }),
});

const NoProfiling = Layer.succeed(Profiling, { profile: (_label, eff) => eff });

const work = Effect.gen(function* () {
  const p = yield* Profiling;
  return yield* p.profile("sum", Effect.sync(() => Array.from({ length: 1_000_000 }, (_, i) => i + 1).reduce((a, b) => a + b, 0)));
});

export const profiled = Effect.runSync(work.pipe(Effect.provide(ProfilingLive)));
export const plain = Effect.runSync(work.pipe(Effect.provide(NoProfiling)));
```

**C++** (a capability whose operation is a function template)

```cpp
#include <chrono>
#include <iostream>
#include <string_view>

template <typename P>
concept Profiling = requires(P& p) { p.profile("label", [] { return 0; }); };

struct ProfilingLive {
  template <typename F>
  auto profile(std::string_view label, F&& action) {
    auto t1 = std::chrono::steady_clock::now();
    auto r = action();  // run the caller's computation
    auto t2 = std::chrono::steady_clock::now();
    std::cout << "Action '" << label << "' took "
              << std::chrono::duration<double>(t2 - t1).count() << " seconds.\n";
    return r;
  }
};

struct NoProfiling {
  template <typename F>
  auto profile(std::string_view, F&& action) { return action(); }
};

template <Profiling P>
long long work(P& p) {
  return p.profile("sum", [] {
    long long s = 0;
    for (long long i = 1; i <= 1000000; ++i) s += i;
    return s;
  });
}

int main() {
  ProfilingLive live;
  NoProfiling off;
  std::cout << work(live) << '\n' << work(off) << '\n';
}
```

## 3. The handler decides the semantics: does a caught failure roll back state?

The same program — add 10, fail, recover — observes different states depending on the effect implementation and interpretation order. Verified results are in the comments. Decide which semantics your domain needs and pin them with a test.

**Haskell**

```haskell
{-# LANGUAGE DataKinds #-}
{-# LANGUAGE ScopedTypeVariables #-}
{-# LANGUAGE TypeApplications #-}
import qualified Control.Monad.Except as Mtl
import qualified Control.Monad.State as Mtl
import Effectful
import Effectful.Error.Static (Error, catchError, runErrorNoCallStack, throwError)
import Effectful.State.Static.Local (State, get, modify, runState)

transfer :: (State Int :> es, Error String :> es) => Eff es ()
transfer = modify @Int (+ 10) >> throwError "boom"

recovered :: (State Int :> es, Error String :> es) => Eff es Int
recovered = (transfer >> pure 0) `catchError` (\_ (_ :: String) -> get @Int)

-- mtl: StateT over Either; the lifted catchError restarts from the state at the catch.
recoveredMtl :: Mtl.StateT Int (Either String) Int
recoveredMtl = (Mtl.modify (+ 10) >> Mtl.throwError "boom") `Mtl.catchError` (\_ -> Mtl.get)

main :: IO ()
main = do
  print (runPureEff (runErrorNoCallStack @String (runState @Int 0 transfer))) -- Left "boom": state not observable
  print (runPureEff (runState @Int 0 (runErrorNoCallStack @String transfer))) -- (Left "boom",10)
  print (runPureEff (runErrorNoCallStack @String (runState @Int 0 recovered))) -- Right (10,10): update kept
  print (Mtl.runStateT recoveredMtl 0) -- Right (0,0): update rolled back
```

**TypeScript** (Effect: `Ref` updates are not rolled back; make transactions explicit, or use STM)

```typescript
import { Effect, Ref } from "effect";

const transfer = (balance: Ref.Ref<number>) =>
  Effect.gen(function* () {
    yield* Ref.update(balance, (n) => n + 10);
    return yield* Effect.fail("boom" as const);
  });

const transactionally = <A, E>(ref: Ref.Ref<number>, eff: Effect.Effect<A, E>) =>
  Effect.gen(function* () {
    const before = yield* Ref.get(ref);
    return yield* eff.pipe(Effect.tapError(() => Ref.set(ref, before)));
  });

const recover = (wrap: (ref: Ref.Ref<number>) => Effect.Effect<never, "boom">) =>
  Effect.runSync(
    Effect.gen(function* () {
      const balance = yield* Ref.make(0);
      yield* wrap(balance).pipe(Effect.catchAll(() => Effect.void));
      return yield* Ref.get(balance);
    }),
  );

export const kept = recover(transfer); // 10
export const rolledBack = recover((ref) => transactionally(ref, transfer(ref))); // 0
```

**C++** (exceptions: in-place mutation survives; commit-on-success copies roll back)

```cpp
#include <stdexcept>

struct Account { int balance = 0; };

void transfer(Account& a) {
  a.balance += 10;
  throw std::runtime_error("boom");
}

template <typename F>
void transactionally(Account& a, F f) {
  Account draft = a;  // work on a copy ...
  f(draft);
  a = draft;          // ... and commit only if f returned normally
}

int kept() {
  Account a;
  try { transfer(a); } catch (const std::exception&) {}
  return a.balance;  // 10
}

int rolledBack() {
  Account a;
  try { transactionally(a, transfer); } catch (const std::exception&) {}
  return a.balance;  // 0
}
```
