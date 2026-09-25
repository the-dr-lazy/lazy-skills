# Functional core, imperative shell — worked examples

Each example is given in Haskell, TypeScript, and C++. Each block is self-contained.

## 1. The core decides, the shell acts: order processing

An entangled handler validates, prices, charges, emails, and updates inventory in one block — untestable without a real payment. Split it: a pure core returns the total *and the list of actions to perform*; a thin shell executes them. The pricing rules are now testable with plain assertions, and the actions themselves can be inspected, logged, or replayed.

**Haskell**

```haskell
data Line = Line {sku :: String, quantity :: Int, unitPrice :: Int}

data Action
  = Charge Int
  | SendConfirmation String Int
  | ReserveStock String Int
  deriving (Eq, Show)

-- Core: pure, returns decisions as data.
planOrder :: String -> [Line] -> Either String (Int, [Action])
planOrder _ [] = Left "empty order"
planOrder email lines
  | any ((<= 0) . quantity) lines = Left "quantities must be positive"
  | otherwise = Right (total, Charge total : SendConfirmation email total : reservations)
  where
    total = sum [quantity l * unitPrice l | l <- lines]
    reservations = [ReserveStock (sku l) (quantity l) | l <- lines]

-- Shell: performs the actions; no business rules here.
runAction :: Action -> IO ()
runAction (Charge amount) = putStrLn ("charging " <> show amount)
runAction (SendConfirmation to amount) = putStrLn ("emailing " <> to <> ": " <> show amount)
runAction (ReserveStock s q) = putStrLn ("reserving " <> show q <> " x " <> s)

processOrder :: String -> [Line] -> IO ()
processOrder email lines = case planOrder email lines of
  Left err -> putStrLn ("rejected: " <> err)
  Right (_, actions) -> mapM_ runAction actions
```

**TypeScript**

```typescript
type Line = { readonly sku: string; readonly quantity: number; readonly unitPrice: number };

type Action =
  | { kind: "charge"; amount: number }
  | { kind: "sendConfirmation"; to: string; amount: number }
  | { kind: "reserveStock"; sku: string; quantity: number };

type Plan = { ok: true; total: number; actions: Action[] } | { ok: false; error: string };

// Core: pure, returns decisions as data.
export function planOrder(email: string, lines: readonly Line[]): Plan {
  if (lines.length === 0) return { ok: false, error: "empty order" };
  if (lines.some((l) => l.quantity <= 0)) return { ok: false, error: "quantities must be positive" };
  const total = lines.reduce((sum, l) => sum + l.quantity * l.unitPrice, 0);
  return {
    ok: true,
    total,
    actions: [
      { kind: "charge", amount: total },
      { kind: "sendConfirmation", to: email, amount: total },
      ...lines.map((l): Action => ({ kind: "reserveStock", sku: l.sku, quantity: l.quantity })),
    ],
  };
}

// Shell: performs the actions through injected infrastructure.
type Infra = {
  charge: (amount: number) => Promise<void>;
  email: (to: string, body: string) => Promise<void>;
  reserve: (sku: string, quantity: number) => Promise<void>;
};

export async function processOrder(infra: Infra, email: string, lines: readonly Line[]): Promise<void> {
  const plan = planOrder(email, lines);
  if (!plan.ok) throw new Error(plan.error);
  for (const a of plan.actions) {
    switch (a.kind) {
      case "charge": await infra.charge(a.amount); break;
      case "sendConfirmation": await infra.email(a.to, `total: ${a.amount}`); break;
      case "reserveStock": await infra.reserve(a.sku, a.quantity); break;
    }
  }
}
```

**C++**

```cpp
#include <expected>
#include <iostream>
#include <string>
#include <utility>
#include <variant>
#include <vector>

struct Line { std::string sku; int quantity; int unitPrice; };

struct Charge { int amount; };
struct SendConfirmation { std::string to; int amount; };
struct ReserveStock { std::string sku; int quantity; };
using Action = std::variant<Charge, SendConfirmation, ReserveStock>;

struct Plan { int total; std::vector<Action> actions; };

// Core: pure, returns decisions as data.
std::expected<Plan, std::string> planOrder(const std::string& email, const std::vector<Line>& lines) {
  if (lines.empty()) return std::unexpected(std::string("empty order"));
  int total = 0;
  for (const auto& l : lines) {
    if (l.quantity <= 0) return std::unexpected(std::string("quantities must be positive"));
    total += l.quantity * l.unitPrice;
  }
  Plan plan{total, {Charge{total}, SendConfirmation{email, total}}};
  for (const auto& l : lines) plan.actions.push_back(ReserveStock{l.sku, l.quantity});
  return plan;
}

template <class... Fs> struct overloaded : Fs... { using Fs::operator()...; };

// Shell: performs the actions; no business rules here.
void processOrder(const std::string& email, const std::vector<Line>& lines) {
  auto plan = planOrder(email, lines);
  if (!plan) { std::cerr << "rejected: " << plan.error() << '\n'; return; }
  for (const auto& action : plan->actions)
    std::visit(overloaded{
                   [](const Charge& c) { std::cout << "charging " << c.amount << '\n'; },
                   [](const SendConfirmation& s) { std::cout << "emailing " << s.to << '\n'; },
                   [](const ReserveStock& r) { std::cout << "reserving " << r.sku << '\n'; },
               },
               action);
}
```

