# cwt-cgt

This repository collects reference materials and simulation code for continuous wavelet transport (CWT) studies. The `cwt-sim` package contains the Python implementation, while the surrounding documents capture theory notes and project context.

## Dependency management

The Python components rely on a small scientific Python stack. Install the full runtime dependencies with:

```bash
pip install -r requirements.txt
```

When developing or validating changes, install the lighter test requirements first:

```bash
pip install -r requirements.test.txt
```

The test requirements file installs everything needed to execute `pytest` successfully, following the guidance in [`AGENTS.md`](AGENTS.md).

## Running the tests

After installing the test dependencies, execute the unit and regression suites from the repository root:

```bash
pytest cwt-sim/tests
```

## Continuous integration

Automated test runs are configured through the [GitHub Actions workflow](.github/workflows/tests.yml). The workflow provisions
Python 3.12, installs the lightweight test requirements, and runs `pytest cwt-sim/tests` for every pull request and for pushes
to the active branches. This keeps the regression and unit suites in sync with continuous development activity without manual
setup.

Additional experiment scripts and notebooks live under `cwt-sim/experiments` and `cwt-sim/notebooks` respectively.
