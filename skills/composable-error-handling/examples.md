# Composable error handling — worked examples

Each example is given in Haskell, TypeScript, and C++. Each block is self-contained.

## 1. Accumulate independent errors (applicative validation)

`Either` stops at the first failure — right for dependent steps. For independent checks (form fields), users want *every* problem at once. An applicative that combines failures with `<>` does exactly that; it is not a monad, which is precisely why it cannot short-circuit.

**Haskell**

```haskell
{-# LANGUAGE DeriveFunctor #-}

data Validation e a = Failure e | Success a deriving (Show, Functor)

instance Semigroup e => Applicative (Validation e) where
  pure = Success
  Failure e1 <*> Failure e2 = Failure (e1 <> e2) -- both sides' errors are kept
  Failure e <*> Success _ = Failure e
  Success _ <*> Failure e = Failure e
  Success f <*> Success a = Success (f a)

data Signup = Signup {name :: String, email :: String, age :: Int} deriving (Show)

field :: Bool -> String -> a -> Validation [String] a
field ok msg a = if ok then Success a else Failure [msg]

validateSignup :: String -> String -> Int -> Validation [String] Signup
validateSignup n e a =
  Signup
    <$> field (not (null n)) "name is required" n
    <*> field ('@' `elem` e) "email must contain @" e
    <*> field (a >= 18) "must be an adult" a

-- validateSignup "" "nope" 12 == Failure ["name is required","email must contain @","must be an adult"]
```

**TypeScript**

```typescript
type Validation<T> = { ok: true; value: T } | { ok: false; errors: string[] };

const field = <T,>(ok: boolean, msg: string, value: T): Validation<T> =>
  ok ? { ok: true, value } : { ok: false, errors: [msg] };

type Signup = { name: string; email: string; age: number };

export function validateSignup(name: string, email: string, age: number): Validation<Signup> {
  const n = field(name.length > 0, "name is required", name);
  const e = field(email.includes("@"), "email must contain @", email);
  const a = field(age >= 18, "must be an adult", age);
  if (n.ok && e.ok && a.ok) return { ok: true, value: { name: n.value, email: e.value, age: a.value } };
  return { ok: false, errors: [n, e, a].flatMap((v) => (v.ok ? [] : v.errors)) };
}
```

**C++**

```cpp
#include <string>
#include <variant>
#include <vector>

struct Signup { std::string name, email; int age; };
using Errors = std::vector<std::string>;

std::variant<Signup, Errors> validateSignup(const std::string& name, const std::string& email, int age) {
  Errors errors;
  auto check = [&](bool ok, const char* msg) { if (!ok) errors.emplace_back(msg); };
  check(!name.empty(), "name is required");
  check(email.find('@') != std::string::npos, "email must contain @");
  check(age >= 18, "must be an adult");
  if (!errors.empty()) return errors;
  return Signup{name, email, age};
}
```

## 2. Translate errors at layer boundaries

Each layer speaks its own error type. The repository's `RowNotFound` should not leak into the API; the service maps it into its own vocabulary, and the HTTP layer maps that into status codes — each mapping in one place.

**Haskell**

```haskell
import Data.Bifunctor (first)

data DbError = RowNotFound | ConnectionLost deriving (Show)
data ServiceError = UnknownUser String | Unavailable deriving (Show)

findUserRow :: String -> Either DbError (String, String)
findUserRow "alyssa" = Right ("alyssa", "a@example.com")
findUserRow _ = Left RowNotFound

getEmail :: String -> Either ServiceError String
getEmail user = snd <$> first toService (findUserRow user)
  where
    toService RowNotFound = UnknownUser user
    toService ConnectionLost = Unavailable

httpStatus :: Either ServiceError a -> Int
httpStatus (Right _) = 200
httpStatus (Left (UnknownUser _)) = 404
httpStatus (Left Unavailable) = 503
```

**TypeScript**

```typescript
type Result<T, E> = { ok: true; value: T } | { ok: false; error: E };

const mapError = <T, E, F>(r: Result<T, E>, f: (e: E) => F): Result<T, F> => (r.ok ? r : { ok: false, error: f(r.error) });

type DbError = "rowNotFound" | "connectionLost";
type ServiceError = { kind: "unknownUser"; user: string } | { kind: "unavailable" };

const findUserRow = (user: string): Result<{ name: string; email: string }, DbError> =>
  user === "alyssa" ? { ok: true, value: { name: user, email: "a@example.com" } } : { ok: false, error: "rowNotFound" };

export function getEmail(user: string): Result<string, ServiceError> {
  const row = mapError(findUserRow(user), (e): ServiceError =>
    e === "rowNotFound" ? { kind: "unknownUser", user } : { kind: "unavailable" },
  );
  return row.ok ? { ok: true, value: row.value.email } : row;
}

export const httpStatus = <T,>(r: Result<T, ServiceError>): number =>
  r.ok ? 200 : r.error.kind === "unknownUser" ? 404 : 503;
```

**C++**

```cpp
#include <expected>
#include <string>
#include <utility>
#include <variant>

enum class DbError { RowNotFound, ConnectionLost };
struct UnknownUser { std::string user; };
struct Unavailable {};
struct ServiceError { std::variant<UnknownUser, Unavailable> kind; };

std::expected<std::pair<std::string, std::string>, DbError> findUserRow(const std::string& user) {
  if (user == "alyssa") return std::pair<std::string, std::string>{user, "a@example.com"};
  return std::unexpected(DbError::RowNotFound);
}

std::expected<std::string, ServiceError> getEmail(const std::string& user) {
  return findUserRow(user)
      .transform_error([&](DbError e) {
        return e == DbError::RowNotFound ? ServiceError{UnknownUser{user}} : ServiceError{Unavailable{}};
      })
      .transform([](const auto& row) { return row.second; });
}

int httpStatus(const std::expected<std::string, ServiceError>& r) {
  if (r) return 200;
  return std::holds_alternative<UnknownUser>(r.error().kind) ? 404 : 503;
}
```

## 3. Early exit from a loop is short-circuiting

No continuations needed: an `Either`-returning step stops the whole traversal at the first `Left`, and the `Left` carries *why* it stopped.

**Haskell**

```haskell
import Control.Monad (foldM)

-- Sum values until the running total would exceed a budget; report where it stopped.
spendUntil :: Int -> [Int] -> Either (Int, Int) Int -- Left (index, total so far) on exit
spendUntil budget xs = foldM step 0 (zip [0 ..] xs)
  where
    step total (i, x)
      | total + x > budget = Left (i, total) -- stops the fold here
      | otherwise = Right (total + x)
```

**TypeScript**

```typescript
type Exit = { index: number; total: number };

export function spendUntil(budget: number, xs: readonly number[]): { done: number } | { exited: Exit } {
  let total = 0;
  for (const [index, x] of xs.entries()) {
    if (total + x > budget) return { exited: { index, total } }; // the exit carries why it stopped
    total += x;
  }
  return { done: total };
}
```

**C++**

```cpp
#include <cstddef>
#include <expected>
#include <utility>
#include <vector>

// unexpected = (index, total so far) where the loop exited
std::expected<int, std::pair<std::size_t, int>> spendUntil(int budget, const std::vector<int>& xs) {
  int total = 0;
  for (std::size_t i = 0; i < xs.size(); ++i) {
    if (total + xs[i] > budget) return std::unexpected(std::pair{i, total});
    total += xs[i];
  }
  return total;
}
```
