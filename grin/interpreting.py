# interpreting.py
#
# ICS 33 Winter 2026
# Project 3: Why Not Smile?
#
# Implements the execution phase of a Grin interpreter.

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from dataclasses import dataclass
import re

from grin.parsing import parse
from grin.runtime import GrinRuntimeError, GrinValue, ProgramState
from grin.token import GrinToken, GrinTokenKind


_INNUM_INTEGER_PATTERN = re.compile(r'-?\d+')
_INNUM_FLOAT_PATTERN = re.compile(r'-?\d+\.\d*')


def _is_int(value: object) -> bool:
    return type(value) is int


def _is_float(value: object) -> bool:
    return type(value) is float


def _is_string(value: object) -> bool:
    return isinstance(value, str)


def _is_number(value: object) -> bool:
    return _is_int(value) or _is_float(value)


class ValueSource(ABC):
    """Something that can produce a Grin value at runtime."""

    @abstractmethod
    def resolve(self, state: ProgramState) -> GrinValue:
        raise NotImplementedError


@dataclass(frozen = True)
class LiteralSource(ValueSource):
    value: GrinValue


    def resolve(self, state: ProgramState) -> GrinValue:
        return self.value


@dataclass(frozen = True)
class VariableSource(ValueSource):
    name: str


    def resolve(self, state: ProgramState) -> GrinValue:
        return state.variable_value(self.name)


@dataclass(frozen = True)
class Condition:
    left: ValueSource
    operator: GrinTokenKind
    right: ValueSource


    def evaluate(self, state: ProgramState, line_number: int) -> bool:
        left_value = self.left.resolve(state)
        right_value = self.right.resolve(state)
        return _evaluate_comparison(
            self.operator, left_value, right_value, line_number)


class Statement(ABC):
    """Base class for executable Grin statements."""

    def __init__(self, line_number: int):
        self._line_number = line_number


    def line_number(self) -> int:
        return self._line_number


    @abstractmethod
    def execute(self, state: ProgramState) -> None:
        raise NotImplementedError


class LetStatement(Statement):
    def __init__(self, line_number: int, target_name: str, source: ValueSource):
        super().__init__(line_number)
        self._target_name = target_name
        self._source = source


    def execute(self, state: ProgramState) -> None:
        state.set_variable_value(self._target_name, self._source.resolve(state))
        state.advance()


class PrintStatement(Statement):
    def __init__(self, line_number: int, source: ValueSource):
        super().__init__(line_number)
        self._source = source


    def execute(self, state: ProgramState) -> None:
        state.write_output(self._source.resolve(state))
        state.advance()


class InnumStatement(Statement):
    def __init__(self, line_number: int, target_name: str):
        super().__init__(line_number)
        self._target_name = target_name


    def execute(self, state: ProgramState) -> None:
        raw = state.read_input(self.line_number())
        value = _parse_innum_value(raw, self.line_number())
        state.set_variable_value(self._target_name, value)
        state.advance()


class InstrStatement(Statement):
    def __init__(self, line_number: int, target_name: str):
        super().__init__(line_number)
        self._target_name = target_name


    def execute(self, state: ProgramState) -> None:
        raw = state.read_input(self.line_number())
        state.set_variable_value(self._target_name, raw)
        state.advance()


class BinaryVariableStatement(Statement, ABC):
    """Shared behavior for ADD/SUB/MULT/DIV."""

    def __init__(self, line_number: int, target_name: str, source: ValueSource):
        super().__init__(line_number)
        self._target_name = target_name
        self._source = source


    @abstractmethod
    def _apply(self, left: GrinValue, right: GrinValue) -> GrinValue:
        raise NotImplementedError


    def execute(self, state: ProgramState) -> None:
        left = state.variable_value(self._target_name)
        right = self._source.resolve(state)
        result = self._apply(left, right)
        state.set_variable_value(self._target_name, result)
        state.advance()


class AddStatement(BinaryVariableStatement):
    def _apply(self, left: GrinValue, right: GrinValue) -> GrinValue:
        return _add(left, right, self.line_number())


