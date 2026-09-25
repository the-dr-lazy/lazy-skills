---
name: functional-programming-languages
description: Use of functional programming languages — pick languages whose defaults reward functional design, and translate FP idioms (sum types, matching, Option/Result, immutability, visitors as Church encodings) into TypeScript, C++, and others. Use when choosing a stack or applying FP in a mainstream language.
---

# Use of functional programming languages

> *functional-architecture.org:* "Functional software architecture is best done in proper functional programming languages." (Pattern page upstream TODO.)

Two claims, both important:

1. **Languages create incentives.** In a language that makes the best practices the *shortest* code — non-null by default, effects visible in types, immutable by default, most-general types inferred, records cheaper than dictionaries — teams keep doing the right thing under deadline pressure. In a language that rewards shortcuts, culture must fight the grain, and that does not scale across teams and dependencies. ("Worst practices should be hard.")
2. **The ideas travel.** Functional programming, used as a style, restricts itself to timeless features — scalars, algebraic data types (records and tagged unions), recursion, first-class functions — which exist, or can be encoded, almost everywhere. Error handling becomes a tagged union, loops become recursion (or stay loops), dependency injection becomes a higher-order function. These idioms outlive frameworks and port between languages; object-oriented and imperative idioms port much worse.

## When the language is yours to choose

Weigh: the defaults (null, mutation, effects, exhaustiveness), the type system's expressiveness, the ecosystem for your domain, hiring and training (FUNARCH experience reports show architects without FP background can be trained — the iSAQB FUNAR curriculum), interoperability, and **performance**. Performance is often an *architectural* property: functional programs run fast when their architecture has mechanical sympathy (data layout, allocation, parallelism), and many teams chose Go or Rust for tools after writing functional TypeScript, because they could not reach their performance goals otherwise (Feldman, FUNARCH 2026). Choose the architecture with the machine in mind, not only the paradigm.

## When the language is fixed: translation table

