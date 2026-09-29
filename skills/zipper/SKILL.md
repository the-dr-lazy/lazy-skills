---
name: zipper
description: Zippers — an immutable structure plus a movable focus, with O(1) navigation and local edits. Use for cursors (editors, playlists, forms), focus in trees (file browsers, ASTs, UI trees), or repeated updates of "the current element" of a persistent structure.
---

# Zipper

> *functional-architecture.org:* "Zippers are efficient functional implementations of a *data structure* (such as a List or Tree) plus a *lens* into that data structure." (Pattern page upstream TODO; this skill adds Gérard Huet's original formulation.)

Updating an element deep inside an immutable structure normally means rebuilding the path from the root each time. A **zipper** keeps the structure *turned inside out around a focus*: the focused element, plus the context needed to rebuild the whole — for a list, the elements to the left (reversed) and to the right; for a tree, the path of parents with their other children. Moving the focus one step and editing at the focus are O(1); "zipping up" rebuilds the whole only when needed. Nothing is mutated, so every previous zipper is still valid (free undo).

Why not just remember a path? In a pure language one value is as good as another, so "the five to change" can only be named by *where* it is, for instance a list of directions `[R, L]` from the root. Every edit then walks from the root again, even when the next edit is next door. A zipper leaves breadcrumbs instead, so switching focus to a nearby part costs one step. Learn You a Haskell's image: the context is the part of the structure you are not focusing on, turned inside out like a sock, so moving up takes the top of the inverted part and un-inverts it.

It is the natural data structure for **cursors**: a text buffer, a playlist, the selected field in a form, the selected node in a tree view, the current position of an interpreter in an AST.

## Procedure

1. **Identify the focus** the application moves around and edits (a character, a track, a node).
2. **Choose the context representation:** list zipper = `(reversed prefix, focus, suffix)`; tree zipper = focus subtree + list of "crumbs" (parent value and sibling subtrees on each side). The design rule for a crumb: it holds everything needed to rebuild the parent (the parent's own data, which way you went, the siblings you did not visit) and *not* the focused subtree, which would duplicate information. A crumb is a node with a hole in it.
3. **Implement the moves** (`left`, `right`, `up`, `down`) returning `Maybe`/optional when the move is impossible — the edges are explicit. An unguarded move crashes: the first `goLeft` in Learn You a Haskell has no case for an empty tree, and `goUp` fails at the root. Every step can fail, so chain moves with `>>=` in the `Maybe` monad (C++23 `std::optional::and_then`).
4. **Implement edits at the focus** (`modify`, `insert`, `delete`) as O(1) operations on the context.
5. **Provide `fromX`/`toX`** to enter and leave the zipper; keep it an abstract type if invariants matter (`airtight-abstractions`).
6. **Keep old zippers** if you need undo/redo: they are persistent values.

Done when: navigation and edits at the focus do not rebuild the whole structure, every move handles the edges explicitly, and `toX . fromX` is the identity (property-tested).

## Example: a cursor over a playlist

**Haskell**

```haskell
data Zipper a = Zipper [a] a [a] -- left (reversed), focus, right
  deriving (Show)

fromList :: [a] -> Maybe (Zipper a)
fromList [] = Nothing
fromList (x : xs) = Just (Zipper [] x xs)

toList :: Zipper a -> [a]
toList (Zipper ls x rs) = reverse ls <> (x : rs)

focus :: Zipper a -> a
focus (Zipper _ x _) = x

left, right :: Zipper a -> Maybe (Zipper a)
left (Zipper (l : ls) x rs) = Just (Zipper ls l (x : rs))
left (Zipper [] _ _) = Nothing
right (Zipper ls x (r : rs)) = Just (Zipper (x : ls) r rs)
right (Zipper _ _ []) = Nothing

modify :: (a -> a) -> Zipper a -> Zipper a -- O(1), and the old zipper is untouched
modify f (Zipper ls x rs) = Zipper ls (f x) rs

insertAfter :: a -> Zipper a -> Zipper a
insertAfter y (Zipper ls x rs) = Zipper (x : ls) y rs
```

**TypeScript**

```typescript
// Persistent singly linked lists keep moves O(1) without copying arrays.
type List<A> = { head: A; tail: List<A> } | null;
const cons = <A,>(head: A, tail: List<A>): List<A> => ({ head, tail });

export type Zipper<A> = { readonly left: List<A>; readonly focus: A; readonly right: List<A> };

export function fromArray<A>(xs: readonly A[]): Zipper<A> | undefined {
  if (xs.length === 0) return undefined;
  const right = xs.slice(1).reduceRight<List<A>>((acc, x) => cons(x, acc), null);
  return { left: null, focus: xs[0] as A, right };
}

export function toArray<A>(z: Zipper<A>): A[] {
  const out: A[] = [];
  for (let l = z.left; l; l = l.tail) out.unshift(l.head);
  out.push(z.focus);
  for (let r = z.right; r; r = r.tail) out.push(r.head);
  return out;
}

export const left = <A,>(z: Zipper<A>): Zipper<A> | undefined =>
  z.left ? { left: z.left.tail, focus: z.left.head, right: cons(z.focus, z.right) } : undefined;

export const right = <A,>(z: Zipper<A>): Zipper<A> | undefined =>
  z.right ? { left: cons(z.focus, z.left), focus: z.right.head, right: z.right.tail } : undefined;

export const modify = <A,>(f: (a: A) => A, z: Zipper<A>): Zipper<A> => ({ ...z, focus: f(z.focus) });
```

**C++**

```cpp
#include <memory>
#include <optional>
#include <vector>

// A persistent list: sharing tails makes every move O(1) and keeps old zippers valid.
template <typename A>
struct Node {
  A head;
  std::shared_ptr<const Node> tail;
};
template <typename A>
using List = std::shared_ptr<const Node<A>>;

template <typename A>
List<A> cons(A x, List<A> xs) { return std::make_shared<const Node<A>>(Node<A>{std::move(x), std::move(xs)}); }

template <typename A>
struct Zipper {
  List<A> left;  // reversed
  A focus;
  List<A> right;
};

template <typename A>
std::optional<Zipper<A>> fromVector(const std::vector<A>& xs) {
  if (xs.empty()) return std::nullopt;
  List<A> right;
  for (auto it = xs.rbegin(); it != xs.rend() - 1; ++it) right = cons(*it, right);
  return Zipper<A>{nullptr, xs.front(), right};
}

template <typename A>
std::optional<Zipper<A>> moveRight(const Zipper<A>& z) {
  if (!z.right) return std::nullopt;
  return Zipper<A>{cons(z.focus, z.left), z.right->head, z.right->tail};
}

template <typename A>
std::optional<Zipper<A>> moveLeft(const Zipper<A>& z) {
  if (!z.left) return std::nullopt;
  return Zipper<A>{z.left->tail, z.left->head, cons(z.focus, z.right)};
}

template <typename A, typename F>
Zipper<A> modify(F f, Zipper<A> z) {
  z.focus = f(z.focus);  // a copy: the caller's zipper is untouched
  return z;
}
```

## Variations

- **Tree zippers** (Huet 1997): the context is a list of crumbs, each recording the parent's value and the siblings to the left and right of the path. Moves: `up`, `down` (to the first child), `left`/`right` among siblings.
- **Rose trees and file systems**: for a folder with any number of children, a crumb is the folder's name plus the items *before* and *after* the focus, two lists, so the hole's position is known and `up` is `ls ++ [item] ++ rs`. Files get no crumb, since you cannot go deeper into one; a file is like an empty tree. `topMost` (go up until there are no crumbs), `attach` (replace the focused subtree) and `rename`/`modify` (edit at the focus) complete a file-system cursor.
- **Zippers are derivatives**: the type of one-hole contexts of a data type is its derivative in the algebra of types (McBride) — a precise recipe for any algebraic data type.
- **Zippers and lenses**: a lens focuses on a part known statically; a zipper carries a focus that moves at run time (`bidirectional-data-transformations`).
- **Comonads**: a zipper with the focus as `extract` and "all possible refocusings" as `duplicate` is a comonad — useful for cellular automata and image filters.

## Related skills

`immutability` · `bidirectional-data-transformations` · `airtight-abstractions` · `composable-guis` (focus in UI trees) · `property-based-testing` (round trips and move/unmove laws)

## Sources

- functional-architecture.org, [Zipper](https://functional-architecture.org/zipper/) (pattern; short description, long form upstream TODO).
- Miran Lipovača, [Learn You a Haskell for Great Good!, chapter 14: Zippers](https://learnyouahaskell.com/zippers) (read from the [site's source](https://github.com/learnyouahaskell/learnyouahaskell.github.io/blob/main/source_md/zippers.md)) — why a path from the root is not enough, breadcrumbs as nodes with holes, list and file-system zippers, `Maybe`-based moves.
- Further reading (not in the provided source list): Gérard Huet, *The Zipper*, Journal of Functional Programming 7(5), 1997; Conor McBride, *The Derivative of a Regular Type is its Type of One-Hole Contexts* (2001); Gabriella Gonzalez, [You could have invented comonads](https://haskellforall.com/2013/02/you-could-have-invented-comonads) (2013).