class SubStatement(BinaryVariableStatement):
    def _apply(self, left: GrinValue, right: GrinValue) -> GrinValue:
        return _sub(left, right, self.line_number())


class MultStatement(BinaryVariableStatement):
    def _apply(self, left: GrinValue, right: GrinValue) -> GrinValue:
        return _mult(left, right, self.line_number())


class DivStatement(BinaryVariableStatement):
    def _apply(self, left: GrinValue, right: GrinValue) -> GrinValue:
        return _div(left, right, self.line_number())


class JumpStatement(Statement, ABC):
    """Shared behavior for GOTO and GOSUB."""

    def __init__(
            self, line_number: int, target: ValueSource,
            condition: Condition | None):
        super().__init__(line_number)
        self._target = target
        self._condition = condition


    @abstractmethod
    def _can_jump_to_end_marker(self) -> bool:
        raise NotImplementedError


    @abstractmethod
    def _allow_jump_to_same_line(self) -> bool:
        raise NotImplementedError


    @abstractmethod
    def _perform_jump(self, state: ProgramState, destination_line: int) -> None:
        raise NotImplementedError


    def _should_jump(self, state: ProgramState) -> bool:
        if self._condition is None:
            return True

        return self._condition.evaluate(state, self.line_number())


    def _resolve_destination_line(self, state: ProgramState) -> int:
        target_value = self._target.resolve(state)

        if _is_int(target_value):
            destination_line = self.line_number() + target_value

            if target_value == 0:
                raise GrinRuntimeError(
                    f'Line {self.line_number()}: Cannot jump to the same line')

            min_allowed = 1
            max_allowed = state.statement_count() + (
                1 if self._can_jump_to_end_marker() else 0)

            if destination_line < min_allowed or destination_line > max_allowed:
                raise GrinRuntimeError(
                    f'Line {self.line_number()}: Jump target is out of bounds')

            if destination_line == self.line_number() and not self._allow_jump_to_same_line():
                raise GrinRuntimeError(
                    f'Line {self.line_number()}: Cannot jump to the same line')

            return destination_line

        if _is_string(target_value):
            destination_line = state.label_line(target_value, self.line_number())

            if destination_line == self.line_number() and not self._allow_jump_to_same_line():
                raise GrinRuntimeError(
                    f'Line {self.line_number()}: Cannot jump to the same line')

            return destination_line

        raise GrinRuntimeError(
            f'Line {self.line_number()}: Jump target must be an integer or string')


    def execute(self, state: ProgramState) -> None:
        if not self._should_jump(state):
            state.advance()
            return

        destination_line = self._resolve_destination_line(state)
        self._perform_jump(state, destination_line)


class GotoStatement(JumpStatement):
    def _can_jump_to_end_marker(self) -> bool:
        return True


    def _allow_jump_to_same_line(self) -> bool:
        return True


    def _perform_jump(self, state: ProgramState, destination_line: int) -> None:
        state.jump_to(destination_line)


class GosubStatement(JumpStatement):
    def _can_jump_to_end_marker(self) -> bool:
        return False


    def _allow_jump_to_same_line(self) -> bool:
        return False


    def _perform_jump(self, state: ProgramState, destination_line: int) -> None:
        state.push_return_line(self.line_number() + 1)
        state.jump_to(destination_line)


class ReturnStatement(Statement):
    def execute(self, state: ProgramState) -> None:
        return_line = state.pop_return_line(self.line_number())
        state.jump_to(return_line)


class EndStatement(Statement):
    def execute(self, state: ProgramState) -> None:
        state.end_program()


@dataclass(frozen = True)
class Program:
    statements: tuple[Statement, ...]
    labels: dict[str, int]


    def statement_at_line(self, line_number: int) -> Statement:
        return self.statements[line_number - 1]


def read_program_lines(input_reader: Callable[[], str]) -> list[str]:
    """Reads source lines until the line containing only '.'."""
    lines: list[str] = []

    while True:
        try:
            line = input_reader()
        except EOFError:
            break

        lines.append(line)

        if line.strip() == '.':
            break

    return lines


def parse_program(lines: Iterable[str]) -> Program:
    return build_program(parse(lines))