| Idea | Haskell | TypeScript | C++ (20/23) |
|---|---|---|---|
| Product type | `data P = P {..}` | object type, `readonly` fields | `struct` |
| Sum type | `data S = A \| B` | discriminated union (`kind` tag) | `std::variant` (or a closed hierarchy + visitor) |
| Exhaustive match | `case`, `-Wincomplete-patterns` | `switch` + `never` check | `std::visit` with an overload set |
| Absence / failure | `Maybe`, `Either` | `T \| undefined`, `Result<T,E>` union | `std::optional`, `std::expected` |
| Immutability | default | `readonly`, `ReadonlyArray`, Immer | `const`, value semantics, `immer` |
| Newtype | `newtype` | branded type or class with `#private` | tag-templated struct, class with private ctor |
| Higher-order functions | default | arrow functions | lambdas, `std::function`, templates |
| Type classes | classes/instances | interfaces + dictionaries passed explicitly | concepts + overloads/templates |
| Higher-kinded types | `Functor f` | not available: specialize per type or encode (e.g. Effect's type lambdas) | template template parameters (limited) |
| Laziness / streams | default | generators, iterators | ranges/views, coroutines |
| Recursion | default, tail calls | recursion without TCO: prefer loops/`reduce` or trampolines | loops; recursion with care |
| Effects in types | `IO`, effect systems | Effect-TS, or capability parameters | capability parameters / concepts |
| Purity | enforced | convention | convention (`constexpr` helps) |

**Sum types without language support** can be Church-encoded: a value becomes a function that takes one handler per case. That is exactly the **visitor pattern**. With generics (Böhm–Berarducci encoding) the handlers can return any type; without generics, visitors are forced to return `void` and communicate through side effects — which is why a language with generics can recover sum types even when it lacks them natively.

## Procedure: applying a functional pattern in a non-functional language

1. State the pattern in functional terms (types, total functions, laws).
2. Map each construct through the table; prefer the native idiom when it preserves the guarantee (discriminated unions in TypeScript, `std::variant` in C++).
3. Where the guarantee cannot be preserved (purity, exhaustiveness in some languages), add conventions plus tooling (lint rules, `-Werror`, code review checklists) — and name the gap.
4. Keep the "functional" surface small and idiomatic for the team: a readable `Result` type beats a hand-rolled monad-transformer stack.

Done when: every functional construct used has a native or encoded equivalent with the same guarantee, and every guarantee that could not be preserved is documented where it is relied on.

## Example: a sum type, natively and as a visitor (Church encoding)

**Haskell**

```haskell
{-# LANGUAGE RankNTypes #-}
-- Native sum type
data Shape = Circle Double | Rectangle Double Double

area :: Shape -> Double
area (Circle r) = pi * r * r
area (Rectangle w h) = w * h

-- The same type, Church-encoded: a shape *is* its pattern match (the visitor pattern).
type ShapeC = forall r. (Double -> r) -> (Double -> Double -> r) -> r

circle :: Double -> ShapeC
circle r = \onCircle _ -> onCircle r

rectangle :: Double -> Double -> ShapeC
rectangle w h = \_ onRectangle -> onRectangle w h

areaC :: ShapeC -> Double
areaC s = s (\r -> pi * r * r) (\w h -> w * h)
```

**TypeScript**

```typescript
// Native: a discriminated union.
type Shape = { kind: "circle"; r: number } | { kind: "rectangle"; w: number; h: number };

export const area = (s: Shape): number => (s.kind === "circle" ? Math.PI * s.r * s.r : s.w * s.h);

// Church-encoded / visitor: a generic "accept" that returns whatever the visitor returns.
type ShapeVisitor<R> = { circle: (r: number) => R; rectangle: (w: number, h: number) => R };
type ShapeC = <R>(v: ShapeVisitor<R>) => R;

export const circle = (r: number): ShapeC => (v) => v.circle(r);
export const rectangle = (w: number, h: number): ShapeC => (v) => v.rectangle(w, h);

export const areaC = (s: ShapeC): number => s({ circle: (r) => Math.PI * r * r, rectangle: (w, h) => w * h });
```

**C++**

```cpp
#include <numbers>
#include <variant>

// Native (C++17+): std::variant.
struct Circle { double r; };
struct Rectangle { double w, h; };
using Shape = std::variant<Circle, Rectangle>;

template <class... Fs> struct overloaded : Fs... { using Fs::operator()...; };

double area(const Shape& s) {
  return std::visit(overloaded{
                        [](const Circle& c) { return std::numbers::pi * c.r * c.r; },
                        [](const Rectangle& r) { return r.w * r.h; },
                    },
                    s);
}

// The classic visitor pattern: a closed hierarchy plus double dispatch.
struct ShapeVisitor {
  virtual ~ShapeVisitor() = default;
  virtual void visitCircle(double r) = 0;
  virtual void visitRectangle(double w, double h) = 0;
};

struct ShapeObj {
  virtual ~ShapeObj() = default;
  virtual void accept(ShapeVisitor& v) const = 0;  // no generics here: results flow through side effects
};

struct CircleObj : ShapeObj {
  double r;
  explicit CircleObj(double r) : r(r) {}
  void accept(ShapeVisitor& v) const override { v.visitCircle(r); }
};

struct AreaVisitor : ShapeVisitor {
  double result = 0;
  void visitCircle(double r) override { result = std::numbers::pi * r * r; }
  void visitRectangle(double w, double h) override { result = w * h; }
};
```

## Related skills

`expressive-static-types` · `decoupled-by-default` (defaults as affordances) · `make-illegal-states-unrepresentable` · `composable-error-handling` · `composable-effects` · `immutability` · `everything-as-a-value`

## Sources

- functional-architecture.org, [Use of functional programming languages](https://functional-architecture.org/functional_programming_languages/) (pattern page; upstream TODO).
- Gabriella Gonzalez, [Worst practices should be hard](https://haskellforall.com/2016/04/worst-practices-should-be-hard) (2016), [Why I prefer functional programming](https://haskellforall.com/2020/10/why-i-prefer-functional-programming) (2020), [The visitor pattern is essentially the same thing as Church encoding](https://haskellforall.com/2021/01/the-visitor-pattern-is-essentially-same) (2021), [Sometimes less is more in language design](https://haskellforall.com/2013/08/sometimes-less-is-more-in-language) (2013).
- Richard Feldman, *Functional Mechanical Sympathy* ([FUNARCH 2026](https://functional-architecture.org/events/funarch-2026/)).
- Michael Sperber, [Six Years of FUNAR: Functional Training for Software Architects](https://dl.acm.org/doi/10.1145/3759163.3760428) (FUNARCH 2025).
- Michael Sperber, *Functional Programming in the Large — Status and Perspective* (FUNARCH 2023 opening talk).
- Will Crichton, [Typed Design Patterns for the Functional Era](https://dl.acm.org/doi/10.1145/3609025.3609477) (FUNARCH 2023) — functional design patterns in Rust.
