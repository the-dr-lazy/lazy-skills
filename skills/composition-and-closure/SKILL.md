---
name: composition-and-closure
description: Composition and closure — combining components yields a component of the same kind (monoids, categories, functors, applicatives), giving flat architectures. Use when designing combinators, pipelines, validators, middleware, or plugin systems, or when components need adapters to combine.
---

# Composition and closure

> *functional-architecture.org:* "We like to combine small software structures to form larger structures – without cognitive overhead." (Principle page upstream TODO.)

**Closure** (in the algebraic sense): combining things of kind `A` yields a thing of kind `A`, indistinguishable in character from its parts. Numbers are closed under `+`: `3 + 4 + 9` is a number, not a "web of numbers". Compare the conventional architecture: combine components `A` into a network `B`; `B`s are not connectable, so wrap a network of `B`s into a `C`… an ever-growing tower of abstractions. Closed composition gives **flat architectures**: when you combine, the result is still combinable, so you never need another layer.

## The pattern family

| Structure | "Plus" (combine many into one) | "Zero" (combine none into one) | Laws |
|---|---|---|---|
| **Monoid** | `(<>) :: m -> m -> m` | `mempty :: m` | associativity, identity |
| **Category** (a typed monoid) | `(.) :: cat b c -> cat a b -> cat a c` | `id :: cat a a` | associativity, identity |
| **Applicative** (combine "horizontally") | `f a -> f b -> f (a, b)` | `f ()` | associativity, identity (up to isomorphism) |
| **Monad** (combine "vertically") | `join :: m (m a) -> m a` | `return :: a -> m a` | associativity, identity |
| **Functor** (the *adapter*) | maps components of one category into another, preserving composition | | `fmap id = id`, `fmap (f . g) = fmap f . fmap g` |

The **laws** are what make composition safe: associativity means grouping never matters (so no parentheses, no "order of assembly" to document); identity means there is always a neutral "empty" component (so "zero or more" is as easy as "one"). The **functor** pattern is the adapter: when two components do not fit (a `Controller KeyEvent` and a `Controller MouseEvent`), map both into a common type (`Controller (Either KeyEvent MouseEvent)`) instead of writing bespoke glue.

## Procedure

1. **Identify the component type** people keep combining (validators, handlers, middleware, event sources, views, queries, parsers, configurations).
2. **Define the combining operation so its result has the same type.** If the result "needs to be a different kind of thing", look for a common type both inputs can be mapped into (a functor, a sum type).
3. **Define the empty component** (validator that accepts everything, view that draws nothing, handler that does nothing).
4. **Check the laws** with property tests (`property-based-testing`): associativity and identity for monoids; the functor laws for adapters.
5. **Derive, don't hand-write, when you can:** functions into a monoid form a monoid; applicatives lift monoids (`liftA2 (<>)`); records of monoids form a monoid.

Done when: combining any number of components (including zero) produces the same type with a single operation, and the laws hold under property tests.

## Example: validators that compose

A validator of `a` returns the list of problems. Validators form a monoid (combine = concatenate problems, empty = no problems), and they adapt *contravariantly*: a validator of a field becomes a validator of the whole record by pre-composing an accessor.

**Haskell**

```haskell
import Data.Functor.Contravariant (Contravariant (..))

newtype Validator a = Validator {validate :: a -> [String]}

instance Semigroup (Validator a) where
  Validator f <> Validator g = Validator (\a -> f a <> g a)

instance Monoid (Validator a) where
  mempty = Validator (const [])

instance Contravariant Validator where -- the adapter: from a part to the whole
  contramap f (Validator v) = Validator (v . f)

check :: String -> (a -> Bool) -> Validator a
check msg ok = Validator (\a -> [msg | not (ok a)])

data User = User {name :: String, age :: Int}

nameV :: Validator String
nameV = check "name is empty" (not . null) <> check "name too long" ((<= 50) . length)

ageV :: Validator Int
ageV = check "age must be positive" (> 0)

userV :: Validator User -- built only from smaller validators, with one operator
userV = contramap name nameV <> contramap age ageV

-- validate userV (User "" (-1)) == ["name is empty", "age must be positive"]
```