def execute_program(
        program: Program, *,
        input_reader: Callable[[], str],
        output_writer: Callable[[str], None]) -> None:
    state = ProgramState(
        statement_count = len(program.statements),
        labels = program.labels,
        input_reader = input_reader,
        output_writer = output_writer)

    while state.has_statement_to_execute():
        statement = program.statement_at_line(state.current_line())
        statement.execute(state)


def run_interpreter(
        *,
        input_reader: Callable[[], str] = input,
        output_writer: Callable[[str], None] = print) -> None:
    lines = read_program_lines(input_reader)
    program = parse_program(lines)
    execute_program(
        program,
        input_reader = input_reader,
        output_writer = output_writer)


def build_program(parsed_lines: Iterable[list[GrinToken]]) -> Program:
    statements: list[Statement] = []
    labels: dict[str, int] = {}

    for tokens in parsed_lines:
        label, body_tokens = _split_label(tokens)
        line_number = tokens[0].location().line()

        if label is not None:
            if label in labels:
                raise GrinRuntimeError(
                    f'Line {line_number}: Duplicate label "{label}"')

            labels[label] = line_number

        statements.append(_build_statement(body_tokens, line_number))

    return Program(tuple(statements), labels)


def _split_label(tokens: list[GrinToken]) -> tuple[str | None, list[GrinToken]]:
    if len(tokens) >= 2 \
            and tokens[0].kind() == GrinTokenKind.IDENTIFIER \
            and tokens[1].kind() == GrinTokenKind.COLON:
        return tokens[0].value(), tokens[2:]

    return None, tokens


def _build_statement(tokens: list[GrinToken], line_number: int) -> Statement:
    kind = tokens[0].kind()

    if kind == GrinTokenKind.LET:
        return LetStatement(
            line_number, _identifier_name(tokens[1]), _value_source(tokens[2]))
    if kind == GrinTokenKind.PRINT:
        return PrintStatement(line_number, _value_source(tokens[1]))
    if kind == GrinTokenKind.INNUM:
        return InnumStatement(line_number, _identifier_name(tokens[1]))
    if kind == GrinTokenKind.INSTR:
        return InstrStatement(line_number, _identifier_name(tokens[1]))
    if kind == GrinTokenKind.ADD:
        return AddStatement(
            line_number, _identifier_name(tokens[1]), _value_source(tokens[2]))
    if kind == GrinTokenKind.SUB:
        return SubStatement(
            line_number, _identifier_name(tokens[1]), _value_source(tokens[2]))
    if kind == GrinTokenKind.MULT:
        return MultStatement(
            line_number, _identifier_name(tokens[1]), _value_source(tokens[2]))
    if kind == GrinTokenKind.DIV:
        return DivStatement(
            line_number, _identifier_name(tokens[1]), _value_source(tokens[2]))
    if kind == GrinTokenKind.GOTO:
        return GotoStatement(
            line_number, _target_source(tokens[1]), _optional_condition(tokens))
    if kind == GrinTokenKind.GOSUB:
        return GosubStatement(
            line_number, _target_source(tokens[1]), _optional_condition(tokens))
    if kind == GrinTokenKind.RETURN:
        return ReturnStatement(line_number)
    if kind == GrinTokenKind.END:
        return EndStatement(line_number)

    raise GrinRuntimeError(
        f'Line {line_number}: Unsupported statement {kind.name}')


def _optional_condition(tokens: list[GrinToken]) -> Condition | None:
    if len(tokens) == 2:
        return None

    return Condition(
        left = _value_source(tokens[3]),
        operator = tokens[4].kind(),
        right = _value_source(tokens[5]))


def _identifier_name(token: GrinToken) -> str:
    return token.value()


def _value_source(token: GrinToken) -> ValueSource:
    if token.kind() == GrinTokenKind.IDENTIFIER:
        return VariableSource(token.value())

    if token.kind() in (
            GrinTokenKind.LITERAL_INTEGER,
            GrinTokenKind.LITERAL_FLOAT,
            GrinTokenKind.LITERAL_STRING):
        return LiteralSource(token.value())

    raise GrinRuntimeError(
        f'Line {token.location().line()}: Expected a value token')


