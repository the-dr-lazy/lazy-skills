---
name: decoupled-by-default
description: Decoupled by default — channels between building blocks as wide as necessary and as narrow as possible, with defaults and tools that make low coupling the easy path. Use when defining module or service interfaces, reviewing coupling, or choosing team conventions and lint rules.
---

# Decoupled by default

> *functional-architecture.org:* "Make the communication channels between building blocks as wide as necessary and as narrow as possible. Build tools with affordances toward low coupling and high cohesion." (Principle page is a German draft; summarized below.)

Piece A is tightly coupled to piece B when A has many dependencies on B, so changes to B are likely to force changes to A. The conventional view treats high coupling as a sin of **omission** — not programming against interfaces, not modularizing — to be repaired afterwards with refactoring "tactics". The draft's counterpoint: when the cart is stuck in the mud, pulling it out takes work, but the root cause was **driving it into the mud**. Better than lowering coupling again and again is not introducing it: the original sin of software architecture is the harmful act, not the missing remedy.

## Where coupling comes from — and the default that avoids it

| Harmful default | What it couples | Decoupled default |
|---|---|---|
| **Mutable shared data** (the default in Java, C++, Python) | Every holder of a reference to every other holder; algorithms to *time* | Immutable values; a change is a function old → new (`immutability`) |
| **Hidden effects** | Callers to the infrastructure a callee secretly uses | Effects in signatures; capabilities passed in (`composable-effects`) |
| **Implicit invariants** (documented in comments) | Every consumer to the producer's unwritten rules | Types that carry the invariant (`make-illegal-states-unrepresentable`) |
| **Over-specific types** | A function to details it never uses | The most general type that works (parametric polymorphism) |
| **Parsing more than you use** | A consumer to every field of a foreign schema | Parse only the fields you need; keep the rest opaque (`parse-dont-validate`) |
| **Foreign representations** (a partner's ID *is* a UUID) | Your code to another team's implementation choice | Opaque types that support only equality and serialization |
| **Weakly typed maps as records** | Every reader to every writer's key conventions | Records / structs with named, typed fields |

The common thread: **the type of an interface should say exactly how much each side must know about the other — and no more.** Static types are not about pinning down the world; they let you state precisely what a component needs and what it ignores.

## Affordances: make the decoupled path the easy path

Languages and tools create incentives. When the easy thing is also the right thing, it survives deadline pressure; when the right thing takes discipline, it erodes, team by team and dependency by dependency. Haskell makes absence of null, effect-free code, immutability, generic types, and records the *shortest* code to write. Where the language does not, choose conventions, libraries, lint rules, and project templates so that:

- the default collection and record types are read-only;
- effectful operations are visibly different from pure ones (names, types, module placement);
- the least-specific type is what inference or the code template produces;
- escape hatches (`any`, casts, `mutable`, global singletons) are longer to write and flagged in review.

## Procedure: review an interface between two building blocks

1. **List what crosses the boundary** (data, callbacks, shared objects, configuration).
2. **Replace locations with values:** no mutable object is shared across the boundary.
3. **Narrow each type** to what the receiver actually uses: generic type parameters, small capability interfaces, projections of large records, opaque identifiers.
4. **Make invariants and effects explicit** in the types instead of in documentation.
5. **Widen only on evidence:** if a consumer genuinely needs more, widen the channel deliberately and name why.

Done when: each side of the boundary could be rewritten without reading the other's implementation, and no consumer can observe or depend on anything the producer did not choose to expose.

## Example: least knowledge through parametric types

A function specialized to `Order` can depend on everything about orders; the generic version *cannot*, which is exactly why it cannot break when `Order` changes. Parametricity turns "should not depend on" into "cannot depend on".

**Haskell**

```haskell
data Order = Order {orderId :: Int, total :: Int, customerEmail :: String}

-- Over-coupled: knows orders, and could inspect any field.
firstLargeOrder :: [Order] -> Maybe Order
firstLargeOrder orders = case filter ((> 1000) . total) orders of
  o : _ -> Just o
  [] -> Nothing

-- Decoupled: works for any element type; by parametricity it can only
-- return an element of the list for which the predicate said True.
firstWhere :: (a -> Bool) -> [a] -> Maybe a
firstWhere p xs = case filter p xs of
  x : _ -> Just x
  [] -> Nothing

firstLargeOrder' :: [Order] -> Maybe Order
firstLargeOrder' = firstWhere ((> 1000) . total)
```

**TypeScript**

```typescript
type Order = { readonly orderId: number; readonly total: number; readonly customerEmail: string };

export const firstWhere = <A,>(p: (a: A) => boolean, xs: readonly A[]): A | undefined => xs.find(p);

// The coupling to Order lives in one small, obvious place.
export const firstLargeOrder = (orders: readonly Order[]) => firstWhere((o) => o.total > 1000, orders);

// A narrow structural type: the consumer states the only field it reads.
export const totalOf = (orders: ReadonlyArray<{ readonly total: number }>): number =>
  orders.reduce((sum, o) => sum + o.total, 0);
```

**C++**

```cpp
#include <algorithm>
#include <concepts>
#include <optional>
#include <ranges>
#include <string>
#include <vector>

struct Order { int orderId; int total; std::string customerEmail; };

template <std::ranges::input_range R, std::predicate<std::ranges::range_reference_t<R>> P>
std::optional<std::ranges::range_value_t<R>> firstWhere(R&& xs, P p) {
  auto it = std::ranges::find_if(xs, p);
  if (it == std::ranges::end(xs)) return std::nullopt;
  return *it;
}

std::optional<Order> firstLargeOrder(const std::vector<Order>& orders) {
  return firstWhere(orders, [](const Order& o) { return o.total > 1000; });
}

// A narrow constraint: the consumer states the only member it reads.
template <typename T>
concept HasTotal = requires(const T& t) { { t.total } -> std::convertible_to<int>; };

template <HasTotal T>
int totalOf(const std::vector<T>& xs) {
  int sum = 0;
  for (const auto& x : xs) sum += x.total;
  return sum;
}
```

## Related skills

`immutability` · `modularization` · `airtight-abstractions` · `composable-effects` · `parse-dont-validate` · `make-illegal-states-unrepresentable` · `functional-programming-languages` (language defaults as affordances) · `late-decision-making`

## Sources

- functional-architecture.org, [Decoupled by Default](https://functional-architecture.org/dbd/) (principle page; draft, in German).
- Gabriella Gonzalez, [Worst practices should be hard](https://haskellforall.com/2016/04/worst-practices-should-be-hard) (2016) and [Worst practices are viral for the wrong reasons](https://haskellforall.com/2014/04/worst-practices-are-viral-for-wrong) (2014).
- Alexis King, [No, dynamic type systems are not inherently more open](https://lexi-lambda.github.io/blog/2020/01/19/no-dynamic-type-systems-are-not-inherently-more-open/) (2020) — types state exactly how much a component needs to know.
- functional-architecture.org, [Make Illegal States Unrepresentable](https://functional-architecture.org/make_illegal_states_unrepresentable/) — implicit invariants as implicit coupling.
- Gabriella Gonzalez, [The CAP theorem for software engineering](https://haskellforall.com/2019/06/the-cap-theorem-for-software-engineering) (2019) — coupling trade-offs between *teams* (monorepo vs polyrepo) seen as consistency vs availability.
