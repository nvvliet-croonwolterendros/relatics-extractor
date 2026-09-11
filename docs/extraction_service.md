# Extractor API Reference

This function serves as the main entry point for extracting element data from Relatics and transforming it into a set of normalized pandas tables. It orchestrates the full extraction workflow across one or more workspaces and elements, including data retrieval, schema validation, table normalization, and application of business-specific transformations.

The function supports both sequential and parallel execution, making it suitable for small ad hoc extracts as well as larger data pipelines. Optionally, selected to-one relations can be inlined into the resulting element tables, simplifying downstream analysis and reporting. The output is a dictionary of transformed DataFrames that can be used directly for further processing, analytics, or data integration tasks.

## Overview

::: relatics_toolkit.extract_element_tables
    options:
      show_root_heading: true
      show_source: true
      heading_level: 2
      members:
        - __init__
        - run_etl_fast
        - run_etl_slow
        - process_element
      merge_init_into_class: true