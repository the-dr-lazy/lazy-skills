---
name: trees-that-grow
description: Trees that grow — one ADT indexed by phase, with type-level functions choosing each constructor's extra fields and extra constructors. Use when one AST or domain type exists in several variants (parsed/typechecked, located, decorated) or near-duplicate types are drifting apart.
---

# Trees that grow

> *functional-architecture.org:* "«Trees that grow» is a method to make models built with algebraic data types more extensible." (Pattern page upstream TODO; technique after Shayan Najd and Simon Peyton Jones, 2017, and Ivan Perez, FUNARCH 2023.)

Compilers — and many data pipelines — carry the "same" data through phases: parsed (with source spans), renamed, typechecked (with types), desugared. Separate types per phase duplicate code and drift; one type with every field optional admits illegal states ("a parsed node with a type"). **Trees that grow** parameterizes the type by a **phase index** and lets a type-level function decide, per phase:

- the **extension field** of each constructor (`XLit p`: a source span when parsed, a type when typechecked, nothing when not needed);
- an **extension constructor** (`XExt p`: a new case, such as a coercion node that exists only after type checking, or an uninhabited type when the phase adds none).

The problem GHC set out to solve: one syntax tree reused across passes had grown pass-specific warts (`ValBindsOut`, `ConPatOut`, `SigPatOut`). The goals were to capture each variant only in the pass that has it, to let tool writers add their own extensions, and to harmonise the GHC, Template Haskell, and haskell-src-exts trees.

GHC's two placeholders are easy to conflate, so copy the split. An unused extension **point** (a field) gets `NoExtField`, an ordinary inhabited unit type, because some pass must still be able to build the node. An unused extension **constructor** gets `DataConCantHappen`, an uninhabited type eliminated by `dataConCantHappen x = case x of {}`. The same trick retires an *ordinary* constructor from one phase: GHC sets `XOverLabel GhcTc = DataConCantHappen`, since type-checker output never has an `OverLabel`, and functions over that phase match it with `dataConCantHappen x`. The impossible match arm must still be written unless the extension field is strict (GHC issue #18764).

A lighter relative, the **extensible type** pattern (Ivan Perez), applies a type function to *every* component (`Expr f` with `f (Expr f)` children): instantiate `f` with identity for plain trees, with "located" for traceability, or with `Either Error` for error recovery.

## Procedure

1. List the variants of the type that exist in the system (phases, decorations, partial/erroneous forms) and what each adds or removes.
2. Add a phase parameter; give every constructor an extension field and add one extension constructor.
3. Define, per phase, the type of each extension field (unit/"no field" when unused) and of the extension constructor (an empty type when there are no extra cases, so matching on it is trivially total).
4. Write phase transitions as functions `Expr Parsed -> Either Error (Expr Typed)`; phase-independent functions stay polymorphic in the phase.
5. Keep the extension types in one place per phase so each phase's shape is readable at a glance.
6. Decide how child positions carry annotations. GHC makes locations an extension point too: `XRec p (HsExpr p)` replaces `Located (HsExpr p)`, so a pass can attach source spans (GHC), nothing (Template Haskell), types (HIE files), or exact-print annotations; a pass uninterested in locations can define `XRec NoLocated a = a`. Pass-polymorphic code reaches through the wrapper with classes such as `UnXRec` and `MapXRec`.

Done when: one definition serves all phases, each phase can express exactly its own extra information and cases, and illegal cross-phase combinations do not type-check.

## Example: a parsed and a typechecked expression tree

**Haskell** (type families, as in GHC)

```haskell
{-# LANGUAGE DataKinds #-}
{-# LANGUAGE EmptyCase #-}
{-# LANGUAGE KindSignatures #-}
{-# LANGUAGE TypeFamilies #-}
import Data.Kind (Type)

data Phase = Parsed | Typed

data SrcSpan = SrcSpan Int Int deriving (Show)
data Ty = TInt | TDouble deriving (Eq, Show)
data NoExt -- no values: the phase adds no constructor

type family XLit (p :: Phase) :: Type
type family XAdd (p :: Phase) :: Type
type family XExt (p :: Phase) :: Type

data Expr (p :: Phase)
  = Lit (XLit p) Int
  | Add (XAdd p) (Expr p) (Expr p)
  | Ext (XExt p) -- the extension constructor

type instance XLit 'Parsed = SrcSpan
type instance XAdd 'Parsed = SrcSpan
type instance XExt 'Parsed = NoExt

data Coerce = Coerce Ty (Expr 'Typed) -- a node that exists only after type checking

type instance XLit 'Typed = Ty
type instance XAdd 'Typed = Ty
type instance XExt 'Typed = Coerce

typeOf :: Expr 'Typed -> Ty
typeOf (Lit t _) = t
typeOf (Add t _ _) = t
typeOf (Ext (Coerce t _)) = t

typecheck :: Expr 'Parsed -> Expr 'Typed
typecheck (Lit _ n) = Lit TInt n
typecheck (Add _ a b) = Add TInt (typecheck a) (typecheck b)
typecheck (Ext none) = case none of {} -- impossible by construction: NoExt has no values

-- Phase-independent code stays polymorphic in the phase.
size :: Expr p -> Int
size (Lit _ _) = 1
size (Add _ a b) = 1 + size a + size b
size (Ext _) = 1
```

