# Free monads — worked examples

Each example is given in Haskell, TypeScript, and C++. Each block is self-contained.

## 1. A sandboxed scripting language for players

Players write programs for an in-game robot. They must not get full `IO`; the game must be free to change how actions are carried out (a new game world, a replay, a test). The command functor is the whole contract: each constructor holds what the player supplies and a continuation for what the interpreter hands back.

**Haskell**

```haskell
{-# LANGUAGE DeriveFunctor #-}
import Control.Monad (forever, when)
import Control.Monad.Free (Free (..), liftF)

data Direction = Forward | Backward deriving (Show)

data Interaction next
  = Fire Direction next
  | ReadLine (String -> next)
  | WriteLine String (Bool -> next)
  deriving (Functor)

type Program = Free Interaction

fire :: Direction -> Program ()
fire d = liftF (Fire d ())

readLine :: Program String
readLine = liftF (ReadLine id)

writeLine :: String -> Program Bool
writeLine s = liftF (WriteLine s id)

easyToAnger :: Program a
easyToAnger = forever $ do
  s <- readLine
  when (s == "No") $ do
    fire Forward
    _ <- writeLine "Take that!"
    pure ()

-- One possible interpreter: replay a chat log and record what the robot did.
data Event = Fired Direction | Said String deriving (Show)

simulate :: [String] -> Program a -> [Event]
simulate _ (Pure _) = []
simulate chat (Free (Fire d next)) = Fired d : simulate chat next
simulate chat (Free (WriteLine s k)) = Said s : simulate chat (k True)
simulate [] (Free (ReadLine _)) = []
simulate (c : cs) (Free (ReadLine k)) = simulate cs (k c)

-- simulate ["Yes", "No"] easyToAnger == [Fired Forward, Said "Take that!"]
```

**TypeScript**

```typescript
type Direction = "forward" | "backward";

type Program<A> =
  | { readonly tag: "pure"; readonly value: A }
  | { readonly tag: "fire"; readonly dir: Direction; readonly next: () => Program<A> }
  | { readonly tag: "readLine"; readonly next: (s: string) => Program<A> }
  | { readonly tag: "writeLine"; readonly line: string; readonly next: (ok: boolean) => Program<A> };

const pure = <A,>(value: A): Program<A> => ({ tag: "pure", value });

function chain<A, B>(p: Program<A>, f: (a: A) => Program<B>): Program<B> {
  switch (p.tag) {
    case "pure": return f(p.value);
    case "fire": return { tag: "fire", dir: p.dir, next: () => chain(p.next(), f) };
    case "readLine": return { tag: "readLine", next: (s) => chain(p.next(s), f) };
    case "writeLine": return { tag: "writeLine", line: p.line, next: (ok) => chain(p.next(ok), f) };
  }
}

const fire = (dir: Direction): Program<void> => ({ tag: "fire", dir, next: () => pure(undefined) });
const readLine: Program<string> = { tag: "readLine", next: pure };
const writeLine = (line: string): Program<boolean> => ({ tag: "writeLine", line, next: pure });

export const easyToAnger = (): Program<never> =>
  chain(readLine, (s) =>
    s === "No"
      ? chain(fire("forward"), () => chain(writeLine("Take that!"), () => easyToAnger()))
      : easyToAnger(),
  );

type Event = { fired: Direction } | { said: string };

export function simulate<A>(chat: readonly string[], program: Program<A>): Event[] {
  const events: Event[] = [];
  let p = program;
  let i = 0;
  for (;;) {
    switch (p.tag) {
      case "pure": return events;
      case "fire": events.push({ fired: p.dir }); p = p.next(); break;
      case "writeLine": events.push({ said: p.line }); p = p.next(true); break;
      case "readLine": {
        const line = chat[i++];
        if (line === undefined) return events;
        p = p.next(line);
      }
    }
  }
}
```

**C++**