def _target_source(token: GrinToken) -> ValueSource:
    if token.kind() == GrinTokenKind.IDENTIFIER:
        return VariableSource(token.value())

    if token.kind() in (
            GrinTokenKind.LITERAL_INTEGER,
            GrinTokenKind.LITERAL_STRING):
        return LiteralSource(token.value())

    raise GrinRuntimeError(
        f'Line {token.location().line()}: Expected a jump target token')


def _evaluate_comparison(
        operator: GrinTokenKind,
        left: GrinValue,
        right: GrinValue,
        line_number: int) -> bool:
    left_value, right_value = _normalized_for_comparison(left, right, line_number)

    if operator == GrinTokenKind.EQUAL:
        return left_value == right_value
    if operator == GrinTokenKind.NOT_EQUAL:
        return left_value != right_value
    if operator == GrinTokenKind.LESS_THAN:
        return left_value < right_value
    if operator == GrinTokenKind.LESS_THAN_OR_EQUAL:
        return left_value <= right_value
    if operator == GrinTokenKind.GREATER_THAN:
        return left_value > right_value
    if operator == GrinTokenKind.GREATER_THAN_OR_EQUAL:
        return left_value >= right_value

    raise GrinRuntimeError(
        f'Line {line_number}: Unknown comparison operator')


def _normalized_for_comparison(
        left: GrinValue,
        right: GrinValue,
        line_number: int) -> tuple[int | float | str, int | float | str]:
    if _is_int(left) and _is_int(right):
        return left, right

    if _is_float(left) and _is_float(right):
        return left, right

    if (_is_int(left) and _is_float(right)) \
            or (_is_float(left) and _is_int(right)):
        return float(left), float(right)

    if _is_string(left) and _is_string(right):
        return left, right

    raise GrinRuntimeError(
        f'Line {line_number}: Incompatible types in comparison')


def _add(left: GrinValue, right: GrinValue, line_number: int) -> GrinValue:
    if _is_number(left) and _is_number(right):
        return left + right

    if _is_string(left) and _is_string(right):
        return left + right

    raise GrinRuntimeError(
        f'Line {line_number}: ADD requires numeric values or two strings')


def _sub(left: GrinValue, right: GrinValue, line_number: int) -> GrinValue:
    if _is_number(left) and _is_number(right):
        return left - right

    raise GrinRuntimeError(
        f'Line {line_number}: SUB requires numeric values')


def _mult(left: GrinValue, right: GrinValue, line_number: int) -> GrinValue:
    if _is_number(left) and _is_number(right):
        return left * right

    if _is_string(left) and _is_int(right):
        if right < 0:
            raise GrinRuntimeError(
                f'Line {line_number}: MULT does not allow negative string repetition')
        return left * right

    if _is_int(left) and _is_string(right):
        if left < 0:
            raise GrinRuntimeError(
                f'Line {line_number}: MULT does not allow negative string repetition')
        return left * right

    raise GrinRuntimeError(
        f'Line {line_number}: MULT requires numeric values or string/integer repetition')


def _div(left: GrinValue, right: GrinValue, line_number: int) -> GrinValue:
    if not (_is_number(left) and _is_number(right)):
        raise GrinRuntimeError(
            f'Line {line_number}: DIV requires numeric values')

    if right == 0:
        raise GrinRuntimeError(
            f'Line {line_number}: Division by zero')

    if _is_int(left) and _is_int(right):
        return left // right

    return left / right


def _parse_innum_value(raw: str, line_number: int) -> GrinValue:
    stripped = raw.strip()

    if _INNUM_INTEGER_PATTERN.fullmatch(stripped):
        return int(stripped)

    if _INNUM_FLOAT_PATTERN.fullmatch(stripped):
        return float(stripped)

    raise GrinRuntimeError(
        f'Line {line_number}: INNUM expected an integer or floating-point input')


__all__ = [
    Program.__name__,
    Statement.__name__,
    build_program.__name__,
    parse_program.__name__,
    execute_program.__name__,
    read_program_lines.__name__,
    run_interpreter.__name__
]
