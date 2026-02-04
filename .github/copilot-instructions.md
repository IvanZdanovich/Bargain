## Purpose

Short, actionable instructions for Copilot or code generation agents to produce code that follows repository rules:
TypedDict for data shapes, Callable aliases for pluggable behavior, and small typed functional pipelines.

---

## Rules
- **Do not generate documentation unless explicitly requested.**
- **Prefer functions over classes** unless a dataclass is needed for clarity.
- **Emit TypedDicts for shared data shapes** and name them with `Data`, `DTO`, or `Record`.
- **Emit Callable type aliases** for pluggable behavior and name them with `Fn` or `Handler`.
- **Compose pipelines from small functions** that accept and return TypedDicts or simple typed values.
- **Do not introduce global mutable state.** Pass dependencies explicitly into functions.
- **Add a parse function for each external input** that returns a TypedDict. Use pydantic only in the parser and convert
  to TypedDict.
- **Include docstrings** that state input and output types and side effects.
- **Add a minimal unit test** for each generated function showing expected types and a simple behavior example.
- **Follow naming conventions** from the repository naming rules.
- **Keep generated code minimal and explicit**; avoid metaprogramming and runtime type hacks.

---

## CI Hints

- **Add mypy config** with strict rules and include `types.py` in the typed package.
- **Add a pre-commit hook** to run `ruff` and `mypy` locally before commits.

---

## Tone and Style for Generated Code

- Clear and explicit over clever and compact.
- Prefer readability: short functions, clear names, and one responsibility per function.
- Include short examples in docstrings showing how to call the function.

---

## Quick Checklist for Pull Requests

- [ ] Types defined in `types.py`
- [ ] Parsers for external inputs included
- [ ] Pipeline wiring uses dependency injection
- [ ] No global mutable state introduced
- [ ] Unit tests added for new functions
- [ ] `mypy` passes locally with `--strict`
- [ ] Docstrings include input/output types and side effects
