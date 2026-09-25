# Designing with types — worked examples

Each example is given in Haskell, TypeScript, and C++. Each block is self-contained.

## 1. Steps 1–2: atomic groups and explicit optionality

**Haskell**

```haskell
-- Before
data ContactFlat = ContactFlat
  { firstName, middleInitial, lastName :: String
  , emailAddress :: String
  , isEmailVerified :: Bool -- true if ownership of email address is confirmed
  , address1, address2, city, state, zip :: String
  , isAddressValid :: Bool -- true if validated against address service
  }

-- After: groups that change together, optionality in the type
data PersonalName = PersonalName {first :: String, middle :: Maybe String, lastN :: String}

data EmailContactInfo = EmailContactInfo {email :: String, verified :: Bool}

data PostalAddress = PostalAddress
  {line1 :: String, line2 :: Maybe String, cityName :: String, stateCode :: String, zipCode :: String}

data PostalContactInfo = PostalContactInfo {postal :: PostalAddress, valid :: Bool}

data Contact = Contact
  {name :: PersonalName, emailInfo :: EmailContactInfo, postalInfo :: PostalContactInfo}

-- Changing the address and resetting its flag is now one update of one group.
changeAddress :: PostalAddress -> Contact -> Contact
changeAddress a c = c {postalInfo = PostalContactInfo a False}
```

**TypeScript**

```typescript
// Before
type ContactFlat = {
  firstName: string; middleInitial: string; lastName: string;
  emailAddress: string; isEmailVerified: boolean;
  address1: string; address2: string; city: string; state: string; zip: string;
  isAddressValid: boolean;
};

// After
type PersonalName = { readonly first: string; readonly middle: string | null; readonly last: string };
type EmailContactInfo = { readonly email: string; readonly verified: boolean };
type PostalAddress = {
  readonly line1: string; readonly line2: string | null;
  readonly city: string; readonly state: string; readonly zip: string;
};
type PostalContactInfo = { readonly address: PostalAddress; readonly valid: boolean };
type Contact = {
  readonly name: PersonalName;
  readonly emailInfo: EmailContactInfo;
  readonly postalInfo: PostalContactInfo;
};

export const changeAddress = (address: PostalAddress, c: Contact): Contact => ({
  ...c,
  postalInfo: { address, valid: false },
});
export type { ContactFlat };
```

**C++**

```cpp
#include <optional>
#include <string>

// Before
struct ContactFlat {
  std::string firstName, middleInitial, lastName;
  std::string emailAddress;
  bool isEmailVerified;
  std::string address1, address2, city, state, zip;
  bool isAddressValid;
};

// After
struct PersonalName { std::string first; std::optional<std::string> middle; std::string last; };
struct EmailContactInfo { std::string email; bool verified; };
struct PostalAddress {
  std::string line1;
  std::optional<std::string> line2;
  std::string city, state, zip;
};
struct PostalContactInfo { PostalAddress address; bool valid; };
struct Contact { PersonalName name; EmailContactInfo emailInfo; PostalContactInfo postalInfo; };

Contact changeAddress(PostalAddress a, Contact c) {
  c.postalInfo = PostalContactInfo{std::move(a), false};
  return c;
}
```

## 2. Step 6: a flag becomes a state machine (email verification)

Business rules: *verification emails go only to unverified addresses; password resets only to verified ones.* Construction always yields an unverified address; the only transition is "verified".

**Haskell**

```haskell
import Data.Time (UTCTime)

newtype EmailAddress = EmailAddress String

data EmailContactInfo
  = Unverified EmailAddress
  | Verified EmailAddress UTCTime

create :: EmailAddress -> EmailContactInfo
create = Unverified

verified :: UTCTime -> EmailContactInfo -> EmailContactInfo
verified at (Unverified e) = Verified e at
verified _ info@(Verified _ _) = info -- verifying twice changes nothing

sendVerificationEmail :: (EmailAddress -> IO ()) -> EmailContactInfo -> IO ()
sendVerificationEmail send (Unverified e) = send e
sendVerificationEmail _ (Verified _ _) = pure ()

sendPasswordReset :: (EmailAddress -> IO ()) -> EmailContactInfo -> IO ()
sendPasswordReset send (Verified e _) = send e
sendPasswordReset _ (Unverified _) = pure ()
```

**TypeScript**

