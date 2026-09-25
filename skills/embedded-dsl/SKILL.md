---
name: embedded-dsl
description: Embedded DSLs — domain rules, workflows, or queries as a small language inside the host language (deep embedding with interpreters, or shallow combinators). Use when rules should compose and be interpreted several ways (run, explain, validate), or when weighing a DSL's long-term cost.
---

# Embedded domain-specific languages

> *Upstream status:* the functional-architecture.org pattern page is TODO. This skill is synthesized from the sources listed at the end.

An **embedded** DSL is a library whose vocabulary is the domain's (``when (totalAtLeast 100) (percentOff 10)``), built from the host language's values and functions. Unlike an external DSL it needs no parser, inherits the host's type checker, editor support, modules, and abstraction facilities, and can be mixed freely with ordinary code.

## Two embeddings

- **Deep embedding (initial encoding):** the DSL builds a data structure (an AST, a free monad). You can then write *several* interpreters — evaluate, pretty-print, explain, optimize, check, compile to SQL — and inspect programs before running them. (`free-monads`, `everything-as-a-value`)
- **Shallow embedding (final encoding):** each construct is directly its meaning (a function, an object with methods). Adding constructs is easy; adding a new interpretation means changing every construct (or using a record of interpretations — "tagless final").

The tension between the two is the expression problem (`data-types-a-la-carte`, `trees-that-grow`).

## Design rules

