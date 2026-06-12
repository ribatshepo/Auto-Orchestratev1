# Engineering Standards Protocol — ENG-STD-001 (Pipeline Baseline)

These standards are **baked into the Auto-Orchestrate pipeline**. Every code-producing agent (software-engineer, infra-engineer, ml-engineer, data-engineer, qa-engineer, security-engineer, sre) MUST apply them to every unit shipped. They are enforced at:

- **Stage 2** (TASK-CREATION-REASONING-001) — task-spec reasoning gate sub-questions reference ENG-STD-001-§N rules
- **Stage 3** (implementation) — software-engineer reads this file as a mandatory preamble before writing code
- **Stage 4.5** (codebase-stats + refactor-analyzer) — detect §5, §8, §9, §10 violations
- **Stage 5** (validator) — emits per-section ENG-STD-001 compliance score; `overall_score < 0.9` fails the recommended_verdict

The standards are **immutable from the task argument's perspective**. User task arguments MAY ADD stricter rules on top of this baseline (via Phase 10's quality-directive pass-through). They CANNOT loosen the baseline. If a task argument contradicts a baseline rule, the baseline wins and the conflict is logged as:

```
[ENG-STD-001] task argument attempted to loosen <rule>; baseline applied.
```

---

## ENG-STD-001-§1 — Design Principles & Default Patterns

- **SOLID principles are the governing design philosophy.** All code must adhere to the Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion principles. No exceptions.
- **Factory Pattern is the default creational pattern.** Object creation must be encapsulated behind factory methods or abstract factories. Direct instantiation of complex objects or service dependencies outside of factory/DI wiring is forbidden.
- **Dependency Injection is the default structural pattern.** All services are wired through a DI container or explicit constructor injection. Factory Pattern takes priority when both creation logic and injection are involved — use factories to produce the instances that DI then wires.
- **Type annotations are imperative.** Every function signature, variable declaration, return type, and class member must carry an explicit type annotation. Inferred types are acceptable only for trivial local assignments where the type is immediately obvious from the right-hand side. Public API boundaries must always have explicit annotations.

---

## ENG-STD-001-§2 — Type Safety

- Enable the strictest type-checking mode available in the language (e.g., strict mode, nullable analysis, type-checked generics). Treat type warnings as errors.
- No use of loosely typed constructs (`any`, `object`, `dynamic`, untyped dictionaries/maps) for structured data. Define an explicit type.
- All public API boundaries (service interfaces, DTOs, configuration models) must use strongly typed structures (records, classes, interfaces, structs, or typed schemas). No anonymous or untyped objects crossing method boundaries.
- Any function or constructor that accepts more than two arguments must receive a single **typed data class** (or equivalent named, strongly typed structure) instead of positional parameters. The data class must carry full type annotations on every field.
- Parse and validate external input at the system boundary and pass validated types inward. Inner layers never receive raw strings for structured data.
- All type annotations must be explicit at public API boundaries. Inferred types are acceptable only for trivial local assignments where the type is immediately clear.

---

## ENG-STD-001-§3 — Error Handling

- Define a result type (`Result<T>`, `Either`, or language equivalent) for operations that can fail in expected ways. Do not use exceptions or panics for control flow.
- Exceptions/panics are reserved for genuinely unexpected failures (bugs, infrastructure down). Catch them at the outermost layer (middleware, entry point), not inside business logic.
- Every error handler must either log and re-raise, wrap in a domain-specific error, or convert to a result failure. Silent or empty error handlers are forbidden.
- External network calls must use resilience patterns (retry, circuit breaker, timeout, bulkhead) via an appropriate library. Never make a raw unprotected network call.
- All error responses exposed to consumers must follow a structured error format (e.g., RFC 9457 Problem Details or an equivalent typed error envelope). Define a shared error factory.

---

## ENG-STD-001-§4 — Naming Consistency

- Follow the established naming conventions for the language exactly. Document the convention once and enforce it with a linter.
- Use clear, descriptive names that reflect purpose. No generic suffixes like `Impl`, `Manager`, or `Helper` unless they convey real meaning.
- Asynchronous functions must be clearly distinguishable from synchronous ones, whether by naming convention, return type, or language-specific markers (e.g., `async` keyword, `Async` suffix, `Promise` return type).
- Configuration models use a consistent suffix (e.g., `Options`, `Config`, `Settings`). Bind them via the language's configuration system.
- Factory classes use the suffix **Factory** (e.g., `UserServiceFactory`, `ConnectionFactory`). The factory's return type must be explicitly annotated.
- Name files to match the primary public type they contain. One public type per file.

---

## ENG-STD-001-§5 — Dead Code Management

- No commented-out code in any committed file. Use version control history instead.
- No unused imports, parameters, variables, or private functions. Treat all related warnings as errors.
- No `TODO` / `FIXME` / `HACK` comments without a linked issue or task ID. If it cannot be done now, create a tracked issue and reference it.
- Remove feature scaffolding from prior iterations if it has been superseded. Do not leave vestigial types or modules.

---

## ENG-STD-001-§6 — Async & Concurrency Patterns