**TypeScript** (an interface as a type-level function from phase to extensions)

```typescript
type SrcSpan = { from: number; to: number };
type Ty = "int" | "double";

// The type-level function: phase -> extension types.
interface Extensions {
  parsed: { lit: SrcSpan; add: SrcSpan; ext: never }; // never: parsed trees have no extra node
  typed: { lit: Ty; add: Ty; ext: { coerceTo: Ty; inner: Expr<"typed"> } };
}
type Phase = keyof Extensions;

export type Expr<P extends Phase> =
  | { tag: "lit"; x: Extensions[P]["lit"]; value: number }
  | { tag: "add"; x: Extensions[P]["add"]; left: Expr<P>; right: Expr<P> }
  | { tag: "ext"; x: Extensions[P]["ext"] };

export function typecheck(e: Expr<"parsed">): Expr<"typed"> {
  switch (e.tag) {
    case "lit": return { tag: "lit", x: "int", value: e.value };
    case "add": return { tag: "add", x: "int", left: typecheck(e.left), right: typecheck(e.right) };
    case "ext": return e.x; // e.x has type never: this case cannot occur
  }
}

export function size<P extends Phase>(e: Expr<P>): number {
  return e.tag === "add" ? 1 + size(e.left) + size(e.right) : 1;
}
```

**C++** (a traits template as the type-level function)

```cpp
#include <memory>
#include <variant>

struct Parsed {};
struct Typed {};
struct SrcSpan { int from, to; };
enum class Ty { Int, Double };
struct NoExt { NoExt() = delete; };  // cannot be constructed: no extra node in this phase

template <typename P> struct Expr;
template <typename P> using ExprPtr = std::shared_ptr<const Expr<P>>;

template <typename P> struct Ext;  // the type-level function: phase -> extension types
template <> struct Ext<Parsed> { using Lit = SrcSpan; using Add = SrcSpan; using Extra = NoExt; };
struct Coerce { Ty to; ExprPtr<Typed> inner; };
template <> struct Ext<Typed> { using Lit = Ty; using Add = Ty; using Extra = Coerce; };

template <typename P>
struct Expr {
  struct Lit { typename Ext<P>::Lit x; int value; };
  struct Add { typename Ext<P>::Add x; ExprPtr<P> left, right; };
  struct Extra { typename Ext<P>::Extra x; };
  std::variant<Lit, Add, Extra> node;
};

ExprPtr<Typed> typecheck(const Expr<Parsed>& e) {
  using T = Expr<Typed>;
  if (auto* lit = std::get_if<Expr<Parsed>::Lit>(&e.node))
    return std::make_shared<const T>(T{T::Lit{Ty::Int, lit->value}});
  const auto& add = std::get<Expr<Parsed>::Add>(e.node);  // Extra is uninhabited for Parsed
  return std::make_shared<const T>(T{T::Add{Ty::Int, typecheck(*add.left), typecheck(*add.right)}});
}

template <typename P>
int size(const Expr<P>& e) {
  if (auto* add = std::get_if<typename Expr<P>::Add>(&e.node)) return 1 + size(*add->left) + size(*add->right);
  return 1;
}
```

## Pitfalls

- **Printing and branching on the phase need extra constraints.** To pretty-print the tree, GHC must know that its identifiers are `Outputable`, and it sometimes branches on the pass (for instance to print types once they exist). It bundles the constraints as `OutputableBndrId` (`OutputableBndr` plus `IsPass`), and using that constraint in instances generally requires `UndecidableInstances`.
- **Uninhabited is not unit.** Using an empty type for an unused *field* makes the node unbuildable in that phase; using a unit type for an unused *constructor* leaves a case every consumer must handle.

## Related skills

`data-types-a-la-carte` (the expression problem more generally) · `make-illegal-states-unrepresentable` (phase-specific fields instead of optional ones) · `correctness-by-construction` · `embedded-dsl` · `bidirectional-data-transformations`

## Sources

- functional-architecture.org, [Trees that grow](https://functional-architecture.org/trees_that_grow/) (pattern; short description, long form upstream TODO).
- Ivan Perez, [Types that Change: The Extensible Type Design Pattern](https://ivanperez.io/#typesthatchange) (FUNARCH 2023).
- Jeffrey M. Young, Sylvain Henry, John Ericson, [Stretching the Glasgow Haskell Compiler](https://dl.acm.org/doi/10.1145/3609025.3609476) (FUNARCH 2023) — GHC's architecture, whose AST uses Trees that Grow.
- GHC developers, [`Language.Haskell.Syntax.Extension`](https://github.com/ghc/ghc/blob/master/compiler/Language/Haskell/Syntax/Extension.hs) (GHC source, read September 2026: *Note [Trees That Grow]*, *Note [Constructor cannot occur]*, *Note [XRec and SrcSpans in the AST]* and the definitions beside them; the note points to the GHC wiki page *Implementing Trees That Grow*, which could not be fetched) — the goals, `NoExtField` versus `DataConCantHappen`, `XRec`, and the instance wrinkle.
- Further reading (not in the provided source list): Shayan Najd and Simon Peyton Jones, *Trees that Grow*, Journal of Universal Computer Science 23(1), 2017.
