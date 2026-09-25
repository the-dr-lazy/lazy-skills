---
name: free-monads
description: Free monads — programs as data built from command functors, run by any number of interpreters (IO, pure test, pretty-printer, sandbox). Use when purifying effectful code, when one program needs several interpretations, when sandboxing user scripts, or when checking laws of effectful code.
---

# Free monads

Good programmers separate data from the interpreter that processes it — a compiler builds a syntax tree once and then compiles it, runs it, pretty-prints it, or archives it. A **free monad** gives any set of commands that treatment: `do` notation builds a *value* describing the program, and interpreters decide later what it means.

```haskell
data Free f r = Free (f (Free f r)) | Pure r   -- a list of functors ending in a result
```

- `Pure` is like `Nil`: no more commands, here is the result.
- `Free` is like `Cons`: one command whose "rest of the program" is inside the functor.
- `(>>=)` appends programs (it is list concatenation for commands); `liftF` makes a one-command program.
- It is the *freest* monad: it adds nothing beyond what makes it a monad, so it leaves the interpreter maximal freedom. That is also its limit — **it guarantees no laws of the commands**. `put x >> put y = put y` holds only if an interpreter makes it hold.

## Procedure

1. **Name the commands.** One constructor per operation. A command that returns information to the program carries a continuation (`GetLine (String -> next)`); one that returns nothing carries `next`; one that ends the program carries nothing (`ExitSuccess`). The command functor is the *contract* between program writer and interpreter for a single step.
2. **Derive the functor** (`deriving Functor`) and lift each command into a smart constructor with `liftF`.
3. **Write the program** with ordinary monadic code. It is pure data; nothing has run.
4. **Write interpreters.** Pattern match on `Pure` / `Free cmd` and recurse. Typical set: the production interpreter (to `IO`, or into another monad), a **pure interpreter** for tests, a pretty-printer or logger, a dry-run.
5. **Test and reason with the pure interpreter.** Equational laws proved for the free program hold under *every* interpreter (`exitSuccess' >> m = exitSuccess'`); property tests against a pure interpreter replace brittle IO tests.

Done when: all logic lives in the free program, the production interpreter is a flat pattern match with no business decisions in it, and at least one pure interpreter exercises the program in tests.

## Example: purify an echo program

The original mixes logic with effects, and whether the last line ever runs depends on how `exitSuccess` happens to be implemented. The purified version concentrates *all* impure code in `runIO`, and the claim can be tested — and proved — once, for every interpreter.

**Haskell** (`free` package)

```haskell
{-# LANGUAGE DeriveFunctor #-}
import Control.Monad.Free (Free (..), liftF)
import System.Exit (exitSuccess)
import Test.QuickCheck (quickCheck)

data TeletypeF next
  = PutStrLn String next
  | GetLine (String -> next)
  | ExitSuccess
  deriving (Functor)

type Teletype = Free TeletypeF

putStrLn' :: String -> Teletype ()
putStrLn' s = liftF (PutStrLn s ())

getLine' :: Teletype String
getLine' = liftF (GetLine id)

exitSuccess' :: Teletype r
exitSuccess' = liftF ExitSuccess

echo :: Teletype ()
echo = do
  s <- getLine'
  putStrLn' s
  exitSuccess'
  putStrLn' "Finished" -- never runs, under any interpreter

runIO :: Teletype r -> IO r -- the only impure code
runIO (Pure r) = pure r
runIO (Free (PutStrLn s next)) = putStrLn s >> runIO next
runIO (Free (GetLine k)) = getLine >>= runIO . k
runIO (Free ExitSuccess) = exitSuccess

runPure :: Teletype r -> [String] -> [String] -- inputs in, outputs out
runPure (Pure _) _ = []
runPure (Free (PutStrLn s next)) xs = s : runPure next xs
runPure (Free (GetLine _)) [] = []
runPure (Free (GetLine k)) (x : xs) = runPure (k x) xs
runPure (Free ExitSuccess) _ = []

main :: IO ()
main = quickCheck (\xs -> runPure echo xs == take 1 xs) -- echo is a glorified `take 1`
```

**TypeScript** (no higher-kinded types, so the program type is specialized to one command set)

```typescript
type Program<A> =
  | { readonly tag: "pure"; readonly value: A }
  | { readonly tag: "putStrLn"; readonly line: string; readonly next: () => Program<A> }
  | { readonly tag: "getLine"; readonly next: (line: string) => Program<A> }
  | { readonly tag: "exitSuccess" };

const pure = <A,>(value: A): Program<A> => ({ tag: "pure", value });
const putStrLn = (line: string): Program<void> => ({ tag: "putStrLn", line, next: () => pure(undefined) });
const getLine: Program<string> = { tag: "getLine", next: pure };
const exitSuccess: Program<never> = { tag: "exitSuccess" };

function chain<A, B>(p: Program<A>, f: (a: A) => Program<B>): Program<B> {
  switch (p.tag) {
    case "pure": return f(p.value);
    case "putStrLn": return { tag: "putStrLn", line: p.line, next: () => chain(p.next(), f) };
    case "getLine": return { tag: "getLine", next: (s) => chain(p.next(s), f) };
    case "exitSuccess": return p;
  }
}

export const echo: Program<void> = chain(getLine, (s) =>
  chain(putStrLn(s), () => chain(exitSuccess, () => putStrLn("Finished"))),
);

// Pure interpreter: a loop, so long programs do not grow the stack.
export function runPure<A>(program: Program<A>, inputs: readonly string[]): string[] {
  const out: string[] = [];
  let p = program;
  let i = 0;
  for (;;) {
    switch (p.tag) {
      case "putStrLn": out.push(p.line); p = p.next(); break;
      case "getLine": {
        const line = inputs[i++];
        if (line === undefined) return out;
        p = p.next(line);
        break;
      }
      case "pure":
      case "exitSuccess":
        return out;
    }
  }
}

// Production interpreter over an injected console.
export async function runIO<A>(
  program: Program<A>,
  io: { readLine: () => Promise<string>; writeLine: (s: string) => void; exit: () => never },
): Promise<A> {
  let p = program;
  for (;;) {
    switch (p.tag) {
      case "putStrLn": io.writeLine(p.line); p = p.next(); break;
      case "getLine": p = p.next(await io.readLine()); break;
      case "exitSuccess": return io.exit();
      case "pure": return p.value;
    }
  }
}
```

