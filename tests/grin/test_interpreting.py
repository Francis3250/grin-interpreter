# test_interpreting.py
#
# ICS 33 Winter 2026
# Project 3: Why Not Smile?
#
# Unit tests for grin.interpreting and grin.runtime.

from grin.interpreting import run_interpreter
from grin.runtime import GrinRuntimeError
import unittest


class TestGrinInterpreting(unittest.TestCase):
    def run_program(self, *lines: str) -> list[str]:
        output: list[str] = []
        reader = _line_reader(*lines)
        run_interpreter(input_reader = reader, output_writer = output.append)
        return output


    def assertRuntimeError(self, *lines: str) -> GrinRuntimeError:
        reader = _line_reader(*lines)

        with self.assertRaises(GrinRuntimeError) as context:
            run_interpreter(input_reader = reader, output_writer = lambda _: None)

        return context.exception


    def test_can_execute_let_and_print(self):
        output = self.run_program(
            'LET A 3',
            'PRINT A',
            '.')

        self.assertEqual(output, ['3'])


    def test_variables_default_to_zero(self):
        output = self.run_program(
            'PRINT DOESNOTEXIST',
            '.')

        self.assertEqual(output, ['0'])


    def test_can_execute_arithmetic_with_expected_types(self):
        output = self.run_program(
            'LET A 7',
            'DIV A 2',
            'PRINT A',
            'LET B "Boo"',
            'MULT B 3',
            'PRINT B',
            'LET C 2',
            'MULT C "Hi"',
            'PRINT C',
            '.')

        self.assertEqual(output, ['3', 'BooBooBoo', 'HiHi'])


    def test_can_execute_conditional_goto(self):
        output = self.run_program(
            'LET A 3',
            'GOTO 2 IF A < 4',
            'PRINT "skipped"',
            'PRINT "ran"',
            '.')

        self.assertEqual(output, ['ran'])


    def test_can_execute_gosub_and_return(self):
        output = self.run_program(
            'LET A 1',
            'GOSUB "CHUNK"',
            'PRINT A',
            'END',
            'CHUNK: LET A 5',
            'RETURN',
            '.')

        self.assertEqual(output, ['5'])


    def test_runtime_error_when_return_has_no_gosub(self):
        error = self.assertRuntimeError(
            'RETURN',
            '.')

        self.assertIn('RETURN without a previous GOSUB', str(error))


    def test_runtime_error_when_goto_target_is_zero(self):
        error = self.assertRuntimeError(
            'GOTO 0',
            '.')

        self.assertIn('Cannot jump to the same line', str(error))


    def test_runtime_error_when_gosub_jumps_to_same_line(self):
        error = self.assertRuntimeError(
            'A: GOSUB "A"',
            '.')

        self.assertIn('Cannot jump to the same line', str(error))


    def test_runtime_error_when_jump_is_out_of_bounds(self):
        error = self.assertRuntimeError(
            'GOTO 100',
            '.')

        self.assertIn('Jump target is out of bounds', str(error))


    def test_runtime_error_when_duplicate_label_exists(self):
        error = self.assertRuntimeError(
            'LOOP: PRINT "a"',
            'LOOP: PRINT "b"',
            '.')

        self.assertIn('Duplicate label', str(error))


    def test_runtime_error_for_invalid_comparison_types(self):
        error = self.assertRuntimeError(
            'LET A 3',
            'GOTO 1 IF A = "3"',
            '.')

        self.assertIn('Incompatible types in comparison', str(error))


    def test_runtime_error_for_invalid_innum_input(self):
        error = self.assertRuntimeError(
            'INNUM A',
            '.',
            'abc')

        self.assertIn('INNUM expected an integer or floating-point input', str(error))


    def test_innum_parses_integer_and_float(self):
        output = self.run_program(
            'INNUM A',
            'PRINT A',
            'INNUM B',
            'PRINT B',
            '.',
            '   11  ',
            ' -3.5 ')

        self.assertEqual(output, ['11', '-3.5'])


def _line_reader(*lines: str):
    iterator = iter(lines)

    def read() -> str:
        try:
            return next(iterator)
        except StopIteration as e:
            raise EOFError from e

    return read


if __name__ == '__main__':
    unittest.main()
