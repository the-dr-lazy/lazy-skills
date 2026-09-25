# Make illegal states unrepresentable — worked examples

Each example is given in Haskell, TypeScript, and C++. Each block is self-contained.

## 1. The flat "before" model

A tag plus optional fields: the type admits a `Connecting` connection with a disconnection time, a ping time without a ping id, and so on. These invariants live only in comments, so every consumer must remember them.

**Haskell**

```haskell
import Data.Time (UTCTime)

data StateTag = TagConnecting | TagConnected | TagDisconnected

data ConnectionInfoFlat = ConnectionInfoFlat
  { stateTag :: StateTag
  , server :: String
  , lastPingTime :: Maybe UTCTime -- only when connected, and only with lastPingId
  , lastPingId :: Maybe Int -- only when connected, and only with lastPingTime
  , sessionId :: Maybe String -- only when connected
  , whenInitiated :: Maybe UTCTime -- only when connecting
  , whenDisconnected :: Maybe UTCTime -- only when disconnected
  }
```

**TypeScript**

```typescript
type ConnectionInfoFlat = {
  state: "connecting" | "connected" | "disconnected";
  server: string;
  lastPingTime?: Date; // only when connected, and only with lastPingId
  lastPingId?: number; // only when connected, and only with lastPingTime
  sessionId?: string; // only when connected
  whenInitiated?: Date; // only when connecting
  whenDisconnected?: Date; // only when disconnected
};

export const illegal: ConnectionInfoFlat = {
  state: "connecting",
  server: "db-1",
  whenDisconnected: new Date(), // compiles, means nothing
};
```

**C++**

```cpp
#include <chrono>
#include <optional>
#include <string>

using Time = std::chrono::system_clock::time_point;
enum class StateTag { Connecting, Connected, Disconnected };

struct ConnectionInfoFlat {
  StateTag state;
  std::string server;
  std::optional<Time> lastPingTime;      // only when connected, and only with lastPingId
  std::optional<int> lastPingId;         // only when connected, and only with lastPingTime
  std::optional<std::string> sessionId;  // only when connected
  std::optional<Time> whenInitiated;     // only when connecting
  std::optional<Time> whenDisconnected;  // only when disconnected
};
```

The refactored sum-of-products version is in [SKILL.md](SKILL.md).

## 2. Business rules as types: contact information (after Wlaschin)

Rule 1: *a contact must have an email or a postal address.* Two optional fields admit "neither"; the rule has exactly three cases. Rule 2 adds phones and becomes 15 combinations — until the domain insight arrives: a contact has a list of **contact methods**, and "at least one" means a required primary plus optional secondaries.

**Haskell**

```haskell
newtype EmailAddress = EmailAddress String
newtype PostalAddress = PostalAddress String
newtype PhoneNumber = PhoneNumber String

-- Rule 1
data ContactInfo
  = EmailOnly EmailAddress
  | PostOnly PostalAddress
  | EmailAndPost EmailAddress PostalAddress

updatePostalAddress :: PostalAddress -> ContactInfo -> ContactInfo
updatePostalAddress new info = case info of
  EmailOnly email -> EmailAndPost email new
  PostOnly _ -> PostOnly new
  EmailAndPost email _ -> EmailAndPost email new

-- Rule 2, after discovering the ContactMethod concept
data ContactMethod
  = Email EmailAddress
  | Post PostalAddress
  | HomePhone PhoneNumber
  | WorkPhone PhoneNumber

data Contact = Contact
  { name :: String
  , primaryContact :: ContactMethod
  , secondaryContacts :: [ContactMethod]
  }

describe :: ContactMethod -> String -- adding a method breaks this match, not silently a report
describe (Email (EmailAddress e)) = "email " <> e
describe (Post (PostalAddress p)) = "post " <> p
describe (HomePhone (PhoneNumber n)) = "home " <> n
describe (WorkPhone (PhoneNumber n)) = "work " <> n
```

**TypeScript**

```typescript
type EmailAddress = { readonly email: string };
type PostalAddress = { readonly lines: readonly string[] };
type PhoneNumber = { readonly digits: string };

// Rule 1
type ContactInfo =
  | { readonly kind: "emailOnly"; readonly email: EmailAddress }
  | { readonly kind: "postOnly"; readonly post: PostalAddress }
  | { readonly kind: "emailAndPost"; readonly email: EmailAddress; readonly post: PostalAddress };

export function updatePostalAddress(post: PostalAddress, info: ContactInfo): ContactInfo {
  switch (info.kind) {
    case "emailOnly":
    case "emailAndPost":
      return { kind: "emailAndPost", email: info.email, post };
    case "postOnly":
      return { kind: "postOnly", post };
  }
}

// Rule 2, after discovering the ContactMethod concept
type ContactMethod =
  | { readonly kind: "email"; readonly value: EmailAddress }
  | { readonly kind: "post"; readonly value: PostalAddress }
  | { readonly kind: "homePhone"; readonly value: PhoneNumber }
  | { readonly kind: "workPhone"; readonly value: PhoneNumber };

export type Contact = {
  readonly name: string;
  readonly primaryContact: ContactMethod;
  readonly secondaryContacts: readonly ContactMethod[];
};
```

