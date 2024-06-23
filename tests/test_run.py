import pytest
from os import getenv
from unittest.mock import patch, mock_open
from rich_gradient.run import Run, RunNotFound

def test_singleton():
    run1 = Run()
    run2 = Run()
    assert run1 is run2

def test_initial_run_count_from_env():
    with patch.dict('os.environ', {'RUN': '5'}):
        run = Run()
        assert run.run == 5

def test_initial_run_count_from_file():
    mock_file_content = '3'
    with patch('builtins.open', mock_open(read_data=mock_file_content)), \
         patch('pathlib.Path.exists', return_value=True):
        run = Run()
        assert run.run == 3

def test_initial_run_count_default_value():
    with patch('builtins.open', mock_open(read_data='')), \
         patch('pathlib.Path.exists', return_value=True):
        run = Run()
        assert run.run == 1

def test_run_file_not_found():
    with patch('pathlib.Path.exists', return_value=False):
        with pytest.raises(RunNotFound):
            Run()

def test_invalid_run_count_env():
    with patch.dict('os.environ', {'RUN': 'invalid'}):
        with pytest.raises(TypeError):
            Run()

def test_invalid_run_count_file():
    mock_file_content = 'invalid'
    with patch('builtins.open', mock_open(read_data=mock_file_content)), \
         patch('pathlib.Path.exists', return_value=True):
        with pytest.raises(ValueError):
            Run()

def test_run_count_setter():
    run = Run()
    run.run = 10
    assert run.run == 10

def test_run_count_setter_invalid():
    run = Run()
    with pytest.raises(TypeError):
        run.run = 'invalid' # type: ignore

def test_increment_run():
    run = Run()
    initial_run = run.run
    run.increment_run()
    assert run.run == initial_run + 1

def test_increment_run_verbose():
    run = Run()
    initial_run = run.run
    with patch('rich.console.Console.print') as mock_print:
        run.increment_run(verbose=True)
        assert run.run == initial_run + 1
        assert mock_print.called

def test_write_envvar():
    run = Run()
    run.run = 10
    run.write_envvar()
    assert getenv('RUN') == '10'

def test_read_envvar():
    with patch.dict('os.environ', {'RUN': '10'}):
        run = Run()
        assert run.read_envvar() == 10

def test_read_envvar_not_set():
    with patch.dict('os.environ', {}, clear=True):
        run = Run()
        with pytest.raises(ValueError):
            run.read_envvar()

def test_write_runfile():
    run = Run()
    run.run = 10
    with patch('builtins.open', mock_open()) as mock_file:
        run.write_runfile()
        mock_file().write.assert_called_once_with('10')

def test_read_runfile():
    mock_file_content = '10'
    with patch('builtins.open', mock_open(read_data=mock_file_content)), \
         patch('pathlib.Path.exists', return_value=True):
        run = Run()
        assert run.read_runfile() == 10

def test_read_runfile_invalid():
    mock_file_content = 'invalid'
    with patch('builtins.open', mock_open(read_data=mock_file_content)), \
         patch('pathlib.Path.exists', return_value=True):
        run = Run()
        with pytest.raises(ValueError):
            run.read_runfile()

def test_read_runfile_not_found():
    with patch('pathlib.Path.exists', return_value=False):
        run = Run()
        with pytest.raises(RunNotFound):
            run.read_runfile()