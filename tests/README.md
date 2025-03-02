# Testing the Pharmacy Rota Generator

This directory contains tests for the pharmacy rota generator application. The tests are written using pytest and cover different aspects of the application.

## Test Structure

- `test_models.py`: Tests for the data models
- `test_scheduler.py`: Tests for the scheduling logic
- `test_web.py`: Tests for the web interface
- `conftest.py`: Shared test fixtures

## Running the Tests

### Run All Tests

```bash
# From the project root directory
pytest tests/

# With more verbose output
pytest -v tests/
```

### Run a Specific Test File

```bash
# Run just the models tests
pytest tests/test_models.py

# Run just the scheduler tests
pytest tests/test_scheduler.py

# Run just the web interface tests
pytest tests/test_web.py
```

### Run a Specific Test Class or Function

```bash
# Run a specific test class
pytest tests/test_models.py::TestPharmacist

# Run a specific test function
pytest tests/test_models.py::TestPharmacist::test_pharmacist_init
```

## Test Coverage

To check test coverage, install pytest-cov:

```bash
pip install pytest-cov
```

Then run:

```bash
# Generate a coverage report
pytest --cov=src tests/

# Generate an HTML coverage report
pytest --cov=src --cov-report=html tests/
# This will create a htmlcov directory with the coverage report
```

## Adding New Tests

When adding new tests:

1. Follow the existing structure and naming conventions
2. Use fixtures from `conftest.py` where appropriate
3. Consider adding new fixtures if you need reusable test data
4. Make sure your tests are isolated and don't depend on side effects from other tests
