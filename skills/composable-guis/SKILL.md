---
name: composable-guis
description: Composable GUIs — UIs as values from pure functions (Model-View-Update), pure state transitions, and components combined by mapping messages. Use when designing UI state or component structure, testing UI logic without a renderer, or wrapping an imperative toolkit.
---

# Composable GUIs

> *functional-architecture.org:* "Facebook's React popularized the component model of user interface programming. Functional programming languages allow to improve on that model by treating components as composable first-class user interfaces. Functional UI libraries provide a set of primitive components and a set of UI combinators, which let you build sophisticated graphical user interfaces without cognitive overhead." (Pattern page upstream TODO.)

Functional UI paradigms evolved from stream-based approaches, through monad-based toolkits that mimicked object-oriented practice, to **Model-View-Update**. Moving from the inherently imperative Model-View-Controller to functional approaches drastically reduces coupling and improves maintainability and testability; **modularity** — composing independent components with their own state and communication — remains the open challenge (Sperber & Schlegel, FUNARCH 2025).

## The shape (Model-View-Update)

- **Model:** an immutable value holding the UI state (design it with `make-illegal-states-unrepresentable`).
- **Message:** a sum type of everything that can happen.
- **`update :: Msg -> Model -> Model`** (optionally also returning commands/effects as values): pure.
- **`view :: Model -> Html Msg`:** pure; the UI is a *value* describing what to show and which message each interaction produces.
- **The runtime** (the imperative shell) renders the view, turns user events into messages, calls `update`, and performs requested effects — `functional-core-imperative-shell` for UIs. In Elm the runtime works out the minimal DOM change for each new `Html` value, and `update` returns `(Model, Cmd Msg)`: the program *commands* the runtime to make an HTTP request or draw a random number, and *subscribes* to things like the clock, so all DOM manipulation stays out of your code (Czaplicki, Elm guide).

Because `view` returns a value parameterized by the message type, **components compose with a functor**: a child's `Html ChildMsg` becomes part of the parent's `Html ParentMsg` by mapping `ChildMsg -> ParentMsg`; the child's model nests in the parent's model; the parent's `update` delegates. Every combination is again a component.

## Procedure

