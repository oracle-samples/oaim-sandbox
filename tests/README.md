# AI Explorer for Apps Tests

This directory contains Tests for the AI Explorer for Apps.  Tests are automatically
run as part of opening a new Pull Requests.  All tests must pass to enable merging.

## Running Tests

All tests can be run by using the following command from the project root:

```bash
pytest tests -v
```

### Server Endpoint Tests

To run the server endpoint tests, use the following command from the project root:

```bash
pytest tests/server -v
```

These tests verify the functionality of the endpoints by establishing:
- A real FastAPI server
- A Docker container used for database tests
- Mocks for external dependencies (OCI)

### Streamlit Tests

To run the Streamlit page tests, use the following command from the project root:

```bash
pytest tests/sandbox -v
```

These tests verify the functionality of the Streamlit app by establishing:
- A real AI Explorer API server 
- A Docker container used for database tests

## Test Structure

### Server Endpoint Tests

The server endpoint tests are organized into two classes:
- `TestNoAuthEndpoints`: Tests that verify authentication is required
- `TestEndpoints`: Tests that verify the functionality of the endpoints

### Streamlit Settings Page Tests

The Streamlit settings page tests are organized into two classes:
- `TestFunctions`: Tests for the utility functions
- `TestUI`: Tests for the Streamlit UI components

## Dependencies

The tests require the following additional dependencies to the default AI Explorer dependencies:
- pytest
- pytest-mock
- docker (for database container tests)

## Test Environment

The tests use a combination of real and mocked components:
- A real FastAPI server is started for the endpoint tests
- A Docker container is used for database tests
- Streamlit components are tested using the AppTest framework
- External dependencies are mocked where appropriate 