**C++**

```cpp
#include <string>
#include <variant>
#include <vector>

struct EmailAddress { std::string value; };
struct PostalAddress { std::string value; };
struct PhoneNumber { std::string value; };

// Rule 1
struct EmailOnly { EmailAddress email; };
struct PostOnly { PostalAddress post; };
struct EmailAndPost { EmailAddress email; PostalAddress post; };
using ContactInfo = std::variant<EmailOnly, PostOnly, EmailAndPost>;

template <class... Fs> struct overloaded : Fs... { using Fs::operator()...; };

ContactInfo updatePostalAddress(PostalAddress post, const ContactInfo& info) {
  return std::visit(overloaded{
      [&](const EmailOnly& e) -> ContactInfo { return EmailAndPost{e.email, post}; },
      [&](const PostOnly&) -> ContactInfo { return PostOnly{post}; },
      [&](const EmailAndPost& ep) -> ContactInfo { return EmailAndPost{ep.email, post}; },
  }, info);
}

// Rule 2, after discovering the ContactMethod concept
struct Email { EmailAddress value; };
struct Post { PostalAddress value; };
struct HomePhone { PhoneNumber value; };
struct WorkPhone { PhoneNumber value; };
using ContactMethod = std::variant<Email, Post, HomePhone, WorkPhone>;

struct Contact {
  std::string name;
  ContactMethod primaryContact;               // "at least one" = one required ...
  std::vector<ContactMethod> secondaryContacts;  // ... plus any number more
};
```

## 3. Flags become a state machine: shopping cart

Each state carries only its own data. Each event takes and returns the *whole* machine, so the handling of the event in every state is decided in one place, not by callers. Supporting functions that genuinely need one state (a report over paid carts) take that state's type directly.

**Haskell**

```haskell
import Data.List.NonEmpty (NonEmpty (..), (<|))

type Item = String
newtype Payment = Payment Double

data ShoppingCart
  = EmptyCart
  | ActiveCart (NonEmpty Item) -- an active cart has at least one item
  | PaidCart (NonEmpty Item) Payment

addItem :: Item -> ShoppingCart -> ShoppingCart
addItem item EmptyCart = ActiveCart (item :| [])
addItem item (ActiveCart items) = ActiveCart (item <| items)
addItem _ paid@(PaidCart _ _) = paid -- a paid cart is closed

makePayment :: Payment -> ShoppingCart -> ShoppingCart
makePayment payment (ActiveCart items) = PaidCart items payment
makePayment _ cart = cart -- nothing to pay / already paid

-- A supporting function works on the "raw" state it needs.
paymentReport :: [(NonEmpty Item, Payment)] -> Double
paymentReport paid = sum [amount | (_, Payment amount) <- paid]
```

**TypeScript**

```typescript
type Item = string;
type NonEmptyArray<T> = readonly [T, ...T[]];

type ShoppingCart =
  | { readonly state: "empty" }
  | { readonly state: "active"; readonly items: NonEmptyArray<Item> }
  | { readonly state: "paid"; readonly items: NonEmptyArray<Item>; readonly payment: number };

export function addItem(item: Item, cart: ShoppingCart): ShoppingCart {
  switch (cart.state) {
    case "empty":
      return { state: "active", items: [item] };
    case "active":
      return { state: "active", items: [item, ...cart.items] };
    case "paid":
      return cart;
  }
}

export function makePayment(payment: number, cart: ShoppingCart): ShoppingCart {
  return cart.state === "active" ? { state: "paid", items: cart.items, payment } : cart;
}

type PaidCart = Extract<ShoppingCart, { state: "paid" }>;
export const paymentReport = (paid: readonly PaidCart[]): number =>
  paid.reduce((sum, c) => sum + c.payment, 0);
```

**C++**

```cpp
#include <string>
#include <type_traits>
#include <variant>
#include <vector>

using Item = std::string;

struct EmptyCart {};
struct ActiveCart { Item first; std::vector<Item> more; };  // at least one item
struct PaidCart { Item first; std::vector<Item> more; double payment; };
using ShoppingCart = std::variant<EmptyCart, ActiveCart, PaidCart>;

ShoppingCart addItem(const Item& item, const ShoppingCart& cart) {
  return std::visit([&](const auto& c) -> ShoppingCart {
    using C = std::decay_t<decltype(c)>;
    if constexpr (std::is_same_v<C, EmptyCart>) return ActiveCart{item, {}};
    else if constexpr (std::is_same_v<C, ActiveCart>) {
      ActiveCart next = c;
      next.more.push_back(item);
      return next;
    } else return c;  // a paid cart is closed
  }, cart);
}

ShoppingCart makePayment(double payment, const ShoppingCart& cart) {
  if (auto* active = std::get_if<ActiveCart>(&cart))
    return PaidCart{active->first, active->more, payment};
  return cart;
}

double paymentReport(const std::vector<PaidCart>& paid) {
  double sum = 0;
  for (const auto& c : paid) sum += c.payment;
  return sum;
}
```