1. **Start from sentences the domain experts already say**, and make them expressions.
2. **Close the language under composition:** combining rules yields a rule; `<>`/`mempty` where it makes sense (`composition-and-closure`).
3. **Give it laws.** A DSL whose operators obey algebraic laws can be reasoned about and optimized (`algebraic-modelling`); `turtle`'s streams obey `+`/`*` laws, PlusCal processes combine as Cartesian products of automata via `Applicative`.
4. **Make it as weak as possible.** A non-Turing-complete, total language (Dhall's stance) is easier to analyze, safer to accept from users, and guaranteed to terminate. Add power only when a real use needs it.
5. **Prefer deep embedding when you need more than one interpretation**; shallow when you need only to run it.
6. **Be honest about the audience.** A DSL "for less technical users on a budget" rarely stays cheap: success pushes it to its limits, failure creates cleanup work, and either way it needs permanent staffing. The division of labour tends to pay off only at ecosystem scale. An eDSL *for programmers* avoids most of this cost.

Done when: domain rules are written in the DSL's vocabulary, rules compose into rules, and at least the interpretations the product needs (run, explain, validate) exist as independent functions over the same description.

## Example: discount rules with two interpreters

**Haskell** (deep embedding)

```haskell
data Cart = Cart {total :: Double, isMember :: Bool}

data Condition = TotalAtLeast Double | Member | And Condition Condition

data Rule
  = PercentOff Double
  | FixedOff Double
  | When Condition Rule
  | Both Rule Rule -- rules compose into rules
  | NoDiscount

instance Semigroup Rule where (<>) = Both
instance Monoid Rule where mempty = NoDiscount

holds :: Condition -> Cart -> Bool
holds (TotalAtLeast x) c = total c >= x
holds Member c = isMember c
holds (And a b) c = holds a c && holds b c

-- Interpretation 1: compute the discount.
discount :: Rule -> Cart -> Double
discount (PercentOff p) c = total c * p / 100
discount (FixedOff x) _ = x
discount (When cond r) c = if holds cond c then discount r c else 0
discount (Both a b) c = discount a c + discount b c
discount NoDiscount _ = 0

-- Interpretation 2: explain the rules to a human.
explain :: Rule -> [String]
explain (PercentOff p) = [show p <> "% off"]
explain (FixedOff x) = [show x <> " off"]
explain (When cond r) = map (<> (" when " <> describe cond)) (explain r)
  where
    describe (TotalAtLeast x) = "the total is at least " <> show x
    describe Member = "the customer is a member"
    describe (And a b) = describe a <> " and " <> describe b
explain (Both a b) = explain a <> explain b
explain NoDiscount = []

summerSale :: Rule
summerSale = When (TotalAtLeast 100) (PercentOff 10) <> When Member (FixedOff 5)
-- discount summerSale (Cart 200 True) == 25.0
```

**TypeScript** (deep embedding)

```typescript
type Cart = { total: number; isMember: boolean };
type Condition = { kind: "totalAtLeast"; amount: number } | { kind: "member" } | { kind: "and"; a: Condition; b: Condition };
type Rule =
  | { kind: "percentOff"; percent: number }
  | { kind: "fixedOff"; amount: number }
  | { kind: "when"; cond: Condition; rule: Rule }
  | { kind: "all"; rules: Rule[] };

export const percentOff = (percent: number): Rule => ({ kind: "percentOff", percent });
export const fixedOff = (amount: number): Rule => ({ kind: "fixedOff", amount });
export const when = (cond: Condition, rule: Rule): Rule => ({ kind: "when", cond, rule });
export const all = (...rules: Rule[]): Rule => ({ kind: "all", rules });
export const totalAtLeast = (amount: number): Condition => ({ kind: "totalAtLeast", amount });
export const member: Condition = { kind: "member" };

const holds = (c: Condition, cart: Cart): boolean =>
  c.kind === "totalAtLeast" ? cart.total >= c.amount : c.kind === "member" ? cart.isMember : holds(c.a, cart) && holds(c.b, cart);

export function discount(r: Rule, cart: Cart): number {
  switch (r.kind) {
    case "percentOff": return (cart.total * r.percent) / 100;
    case "fixedOff": return r.amount;
    case "when": return holds(r.cond, cart) ? discount(r.rule, cart) : 0;
    case "all": return r.rules.reduce((sum, x) => sum + discount(x, cart), 0);
  }
}

const describe = (c: Condition): string =>
  c.kind === "totalAtLeast" ? `the total is at least ${c.amount}` : c.kind === "member" ? "the customer is a member" : `${describe(c.a)} and ${describe(c.b)}`;

export function explain(r: Rule): string[] {
  switch (r.kind) {
    case "percentOff": return [`${r.percent}% off`];
    case "fixedOff": return [`${r.amount} off`];
    case "when": return explain(r.rule).map((s) => `${s} when ${describe(r.cond)}`);
    case "all": return r.rules.flatMap(explain);
  }
}

export const summerSale = all(when(totalAtLeast(100), percentOff(10)), when(member, fixedOff(5)));
```

**C++** (deep embedding)

```cpp
#include <memory>
#include <string>
#include <variant>
#include <vector>

struct Cart { double total; bool isMember; };

struct Condition;
using CondPtr = std::shared_ptr<const Condition>;
struct TotalAtLeast { double amount; };
struct Member {};
struct And { CondPtr a, b; };
struct Condition { std::variant<TotalAtLeast, Member, And> node; };

struct Rule;
using RulePtr = std::shared_ptr<const Rule>;
struct PercentOff { double percent; };
struct FixedOff { double amount; };
struct When { CondPtr cond; RulePtr rule; };
struct All { std::vector<RulePtr> rules; };
struct Rule { std::variant<PercentOff, FixedOff, When, All> node; };

template <typename T> RulePtr rule(T t) { return std::make_shared<const Rule>(Rule{std::move(t)}); }
template <typename T> CondPtr cond(T t) { return std::make_shared<const Condition>(Condition{std::move(t)}); }

bool holds(const Condition& c, const Cart& cart) {
  if (auto* t = std::get_if<TotalAtLeast>(&c.node)) return cart.total >= t->amount;
  if (std::holds_alternative<Member>(c.node)) return cart.isMember;
  const auto& a = std::get<And>(c.node);
  return holds(*a.a, cart) && holds(*a.b, cart);
}

double discount(const Rule& r, const Cart& cart) {  // interpretation 1
  if (auto* p = std::get_if<PercentOff>(&r.node)) return cart.total * p->percent / 100;
  if (auto* f = std::get_if<FixedOff>(&r.node)) return f->amount;
  if (auto* w = std::get_if<When>(&r.node)) return holds(*w->cond, cart) ? discount(*w->rule, cart) : 0;
  double sum = 0;
  for (const auto& x : std::get<All>(r.node).rules) sum += discount(*x, cart);
  return sum;
}

std::string describe(const Condition& c) {
  if (auto* t = std::get_if<TotalAtLeast>(&c.node)) return "the total is at least " + std::to_string(t->amount);
  if (std::holds_alternative<Member>(c.node)) return "the customer is a member";
  const auto& a = std::get<And>(c.node);
  return describe(*a.a) + " and " + describe(*a.b);
}

std::vector<std::string> explain(const Rule& r) {  // interpretation 2
  if (auto* p = std::get_if<PercentOff>(&r.node)) return {std::to_string(p->percent) + "% off"};
  if (auto* f = std::get_if<FixedOff>(&r.node)) return {std::to_string(f->amount) + " off"};
  if (auto* w = std::get_if<When>(&r.node)) {
    auto lines = explain(*w->rule);
    for (auto& l : lines) l += " when " + describe(*w->cond);
    return lines;
  }
  std::vector<std::string> out;
  for (const auto& x : std::get<All>(r.node).rules) {
    auto lines = explain(*x);
    out.insert(out.end(), lines.begin(), lines.end());
  }
  return out;
}

const RulePtr summerSale = rule(All{{rule(When{cond(TotalAtLeast{100}), rule(PercentOff{10})}),
                                     rule(When{cond(Member{}), rule(FixedOff{5})})}});
```

## Related skills

`free-monads` (effectful DSLs) · `everything-as-a-value` · `composition-and-closure` · `algebraic-modelling` · `denotational-design` (give the DSL a precise meaning first) · `data-types-a-la-carte` · `trees-that-grow` · `bidirectional-data-transformations`

## Sources

- functional-architecture.org, [Embedded Domain-Specific Languages](https://functional-architecture.org/dsl/) (pattern page; upstream TODO).
- Gabriella Gonzalez, [Why free monads matter](https://haskellforall.com/2012/06/you-could-have-invented-free-monads) (2012), [Mathematical APIs](https://haskellforall.com/2015/04/mathematical-apis) (2015), [Sometimes less is more in language design](https://haskellforall.com/2013/08/sometimes-less-is-more-in-language) (2013), [Modeling PlusCal in Haskell using Cartesian products of NFAs](https://haskellforall.com/2022/03/modeling-pluscal-in-haskell-using) (2022), [Why do our programs need to read input and write output?](https://haskellforall.com/2017/10/why-do-our-programs-need-to-read-input) (2017), [The siren song of domain-specific languages](https://haskellforall.com/2024/02/the-siren-song-of-domain-specific) (2024).
- Weixi Ma et al., [F3: A Compiler For Feature Engineering](https://dl.acm.org/doi/10.1145/3677998.3678220) (FUNARCH 2024) — a DSL and compiler at Meta.
- Seungheon Oh, Ziyang Liu, Philip Wadler, *From Lambda to Ledger: An Architectural Comparison of Plinth and Plutarch* ([FUNARCH 2026](https://functional-architecture.org/events/funarch-2026/)) — compiling a subset of the host language vs explicitly constructed typed terms embedded in it.