1. Model the state and the messages as types; make impossible UI states unrepresentable (no `isLoading` + `error` + `data` all optional — use a sum type).
2. Write `update` as a pure function; return effects as values (commands) instead of performing them.
3. Write `view` as a pure function from model to UI value.
4. Reuse a piece of UI as a **view function** first (`viewPicker :: [(String, msg)] -> Html msg`, polymorphic in the message it emits), which leaves the parent's model and `update` untouched. Make it a component — nest its model, map its messages — only when it has its own state and transitions (see *When composition gets heavy*).
5. Test `update` with example and property tests (replay message sequences; check invariants); test `view` by inspecting the value, not pixels (Bonsai's expect tests print the rendered DOM, then only the diff after each programmatic input).
6. When wrapping an imperative toolkit, put a **functional shell** around it: observables/values in, widget mutations confined to the shell (GUI Easy).

Done when: all UI state lives in immutable models, all transitions are pure functions tested without a renderer, and larger screens are built only by combining smaller components.

## Example: two counters composed from one component

**Haskell**

```haskell
{-# LANGUAGE DeriveFunctor #-}

-- A tiny UI value type, parameterized by the message it can produce.
data Html msg = Text String | Button String msg | Div [Html msg] deriving (Show, Functor)

-- The component.
data CounterMsg = Increment | Decrement deriving (Show)

updateCounter :: CounterMsg -> Int -> Int
updateCounter Increment n = n + 1
updateCounter Decrement n = n - 1

viewCounter :: Int -> Html CounterMsg
viewCounter n = Div [Button "-" Decrement, Text (show n), Button "+" Increment]

-- Composition: nest models, map messages (the functor does the plumbing).
data Msg = First CounterMsg | Second CounterMsg deriving (Show)

data Model = Model {first :: Int, second :: Int} deriving (Show)

update :: Msg -> Model -> Model
update (First m) model = model {first = updateCounter m (first model)}
update (Second m) model = model {second = updateCounter m (second model)}

view :: Model -> Html Msg
view model = Div [fmap First (viewCounter (first model)), fmap Second (viewCounter (second model))]

-- Pure replay: a fold over messages is a whole UI session, testable without a screen.
session :: Model
session = foldl (flip update) (Model 0 0) [First Increment, Second Increment, Second Increment]
```

**TypeScript**

```typescript
type Html<Msg> =
  | { tag: "text"; text: string }
  | { tag: "button"; label: string; onClick: Msg }
  | { tag: "div"; children: Html<Msg>[] };

const mapHtml = <A, B>(f: (a: A) => B, h: Html<A>): Html<B> =>
  h.tag === "text" ? h : h.tag === "button" ? { ...h, onClick: f(h.onClick) } : { tag: "div", children: h.children.map((c) => mapHtml(f, c)) };

// The component.
type CounterMsg = "increment" | "decrement";
const updateCounter = (m: CounterMsg, n: number): number => (m === "increment" ? n + 1 : n - 1);
const viewCounter = (n: number): Html<CounterMsg> => ({
  tag: "div",
  children: [{ tag: "button", label: "-", onClick: "decrement" }, { tag: "text", text: String(n) }, { tag: "button", label: "+", onClick: "increment" }],
});

// Composition.
type Msg = { which: "first" | "second"; msg: CounterMsg };
type Model = { readonly first: number; readonly second: number };

export const update = (m: Msg, model: Model): Model => ({ ...model, [m.which]: updateCounter(m.msg, model[m.which]) });

export const view = (model: Model): Html<Msg> => ({
  tag: "div",
  children: [
    mapHtml((msg: CounterMsg): Msg => ({ which: "first", msg }), viewCounter(model.first)),
    mapHtml((msg: CounterMsg): Msg => ({ which: "second", msg }), viewCounter(model.second)),
  ],
});

export const session = ([{ which: "first", msg: "increment" }, { which: "second", msg: "increment" }] as Msg[]).reduce(
  (model, msg) => update(msg, model),
  { first: 0, second: 0 } as Model,
);
```

**C++**

```cpp
#include <functional>
#include <string>
#include <variant>
#include <vector>

template <typename Msg>
struct Html {
  struct Text { std::string text; };
  struct Button { std::string label; Msg onClick; };
  struct Div { std::vector<Html> children; };
  std::variant<Text, Button, Div> node;
};

template <typename B, typename A>
Html<B> mapHtml(const std::function<B(A)>& f, const Html<A>& h) {
  if (auto* t = std::get_if<typename Html<A>::Text>(&h.node)) return {typename Html<B>::Text{t->text}};
  if (auto* b = std::get_if<typename Html<A>::Button>(&h.node)) return {typename Html<B>::Button{b->label, f(b->onClick)}};
  typename Html<B>::Div d;
  for (const auto& c : std::get<typename Html<A>::Div>(h.node).children) d.children.push_back(mapHtml(f, c));
  return {d};
}

// The component.
enum class CounterMsg { Increment, Decrement };
int updateCounter(CounterMsg m, int n) { return m == CounterMsg::Increment ? n + 1 : n - 1; }
Html<CounterMsg> viewCounter(int n) {
  using H = Html<CounterMsg>;
  return {H::Div{{H{H::Button{"-", CounterMsg::Decrement}}, H{H::Text{std::to_string(n)}}, H{H::Button{"+", CounterMsg::Increment}}}}};
}

// Composition.
struct Msg { bool first; CounterMsg msg; };
struct Model { int first = 0, second = 0; };

Model update(const Msg& m, Model model) {
  (m.first ? model.first : model.second) = updateCounter(m.msg, m.first ? model.first : model.second);
  return model;
}

Html<Msg> view(const Model& model) {
  std::function<Msg(CounterMsg)> toFirst = [](CounterMsg c) { return Msg{true, c}; };
  std::function<Msg(CounterMsg)> toSecond = [](CounterMsg c) { return Msg{false, c}; };
  return {Html<Msg>::Div{{mapHtml(toFirst, viewCounter(model.first)), mapHtml(toSecond, viewCounter(model.second))}}};
}
```

## Beyond MVU

- **Monoidal inputs and outputs:** Gonzalez's `mvc` combines all views into one `View` and all controllers into one `Controller` (both monoids), unified with functors, so a whole application has one pure `Model` with a single entry and exit.
- **Spreadsheet-like updates:** `Applicative` "updatable" values recompute derived values when inputs change, reusing unchanged parts; *self-adjusting computation* scales the idea to a large commercial system (Wehr, FUNARCH 2023).
- **UIs from types:** Grace generates interactive web forms from a pure function's type.
- **Functional shells over imperative toolkits:** observables plus reusable views make imperative widget libraries composable (GUI Easy).

## When composition gets heavy

- **Reuse views before components.** Elm's guide shows a `checkbox msg name` helper reused everywhere "without disrupting our `Model` or `update`", where a "checkbox component" would need its state synchronized with the parent's model. Its rule is "choose the absolute simplest thing that does everything you need": a view configured by many arguments is over-reuse, and two simple, similar chunks beat one complex shared one. Bonsai draws the same line: *views* take plain values, return plain values, and may call only views; *components* take and return reactive values and may call both.
- **Don't reach for components by reflex.** The guide argues components are objects (local state plus methods) and steer modules toward the visual layout — "There is a sidebar, so I need a `Sidebar` module" — when a `viewSidebar` function and a field in the existing model would do. It also warns against splitting modules into `Model`, `Update`, and `View` files (unclear boundaries): build each module around a central type, wait until pages show what is similar rather than the same, and rely on the compiler to make the later refactor cheap.
- **Message wrapping has a cost.** Composing components by nesting their action types in `Either`s made one Bonsai demo's top-level action type an unwieldy tree, and the wrapping was practically worthless: components should not construct each other's actions. Pass data, or the child's `inject` function, instead (Bonsai history). The `First`/`Second` wrapper above is that cost in miniature; it is cheap for one or two levels.
- **State need not follow the component tree.** Bonsai composes state primitives à la carte instead of attaching state to a UI component, so embedding stateful components (say, in tabs) does not require hoisting each child's state into the app's top-level model. It keeps a node's state while the node is inactive unless you reset it explicitly.
- **Updates must read the current state.** Bonsai's plain `state` setter takes a new value computed from a captured copy of the record, so two async results can overwrite each other with stale fields; `state'` takes an `old -> new` function that always sees the latest state. `update :: Msg -> Model -> Model` has this property by construction.
- **A fixed graph can be optimized.** `Bonsai.t` deliberately has no `bind` (an arrow, not a monad): the graph is static after initialization, so it can be condensed and instrumented, and conditional views toggle which parts are active (`match%sub`, `assoc`) instead of creating nodes at runtime.

## Related skills

`functional-core-imperative-shell` · `everything-as-a-value` (UI components as values) · `composition-and-closure` · `make-illegal-states-unrepresentable` (UI state) · `immutability` · `property-based-testing` (replaying message sequences)

## Sources

- functional-architecture.org, [Composable GUI libraries](https://functional-architecture.org/composable_guis/) (pattern page; upstream TODO).
- Michael Sperber, Markus Schlegel, [Evolution of Functional UI Paradigms](https://dl.acm.org/doi/10.1145/3759163.3760429) (FUNARCH 2025).
- Ben Knoble, Bogdan Popa, [Functional Shell and Reusable Components for Easy GUIs](https://defn.io/papers/fungui-funarch23.pdf) (FUNARCH 2023).
- Stefan Wehr, [A Software Architecture Based on Coarse-Grained Self-Adjusting Computations](https://dl.acm.org/doi/10.1145/3609025.3609481) (FUNARCH 2023).
- Gabriella Gonzalez, [Model-view-controller, Haskell-style](https://haskellforall.com/2014/04/model-view-controller-haskell-style) (2014), [Spreadsheet-like programming in Haskell](https://haskellforall.com/2014/06/spreadsheet-like-programming-in-haskell) (2014), [Generate web forms from pure functions](https://haskellforall.com/2022/05/generate-web-forms-from-pure-functions) (2022).
- Evan Czaplicki, [The Elm Architecture](https://guide.elm-lang.org/architecture/) and [Commands and Subscriptions](https://guide.elm-lang.org/effects/) (guide for Elm 0.19.2; read from [`evancz/guide.elm-lang.org`](https://github.com/evancz/guide.elm-lang.org)) — the Model/View/Update loop, the runtime that owns the DOM, and commands and subscriptions as values sent to it.
- Evan Czaplicki, [Structuring Web Apps](https://guide.elm-lang.org/webapps/structure.html) (same guide) and the [checkboxes](https://github.com/evancz/guide.elm-lang.org/blob/master/book/architecture/checkboxes.md) and [radio buttons](https://github.com/evancz/guide.elm-lang.org/blob/master/book/architecture/radio_buttons.md) pages (in the repository, not linked from its table of contents) — reusable views versus components, modules around a central type, and "too much reuse".
- Jane Street, [Bonsai](https://github.com/janestreet/bonsai) (README) and its web documentation, [Thinking in Bonsai](https://github.com/janestreet/bonsai_web/blob/master/docs/thinking_in_bonsai.md) and [Bonsai history](https://github.com/janestreet/bonsai_web/blob/master/docs/blog/history.md) (repository docs) — purely functional state machines, state composed à la carte, views versus components, `state'` update functions, the no-`bind` static graph, and the cost of nested action types.
