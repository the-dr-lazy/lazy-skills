# Names are not type safety — worked examples

Each example is given in Haskell, TypeScript, and C++. Each block is self-contained.

## 1. Non-empty list: trusted token versus constructive type

The token version is sound only while every line of its home module is correct; `head` still needs an "impossible" branch. The constructive version needs no trust: its only constructor requires an element.

**Haskell**

```haskell
module NonEmptyToken (NonEmpty, cons, nonEmpty, head, tail) where

import Prelude hiding (head, tail)

-- Token: the constructor is not exported, so this module is the trust boundary.
newtype NonEmpty a = NonEmpty [a]

cons :: a -> [a] -> NonEmpty a
cons x xs = NonEmpty (x : xs)

nonEmpty :: [a] -> Maybe (NonEmpty a)
nonEmpty [] = Nothing
nonEmpty xs = Just (NonEmpty xs)

head :: NonEmpty a -> a
head (NonEmpty (x : _)) = x
head (NonEmpty []) = error "impossible: empty NonEmpty value" -- trusted, not proven

tail :: NonEmpty a -> [a]
tail (NonEmpty (_ : xs)) = xs
tail (NonEmpty []) = error "impossible: empty NonEmpty value"
```

Compare the constructive `data NonEmpty a = a :| [a]` from `Data.List.NonEmpty`, where `head (x :| _) = x` is total and there is no trusted code at all.

**TypeScript**

```typescript
// Token: #items is unreachable from outside, so the class is the trust boundary.
export class NonEmptyToken<T> {
  readonly #items: readonly T[];
  private constructor(items: readonly T[]) {
    this.#items = items;
  }
  static of<T>(xs: readonly T[]): NonEmptyToken<T> | undefined {
    return xs.length > 0 ? new NonEmptyToken(xs) : undefined;
  }
  head(): T {
    const x = this.#items[0];
    if (x === undefined) throw new Error("impossible: empty NonEmptyToken"); // trusted, not proven
    return x;
  }
}

// Constructive: the type itself demands a first element.
export type NonEmpty<T> = readonly [T, ...T[]];
export const head = <T,>(xs: NonEmpty<T>): T => xs[0]; // total, nothing to trust
```

**C++**

```cpp
#include <optional>
#include <stdexcept>
#include <vector>

// Token: the invariant holds only if every member function preserves it.
template <typename T>
class NonEmptyToken {
public:
  static std::optional<NonEmptyToken> of(std::vector<T> xs) {
    if (xs.empty()) return std::nullopt;
    return NonEmptyToken(std::move(xs));
  }
  const T& head() const {
    if (items_.empty()) throw std::logic_error("impossible: empty NonEmptyToken");  // trusted
    return items_.front();
  }
private:
  explicit NonEmptyToken(std::vector<T> xs) : items_(std::move(xs)) {}
  std::vector<T> items_;
};

// Constructive: there is nothing to trust.
template <typename T>
struct NonEmpty {
  T first;
  std::vector<T> rest;
  const T& head() const { return first; }
};
```

## 2. How tokens get forged

Every one of these compiles. Each is a hole in an extrinsic guarantee; none can affect a constructive type.

**Haskell**

```haskell
{-# LANGUAGE DeriveGeneric #-}
{-# LANGUAGE TypeApplications #-}
import GHC.Generics (Generic, K1 (..), M1 (..), to)

newtype NonEmpty a = NonEmpty [a] -- constructor "hidden" by the module's export list...
  deriving (Show, Read, Generic) -- ...but these instances construct values anyway

forgedByRead :: NonEmpty ()
forgedByRead = read "NonEmpty []"

forgedByGeneric :: NonEmpty ()
forgedByGeneric = to (M1 (M1 (M1 (K1 []))))
```

**TypeScript**

```typescript
type Email = string & { readonly __brand: "Email" };

const parseEmail = (s: string): Email | undefined => (s.includes("@") ? (s as Email) : undefined);

// Anyone, anywhere, can do what parseEmail does without the check:
export const forged = "not an email" as Email;

// Structural typing: a same-shaped object satisfies an interface-based "token".
interface Validated { readonly value: string; readonly validated: true }
export const alsoForged: Validated = { value: "anything", validated: true };
export { parseEmail };
```

**C++**

