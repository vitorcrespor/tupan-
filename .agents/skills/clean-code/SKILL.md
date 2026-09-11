---
name: clean-code
description: Refactors legacy code for readability and maintainability while preserving its observable behavior. Use when the user asks to clean up, untangle, or reduce technical debt in existing code; when a refactor must not break current behavior or callers; or when refactoring an externally consumed API that needs a preserve-v1 versus add-v2 decision.
---


# Clean Code

Refactor legacy code so that a future maintainer can understand and change it with less risk. Preserve observable behavior unless the user explicitly approves a behavior change.

## Operating priorities

Apply these priorities in order:

1. Preserve behavior with evidence.
2. Use precise, domain-oriented names.
3. Keep related logic easy to read in one place.
4. Reduce branching, duplication, hidden state, and change coupling.
5. Introduce abstractions only when they remove demonstrated complexity.
6. Prefer a focused diff over a broad rewrite.

Do not optimize for the number of methods, classes, files, patterns, or lines. Excessive extraction can make code harder to understand by forcing readers to jump between files.

## Non-negotiable rules

- Do not change production behavior before retained characterization tests pass against the unchanged legacy code.
- Keep the characterization tests as permanent legacy regression tests. Do not delete or weaken them after the refactor.
- Do not combine a refactor with a bug fix, feature change, dependency upgrade, or unrelated formatting pass.
- If the target is an API and the versioning strategy is unresolved, complete the characterization-test gate and then ask the API versioning question before implementation.
- Work in small, reversible batches. Run the narrowest relevant tests after every batch.
- Preserve surprising behavior as legacy behavior unless the user explicitly authorizes changing it.
- Never hide pre-existing failures, skip tests, relax assertions, or claim a green suite that was not run successfully.
- Respect repository-local instructions, architecture, naming conventions, and user changes already present in the working tree.

## Workflow

### 1. Establish the refactoring boundary

Before editing:

