# Relatics Connector

This is a connector for extracting and ingesting data from Relatics. The connector uses the python to interface with the Relatics API and transform the data into a format suitable for data warehouses.

## Features

- Authentication via OAuth 2.0 token-based authentication
- Data extraction from Relatics API once per process with caching
- Dynamic table schema generation based on actual Relatics data structure
- In-memory processing using pandas DataFrames
- Standalone execution mode

## Prerequisites

- Python 3.14 or higher
- Relatics API credentials (client_id, client_secret, environment)

## Setup

1. Create a `configuration.json` file with your Relatics API credentials:
   ```json
   {
     "client_id": "YOUR_CLIENT_ID",
     "client_secret": "YOUR_CLIENT_SECRET",
     "environment": "YOUR_ENVIRONMENT"
   }
   ```

2. Install dependencies:
   ```
   pip install -e .
   ```

## Usage

### Standalone Execution
```bash
python main.py
```

This will extract data from Relatics and store it in a local SQLite database at `data/relatics.sqlite`.

## Testing

Run unit tests with pytest:
```bash
pytest tests/
```

Tests use pytest-mock to mock external API calls and prevent network dependencies during testing.

## Architecture

- Authentication uses OAuth 2.0 token-based authentication with Relatics API
- Data is extracted once per process and cached to avoid multiple API calls
- Tables are dynamically generated based on actual Relatics data structure  
- Schema is inferred from data frames during sync operations
- All processing happens in memory using pandas DataFrames

## Configuration

The connector requires a `configuration.json` file with:
- `client_id`: Relatics client ID
- `client_secret`: Relatics client secret  
- `environment`: Relatics environment (e.g., "cwd")

## Repository Structure

- `main.py`: Standalone execution entry point
- `configuration.json`: Client credentials
- `src/`: Source code directory with extraction logic
- `tests/`: Unit and integration tests with fixtures