**TypeScript**

```typescript
type Validator<A> = (a: A) => string[];

const combine = <A,>(...vs: Validator<A>[]): Validator<A> => (a) => vs.flatMap((v) => v(a)); // mconcat
const empty = <A,>(): Validator<A> => () => []; // mempty
const contramap = <A, B>(f: (b: B) => A, v: Validator<A>): Validator<B> => (b) => v(f(b));
const check = <A,>(msg: string, ok: (a: A) => boolean): Validator<A> => (a) => (ok(a) ? [] : [msg]);

type User = { readonly name: string; readonly age: number };

const nameV = combine<string>(check("name is empty", (s) => s.length > 0), check("name too long", (s) => s.length <= 50));
const ageV = check<number>("age must be positive", (n) => n > 0);

export const userV: Validator<User> = combine(
  contramap((u: User) => u.name, nameV),
  contramap((u: User) => u.age, ageV),
);
export const noRules = empty<User>();
```

**C++**

```cpp
#include <functional>
#include <string>
#include <vector>

template <typename A>
using Validator = std::function<std::vector<std::string>(const A&)>;

template <typename A>
Validator<A> operator+(Validator<A> f, Validator<A> g) {  // combine
  return [f, g](const A& a) {
    auto out = f(a);
    auto more = g(a);
    out.insert(out.end(), more.begin(), more.end());
    return out;
  };
}

template <typename A>
Validator<A> empty() { return [](const A&) { return std::vector<std::string>{}; }; }

template <typename B, typename A, typename F>
Validator<B> contramap(F f, Validator<A> v) { return [f, v](const B& b) { return v(f(b)); }; }

template <typename A, typename P>
Validator<A> check(std::string msg, P ok) {
  return [msg, ok](const A& a) { return ok(a) ? std::vector<std::string>{} : std::vector<std::string>{msg}; };
}

struct User { std::string name; int age; };

Validator<User> userValidator() {
  Validator<std::string> nameV = check<std::string>("name is empty", [](const std::string& s) { return !s.empty(); }) +
                                 check<std::string>("name too long", [](const std::string& s) { return s.size() <= 50; });
  Validator<int> ageV = check<int>("age must be positive", [](int n) { return n > 0; });
  return contramap<User>([](const User& u) { return u.name; }, nameV) +
         contramap<User>([](const User& u) { return u.age; }, ageV);
}
```

## Examples from the sources

- `mvc`: `View`s and `Controller`s are monoids (combining views sequences their effects; combining controllers interleaves their events), so a whole application has exactly one view and one controller; functors (`fmap`, `handles`) unify their types; `Managed` resources combine applicatively.
- `foldl`: folds combine applicatively and still traverse the data once.
- The "wizard" monoid: `IO` actions returning monoids combine, so prompts-then-actions wizards compose into bigger wizards.
- Optics are monoids: `Fold`s combine with `<>` into a fold over all their targets.
- Unix pipes and function composition: the category pattern.

## Related skills

`algebraic-modelling` · `everything-as-a-value` · `composable-guis` · `composable-error-handling` · `bidirectional-data-transformations` · `modularization` · `property-based-testing` (checking the laws)

## Sources

- functional-architecture.org, [Composition and Closure](https://functional-architecture.org/composition/) (principle page; upstream TODO).
- Gabriella Gonzalez, [Scalable program architectures](https://haskellforall.com/2014/04/scalable-program-architectures) (2014), [The category design pattern](https://haskellforall.com/2012/08/the-category-design-pattern) (2012), [The functor design pattern](https://haskellforall.com/2012/09/the-functor-design-pattern) (2012), [Model-view-controller, Haskell-style](https://haskellforall.com/2014/04/model-view-controller-haskell-style) (2014), [Composable streaming folds](https://haskellforall.com/2013/08/composable-streaming-folds) (2013), [The wizard monoid](https://haskellforall.com/2018/02/the-wizard-monoid) (2018), [Optics are monoids](https://haskellforall.com/2021/09/optics-are-monoids) (2021), [Applicatives should usually implement Semigroup and Monoid](https://haskellforall.com/2022/03/applicatives-should-usually-implement) (2022).
