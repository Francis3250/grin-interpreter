# runtime.py
#
# ICS 33 Winter 2026
# Project 3: Why Not Smile?
#
# Runtime support for executing a parsed Grin program.

from collections.abc import Callable


GrinValue = int | float | str


class GrinRuntimeError(Exception):
    """Raised when a runtime error occurs while interpreting Grin code."""

    def __init__(self, message: str):
        super().__init__(f'Error during interpretation: {message}')
        self._message = message


class ProgramState:
    """Mutable state for one execution of a Grin program."""

    def __init__(
            self, *,
            statement_count: int,
            labels: dict[str, int],
            input_reader: Callable[[], str],
            output_writer: Callable[[str], None]):
        self._statement_count = statement_count
        self._labels = dict(labels)
        self._input_reader = input_reader
        self._output_writer = output_writer

        self._line_number = 1
        self._variables: dict[str, GrinValue] = {}
        self._return_stack: list[int] = []


    def current_line(self) -> int:
        return self._line_number


    def has_statement_to_execute(self) -> bool:
        return self._line_number <= self._statement_count


    def advance(self) -> None:
        self._line_number += 1


    def jump_to(self, line_number: int) -> None:
        self._line_number = line_number


    def end_program(self) -> None:
        self._line_number = self._statement_count + 1


    def statement_count(self) -> int:
        return self._statement_count


    def label_line(self, label: str, line_number: int) -> int:
        if label in self._labels:
            return self._labels[label]

        raise GrinRuntimeError(
            f'Line {line_number}: Jump to undefined label "{label}"')


    def variable_value(self, name: str) -> GrinValue:
        return self._variables.get(name, 0)


    def set_variable_value(self, name: str, value: GrinValue) -> None:
        self._variables[name] = value


    def read_input(self, line_number: int) -> str:
        try:
            return self._input_reader()
        except EOFError as e:
            raise GrinRuntimeError(
                f'Line {line_number}: Input expected but EOF was encountered') from e


    def write_output(self, value: GrinValue) -> None:
        self._output_writer(str(value))


    def push_return_line(self, line_number: int) -> None:
        self._return_stack.append(line_number)


    def pop_return_line(self, line_number: int) -> int:
        if self._return_stack:
            return self._return_stack.pop()

        raise GrinRuntimeError(
            f'Line {line_number}: RETURN without a previous GOSUB')


__all__ = [
    'GrinValue',
    GrinRuntimeError.__name__,
    ProgramState.__name__
]
