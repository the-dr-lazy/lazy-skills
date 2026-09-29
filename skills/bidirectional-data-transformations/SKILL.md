---
name: bidirectional-data-transformations
description: Bidirectional data transformations — lenses, isos, and prisms that declare a correspondence once and give both directions with round-trip laws. Use when mapping domain ↔ DTO, row, or view model, when writing to- and from-conversions by hand, or when updating nested immutable data.
---

# Bidirectional data transformations

Different components of a system need the same information in different structures — for performance, storage, serialization, convenience, or technical constraints. So programmers translate data between structures all the time, and usually write each translation **twice**, once per direction. That is redundant, tedious, error-prone, and a case of low coherence: the knowledge "field `x` here *is* field `y` there" is duplicated and can drift.

**Functional optics** describe the connection once, as a composable value:

| Optic | Relates | Laws (what makes it trustworthy) |
|---|---|---|
| **Lens** `S ⇄ A` | a whole and one part that always exists | get-set: `view l (set l a s) = a`; set-get: `set l (view l s) s = s`; set-set |
| **Iso** (projection) `S ≅ A` | two representations of the same information | `from (to s) = s` and `to (from a) = a` |
| **Prism** `S ⇄ A` | a sum type and one of its cases | `preview p (review p a) = Just a` |
| **Traversal / Fold** | a whole and zero or more parts | functor/monoid laws; folds are monoids and combine with `<>` |

Optics **compose**: `address . city` is a lens from a person to a city; an iso composed with a lens is a lens. The composition carries both directions and the laws.

## Procedure

1. **Identify pairs of representations** that carry the same information (domain ↔ DTO, domain ↔ row, model ↔ view model, nested update paths).
2. **Declare the smallest optics** (one per field or case), preferably derived by the library (Haskell `makeLenses`, active-clojure record lenses).
3. **Compose them** into the whole mapping; do not write a second, reverse function by hand.
4. **Check the laws** with round-trip property tests (`property-based-testing`) — especially for isos between domain and wire formats.
5. **Keep lossy steps explicit:** if a direction loses information, it is not an iso; model the loss (a lens from the richer side, a prism for partiality, a parse step for invalid input — `parse-dont-validate`).

Done when: each correspondence between representations is declared exactly once, both directions are derived from it, and round-trip laws are tested.

## When to reach for it (synthesized; upstream TODO)

- Two or more representations of the same entity are maintained in the same codebase (API DTO, storage row, domain model, UI form).
- Updates reach several levels into immutable nested data.
- Conversions are symmetric and mostly structural.

Reach for something else when the mapping is genuinely one-way (reporting, logs), mostly *computation* rather than *correspondence*, or when the team would pay more for the optics vocabulary than it saves. A shallow path is such a case: Elixir ships `Access`, `get_in`, and `put_in`, and pathex's README presents itself as the option with more functionality and speed than those, so try the built-ins first.

**Dynamic data makes optics partial.** On Erlang/Elixir maps and JSON, a "lens" is really a path, and a missing key can be an error, silently skipped, or created. The creating variants (datum's Ω-lenses, optic's `create` option) are, by their own documentation, not "well behaving": the lens laws no longer hold. pathex's `force_set!` likewise builds missing structure. optic's default (non-strict) mode also silently skips containers of an unexpected type. Choose strictness per call site, and property-test the laws only for the strict optics. optic's own criterion for optics that combine "without surprise" is that they are associative and idempotent.

## Example: one declaration, both directions

**Haskell** (`lens`)

```haskell
{-# LANGUAGE TemplateHaskell #-}
import Control.Lens

data Address = Address {_street :: String, _city :: String} deriving (Eq, Show)
data Person = Person {_name :: String, _address :: Address} deriving (Eq, Show)
makeLenses ''Address
makeLenses ''Person

-- The wire format: flat and differently named.
data PersonDto = PersonDto {dtoName :: String, dtoStreet :: String, dtoCity :: String} deriving (Eq, Show)

-- Declared once; `view` and `review` are the two directions.
dto :: Iso' Person PersonDto
dto = iso (\p -> PersonDto (p ^. name) (p ^. address . street) (p ^. address . city))
          (\d -> Person (dtoName d) (Address (dtoStreet d) (dtoCity d)))

alyssa :: Person
alyssa = Person "Alyssa" (Address "1 Main St" "Boston")

main :: IO ()
main = do
  print (alyssa ^. address . city) -- "Boston": a composed lens, read
  print (alyssa & address . city .~ "Cambridge") -- ... and write, immutably
  print (view dto alyssa) -- domain -> wire
  print (review dto (view dto alyssa) == alyssa) -- wire -> domain, round trip: True
```

**TypeScript** (a minimal optics kernel; libraries such as `optics-ts` or `monocle-ts` provide the full family)

```typescript
type Lens<S, A> = { get: (s: S) => A; set: (a: A, s: S) => S };
type Iso<S, A> = { to: (s: S) => A; from: (a: A) => S };

const compose = <S, A, B>(outer: Lens<S, A>, inner: Lens<A, B>): Lens<S, B> => ({
  get: (s) => inner.get(outer.get(s)),
  set: (b, s) => outer.set(inner.set(b, outer.get(s)), s),
});
const prop = <S, K extends keyof S>(k: K): Lens<S, S[K]> => ({ get: (s) => s[k], set: (a, s) => ({ ...s, [k]: a }) });

type Address = { readonly street: string; readonly city: string };
type Person = { readonly name: string; readonly address: Address };
type PersonDto = { readonly name: string; readonly street: string; readonly city: string };

export const city: Lens<Person, string> = compose(prop<Person, "address">("address"), prop<Address, "city">("city"));

export const dto: Iso<Person, PersonDto> = {
  to: (p) => ({ name: p.name, street: p.address.street, city: p.address.city }),
  from: (d) => ({ name: d.name, address: { street: d.street, city: d.city } }),
};

const alyssa: Person = { name: "Alyssa", address: { street: "1 Main St", city: "Boston" } };
export const moved = city.set("Cambridge", alyssa);
export const roundTrip = JSON.stringify(dto.from(dto.to(alyssa))) === JSON.stringify(alyssa); // true
```

