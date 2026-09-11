# Relatics Connector AGENT Instructions

This project is a connector for Relatics data extraction and ingestion. The implementation uses Python.

## Key Files and Entry Points

- `main.py` - The entry point for running the connector in standalone mode
- `configuration.json` - Contains client credentials for Relatics API access

## How to Run

### Standalone execution:
```bash
python main.py
```

### Running tests:
```bash
pytest tests/
```

## Configuration

The connector requires a `configuration.json` file with:
- `client_id`
- `client_secret`
- `environment`

## Architecture Notes

- Authentication uses OAuth 2.0 token-based authentication with Relatics API
- Data is extracted once per process and cached
- Tables are dynamically generated based on actual Relatics data structure
- Schema is inferred from data frames during sync operations
- All processing happens in memory using pandas DataFrames

## Testing Conventions

- Tests use pytest with pytest-mock
- Test fixtures are located in `tests/unit/fixtures/test_transformer/`
- Integration tests require a valid Relatics API connection
- Unit tests mock external API calls to prevent network dependencies