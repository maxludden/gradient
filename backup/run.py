import atexit
from os import environ, getenv
from pathlib import Path
from typing import Optional

from rich.console import Console


class RunNotFound(FileNotFoundError):
    """An exception to raise when the run count is invalid."""

    pass


class Singleton(type):
    _instances = {}  # type: ignore

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class Run(metaclass=Singleton):
    """A class to keep track of the number of times a Python module is debugged or run."""

    SUPERGENE: Path = Path.home() / "dev" / "py" / "gradient"
    RUNFILE = Path("/Users/maxludden/dev/py/gradient/logs/log.txt")

    def __init__(self, run: Optional[int] = None, verbose: bool = False) -> None:
        if run:
            if not isinstance(run, int):
                raise TypeError("The run count must be an integer.")
            self.run = run
        else:
            run_env = getenv("RUN")
            if run_env:
                self.run = int(run_env)
            else:
                if not self.RUNFILE.exists():
                    raise ValueError("The run file is not found.")
                with open(self.RUNFILE, "r") as f:
                    f_content = f.read()
                    if f_content.strip():  # Check if f_content is not empty
                        self.run = int(f_content)
                    else:
                        self.run = 1  # Set a default value if f_content is empty
        atexit.register(self.increment_run, verbose=verbose)

    def __call__(self) -> int:
        return self.run

    def _validate(self) -> bool:
        """Validate the run count."""
        if not isinstance(self.run, int):
            return False
        return True

    @property
    def run(self) -> int:
        """The run count."""
        return self._run

    @run.setter
    def run(self, value: int) -> None:
        """Set the run count."""
        if not isinstance(value, int):
            raise TypeError("The run count must be an integer.")
        self._run = value

    def increment_run(self, verbose: bool = False) -> None:
        """Increment the run count."""
        if verbose:
            _console = Console()
            _console.print(f"Run: [i b #00afff]{self._run}[/]")
        self._run += 1
        if verbose:
            _console.print(f"Incrimented Run: [i b #00afff]{self._run}[/]")
        self.write_envvar()
        if verbose:
            _console.print(f"Run ENVVAR: [i b #00afff]{getenv("RUN")}[/]")
        self.write_runfile()

    def read_envvar(self) -> int:
        """Read the run count from environmental variable or from a file."""
        run = getenv("RUN")
        if not run:
            raise ValueError("The run environmental varialbe is not set.")
        self.run = int(run)
        return self.run

    def write_envvar(self) -> None:
        """Write the run count to an environmental variable."""
        environ["RUN"] = str(self._run)

    def read_runfile(self) -> int:
        """Read the run count from a file."""
        try:
            with open(self.RUNFILE, "r") as f:
                run = int(f.read())
        except FileNotFoundError:
            raise RunNotFound("The run file is not found.")
        except ValueError:
            raise RunNotFound("The run file is invalid.")
        return run

    def write_runfile(self) -> None:
        """Write the run count to a file.add()

        Args:
            run (int): The run count.
        """
        with open(self.RUNFILE, "w") as f:
            f.write(str(self._run))


# Register the increment_run_count method to be called when the program exits
global run
run: Run = Run()


if __name__ == "__main__":
    run = Run()
    console = Console()
    console.clear()
    console.print(f"Run: [b i #00afff]{run.run}[/]")
    console.line(2)