```typescript
type EmailAddress = string;

type EmailContactInfo =
  | { readonly state: "unverified"; readonly email: EmailAddress }
  | { readonly state: "verified"; readonly email: EmailAddress; readonly verifiedAt: Date };

export const create = (email: EmailAddress): EmailContactInfo => ({ state: "unverified", email });

export const verified = (at: Date, info: EmailContactInfo): EmailContactInfo =>
  info.state === "unverified" ? { state: "verified", email: info.email, verifiedAt: at } : info;

export function sendVerificationEmail(send: (e: EmailAddress) => void, info: EmailContactInfo): void {
  if (info.state === "unverified") send(info.email);
}

export function sendPasswordReset(send: (e: EmailAddress) => void, info: EmailContactInfo): void {
  if (info.state === "verified") send(info.email);
}
```

**C++**

```cpp
#include <chrono>
#include <functional>
#include <string>
#include <variant>

using EmailAddress = std::string;
using Time = std::chrono::system_clock::time_point;

struct Unverified { EmailAddress email; };
struct Verified { EmailAddress email; Time at; };
using EmailContactInfo = std::variant<Unverified, Verified>;

EmailContactInfo create(EmailAddress e) { return Unverified{std::move(e)}; }

EmailContactInfo verified(Time at, const EmailContactInfo& info) {
  if (auto* u = std::get_if<Unverified>(&info)) return Verified{u->email, at};
  return info;  // verifying twice changes nothing
}

void sendVerificationEmail(const std::function<void(const EmailAddress&)>& send, const EmailContactInfo& info) {
  if (auto* u = std::get_if<Unverified>(&info)) send(u->email);
}

void sendPasswordReset(const std::function<void(const EmailAddress&)>& send, const EmailContactInfo& info) {
  if (auto* v = std::get_if<Verified>(&info)) send(v->email);
}
```

## 3. Step 6: an enum plus fields becomes a union (package delivery)

The enum version leaves `DeliveryDate`/`DeliverySignature` settable in any state and silently assumes three states in its `else`. The union version must handle every state for every event. Errors are returned, not thrown, so the caller decides (see `composable-error-handling`).

**Haskell**

```haskell
import Data.Time (UTCTime)

newtype PackageId = PackageId Int

data Package
  = Undelivered PackageId
  | OutForDelivery PackageId
  | Delivered PackageId UTCTime String -- date and signature exist only here

putOnTruck :: Package -> Either String Package
putOnTruck (Undelivered pid) = Right (OutForDelivery pid)
putOnTruck (OutForDelivery _) = Left "package already out"
putOnTruck (Delivered {}) = Left "package already delivered"

signedFor :: UTCTime -> String -> Package -> Either String Package
signedFor _ _ (Undelivered _) = Left "package not out"
signedFor at signature (OutForDelivery pid) = Right (Delivered pid at signature)
signedFor _ _ (Delivered {}) = Left "package already delivered"
```

**TypeScript**

```typescript
type Result<T> = { ok: true; value: T } | { ok: false; error: string };

type Package =
  | { readonly state: "undelivered"; readonly id: number }
  | { readonly state: "outForDelivery"; readonly id: number }
  | { readonly state: "delivered"; readonly id: number; readonly at: Date; readonly signature: string };

export function putOnTruck(p: Package): Result<Package> {
  switch (p.state) {
    case "undelivered":
      return { ok: true, value: { state: "outForDelivery", id: p.id } };
    case "outForDelivery":
      return { ok: false, error: "package already out" };
    case "delivered":
      return { ok: false, error: "package already delivered" };
  }
}

export function signedFor(at: Date, signature: string, p: Package): Result<Package> {
  switch (p.state) {
    case "undelivered":
      return { ok: false, error: "package not out" };
    case "outForDelivery":
      return { ok: true, value: { state: "delivered", id: p.id, at, signature } };
    case "delivered":
      return { ok: false, error: "package already delivered" };
  }
}
```

**C++**

