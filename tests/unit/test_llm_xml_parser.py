"""
Unit tests for xml_report_parser.parse_xml / _parse_xml_to_dict / _recursive_unpack.

Adjust the import below to match wherever these functions actually live in
your project (e.g. `from myapp.reports import parse_xml, ...`).

WARNING:
These tests are llm generated while they pass with the current code and are probably 
"""
import xml.etree.ElementTree as ET

import pandas as pd
import pytest

from src.ingestion.xml_parser import parse_xml, _parse_xml_to_dict, _recursive_unpack


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_root(xml_string: str) -> ET.Element:
    return ET.fromstring(xml_string)


# ---------------------------------------------------------------------------
# _recursive_unpack
# ---------------------------------------------------------------------------

class TestRecursiveUnpack:
    def test_flat_dict_returns_single_record(self):
        row = {"a": "1", "b": "2"}
        result = _recursive_unpack(row)
        assert result == [{"a": "1", "b": "2"}]

    def test_empty_dict_returns_single_empty_record(self):
        result = _recursive_unpack({})
        assert result == [{}]

    @pytest.mark.parametrize("falsy_value", ["", None, 0, [], {}])
    def test_falsy_scalar_values_are_dropped(self, falsy_value):
        row = {"keep": "value", "drop": falsy_value}
        result = _recursive_unpack(row)
        assert result == [{"keep": "value"}]

    def test_nested_dict_is_flattened_with_prefix(self):
        row = {"parent": {"child": "value"}}
        result = _recursive_unpack(row)
        assert result == [{"parent.child": "value"}]

    def test_deeply_nested_dict_is_flattened(self):
        row = {"a": {"b": {"c": "value"}}}
        result = _recursive_unpack(row)
        assert result == [{"a.b.c": "value"}]

    def test_single_item_list_of_dicts_produces_one_record(self):
        row = {"items": [{"id": "1"}]}
        result = _recursive_unpack(row)
        assert result == [{"items.id": "1"}]

    def test_multi_item_list_of_dicts_produces_one_record_per_item(self):
        row = {"items": [{"id": "1"}, {"id": "2"}]}
        result = _recursive_unpack(row)
        assert len(result) == 2
        assert {"items.id": "1"} in result
        assert {"items.id": "2"} in result

    def test_two_list_keys_produce_cartesian_product(self):
        row = {
            "colors": [{"name": "red"}, {"name": "blue"}],
            "sizes": [{"val": "S"}, {"val": "M"}, {"val": "L"}],
        }
        result = _recursive_unpack(row)
        # cartesian product => 2 * 3 = 6 records
        assert len(result) == 6
        combos = {(r["colors.name"], r["sizes.val"]) for r in result}
        assert combos == {
            ("red", "S"), ("red", "M"), ("red", "L"),
            ("blue", "S"), ("blue", "M"), ("blue", "L"),
        }

    def test_base_record_merged_into_every_cartesian_product_row(self):
        row = {
            "id": "root-1",
            "items": [{"id": "1"}, {"id": "2"}],
        }
        result = _recursive_unpack(row)
        assert len(result) == 2
        for record in result:
            assert record["id"] == "root-1"

    def test_empty_list_value_is_dropped(self):
        row = {"items": [], "keep": "value"}
        result = _recursive_unpack(row)
        assert result == [{"keep": "value"}]

    def test_list_of_non_dicts_is_dropped(self):
        # value is a truthy list but not all items are dicts -> falls through
        # to the final `elif value:` branch and is kept as-is.
        row = {"items": ["a", "b"], "keep": "value"}
        result = _recursive_unpack(row)
        assert result == [{"items": ["a", "b"], "keep": "value"}]

    def test_nested_list_inside_list_of_dicts_cartesian_product(self):
        row = {
            "outer": [
                {"id": "1", "inner": [{"x": "a"}, {"x": "b"}]},
            ]
        }
        result = _recursive_unpack(row)
        assert len(result) == 2
        combos = {r["outer.inner.x"] for r in result}
        assert combos == {"a", "b"}
        for r in result:
            assert r["outer.id"] == "1"


# ---------------------------------------------------------------------------
# _parse_xml_to_dict
# ---------------------------------------------------------------------------