The same move turns an `Order` with `PaidDate`, `ShippedDate`, `ReturnedDate` options into `Unpaid | Paid | Shipped | Returned`, each case carrying the data accumulated so far.

## 4. Choose the structure: time series

A list of `(time, value)` pairs admits out-of-order, duplicate, and contradictory samples, and every consumer must agree how to treat them. A map makes contradictions inexpressible. A function from time to optional value also makes every *legal* series representable — including a constant series that no finite list can hold. The one place that still sees lists is the parse step at the boundary.

**Haskell**

```haskell
import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map

type Time = Integer -- e.g. epoch milliseconds

newtype TimeSeries = TimeSeries {valueAt :: Time -> Maybe Double}

fromMap :: Map Time Double -> TimeSeries
fromMap m = TimeSeries (`Map.lookup` m)

constant :: Double -> TimeSeries
constant x = TimeSeries (const (Just x))

-- The anti-corruption layer: the only code that sees the permissive format.
-- Later samples win, so the result is total and deterministic.
parseSamples :: [(Time, Double)] -> Map Time Double
parseSamples = Map.fromList
```

**TypeScript**

```typescript
type Time = number; // epoch milliseconds

export type TimeSeries = (t: Time) => number | undefined;

export const fromMap = (m: ReadonlyMap<Time, number>): TimeSeries => (t) => m.get(t);
export const constant = (x: number): TimeSeries => () => x;

// The anti-corruption layer: later samples win.
export const parseSamples = (samples: ReadonlyArray<readonly [Time, number]>): ReadonlyMap<Time, number> =>
  new Map(samples);
```

**C++**

```cpp
#include <cstdint>
#include <functional>
#include <map>
#include <optional>
#include <utility>
#include <vector>

using Time = std::int64_t;  // epoch milliseconds
using TimeSeries = std::function<std::optional<double>(Time)>;

TimeSeries fromMap(std::map<Time, double> m) {
  return [m = std::move(m)](Time t) -> std::optional<double> {
    if (auto it = m.find(t); it != m.end()) return it->second;
    return std::nullopt;
  };
}

TimeSeries constant(double x) {
  return [x](Time) -> std::optional<double> { return x; };
}

// The anti-corruption layer: later samples win.
std::map<Time, double> parseSamples(const std::vector<std::pair<Time, double>>& samples) {
  std::map<Time, double> out;
  for (const auto& [t, v] : samples) out.insert_or_assign(t, v);
  return out;
}
```

## 5. Positive space: build only the valid values

Instead of restricting lists to even length after the fact, define a type whose construction rules can only produce even lengths. Instead of an integer "that must not be negative", define naturals by the Peano axioms. Pragmatically, reuse an existing structure (a list of pairs) when you can.

**Haskell**

```haskell
data EvenList a = EvenNil | EvenCons a a (EvenList a)

type EvenList' a = [(a, a)] -- the pragmatic encoding: reuse lists

toList :: EvenList a -> [a]
toList EvenNil = []
toList (EvenCons x y rest) = x : y : toList rest

data Natural = Zero | Succ Natural

toInteger' :: Natural -> Integer
toInteger' Zero = 0
toInteger' (Succ n) = 1 + toInteger' n
```

**TypeScript**

```typescript
export type EvenList<T> = readonly [] | readonly [T, T, EvenList<T>];
export type EvenList2<T> = ReadonlyArray<readonly [T, T]>; // the pragmatic encoding

export type Natural = "zero" | { readonly succ: Natural };

export const toNumber = (n: Natural): number => (n === "zero" ? 0 : 1 + toNumber(n.succ));

export const two: Natural = { succ: { succ: "zero" } };
export const pairs: EvenList<string> = ["a", "b", ["c", "d", []]];
```

**C++**

```cpp
#include <memory>
#include <utility>
#include <variant>
#include <vector>

template <typename T>
using EvenList = std::vector<std::pair<T, T>>;  // the pragmatic encoding

struct Zero {};
struct Succ;
using Natural = std::variant<Zero, std::shared_ptr<const Succ>>;
struct Succ { Natural pred; };

Natural succ(Natural n) { return std::make_shared<const Succ>(Succ{std::move(n)}); }

unsigned toUnsigned(const Natural& n) {
  if (std::holds_alternative<Zero>(n)) return 0;
  return 1 + toUnsigned(std::get<std::shared_ptr<const Succ>>(n)->pred);
}
```
