---
name: immutability
description: Immutability — values instead of mutable locations, so data can be shared, cached, and validated once. Use when designing types and APIs, fixing bugs from shared mutable objects or defensive copies, removing setters, or choosing collections in TypeScript or C++.
---

# Immutability

> *functional-architecture.org:* "Stop thinking in terms of state and resource management and start thinking in terms of your domain." (Principle page upstream TODO.)

A mutable datum is really two things: **the datum and a location** that holds it. Every algorithm that touches it now has to reason about *time* — what is in the location *now*, who else can write to it, and when. Passing an object by reference passes the location, not the information. An immutable **value** is just the information.

## Why it matters

- **No hidden coupling through shared locations.** A receiver of a mutable `Person` depends not only on `Person` but on every other holder of that reference. Callers compensate with defensive copies; readers must study the implementation of distant classes to know whether a copy was needed (`decoupled-by-default`).
- **Checks stay true.** A value validated at construction is valid forever; a smart constructor's guarantee cannot be undone by a setter (`smart-constructor`).
- **Free sharing.** Values can be cached, memoized, put in maps and sets, and handed to other threads without locks.
- **History for free.** Old versions remain available: undo, audit, time travel, event sourcing, and diffing become straightforward, and persistent data structures make "copying" cheap through structural sharing.
- **Fewer tests.** Setter/getter round-trip and "set is idempotent" properties disappear when there are no setters.
- **Default matters.** In most mainstream languages mutability is the default and immutability takes extra effort, so programs end up coupled by accident. Functional languages invert the default; where your language does not, adopt conventions and tools that make immutability the path of least resistance.

## Procedure

1. **Make fields read-only** (`readonly`, `const`, no setters). Construct complete values up front.
2. **Replace each mutator with a function returning a new value** (`withAddress`, record update syntax, `{ ...p, address }`).
3. **Use persistent / immutable collections** for shared data: Haskell `Data.Map`/`Data.Sequence`; TypeScript `ReadonlyArray`/`ReadonlyMap` with spread or structural-sharing libraries (Immer, Immutable.js); C++ value semantics with `const`, or persistent containers (e.g. the `immer` library).
4. **Keep unavoidable mutation local and unobservable** — a mutable buffer inside a function that returns a fresh value (Haskell `ST`, a local vector in C++) is pure from the outside. Measure before introducing observable mutation for speed.
5. **Model change explicitly.** When something genuinely changes over time (an account balance), represent the change as values — a new state returned by a transition, or an event appended to a log (`event-sourcing`) — rather than an object mutated in place.

Done when: no value crosses a module boundary through a mutable reference, no caller needs a defensive copy, and every "change" in the domain is a function from old value to new value.

## Example: transferring a person between departments

The mutable version passes locations: `DepartmentA` cannot know whether `DepartmentB` will still change "its" person later (`backToTheOffice` does), so it must either inspect `DepartmentB`'s implementation or clone defensively. The immutable version passes information; `move` is a function from an old person to a new one.

**Haskell**

```haskell
data Person = Person {name :: String, address :: String} deriving (Eq, Show)

-- A change is a function from the old value to a new one.
move :: String -> Person -> Person
move newAddress p = p {address = newAddress}

data Department = Department {deptName :: String, staff :: [Person]} deriving (Show)

transfer :: Person -> Department -> Department -> (Department, Department)
transfer p from to =
  ( from {staff = filter (/= p) (staff from)}
  , to {staff = p : staff to}
  )
-- Nothing the old department does later can change the person the new one received.
```

**TypeScript**

```typescript
type Person = { readonly name: string; readonly address: string };
type Department = { readonly name: string; readonly staff: readonly Person[] };

export const move = (newAddress: string, p: Person): Person => ({ ...p, address: newAddress });

export function transfer(p: Person, from: Department, to: Department): [Department, Department] {
  return [
    { ...from, staff: from.staff.filter((q) => q !== p) },
    { ...to, staff: [p, ...to.staff] },
  ];
}

// Mutable contrast (what not to share across modules):
class MutablePerson {
  constructor(public name: string, public address: string) {}
  setAddress(a: string): void { this.address = a; } // every holder of this reference sees it
}
export { MutablePerson };
```

**C++**

```cpp
#include <algorithm>
#include <string>
#include <utility>
#include <vector>

struct Person {
  std::string name;
  std::string address;
  bool operator==(const Person&) const = default;
};

// Value semantics: parameters are copies (or moved-in values); results are new values.
Person move(std::string newAddress, Person p) {
  p.address = std::move(newAddress);  // mutates a local copy only: unobservable to callers
  return p;
}

struct Department {
  std::string name;
  std::vector<Person> staff;  // holds values, not pointers to shared persons
};

std::pair<Department, Department> transfer(const Person& p, Department from, Department to) {
  std::erase(from.staff, p);
  to.staff.insert(to.staff.begin(), p);
  return {std::move(from), std::move(to)};
}
```

In C++, *value semantics* (types held by value, passed by value or `const&`, no shared owning pointers to mutable state) gives most of the benefit; the mutation inside `move` touches only a local copy. Sharing `std::shared_ptr<Person>` across departments recreates the Java problem.

## Related skills

`decoupled-by-default` · `pure-functions` · `event-sourcing` · `smart-constructor` · `functional-core-imperative-shell` · `zipper` (efficient "updates" to immutable structures)

## Sources

- functional-architecture.org, [Immutability](https://functional-architecture.org/immutability/) (principle page; upstream TODO) and the draft of [Decoupled by Default](https://functional-architecture.org/dbd/) (German; section *Das Problem mit veränderlichem Zustand* — the `Person`/`Department` example and the Haskell `move`).
- Gabriella Gonzalez, [Worst practices should be hard](https://haskellforall.com/2016/04/worst-practices-should-be-hard) (2016) — immutability by default as an incentive.
- Scott Wlaschin, [Choosing properties in practice, part 3](https://fsharpforfunandprofit.com/posts/property-based-testing-5/) — the immutable `Dollar` removes whole categories of tests.
- Alexis King, [Parse, don't validate](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/) — "avoid denormalized representations of data, *especially* if it's mutable."
