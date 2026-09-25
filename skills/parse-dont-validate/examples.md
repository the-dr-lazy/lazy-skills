# Parse, don't validate — worked examples

Every example is given in Haskell, TypeScript, and C++. Each block is self-contained.

## 1. A check whose result is consumed cannot be forgotten

A validator returning `()` can be dropped from the call site and everything still compiles. A parser returning the refined structure cannot: later code needs its result. Here the refined structure is a map, which makes duplicate keys unrepresentable.

**Haskell**

```haskell
import Control.Monad (foldM)
import Data.Map.Strict (Map)
import qualified Data.Map.Strict as Map

-- Validator: the Bool/() result is easy to ignore.
hasDuplicateKeys :: Ord k => [(k, v)] -> Bool
hasDuplicateKeys kvs = Map.size (Map.fromList kvs) /= length kvs

-- Parser: returns the structure that makes duplicates impossible.
parseUniqueKeys :: (Ord k, Show k) => [(k, v)] -> Either String (Map k v)
parseUniqueKeys = foldM insertUnique Map.empty
  where
    insertUnique acc (k, v)
      | Map.member k acc = Left ("duplicate key: " <> show k)
      | otherwise = Right (Map.insert k v acc)

-- Downstream code is written against the representation we wish we had.
lookupPort :: Map String Int -> Maybe Int
lookupPort = Map.lookup "port"
```

**TypeScript**

```typescript
type Result<T, E = string> = { ok: true; value: T } | { ok: false; error: E };

export function parseUniqueKeys<K, V>(
  entries: ReadonlyArray<readonly [K, V]>,
): Result<ReadonlyMap<K, V>> {
  const map = new Map<K, V>();
  for (const [k, v] of entries) {
    if (map.has(k)) return { ok: false, error: `duplicate key: ${String(k)}` };
    map.set(k, v);
  }
  return { ok: true, value: map };
}

export const lookupPort = (config: ReadonlyMap<string, number>): number | undefined =>
  config.get("port");
```

**C++**

```cpp
#include <expected>
#include <map>
#include <optional>
#include <string>
#include <utility>
#include <vector>

template <typename K, typename V>
std::expected<std::map<K, V>, std::string>
parseUniqueKeys(const std::vector<std::pair<K, V>>& entries) {
  std::map<K, V> result;
  for (const auto& [k, v] : entries) {
    if (!result.emplace(k, v).second) return std::unexpected(std::string("duplicate key"));
  }
  return result;
}

std::optional<int> lookupPort(const std::map<std::string, int>& config) {
  if (auto it = config.find("port"); it != config.end()) return it->second;
  return std::nullopt;
}
```

## 2. Parse only what you need; ignore the rest explicitly

A statically typed consumer of an event stream does not need a schema for the universe. It parses the events it cares about and states, in code, what it does with the others. The dynamically typed equivalent makes the same assumptions (`data.user.email` exists) but hides them in every code path.

**Haskell**

```haskell
{-# LANGUAGE OverloadedStrings #-}
import Data.Aeson (Value, withObject, (.:))
import Data.Aeson.Types (Parser, parseMaybe)
import Data.Text (Text)
import qualified Data.Text.IO as Text

data Event = Login LoginPayload | Signup SignupPayload

newtype LoginPayload = LoginPayload {loginUserId :: Int}

data SignupPayload = SignupPayload {signupName :: Text, signupEmail :: Text}

parseEvent :: Value -> Parser Event
parseEvent = withObject "Event" $ \o -> do
  eventType <- o .: "event_type" :: Parser Text
  payload <- o .: "data"
  case eventType of
    "login" -> Login <$> withObject "login" (\d -> LoginPayload <$> d .: "user_id") payload
    "signup" ->
      Signup <$> withObject "signup" (\d -> do
        user <- d .: "user"
        SignupPayload <$> user .: "name" <*> user .: "email") payload
    other -> fail ("event we do not handle: " <> show other)

handleEvent :: (Text -> Text -> IO ()) -> Value -> IO ()
handleEvent sendEmail raw = case parseMaybe parseEvent raw of
  Just (Signup p) -> sendEmail (signupEmail p) ("Welcome, " <> signupName p <> "!")
  Just (Login _) -> pure ()
  Nothing -> pure () -- unknown or malformed events are ignored, by explicit choice

main :: IO ()
main = handleEvent (\to body -> Text.putStrLn (to <> ": " <> body)) "not an event"
```

The `SignupPayload` type is also documentation: it says this service never reads `timestamp` or `userId`. Delete a field; if the code still compiles, nothing depended on it.

**TypeScript**

```typescript
type Event =
  | { kind: "login"; userId: number }
  | { kind: "signup"; name: string; email: string };

const isRecord = (u: unknown): u is Record<string, unknown> =>
  typeof u === "object" && u !== null && !Array.isArray(u);

export function parseEvent(raw: unknown): Event | undefined {
  if (!isRecord(raw)) return undefined;
  const data = raw["data"];
  if (!isRecord(data)) return undefined;
  switch (raw["event_type"]) {
    case "login": {
      const userId = data["user_id"];
      return typeof userId === "number" ? { kind: "login", userId } : undefined;
    }
    case "signup": {
      const user = data["user"];
      if (!isRecord(user)) return undefined;
      const { name, email } = user;
      return typeof name === "string" && typeof email === "string"
        ? { kind: "signup", name, email }
        : undefined;
    }
    default:
      return undefined; // an event this service does not handle
  }
}

export function handleEvent(
  raw: unknown,
  sendEmail: (to: string, body: string) => void,
): void {
  const event = parseEvent(raw);
  if (event?.kind === "signup") sendEmail(event.email, `Welcome, ${event.name}!`);
  // login and unknown events: nothing to do, by explicit choice
}
```