class TestParseXmlToDict:
    def test_element_with_no_children_returns_empty_dict(self):
        root = make_root("<Report></Report>")
        result = _parse_xml_to_dict(root)
        assert result == {}

    def test_single_child_with_attributes(self):
        root = make_root('<Report><Item id="1" name="foo"/></Report>')
        result = _parse_xml_to_dict(root)
        assert result == {"Item": [{"id": "1", "name": "foo"}]}

    def test_multiple_children_same_tag_are_grouped_into_a_list(self):
        root = make_root(
            '<Report><Item id="1"/><Item id="2"/><Item id="3"/></Report>'
        )
        result = _parse_xml_to_dict(root)
        assert result == {
            "Item": [{"id": "1"}, {"id": "2"}, {"id": "3"}]
        }

    def test_children_with_different_tags(self):
        root = make_root(
            '<Report><Header title="Q1"/><Item id="1"/></Report>'
        )
        result = _parse_xml_to_dict(root)
        assert result == {
            "Header": [{"title": "Q1"}],
            "Item": [{"id": "1"}],
        }

    def test_nested_children_are_recursively_parsed(self):
        root = make_root(
            """
            <Report>
                <Item id="1">
                    <SubItem code="A"/>
                </Item>
            </Report>
            """
        )
        result = _parse_xml_to_dict(root)
        assert result == {
            "Item": [
                {"id": "1", "SubItem": [{"code": "A"}]}
            ]
        }

    def test_child_with_no_attributes_and_no_children_is_dropped(self):
        # unpacked_element ends up as an empty dict, which is falsy,
        # so it is filtered out of the resulting list.
        root = make_root("<Report><Item></Item></Report>")
        result = _parse_xml_to_dict(root)
        assert result == {"Item": []}

    def test_child_with_no_attributes_but_with_children_is_kept(self):
        root = make_root(
            '<Report><Item><SubItem code="A"/></Item></Report>'
        )
        result = _parse_xml_to_dict(root)
        assert result == {
            "Item": [{"SubItem": [{"code": "A"}]}]
        }


# ---------------------------------------------------------------------------
# parse_xml
# ---------------------------------------------------------------------------

class TestParseXml:
    def test_simple_repeated_elements_become_dataframe_rows(self):
        root = make_root(
            """
            <root>
                <Report>
                    <Item id="1" name="foo"/>
                    <Item id="2" name="bar"/>
                </Report>
            </root>
            """
        )
        df = parse_xml(root, "Report")
        assert list(df.columns) == ["id", "name"]
        assert len(df) == 2
        assert set(df["id"]) == {"1", "2"}
        assert set(df["name"]) == {"foo", "bar"}

    def test_nested_elements_produce_flattened_columns_with_last_segment_only(self):
        root = make_root(
            """
            <root>
                <Report>
                    <Item id="1">
                        <Detail code="A"/>
                    </Item>
                </Report>
            </root>
            """
        )
        df = parse_xml(root, "Report")
        # Full path would be "Item.id" / "Item.Detail.code", but parse_xml
        # keeps only the last dotted segment.
        assert set(df.columns) == {"id", "code"}
        assert df.iloc[0]["id"] == "1"
        assert df.iloc[0]["code"] == "A"

    def test_report_part_not_found_returns_empty_dataframe(self):
        root = make_root("<root><Report><Item id='1'/></Report></root>")
        df = parse_xml(root, "DoesNotExist")
        assert isinstance(df, pd.DataFrame)
        assert df.empty
        assert list(df.columns) == []

    def test_report_part_with_no_children_returns_empty_dataframe(self):
        # This exercises the `if start_element:` truthiness quirk: an
        # Element with zero children is falsy, so nothing is parsed even
        # though the element itself was found.
        root = make_root("<root><Report></Report></root>")
        df = parse_xml(root, "Report")
        assert df.empty

    def test_cartesian_product_across_sibling_lists(self):
        root = make_root(
            """
            <root>
                <Report>
                    <Color name="red"/>
                    <Color name="blue"/>
                    <Size val="S"/>
                    <Size val="M"/>
                </Report>
            </root>
            """
        )
        df = parse_xml(root, "Report")
        # 2 colors * 2 sizes = 4 rows
        assert len(df) == 4
        assert set(df.columns) == {"name", "val"}

    def test_duplicate_last_segment_creates_duplicate_columns(self):
        # Item.id and Item.Detail.id both collapse to "id" -> duplicate
        # column names in the final DataFrame. This documents existing
        # (possibly surprising) behavior rather than "correct" behavior.
        root = make_root(
            """
            <root>
                <Report>
                    <Item id="1">
                        <Detail id="A"/>
                    </Item>
                </Report>
            </root>
            """
        )
        df = parse_xml(root, "Report")
        assert list(df.columns).count("id") == 2

    def test_nested_report_part_path(self):
        # report_part can be an ElementTree find() path, e.g. "Section/Report"
        root = make_root(
            """
            <root>
                <Section>
                    <Report>
                        <Item id="1"/>
                    </Report>
                </Section>
            </root>
            """
        )
        df = parse_xml(root, "Section/Report")
        assert list(df.columns) == ["id"]
        assert df.iloc[0]["id"] == "1"

    def test_element_with_text_but_no_children_returns_empty_dataframe(self):
        # Text content is ignored entirely by this parser; an element with
        # only text and no child elements is treated as childless.
        root = make_root("<root><Report>some text</Report></root>")
        df = parse_xml(root, "Report")
        assert df.empty

    def test_single_child_no_attributes_produces_empty_dataframe(self):
        # Item has no attributes and no children -> _parse_xml_to_dict
        # drops it entirely (empty dict is falsy), leaving Report's dict
        # as {"Item": []}. _recursive_unpack drops the empty list too,
        # so we get a single empty record.
        root = make_root("<root><Report><Item/></Report></root>")
        df = parse_xml(root, "Report")
        assert len(df) == 1
        assert list(df.columns) == []

    def test_returns_dataframe_type(self):
        root = make_root(
            "<root><Report><Item id='1'/></Report></root>"
        )
        result = parse_xml(root, "Report")
        assert isinstance(result, pd.DataFrame)