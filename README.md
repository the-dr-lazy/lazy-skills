# lazy-skills

Agent skills for **functional software architecture** and **functional domain modeling**: principles, patterns, effect systems, and property-based testing — distilled from [functional-architecture.org](https://functional-architecture.org/), Alexis King, Scott Wlaschin, Gabriella Gonzalez, and the other authors in the [bibliography](#bibliography).

These patterns, architectures, and concepts come from functional programming, but **they are not restricted to functional languages**. Every skill shows its examples in three languages — **Haskell**, **TypeScript**, and **C++** — and says where a mainstream language enforces the idea, where it needs an encoding, and where it becomes a convention. How far a pattern goes in your language depends on the language and its community's libraries; each skill names the relevant ones.

## Install

As a Claude Code plugin (this repository is its own marketplace), from inside Claude Code:

```text
/plugin marketplace add the-dr-lazy/lazy-skills
/plugin install lazy-skills@lazy-skills
```

Or copy individual directories from [`skills/`](skills/) into `~/.claude/skills/` (personal) or `.claude/skills/` (per project).

Each skill is a directory with a `SKILL.md` (when to use it, the procedure, a worked example in all three languages, related skills, sources) and, where there is more material, an `examples.md` with further worked examples. Skills are model-invoked: the agent loads one when its description matches the task. Start from [`functional-architecture`](skills/functional-architecture/SKILL.md) when unsure which one applies.

## Skills

### Overview

| Skill | What it covers |
|---|---|
| [functional-architecture](skills/functional-architecture/SKILL.md) | Values, principles, and patterns of functional-architecture.org mapped to the skills below; a situation → skill guide; evaluating technologies against principles; [FUNARCH publications](skills/functional-architecture/publications.md) |

### Principles (functional-architecture.org)

| Skill | What it covers | Upstream page |
|---|---|---|
| [immutability](skills/immutability/SKILL.md) | Values instead of locations; persistent data; change as a function | TODO |
| [pure-functions](skills/pure-functions/SKILL.md) | Side effects, referential transparency, recognizing and removing hidden effects | TODO |
| [everything-as-a-value](skills/everything-as-a-value/SKILL.md) | Reifying concepts (functions, programs, UIs, accessors, rules) as first-class values | Draft |
| [composition-and-closure](skills/composition-and-closure/SKILL.md) | Combining A's into an A: monoids, categories, functors, applicatives | TODO |
| [algebraic-modelling](skills/algebraic-modelling/SKILL.md) | Properties and algebraic structures as a design method; laws as tests | Published |
| [airtight-abstractions](skills/airtight-abstractions/SKILL.md) | Abstractions defined by meaning and laws, with no representation leaks | TODO |
| [architecture-as-code](skills/architecture-as-code/SKILL.md) | Architectural decisions in types and code; documentation generated from code | TODO |
| [decoupled-by-default](skills/decoupled-by-default/SKILL.md) | Narrow channels, affordances toward low coupling | Draft (German) |
| [late-decision-making](skills/late-decision-making/SKILL.md) | Designing so decisions stay cheap to change; model before representation | Draft |
| [modularization](skills/modularization/SKILL.md) | Hiding decisions behind simple interfaces; vertical module organization | TODO |
| [make-illegal-states-unrepresentable](skills/make-illegal-states-unrepresentable/SKILL.md) | Sum-of-products, enums, structures with built-in invariants, state machines | Published (2 sections TODO) |

### Patterns, tools, and techniques (functional-architecture.org)

| Skill | What it covers | Upstream page |
|---|---|---|
| [functional-core-imperative-shell](skills/functional-core-imperative-shell/SKILL.md) | Pure core, thin effectful shell; decisions as data | Published |
| [zipper](skills/zipper/SKILL.md) | A structure plus a movable focus; O(1) local edits of immutable data | TODO |
| [continuations](skills/continuations/SKILL.md) | The rest of the computation as a value; workflows as straight-line code | TODO |
| [functional-programming-languages](skills/functional-programming-languages/SKILL.md) | Choosing languages by their defaults; translating FP idioms into TS/C++ | TODO |
| [expressive-static-types](skills/expressive-static-types/SKILL.md) | Types as a tool you direct; strictness; containing escape hatches | TODO |
| [event-sourcing](skills/event-sourcing/SKILL.md) | Event log as source of truth; `decide`/`evolve`/projections | TODO (short text only) |
| [bidirectional-data-transformations](skills/bidirectional-data-transformations/SKILL.md) | Lenses, isos, prisms: one declaration, both directions | Published (partly TODO) |
| [embedded-dsl](skills/embedded-dsl/SKILL.md) | Deep and shallow embeddings; interpreters; the cost of DSLs | TODO |
| [composable-effects](skills/composable-effects/SKILL.md) | Making effects explicit and interchangeable; the ladder of approaches | TODO |
| [composable-error-handling](skills/composable-error-handling/SKILL.md) | Errors as values; open variants first (one type per error, handled errors leave the type); flat short-circuiting; accumulation; layer translation | TODO |
| [composable-guis](skills/composable-guis/SKILL.md) | UIs as values; Model-View-Update; components composed by functors | TODO |
| [property-based-testing](skills/property-based-testing/SKILL.md) | Choosing properties, generators, shrinking, model-based testing | TODO |
| [formal-verification](skills/formal-verification/SKILL.md) | The ladder of rigor; trusted kernels; certifiers; model checking | TODO |
| [denotational-design](skills/denotational-design/SKILL.md) | Meaning first; type class morphisms; testing implementation against meaning | TODO (short text only) |
| [parse-dont-validate](skills/parse-dont-validate/SKILL.md) | Refine input into precise types once, at the boundary | TODO |
| [trees-that-grow](skills/trees-that-grow/SKILL.md) | Phase-indexed extensible ADTs | TODO |
| [data-types-a-la-carte](skills/data-types-a-la-carte/SKILL.md) | The expression problem; coproducts of functors; object algebras | TODO |
| [smart-constructor](skills/smart-constructor/SKILL.md) | Normalizing, validating constructors behind hidden representations | TODO |
| [correctness-by-construction](skills/correctness-by-construction/SKILL.md) | Constructive types, typestate, GADTs, machine-checked specifications | TODO |

### Domain modeling (beyond the site's list)

| Skill | What it covers |
|---|---|
| [designing-with-types](skills/designing-with-types/SKILL.md) | Wlaschin's step-by-step workflow from a primitive-obsessed record to precise types |
| [names-are-not-type-safety](skills/names-are-not-type-safety/SKILL.md) | **Intrinsic vs extrinsic safety; newtypes as tokens; when a wrapper is only a name; type-alias smells** |
| [boolean-blindness](skills/boolean-blindness/SKILL.md) | Boolean and algebraic blindness; witnesses instead of booleans ("learning by testing") |
| [belt-and-suspenders](skills/belt-and-suspenders/SKILL.md) | Two independent guards when a failure cannot be made structurally impossible |

### Free monads and algebraic effect systems (beyond the site's list)

| Skill | What it covers |
|---|---|
| [free-monads](skills/free-monads/SKILL.md) | Programs as data; interpreters; purifying code; laws through pure interpreters |
| [algebraic-effect-systems](skills/algebraic-effect-systems/SKILL.md) | effectful, polysemy, mtl, Effect-TS, C++ capabilities; higher-order effects; handler semantics |

## Verified examples

Every Haskell, TypeScript, and C++ code block in `skills/**/*.md` (266 blocks at the time of writing) is type-checked by [`tools/check_examples.py`](tools/check_examples.py): GHC 9.10 (`-fno-code`), TypeScript 5.9 (`--strict --noUncheckedIndexedAccess --exactOptionalPropertyTypes`), and Clang 21 (`-std=c++23 -Wall -fsyntax-only`). Blocks with a `main` were also compiled and run while writing the skills, and every property-based test runs green (or fails exactly where the text says it must, as in the "Enterprise Developer from Hell" examples). Each block is self-contained; put `<!-- check:skip -->` on the line before a block that is intentionally not compilable.

### Development environment

The toolchain (GHC 9.10 with every imported package, Clang 21 with RapidCheck, Node.js 22, Python 3) is declared in [`devenv.nix`](devenv.nix). With [devenv](https://devenv.sh/getting-started/) and [direnv](https://direnv.net/) installed:

```bash
direnv allow
```

Entering the directory then loads the shell, installs the TypeScript dependencies into `tools/ts`, and installs the git hooks. Without direnv, use `devenv shell`. The shell provides:

- `check-skills` — validates every skill: frontmatter (`name` matches the directory, is lowercase-hyphenated and ≤ 64 characters; `description` is non-empty, ≤ 1024 characters, and has no XML tags; no unknown keys), `SKILL.md` under 500 lines, balanced code fences, relative links that resolve, valid `.claude-plugin/*.json`, and every skill linked from this README ([`tools/check_skills.py`](tools/check_skills.py)).
- `check-examples [--lang haskell|typescript|cpp] [paths...]` — type-checks the code blocks. Optional: `GHCFLAGS="-Werror=incomplete-patterns"`.
- `devenv test` — runs every git hook on every file.

The pre-commit hook runs `check-skills`, `check-examples` on the staged Markdown files, `check-json`, `actionlint`, and `nixfmt`. CI ([`.github/workflows/check.yml`](.github/workflows/check.yml)) runs the same checks on every push to `main` and every pull request.

Without Nix: install GHC with `QuickCheck hedgehog containers mtl free polysemy polysemy-plugin effectful effectful-th lens optics aeson text time`, Clang ≥ 19 (or GCC ≥ 14) with RapidCheck, Node.js ≥ 20, and Python 3 with PyYAML; run `npm install --prefix tools/ts`; then `python3 tools/check_skills.py` and `GHC=… CXX=… CXXFLAGS=-I/path/to/rapidcheck/include python3 tools/check_examples.py`.

## TODO

### Topics not yet completed upstream on functional-architecture.org

The skills below exist, but the corresponding page on functional-architecture.org is unfinished, so the skill is synthesized from the other sources in the bibliography (each skill's *Sources* section says which). Revisit each skill when its upstream page is published.

**Principles**

- [ ] **Immutability** — page TODO. Skill currently based on the *Decoupled by Default* draft, Gonzalez, Wlaschin, King, and Hickey (*The Value of Values*, *Are We There Yet?*).
- [ ] **Pure Functions** — page TODO. Based on McNally (*Side Effect*), Gonzalez, and Hughes (*Why Functional Programming Matters*).
- [ ] **Everything as a Value** — draft (reification; functions and Jolie services as first-class values).
- [ ] **Composition and Closure** — page TODO. Based on Gonzalez's category/functor/scalable-architecture posts, Milewski's *Category Theory for Programmers*, Yorgey's *Typeclassopedia*, and Hughes.
- [ ] **Airtight Abstractions** — page TODO. Based on King and Gonzalez.
- [ ] **Architecture as Code** — page TODO. Based on FUNARCH papers (Crem, Crichton), Gonzalez, and the Structurizr documentation.
- [ ] **Decoupled by Default** — draft, currently **German only**; the skill summarizes it in English (re-check against an English version when published).
- [ ] **Late Decision Making** — draft; the incidents case study stops mid-way (placeholder image and "…").
- [ ] **Modularization** — page TODO. Based on Gonzalez, King, and FUNARCH (GHC and DDD).
- [ ] **Make Illegal States Unrepresentable** — published, but the *Smart constructors* and *Decoupling* sections are TODO.

**Patterns**

- [ ] **Zipper** — short description only; long form TODO. The skill relies on Huet's paper (outside the provided sources) and *Learn You a Haskell*.
- [ ] **Continuations** — short description is literally "TODO". Based on FUNARCH 2024 (Congame), Gonzalez, and the Racket *Continue* tutorial.
- [ ] **Use of functional programming languages** — page TODO.
- [ ] **Expressive static type systems** — page TODO.
- [ ] **Event Sourcing** — short description only; long form TODO.
- [ ] **Bidirectional Data Transformations** — published, but *When to reach for this pattern*, *When not to*, and the Erlang/Elixir library list are TODO.
- [ ] **Embedded Domain-Specific Languages** — short description is "TODO".
- [ ] **Composable Effects** — page TODO (the published FCIS page links to it).
- [ ] **Composable Error Handling** — page TODO (the published FCIS page links to it).
- [ ] **Composable GUI libraries** — page TODO.
- [ ] **Property-based testing** — page TODO (the skill is based on Wlaschin's complete series, plus Hughes's *How to Specify It!* and falsify's documentation).
- [ ] **Formal Verification** — short description is "TODO". Based on FUNARCH 2024/2025 experience reports, *Learn TLA+*, and *Functional Programming in Lean*.
- [ ] **Denotational Design** — short description only. The skill relies on Conal Elliott's work (outside the provided sources); its link to model-based testing comes from Hughes's *How to Specify It!*.
- [ ] **Parse, don't validate** — page TODO (the skill is based on King's post, with Parsons and a TypeScript walkthrough).
- [ ] **Trees that grow** — short description only. Relies on Najd & Peyton Jones, Perez (FUNARCH 2023), and the notes in GHC's `Language.Haskell.Syntax.Extension`.
- [ ] **Data types à la carte** — short description only. Relies on Swierstra and on object algebras (outside the provided sources), plus Maguire's *Better Data Types à la Carte*.
- [ ] **Smart constructor** — page TODO (the skill is based on Wlaschin, King, Kowainik's mini-patterns, and Karpov).
- [ ] **Correctness by Construction** — short description is "TODO".

**Elsewhere on the site**

- [ ] FAQ answers are TODO: *Which domains suit functional architecture?* and *How do you interface with external systems?* (the overview skill gives interim pointers).
- [ ] FUNARCH 2026: proceedings and video links are TODO; one entry is titled "Evolution of Functional UI Paradigms" while its abstract describes the *Lokalisierung* event-based system (recorded as such in [publications.md](skills/functional-architecture/publications.md)).

### Future work for this repository

- [ ] Add `examples.md` (more worked examples in all three languages) to the skills that currently have one example: airtight-abstractions, architecture-as-code, belt-and-suspenders, bidirectional-data-transformations, composable-guis, composition-and-closure, continuations, data-types-a-la-carte, decoupled-by-default, denotational-design, embedded-dsl, event-sourcing, everything-as-a-value, expressive-static-types, formal-verification, functional-programming-languages, immutability, late-decision-making, modularization, pure-functions, trees-that-grow, zipper.
- [ ] Traverse follow-ups linked from the sources: *Polysemy is fun!* part 2 (interpreters), further *Haskell Unfolder* episodes (falsify, laws, testing without a reference implementation), and Sandy Maguire's other Polysemy internals posts.
- [x] Run `tools/check_examples.py` in CI.
- [ ] Add trigger evaluations for the skill descriptions (does the agent pick the right skill for a prompt?).
- [ ] Consider additional example languages the sources use (F#, OCaml, Clojure, Scala, Rust).

## Bibliography

Sources traversed for this repository, grouped as requested. Every skill cites the specific sources it draws on.

### Architecture

- **Active Group GmbH and contributors** (Michael Sperber, Markus Schlegel, et al.), [*Functional Software Architecture — FP in the Large*](https://functional-architecture.org/), source at [functional-architecture/functional-architecture.github.io](https://github.com/functional-architecture/functional-architecture.github.io): values, principles, patterns, FAQ, the definitions of value/principle/pattern (`README.org`), and the pages [Algebraic Modelling](https://functional-architecture.org/algebra/), [Make Illegal States Unrepresentable](https://functional-architecture.org/make_illegal_states_unrepresentable/), [Functional Core, Imperative Shell](https://functional-architecture.org/functional_core_imperative_shell/), [Bidirectional Data Transformations](https://functional-architecture.org/bidirectional_data_transformations/), [Everything as a Value](https://functional-architecture.org/eaav/) (draft), [Decoupled by Default](https://functional-architecture.org/dbd/) (draft), [Late Decision Making](https://functional-architecture.org/late/) (draft), [Events](https://functional-architecture.org/events/), [Publications](https://functional-architecture.org/publications/).
- **FUNARCH — ACM SIGPLAN Workshop on Functional Software Architecture** (2023–2026), all papers and talks summarized in [publications.md](skills/functional-architecture/publications.md), including: Sperber (opening talk, 2023; *Six Years of FUNAR*, 2025; *Lokalisierung*, 2026); Wehr (self-adjusting computations, 2023); Perone & Karachalias (*Crem*, 2023); Knoble & Popa (*GUI Easy*, 2023); Gibbons, Kidney, Schrijvers & Wu (*Phases in Software Architecture*, 2023); Young, Henry & Ericson (*Stretching GHC*, 2023); Crichton (*Typed Design Patterns*, 2023); Perez (*Types that Change*, 2023); Sampellegrini (*Architecting Functional Programs*, 2024); Ma et al. (*F3*, 2024); Sottile & Tekriwal (verified interpreter, 2024); Chapman, Bailly & Vinogradova (*Cardano*, 2024); Kaufmann & Popa (*Continuations*, 2024); Crestani, Schlegel & Schneider (*Bidirectional Data Transformations*, 2024); Krijnen, Swierstra, Keller, Chakravarty & Dral (*Layered Certifying Compiler*, 2025); Sperber & Schlegel (*Evolution of Functional UI Paradigms*, 2025); Ellis (*Bluefin in Industry*, 2025); Feldman (*Functional Mechanical Sympathy*, 2026); Oh, Liu & Wadler (*Plinth and Plutarch*, 2026); Heuer, Woldmann Lu & Haase (*Typestate and Newtype in Rust*, 2026).

### Domain modeling

- Alexis King, [*Parse, don't validate*](https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/) (2019).
- **Alexis King, [*Names are not type safety*](https://lexi-lambda.github.io/blog/2020/11/01/names-are-not-type-safety/) (2020).**
- Scott Wlaschin, *Designing with types* series, F# for Fun and Profit (2013): [Introduction](https://fsharpforfunandprofit.com/posts/designing-with-types-intro/) · [Single case union types](https://fsharpforfunandprofit.com/posts/designing-with-types-single-case-dus/) · [Making illegal states unrepresentable](https://fsharpforfunandprofit.com/posts/designing-with-types-making-illegal-states-unrepresentable/) · [Discovering new concepts](https://fsharpforfunandprofit.com/posts/designing-with-types-discovering-the-domain/) · [Making state explicit](https://fsharpforfunandprofit.com/posts/designing-with-types-representing-states/) · [Constrained strings](https://fsharpforfunandprofit.com/posts/designing-with-types-more-semantic-types/) · [Non-string types](https://fsharpforfunandprofit.com/posts/designing-with-types-non-strings/) · [Conclusion](https://fsharpforfunandprofit.com/posts/designing-with-types-conclusion/) ([series index](https://fsharpforfunandprofit.com/series/designing-with-types/)).
- Wolf McNally, [*Make Illegal States Unrepresentable*](https://aipatternbook.com/make-illegal-states-unrepresentable) and [*Belt-and-Suspenders*](https://aipatternbook.com/belt-and-suspenders), *Encyclopedia of Agentic Coding Patterns*.
- David Luposchainsky (quchen), [*Algebraic blindness*](https://github.com/quchen/articles/blob/master/algebraic-blindness.md).
- Type aliases: Edward Z. Yang, [*On type synonyms*](https://blog.ezyang.com/2011/06/on-type-synonyms/) (2011) · Kowainik, [*Haskell Style Guide*](https://github.com/kowainik/org/blob/main/style-guide.md) · Google, [*C++ Style Guide: Aliases*](https://google.github.io/styleguide/cppguide.html#Aliases).
- Edsko de Vries & Andres Löh (Well-Typed), [*The Haskell Unfolder, Episode 7: learning by testing*](https://discourse.haskell.org/t/the-haskell-unfolder-episode-7-learning-by-testing/6979) (2023), with the episode's [code](https://github.com/well-typed/unfolder/tree/main/episode007-learning-by-testing).

### Free monads and algebraic effect systems

- Raghu Kaippully, [*Polysemy is fun! — Part 1*](https://haskell-explained.gitlab.io/blog/posts/2019/07/28/polysemy-is-cool-part-1/index.html), Haskell Explained (2019).
- Sandy Maguire, [*Polysemy Internals: The Effect-Interpreter Effect*](https://reasonablypolymorphic.com/blog/tactics/), Reasonably Polymorphic (2019).
- Gabriella Gonzalez, [*Why free monads matter*](https://haskellforall.com/2012/06/you-could-have-invented-free-monads) (a.k.a. "You could have invented free monads"), Haskell for all (2012).
- Andrzej Rybczak and contributors, [*effectful*](https://github.com/haskell-effectful/effectful) — "a performant implementation of extensible effects" (README and the [`Effectful.Dispatch.Dynamic`](https://hackage.haskell.org/package/effectful-core/docs/Effectful-Dispatch-Dynamic.html) documentation).
- Wolf McNally, [*Side Effect*](https://aipatternbook.com/side-effect/), *Encyclopedia of Agentic Coding Patterns*.

### Property-based testing

- Scott Wlaschin, *Property Based Testing* series, F# for Fun and Profit (2014): [The Enterprise Developer from Hell](https://fsharpforfunandprofit.com/posts/property-based-testing/) · [Understanding FsCheck](https://fsharpforfunandprofit.com/posts/property-based-testing-1/) · [Choosing properties for property-based testing](https://fsharpforfunandprofit.com/posts/property-based-testing-2/) · [Choosing properties in practice, part 1](https://fsharpforfunandprofit.com/posts/property-based-testing-3/) · [part 2](https://fsharpforfunandprofit.com/posts/property-based-testing-4/) · [part 3](https://fsharpforfunandprofit.com/posts/property-based-testing-5/) ([series index](https://fsharpforfunandprofit.com/series/property-based-testing/)).

### From the blogs traversed for related posts

**Alexis King — [lexi-lambda.github.io](https://lexi-lambda.github.io/)** (all 32 posts triaged; the relevant ones read in full; posts on Racket macros, Hackett, deployment, and tooling are out of scope). Used:

- [*Types as axioms, or: playing god with static types*](https://lexi-lambda.github.io/blog/2020/08/13/types-as-axioms-or-playing-god-with-static-types/) (2020)
- [*No, dynamic type systems are not inherently more open*](https://lexi-lambda.github.io/blog/2020/01/19/no-dynamic-type-systems-are-not-inherently-more-open/) (2020)
- [*Using types to unit-test in Haskell*](https://lexi-lambda.github.io/blog/2016/10/03/using-types-to-unit-test-in-haskell/) (2016)
- [*Lifts for free: making mtl typeclasses derivable*](https://lexi-lambda.github.io/blog/2017/04/28/lifts-for-free-making-mtl-typeclasses-derivable/) (2017)
- [*Unit testing effectful Haskell with monad-mock*](https://lexi-lambda.github.io/blog/2017/06/29/unit-testing-effectful-haskell-with-monad-mock/) (2017)
- [*Climbing the infinite ladder of abstraction*](https://lexi-lambda.github.io/blog/2016/08/11/climbing-the-infinite-ladder-of-abstraction/) (2016)
- Also read: [*Demystifying MonadBaseControl*](https://lexi-lambda.github.io/blog/2019/09/07/demystifying-monadbasecontrol/) (2019) and [*An opinionated guide to Haskell in 2018*](https://lexi-lambda.github.io/blog/2018/02/10/an-opinionated-guide-to-haskell-in-2018/) (background for the effect-system skills).

**Gabriella Gonzalez — [haskellforall.com](https://haskellforall.com/)** (the full post index triaged; about sixty relevant posts read; posts on Nix, Dhall releases, community, and hiring are out of scope). Used:

- Effects and interpreters: [*Purify code using free monads*](https://haskellforall.com/2012/07/purify-code-using-free-monads) (2012) · [*Free monad transformers*](https://haskellforall.com/2012/07/free-monad-transformers) (2012) · [*Algebraic side effects*](https://haskellforall.com/2015/03/algebraic-side-effects) (2015) · [*The Continuation Monad*](https://haskellforall.com/2012/12/the-continuation-monad) (2012) · [*How the continuation monad works*](https://haskellforall.com/2014/04/how-continuation-monad-works) (2014) · [*Breaking from a loop*](https://haskellforall.com/2012/07/breaking-from-loop) (2012)
- Composition and algebra: [*The category design pattern*](https://haskellforall.com/2012/08/the-category-design-pattern) (2012) · [*The functor design pattern*](https://haskellforall.com/2012/09/the-functor-design-pattern) (2012) · [*Scalable program architectures*](https://haskellforall.com/2014/04/scalable-program-architectures) (2014) · [*Model-view-controller, Haskell-style*](https://haskellforall.com/2014/04/model-view-controller-haskell-style) (2014) · [*Mathematical APIs*](https://haskellforall.com/2015/04/mathematical-apis) (2015) · [*Equational reasoning*](https://haskellforall.com/2013/12/equational-reasoning) (2013) · [*Equational reasoning at scale*](https://haskellforall.com/2014/07/equational-reasoning-at-scale) (2014) · [*The wizard monoid*](https://haskellforall.com/2018/02/the-wizard-monoid) (2018) · [*Electoral vote distributions are Monoids*](https://haskellforall.com/2016/10/electoral-vote-distributions-are-monoids) (2016) · [*Optics are monoids*](https://haskellforall.com/2021/09/optics-are-monoids) (2021) · [*Composable streaming folds*](https://haskellforall.com/2013/08/composable-streaming-folds) (2013) · [*From mathematics to map-reduce*](https://haskellforall.com/2016/02/from-mathematics-to-map-reduce) (2016) · [*Applicatives should usually implement Semigroup and Monoid*](https://haskellforall.com/2022/03/applicatives-should-usually-implement) (2022) · [*What does "isomorphic" mean (in Haskell)?*](https://haskellforall.com/2022/10/what-does-isomorphic-mean-in-haskell) (2022) · [*Spreadsheet-like programming in Haskell*](https://haskellforall.com/2014/06/spreadsheet-like-programming-in-haskell) (2014) · [*You could have invented comonads*](https://haskellforall.com/2013/02/you-could-have-invented-comonads) (2013) · [*The Curry-Howard correspondence between programs and proofs*](https://haskellforall.com/2017/02/the-curry-howard-correspondence-between) (2017)
- Values, data, and modules: [*Data is Code*](https://haskellforall.com/2016/04/data-is-code) (2016) · [*The visitor pattern is essentially the same thing as Church encoding*](https://haskellforall.com/2021/01/the-visitor-pattern-is-essentially-same) (2021) · [*Scrap your type classes*](https://haskellforall.com/2012/05/scrap-your-type-classes) (2012) · [*First-class modules without defaults*](https://haskellforall.com/2012/07/first-class-modules-without-defaults) (2012) · [*Generate web forms from pure functions*](https://haskellforall.com/2022/05/generate-web-forms-from-pure-functions) (2022) · [*Module organization guidelines for Haskell projects*](https://haskellforall.com/2021/05/module-organization-guidelines-for) (2021) · [*Explicit is better than implicit*](https://haskellforall.com/2015/10/explicit-is-better-than-implicit) (2015) · [*total-1.0.0: Exhaustive pattern matching using traversals, prisms, and lenses*](https://haskellforall.com/2015/01/total-100-exhaustive-pattern-matching) (2015) · [*Ergonomic newtypes for Haskell strings and numbers*](https://haskellforall.com/2023/04/ergonomic-newtypes-for-haskell-strings) (2023)
- Types, errors, and language design: [*Worst practices should be hard*](https://haskellforall.com/2016/04/worst-practices-should-be-hard) (2016) · [*Worst practices are viral for the wrong reasons*](https://haskellforall.com/2014/04/worst-practices-are-viral-for-wrong) (2014) · [*Sometimes less is more in language design*](https://haskellforall.com/2013/08/sometimes-less-is-more-in-language) (2013) · [*Statements vs Expressions*](https://haskellforall.com/2013/07/statements-vs-expressions) (2013) · [*Dynamic type errors lack relevance*](https://haskellforall.com/2021/01/dynamic-type-errors-lack-relevance) (2021) · [*The trick to avoid deeply-nested error-handling code*](https://haskellforall.com/2021/05/the-trick-to-avoid-deeply-nested-error) (2021) · [*errors-1.0: Simplified error handling*](https://haskellforall.com/2012/07/errors-10-simplified-error-handling) (2012) · [*Prefer to use fail for IO exceptions*](https://haskellforall.com/2019/12/prefer-to-use-fail-for-io-exceptions) (2019) · [*Why I prefer functional programming*](https://haskellforall.com/2020/10/why-i-prefer-functional-programming) (2020)
- Architecture and practice: [*The CAP theorem for software engineering*](https://haskellforall.com/2019/06/the-cap-theorem-for-software-engineering) (2019) · [*The golden rule of software quality*](https://haskellforall.com/2020/07/the-golden-rule-of-software-quality) (2020) · [*The siren song of domain-specific languages*](https://haskellforall.com/2024/02/the-siren-song-of-domain-specific) (2024) · [*Why do our programs need to read input and write output?*](https://haskellforall.com/2017/10/why-do-our-programs-need-to-read-input) (2017) · [*A sufficiently detailed spec is code*](https://haskellforall.com/2026/03/a-sufficiently-detailed-spec-is-code) (2026) · [*Modeling PlusCal in Haskell using Cartesian products of NFAs*](https://haskellforall.com/2022/03/modeling-pluscal-in-haskell-using) (2022) · [*Test stream programming using Haskell's QuickCheck*](https://haskellforall.com/2013/11/test-stream-programming-using-haskells) (2013)

### Further reading cited by the sources or by the skills (not in the provided list)

Yaron Minsky, [*Effective ML Revisited*](https://blog.janestreet.com/effective-ml-revisited/) (Jane Street) · Richard Feldman, *Making Impossible States Impossible* (elm-conf 2016) · Matt Parsons, *Type Safety Back and Forth* (2017) · Matt Noonan, *Ghosts of Departed Proofs* (2018) · Momot, Bratus, Hallberg & Patterson, *The Seven Turrets of Babel: A Taxonomy of LangSec Errors and How to Expunge Them* (2016) · Robert Harper, *Boolean Blindness* (2011) · Conor McBride, *How to Keep Your Neighbours in Order* (2014) and *The Derivative of a Regular Type is its Type of One-Hole Contexts* (2001) · Koen Claessen & John Hughes, *QuickCheck* (2000) · Gérard Huet, *The Zipper* (JFP 1997) · Wouter Swierstra, *Data types à la carte* (JFP 2008) · Shayan Najd & Simon Peyton Jones, *Trees that Grow* (J.UCS 2017) · Bruno Oliveira & William Cook, *Extensibility for the Masses* (ECOOP 2012) · Philip Wadler, *The Expression Problem* (1998) · Conal Elliott, *Denotational design with type class morphisms* (2009) · Sandy Maguire, *Algebra-Driven Design* (Leanpub) · Gary Bernhardt, *Functional Core, Imperative Shell* (Destroy All Software, 2012) · Alistair Cockburn, *Hexagonal Architecture* (2005) · Eric Evans, *Domain-Driven Design* (2003) · David Parnas, *On the Criteria To Be Used in Decomposing Systems into Modules* (1972) · Michael Snoyman, *ReaderT design pattern* (2017) · Alexis King, *Effects for Less* (talk, 2020) · Freckle Engineering, *Tagged is not a Newtype* (2020).
