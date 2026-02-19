# test_runtime.py
#
# ICS 33 Winter 2026
# Project 3: Why Not Smile?
#
# Unit tests for grin.runtime module.

from grin.runtime import GrinRuntimeError, ProgramState
import unittest


class TestProgramState(unittest.TestCase):
    def test_initial_line_number_is_one(self):
        state = ProgramState(
            statement_count=5,
            labels={},
            input_reader=lambda: '',
            output_writer=lambda _: None)

        self.assertEqual(state.current_line(), 1)


    def test_advance_increments_line_number(self):
        state = ProgramState(
            statement_count=5,
            labels={},
            input_reader=lambda: '',
            output_writer=lambda _: None)

        state.advance()
        self.assertEqual(state.current_line(), 2)


    def test_jump_to_sets_line_number(self):
        state = ProgramState(
            statement_count=5,
            labels={},
            input_reader=lambda: '',
            output_writer=lambda _: None)

        state.jump_to(4)
        self.assertEqual(state.current_line(), 4)


    def test_has_statement_to_execute(self):
        state = ProgramState(
            statement_count=3,
            labels={},
            input_reader=lambda: '',
            output_writer=lambda _: None)

        self.assertTrue(state.has_statement_to_execute())

        state.jump_to(3)
        self.assertTrue(state.has_statement_to_execute())

        state.advance()
        self.assertFalse(state.has_statement_to_execute())


    def test_end_program_sets_line_beyond_last(self):
        state = ProgramState(
            statement_count=3,
            labels={},
            input_reader=lambda: '',
            output_writer=lambda _: None)

        state.end_program()
        self.assertFalse(state.has_statement_to_execute())


    def test_variable_defaults_to_zero(self):
        state = ProgramState(
            statement_count=1,
            labels={},
            input_reader=lambda: '',
            output_writer=lambda _: None)

        self.assertEqual(state.variable_value('X'), 0)


    def test_can_set_and_get_variable(self):
        state = ProgramState(
            statement_count=1,
            labels={},
            input_reader=lambda: '',
            output_writer=lambda _: None)

        state.set_variable_value('X', 42)
        self.assertEqual(state.variable_value('X'), 42)


    def test_can_set_string_variable(self):
        state = ProgramState(
            statement_count=1,
            labels={},
            input_reader=lambda: '',
            output_writer=lambda _: None)

        state.set_variable_value('NAME', 'Boo')
        self.assertEqual(state.variable_value('NAME'), 'Boo')


    def test_push_and_pop_return_line(self):
        state = ProgramState(
            statement_count=5,
            labels={},
            input_reader=lambda: '',
            output_writer=lambda _: None)

        state.push_return_line(3)
        state.push_return_line(7)

        self.assertEqual(state.pop_return_line(1), 7)
        self.assertEqual(state.pop_return_line(1), 3)


    def test_pop_without_push_raises_error(self):
        state = ProgramState(
            statement_count=1,
            labels={},
            input_reader=lambda: '',
            output_writer=lambda _: None)

        with self.assertRaises(GrinRuntimeError) as context:
            state.pop_return_line(1)

        self.assertIn('RETURN without a previous GOSUB', str(context.exception))


    def test_label_line_returns_correct_line(self):
        state = ProgramState(
            statement_count=5,
            labels={'START': 1, 'END': 5},
            input_reader=lambda: '',
            output_writer=lambda _: None)

        self.assertEqual(state.label_line('START', 1), 1)
        self.assertEqual(state.label_line('END', 1), 5)


    def test_label_line_raises_for_undefined_label(self):
        state = ProgramState(
            statement_count=5,
            labels={},
            input_reader=lambda: '',
            output_writer=lambda _: None)

        with self.assertRaises(GrinRuntimeError) as context:
            state.label_line('MISSING', 1)

        self.assertIn('Jump to undefined label', str(context.exception))


    def test_read_input_delegates_to_reader(self):
        state = ProgramState(
            statement_count=1,
            labels={},
            input_reader=lambda: 'test input',
            output_writer=lambda _: None)

        self.assertEqual(state.read_input(1), 'test input')


    def test_write_output_delegates_to_writer(self):
        output = []
        state = ProgramState(
            statement_count=1,
            labels={},
            input_reader=lambda: '',
            output_writer=output.append)

        state.write_output('Hello')
        state.write_output(42)

        self.assertEqual(output, ['Hello', '42'])


if __name__ == '__main__':
    unittest.main()
