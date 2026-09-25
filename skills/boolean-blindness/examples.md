# Boolean and algebraic blindness — worked examples

Each example is given in Haskell, TypeScript, and C++. Each block is self-contained.

## 1. Flags become enumerations

**Haskell**

```haskell
-- Blind: what does True mean? What do three Bools mean together?
openBlind :: Bool -> FilePath -> IO ()
openBlind _ _ = pure ()

data IOMode = ReadMode | WriteMode | AppendMode | ReadWriteMode

openSighted :: IOMode -> FilePath -> IO ()
openSighted _ _ = pure ()

-- Three booleans admit 8 states; a traffic light has 3.
data TrafficLightBlind = TrafficLightBlind {red :: Bool, yellow :: Bool, green :: Bool}

data TrafficLight = Red | Yellow | Green deriving (Show, Eq, Enum, Bounded)

next :: TrafficLight -> TrafficLight
next Red = Green
next Green = Yellow
next Yellow = Red
```

**TypeScript**

```typescript
// Blind: openFile(true, "file.txt")
export declare function openBlind(writable: boolean, path: string): void;

export type IOMode = "read" | "write" | "append" | "readWrite";
export declare function openSighted(mode: IOMode, path: string): void;

type TrafficLightBlind = { red: boolean; yellow: boolean; green: boolean }; // 8 states, 3 legal
export type TrafficLight = "red" | "yellow" | "green";

export const next = (l: TrafficLight): TrafficLight =>
  l === "red" ? "green" : l === "green" ? "yellow" : "red";
export type { TrafficLightBlind };
```

**C++**

```cpp
#include <string>

void openBlind(bool /*writable?*/, const std::string& /*path*/) {}

enum class IOMode { Read, Write, Append, ReadWrite };
void openSighted(IOMode, const std::string&) {}

struct TrafficLightBlind { bool red, yellow, green; };  // 8 states, 3 legal
enum class TrafficLight { Red, Yellow, Green };

TrafficLight next(TrafficLight l) {
  switch (l) {
    case TrafficLight::Red: return TrafficLight::Green;
    case TrafficLight::Green: return TrafficLight::Yellow;
    case TrafficLight::Yellow: return TrafficLight::Red;
  }
  return TrafficLight::Red;  // unreachable for valid enumerators
}

void demo() {
  openBlind(true, "file.txt");            // what does true mean?
  openSighted(IOMode::Read, "file.txt");  // says what it means
}
```

## 2. A `Maybe Bool` with three meanings

From GHCi's source: `Nothing` = no more input (`ghc -e`), `Just True` = last command succeeded, `Just False` = last command failed (abort with exit code 1 under `-e`, continue interactively).

**Haskell**

```haskell
import System.Exit (ExitCode (..))

-- Before: Maybe Bool, meaning documented elsewhere (if anywhere).
data CommandResult
  = NoMoreInput -- ^ ghc -e has consumed all its input
  | Success -- ^ the last command succeeded
  | Failure -- ^ the last command failed
  deriving (Eq, Show)

exitCodeFor :: CommandResult -> Maybe ExitCode
exitCodeFor NoMoreInput = Just ExitSuccess
exitCodeFor Success = Nothing
exitCodeFor Failure = Just (ExitFailure 1)
```

**TypeScript**

```typescript
// Before: boolean | undefined, meaning documented elsewhere (if anywhere).
export type CommandResult =
  | "noMoreInput" // ghc -e has consumed all its input
  | "success" // the last command succeeded
  | "failure"; // the last command failed

export function exitCodeFor(r: CommandResult): number | undefined {
  switch (r) {
    case "noMoreInput":
      return 0;
    case "success":
      return undefined;
    case "failure":
      return 1;
  }
}
```

**C++**

```cpp
#include <optional>

// Before: std::optional<bool>, meaning documented elsewhere (if anywhere).
enum class CommandResult {
  NoMoreInput,  // ghc -e has consumed all its input
  Success,      // the last command succeeded
  Failure,      // the last command failed
};

std::optional<int> exitCodeFor(CommandResult r) {
  switch (r) {
    case CommandResult::NoMoreInput: return 0;
    case CommandResult::Success: return std::nullopt;
    case CommandResult::Failure: return 1;
  }
  return std::nullopt;
}
```

## 3. Evidence on both sides: `partition` with `Either`

Which half of `partition p xs` holds the elements that passed? With `Either`, each side carries its own type, so they cannot be confused.

**Haskell**

```haskell
import Data.Either (partitionEithers)
import Text.Read (readMaybe)

data Rejected = Rejected {input :: String, reason :: String} deriving (Show)

classify :: String -> Either Rejected Int
classify s = maybe (Left (Rejected s "not a number")) Right (readMaybe s)

split :: [String] -> ([Rejected], [Int])
split = partitionEithers . map classify
```

**TypeScript**

```typescript
type Either<L, R> = { tag: "left"; value: L } | { tag: "right"; value: R };
type Rejected = { input: string; reason: string };

const classify = (s: string): Either<Rejected, number> => {
  const n = Number(s);
  return s.trim() !== "" && Number.isFinite(n)
    ? { tag: "right", value: n }
    : { tag: "left", value: { input: s, reason: "not a number" } };
};

export function partitionEithers<L, R>(xs: readonly Either<L, R>[]): [L[], R[]] {
  const ls: L[] = [];
  const rs: R[] = [];
  for (const x of xs) {
    if (x.tag === "left") ls.push(x.value);
    else rs.push(x.value);
  }
  return [ls, rs];
}

export const split = (xs: readonly string[]) => partitionEithers(xs.map(classify));
```

**C++**

