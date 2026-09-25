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