```cpp
enum class Weekday { Mon = 1, Tue, Wed, Thu, Fri, Sat, Sun };

struct Percent {  // "validated" in the factory, but the members are public
  int value;
  static Percent make(int v) { return Percent{v < 0 ? 0 : v > 100 ? 100 : v}; }
};

Weekday forgedDay = static_cast<Weekday>(42);  // enums are open
Percent forgedPercent{250};                     // aggregate init skips the factory
```

## 3. Labels that prevent mix-ups (and are honest about it)

`CustomerId` versus `OrderId`, seconds versus milliseconds: same representation, different meaning. A transparent wrapper stops you adding a `Distance` to a `Duration`; it validates nothing. Keep it cheap to use so that people keep using it.

**Haskell**

```haskell
{-# LANGUAGE DerivingStrategies #-}
{-# LANGUAGE GeneralizedNewtypeDeriving #-}
{-# LANGUAGE OverloadedStrings #-}
import Data.String (IsString)
import Data.Text (Text)
import Numeric.Natural (Natural)

newtype CustomerId = CustomerId Int deriving newtype (Eq, Ord, Show)
newtype OrderId = OrderId Int deriving newtype (Eq, Ord, Show)

newtype TimeoutSecs = TimeoutSecs Int deriving newtype (Eq, Ord, Show, Num)
newtype TimeoutMs = TimeoutMs Int deriving newtype (Eq, Ord, Show, Num)

toMs :: TimeoutSecs -> TimeoutMs
toMs (TimeoutSecs s) = TimeoutMs (s * 1000)

-- Ergonomics (Gonzalez): literals and Show go through the wrapped type.
newtype Name = Name Text deriving newtype (IsString, Show)
newtype Age = Age Natural deriving newtype (Num, Show)

data Person = Person {name :: Name, age :: Age} deriving stock (Show)

example :: Person
example = Person {name = "John Doe", age = 42} -- shows as Person {name = "John Doe", age = 42}
```

**TypeScript**

```typescript
declare const unit: unique symbol;
type Tagged<T, U extends string> = T & { readonly [unit]: U };

type CustomerId = Tagged<number, "CustomerId">;
type OrderId = Tagged<number, "OrderId">;
type Seconds = Tagged<number, "Seconds">;
type Millis = Tagged<number, "Millis">;

const seconds = (n: number) => n as Seconds;
const toMillis = (s: Seconds) => (s * 1000) as Millis;

export function sleep(ms: Millis): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export const ok = sleep(toMillis(seconds(2)));
// sleep(seconds(2));          // error: Seconds is not Millis
export type { CustomerId, OrderId };
```

**C++**

```cpp
#include <chrono>
#include <compare>

// std::chrono is the standard library's own "label" types done well.
using std::chrono::milliseconds;
using std::chrono::seconds;

void sleepFor(milliseconds) {}

template <typename Tag>
struct Id {
  int value;
  auto operator<=>(const Id&) const = default;
};
using CustomerId = Id<struct CustomerTag>;
using OrderId = Id<struct OrderTag>;

void demo() {
  sleepFor(seconds(2));  // converts correctly: 2s -> 2000ms
  CustomerId c{42};
  OrderId o{42};
  // bool same = (c == o);  // error: different types, even with the same int inside
  (void)c; (void)o;
}
```

## 4. Newtype noise

A wrapper that is unwrapped the moment it leaves its record, derives every instance of the wrapped type, and guards against no realistic mix-up adds ceremony without safety. Delete it, or keep only a type alias when the label genuinely helps a reader.

**Haskell**

```haskell
import Data.Text (Text)

-- Before: newtype ArgumentName = ArgumentName { unArgumentName :: Text }
--           deriving (Show, Eq, Ord, ...a dozen more...)
-- Every use site immediately unwraps it; the field name already says "argument".

type ArgumentName = Text -- after: a label for readers, honest about being one

data Argument = Argument {argumentName :: ArgumentName, argumentValue :: Int}
```

**TypeScript**

```typescript
// Before: class ArgumentName { constructor(readonly value: string) {} }
// ...with `.value` at every use site and no invariant anywhere.

type ArgumentName = string; // after

export type Argument = { readonly argumentName: ArgumentName; readonly argumentValue: number };
```

**C++**

```cpp
#include <string>

// Before: struct ArgumentName { std::string value; };  // .value at every use site
using ArgumentName = std::string;  // after

struct Argument {
  ArgumentName argumentName;
  int argumentValue;
};
```

