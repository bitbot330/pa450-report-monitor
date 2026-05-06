import xml.etree.ElementTree as ET

from pa450_report_monitor.__main__ import Pa450ApiClient


class FakePa450ApiClient(Pa450ApiClient):
    def __init__(self):
        super().__init__(host="pa450.example", api_key="key")
        self.requests = []

    def _post(self, data, include_key=True):
        self.requests.append(data)
        xpath = data.get("xpath", "")
        if xpath == "/config/shared/reports/entry[@name='top-sources']":
            return ET.fromstring(
                '''
                <response status="success">
                  <result>
                    <entry name="top-sources">
                      <type><traffic-summary /></type>
                      <period>last-24-hrs</period>
                      <topn>50</topn>
                    </entry>
                  </result>
                </response>
                '''
            )
        raise AssertionError(f"unexpected xpath: {xpath}")


def test_get_custom_report_definition_uses_fixed_shared_report_path():
    client = FakePa450ApiClient()

    report_definition = client.get_custom_report_definition("top-sources")

    assert "<type>" in report_definition.xml
    assert "<period>last-24-hrs</period>" in report_definition.xml
    assert report_definition.xpath == "/config/shared/reports/entry[@name='top-sources']"
    assert [request["xpath"] for request in client.requests] == [
        "/config/shared/reports/entry[@name='top-sources']",
    ]
