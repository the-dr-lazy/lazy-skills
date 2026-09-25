# Composable effects — worked examples

Each example is given in Haskell, TypeScript, and C++. Each block is self-contained.

## 1. Records of functions: capabilities as plain values

A capability can be an ordinary value — a record whose fields are functions. No type classes, no inheritance, no framework: instances become values you can construct, pass, store, and wrap at run time ("scrap your type classes"). This works identically in every language with first-class functions.

**Haskell**

```haskell
import Data.IORef (modifyIORef', newIORef, readIORef)
import qualified Data.Map.Strict as Map

data UserStore m = UserStore
  { saveUser :: String -> String -> m ()
  , findUser :: String -> m (Maybe String)
  }

register :: Monad m => UserStore m -> String -> String -> m Bool
register store name email = do
  existing <- findUser store name
  case existing of
    Just _ -> pure False
    Nothing -> saveUser store name email >> pure True

inMemoryStore :: IO (UserStore IO)
inMemoryStore = do
  ref <- newIORef Map.empty
  pure
    UserStore
      { saveUser = \n e -> modifyIORef' ref (Map.insert n e)
      , findUser = \n -> Map.lookup n <$> readIORef ref
      }

main :: IO ()
main = do
  store <- inMemoryStore
  first <- register store "alyssa" "a@example.com"
  second <- register store "alyssa" "b@example.com"
  print (first, second) -- (True,False)
```

**TypeScript**

```typescript
type UserStore = {
  readonly saveUser: (name: string, email: string) => Promise<void>;
  readonly findUser: (name: string) => Promise<string | undefined>;
};

export async function register(store: UserStore, name: string, email: string): Promise<boolean> {
  if ((await store.findUser(name)) !== undefined) return false;
  await store.saveUser(name, email);
  return true;
}

export function inMemoryStore(): UserStore {
  const users = new Map<string, string>();
  return {
    saveUser: async (name, email) => void users.set(name, email),
    findUser: async (name) => users.get(name),
  };
}
```

**C++**

```cpp
#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <string>

struct UserStore {
  std::function<void(const std::string&, const std::string&)> saveUser;
  std::function<std::optional<std::string>(const std::string&)> findUser;
};

bool registerUser(const UserStore& store, const std::string& name, const std::string& email) {
  if (store.findUser(name)) return false;
  store.saveUser(name, email);
  return true;
}

UserStore inMemoryStore() {
  auto users = std::make_shared<std::map<std::string, std::string>>();
  return UserStore{
      [users](const std::string& n, const std::string& e) { users->insert_or_assign(n, e); },
      [users](const std::string& n) -> std::optional<std::string> {
        if (auto it = users->find(n); it != users->end()) return it->second;
        return std::nullopt;
      },
  };
}
```

## 2. Interpreters compose: a logging decorator

Because a capability is a value, cross-cutting behaviour is a function from capability to capability. The logic does not change; the wiring at the edge does.

**Haskell**

```haskell
data UserStore m = UserStore
  { saveUser :: String -> String -> m ()
  , findUser :: String -> m (Maybe String)
  }

withLogging :: (String -> IO ()) -> UserStore IO -> UserStore IO
withLogging logLine store =
  UserStore
    { saveUser = \n e -> logLine ("saveUser " <> n) >> saveUser store n e
    , findUser = \n -> do
        r <- findUser store n
        logLine ("findUser " <> n <> " -> " <> maybe "miss" (const "hit") r)
        pure r
    }
```

**TypeScript**

```typescript
type UserStore = {
  readonly saveUser: (name: string, email: string) => Promise<void>;
  readonly findUser: (name: string) => Promise<string | undefined>;
};

export const withLogging = (log: (line: string) => void, store: UserStore): UserStore => ({
  saveUser: async (name, email) => {
    log(`saveUser ${name}`);
    await store.saveUser(name, email);
  },
  findUser: async (name) => {
    const r = await store.findUser(name);
    log(`findUser ${name} -> ${r === undefined ? "miss" : "hit"}`);
    return r;
  },
});
```

