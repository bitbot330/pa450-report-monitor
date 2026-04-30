import xml.etree.ElementTree as ET

from pa450_report_monitor.pa450_api import Pa450ApiClient


class FakePa450ApiClient(Pa450ApiClient):
    def __init__(self):
        super().__init__(host="pa450.example", api_key="key")
        self.requests = []

    def _post(self, data, include_key=True):
        self.requests.append(data)
        xpath = data.get("xpath", "")
        if "vsys1" in xpath:
            return ET.fromstring('<response status="success"><result /></response>')
        if "/config/shared/reports" in xpath:
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


def test_get_custom_report_definition_falls_back_to_shared_reports():
    client = FakePa450ApiClient()

    definition = client.get_custom_report_definition("vsys1", "top-sources")

    assert "<type>" in definition
    assert "<period>last-24-hrs</period>" in definition
    xpaths = [request["xpath"] for request in client.requests]
    assert xpaths == [
        "/config/devices/entry/vsys/entry[@name='vsys1']/reports/entry[@name='top-sources']",
        "/config/shared/reports/entry[@name='top-sources']",
    ]
