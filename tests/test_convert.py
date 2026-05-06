from pa450_report_monitor.report import xml_text_to_rows


def test_xml_text_to_rows_extracts_entry_children():
    xml = """
    <response status="success">
      <result>
        <entry><source>10.0.0.1</source><bytes>123</bytes></entry>
        <entry><source>10.0.0.2</source><bytes>456</bytes></entry>
      </result>
    </response>
    """

    rows = xml_text_to_rows(xml)

    assert rows == [
        {"source": "10.0.0.1", "bytes": "123"},
        {"source": "10.0.0.2", "bytes": "456"},
    ]