## 5. An alias that hides a container: the multilingual name

`type PermissionName = Multilingual NonEmptyString` welds a domain concept to one container. Any other alias of the same type is interchangeable with it. Once you pick a language, the value is a bare string again. A name in only one language, such as the one a user typed, has no type at all. The fix is to make the concept a type and choose the container at each use site.

**Haskell**

```haskell
{-# LANGUAGE DeriveTraversable #-}
{-# LANGUAGE DerivingStrategies #-}
import Data.List (find)
import Data.List.NonEmpty (NonEmpty)
import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map

type NonEmptyString = NonEmpty Char -- fine: the name restates the right-hand side

data Lang = En | De | Fa deriving stock (Eq, Ord, Show)

-- One reusable container for anything translatable.
data Multilingual a = Multilingual {fallback :: a, translations :: Map Lang a}
  deriving stock (Show, Functor, Foldable, Traversable)

localize :: Lang -> Multilingual a -> a
localize lang m = Map.findWithDefault (fallback m) lang (translations m)

-- Before:
--   type PermissionName = Multilingual NonEmptyString
--   type RoleName = Multilingual NonEmptyString -- the same type: they swap silently
-- and the name a user typed, in one language, is a bare NonEmptyString.

-- After: the concept is a type; the container is chosen where it is used.
newtype PermissionName = PermissionName NonEmptyString deriving stock (Eq, Show)
newtype RoleName = RoleName NonEmptyString deriving stock (Eq, Show)

data Permission = Permission {permissionName :: Multilingual PermissionName}
data Role = Role {roleName :: Multilingual RoleName, rolePermissions :: [Permission]}

-- A name in one language is still a PermissionName, never a RoleName.
findPermission :: Lang -> PermissionName -> [Permission] -> Maybe Permission
findPermission lang name = find ((== name) . localize lang . permissionName)
```

**TypeScript**

```typescript
type Lang = "en" | "de" | "fa";

// One reusable container for anything translatable.
type Multilingual<T> = { readonly fallback: T; readonly translations: Partial<Record<Lang, T>> };

const localize = <T,>(lang: Lang, m: Multilingual<T>): T => m.translations[lang] ?? m.fallback;

// Before:
//   type PermissionName = Multilingual<string>;
//   type RoleName = Multilingual<string>; // the same type: they swap silently
// and the name a user typed, in one language, is a bare string.

// After: the concept is a type; the container is chosen where it is used.
type PermissionName = string & { readonly __brand: "PermissionName" };
type RoleName = string & { readonly __brand: "RoleName" };

interface Permission { readonly name: Multilingual<PermissionName> }
export interface Role { readonly name: Multilingual<RoleName>; readonly permissions: readonly Permission[] }

// A name in one language is still a PermissionName, never a RoleName.
export const findPermission = (lang: Lang, name: PermissionName, ps: readonly Permission[]) =>
  ps.find((p) => localize(lang, p.name) === name);

// findPermission("en", someRoleName, ps); // error: RoleName is not PermissionName
```

**C++**

```cpp
#include <algorithm>
#include <map>
#include <optional>
#include <string>
#include <vector>

enum class Lang { En, De, Fa };

// One reusable container for anything translatable.
template <typename T>
struct Multilingual {
  T fallback;
  std::map<Lang, T> translations;
};

template <typename T>
const T& localize(Lang lang, const Multilingual<T>& m) {
  auto it = m.translations.find(lang);
  return it == m.translations.end() ? m.fallback : it->second;
}

// Before:
//   using PermissionName = Multilingual<std::string>;
//   using RoleName = Multilingual<std::string>;  // the same type: they swap silently
// and the name a user typed, in one language, is a bare std::string.

// After: the concept is a type; the container is chosen where it is used.
struct PermissionName {
  std::string value;
  bool operator==(const PermissionName&) const = default;
};
struct RoleName {
  std::string value;
  bool operator==(const RoleName&) const = default;
};

struct Permission { Multilingual<PermissionName> name; };
struct Role { Multilingual<RoleName> name; std::vector<Permission> permissions; };

// A name in one language is still a PermissionName, never a RoleName.
std::optional<Permission> findPermission(Lang lang, const PermissionName& name,
                                         const std::vector<Permission>& ps) {
  auto it = std::ranges::find_if(ps, [&](const Permission& p) { return localize(lang, p.name) == name; });
  if (it == ps.end()) return std::nullopt;
  return *it;
}
```

