# Relatics Extractor

A Python package for extracting, parsing, and transforming data from Relatics (a requirements management tool) into database-ready pandas DataFrames.

## Overview

The Relatics Extractor is designed to streamline the process of extracting data from Relatics API endpoints and converting it into structured, normalized tables suitable for database storage. It handles complex relationships between entities, nested XML structures, and provides robust error handling throughout the extraction pipeline.

## Key Features

- **Authentication**: Implements OAuth 2.0 token-based authentication with Relatics API
- **Data Extraction**: Handles API calls to retrieve elements and their relationships
- **XML Parsing**: Parses deeply nested XML structures into pandas DataFrames
- **Schema Validation**: Validates data against predefined schemas and normalizes tables
- **Relationship Management**: Properly handles different relationship cardinalities:
  - :1 (one-to-one) relations are embedded in element tables  
  - :n (many-to-one) relations become link tables
- **Multithreading Support**: Uses ThreadPoolExecutor for faster processing of multiple elements
- **Error Handling**: Robust error handling with logging and failure tracking

## Installation

```bash
# Install from source
pip install .

# Or install in development mode
pip install -e .
```

## Usage

### Basic Setup

```python
from relatics_extractor import Extractor

# Initialize the extractor with your credentials
extractor = Extractor(
    client_id="your_client_id",
    client_secret="your_client_secret", 
    environment="your_environment"
)
```

### Running ETL Pipeline

```python
# Run the extraction process for multiple workspaces
tables = extractor.run_etl_fast(
    workspaces=["workspace1", "workspace2"],
    element_operation="GetElements",
    datamodel_operation="GetDatamodel"
)

# Access extracted tables
for table_name, df in tables.items():
    print(f"Table: {table_name}")
    print(df.head())
```

## Architecture

The extractor follows a clear pipeline architecture:

1. **Extraction**: Uses `RelaticsClient` to fetch data from API endpoints
2. **Parsing**: Parses XML responses using `parse_xml` function  
3. **Validation**: Validates schemas using `validator.py`
4. **Transformation**: Transforms data using `transformer.py` to normalize relationships

## Key Components

- **Extractor**: Main class that orchestrates the full ETL pipeline
- **RelaticsClient**: Handles OAuth 2.0 authentication and API requests  
- **parse_xml**: Parses deeply nested XML structures
- **transformer**: Transforms raw data into structured tables with proper relationship handling
- **validator**: Validates schema compliance and normalizes table structures

## License

MIT