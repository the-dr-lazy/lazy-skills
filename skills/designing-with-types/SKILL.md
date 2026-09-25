---
name: designing-with-types
description: Designing with types — Wlaschin's step-by-step workflow from a primitive-obsessed, flag-laden record to precise domain types. Use when modeling a new domain, reviewing a model full of strings, bools, and nullables, or making a model type-safe end to end.
---

# Designing with types

Types are a design tool: used thoughtfully, they make a design more transparent *and* more correct at the same time. This skill is the micro-level workflow — individual types and functions — that ties the other domain-modeling skills together. The running example is Scott Wlaschin's `Contact`:

```text
Contact { FirstName, MiddleInitial, LastName : string
          EmailAddress : string;  IsEmailVerified : bool
          Address1, Address2, City, State, Zip : string;  IsAddressValid : bool }
```

Everything is a string or a flag; every business rule lives somewhere else, if anywhere.

## Workflow

Work through the steps in order; each one makes the next one visible. After each step, compile and let the errors point at the code that must change.

1. **Group atomic data.** Put fields that must change together (consistency boundaries) into their own records: `PersonalName`, `PostalAddress`, `EmailContactInfo`. Leave unrelated data apart. Flags that describe a group (`IsEmailVerified`) travel with the group, because changing the data must reset the flag.
   *Done when:* every record's fields are updated together, and no update needs to touch two records to stay consistent.
2. **Make optionality explicit.** `MiddleInitial : string option`. No nulls; absence is in the type.
3. **Wrap meaningful primitives.** An email address is not a zip code. Give each domain primitive its own type with a smart constructor (`smart-constructor`), decide how construction failure is reported, and construct/unwrap only at service boundaries. Know what the wrapper buys (`names-are-not-type-safety`).
4. **Encode business rules as types.** *"A contact must have an email or a postal address"* is `EmailOnly | PostOnly | EmailAndPost` — not two options (which admit "neither") and not two required fields (which forbid "only one") (`make-illegal-states-unrepresentable`).
5. **Use the types to discover concepts.** When the encoding gets awkward (15 combinations of four contact methods), step back. The missing concept is `ContactMethod = Email | Post | HomePhone | WorkPhone`; "at least one" becomes a required primary plus a list of secondaries. Awkward types are a signal to refactor toward deeper insight (Evans, *Domain-Driven Design*, chapters 8–9).
6. **Make state explicit.** A boolean flag (`IsEmailVerified`), a status enum next to data, or a record of options that fill in over time is an implicit state machine. Make one case per state, carrying only that state's data; make each event a function from the whole machine to the whole machine; let business rules ("send password resets only to verified addresses") become type signatures.
7. **Constrain the remaining primitives.** Strings get maximum lengths and canonical forms (`String50`), numbers get ranges (`NonNegativeInt`, `CartQuantity` 1–99), dates get bounds (`SafeDate`). These are the physical model, and they belong in the shared model so every service agrees.
8. **Delete what the types made redundant**: null checks, defensive `if`s, "impossible" branches, validation duplicated in the UI and the database layer.

*Workflow done when:* stripping away everything but the type definitions still tells a reader the business rules and domain constraints, and there is essentially one way to write code that compiles against them.

## The result

**Haskell**

```haskell
newtype String50 = String50 String
newtype EmailAddress = EmailAddress String
newtype ZipCode = ZipCode String
newtype StateCode = StateCode String
newtype PhoneNumber = PhoneNumber String
newtype Day = Day Int

data PersonalName = PersonalName
  {firstName :: String50, middleInitial :: Maybe Char, lastName :: String50}

data EmailContactInfo
  = UnverifiedEmail EmailAddress
  | VerifiedEmail EmailAddress Day -- verification date exists only once verified

data PostalAddress = PostalAddress
  {address1 :: String50, address2 :: Maybe String50, city :: String50, state :: StateCode, zip :: ZipCode}

data PostalContactInfo = PostalContactInfo {address :: PostalAddress, isAddressValid :: Bool}

data ContactMethod
  = Email EmailContactInfo
  | Post PostalContactInfo
  | HomePhone PhoneNumber
  | WorkPhone PhoneNumber

data Contact = Contact
  {name :: PersonalName, primaryContact :: ContactMethod, secondaryContacts :: [ContactMethod]}

-- A business rule as a signature: only verified addresses get password resets.
sendPasswordReset :: EmailContactInfo -> Maybe EmailAddress
sendPasswordReset (VerifiedEmail addr _) = Just addr
sendPasswordReset (UnverifiedEmail _) = Nothing
```

**TypeScript**