**C++**

```cpp
#include <functional>
#include <string>

template <typename S, typename A>
struct Lens {
  std::function<A(const S&)> get;
  std::function<S(A, S)> set;
};

template <typename S, typename A, typename B>
Lens<S, B> compose(Lens<S, A> outer, Lens<A, B> inner) {
  return {[=](const S& s) { return inner.get(outer.get(s)); },
          [=](B b, S s) { return outer.set(inner.set(std::move(b), outer.get(s)), std::move(s)); }};
}

template <typename S, typename A>
struct Iso {
  std::function<A(const S&)> to;
  std::function<S(const A&)> from;
};

struct Address { std::string street, city; bool operator==(const Address&) const = default; };
struct Person { std::string name; Address address; bool operator==(const Person&) const = default; };
struct PersonDto { std::string name, street, city; };

const Lens<Person, Address> addressL{[](const Person& p) { return p.address; },
                                     [](Address a, Person p) { p.address = std::move(a); return p; }};
const Lens<Address, std::string> cityL{[](const Address& a) { return a.city; },
                                       [](std::string c, Address a) { a.city = std::move(c); return a; }};
const Lens<Person, std::string> personCity = compose(addressL, cityL);

const Iso<Person, PersonDto> dto{
    [](const Person& p) { return PersonDto{p.name, p.address.street, p.address.city}; },
    [](const PersonDto& d) { return Person{d.name, Address{d.street, d.city}}; }};

bool roundTrips(const Person& p) { return dto.from(dto.to(p)) == p; }
```

## Optics libraries

Haskell: [`lens`](https://hackage.haskell.org/package/lens), [`optics`](https://hackage.haskell.org/package/optics) (different design trade-offs; see its *Comparison with `lens`*). Scala: Monocle. F#: Aether. OCaml: ocaml-lens, Jane Street's Accessor. Clojure(Script): active-clojure's `active.clojure.lens`, where record accessors are lenses and records can define projection lenses. TypeScript: optics-ts, monocle-ts, Effect's `Optic`-style APIs. C++: no mainstream library; the lens-as-a-pair-of-functions kernel above is usually enough.

Erlang/Elixir (upstream TODO; the list below was checked against each repository and hex.pm in September 2026, using last release and last commit as the maintenance signal):

- Elixir: [`pathex`](https://github.com/hissssst/pathex) is the maintained choice (hex 2.6.1, August 2025). `path :user / :addresses / 0 / :street` builds a closure that can view, set, update, and delete; paths compile to pattern matches and compose with `~>`. Its README warns that Elixir 1.17 has bugs that block reliable use and that 1.18 emits spurious type-checking warnings for generated code, so pin and test your Elixir version. [`focus`](https://github.com/smpoulsen/focus) offers `Focus.view/set/over` and `~>` composition, but its last release and commit are from October 2021, and pathex's README calls it slow.
- Erlang: [`optic`](https://github.com/jkrukoff/optic) composes optics over lists, maps, tuples, dicts, sets, arrays, and proplists (hex 3.1.0, April 2019; dormant since). The lens module in [`datum`](https://github.com/fogfish/datum/blob/master/doc/lens.md) implements van Laarhoven lenses with `get`/`put`/`map`, composition and product lenses, and documents the get-put, put-get, and put-put laws; it belongs to a broader library of functional data types and generic programming for Erlang, and the repository's last commit is July 2025. [`erl-lenses`](https://github.com/jlouis/erl-lenses) is a single-file 2012 exploration whose README says it is not ready for large projects: a reference, not a dependency.

## Related skills

`immutability` · `composition-and-closure` (optics compose; folds are monoids) · `parse-dont-validate` (the lossy direction) · `airtight-abstractions` (prisms decouple interfaces from representation) · `everything-as-a-value` (accessors as values) · `property-based-testing` (round-trip laws)

## Sources

- functional-architecture.org, [Bidirectional Data Transformations](https://functional-architecture.org/bidirectional_data_transformations/) (published pattern page; *When to reach / not to reach* upstream TODO).
- Marcus Crestani, Markus Schlegel, Marco Schneider, [Bidirectional Data Transformations](https://dl.acm.org/doi/10.1145/3677998.3678224) (FUNARCH 2024).
- Library documentation read for the Erlang/Elixir list and the partiality caveats: [pathex](https://github.com/hissssst/pathex) (README; hex.pm release history), [focus](https://github.com/smpoulsen/focus) (README; hex.pm), [optic](https://github.com/jkrukoff/optic) (README on well-behaved optics and the `strict`/`create` options), [datum lens](https://github.com/fogfish/datum/blob/master/doc/lens.md) (lens laws and Ω-lenses), [erl-lenses](https://github.com/jlouis/erl-lenses) (README). Release and commit dates from hex.pm and the default branches, September 2026.
- Gabriella Gonzalez, [Optics are monoids](https://haskellforall.com/2021/09/optics-are-monoids) (2021), [total-1.0.0: Exhaustive pattern matching using traversals, prisms, and lenses](https://haskellforall.com/2015/01/total-100-exhaustive-pattern-matching) (2015), [What does "isomorphic" mean (in Haskell)?](https://haskellforall.com/2022/10/what-does-isomorphic-mean-in-haskell) (2022), [Explicit is better than implicit](https://haskellforall.com/2015/10/explicit-is-better-than-implicit) (2015).