**C++** (commands in a `std::variant`, continuations in `std::function`)

```cpp
#include <functional>
#include <string>
#include <type_traits>
#include <variant>
#include <vector>

template <typename A> struct Program;
template <typename A> struct Pure { A value; };
template <typename A> struct PutStrLn { std::string line; std::function<Program<A>()> next; };
template <typename A> struct GetLine { std::function<Program<A>(std::string)> next; };
struct ExitSuccess {};

template <typename A>
struct Program { std::variant<Pure<A>, PutStrLn<A>, GetLine<A>, ExitSuccess> step; };

using Unit = std::monostate;
template <typename A> Program<A> pure(A a) { return {Pure<A>{std::move(a)}}; }
inline Program<Unit> putStrLn(std::string s) { return {PutStrLn<Unit>{std::move(s), [] { return pure(Unit{}); }}}; }
inline Program<std::string> getLine() { return {GetLine<std::string>{[](std::string s) { return pure(std::move(s)); }}}; }
template <typename A> Program<A> exitSuccess() { return {ExitSuccess{}}; }

template <typename T> struct ValueOf;
template <typename B> struct ValueOf<Program<B>> { using type = B; };

template <typename A, typename F>
auto bind(Program<A> p, F f) -> Program<typename ValueOf<std::invoke_result_t<F, A>>::type> {
  using B = typename ValueOf<std::invoke_result_t<F, A>>::type;
  if (auto* x = std::get_if<Pure<A>>(&p.step)) return f(std::move(x->value));
  if (auto* x = std::get_if<PutStrLn<A>>(&p.step))
    return {PutStrLn<B>{x->line, [next = x->next, f] { return bind(next(), f); }}};
  if (auto* x = std::get_if<GetLine<A>>(&p.step))
    return {GetLine<B>{[next = x->next, f](std::string s) { return bind(next(std::move(s)), f); }}};
  return {ExitSuccess{}};
}

inline Program<Unit> echo() {
  return bind(getLine(), [](std::string s) {
    return bind(putStrLn(std::move(s)), [](Unit) {
      return bind(exitSuccess<Unit>(), [](Unit) { return putStrLn("Finished"); });
    });
  });
}

template <typename A>
std::vector<std::string> runPure(Program<A> p, const std::vector<std::string>& inputs) {
  std::vector<std::string> out;
  std::size_t i = 0;
  for (;;) {
    if (auto* x = std::get_if<PutStrLn<A>>(&p.step)) { out.push_back(x->line); p = x->next(); }
    else if (auto* x = std::get_if<GetLine<A>>(&p.step)) {
      if (i == inputs.size()) return out;
      p = x->next(inputs[i++]);
    } else return out;  // Pure or ExitSuccess
  }
}
```

More: a sandboxed game-scripting language with its interaction contract, cooperative threads as merged command lists, and law checking through a pure interpreter — in three languages: [examples.md](examples.md).

## Trade-offs and when to reach for something else

- **Performance:** naive `Free` has quadratic left-nested binds and allocates per step. Church-encoded / codensity free monads, freer monads, or a concrete effect library fix this (`algebraic-effect-systems`).
- **Several command sets:** one functor per program does not compose. Coproducts of functors (`data-types-a-la-carte`) or an extensible effect system solve it.
- **Laws belong to interpreters.** If you need `State` laws, delegate that part of the meaning to a real `State` (`FreeT f (State s)`) instead of simulating `Get`/`Put` commands.
- **`FreeT`** interleaves command steps with a base monad — generators and streaming (`yield` as a command, the consumer demands one element at a time).
- **Higher-order operations** (`bracket`, `local`, `catch`) do not fit a plain functor; effect systems handle them explicitly.
- **Mainstream languages:** TypeScript and C++ lack higher-kinded types, so each command set gets its own `Program` type (the "operational" style above). Generator-based "do notation" (`function*` / `yield`, as in Effect-TS's `Effect.gen`) is the idiomatic TypeScript surface syntax; the interpreter drives the generator.

## Related skills

`composable-effects` (choosing among effect approaches) · `algebraic-effect-systems` · `functional-core-imperative-shell` · `embedded-dsl` · `data-types-a-la-carte` · `continuations` · `property-based-testing` · `everything-as-a-value`

## Sources

- Gabriella Gonzalez, [Why free monads matter](https://haskellforall.com/2012/06/you-could-have-invented-free-monads) (2012).
- Gabriella Gonzalez, [Purify code using free monads](https://haskellforall.com/2012/07/purify-code-using-free-monads) (2012).
- Gabriella Gonzalez, [Free monad transformers](https://haskellforall.com/2012/07/free-monad-transformers) (2012).
- Gabriella Gonzalez, [Algebraic side effects](https://haskellforall.com/2015/03/algebraic-side-effects) (2015).
- functional-architecture.org, [Composable Effects](https://functional-architecture.org/composable_effects/) (pattern page; upstream TODO) and the *Shortcomings* section of [Functional Core, Imperative Shell](https://functional-architecture.org/functional_core_imperative_shell/).
