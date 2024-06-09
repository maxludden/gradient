import pytest

from gradient.run import Run


# Helper function to reset the Singleton instance for testing purposes
def reset_singleton(cls):
    cls._instances = {}


def test_singleton():
    reset_singleton(Run)
    run1 = Run()
    run2 = Run()
    assert run1 is run2


def test_initialization_with_run_argument():
    reset_singleton(Run)
    run = Run(run=5)
    assert run.run == 5


def test_initialization_with_invalid_run_argument():
    reset_singleton(Run)
    with pytest.raises(TypeError):
        Run(run="invalid")  # type: ignore


def test_run_setter_validation():
    reset_singleton(Run)
    run = Run(run=5)
    with pytest.raises(TypeError):
        run.run = "invalid"  # type: ignore


def text_inc_run():
    reset_singleton(Run)
    run = Run(run=5)
    assert run.run == 5
    run.increment_run()
    assert run.run == 6
    run.increment_run()
    assert run.run == 7
