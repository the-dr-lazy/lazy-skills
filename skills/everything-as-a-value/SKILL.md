---
name: everything-as-a-value
description: Everything as a value — reify implicit concepts (functions, programs, UI components, accessors, rules) as first-class values that can be passed, analyzed, composed, and interpreted. Use when code works around a concept it never names, or when designing extension points.
---

# Everything as a value

> *functional-architecture.org (draft):* "Reifying concepts as values allows these concepts to be passed around, analyzed and composed. Functions as values, property accessors as values, UI components as values …"

Every piece of software is *about* something — numbers, time series, system resources, charts, SQL queries. **Whenever a piece of software is about a concept, you can either program blindly around the concept or make it an explicit part of your programming model.** A visualization component can take byte arrays and draw pixels without ever mentioning "graph", or it can parse bytes into time series, turn those into graphs, and render graphs into pixels. Functional software architecture strongly favours the second: *reifying* the concept, *internalizing* it, making it *first-class*.

## Successful reifications

| Concept | As a value | What it enables |
|---|---|---|
| Procedures | first-class functions | higher-order functions, callbacks, dependency injection without frameworks |
| Programs / effects | free monads, command lists, `Effect` values | inspection, multiple interpreters, testing, sandboxing (`free-monads`) |
| Interface implementations | records of functions, dictionaries, first-class modules | choose, wrap, and combine implementations at run time (`composable-effects`) |
| Property access | lenses, prisms, optics | compose, reuse, and reverse accessors (`bidirectional-data-transformations`) |
| UI components | functions from model to view, combinators | composable GUIs (`composable-guis`) |
| Services | Jolie: "a composition of services is a service" | services composed like expressions |
| Data | Church encoding: "data is code" | sum types via functions (the visitor pattern) |
| Forms | a function's type | Grace generates an interactive web form from a pure function's type |
| Errors, absence | `Either`/`Result`, `Maybe`/`Option` | errors that compose (`composable-error-handling`) |
| Time, events | an event log | replay, audit, projections (`event-sourcing`) |

## Procedure

1. **Name the concept** the code is really about but never mentions (a chart, a pricing rule, a migration step, a permission, a workflow).
2. **Define it as a value**: a data type (when you need to inspect it) or a function/record of functions (when you only need to run it). Prefer data when several interpretations are plausible.
3. **Give it operations that return the same kind of value** (combine, transform, restrict) so it composes (`composition-and-closure`).
4. **Write interpretations** (render, execute, explain, validate) as ordinary functions over the value.
5. **Move the old hard-wired code** to construct the value and hand it to an interpreter.

Done when: the concept appears by name in the types, can be stored and passed like any other value, and has at least two uses beyond the one hard-wired path (e.g. render *and* analyze, execute *and* test).

## Example: making "chart" a concept

**Haskell**

```haskell
type Series = [(Double, Double)]

-- The concept, reified.
data Chart
  = Line String Series
  | Overlay Chart Chart
  | Titled String Chart

-- Composable: combining charts yields a chart.
overlay :: [Chart] -> Maybe Chart
overlay [] = Nothing
overlay cs = Just (foldr1 Overlay cs)

-- Analyzable: questions about the chart without rendering it.
seriesNames :: Chart -> [String]
seriesNames (Line n _) = [n]
seriesNames (Overlay a b) = seriesNames a <> seriesNames b
seriesNames (Titled _ c) = seriesNames c

-- One of several interpretations.
renderText :: Chart -> String
renderText (Line n pts) = n <> ": " <> show (length pts) <> " points\n"
renderText (Overlay a b) = renderText a <> renderText b
renderText (Titled t c) = "== " <> t <> " ==\n" <> renderText c
```

**TypeScript**

```typescript
type Series = ReadonlyArray<readonly [number, number]>;

type Chart =
  | { kind: "line"; name: string; points: Series }
  | { kind: "overlay"; charts: readonly Chart[] }
  | { kind: "titled"; title: string; chart: Chart };

export const overlay = (...charts: Chart[]): Chart => ({ kind: "overlay", charts });

export function seriesNames(c: Chart): string[] {
  switch (c.kind) {
    case "line": return [c.name];
    case "overlay": return c.charts.flatMap(seriesNames);
    case "titled": return seriesNames(c.chart);
  }
}

export function renderText(c: Chart): string {
  switch (c.kind) {
    case "line": return `${c.name}: ${c.points.length} points\n`;
    case "overlay": return c.charts.map(renderText).join("");
    case "titled": return `== ${c.title} ==\n${renderText(c.chart)}`;
  }
}
```

**C++**

```cpp
#include <memory>
#include <string>
#include <utility>
#include <variant>
#include <vector>

using Series = std::vector<std::pair<double, double>>;

struct Chart;
using ChartPtr = std::shared_ptr<const Chart>;
struct Line { std::string name; Series points; };
struct Overlay { std::vector<ChartPtr> charts; };
struct Titled { std::string title; ChartPtr chart; };
struct Chart { std::variant<Line, Overlay, Titled> node; };

ChartPtr overlay(std::vector<ChartPtr> charts) { return std::make_shared<const Chart>(Chart{Overlay{std::move(charts)}}); }

std::vector<std::string> seriesNames(const Chart& c) {
  if (auto* l = std::get_if<Line>(&c.node)) return {l->name};
  if (auto* t = std::get_if<Titled>(&c.node)) return seriesNames(*t->chart);
  std::vector<std::string> out;
  for (const auto& child : std::get<Overlay>(c.node).charts) {
    auto names = seriesNames(*child);
    out.insert(out.end(), names.begin(), names.end());
  }
  return out;
}

std::string renderText(const Chart& c) {
  if (auto* l = std::get_if<Line>(&c.node)) return l->name + ": " + std::to_string(l->points.size()) + " points\n";
  if (auto* t = std::get_if<Titled>(&c.node)) return "== " + t->title + " ==\n" + renderText(*t->chart);
  std::string out;
  for (const auto& child : std::get<Overlay>(c.node).charts) out += renderText(*child);
  return out;
}
```

## Trade-offs

Reification costs a type and an interpreter. Choose **data** (an AST) when you need to inspect, optimize, serialize, or interpret the concept in several ways; choose **functions** (the final encoding) when running it is the only interpretation and you want extensibility of new cases for free. The tension between the two is the expression problem (`data-types-a-la-carte`, `trees-that-grow`). Reify what the domain talks about, not every implementation detail: a concept deserves to be first-class when people *reason* about it.

## Related skills

`composition-and-closure` · `free-monads` · `composable-effects` · `bidirectional-data-transformations` · `composable-guis` · `embedded-dsl` · `denotational-design` · `algebraic-modelling`

## Sources

- functional-architecture.org, [Everything as a Value](https://functional-architecture.org/eaav/) (principle page; draft — reification, functions as first-class procedures, Jolie services as first-class values).
- Gabriella Gonzalez, [Data is Code](https://haskellforall.com/2016/04/data-is-code) (2016), [The visitor pattern is essentially the same thing as Church encoding](https://haskellforall.com/2021/01/the-visitor-pattern-is-essentially-same) (2021), [Scrap your type classes](https://haskellforall.com/2012/05/scrap-your-type-classes) (2012), [First-class modules without defaults](https://haskellforall.com/2012/07/first-class-modules-without-defaults) (2012), [Generate web forms from pure functions](https://haskellforall.com/2022/05/generate-web-forms-from-pure-functions) (2022), [Why free monads matter](https://haskellforall.com/2012/06/you-could-have-invented-free-monads) (2012).
