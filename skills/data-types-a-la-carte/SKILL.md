---
name: data-types-a-la-carte
description: Data types à la carte — solve the expression problem (add cases and operations without editing existing code) with coproducts of functors, or object algebras in TypeScript and C++. Use when plugins extend a sum type, or when designing extensible interpreters and DSLs.
---

# Data types à la carte

> *functional-architecture.org:* "«Data types à la carte» is a technique to deal with the dreaded Expression Problem in functional languages." (Pattern page upstream TODO; technique after Wouter Swierstra, 2008.)

**The expression problem:** with an algebraic data type, adding a new *operation* is easy (write a function) but adding a new *case* means editing the type and every function over it. With an object hierarchy it is the reverse. The goal is to add both, **without modifying or recompiling existing code, and with static type safety**.

**Data types à la carte** splits a data type into one functor per constructor, combines them with a coproduct `:+:`, and closes the recursion with a fixed point `Fix`. Each interpretation is a type class with one instance per constructor functor. New constructor: a new functor plus instances. New interpretation: a new class plus instances. A subsumption class `:<:` injects constructors into any signature that contains them, so smart constructors work for every "menu" that includes them. The same idea — coproducts of functors — is how **extensible effects** combine independent effect signatures (`free-monads`, `algebraic-effect-systems`).

In languages without higher-kinded types, the practical answer is **object algebras** (tagless final): a generic interface with one method per constructor; programs are written against the interface; interpretations are implementations; new constructors extend the interface.

## Procedure

1. Decide the axis of extension: new cases? new operations? both? Only one axis → a plain ADT (operations) or an interface (cases) is simpler.
2. **Both axes, Haskell:** one functor per case, `:+:` for the menu, `Fix` for recursion, one class per interpretation, `:<:` for injection.
3. **Both axes, TypeScript/C++:** an algebra interface `Alg<E>` per group of constructors; extend interfaces for new constructors; programs are generic functions `<E>(alg: Alg<E>) => E`; each interpretation is an implementation of the algebra.
4. Keep the menu at the edges: libraries export constructors and interpretations; applications choose the combination.
5. Measure the ergonomics cost (type errors, instance boilerplate) against how often the extension actually happens; many codebases need only one axis.

Done when: adding a constructor or an interpretation is a new module that compiles against unchanged existing modules, and existing programs still type-check.

## Example: expressions extended with multiplication and rendering after the fact

