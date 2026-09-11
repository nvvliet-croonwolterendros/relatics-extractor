# Getting Started

This package makes it easy to retrieve data from, and interact with Relatics.

In order to make full use of the relatics extraction function a very specific webservice needs be be made, which can be found later in the getting started.

With the webservice in place an ETL run can be started which can extract a list of elements at once and deduplicate the resulting tables. Doing this will make the relatics data clean enough to be used in downstream applications or database storage.

This package supports two main use cases:

- Single report part extraction.
- Complete ETL Pipeline.

## Single report part extraction
In order to do single report part extraction and transformation using this package the following code can be used:

```python
from relatics_toolkit import RelaticsClient, parse_xml

# Retrieve XML from relatics webservice
client = RelaticsClient(client_id, client_secret, environment)
result = client.get_request(workspace_id, operation)

# Parse resulting XML
parsed_df = parse_xml(result, "ReportPart")
```

Now parsed_df is a `pd.DataFrame` and can be used for downstream applications.

!!! note
    Relatics doesn't include parts of a report if they are empty. If for example a property is added in a report part, but is never used in Relatics, the corresponding column will not show up in the webservice and therefore not in the DataFrame.

## Complete ETL Pipeline
To do a full ETL pipeline extraction a very specific Relatics report needs to be constructed, more about this on the next page.

The ETL pipeline will do the following:

- Produce a table with the Name, Description, RichText and GUID of the Element and append all its properties and relations with a **:1** cardinality.
- Produce a link table for each relation the element has to other elements with **:n** cardinality. The link table will only have the *r1_element_guid*, *r2_element_guid* and *workspace_id*

!!! example
    If a **requirement** element has a *:n* relation with the **Issue** element. The link table will be called **raw_relatics__requirement_issue** and will contain the columns: *requirement_guid*, *issue_guid* and *workspace_id*

- Combine all these tables into a dictionary and return it.

If multiple workspaces are provided the Extractor will loop over each workspace and try to append to a Dataframe in the dictionary if it exists. If the tablename doesnt exist yet a key will be added to the dictionary.

For a more detailed explanation follow the next pages in this getting started!