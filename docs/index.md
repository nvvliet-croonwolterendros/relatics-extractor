# Relatics Connector

Welcome to the Relatics Connector documentation. This package provides a comprehensive solution for extracting, parsing, and transforming data from Relatics, enabling seamless integration with downstream applications and database storage.

## Overview

The Relatics Connector is designed to simplify interactions with the Relatics DataExchange API, offering:

- **Authentication**: OAuth 2.0 token-based authentication support
- **Data Extraction**: Flexible extraction methods for various data types
- **XML Processing**: Efficient parsing of complex nested XML structures
- **ETL Pipeline**: Comprehensive end-to-end data transformation and loading capabilities

## Key Features

### Data Extraction Methods

The connector supports two main use cases:

1. **Single Report Part Extraction**
2. **Complete ETL Pipeline**

#### Single Report Part Extraction

For extracting specific report parts, you can use the `parse_xml` function along with the RelaticsClient to retrieve and parse XML data.

```python
from relatics_toolkit import RelaticsClient, parse_xml

# Retrieve XML from relatics webservice
client = RelaticsClient(client_id, client_secret, environment)
result = client.get_request(workspace_id, operation)

# Parse resulting XML
parsed_df = parse_xml(result, "ReportPart")
```

#### Complete ETL Pipeline

For full data extraction and transformation, the connector provides an ETL pipeline that:

- Retrieves elements with their `ConfigurationOfRef`
- Extracts element information including Name, Description, RichText, and GUID
- Handles relationships with different cardinalities (1:1, 1:n)
- Creates appropriate link tables for 1:n relationships
- Combines all data into a structured dictionary format

## Core Components

### RelaticsClient
The `RelaticsClient` class handles authentication and API requests to the Relatics DataExchange API.

### extract_element_tables
The `extract_element_tables` function orchestrates the complete extraction, parsing, schema validation, and transformation pipeline for Relatics data into database-ready pandas DataFrames.

### parse_xml
The `parse_xml` function parses deeply nested XML structures returned by Relatics into structured pandas DataFrames.

## Getting Started

To get started with the Relatics Connector, refer to the [Getting Started](getting_started/index.md) guide which provides detailed instructions on setting up your environment and running basic extractions.