```cpp
#include <charconv>
#include <string>
#include <utility>
#include <variant>
#include <vector>

struct Rejected { std::string input, reason; };
using Classified = std::variant<Rejected, int>;

Classified classify(const std::string& s) {
  int n = 0;
  auto [ptr, ec] = std::from_chars(s.data(), s.data() + s.size(), n);
  if (ec != std::errc() || ptr != s.data() + s.size()) return Rejected{s, "not a number"};
  return n;
}

std::pair<std::vector<Rejected>, std::vector<int>> split(const std::vector<std::string>& xs) {
  std::pair<std::vector<Rejected>, std::vector<int>> out;
  for (const auto& s : xs) {
    auto c = classify(s);
    if (auto* r = std::get_if<Rejected>(&c)) out.first.push_back(*r);
    else out.second.push_back(std::get<int>(c));
  }
  return out;
}
```

## 4. Parsers: `token` is the primitive, `satisfy` is derived

With only `satisfy :: (Token -> Bool) -> Parser Token`, parsing a literal needs a partial extraction afterwards. With `token :: (Token -> Maybe a) -> Parser a`, the test hands over the payload. (megaparsec provides both, with `token` primitive.)

**Haskell**

```haskell
data Token = Keyword String | Identifier String | Literal Int deriving (Show)

newtype Parser a = Parser {runParser :: [Token] -> Maybe (a, [Token])}

satisfy :: (Token -> Bool) -> Parser Token
satisfy p = Parser $ \ts -> case ts of
  t : rest | p t -> Just (t, rest)
  _ -> Nothing

token :: (Token -> Maybe a) -> Parser a
token f = Parser $ \ts -> case ts of
  t : rest -> fmap (\a -> (a, rest)) (f t)
  [] -> Nothing

-- Blind: the Bool is thrown away, so we must re-inspect partially.
litBlind :: Parser Int
litBlind = Parser $ \ts -> case runParser (satisfy isLit) ts of
  Just (Literal n, rest) -> Just (n, rest)
  Just _ -> error "ugh" -- "cannot happen"
  Nothing -> Nothing
  where
    isLit (Literal _) = True
    isLit _ = False

-- Sighted: the test returns the payload.
lit :: Parser Int
lit = token $ \t -> case t of
  Literal n -> Just n
  _ -> Nothing
```

**TypeScript**

```typescript
type Token =
  | { kind: "keyword"; text: string }
  | { kind: "identifier"; text: string }
  | { kind: "literal"; value: number };

type Parser<A> = (ts: readonly Token[]) => [A, readonly Token[]] | undefined;

export const token =
  <A,>(f: (t: Token) => A | undefined): Parser<A> =>
  (ts) => {
    const [t, ...rest] = ts;
    if (t === undefined) return undefined;
    const a = f(t);
    return a === undefined ? undefined : [a, rest];
  };

export const lit: Parser<number> = token((t) => (t.kind === "literal" ? t.value : undefined));
```

**C++**

```cpp
#include <optional>
#include <span>
#include <string>
#include <utility>
#include <variant>

struct Keyword { std::string text; };
struct Identifier { std::string text; };
struct Literal { int value; };
using Token = std::variant<Keyword, Identifier, Literal>;

template <typename A>
using ParseResult = std::optional<std::pair<A, std::span<const Token>>>;

template <typename F>
auto token(F f, std::span<const Token> ts) -> ParseResult<typename decltype(f(ts.front()))::value_type> {
  if (ts.empty()) return std::nullopt;
  if (auto a = f(ts.front())) return std::pair{*a, ts.subspan(1)};
  return std::nullopt;
}

ParseResult<int> lit(std::span<const Token> ts) {
  return token([](const Token& t) -> std::optional<int> {
    if (auto* l = std::get_if<Literal>(&t)) return l->value;
    return std::nullopt;
  }, ts);
}
```

## 5. Pattern matching is learning by testing

In the Boolean version, the test and the access are separate, so swapping the branches still compiles and crashes. In the matching version, the branch that has the data is the only one that can use it.

**Haskell**

```haskell
badMap :: (a -> b) -> [a] -> [b]
badMap f xs =
  if null xs
    then []
    else f (head xs) : badMap f (tail xs) -- swap the branches: still compiles

goodMap :: (a -> b) -> [a] -> [b]
goodMap f xs = case xs of
  [] -> []
  x : rest -> f x : goodMap f rest -- swap the branches: x is out of scope
```

**TypeScript**

```typescript
type List<A> = { tag: "nil" } | { tag: "cons"; head: A; tail: List<A> };

export function badMap<A, B>(f: (a: A) => B, xs: readonly A[]): B[] {
  // swap the branches: still compiles (and xs[0]! lies)
  return xs.length === 0 ? [] : [f(xs[0]!), ...badMap(f, xs.slice(1))];
}

export function goodMap<A, B>(f: (a: A) => B, xs: List<A>): List<B> {
  switch (xs.tag) {
    case "nil":
      return { tag: "nil" };
    case "cons": // only here are head and tail in scope
      return { tag: "cons", head: f(xs.head), tail: goodMap(f, xs.tail) };
  }
}
```

**C++**

```cpp
#include <optional>
#include <string>

std::string greetBlind(const std::optional<std::string>& name) {
  if (!name.has_value()) return "hello, stranger";
  return "hello, " + *name;  // invert the test: still compiles, undefined behaviour
}

std::string greetSighted(const std::optional<std::string>& name) {
  // transform only runs where the value exists; the fallback has none to misuse
  return name.transform([](const std::string& n) { return "hello, " + n; })
      .value_or("hello, stranger");
}
```
