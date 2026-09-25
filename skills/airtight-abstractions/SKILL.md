---
name: airtight-abstractions
description: Airtight abstractions — define an abstraction by its operations and laws, hide its representation, and close leaks (derived equality, serialization, casts, exposed constructors). Use when designing or reviewing a module or library API, or when representation changes break clients.
---

# Airtight abstractions

> *functional-architecture.org:* "Abstraction is the sharpest weapon of reason. Functional software architects welcome abstraction as a tool for coping with complexity." (Principle page upstream TODO.)

An abstraction is **airtight** when a client can observe nothing but what the interface promises: it cannot inspect, forge, or depend on the representation, so the implementation can change freely and the client's reasoning stays valid. Functional programming offers unusually good tools for this — abstract data types with hidden constructors, parametric polymorphism ("cannot inspect what you do not know"), laws that pin down meaning, and `denotational-design` to say *what* an abstraction means before *how* it is built.

## Where abstractions leak

- **Structural equality and ordering** on the representation: two equal queues stored differently compare unequal.
- **Derived instances** that construct or deconstruct (`Generic`, `Read`, JSON), and debug output (`Show`) that exposes internals clients then parse.
- **Exposed constructors / fields**, and in TypeScript, structural typing and `as` casts; in C++, public members, `friend`s, and aggregate initialization.
- **Partial operations** whose failure modes reveal representation (an exception message, an index error).
- **Iteration order, identity, and performance** that clients start relying on ("the list is always sorted").
- **Pattern matching on constructors** in the public API: offer smart constructors and eliminators (folds, prisms) instead, which decouple the interface from the representation.

## Procedure

1. **State the meaning.** Write the operations and the laws that relate them (`pop (push x empty) == Just (x, empty)`; `toList (fromList xs) == xs`). If you can, give a simple model (`toList` into a list) that defines what every operation means (`denotational-design`).
2. **Hide the representation**: export the type abstractly (Haskell export lists, OCaml/F# signatures, TypeScript `#private` class fields, C++ private members).
3. **Define observations through the model, not the representation** — equality, ordering, show, serialization all go via the model.
4. **Close the leaks** from the list above; prefer eliminators over exposed constructors.
5. **Test the laws against the model** with property-based tests; they are the contract with every client.
6. **Keep abstractions earned.** Abstraction for its own sake is a known worst practice ("architecture astronauts"); an abstraction pays off when it hides a decision someone would otherwise have to understand (`modularization`).

Done when: replacing the representation (and nothing else) cannot change the behaviour of any client, and the laws are property-tested.

## Example: a queue whose representation cannot leak

A two-list queue stores `[1]` as `Queue [1] []` or `Queue [] [1]`. Derived equality would call them different; equality through the model does not.

**Haskell**

```haskell
module Queue (Queue, empty, push, pop, toList) where -- constructor not exported

data Queue a = Queue [a] [a] -- front, reversed back

empty :: Queue a
empty = Queue [] []

push :: a -> Queue a -> Queue a
push x (Queue f b) = Queue f (x : b)

pop :: Queue a -> Maybe (a, Queue a)
pop (Queue [] []) = Nothing
pop (Queue [] b) = pop (Queue (reverse b) [])
pop (Queue (x : f) b) = Just (x, Queue f b)

toList :: Queue a -> [a] -- the model: what a queue *means*
toList (Queue f b) = f <> reverse b

instance Eq a => Eq (Queue a) where -- observed through the model, never the representation
  q == r = toList q == toList r

instance Show a => Show (Queue a) where
  show q = "fromList " <> show (toList q)
```

**TypeScript**

```typescript
export class Queue<A> {
  readonly #front: readonly A[];
  readonly #back: readonly A[];
  private constructor(front: readonly A[], back: readonly A[]) {
    this.#front = front;
    this.#back = back;
  }
  static empty<A>(): Queue<A> {
    return new Queue<A>([], []);
  }
  push(x: A): Queue<A> {
    return new Queue(this.#front, [x, ...this.#back]);
  }
  pop(): [A, Queue<A>] | undefined {
    if (this.#front.length === 0 && this.#back.length === 0) return undefined;
    if (this.#front.length === 0) return new Queue([...this.#back].reverse(), []).pop();
    const [x, ...rest] = this.#front;
    return [x as A, new Queue(rest, this.#back)];
  }
  toArray(): A[] {
    return [...this.#front, ...[...this.#back].reverse()]; // the model
  }
  equals(other: Queue<A>): boolean {
    const a = this.toArray();
    const b = other.toArray();
    return a.length === b.length && a.every((x, i) => x === b[i]);
  }
  toJSON(): A[] {
    return this.toArray(); // serialization goes through the model too
  }
}
```

**C++**

```cpp
#include <algorithm>
#include <optional>
#include <utility>
#include <vector>

template <typename A>
class Queue {
public:
  Queue push(A x) const {
    Queue q = *this;
    q.back_.push_back(std::move(x));
    return q;
  }
  std::optional<std::pair<A, Queue>> pop() const {
    Queue q = *this;
    if (q.front_.empty()) {
      q.front_.assign(q.back_.rbegin(), q.back_.rend());
      q.back_.clear();
    }
    if (q.front_.empty()) return std::nullopt;
    A x = q.front_.front();
    q.front_.erase(q.front_.begin());
    return std::pair{x, q};
  }
  std::vector<A> toVector() const {  // the model
    std::vector<A> out = front_;
    out.insert(out.end(), back_.rbegin(), back_.rend());
    return out;
  }
  friend bool operator==(const Queue& a, const Queue& b) { return a.toVector() == b.toVector(); }

private:
  std::vector<A> front_, back_;  // representation: invisible to clients
};
```

## Related skills

`denotational-design` · `modularization` · `names-are-not-type-safety` (trust boundaries and their holes) · `decoupled-by-default` · `bidirectional-data-transformations` (prisms decouple interface from representation) · `property-based-testing` · `algebraic-modelling`

## Sources

- functional-architecture.org, [Airtight Abstractions](https://functional-architecture.org/abstraction/) (principle page; upstream TODO) and [Denotational Design](https://functional-architecture.org/denotational_design/) ("a methodology to build airtight abstraction barriers").
- **Alexis King, [Names are not type safety](https://lexi-lambda.github.io/blog/2020/11/01/names-are-not-type-safety/)** (2020) — abstraction boundaries as trust boundaries; derived `Generic`/`Read` instances as holes.
- Alexis King, [Climbing the infinite ladder of abstraction](https://lexi-lambda.github.io/blog/2016/08/11/climbing-the-infinite-ladder-of-abstraction/) (2016).
- Gabriella Gonzalez, [total-1.0.0: Exhaustive pattern matching using traversals, prisms, and lenses](https://haskellforall.com/2015/01/total-100-exhaustive-pattern-matching) (2015), [Explicit is better than implicit](https://haskellforall.com/2015/10/explicit-is-better-than-implicit) (2015), [Worst practices should be hard](https://haskellforall.com/2016/04/worst-practices-should-be-hard) (2016, "excessive abstraction").
