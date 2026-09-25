---
name: belt-and-suspenders
description: Belt-and-suspenders — guard an expensive failure with two independent checks when types cannot rule it out. Use at serialization boundaries, for behavioural failures, for AI-generated output, or before deleting a check that looks redundant.
---

# Belt-and-suspenders

*Guard a single expensive failure with two independent checks, either sufficient alone, so the failure escapes only when both fail at once.*

This is the **fallback** to `make-illegal-states-unrepresentable`. First ask whether you can have *zero* checks — a type that cannot express the bad state. Reach for two guards only when structural prevention is not on the table:

- the value crosses a serialization boundary (JSON, SQL, a form, another process) where types are erased;
- the failure is behavioural, not structural (a migration drops an index, a payment is applied twice);
- the thing being guarded is non-deterministic output (a model, an agent, a third-party service).

## Rules

1. **Price it.** Multiply the cost of the failure by the chance the first guard misses it. Install the second guard when that product is large and the guard is cheap. When the failure is recoverable and the guard is heavy, one guard wins (KISS, YAGNI).
2. **Make the guards independent.** Two guards that share a flaw are one guard wearing two hats. Client and server validation that call the same shared library fail together; a server-side parser plus a database `CHECK` constraint, or a type plus a property test, or a parser plus an invariant check in a different module fail for different reasons.
3. **Fail fast and loud.** Each guard reports every catch visibly. A backstop that catches silently teaches everyone to rely on it, and the front line rots.
4. **Mark the second guard as load-bearing.** It looks duplicative, which makes it the first thing a reviewer — or an agent simplifying a file — deletes. A comment naming the failure it guards and the independent guard it backs up keeps it alive.

Done when: each expensive failure has either a structural guarantee or two guards that fail for different reasons, and every redundant-looking guard says why it is there.

## Example: money leaves an account only once, and never below zero

The first guard is structural at the API boundary (the amount is parsed into a positive type). The second is an independent invariant in the ledger's pure transition function, which would catch a bug anywhere upstream — including code paths that never saw the parser.

**Haskell**

```haskell
module Ledger (Amount, parseAmount, Account (..), withdraw) where

-- Guard 1 (boundary): only positive amounts exist.
newtype Amount = Amount Integer -- cents; constructor not exported

parseAmount :: Integer -> Either String Amount
parseAmount n
  | n > 0 = Right (Amount n)
  | otherwise = Left "amount must be positive"

newtype Account = Account {balance :: Integer} deriving (Show)

-- Guard 2 (ledger invariant). LOAD-BEARING: independent of parseAmount; it also protects
-- replayed events, migrations, and admin tools that construct transitions directly.
withdraw :: Amount -> Account -> Either String Account
withdraw (Amount n) (Account b)
  | b - n < 0 = Left ("invariant violated: balance would become " <> show (b - n))
  | otherwise = Right (Account (b - n))
```

**TypeScript**

```typescript
// Guard 1 (boundary): only positive amounts exist.
export class Amount {
  private constructor(readonly cents: bigint) {}
  static parse(n: bigint): Amount | string {
    return n > 0n ? new Amount(n) : "amount must be positive";
  }
}

export type Account = { readonly balance: bigint };

// Guard 2 (ledger invariant). LOAD-BEARING: independent of Amount.parse; it also protects
// replayed events, migrations, and admin tools that construct transitions directly.
export function withdraw(amount: Amount, account: Account): Account {
  const next = account.balance - amount.cents;
  if (next < 0n) throw new Error(`invariant violated: balance would become ${next}`);
  return { balance: next };
}
```

**C++**

```cpp
#include <cstdint>
#include <expected>
#include <string>

// Guard 1 (boundary): only positive amounts exist.
class Amount {
public:
  static std::expected<Amount, std::string> parse(std::int64_t cents) {
    if (cents <= 0) return std::unexpected(std::string("amount must be positive"));
    return Amount(cents);
  }
  std::int64_t cents() const { return cents_; }
private:
  explicit Amount(std::int64_t c) : cents_(c) {}
  std::int64_t cents_;
};

struct Account { std::int64_t balance; };

// Guard 2 (ledger invariant). LOAD-BEARING: independent of Amount::parse; it also protects
// replayed events, migrations, and admin tools that construct transitions directly.
std::expected<Account, std::string> withdraw(Amount a, Account acc) {
  const std::int64_t next = acc.balance - a.cents();
  if (next < 0)
    return std::unexpected("invariant violated: balance would become " + std::to_string(next));
  return Account{next};
}
```

A third, again independent, layer is a database constraint (`CHECK (balance >= 0)`) — different technology, different failure modes.

## Typical pairs in functional architectures

| First guard | Independent second guard |
|---|---|
| Client-side form validation (fast feedback) | Server-side parser (`parse-dont-validate`) — the only one that stops a hostile client |
| Smart constructor (`smart-constructor`) | Property tests of the constructor's module; a database constraint |
| Types | Property-based tests of behaviour the types cannot express (`property-based-testing`) |
| An agent's generated migration / code | Replay against a disposable copy and diff; an evaluator; a human review |
| Idempotent command handler | Deduplication by message id in the event store (`event-sourcing`) |

## Related skills

`make-illegal-states-unrepresentable` (the stronger move) · `parse-dont-validate` · `smart-constructor` · `property-based-testing` · `formal-verification`

## Sources

- Wolf McNally, [Belt-and-Suspenders](https://aipatternbook.com/belt-and-suspenders), *Encyclopedia of Agentic Coding Patterns*.
- Wolf McNally, [Make Illegal States Unrepresentable](https://aipatternbook.com/make-illegal-states-unrepresentable) — "Belt-and-Suspenders is the fallback when structural prevention is not available."
