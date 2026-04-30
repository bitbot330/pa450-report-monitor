from __future__ import annotations

import ssl
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass


class Pa450ApiError(RuntimeError):
    pass


@dataclass
class Pa450ApiClient:
    host: str
    verify_tls: bool = True
    api_key: str | None = None

    @property
    def api_url(self) -> str:
        host = self.host
        if not host.startswith(("http://", "https://")):
            host = f"https://{host}"
        return f"{host.rstrip('/')}/api/"

    def _ssl_context(self):
        if self.verify_tls:
            return None
        return ssl._create_unverified_context()

    def _post(self, data: dict[str, str], include_key: bool = True) -> ET.Element:
        encoded = urllib.parse.urlencode(data).encode("utf-8")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        if include_key and self.api_key:
            headers["X-PAN-KEY"] = self.api_key
        request = urllib.request.Request(self.api_url, data=encoded, headers=headers, method="POST")
        with urllib.request.urlopen(request, context=self._ssl_context(), timeout=60) as response:
            body = response.read()
        try:
            root = ET.fromstring(body)
        except ET.ParseError as exc:
            raise Pa450ApiError(f"PAN-OS API returned invalid XML: {exc}") from exc
        if root.attrib.get("status") == "error":
            raise Pa450ApiError(ET.tostring(root, encoding="unicode"))
        return root

    def keygen(self, username: str, password: str) -> str:
        root = self._post(
            {"type": "keygen", "user": username, "password": password},
            include_key=False,
        )
        key = root.findtext(".//key")
        if not key:
            raise Pa450ApiError("API key not found in keygen response")
        self.api_key = key
        return key

    def get_custom_report_definition(self, vsys: str, report_name: str) -> str:
        xpath = f"/config/devices/entry/vsys/entry[@name='{vsys}']/reports/entry[@name='{report_name}']"
        root = self._post({"type": "config", "action": "get", "xpath": xpath})
        entry = root.find(".//entry")
        if entry is None:
            raise Pa450ApiError(f"Custom report not found: vsys={vsys}, report={report_name}")
        return "".join(ET.tostring(child, encoding="unicode") for child in list(entry))

    def enqueue_dynamic_report(self, report_job_name: str, report_definition_xml: str) -> str:
        root = self._post(
            {
                "type": "report",
                "reporttype": "dynamic",
                "reportname": report_job_name,
                "cmd": report_definition_xml,
            }
        )
        job_id = root.findtext(".//job")
        if not job_id:
            raise Pa450ApiError("Job ID not found in report enqueue response")
        return job_id

    def get_report_result(self, job_id: str) -> ET.Element:
        return self._post({"type": "report", "action": "get", "job-id": job_id})

    def wait_for_report_result(self, job_id: str, attempts: int = 12, delay_seconds: int = 10) -> ET.Element:
        last_root: ET.Element | None = None
        for _ in range(attempts):
            root = self.get_report_result(job_id)
            last_root = root
            if root.find(".//entry") is not None or root.findtext(".//status") in {"FIN", "Completed"}:
                return root
            time.sleep(delay_seconds)
        if last_root is None:
            raise Pa450ApiError("No report result returned")
        return last_root
