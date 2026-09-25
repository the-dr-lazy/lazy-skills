---
name: late-decision-making
description: Late decision making — under uncertainty, model the domain first and keep infrastructure choices behind pure models and swappable implementations so decisions stay cheap to change. Use at the start of a project, with unreliable external systems, or when a choice would be expensive to reverse.
---

# Late decision making

> *functional-architecture.org:* "Software design is usually performed under uncertainty. Instead of trying to make the right decisions up front, we want to design our systems in such a way that it is easy to change our minds later in the process. This shifts our focus from **making decisions** to **making decisions possible**." (Principle page: draft.)

Classical architecture lore says architects must make the difficult decisions early, and make them right, for the whole lifecycle. That requires perfect foresight. The functional position is the opposite: uncertainty is greatest at the start, and *how hard a decision is to change is a property of the software, not of the decision*. So invest in malleability, and decide when you know more.

## The case study (from the draft)

Operators monitor factory incidents from an external system `E` (poorly documented; "supports queries"; one known call, `getAll`; data "potentially huge"; rumoured push interface), through our server `S`, in a browser client `C` (users sketched a tabbed UI: details for one category, overviews for the others). Open questions: can `E` filter by category or aggregate? Can `C` just get everything? Should `S` filter/aggregate? Polling rates — fixed, per tab, dynamic, configurable? Websockets? Caching where? Is the tabbed UI even right? Prefetching?

None of these needs answering on day one if the design keeps them open.

## Procedure

1. **Model the primary domain concept first — not its representation.** `E` represents an incident as `{title, introduction_date, category, severity}`. Ask stakeholders what it *means*: an incident is *information about* something bad happening. Complete models need things `E` omits (`resolved_date`, since `E` only returns active incidents); keep representation and model distinct.
2. **Model what users actually need.** Operators care about *all* incidents per category, and mostly about aggregates: "are there any?" (a count), "is anything severe?" (the maximum severity). Aggregates like these are often monoids — computable anywhere, in any grouping, incrementally.
3. **Write the domain logic as pure functions over the model** (summaries, filters, severity rules). Pure code runs unchanged in the client, the server, or a job — so *where* it runs stays a late decision.
4. **Put every uncertain infrastructure choice behind a capability** (`IncidentSource`: `getAll`-then-filter today, a query or push stream tomorrow; polling policy as a value; cache as a decorator) with interchangeable implementations (`composable-effects`).
5. **Make time explicit when it matters** (introduced/resolved dates) without committing to an implementation technique — the model may look like event sourcing without the implementation being event-sourced.
6. **Record which decisions are still open** and what evidence would settle them; revisit as you learn.

Done when: each open question maps to one swappable implementation or one parameter, and the domain logic compiles and is tested without any of them decided.

## Example: summaries that can run anywhere, sources that can change

**Haskell**

```haskell
import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map

newtype Category = Category String deriving (Eq, Ord, Show)

data Incident = Incident {title :: String, category :: Category, severity :: Int, resolved :: Bool}

-- What operators need per category: a monoid, so it can be computed anywhere, in any grouping.
data Summary = Summary {active :: Int, maxSeverity :: Maybe Int} deriving (Eq, Show)

instance Semigroup Summary where
  Summary a m <> Summary b n = Summary (a + b) (max m n)

instance Monoid Summary where
  mempty = Summary 0 Nothing

summarize :: [Incident] -> Map Category Summary
summarize is = Map.fromListWith (<>) [(category i, Summary 1 (Just (severity i))) | i <- is, not (resolved i)]

-- The undecided part: how incidents are obtained.
newtype IncidentSource m = IncidentSource {incidentsIn :: Category -> m [Incident]}

viaGetAll :: Functor m => m [Incident] -> IncidentSource m -- what E certainly supports today
viaGetAll getAll = IncidentSource (\c -> filter ((== c) . category) <$> getAll)

viaQuery :: (Category -> m [Incident]) -> IncidentSource m -- if E turns out to support queries
viaQuery = IncidentSource
```

**TypeScript**

```typescript
type Incident = { title: string; category: string; severity: number; resolved: boolean };
type Summary = { active: number; maxSeverity: number | null };

const emptySummary: Summary = { active: 0, maxSeverity: null };
const combine = (a: Summary, b: Summary): Summary => ({
  active: a.active + b.active,
  maxSeverity: a.maxSeverity === null ? b.maxSeverity : b.maxSeverity === null ? a.maxSeverity : Math.max(a.maxSeverity, b.maxSeverity),
});

// Pure: runs in the browser, on the server, or in a job — a decision we can defer.
export function summarize(incidents: readonly Incident[]): Map<string, Summary> {
  const out = new Map<string, Summary>();
  for (const i of incidents) {
    if (i.resolved) continue;
    out.set(i.category, combine(out.get(i.category) ?? emptySummary, { active: 1, maxSeverity: i.severity }));
  }
  return out;
}

// The undecided part: how incidents are obtained.
export type IncidentSource = { incidentsIn: (category: string) => Promise<Incident[]> };

export const viaGetAll = (getAll: () => Promise<Incident[]>): IncidentSource => ({
  incidentsIn: async (c) => (await getAll()).filter((i) => i.category === c),
});
export const viaQuery = (query: (c: string) => Promise<Incident[]>): IncidentSource => ({ incidentsIn: query });
```

**C++**

```cpp
#include <algorithm>
#include <functional>
#include <map>
#include <optional>
#include <string>
#include <vector>

struct Incident { std::string title, category; int severity; bool resolved; };

struct Summary {
  int active = 0;
  std::optional<int> maxSeverity;
};

Summary operator+(const Summary& a, const Summary& b) {
  std::optional<int> m = a.maxSeverity;
  if (b.maxSeverity && (!m || *b.maxSeverity > *m)) m = b.maxSeverity;
  return {a.active + b.active, m};
}

// Pure: can run in the client, the server, or a batch job.
std::map<std::string, Summary> summarize(const std::vector<Incident>& incidents) {
  std::map<std::string, Summary> out;
  for (const auto& i : incidents)
    if (!i.resolved) out[i.category] = out[i.category] + Summary{1, i.severity};
  return out;
}

// The undecided part: how incidents are obtained.
using IncidentSource = std::function<std::vector<Incident>(const std::string& category)>;

IncidentSource viaGetAll(std::function<std::vector<Incident>()> getAll) {
  return [getAll](const std::string& c) {
    auto all = getAll();
    std::erase_if(all, [&](const Incident& i) { return i.category != c; });
    return all;
  };
}

IncidentSource viaQuery(IncidentSource query) { return query; }
```

## Related skills

`composable-effects` (interchangeable implementations) · `algebraic-modelling` (aggregates as monoids) · `denotational-design` (model before representation) · `functional-core-imperative-shell` · `decoupled-by-default` · `modularization` · `event-sourcing`

## Sources

- functional-architecture.org, [Late Decision Making](https://functional-architecture.org/late/) (principle page; draft with the incidents case study) and the *Maintainability* value (site source, `lib/values.ml`): "Decisions being hard to change is not a function of the decision itself but a function of the software itself."
- Raghu Kaippully, [Polysemy is fun! — Part 1](https://haskell-explained.gitlab.io/blog/posts/2019/07/28/polysemy-is-cool-part-1/index.html) — "all such implementation decisions … can be done at a later stage."
- Gabriella Gonzalez, [Why free monads matter](https://haskellforall.com/2012/06/you-could-have-invented-free-monads) — decoupling programs from their interpreters.