**Haskell** (Swierstra's encoding)

```haskell
{-# LANGUAGE DeriveFunctor #-}
{-# LANGUAGE FlexibleContexts #-}
{-# LANGUAGE FlexibleInstances #-}
{-# LANGUAGE MultiParamTypeClasses #-}
{-# LANGUAGE TypeOperators #-}

newtype Fix f = In (f (Fix f))

foldFix :: Functor f => (f a -> a) -> Fix f -> a
foldFix alg (In t) = alg (fmap (foldFix alg) t)

-- The coproduct of functors: the "menu".
data (f :+: g) e = Inl (f e) | Inr (g e) deriving (Functor)
infixr 6 :+:

newtype Val e = Val Int deriving (Functor)
data Add e = Add e e deriving (Functor)

-- An interpretation: one instance per constructor functor.
class Functor f => Eval f where
  evalAlg :: f Int -> Int

instance Eval Val where evalAlg (Val n) = n
instance Eval Add where evalAlg (Add a b) = a + b
instance (Eval f, Eval g) => Eval (f :+: g) where
  evalAlg (Inl x) = evalAlg x
  evalAlg (Inr y) = evalAlg y

eval :: Eval f => Fix f -> Int
eval = foldFix evalAlg

-- Automatic injection into any signature containing the constructor.
class (Functor sub, Functor sup) => sub :<: sup where
  inj :: sub a -> sup a

instance Functor f => f :<: f where inj = id
instance {-# OVERLAPPING #-} (Functor f, Functor g) => f :<: (f :+: g) where inj = Inl
instance {-# OVERLAPPABLE #-} (Functor f, Functor g, Functor h, f :<: g) => f :<: (h :+: g) where inj = Inr . inj

inject :: g :<: f => g (Fix f) -> Fix f
inject = In . inj

val :: Val :<: f => Int -> Fix f
val n = inject (Val n)

add :: Add :<: f => Fix f -> Fix f -> Fix f
add a b = inject (Add a b)

-- Later, elsewhere, without editing the code above: a new constructor ...
data Mul e = Mul e e deriving (Functor)
instance Eval Mul where evalAlg (Mul a b) = a * b

mul :: Mul :<: f => Fix f -> Fix f -> Fix f
mul a b = inject (Mul a b)

-- ... and a new interpretation.
class Functor f => Render f where
  renderAlg :: f String -> String

instance Render Val where renderAlg (Val n) = show n
instance Render Add where renderAlg (Add a b) = "(" <> a <> " + " <> b <> ")"
instance Render Mul where renderAlg (Mul a b) = "(" <> a <> " * " <> b <> ")"
instance (Render f, Render g) => Render (f :+: g) where
  renderAlg (Inl x) = renderAlg x
  renderAlg (Inr y) = renderAlg y

example :: Fix (Val :+: Add :+: Mul)
example = mul (val 2) (add (val 3) (val 4))

main :: IO ()
main = putStrLn (foldFix renderAlg example <> " = " <> show (eval example)) -- (2 * (3 + 4)) = 14
```

**TypeScript** (object algebras)

```typescript
// Constructors as an algebra interface; programs are generic over the carrier E.
interface ExpAlg<E> {
  val(n: number): E;
  add(a: E, b: E): E;
}

const evalExp: ExpAlg<number> = { val: (n) => n, add: (a, b) => a + b };

// Later, elsewhere, without editing the code above: a new constructor ...
interface MulAlg<E> extends ExpAlg<E> {
  mul(a: E, b: E): E;
}
const evalMul: MulAlg<number> = { ...evalExp, mul: (a, b) => a * b };

// ... and a new interpretation.
const render: MulAlg<string> = {
  val: (n) => String(n),
  add: (a, b) => `(${a} + ${b})`,
  mul: (a, b) => `(${a} * ${b})`,
};

// Old programs keep working with every newer algebra.
export const three = <E,>(alg: ExpAlg<E>): E => alg.add(alg.val(1), alg.val(2));
export const example = <E,>(alg: MulAlg<E>): E => alg.mul(alg.val(2), alg.add(alg.val(3), alg.val(4)));

export const result = `${example(render)} = ${example(evalMul)}`; // "(2 * (3 + 4)) = 14"
export const old = three(render); // "(1 + 2)"
```

**C++** (object algebras with concepts)

```cpp
#include <concepts>
#include <iostream>
#include <string>

template <typename Alg>
concept ExpAlg = requires(Alg alg, typename Alg::Carrier e) {
  { alg.val(1) } -> std::same_as<typename Alg::Carrier>;
  { alg.add(e, e) } -> std::same_as<typename Alg::Carrier>;
};

struct Eval {
  using Carrier = int;
  int val(int n) const { return n; }
  int add(int a, int b) const { return a + b; }
};

// Later, elsewhere: a new constructor ...
template <typename Alg>
concept MulAlg = ExpAlg<Alg> && requires(Alg alg, typename Alg::Carrier e) {
  { alg.mul(e, e) } -> std::same_as<typename Alg::Carrier>;
};

struct EvalMul : Eval {
  int mul(int a, int b) const { return a * b; }
};

// ... and a new interpretation.
struct Render {
  using Carrier = std::string;
  std::string val(int n) const { return std::to_string(n); }
  std::string add(const std::string& a, const std::string& b) const { return "(" + a + " + " + b + ")"; }
  std::string mul(const std::string& a, const std::string& b) const { return "(" + a + " * " + b + ")"; }
};

template <ExpAlg Alg>
auto three(const Alg& alg) { return alg.add(alg.val(1), alg.val(2)); }  // an old program

template <MulAlg Alg>
auto example(const Alg& alg) { return alg.mul(alg.val(2), alg.add(alg.val(3), alg.val(4))); }

int main() {
  std::cout << example(Render{}) << " = " << example(EvalMul{}) << '\n';  // (2 * (3 + 4)) = 14
  std::cout << three(Render{}) << '\n';                                   // (1 + 2)
}
```

## Related skills

`trees-that-grow` (extensibility across compiler phases) · `free-monads` and `algebraic-effect-systems` (coproducts of effect functors) · `embedded-dsl` · `everything-as-a-value` · `composition-and-closure`

## Sources

- functional-architecture.org, [Data types à la carte](https://functional-architecture.org/data_types_a_la_carte/) (pattern; short description, long form upstream TODO).
- Further reading (not in the provided source list): Wouter Swierstra, *Data types à la carte*, Journal of Functional Programming 18(4), 2008; Bruno C. d. S. Oliveira and William R. Cook, *Extensibility for the Masses: Practical Extensibility with Object Algebras* (ECOOP 2012); Philip Wadler, *The Expression Problem* (1998).
- Gabriella Gonzalez, [The visitor pattern is essentially the same thing as Church encoding](https://haskellforall.com/2021/01/the-visitor-pattern-is-essentially-same) (2021) — object algebras generalize the visitor.
