# Publications — FUNARCH and related

The ACM SIGPLAN Workshop on Functional Software Architecture — FP in the Large (FUNARCH) is the publication venue listed by functional-architecture.org, together with the *Functional Software Architecture* category of the Journal of Functional Programming (category editor: Mike Sperber). Proceedings are in the ACM Digital Library; talk videos are linked from each [event page](https://functional-architecture.org/events/).

Each entry: authors, title (linked), one line on the architectural lesson, and the skills it informs.

## FUNARCH 2023 (Seattle) — [proceedings](https://dl.acm.org/doi/proceedings/10.1145/3609025)

- **Mike Sperber** — *Functional Programming in the Large: Status and Perspective* (opening talk). FP-in-the-large knowledge is mostly folklore; the field needs to talk to the software-architecture community, especially Domain-Driven Design. → `functional-architecture`
- **Stefan Wehr** — [A Software Architecture Based on Coarse-Grained Self-Adjusting Computations](https://dl.acm.org/doi/10.1145/3609025.3609481). A commercial Haskell system built around automatic, efficient recomputation of outputs when inputs change. → `composable-guis`, `algebraic-modelling`
- **Marco Perone, Georgios Karachalias** — [Crème de la Crem: Composable Representable Executable Machines](https://dl.acm.org/doi/10.1145/3609025.3609480). Architectures as compositions of state machines; allowed transitions at the type level; diagrams generated from the implementation. → `architecture-as-code`, `correctness-by-construction`
- **Ben Knoble, Bogdan Popa** — [Functional Shell and Reusable Components for Easy GUIs](https://defn.io/papers/fungui-funarch23.pdf). Functional shells and observables make imperative GUI toolkits composable. → `composable-guis`, `functional-core-imperative-shell`
- **Jeremy Gibbons, Oisín Kidney, Tom Schrijvers, Nicolas Wu** — [Phases in Software Architecture](https://www.cs.ox.ac.uk/publications/publication15860-abstract.html). A multi-phase applicative functor lets computations be specified by location but executed in phases (gather, process, distribute). → `composition-and-closure`, `algebraic-modelling`
- **Jeffrey M. Young, Sylvain Henry, John Ericson** — [Stretching the Glasgow Haskell Compiler: Nourishing GHC with Domain-Driven Design](https://dl.acm.org/doi/10.1145/3609025.3609476). How GHC violates immutability, modularity, and composability, with DDD-based guidance. → `modularization`, `trees-that-grow`
- **Will Crichton** — [Typed Design Patterns for the Functional Era](https://dl.acm.org/doi/10.1145/3609025.3609477). Patterns whose entirety cannot be a library: Witness, State Machine, Parallel Lists, Registry (in Rust). → `correctness-by-construction`, `functional-programming-languages`
- **Ivan Perez** — [Types that Change: The Extensible Type Design Pattern](https://ivanperez.io/#typesthatchange). An ADT extended with a type function applied to every component, for traceability and error recovery across compiler stages. → `trees-that-grow`

## FUNARCH 2024 (Milan) — [proceedings](https://dl.acm.org/doi/proceedings/10.1145/3677998)

- **Marco Sampellegrini** — [Architecting Functional Programs](https://dl.acm.org/doi/10.1145/3677998.3678219) (keynote). Types stop at service boundaries; event sourcing, CQRS, and DDD — and conversations with the business — carry correctness in the large. → `event-sourcing`, `expressive-static-types`
- **Weixi Ma, Arnaud Venet, Junhua Gu, Subbu Subramanian, Siyu Wang, Rocky Liu, Daniel Friedman, Yafei Yang** — [F3: A Compiler For Feature Engineering](https://dl.acm.org/doi/10.1145/3677998.3678220). A DSL and compiler at Meta built on FP and type theory. → `embedded-dsl`
- **Matthew Sottile, Mohit Tekriwal** — [Design and implementation of a verified interpreter for additive manufacturing programs](https://dl.acm.org/doi/10.1145/3677998.3678221). Moving from hand-written OCaml to verified, extracted components; architectural lessons for integrating verified code. → `formal-verification`
- **James Chapman, Arnaud Bailly, Polina Vinogradova** — [Applying Continuous Formal Methods to Cardano](https://dl.acm.org/doi/10.1145/3677998.3678222). Formal methods, functional architecture, and Haskell in a large blockchain. → `formal-verification`
- **Marc Kaufmann, Bogdan Popa** — [Continuations: what have they ever done for us?](https://dl.acm.org/doi/10.1145/3677998.3678223). Delimited continuations for multi-step study flows; persistence, dynamic variables, leaks, and debugging as challenges. → `continuations`
- **Marcus Crestani, Markus Schlegel, Marco Schneider** — [Bidirectional Data Transformations](https://dl.acm.org/doi/10.1145/3677998.3678224). Optics (lenses, projections) to declare conversions between representations once. → `bidirectional-data-transformations`

## FUNARCH 2025 (Singapore) — [proceedings](https://dl.acm.org/doi/proceedings/10.1145/3759163)

- **Jacco Krijnen, Wouter Swierstra, Gabriele Keller, Manuel Chakravarty, Joris Dral** — [A Layered Certifying Compiler Architecture](https://dl.acm.org/doi/10.1145/3759163.3760427). Translation validation by a layered certifier developed independently of the Plutus compiler; Rocq extraction integrates it. → `formal-verification`, `belt-and-suspenders`
- **Michael Sperber, Markus Schlegel** — [Evolution of Functional UI Paradigms](https://dl.acm.org/doi/10.1145/3759163.3760429). From stream-based and monadic toolkits to Model-View-Update; less coupling, but modularity remains a challenge. → `composable-guis`
- **Michael Sperber** — [Six Years of FUNAR: Functional Training for Software Architects](https://dl.acm.org/doi/10.1145/3759163.3760428). Teaching the iSAQB functional-architecture curriculum to audiences without FP background. → `functional-programming-languages`
- **Tom Ellis** — *Bluefin in Industry* (lightning talk). Replacing transformers/mtl with the Bluefin effect system in Groq's assembly tooling. → `algebraic-effect-systems`
- **Jeffrey Young** — *What Could Functional Architecture Mean* and *The Future of FUNARCH* (lightning talks). → `functional-architecture`

## FUNARCH 2026 — [event page](https://functional-architecture.org/events/funarch-2026/) (proceedings links upstream TODO)

- **Richard Feldman** — *Functional Mechanical Sympathy*. Performance of functional programs is largely architectural; architect with the machine in mind. → `functional-programming-languages`
- **Seungheon Oh, Ziyang Liu, Philip Wadler** — *From Lambda to Ledger: An Architectural Comparison of Plinth and Plutarch*. Compiling a Haskell subset via GHC vs explicitly constructed typed terms embedded in Haskell. → `embedded-dsl`
- **Michael Sperber** — experience report on *Lokalisierung* (listed on the page under the title "Evolution of Functional UI Paradigms"; the abstract describes a 10-year event-based, peer-to-peer configuration system). → `event-sourcing`
- **Leon Heuer, Falk Woldmann Lu, Jan Haase** — *Functional State Machines in Rust: Typestate and Newtype Patterns*. Typestate improves faultlessness and testability at a boilerplate cost; newtype + parse-don't-validate is cheap and effective. → `correctness-by-construction`, `parse-dont-validate`, `names-are-not-type-safety`
