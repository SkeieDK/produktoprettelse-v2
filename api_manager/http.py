import requests
import json
from typing import Any, Dict, Optional
import logging
from urllib.parse import quote


class HTTPClient:
    def __init__(self, api_key: str, logger: logging.Logger, api_username: str = ""):
        self.api_key = api_key
        self.api_username = api_username
        self.logger = logger

    def _create_auth_string(self) -> str:
        import base64
        auth_text = f":{self.api_key}"
        return base64.b64encode(auth_text.encode("utf-8")).decode("utf-8")

    def request(self, url: str, params: Optional[Dict[str, Any]] = None, method: str = "GET", json_data: Optional[Dict] = None, timeout: int = 30) -> Dict:
        """Perform an HTTP request with basic auth and JSON handling.

        This wraps underlying `requests` calls and raises Exceptions on error.
        """
        auth_string = self._create_auth_string()
        headers = {
            'accept': 'text/plain',
            'Authorization': f'Basic {auth_string}'
        }
        try:
            # Debug logging for request details (avoid logging auth)
            self.logger.debug(f"HTTP Request: method={method} url={url} params={params} json_data={'<redacted>' if json_data else None}")
            # ensure quoting appears only once
            url = quote(url, safe=':/')
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=timeout)
            elif method == "POST":
                headers['Content-Type'] = 'application/json'
                response = requests.post(url, headers=headers, params=params, json=json_data, timeout=timeout)
            elif method == "PUT":
                headers['Content-Type'] = 'application/json'
                response = requests.put(url, headers=headers, params=params, json=json_data, timeout=timeout)
            elif method == "PATCH":
                headers['Content-Type'] = 'application/json'
                response = requests.patch(url, headers=headers, params=params, json=json_data, timeout=timeout)
            elif method == "DELETE":
                headers['Content-Type'] = 'application/json'
                response = requests.delete(url, headers=headers, params=params, json=json_data, timeout=timeout)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            self.logger.debug(f"HTTP Response: url={url} status={response.status_code}")
            if not response.content:
                return {}
            return response.json()
        except requests.exceptions.RequestException as e:
            # Provide maximum context for errors
            self.logger.error(f"HTTP request failed: method={method} url={url} params={params} error={e}")
            raise
        except json.JSONDecodeError as e:
            # Log the raw response content for debugging malformed JSON
            try:
                self.logger.error(f"Failed to parse JSON response: {e}; Response text: {response.text}")
            except Exception:
                self.logger.error(f"Failed to parse JSON response: {e}; Could not access response text")
            raise
