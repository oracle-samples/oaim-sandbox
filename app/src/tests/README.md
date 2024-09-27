# Tests
<!-- spell-checker:ignore pytest -->
Tests are written for `pytest` (not distributed). Run `pytest` from the `app/src` directory.

Tests should be written for each script in:

- `app/src/content`
- `app/src/modules`

and can be run individually:

```bash
pytest tests/content/<script>_test.py`
```

To run a single test in a script:

```bash
pytest tests/content/<script>_test.py -k <test_name>
```