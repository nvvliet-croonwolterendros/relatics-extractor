# XML Parser Reference

The `parse_xml` function unpakcs a relatics XML into a pandas dataframe.
The XML relatics returns is deeply nested and needs to be unpacked, multiple report parts can be part of the same report. This means that multible different tables can be formed from a single webservice.
In order to cleanly extract these tables the `report part` should be specified. This means the report part as defined in the Relatics report.

## Overview

::: relatics_toolkit.parse_xml
    options:
      show_root_heading: true
      show_source: true
      heading_level: 2
      members:
        - true
      merge_init_into_class: true