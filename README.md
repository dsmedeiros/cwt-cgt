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

Additional experiment scripts and notebooks live under `cwt-sim/experiments` and `cwt-sim/notebooks` respectively.