## 6. Instances and overloads on an alias belong to the underlying type

Behavior cannot be attached to an alias. An instance or overload written "for" it is really for the right-hand side, so every other alias of that type shares it.

**Haskell**

```haskell
{-# LANGUAGE FlexibleInstances #-}
import Data.List.NonEmpty (NonEmpty)

class Describe a where
  describe :: a -> String

type PermissionName = NonEmpty Char
type RoleName = NonEmpty Char

-- Reads as an instance for permission names; it is `instance Describe (NonEmpty Char)`.
instance Describe PermissionName where
  describe _ = "a permission"

-- instance Describe RoleName where ... -- error: duplicate instance declarations

oops :: RoleName -> String
oops = describe -- compiles, and calls a role "a permission"
```

An alias instance also overlaps the container's general instance. Without a pragma, every use is an "Overlapping instances" error. With `OVERLAPPING`, generic code over `Multilingual a` stops compiling. With `INCOHERENT`, it compiles, and the answer depends on where the type becomes known:

```haskell
{-# LANGUAGE FlexibleInstances #-}
import Data.List.NonEmpty (NonEmpty ((:|)))
import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map

data Lang = En | De deriving (Eq, Ord, Show)

data Multilingual a = Multilingual {fallback :: a, translations :: Map Lang a}

class Describe a where
  describe :: a -> String

instance Describe Char where
  describe c = [c]

instance Describe a => Describe (NonEmpty a) where
  describe = concatMap describe

instance Describe a => Describe (Multilingual a) where
  describe m = "translated: " <> describe (fallback m)

type PermissionName = Multilingual (NonEmpty Char)

-- Overlaps the instance above. Without a pragma, `describe p` is an error;
-- with OVERLAPPING, `describeAll` below is an error; INCOHERENT compiles.
instance {-# INCOHERENT #-} Describe PermissionName where
  describe _ = "a permission"

describeAll :: Describe a => [Multilingual a] -> [String]
describeAll = map describe

main :: IO ()
main = do
  let p = Multilingual ('r' :| "ead") Map.empty :: PermissionName
  print (describe p) -- "a permission"
  print (describeAll [p]) -- ["translated: read"]: same value, other instance
```

With newtypes, each concept gets its own instance, and `Multilingual PermissionName` uses the general instance, which calls `PermissionName`'s. Nothing overlaps:

```haskell
{-# LANGUAGE DerivingStrategies #-}
{-# LANGUAGE GeneralizedNewtypeDeriving #-}
import Data.List.NonEmpty (NonEmpty)

class Describe a where
  describe :: a -> String

newtype PermissionName = PermissionName (NonEmpty Char) deriving newtype (Eq, Show)
newtype RoleName = RoleName (NonEmpty Char) deriving newtype (Eq, Show)

instance Describe PermissionName where
  describe _ = "a permission"

instance Describe RoleName where
  describe _ = "a role"
```

**TypeScript**

```typescript
type Meters = number;
type Seconds = number;

// Two overloads that read differently but have the same signature: (x: number) => string.
function format(x: Meters): string;
function format(x: Seconds): string;
function format(x: number): string {
  return `${x}`; // nothing tells the implementation which one the caller meant
}

export const ambiguous = format(3); // 3 m or 3 s? Neither the checker nor the code knows.

// Brands are erased at runtime, so to dispatch, carry the distinction in the value.
type Quantity = { readonly unit: "m"; readonly value: number } | { readonly unit: "s"; readonly value: number };

export const formatQuantity = (q: Quantity): string => `${q.value} ${q.unit}`;
```

**C++**

```cpp
#include <string>

namespace alias {
using Meters = double;
using Seconds = double;

inline std::string format(Meters m) { return std::to_string(m) + " m"; }
// inline std::string format(Seconds s) { ... }  // error: redefinition of format (both take a double)
}  // namespace alias

namespace strong {
struct Meters { double value; };
struct Seconds { double value; };

inline std::string format(Meters m) { return std::to_string(m.value) + " m"; }
inline std::string format(Seconds s) { return std::to_string(s.value) + " s"; }  // a real overload
}  // namespace strong
```