```typescript
type Brand<T, B extends string> = T & { readonly __brand: B }; // minted only by smart constructors
type String50 = Brand<string, "String50">;
type EmailAddress = Brand<string, "EmailAddress">;
type ZipCode = Brand<string, "ZipCode">;
type StateCode = Brand<string, "StateCode">;
type PhoneNumber = Brand<string, "PhoneNumber">;

type PersonalName = {
  readonly firstName: String50;
  readonly middleInitial: string | null;
  readonly lastName: String50;
};

type EmailContactInfo =
  | { readonly state: "unverified"; readonly email: EmailAddress }
  | { readonly state: "verified"; readonly email: EmailAddress; readonly verifiedOn: Date };

type PostalAddress = {
  readonly address1: String50;
  readonly address2: String50 | null;
  readonly city: String50;
  readonly state: StateCode;
  readonly zip: ZipCode;
};

type ContactMethod =
  | { readonly kind: "email"; readonly info: EmailContactInfo }
  | { readonly kind: "post"; readonly address: PostalAddress; readonly isAddressValid: boolean }
  | { readonly kind: "homePhone"; readonly phone: PhoneNumber }
  | { readonly kind: "workPhone"; readonly phone: PhoneNumber };

export type Contact = {
  readonly name: PersonalName;
  readonly primaryContact: ContactMethod;
  readonly secondaryContacts: readonly ContactMethod[];
};

export const sendPasswordReset = (info: EmailContactInfo): EmailAddress | undefined =>
  info.state === "verified" ? info.email : undefined;
```

**C++**

```cpp
#include <chrono>
#include <optional>
#include <string>
#include <variant>
#include <vector>

template <typename Tag>
class Constrained {  // minted only by smart constructors (see the smart-constructor skill)
public:
  const std::string& value() const { return v_; }
private:
  explicit Constrained(std::string v) : v_(std::move(v)) {}
  std::string v_;
  template <typename T> friend std::optional<Constrained<T>> make(std::string);
};

using String50 = Constrained<struct String50Tag>;
using EmailAddress = Constrained<struct EmailTag>;
using ZipCode = Constrained<struct ZipTag>;
using StateCode = Constrained<struct StateTag>;
using PhoneNumber = Constrained<struct PhoneTag>;

struct PersonalName { String50 firstName; std::optional<char> middleInitial; String50 lastName; };

struct UnverifiedEmail { EmailAddress email; };
struct VerifiedEmail { EmailAddress email; std::chrono::sys_days verifiedOn; };
using EmailContactInfo = std::variant<UnverifiedEmail, VerifiedEmail>;

struct PostalAddress {
  String50 address1;
  std::optional<String50> address2;
  String50 city;
  StateCode state;
  ZipCode zip;
};

struct Email { EmailContactInfo info; };
struct Post { PostalAddress address; bool isAddressValid; };
struct HomePhone { PhoneNumber phone; };
struct WorkPhone { PhoneNumber phone; };
using ContactMethod = std::variant<Email, Post, HomePhone, WorkPhone>;

struct Contact {
  PersonalName name;
  ContactMethod primaryContact;
  std::vector<ContactMethod> secondaryContacts;
};

std::optional<EmailAddress> sendPasswordReset(const EmailContactInfo& info) {
  if (auto* v = std::get_if<VerifiedEmail>(&info)) return v->email;
  return std::nullopt;
}
```

The step-by-step versions (before, after each step), the email-verification and package-delivery state machines, and the order lifecycle are in [examples.md](examples.md).

## Is it worth it?

The "after" code is much longer. It is also explicit about every rule, will not let you postpone error handling (it has to be decided at construction time — a name too long, a missing contact method), and removes whole classes of bugs without a single unit test: you cannot send two verification emails to a verified address or truncate a name in a `varchar(50)`. The business logic *is* this complicated; the "before" code hides the complexity, it does not remove it.

Apply judgment, not a golden hammer: skip the state machine when states carry no behaviour, when transitions happen outside the app, or when rules change too fast to compile (`make-illegal-states-unrepresentable` → *When not to*).

## Related skills

`make-illegal-states-unrepresentable` · `smart-constructor` · `names-are-not-type-safety` · `parse-dont-validate` · `boolean-blindness` · `property-based-testing` (properties also drive model changes, e.g. `int` → `PositiveInteger`)

## Sources

Scott Wlaschin, *Designing with types* series (F# for Fun and Profit, 2013):
[1 Introduction](https://fsharpforfunandprofit.com/posts/designing-with-types-intro/) ·
[2 Single case union types](https://fsharpforfunandprofit.com/posts/designing-with-types-single-case-dus/) ·
[3 Making illegal states unrepresentable](https://fsharpforfunandprofit.com/posts/designing-with-types-making-illegal-states-unrepresentable/) ·
[4 Discovering new concepts](https://fsharpforfunandprofit.com/posts/designing-with-types-discovering-the-domain/) ·
[5 Making state explicit](https://fsharpforfunandprofit.com/posts/designing-with-types-representing-states/) ·
[6 Constrained strings](https://fsharpforfunandprofit.com/posts/designing-with-types-more-semantic-types/) ·
[7 Non-string types](https://fsharpforfunandprofit.com/posts/designing-with-types-non-strings/) ·
[8 Conclusion](https://fsharpforfunandprofit.com/posts/designing-with-types-conclusion/).
Also: Alexis King, [Parse, don't validate](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/) ("write functions on the data representation you wish you had").
