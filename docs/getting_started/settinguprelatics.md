# Setting up the right Relatics report and webservice.
## Introduction

In order to make the ETL process work a very specific relatics report and webservice needs to be setup. This webservice will be used by the `relatics_toolkit.extract_element_tables` in order to produce the full extraction.

The ETL pipeline will do the following:

- Get a list of elements with their `ConfigurationOfRef` to be extracted and start a loop.
- Produce a table with the Name, Description, RichText and GUID of the Element and append all their relations with a **:1** cardinality.
- Produce a link table for each relation the element has to other elements with **:n** cardinality. The link table will only have the *ElementGUID*, *R2RelationElementGUID* and *workspaceid*
If a **requirement** element has a :n relation with the **Issue** element. The link table will be called **raw_relatics__requirement_issue** and will contain the columns: *requirement_guid*, *issue_guid* and *workspaceid*
- Combine all these tables into a dictionary and return it.

!!! danger "Warning!"
    Don't skip any steps in this setup. Copy names and query patterns exactly. The `extract_element_tables` method has no flexibility in report part naming and the naming of the query values should therefore match this guide.
    If multiple workspaces are to be extracted in the same run ensure that the names of all the reports mentioned below are the same.

!!! tip
    Ensure that after creating a report you enter the *output extension* to be **xml**

## Setting up the Report structure
The report in relatics needs to be the following structure:

![Report structure](assets/report_structure.png)

This is the only part where you can change a name. The report part which contains all elements to export is defaulted to `Elements`. If you so desire you can modify this name and pass it as an parameter in the `extract_element_tables` method.
Next we will go more in depth of the individual report parts needed for the connector.

### Data extraction report
With the ConfigurationOfRef list obtained by the process above we can start looping over their ConfigurationOfRefs. The report that is shown below will get all the requried data for one Relatics element. Then, using this information, the extractor will produce the element tables (with the information for each element. e.g. name and discription. And all relations with a :1 cardinality) and all the link tables (the relation to elements with a :n cardinality).

The report structure will look like this:

![Report structure](assets/report_structure.png)

#### Element
This Part is the entry point for the extractor, it takes the ConfigurationOfRef of the desired, to be extracted, element as parameter and will generate the report from this information.
The R1Element and R1ElementID are important pieces of information to cleanly construct the tables.

![Report structure](assets/element_query_with_details.png)

![Report structure](assets/parameter.png)

#### ElementInstances
The Table for element instances will be used to generate the element table with information about the element itself. and you set it up like this:

![Element Instances](assets/element_instances.png)

#### Properties
This table gives you the information about all properties that could exist. This is needed to make a consistent table with all possible fields present, even when they're empty.

![Element Instances](assets/properties_query.png)

Below are the node details for each node in the query:

*R1Element*:

Nothing is selected in this section, the only relevant part is in the constraint:
![Property node constraint](assets/properties_node_R1Element.png)

*Property*:

![Property node constraint](assets/properties_node_property_advanced.png)
![Property node constraint](assets/properties_node_property_join.png)

#### PropertyInstances

This table returns the actual properties with their value. Set it up like this.
![Property Instances query](assets/propertyinstances_query.png)

*R1Instance*:

You set up the constraint and advanced fields.

![Property Instances R1Instance](assets/propertyinstances_node_r1instance.png)

*PropertyInstance*:

You set up the Advanced fields an Join Editor.

![Property Instances PropertyInstance](assets/propertyinstances_node_propertyinstance.png)

![Property Instances PropertyInstance join](assets/propertyinstances_node_propertyinstance_join.png)

#### Relations
This table gives you the possible relations an element can have, akin to the *Properties* table.

![Relation query](assets/relations_query.png)

*R1Element*:

Modify the Constraint Editor:

![Relation node R1Element](assets/relations_node_r1element.png)

*Relation*:

Modify the Join Editor, Common fields and Advanced fields.

![Relation node Relation](assets/relations_node_relation.png)
![Relation node Relation Advanced fields](assets/relations_node_relation_advanced.png)

*R2Element*:

Modify the Common fields, Advanced fields and Join Editor.

![Relation node R2Element](assets/relations_node_r2element.png)
![Relation node R2Element Join Editor](assets/relations_node_r2element_join.png)

*All types*:

![Relation node alltypes](assets/relations_node_alltypes.png)
![Relation node R2Element alltypes](assets/relations_node_alltypes_join.png)

#### RelationInstances
This table gives you the actual relations an element has.

!!! bug
    Known bug: When a Relatics Library has relations to another library and a child element has the same relation to this library. The Extractor cannot pick up the right relation and skips the child element altogether.

![Relation Instances query](assets/relationinstances_query.png)

*R1Instance*:

Modify the Common fields, Constraint editor and Advandec fields section:
![Relation Instances R1Instance](assets/relationinstances_node_r1instance.png)

*RelationInstance*:

Modify the Join editor and Advanced fields.
![Relation Instances Relationinstance](assets/relationinstances_node_relationinstance.png)

*Relation*:

Modify the Join Editor and Advanced fields.
![Relation Instances Relation](assets/relationinstances_node_relationinstance.png)

*R2Instance*:

Modify the Common fields, Advanced fiels and Join Editor.
![Relation Instances R2Instance](assets/relationinstances_node_r2instance.png)
![Relation Instances R2Instance join editor](assets/relationinstances_node_r2instance_join.png)

*R2Element*:

Modify the Common fields, Advanced fields and Join Editor.
![Relation Instances R2Element](assets/relationinstances_node_r2element.png)
![Relation Instances R2Element join](assets/relationinstances_node_r2element_join.png)

*R1Element*:

Modify Common fields and Join Editor.
![Relation Instances R1Element](assets/relationinstances_node_r1element.png)