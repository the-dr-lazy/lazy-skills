---
name: modularization
description: Modularization — hide likely-to-change decisions behind small interfaces, organize modules vertically by feature, and export abstract types. Use when splitting code into modules or packages, choosing exports, or untangling changes that touch every module.
---

# Modularization

> *functional-architecture.org:* "Modules hide difficult decisions behind simple interfaces. While modularization is not an exclusive feature of functional architectures, functional abstractions allow for simpler interfaces and therefore allow to hide more decisions, leading to more malleable designs overall." (Principle page upstream TODO.)

A module is worth having when it **hides a decision** — a data representation, an algorithm, a storage format, a protocol, an external service — that other code would otherwise have to know about. The interface is the part that other modules may depend on; everything else can change without them noticing.

Functional techniques make interfaces smaller: an abstract type plus a handful of functions (instead of a class hierarchy with protected members); parametric polymorphism (a function over `[a]` cannot depend on what `a` is); interfaces as ordinary values (records of functions, first-class modules) that can be chosen and composed at run time; immutable values crossing boundaries instead of shared mutable objects.

## Organize vertically, not horizontally

- **Vertical:** group related functionality — `Syntax`, `Parsing`, `Infer`, `Evaluation`, `Pretty` — each containing its types, functions, and error messages.
- **Horizontal:** group by kind — `Types`, `Lib`, `Constants`, `App`. Avoid it:
  - horizontal modules are so coupled that no subset is useful alone; vertical ones split into packages (open-source `Syntax`/`Parsing`/`Pretty` as a formatter without the type checker);
  - adding a type to `Types` rebuilds everything; rewriting `Infer` rebuilds only its dependents;
  - horizontal changes touch every module; vertical changes tend to stay in one.

## Procedure

1. **List the decisions likely to change** or hard to understand (representation, algorithm, vendor, format, policy).
2. **Give each decision one home module**, named after the concept it provides (vertical), whose interface does not mention the decision.
3. **Export an abstract type and operations**, not constructors or fields; prefer the most general types; keep effectful operations explicit.
4. **Make the home module the trust boundary** for any invariant it maintains — and keep that trusted surface small (`names-are-not-type-safety`).
5. **Check dependency direction:** domain modules do not import infrastructure; infrastructure implements interfaces the domain defines (`composable-effects`).
6. **Name the default module after the package** (`foo-bar` → `Foo.Bar`) so users know what to import.

Done when: each likely-to-change decision can be changed by editing one module, no module is a grab-bag of a *kind* of thing, and module interfaces expose no representation.

## Example: hiding the representation of a directory

Clients of `Directory` can add and look up people; whether that is a list, a map, a trie, or a database table is the module's secret. Switching from a list to a map changes one module.

**Haskell**

```haskell
module Directory (Directory, empty, add, lookupEmail, size) where -- representation hidden

import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map

newtype Directory = Directory (Map String String) -- was [(String, String)]; clients never knew

empty :: Directory
empty = Directory Map.empty

add :: String -> String -> Directory -> Directory
add name email (Directory m) = Directory (Map.insert name email m)

lookupEmail :: String -> Directory -> Maybe String
lookupEmail name (Directory m) = Map.lookup name m

size :: Directory -> Int
size (Directory m) = Map.size m
```

**TypeScript**

```typescript
// directory.ts — only these names are exported; the representation is the module's secret.
export class Directory {
  readonly #entries: ReadonlyMap<string, string>; // was an array of pairs; clients never knew
  private constructor(entries: ReadonlyMap<string, string>) {
    this.#entries = entries;
  }
  static empty(): Directory {
    return new Directory(new Map());
  }
  add(name: string, email: string): Directory {
    return new Directory(new Map(this.#entries).set(name, email));
  }
  lookupEmail(name: string): string | undefined {
    return this.#entries.get(name);
  }
  get size(): number {
    return this.#entries.size;
  }
}
```

**C++**

```cpp
#include <cstddef>
#include <map>
#include <optional>
#include <string>

// directory.hpp — with C++20 modules, only `export`ed names would be visible at all.
class Directory {
public:
  Directory add(std::string name, std::string email) const {
    Directory d = *this;
    d.entries_.insert_or_assign(std::move(name), std::move(email));
    return d;
  }
  std::optional<std::string> lookupEmail(const std::string& name) const {
    if (auto it = entries_.find(name); it != entries_.end()) return it->second;
    return std::nullopt;
  }
  std::size_t size() const { return entries_.size(); }

private:
  std::map<std::string, std::string> entries_;  // was a vector of pairs; clients never knew
};
```

## Related skills

`airtight-abstractions` · `decoupled-by-default` · `names-are-not-type-safety` · `composable-effects` (interfaces the domain owns) · `architecture-as-code` (checking dependency rules) · `late-decision-making`

## Sources

- functional-architecture.org, [Modularization](https://functional-architecture.org/modularization/) (principle page; upstream TODO).
- Gabriella Gonzalez, [Module organization guidelines for Haskell projects](https://haskellforall.com/2021/05/module-organization-guidelines-for) (2021), [First-class modules without defaults](https://haskellforall.com/2012/07/first-class-modules-without-defaults) (2012).
- **Alexis King, [Names are not type safety](https://lexi-lambda.github.io/blog/2020/11/01/names-are-not-type-safety/)** (2020) — the home module as trust boundary.
- Jeffrey M. Young, Sylvain Henry, John Ericson, [Stretching the Glasgow Haskell Compiler: Nourishing GHC with Domain-Driven Design](https://dl.acm.org/doi/10.1145/3609025.3609476) (FUNARCH 2023) — how a large functional system loses modularity, and guidance from DDD.
- Further reading: David Parnas, *On the Criteria To Be Used in Decomposing Systems into Modules* (1972).