```cpp
#include <functional>
#include <memory>
#include <string>
#include <variant>
#include <vector>

enum class Direction { Forward, Backward };

struct Program;  // a program whose result we never need (scripts run forever)
using Next = std::function<Program()>;

struct Done {};
struct Fire { Direction dir; Next next; };
struct ReadLine { std::function<Program(std::string)> next; };
struct WriteLine { std::string line; std::function<Program(bool)> next; };

struct Program { std::variant<Done, Fire, ReadLine, WriteLine> step; };

Program easyToAnger() {
  return {ReadLine{[](std::string s) -> Program {
    if (s != "No") return easyToAnger();
    return {Fire{Direction::Forward, [] {
      return Program{WriteLine{"Take that!", [](bool) { return easyToAnger(); }}};
    }}};
  }}};
}

struct Fired { Direction dir; };
struct Said { std::string line; };
using Event = std::variant<Fired, Said>;

std::vector<Event> simulate(const std::vector<std::string>& chat, Program p) {
  std::vector<Event> events;
  std::size_t i = 0;
  for (;;) {
    if (auto* f = std::get_if<Fire>(&p.step)) { events.push_back(Fired{f->dir}); p = f->next(); }
    else if (auto* w = std::get_if<WriteLine>(&p.step)) { events.push_back(Said{w->line}); p = w->next(true); }
    else if (auto* r = std::get_if<ReadLine>(&p.step)) {
      if (i == chat.size()) return events;
      p = r->next(chat[i++]);
    } else return events;
  }
}
```

## 2. Cooperative threads are merged command lists

A thread is a sequence of atomic steps, each revealing the next only when run. Interleaving two threads is a list merge; running is a fold. This works for any base monad, not just `IO` — thread two `State` computations the same way.

**Haskell**

```haskell
import Control.Monad (ap, liftM)

data Thread m r = Atomic (m (Thread m r)) | Return r

instance Monad m => Functor (Thread m) where fmap = liftM
instance Monad m => Applicative (Thread m) where pure = Return; (<*>) = ap
instance Monad m => Monad (Thread m) where
  Atomic m >>= f = Atomic (fmap (>>= f) m)
  Return r >>= f = f r

atomic :: Monad m => m a -> Thread m a
atomic m = Atomic (fmap Return m)

interleave :: Monad m => Thread m r -> Thread m r -> Thread m r
interleave (Atomic m1) (Atomic m2) = do
  next1 <- atomic m1
  next2 <- atomic m2
  interleave next1 next2
interleave t1 (Return _) = t1
interleave (Return _) t2 = t2

runThread :: Monad m => Thread m r -> m r
runThread (Atomic m) = m >>= runThread
runThread (Return r) = pure r

main :: IO ()
main = runThread (interleave t1 t2) -- prints 1, a, 2, b
  where
    t1 = atomic (print 1) >> atomic (print 2)
    t2 = atomic (putStrLn "a") >> atomic (putStrLn "b")
```

