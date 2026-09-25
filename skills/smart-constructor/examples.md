# Smart constructor — worked examples

Each example is given in Haskell, TypeScript, and C++. Each block is self-contained.

## 1. One helper for all constrained strings

`create canonicalize isValid wrap` captures the whole pattern; each new type is then a one-liner (after Wlaschin's `WrappedString`).

**Haskell**

```haskell
module Wrapped (String50, String100, ZipCode, StateCode, string50, string100, zipCode, stateCode, value) where

import Data.Char (isDigit, isSpace, toUpper)

class Wrapped a where
  value :: a -> String

create :: (String -> String) -> (String -> Bool) -> (String -> a) -> String -> Maybe a
create canonicalize isValid wrap raw =
  let s = canonicalize raw in if isValid s then Just (wrap s) else Nothing

singleLineTrimmed :: String -> String
singleLineTrimmed = trim . map (\c -> if isSpace c then ' ' else c)
  where trim = reverse . dropWhile (== ' ') . reverse . dropWhile (== ' ')

newtype String50 = String50 String deriving (Eq, Ord, Show)
newtype String100 = String100 String deriving (Eq, Ord, Show)
newtype ZipCode = ZipCode String deriving (Eq, Ord, Show)
newtype StateCode = StateCode String deriving (Eq, Ord, Show)

instance Wrapped String50 where value (String50 s) = s
instance Wrapped String100 where value (String100 s) = s
instance Wrapped ZipCode where value (ZipCode s) = s
instance Wrapped StateCode where value (StateCode s) = s

string50 :: String -> Maybe String50
string50 = create singleLineTrimmed ((<= 50) . length) String50

string100 :: String -> Maybe String100
string100 = create singleLineTrimmed ((<= 100) . length) String100

zipCode :: String -> Maybe ZipCode
zipCode = create singleLineTrimmed (\s -> length s == 5 && all isDigit s) ZipCode

stateCode :: String -> Maybe StateCode
stateCode = create (map toUpper . singleLineTrimmed) (`elem` ["AZ", "CA", "NY"]) StateCode
```

**TypeScript**

```typescript
const create =
  <T,>(canonicalize: (s: string) => string, isValid: (s: string) => boolean, wrap: (s: string) => T) =>
  (raw: string): T | undefined => {
    const s = canonicalize(raw);
    return isValid(s) ? wrap(s) : undefined;
  };

const singleLineTrimmed = (s: string) => s.replace(/\s/g, " ").trim();

// A class per type keeps construction private; the helper keeps it one line.
class Wrapped<Tag extends string> {
  readonly #value: string;
  protected constructor(value: string, readonly tag: Tag) {
    this.#value = value;
  }
  get value(): string {
    return this.#value;
  }
}

export class String50 extends Wrapped<"String50"> {
  private constructor(s: string) { super(s, "String50"); }
  static create = create(singleLineTrimmed, (s) => s.length <= 50, (s) => new String50(s));
}

export class ZipCode extends Wrapped<"ZipCode"> {
  private constructor(s: string) { super(s, "ZipCode"); }
  static create = create(singleLineTrimmed, (s) => /^\d{5}$/.test(s), (s) => new ZipCode(s));
}

export class StateCode extends Wrapped<"StateCode"> {
  private constructor(s: string) { super(s, "StateCode"); }
  static create = create(
    (s) => singleLineTrimmed(s).toUpperCase(),
    (s) => ["AZ", "CA", "NY"].includes(s),
    (s) => new StateCode(s),
  );
}
```

**C++**

```cpp
#include <algorithm>
#include <cctype>
#include <optional>
#include <string>
#include <utility>

template <typename Tag>
class Wrapped {
public:
  template <typename Canon, typename Valid>
  static std::optional<Wrapped> create(std::string raw, Canon canonicalize, Valid isValid) {
    std::string s = canonicalize(std::move(raw));
    if (!isValid(s)) return std::nullopt;
    return Wrapped(std::move(s));
  }
  const std::string& value() const { return value_; }
  bool operator==(const Wrapped&) const = default;
private:
  explicit Wrapped(std::string s) : value_(std::move(s)) {}
  std::string value_;
};

inline std::string singleLineTrimmed(std::string s) {
  std::replace_if(s.begin(), s.end(), [](unsigned char c) { return std::isspace(c); }, ' ');
  auto first = s.find_first_not_of(' ');
  if (first == std::string::npos) return "";
  return s.substr(first, s.find_last_not_of(' ') - first + 1);
}

using String50 = Wrapped<struct String50Tag>;
using ZipCode = Wrapped<struct ZipCodeTag>;

inline std::optional<String50> string50(std::string raw) {
  return String50::create(std::move(raw), singleLineTrimmed,
                          [](const std::string& s) { return s.size() <= 50; });
}

inline std::optional<ZipCode> zipCode(std::string raw) {
  return ZipCode::create(std::move(raw), singleLineTrimmed, [](const std::string& s) {
    return s.size() == 5 && std::all_of(s.begin(), s.end(), [](unsigned char c) { return std::isdigit(c); });
  });
}
```

## 2. Let the caller choose the failure channel

A constructor that takes `success` and `failure` continuations can reproduce `Maybe`, `Either`, and exceptions. Partially apply it once per call site style.

**Haskell**

```haskell
newtype EmailAddress = EmailAddress String deriving (Show)

createWithCont :: (EmailAddress -> r) -> (String -> r) -> String -> r
createWithCont success failure s
  | '@' `elem` s = success (EmailAddress s)
  | otherwise = failure "email address must contain an @ sign"

createMaybe :: String -> Maybe EmailAddress
createMaybe = createWithCont Just (const Nothing)

createEither :: String -> Either String EmailAddress
createEither = createWithCont Right Left

createOrDie :: String -> EmailAddress
createOrDie = createWithCont id error -- only at a boundary that may crash
```

**TypeScript**

```typescript
export class EmailAddress {
  private constructor(readonly value: string) {}
  static createWithCont<R>(success: (e: EmailAddress) => R, failure: (msg: string) => R, s: string): R {
    return s.includes("@") ? success(new EmailAddress(s)) : failure("email address must contain an @ sign");
  }
}

export const createOptional = (s: string) =>
  EmailAddress.createWithCont<EmailAddress | undefined>((e) => e, () => undefined, s);

export const createOrThrow = (s: string) =>
  EmailAddress.createWithCont<EmailAddress>(
    (e) => e,
    (msg) => {
      throw new Error(msg);
    },
    s,
  );
```

**C++**

```cpp
#include <expected>
#include <optional>
#include <stdexcept>
#include <string>

class EmailAddress {
public:
  template <typename Success, typename Failure>
  static auto createWithCont(Success success, Failure failure, std::string s) {
    return s.find('@') != std::string::npos ? success(EmailAddress(std::move(s)))
                                            : failure(std::string("email address must contain an @ sign"));
  }
  const std::string& value() const { return value_; }
private:
  explicit EmailAddress(std::string v) : value_(std::move(v)) {}
  std::string value_;
};

std::optional<EmailAddress> createOptional(std::string s) {
  return EmailAddress::createWithCont(
      [](EmailAddress e) { return std::optional<EmailAddress>(std::move(e)); },
      [](const std::string&) { return std::optional<EmailAddress>(); }, std::move(s));
}

std::expected<EmailAddress, std::string> createExpected(std::string s) {
  return EmailAddress::createWithCont(
      [](EmailAddress e) { return std::expected<EmailAddress, std::string>(std::move(e)); },
      [](std::string msg) { return std::expected<EmailAddress, std::string>(std::unexpected(std::move(msg))); },
      std::move(s));
}
```

## 3. Numbers and dates carry business rules too

A cart quantity is not an `int`: it is 1–99. With the constraint in the type, the classic "decrement below zero" bug has nowhere to hide — `decrement` has to say what happens at the bottom.

**Haskell**

```haskell
module Quantity (Quantity, mkQuantity, quantity, increment, decrement, SafeDate, mkSafeDate) where

import Data.Time.Calendar (Day, fromGregorian)

newtype Quantity = Quantity Int deriving (Eq, Ord, Show)

mkQuantity :: Int -> Maybe Quantity
mkQuantity n
  | n > 0 && n < 100 = Just (Quantity n)
  | otherwise = Nothing

quantity :: Quantity -> Int
quantity (Quantity n) = n

increment, decrement :: Quantity -> Maybe Quantity
increment (Quantity n) = mkQuantity (n + 1)
decrement (Quantity n) = mkQuantity (n - 1) -- Nothing at 1: the caller must decide

newtype SafeDate = SafeDate Day deriving (Eq, Ord, Show)

mkSafeDate :: Day -> Maybe SafeDate
mkSafeDate d
  | d >= fromGregorian 1980 1 1 && d <= fromGregorian 2038 1 1 = Just (SafeDate d)
  | otherwise = Nothing
```

**TypeScript**

```typescript
export class Quantity {
  private constructor(readonly value: number) {}
  static create(n: number): Quantity | undefined {
    return Number.isInteger(n) && n > 0 && n < 100 ? new Quantity(n) : undefined;
  }
  increment(): Quantity | undefined {
    return Quantity.create(this.value + 1);
  }
  decrement(): Quantity | undefined {
    return Quantity.create(this.value - 1); // undefined at 1: the caller must decide
  }
}

export class SafeDate {
  private constructor(readonly value: Date) {}
  static create(d: Date): SafeDate | undefined {
    const min = Date.UTC(1980, 0, 1);
    const max = Date.UTC(2038, 0, 1);
    return d.getTime() >= min && d.getTime() <= max ? new SafeDate(new Date(d)) : undefined;
  }
}
```

**C++**

```cpp
#include <chrono>
#include <optional>

class Quantity {
public:
  static std::optional<Quantity> create(int n) {
    if (n <= 0 || n >= 100) return std::nullopt;
    return Quantity(n);
  }
  int value() const { return n_; }
  std::optional<Quantity> increment() const { return create(n_ + 1); }
  std::optional<Quantity> decrement() const { return create(n_ - 1); }  // nullopt at 1
private:
  explicit Quantity(int n) : n_(n) {}
  int n_;
};

class SafeDate {
public:
  static std::optional<SafeDate> create(std::chrono::year_month_day d) {
    using namespace std::chrono;
    if (d < year{1980} / January / 1 || d > year{2038} / January / 1) return std::nullopt;
    return SafeDate(d);
  }
  std::chrono::year_month_day value() const { return d_; }
private:
  explicit SafeDate(std::chrono::year_month_day d) : d_(d) {}
  std::chrono::year_month_day d_;
};
```

## 4. Construct at the boundary, not in the UI's own `if`

The UI calls the constructor and reacts to its result; it does not duplicate the rule. The domain receives only the opaque value.

**Haskell**

```haskell
newtype EmailAddress = EmailAddress String

mkEmailAddress :: String -> Either String EmailAddress
mkEmailAddress s
  | '@' `elem` s && length s <= 100 = Right (EmailAddress s)
  | otherwise = Left "please enter a valid email address"

newtype Customer = Customer {customerEmail :: EmailAddress}

-- Boundary: raw text in, either a domain value or a message for the form.
submitForm :: String -> Either String Customer
submitForm rawEmail = Customer <$> mkEmailAddress rawEmail
```

**TypeScript**

```typescript
class EmailAddress {
  private constructor(readonly value: string) {}
  static create(s: string): EmailAddress | string {
    return s.includes("@") && s.length <= 100 ? new EmailAddress(s) : "please enter a valid email address";
  }
}

type Customer = { readonly email: EmailAddress };

export function submitForm(rawEmail: string, showError: (msg: string) => void): Customer | undefined {
  const email = EmailAddress.create(rawEmail);
  if (typeof email === "string") {
    showError(email);
    return undefined;
  }
  return { email };
}
```

**C++**

```cpp
#include <expected>
#include <string>

class EmailAddress {
public:
  static std::expected<EmailAddress, std::string> create(std::string s) {
    if (s.find('@') == std::string::npos || s.size() > 100)
      return std::unexpected(std::string("please enter a valid email address"));
    return EmailAddress(std::move(s));
  }
  const std::string& value() const { return v_; }
private:
  explicit EmailAddress(std::string v) : v_(std::move(v)) {}
  std::string v_;
};

struct Customer { EmailAddress email; };

std::expected<Customer, std::string> submitForm(std::string rawEmail) {
  return EmailAddress::create(std::move(rawEmail)).transform([](EmailAddress e) { return Customer{std::move(e)}; });
}
```

## 5. Property tests for the trusted module

Because the guarantee is extrinsic, test the constructor itself: whatever it accepts satisfies the invariant, and canonicalization is idempotent.

**Haskell**

```haskell
import Data.Char (isSpace, toUpper)
import Test.QuickCheck

newtype StateCode = StateCode String deriving (Eq, Show)

canonicalize :: String -> String
canonicalize = map toUpper . filter (not . isSpace)

mkStateCode :: String -> Maybe StateCode
mkStateCode raw = let s = canonicalize raw in if s `elem` ["AZ", "CA", "NY"] then Just (StateCode s) else Nothing

prop_acceptedValuesAreValid :: String -> Bool
prop_acceptedValuesAreValid raw = case mkStateCode raw of
  Nothing -> True
  Just (StateCode s) -> length s == 2 && all (`elem` ['A' .. 'Z']) s

prop_canonicalizeIdempotent :: String -> Bool
prop_canonicalizeIdempotent s = canonicalize (canonicalize s) == canonicalize s

prop_roundTrip :: Property
prop_roundTrip = forAll (elements ["az", " ca ", "Ny"]) $ \raw ->
  case mkStateCode raw of
    Just code@(StateCode s) -> mkStateCode s === Just code
    Nothing -> property False

main :: IO ()
main = quickCheck prop_acceptedValuesAreValid >> quickCheck prop_canonicalizeIdempotent >> quickCheck prop_roundTrip
```

**TypeScript**

```typescript
import fc from "fast-check";

const canonicalize = (s: string) => s.replace(/\s/g, "").toUpperCase();
const mkStateCode = (raw: string): string | undefined => {
  const s = canonicalize(raw);
  return ["AZ", "CA", "NY"].includes(s) ? s : undefined;
};

fc.assert(
  fc.property(fc.string(), (raw) => {
    const code = mkStateCode(raw);
    return code === undefined || /^[A-Z]{2}$/.test(code);
  }),
);

fc.assert(fc.property(fc.string(), (s) => canonicalize(canonicalize(s)) === canonicalize(s)));

fc.assert(
  fc.property(fc.constantFrom("az", " ca ", "Ny"), (raw) => {
    const code = mkStateCode(raw);
    return code !== undefined && mkStateCode(code) === code;
  }),
);
```

**C++**

```cpp
#include <rapidcheck.h>

#include <algorithm>
#include <cctype>
#include <optional>
#include <string>

std::string canonicalize(std::string s) {
  s.erase(std::remove_if(s.begin(), s.end(), [](unsigned char c) { return std::isspace(c); }), s.end());
  std::transform(s.begin(), s.end(), s.begin(), [](unsigned char c) { return static_cast<char>(std::toupper(c)); });
  return s;
}

std::optional<std::string> mkStateCode(const std::string& raw) {
  auto s = canonicalize(raw);
  if (s == "AZ" || s == "CA" || s == "NY") return s;
  return std::nullopt;
}

int main() {
  rc::check("accepted values are valid", [](const std::string& raw) {
    auto code = mkStateCode(raw);
    RC_ASSERT(!code || (code->size() == 2 && std::all_of(code->begin(), code->end(), ::isupper)));
  });
  rc::check("canonicalize is idempotent", [](const std::string& s) {
    RC_ASSERT(canonicalize(canonicalize(s)) == canonicalize(s));
  });
}
```