**C++**

```cpp
#include <functional>
#include <optional>
#include <string>

struct UserStore {
  std::function<void(const std::string&, const std::string&)> saveUser;
  std::function<std::optional<std::string>(const std::string&)> findUser;
};

UserStore withLogging(std::function<void(const std::string&)> log, UserStore store) {
  return UserStore{
      [log, store](const std::string& n, const std::string& e) {
        log("saveUser " + n);
        store.saveUser(n, e);
      },
      [log, store](const std::string& n) {
        auto r = store.findUser(n);
        log("findUser " + n + " -> " + (r ? "hit" : "miss"));
        return r;
      },
  };
}
```

## 3. One contract, checked against every implementation

Fakes are only trustworthy if they behave like the real thing. State the capability's laws once as properties and run them against the fake in unit tests and against the production implementation in integration tests.

**Haskell**

```haskell
import Data.IORef (modifyIORef', newIORef, readIORef)
import qualified Data.Map.Strict as Map
import Test.QuickCheck
import Test.QuickCheck.Monadic (assert, monadicIO, run)

data UserStore m = UserStore
  { saveUser :: String -> String -> m ()
  , findUser :: String -> m (Maybe String)
  }

inMemoryStore :: IO (UserStore IO)
inMemoryStore = do
  ref <- newIORef Map.empty
  pure UserStore {saveUser = \n e -> modifyIORef' ref (Map.insert n e), findUser = \n -> Map.lookup n <$> readIORef ref}

-- The contract: reading after writing returns what was written (last write wins).
prop_readYourWrites :: IO (UserStore IO) -> String -> String -> String -> Property
prop_readYourWrites mkStore name e1 e2 = monadicIO $ do
  found <- run $ do
    store <- mkStore
    saveUser store name e1
    saveUser store name e2
    findUser store name
  assert (found == Just e2)

main :: IO ()
main = quickCheck (prop_readYourWrites inMemoryStore) -- and, in integration tests, the real store
```

**TypeScript**

```typescript
import fc from "fast-check";

type UserStore = {
  readonly saveUser: (name: string, email: string) => Promise<void>;
  readonly findUser: (name: string) => Promise<string | undefined>;
};

function inMemoryStore(): UserStore {
  const users = new Map<string, string>();
  return { saveUser: async (n, e) => void users.set(n, e), findUser: async (n) => users.get(n) };
}

export const readYourWrites = (mkStore: () => UserStore) =>
  fc.assert(
    fc.asyncProperty(fc.string(), fc.string(), fc.string(), async (name, e1, e2) => {
      const store = mkStore();
      await store.saveUser(name, e1);
      await store.saveUser(name, e2);
      return (await store.findUser(name)) === e2;
    }),
  );

await readYourWrites(inMemoryStore); // and, in integration tests, the real store
```

**C++**

```cpp
#include <rapidcheck.h>

#include <functional>
#include <map>
#include <memory>
#include <optional>
#include <string>

struct UserStore {
  std::function<void(const std::string&, const std::string&)> saveUser;
  std::function<std::optional<std::string>(const std::string&)> findUser;
};

UserStore inMemoryStore() {
  auto users = std::make_shared<std::map<std::string, std::string>>();
  return UserStore{[users](const std::string& n, const std::string& e) { users->insert_or_assign(n, e); },
                   [users](const std::string& n) -> std::optional<std::string> {
                     if (auto it = users->find(n); it != users->end()) return it->second;
                     return std::nullopt;
                   }};
}

void checkReadYourWrites(const std::function<UserStore()>& mkStore) {
  rc::check("read your writes", [&](const std::string& name, const std::string& e1, const std::string& e2) {
    UserStore store = mkStore();
    store.saveUser(name, e1);
    store.saveUser(name, e2);
    RC_ASSERT(store.findUser(name) == std::optional<std::string>(e2));
  });
}

int main() { checkReadYourWrites(inMemoryStore); }  // and, in integration tests, the real store
```
