---
name: names-are-not-type-safety
description: Names are not type safety — distinguish intrinsic safety (constructive types) from extrinsic safety (a newtype, wrapper, or brand plus smart constructor behind a trust boundary), and know when a type alias (type synonym, `using`, `typedef`) is the wrong tool. Use when introducing or reviewing a newtype, wrapper, branded or opaque type, type alias, or "type-safe" IDs and strings.
---

# Names are not type safety

A `newtype` (single-case union, branded type, wrapper class) declares a type that is nominally distinct from, but representationally the same as, the type it wraps. **On its own, it is just a name.** A name prevents some mix-ups; it does not make illegal values unrepresentable.

> Alexis King, *Names are not type safety* (2020): newtypes "can provide *some* value, and when coupled with a smart constructor and an encapsulation boundary, it can even provide some safety. But it is a meaningfully distinct *kind* of type safety … one that is far weaker."

## Intrinsic versus extrinsic safety

| | Constructive type | Wrapper + smart constructor |
|---|---|---|
| Example | `data OneToFive = One \| Two \| Three \| Four \| Five` | `newtype OneToFive = OneToFive Int` + `toOneToFive :: Int -> Maybe OneToFive` |
| Where the invariant lives | In the type declaration | In the smart constructor's code |
| What consumers see | Exactly the legal cases; exhaustiveness checking works | An `Int`; they need an `error "impossible"` branch |
| What you must trust | The typechecker | The defining module and every future edit to it |
| Adding a case | Every consumer fails to compile | Every consumer still compiles, then fails at runtime |

The smart constructor *validates*; the Boolean result is used for control flow and then thrown away. Downstream code cannot benefit from the restricted domain — it is functionally accepting `Int`s. Prefer the constructive form whenever it is practical (`correctness-by-construction`, `make-illegal-states-unrepresentable`).

## Newtypes as tokens: the legitimate safety story

An opaque wrapper (constructor not exported) turns its **home module** into a trust boundary. The module issues tokens through its constructors; tokens are worthless elsewhere and can only be redeemed through the module's accessors. Invariant violations can only originate inside that module, so its API is small enough to test thoroughly (property-based testing, fuzzing).

This safety is conditional. Holes appear easily:

- **Derived instances that construct values:** `deriving (Generic)`, `deriving (Read)`, JSON decoders that build the value directly, `Arbitrary` instances in production code.
- **TypeScript:** any `as Brand` cast anywhere forges a brand; structural typing lets a same-shaped object literal satisfy an interface. Prefer a class with `#private` fields if forgery matters.
- **C++:** public aggregate initialization, a public default constructor, a non-`explicit` converting constructor, `reinterpret_cast`/`memcpy`, and `enum class` values forged with `static_cast`.

Keep the trust boundary sound:

1. State every invariant to maintainers of the trusted module (comments are mandatory for non-trivial invariants).
2. Audit every change to the module for weakened invariants.
3. Refuse "unsafe" trapdoors that bypass the constructor.
4. Refactor periodically so the trusted surface stays small — responsibilities accumulate there over time, especially in churning application code. Libraries, which change less and get more scrutiny, are the natural home for this technique.

## Decision procedure