```cpp
#include <chrono>
#include <expected>
#include <string>
#include <type_traits>
#include <variant>

using Time = std::chrono::system_clock::time_point;

struct Undelivered { int id; };
struct OutForDelivery { int id; };
struct Delivered { int id; Time at; std::string signature; };
using Package = std::variant<Undelivered, OutForDelivery, Delivered>;
using Step = std::expected<Package, std::string>;

Step putOnTruck(const Package& p) {
  return std::visit([](const auto& s) -> Step {
    using S = std::decay_t<decltype(s)>;
    if constexpr (std::is_same_v<S, Undelivered>) return OutForDelivery{s.id};
    else if constexpr (std::is_same_v<S, OutForDelivery>) return std::unexpected(std::string("package already out"));
    else return std::unexpected(std::string("package already delivered"));
  }, p);
}

Step signedFor(Time at, const std::string& signature, const Package& p) {
  return std::visit([&](const auto& s) -> Step {
    using S = std::decay_t<decltype(s)>;
    if constexpr (std::is_same_v<S, OutForDelivery>) return Delivered{s.id, at, signature};
    else if constexpr (std::is_same_v<S, Undelivered>) return std::unexpected(std::string("package not out"));
    else return std::unexpected(std::string("package already delivered"));
  }, p);
}
```

## 4. Step 6: options that fill in over time (order lifecycle)

`PaidDate`, `ShippedDate`, `ReturnedDate` as options are a clue that the type does too much. Each state carries everything accumulated so far, and nothing more.

**Haskell**

```haskell
import Data.Time (UTCTime)

data Placed = Placed {orderId :: Int, placedAt :: UTCTime}
data Payment = Payment {paidAt :: UTCTime, amount :: Double}
data Shipment = Shipment {shippedAt :: UTCTime, method :: String}
data Return = Return {returnedAt :: UTCTime, reason :: String}

data Order
  = Unpaid Placed
  | Paid Placed Payment
  | Shipped Placed Payment Shipment
  | Returned Placed Payment Shipment Return

pay :: Payment -> Order -> Either String Order
pay p (Unpaid o) = Right (Paid o p)
pay _ _ = Left "order is already paid"

ship :: Shipment -> Order -> Either String Order
ship s (Paid o p) = Right (Shipped o p s)
ship _ (Unpaid _) = Left "order is not paid for"
ship _ _ = Left "order is already shipped"
```

**TypeScript**

```typescript
type Placed = { readonly orderId: number; readonly placedAt: Date };
type Payment = { readonly paidAt: Date; readonly amount: number };
type Shipment = { readonly shippedAt: Date; readonly method: string };
type Return = { readonly returnedAt: Date; readonly reason: string };

type Order =
  | { readonly state: "unpaid"; readonly placed: Placed }
  | { readonly state: "paid"; readonly placed: Placed; readonly payment: Payment }
  | { readonly state: "shipped"; readonly placed: Placed; readonly payment: Payment; readonly shipment: Shipment }
  | {
      readonly state: "returned";
      readonly placed: Placed;
      readonly payment: Payment;
      readonly shipment: Shipment;
      readonly ret: Return;
    };

type Result<T> = { ok: true; value: T } | { ok: false; error: string };

export const pay = (payment: Payment, o: Order): Result<Order> =>
  o.state === "unpaid"
    ? { ok: true, value: { state: "paid", placed: o.placed, payment } }
    : { ok: false, error: "order is already paid" };

export const ship = (shipment: Shipment, o: Order): Result<Order> =>
  o.state === "paid"
    ? { ok: true, value: { state: "shipped", placed: o.placed, payment: o.payment, shipment } }
    : { ok: false, error: o.state === "unpaid" ? "order is not paid for" : "order is already shipped" };
```

**C++**

```cpp
#include <chrono>
#include <expected>
#include <string>
#include <variant>

using Time = std::chrono::system_clock::time_point;

struct Placed { int orderId; Time placedAt; };
struct Payment { Time paidAt; double amount; };
struct Shipment { Time shippedAt; std::string method; };
struct Return { Time returnedAt; std::string reason; };

struct Unpaid { Placed placed; };
struct Paid { Placed placed; Payment payment; };
struct Shipped { Placed placed; Payment payment; Shipment shipment; };
struct Returned { Placed placed; Payment payment; Shipment shipment; Return ret; };
using Order = std::variant<Unpaid, Paid, Shipped, Returned>;

std::expected<Order, std::string> pay(Payment p, const Order& o) {
  if (auto* u = std::get_if<Unpaid>(&o)) return Paid{u->placed, p};
  return std::unexpected(std::string("order is already paid"));
}

std::expected<Order, std::string> ship(Shipment s, const Order& o) {
  if (auto* p = std::get_if<Paid>(&o)) return Shipped{p->placed, p->payment, std::move(s)};
  if (std::holds_alternative<Unpaid>(o)) return std::unexpected(std::string("order is not paid for"));
  return std::unexpected(std::string("order is already shipped"));
}
```