1. Read repository instructions and nearby documentation, including files such as `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, ADRs, and module READMEs when present.
2. Inspect the working tree. Do not overwrite or reformat unrelated user changes.
3. Discover the repository's test, lint, type-check, build, and integration commands from configuration and CI files rather than guessing.
4. Trace the complete call path through the requested code, its callers, consumers, state changes, and external effects.
5. Identify the observable seam through which behavior can be tested.
6. Determine whether the target is an API: HTTP/RPC/GraphQL endpoints, a published library or SDK, a public CLI, an event/message contract, or another externally consumed interface.
7. Run the existing relevant tests and, when practical, the full suite. Record all pre-existing failures exactly.
8. State the intended scope and the behavior that must remain unchanged.

Completion criteria:

- The target, callers, consumers, observable behavior, verification commands, and baseline state are known.
- No production code has been changed.

### 2. Lock current behavior with retained characterization tests

Read [references/characterization-tests.md](../../references/characterization-tests.md), then add tests that describe what the legacy code actually does today.

Requirements:

1. Test through the most stable observable seam available. Prefer a public function, service boundary, endpoint, command, event, or persisted effect over private methods.
2. Add coverage for the main path, important boundaries, error behavior, output shape, and meaningful side effects.
3. Capture legacy quirks explicitly when consumers may depend on them. Label them as legacy behavior; do not silently correct them.
4. Make the tests deterministic. Control time, randomness, environment, network, filesystem, and concurrency only as needed.
5. Follow repository conventions while making the tests easy to retain and recognize. Prefer a `legacy` or `characterization` suite, directory, tag, or filename where the test framework permits it.
6. Run the new tests against the unchanged production code. They must pass before refactoring begins.
7. Confirm the production diff is still empty after this step, apart from test fixtures or test-only support.

Do not write assertions that merely repeat the implementation. Assert externally observable results and effects.

If unrelated tests already fail, preserve the exact baseline and require the newly added characterization suite to pass. Do not misrepresent the entire repository as green.

Completion criteria:

- Retained characterization tests pass on the unchanged legacy implementation.
- The tests cover the behavior at risk from the planned refactor.
- Production code remains unchanged.

### 3. Apply the API versioning gate

Perform this step only when the target is an API and the user has not already selected a versioning strategy.

Ask exactly one decision question:

> I found an externally consumed API. Should I **(A)** refactor its internals while preserving the existing v1 contract, or **(B)** leave the v1 production implementation untouched and add a side-by-side v2 implementation? I recommend **[A or B]** because **[one concrete repository-specific reason]**.

Stop before implementation until the user answers. Do not repeat the question if the user already gave a clear choice.

Then follow [references/api-versioning.md](../../references/api-versioning.md):

- **A — preserve v1 in place:** refactor internals only; contract tests must prove the v1 interface and behavior remain compatible.
- **B — add v2 beside v1:** do not edit v1 production code; add a separate v2 entry point and implementation using the repository's existing versioning mechanism. Tests and documentation may be added around v1 without changing it.

Completion criteria:

- The API strategy is explicit and recorded before production changes.

### 4. Design the smallest useful refactor

Read [references/refactoring-heuristics.md](../../references/refactoring-heuristics.md) before filling in the change plan below.

Create a concise change plan. For each proposed edit, record:

| Observed friction | Evidence in the code | Smallest transformation | Protecting test | Navigation impact |
|---|---|---|---|---|

Plan in this order:

1. Improve misleading or vague names using the domain language already present in requirements, tests, and neighboring code.
2. Simplify local control flow with guard clauses, clearer conditions, explicit intermediate values, and removal of dead branches.
3. Remove proven duplication and unnecessary indirection.
4. Move behavior toward the data or concept it naturally belongs to when this improves cohesion.
5. Extract a method, class, module, or pattern only when the extraction has a precise name and reduces demonstrated complexity or change coupling.

Every new abstraction must answer:

- What concrete problem does this solve now?
- Which likely change becomes localized?
- Does the reader gain more than the navigation cost introduced?
- Can the same result be achieved with a rename, deletion, or small local rewrite?

If those answers are weak, do not introduce the abstraction.

Completion criteria:

- Every planned change is behavior-preserving, test-protected, and justified by observed friction.

### 5. Implement in small behavior-preserving batches

Use this preferred sequence:

1. Rename for meaning.
2. Clarify variables, conditions, and data flow.
3. Remove dead code and redundant wrappers.
4. Consolidate real duplication.
5. Improve ownership and locality.
6. Extract or move cohesive logic only when earned.
7. Apply a design pattern only when real variation or coupling justifies its added indirection.

For each batch:

1. Make one coherent transformation.
2. Inspect the diff for accidental scope expansion.
3. Run the narrow characterization tests and relevant unit tests.
4. Keep the batch only when behavior remains protected and readability or change cost measurably improves.
5. Revert or correct the latest batch immediately if a previously passing test fails unexpectedly.

Constraints:

- Do not perform a wholesale rewrite unless the user explicitly requests one and the retained tests protect the full contract.
- Add an interface, factory, adapter, base class, configuration option, or extension point only when the variation it serves already exists in the code.
- Do not split cohesive single-use logic across files merely to make functions shorter.
- Do not alter validation, authorization, transactions, error mapping, logging, accessibility, or other trust-boundary behavior as a simplification shortcut.
- Do not add a dependency when the repository, language, or platform already provides a clear solution.
- Under the v2 strategy, keep v1 production files untouched even when sharing code would be convenient, unless the user separately approves modifying v1.

Completion criteria:

- Every file in the production diff appears in the step 4 change plan.
- Relevant tests pass after each batch.
- The result is easier to read locally and easier to change along the identified change axis.

### 6. Verify the completed refactor

Read [references/verification-and-reporting.md](../../references/verification-and-reporting.md) before running the first verification command.

Run all commands applicable to the touched area:

1. Retained legacy characterization tests.
2. Relevant unit, integration, contract, and end-to-end tests.
3. The full test suite when practical.
4. Linting, formatting checks, static analysis, and type checking.
5. Build or packaging commands.
6. Security, performance, concurrency, migration, or compatibility checks when the refactor touches those risks.
7. `git diff --check` or the repository equivalent.

Compare final results with the recorded baseline. There must be no new unexplained failures.

Review the final diff for:

- accidental API or schema changes;
- changed defaults, ordering, error behavior, side effects, serialization, or null handling;
- disabled, weakened, or over-mocked tests;
- unrelated formatting or dependency changes;
- unnecessary files, wrappers, abstractions, comments, or compatibility shims;
- v1 production changes when the selected strategy was side-by-side v2.

Completion criteria:

- Verification evidence is recorded accurately.
- No new regression is known.
- Any command not run is named with the reason.

### 7. Report the result

Use this structure:

```markdown
## Refactor completed

- **Scope:**
- **API strategy:** Not applicable | v1 preserved in place | side-by-side v2
- **Legacy characterization tests retained:**
- **Main readability and change-cost improvements:**
- **Verification commands and results:**
- **Known behavior intentionally preserved:**
- **Unverified risks or pre-existing failures:**
- **Follow-up:** Only work justified by a current requirement
```

Separate verified facts from assumptions. Do not state that behavior is unchanged solely because the code looks equivalent; cite the tests and checks that support the conclusion.