1. **Can the invariant be expressed by construction at acceptable cost?** (a closed set → sum type; non-empty → head + tail; unique keys → map.) Do that.
2. **Otherwise, is it a genuine invariant worth a trust boundary?** (a range, a checksum, a normalized string) → opaque type, smart constructor returning the refined type, no escape hatches, property tests for the module's API. Call it what it is: extrinsic safety.
3. **Is the goal only to keep same-representation values apart?** (`CustomerId` vs `OrderId`, `Distance` vs `Duration`, seconds vs milliseconds, UTC vs local time) → a transparent wrapper is fine and useful: it prevents *logical mistakes*, it does not *prevent misuse*. Make it ergonomic (derive `IsString`/`Num`/`Show` via the underlying type in Haskell) so nobody is tempted to strip it.
4. **Is it wrapped and unwrapped at will, with no mix-up risk and no invariant?** → delete it. It is a security blanket: "forcing programmers to jump through a few hoops is not type safety." If the label adds clarity, a field name or a type alias suffices — within the limits in [Type aliases](#type-aliases-abbreviate-never-promise).

Done when: every wrapper type in the change is either constructive, an opaque token with a named trust boundary and tests, or a deliberately transparent label — and nobody describes the third kind as validation.

Other legitimate newtype uses that are *not* about safety: selecting an alternative type-class instance (`Sum`, `Product`), rearranging type parameters (`Flip`), and discouraging accidental exposure (a secret key without a `Show` instance — which discourages, but does not prevent, misuse).

## Type aliases: abbreviate, never promise

A type alias (`type` in Haskell and TypeScript, `using`/`typedef` in C++) is weaker than even a transparent newtype: the type checker treats it exactly as its right-hand side. `type UserId = Text` *is* `Text`. The Rust book puts it plainly: with an alias "we don't get the type-checking benefits that we get from the newtype pattern."

**Rule: an alias may abbreviate a type; it must not promise anything about it.** Test: replace the alias with its right-hand side everywhere. Does a reader or caller lose something they rely on? If not, the alias is shorthand and fine. If so, the name carries meaning the compiler cannot check, so that meaning needs a type (use the decision procedure above).

### Smells

1. **Promises a distinction.** `type UserId = Text`, or `Password` and `PasswordHash` as two aliases of `String`: swapped arguments compile, and nothing checks that the names are used consistently. → Transparent newtype.
2. **Promises an invariant.** `type Positive = Int`, `type SortedList a = [a]`, `type ValidEmail = Text`: a claim that nothing checks. → Constructive type, or opaque newtype + smart constructor.
3. **Hides a container behind a singular name.** `type PermissionName = Multilingual NonEmptyString`; the synonyms like `type CmmActuals = [CmmActual]` that Edward Yang removed from GHC. The name reads as one value but is a structure. The element has no type of its own, so a name in one language, a list of names, or an optional name cannot be expressed, and the concept is welded to one container. → Newtype the element and write the container at each use site (below).
4. **Promises its own instances or overloads.** `instance ToJSON PermissionName` is an instance for `Multilingual NonEmptyString`. Every other alias of that type shares it, and a second instance is a duplicate. It also *overlaps* the container's general `instance ToJSON a => ToJSON (Multilingual a)`, so uses fail with "Overlapping instances". Adding `{-# OVERLAPPING #-}` breaks generic code over `Multilingual a` ("the choice depends on the instantiation of `a`"). Adding `{-# INCOHERENT #-}` gives the same value different answers depending on where its type becomes known. `showList` in `Show` and `toJSONList` in aeson exist only because `String` is an alias of `[Char]`. In C++, overloads on two aliases of `double` are a redefinition. → Newtype the element and give it its own instance; the container's general instance composes with it (`deriving newtype` / `deriving via` to reuse behavior).
5. **Exported as if it were an abstraction.** Clients use the right-hand side's API directly, so the representation is frozen. Haskell's `type FilePath = String` could not be fixed in place; the fix is a new type (`newtype OsPath`) and a new API. Google's C++ guide warns that aliases "can create an unclear API contract". → Keep convenience aliases module-private, export an abstract type, or document that the alias is guaranteed to stay identical.
6. **Hides a quantifier or constraint** (Haskell). A value of type `type Lens s a = forall f. Functor f => …` cannot be stored in a list, a `Maybe`, or a record field without impredicativity. That is why `lens` ships `ReifiedLens` (a newtype) and `ALens`. → Newtype it where it must be stored.
7. **Renames the familiar, or chains aliases.** `type Str = String`; `type Row = Fields` with `type Fields = Map Text Value`. This adds indirection and no information. → Inline it.

Smells 1–3 share a symptom: errors and editor hovers often show the expanded type, so the name disappears where it would help most. For a `UserId`, TypeScript reports `Type 'number' is not assignable to type 'string'`.

### The code-review case: a multilingual name

<!-- check:skip -->
```haskell
-- Before: the concept and its container are one name.
type PermissionName = Multilingual NonEmptyString

-- After: the concept is a type; the container is chosen where it is used.
newtype PermissionName = PermissionName NonEmptyString

data Permission = Permission {permissionName :: Multilingual PermissionName}
```

After the change, `PermissionName` no longer unifies with a `RoleName` of the same shape. `localize :: Lang -> Multilingual a -> a` returns a `PermissionName` instead of a bare string. A name typed in one language, `[PermissionName]`, and `Maybe PermissionName` all have types. `Multilingual` stays one reusable functor, and `ToJSON PermissionName` belongs to permission names alone. Worked out in three languages in [examples.md](examples.md#5-an-alias-that-hides-a-container-the-multilingual-name).

### When an alias is right

- **Shorthand whose name restates its right-hand side:** `type Parser = Parsec Void Text`, `type State s = StateT s Identity`, `type Lens' s a = Lens s s a a`. Kowainik's style guide allows aliases "only for specializing general types". That condition is necessary but not sufficient: `Multilingual NonEmptyString` specializes a general type too, but `PermissionName` names a domain concept, not a shape.
- **Function types:** `type Handler = Request -> IO Response`, `type ShowS = String -> String`. These are mostly fine: wrapping a function type in a data type buys little, and two function types rarely get mixed up. The alias hides the parameter names, though, so document it: what each argument means and what the function must guarantee (`-- | Handles one request. Must not throw; failures become 5xx responses.`).
- **Naming a type that is already distinct:** a TypeScript union or object type (`type Shape = Circle | Square`), a C++ `std::variant`, or a tagged instantiation (`using CustomerId = Id<struct CustomerTag>`).
- **Module-private convenience:** in function bodies, private sections, or implementation files. Yang's advice is to keep synonyms unexported, as candidates for promotion to real data types.
- **Constraint synonyms:** `type App m = (MonadReader Env m, MonadIO m)`.
- **Gradual refactoring:** the old name aliases the new one while callers migrate. This is the reason Go added aliases.
- **An honest label** with no realistic mix-up, where a newtype would be noise ([examples.md §4](examples.md#4-newtype-noise)). A field name usually says it better.

Done when: no alias promises anything — each one abbreviates, names an already-distinct type, or is an honest label — and every name that carries meaning is a type.

## Example: an integer from 1 to 5

**Haskell**

```haskell
-- Intrinsic: the declaration is the invariant.
data OneToFive = One | Two | Three | Four | Five

ordinal :: OneToFive -> String
ordinal One = "first"
ordinal Two = "second"
ordinal Three = "third"
ordinal Four = "fourth"
ordinal Five = "fifth" -- exhaustive; a sixth constructor would be flagged here

-- Extrinsic: the invariant lives in toRanged; consumers still see an Int.
newtype Ranged = Ranged Int

toRanged :: Int -> Maybe Ranged
toRanged n
  | n >= 1 && n <= 5 = Just (Ranged n)
  | otherwise = Nothing

ordinalRanged :: Ranged -> String
ordinalRanged (Ranged n) = case n of
  1 -> "first"
  2 -> "second"
  3 -> "third"
  4 -> "fourth"
  5 -> "fifth"
  _ -> error "impossible: bad Ranged value" -- a hole punched through the type system
```

**TypeScript**

```typescript
// Intrinsic: a closed union of literals.
type OneToFive = 1 | 2 | 3 | 4 | 5;

export function ordinal(n: OneToFive): string {
  switch (n) {
    case 1: return "first";
    case 2: return "second";
    case 3: return "third";
    case 4: return "fourth";
    case 5: return "fifth";
  }
}

// Extrinsic: a brand is only a name; `42 as Ranged` forges one anywhere.
type Ranged = number & { readonly __brand: "Ranged" };

export const toRanged = (n: number): Ranged | undefined =>
  Number.isInteger(n) && n >= 1 && n <= 5 ? (n as Ranged) : undefined;

export function ordinalRanged(n: Ranged): string {
  const names = ["first", "second", "third", "fourth", "fifth"];
  const name = names[n - 1];
  if (name === undefined) throw new Error("impossible: bad Ranged value");
  return name;
}
```

**C++**

```cpp
#include <optional>
#include <stdexcept>
#include <string>
#include <utility>

// Closed in intent, but not intrinsically: static_cast<OneToFive>(6) compiles.
enum class OneToFive { One = 1, Two, Three, Four, Five };

std::string ordinal(OneToFive n) {
  switch (n) {  // -Wswitch flags a missing enumerator ...
    case OneToFive::One: return "first";
    case OneToFive::Two: return "second";
    case OneToFive::Three: return "third";
    case OneToFive::Four: return "fourth";
    case OneToFive::Five: return "fifth";
  }
  std::unreachable();  // ... but the compiler still needs this: enums are open
}

// Extrinsic: an opaque token issued by a trusted class.
class Ranged {
public:
  static std::optional<Ranged> make(int n) {
    if (n < 1 || n > 5) return std::nullopt;
    return Ranged(n);
  }
  int value() const { return n_; }
private:
  explicit Ranged(int n) : n_(n) {}
  int n_;
};

std::string ordinalRanged(Ranged r) {
  static const char* names[] = {"first", "second", "third", "fourth", "fifth"};
  if (r.value() < 1 || r.value() > 5) throw std::logic_error("impossible: bad Ranged value");
  return names[r.value() - 1];
}
```

More examples — a non-empty list as a trusted token vs a constructive type, the holes that forge tokens, labels that prevent mix-ups, newtype noise, an alias that hides a container, and instances or overloads on an alias — in all three languages: [examples.md](examples.md).

## Related skills

`correctness-by-construction` · `smart-constructor` · `make-illegal-states-unrepresentable` · `parse-dont-validate` · `airtight-abstractions` (trust boundaries) · `property-based-testing` (testing a trusted module's API) · `boolean-blindness`

## Sources

- **Alexis King, [Names are not type safety](https://lexi-lambda.github.io/blog/2020/11/01/names-are-not-type-safety/) (2020).**
- Alexis King, [Types as axioms, or: playing god with static types](https://lexi-lambda.github.io/blog/2020/08/13/types-as-axioms-or-playing-god-with-static-types/) (2020).
- Gabriella Gonzalez, [Ergonomic newtypes for Haskell strings and numbers](https://haskellforall.com/2023/04/ergonomic-newtypes-for-haskell-strings) (2023).
- Scott Wlaschin, [Designing with types: Single case union types](https://fsharpforfunandprofit.com/posts/designing-with-types-single-case-dus/) and [Non-string types](https://fsharpforfunandprofit.com/posts/designing-with-types-non-strings/) (2013).
- David Luposchainsky (quchen), [Algebraic blindness](https://github.com/quchen/articles/blob/master/algebraic-blindness.md).
- Further reading cited by the source: Freckle, *Tagged is not a Newtype* (2020).

Type aliases:

- **Edward Z. Yang, [On type synonyms](https://blog.ezyang.com/2011/06/on-type-synonyms/) (2011)** — removing container synonyms such as `type CmmActuals = [CmmActual]` from GHC; function-type synonyms are mostly fine if documented; keep other synonyms unexported, as candidates for promotion to data types.
- Kowainik, [Haskell Style Guide](https://github.com/kowainik/org/blob/main/style-guide.md) (aliases only for specializing general types) and [Haskell mini-patterns handbook](https://kowainik.github.io/posts/haskell-mini-patterns) (2020), *Newtype* (`type WorkerId = UUID`).
- Julian Ospald, [Fixing 'FilePath' in Haskell](https://hasufell.github.io/posts/2022-06-29-fixing-haskell-filepaths.html) (2022) — `type FilePath = String` replaced by `newtype OsPath`.
- GHC User's Guide, [Instance declarations](https://downloads.haskell.org/ghc/latest/docs/users_guide/exts/instances.html) (`TypeSynonymInstances`: a synonym in an instance head is shorthand for its right-hand side); `lens`, [Control.Lens.Reified](https://hackage.haskell.org/package/lens/docs/Control-Lens-Reified.html).
- Google, [C++ Style Guide: Aliases](https://google.github.io/styleguide/cppguide.html#Aliases) — "Type aliases can create an unclear API contract"; document the intent of every public alias.
- Walter E. Brown, [Toward Opaque Typedefs for C++1Y, v2](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2013/n3741.pdf) (WG21 N3741, 2013) — why a transparent `typedef` cannot keep `double`s apart.
- The same rule in other languages: [The Rust Programming Language, *Advanced Types*](https://doc.rust-lang.org/book/ch20-03-advanced-types.html) · Russ Cox & Robert Griesemer, [Go type alias proposal](https://github.com/golang/proposal/blob/master/design/18130-type-alias.md) (2016; aliases exist for gradual code repair) · [Kotlin KEEP: type aliases](https://github.com/Kotlin/KEEP/blob/master/proposals/type-aliases.md) ("Type aliases do not introduce new types") · Scott Wlaschin, [Type abbreviations](https://fsharpforfunandprofit.com/posts/type-abbreviations/) (F#).
