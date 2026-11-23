# Grin Interpreter

An interpreter for **Grin**, a small BASIC-like language with line labels, variables, arithmetic, console I/O, and `GOTO` / `GOSUB` / `RETURN` control flow.

> Course project — ICS 33 (Intermediate Programming), UC Irvine, Winter 2026.
> The project specification, lexer, parser, and token/location modules were provided as starter code by the course (Prof. Alex Thornton). **My work is the runtime and the interpreter**, plus their unit tests.

## What I built

| Module | What it does |
|---|---|
| `grin/runtime.py` | Program state: variable storage, the program counter, and a **return-address stack** for `GOSUB` / `RETURN` |
| `grin/interpreting.py` | Turns parsed statements into executable objects and runs them (~600 lines) |
| `tests/grin/test_interpreting.py`, `tests/grin/test_runtime.py` | 27 unit tests for the two modules above |

### Design
- **Polymorphic statement hierarchy.** Every statement is a `Statement` subclass with an `execute(state)` method: `LET`, `PRINT`, `INNUM`, `INSTR`, `ADD` / `SUB` / `MULT` / `DIV`, `GOTO`, `GOSUB`, `RETURN`, `END`.
- **Shared arithmetic base class.** `ADD`, `SUB`, `MULT` and `DIV` inherit from one `BinaryVariableStatement` and only override the operation, so type checking (int / float / string) lives in one place.
- **Jumps by label or relative offset**, optionally guarded by a condition (`GOTO 2 IF A < B`), all handled by a single `JumpStatement` base class.
- **Runtime errors** (bad jump targets, type mismatches, division by zero) are raised as `GrinRuntimeError` and reported with the offending line.

## Example

```
LET A 1
LET B 5
PRINT A
ADD A 1
GOTO -2 IF A <= B
END
.
```

## Running

```bash
python project3.py          # type a Grin program, end it with a line containing only "."
python -m unittest tests/grin/test_*.py   # 74 tests, all passing
```

Requires Python 3.10+.