In production TypeScript, a schema library (Zod, Valibot, `effect/Schema`) derives the same parser and the `Event` type from one declaration.

**C++**

```cpp
#include <functional>
#include <map>
#include <optional>
#include <string>
#include <variant>

// The outside world hands us loosely structured data.
using RawEvent = std::map<std::string, std::string>;

struct Login { int userId; };
struct Signup { std::string name, email; };
using Event = std::variant<Login, Signup>;

std::optional<std::string> field(const RawEvent& raw, const std::string& key) {
  if (auto it = raw.find(key); it != raw.end()) return it->second;
  return std::nullopt;
}

std::optional<Event> parseEvent(const RawEvent& raw) {
  auto type = field(raw, "event_type");
  if (type == "login") {
    auto id = field(raw, "data.user_id");
    if (!id) return std::nullopt;
    try { return Login{std::stoi(*id)}; } catch (...) { return std::nullopt; }
  }
  if (type == "signup") {
    auto name = field(raw, "data.user.name");
    auto email = field(raw, "data.user.email");
    if (name && email) return Signup{*name, *email};
  }
  return std::nullopt;  // an event this service does not handle
}

template <class... Fs> struct overloaded : Fs... { using Fs::operator()...; };

void handleEvent(const RawEvent& raw,
                 const std::function<void(const std::string&, const std::string&)>& sendEmail) {
  auto event = parseEvent(raw);
  if (!event) return;  // unknown or malformed: ignored by explicit choice
  std::visit(overloaded{
                 [](const Login&) {},
                 [&](const Signup& s) { sendEmail(s.email, "Welcome, " + s.name + "!"); },
             },
             *event);
}
```

## 3. Keep opaque data opaque

If a foreign service promises only that user IDs are strings, modelling them as UUIDs over-promises. Model them as an opaque type: it can be compared and serialized, nothing else, and it can only be created by the boundary parser.

**Haskell**

```haskell
{-# LANGUAGE DerivingStrategies #-}
{-# LANGUAGE GeneralizedNewtypeDeriving #-}
module UserId (UserId) where -- the constructor is not exported

import Data.Aeson (FromJSON, ToJSON)
import Data.Text (Text)

newtype UserId = UserId Text
  deriving newtype (Eq, Ord, Show, FromJSON, ToJSON)
```

Clients can compare `UserId`s and round-trip them through JSON; they cannot inspect the text or forge a `UserId` from an arbitrary string.

**TypeScript**

```typescript
export class UserId {
  readonly #raw: string;
  private constructor(raw: string) {
    this.#raw = raw;
  }
  static parse(u: unknown): UserId | undefined {
    return typeof u === "string" && u.length > 0 ? new UserId(u) : undefined;
  }
  equals(other: UserId): boolean {
    return this.#raw === other.#raw;
  }
  toJSON(): string {
    return this.#raw;
  }
}
```

**C++**

```cpp
#include <optional>
#include <string>

class UserId {
public:
  static std::optional<UserId> parse(std::string raw) {
    if (raw.empty()) return std::nullopt;
    return UserId(std::move(raw));
  }
  bool operator==(const UserId&) const = default;
  const std::string& serialize() const { return raw_; }

private:
  explicit UserId(std::string raw) : raw_(std::move(raw)) {}
  std::string raw_;
};
```

## 4. Refine inside a branch

Push the burden of proof up only as far as the code that needs it. When a single branch needs a stronger type, parse on entry to that branch.

**Haskell**

```haskell
import Data.List.NonEmpty (NonEmpty (..), nonEmpty)

data Report = EmptyReport | Summary {first :: Int, total :: Int}

summarize :: [Int] -> Report
summarize xs = case nonEmpty xs of
  Nothing -> EmptyReport
  Just ne -> summarizeNonEmpty ne -- this branch has the proof it needs

summarizeNonEmpty :: NonEmpty Int -> Report
summarizeNonEmpty ne@(x :| _) = Summary {first = x, total = sum ne}
```

**TypeScript**

```typescript
type NonEmptyArray<T> = readonly [T, ...T[]];
type Report = { kind: "empty" } | { kind: "summary"; first: number; total: number };

const isNonEmpty = <T,>(xs: readonly T[]): xs is NonEmptyArray<T> => xs.length > 0;

const summarizeNonEmpty = (xs: NonEmptyArray<number>): Report => ({
  kind: "summary",
  first: xs[0],
  total: xs.reduce((a, b) => a + b, 0),
});

export const summarize = (xs: readonly number[]): Report =>
  isNonEmpty(xs) ? summarizeNonEmpty(xs) : { kind: "empty" };
```

**C++**

```cpp
#include <numeric>
#include <span>
#include <variant>
#include <vector>

struct EmptyReport {};
struct Summary { int first; int total; };
using Report = std::variant<EmptyReport, Summary>;

struct NonEmptyView {  // a span plus the proof that it has an element
  int head;
  std::span<const int> all;
};

Report summarizeNonEmpty(NonEmptyView xs) {
  return Summary{xs.head, std::accumulate(xs.all.begin(), xs.all.end(), 0)};
}

Report summarize(const std::vector<int>& xs) {
  if (xs.empty()) return EmptyReport{};
  return summarizeNonEmpty(NonEmptyView{xs.front(), xs});
}
```