**TypeScript** (generators are TypeScript's native "sequence of atomic steps")

```typescript
type Thread = Generator<void, void, void>;

export function* interleave(t1: Thread, t2: Thread): Thread {
  let a = t1.next();
  let b = t2.next();
  while (!a.done || !b.done) {
    if (!a.done) { yield; a = t1.next(); }
    if (!b.done) { yield; b = t2.next(); }
  }
}

export function runThread(t: Thread): void {
  while (!t.next().done) { /* each step runs one atomic action */ }
}

function* printer(xs: readonly string[], out: string[]): Thread {
  for (const x of xs) { out.push(x); yield; }
}

const out: string[] = [];
runThread(interleave(printer(["1", "2"], out), printer(["a", "b"], out)));
// out is ["1", "a", "2", "b"]
export { out };
```

**C++**

```cpp
#include <functional>
#include <iostream>
#include <memory>

// A thread runs one atomic step and returns the rest (nullptr when finished).
struct Thread {
  std::function<std::shared_ptr<Thread>()> step;
};
using ThreadPtr = std::shared_ptr<Thread>;

ThreadPtr atomic(std::function<void()> action, ThreadPtr rest = nullptr) {
  return std::make_shared<Thread>(Thread{[action, rest] { action(); return rest; }});
}

ThreadPtr interleave(ThreadPtr t1, ThreadPtr t2) {
  if (!t1) return t2;
  if (!t2) return t1;
  return std::make_shared<Thread>(Thread{[t1, t2] {
    ThreadPtr rest1 = t1->step();  // one step of the first thread ...
    return interleave(t2, rest1);  // ... then let the second go first
  }});
}

void runThread(ThreadPtr t) {
  while (t) t = t->step();
}

int main() {
  auto t1 = atomic([] { std::cout << 1 << '\n'; }, atomic([] { std::cout << 2 << '\n'; }));
  auto t2 = atomic([] { std::cout << "a\n"; }, atomic([] { std::cout << "b\n"; }));
  runThread(interleave(t1, t2));  // 1 a 2 b
}
```

## 3. Laws that hold for every interpreter

Because `Free` is plain data, equations about programs can be checked with any interpreter — and, when proved by equational reasoning, hold for all of them. Here: *nothing after `exitSuccess` runs*.

**Haskell**

```haskell
{-# LANGUAGE DeriveFunctor #-}
import Control.Monad.Free (Free (..), liftF)
import Test.QuickCheck

data TeletypeF next = PutStrLn String next | GetLine (String -> next) | ExitSuccess
  deriving (Functor)

type Teletype = Free TeletypeF

putStrLn' :: String -> Teletype ()
putStrLn' s = liftF (PutStrLn s ())

exitSuccess' :: Teletype r
exitSuccess' = liftF ExitSuccess

runPure :: Teletype r -> [String] -> [String]
runPure (Pure _) _ = []
runPure (Free (PutStrLn s next)) xs = s : runPure next xs
runPure (Free (GetLine _)) [] = []
runPure (Free (GetLine k)) (x : xs) = runPure (k x) xs
runPure (Free ExitSuccess) _ = []

-- exitSuccess' >> m  ==  exitSuccess'   (observed through the pure interpreter)
prop_exitSwallowsRest :: [String] -> [String] -> Bool
prop_exitSwallowsRest lines inputs =
  runPure (exitSuccess' >> mapM_ putStrLn' lines) inputs == runPure (exitSuccess' :: Teletype ()) inputs

main :: IO ()
main = quickCheck prop_exitSwallowsRest
```

**TypeScript**

```typescript
import fc from "fast-check";

type Program<A> =
  | { readonly tag: "pure"; readonly value: A }
  | { readonly tag: "putStrLn"; readonly line: string; readonly next: () => Program<A> }
  | { readonly tag: "exitSuccess" };

const pure = <A,>(value: A): Program<A> => ({ tag: "pure", value });
const putStrLn = (line: string): Program<void> => ({ tag: "putStrLn", line, next: () => pure(undefined) });
const exitSuccess: Program<never> = { tag: "exitSuccess" };

function chain<A, B>(p: Program<A>, f: (a: A) => Program<B>): Program<B> {
  switch (p.tag) {
    case "pure": return f(p.value);
    case "putStrLn": return { tag: "putStrLn", line: p.line, next: () => chain(p.next(), f) };
    case "exitSuccess": return p;
  }
}

const sequence = (lines: readonly string[]): Program<void> =>
  lines.reduceRight<Program<void>>((rest, l) => chain(putStrLn(l), () => rest), pure(undefined));

function runPure<A>(p: Program<A>): string[] {
  const out: string[] = [];
  while (p.tag === "putStrLn") { out.push(p.line); p = p.next(); }
  return out;
}

fc.assert(
  fc.property(fc.array(fc.string()), (lines) =>
    JSON.stringify(runPure(chain(exitSuccess, () => sequence(lines)))) === JSON.stringify(runPure(exitSuccess)),
  ),
);
```

**C++**

```cpp
#include <rapidcheck.h>

#include <functional>
#include <string>
#include <variant>
#include <vector>

struct Program;
struct Pure {};
struct PutStrLn { std::string line; std::function<Program()> next; };
struct ExitSuccess {};
struct Program { std::variant<Pure, PutStrLn, ExitSuccess> step; };

Program then(Program p, std::function<Program()> k) {  // p >> k()
  if (std::holds_alternative<Pure>(p.step)) return k();
  if (auto* x = std::get_if<PutStrLn>(&p.step))
    return {PutStrLn{x->line, [next = x->next, k] { return then(next(), k); }}};
  return p;  // ExitSuccess swallows the rest
}

Program sequence(std::vector<std::string> lines, std::size_t i = 0) {
  if (i == lines.size()) return {Pure{}};
  return {PutStrLn{lines[i], [lines, i] { return sequence(lines, i + 1); }}};
}

std::vector<std::string> runPure(Program p) {
  std::vector<std::string> out;
  while (auto* x = std::get_if<PutStrLn>(&p.step)) { out.push_back(x->line); p = x->next(); }
  return out;
}

int main() {
  rc::check("exitSuccess >> m == exitSuccess", [](const std::vector<std::string>& lines) {
    Program exit{ExitSuccess{}};
    RC_ASSERT(runPure(then(exit, [lines] { return sequence(lines); })) == runPure(exit));
  });
}
```