- All I/O operations (cache, HTTP, database, file system) must be asynchronous end-to-end. No blocking on async results from synchronous contexts.
- Pass cancellation/context signals through the entire async call chain so that work can be aborted cooperatively.
- Use the most efficient async primitive available for the common case (e.g., value-type futures for frequently synchronous paths, lazy streams for incremental results).
- Use typed streaming abstractions (async iterators, reactive streams, channels) for incremental data flows. No unbounded in-memory queues.
- For producer-consumer pipelines, use bounded, typed channel or queue abstractions with explicit back-pressure.

---

## ENG-STD-001-§7 — Linting and Static Analysis

- Treat all warnings as errors in CI. Non-conforming code must not merge.
- Maintain a shared linter/formatter configuration file (e.g., `.editorconfig`, `.eslintrc`, `rustfmt.toml`, `.clang-format`) enforcing these standards.
- Run the formatter and linter as a CI gate. Automated formatting is not optional.
- Enable the language's recommended set of static analyzers at their strictest useful level.

---

## ENG-STD-001-§8 — Forbidden Patterns

- **No god classes or god methods.** No type exceeding ~300 lines. No function exceeding ~40 lines. If either limit is hit, decompose.
- **No feature flag sprawl.** Feature variation by deployment tier is handled through dependency wiring (register different implementations per tier), not runtime conditional checks scattered through code. Define a clear tier-aware service registration module and keep tier logic there.
- **No tech debt by default.** Do not introduce a shortcut with a promise to fix later. If a proper implementation is too complex for the current step, define the interface/contract now and implement it in the correct future iteration.
- **No environment variable sprawl.** All configuration is bound to strongly typed config objects via the language's configuration system. No direct environment variable reads scattered through code. Configuration shape is defined once and validated at startup.
- **No security violations.** No secrets in code, config files, or logs. No query string concatenation. No unsanitized user input reaching prompts, queries, or shell commands. Use parameterized queries, input validation types, and template composition — never string interpolation with user content.
- **No direct instantiation of dependencies.** Services must be created via factories and wired via DI. Calling `new SomeService(...)` directly in business logic is forbidden; use the registered factory or let the DI container resolve the dependency.
- **No untyped function signatures.** Every function must have explicit type annotations on all parameters and return types. Functions with implicit or missing type annotations must not pass code review.

---

## ENG-STD-001-§9 — Dependency Injection & Service Wiring

- All services are wired through a DI container or explicit dependency passing (constructor injection, function parameters). No hidden instantiation of services with dependencies.
- Register or scope services with the narrowest possible lifetime: transient/per-call for stateless utilities, per-request for request-scoped work, singleton only for truly shared thread-safe state.
- Tier-specific behaviour is wired at registration/startup time. Create a module or factory per subsystem that selects the correct implementation for the deployment tier.
- Use factory classes or factory methods to encapsulate complex construction logic. The DI container should resolve dependencies; the factory should handle conditional creation, configuration-driven variants, and multi-step initialisation.
- When both a factory and DI are involved, the factory produces the instance and DI manages its lifetime and injection. The factory is itself registered in the DI container so it can receive its own dependencies.

---

## ENG-STD-001-§10 — Data Classes & Argument Objects

- Any function, method, or constructor that accepts more than two parameters must define a dedicated data class (or record/struct/named tuple equivalent) to serve as its single argument.
- Data classes must be immutable by default. Use read-only fields or frozen structures. Mutable state requires explicit justification.
- Every field in a data class must carry an explicit type annotation. Default values are encouraged for optional fields.
- Data classes used at API boundaries must include validation logic (via constructors, factory methods, or validation decorators) to enforce invariants at creation time.
- Name data classes to reflect their purpose (e.g., `CreateUserRequest`, `ConnectionOptions`, `ReportFilterCriteria`). Do not use generic names like `Params` or `Args`.

---

## Enforcement Map

| Stage | Mechanism | Sections Enforced |
|---|---|---|
| Stage 2 reasoning gate (TASK-CREATION-REASONING-001) | Sub-questions reference ENG-STD-001-§N IDs | §1, §2, §3, §7, §8, §9, §10 |
| Stage 3 (software-engineer) | Mandatory preamble read of this file before writing code | All §1–§10 |
| Stage 4.5 (codebase-stats + refactor-analyzer) | Detection rules in scripts/ | §5, §8, §9, §10 |
| Stage 5 (validator) | Per-section compliance score; `overall_score < 0.9` fails recommended_verdict | All §1–§10 |

## Cross-references

- `_shared/protocols/agent-preamble.md` — PREAMBLE-001..004 (read continuity-brief.md first; ENG-STD-001 is read alongside it for code-producing agents)
- `skills/production-code-workflow/SKILL.md` — implements §1, §2, §3, §5, §8, §9, §10 patterns
- `skills/validator/SKILL.md` — emits the per-section compliance score
- `skills/test-writer-pytest/SKILL.md` — implements the Testing Contract referenced by §7
- `commands/auto-orchestrate.md` — ENG-STD-001 constraint row + Stage 2 sub-question references