## 2. The whole program as a pure state machine (`mvc` style)

Gonzalez's `mvc` library statically enforces that the model is a pure transformation from inputs to outputs, with all inputs combined into one controller and all outputs into one view. The same architecture works without the library: the core is `step :: State -> Input -> (State, [Output])`; the shell is a loop that reads inputs, calls `step`, and performs outputs. The core can be replayed, property-tested, and reasoned about in isolation.

**Haskell**

```haskell
import Data.List (mapAccumL)

data Input = Click Int Int | Tick deriving (Show)
data Output = DrawRectangle (Int, Int) (Int, Int) | Log String deriving (Eq, Show)

-- State: the first corner of a rectangle in progress, if any.
type State = Maybe (Int, Int)

-- Core: every pair of clicks draws one rectangle.
step :: State -> Input -> (State, [Output])
step Nothing (Click x y) = (Just (x, y), [])
step (Just c) (Click x y) = (Nothing, [DrawRectangle c (x, y)])
step s Tick = (s, [Log "tick"])

runPure :: [Input] -> [Output]
runPure = concat . snd . mapAccumL step Nothing

-- Shell: feed real inputs, perform outputs.
main :: IO ()
main = mapM_ print (runPure [Click 0 0, Tick, Click 10 10, Click 5 5])
-- property: length of DrawRectangle outputs == (number of clicks) `div` 2
```

**TypeScript**

```typescript
type Input = { kind: "click"; x: number; y: number } | { kind: "tick" };
type Output = { kind: "drawRectangle"; from: [number, number]; to: [number, number] } | { kind: "log"; msg: string };
type State = [number, number] | null;

// Core
export function step(s: State, i: Input): [State, Output[]] {
  if (i.kind === "tick") return [s, [{ kind: "log", msg: "tick" }]];
  if (s === null) return [[i.x, i.y], []];
  return [null, [{ kind: "drawRectangle", from: s, to: [i.x, i.y] }]];
}

export function runPure(inputs: readonly Input[]): Output[] {
  let s: State = null;
  const out: Output[] = [];
  for (const i of inputs) {
    const [next, outputs] = step(s, i);
    s = next;
    out.push(...outputs);
  }
  return out;
}

// Shell: an event source (DOM, socket, stdin) calls `step` and performs the outputs.
export function shell(subscribe: (onInput: (i: Input) => void) => void, perform: (o: Output) => void): void {
  let s: State = null;
  subscribe((i) => {
    const [next, outputs] = step(s, i);
    s = next;
    outputs.forEach(perform);
  });
}
```

**C++**

```cpp
#include <iostream>
#include <optional>
#include <utility>
#include <variant>
#include <vector>

struct Click { int x, y; };
struct Tick {};
using Input = std::variant<Click, Tick>;

struct DrawRectangle { std::pair<int, int> from, to; };
struct Log { const char* msg; };
using Output = std::variant<DrawRectangle, Log>;

using State = std::optional<std::pair<int, int>>;

// Core
std::pair<State, std::vector<Output>> step(const State& s, const Input& in) {
  if (std::holds_alternative<Tick>(in)) return {s, {Log{"tick"}}};
  auto [x, y] = std::get<Click>(in);
  if (!s) return {std::pair{x, y}, {}};
  return {std::nullopt, {DrawRectangle{*s, {x, y}}}};
}

std::vector<Output> runPure(const std::vector<Input>& inputs) {
  State s;
  std::vector<Output> out;
  for (const auto& in : inputs) {
    auto [next, outputs] = step(s, in);
    s = next;
    out.insert(out.end(), outputs.begin(), outputs.end());
  }
  return out;
}

// Shell
int main() {
  for (const auto& o : runPure({Click{0, 0}, Tick{}, Click{10, 10}, Click{5, 5}}))
    std::cout << (std::holds_alternative<DrawRectangle>(o) ? "rectangle\n" : "log\n");
}
```
