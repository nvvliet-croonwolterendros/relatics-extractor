import requests
import xml.etree.ElementTree as ET
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class TokenRequestError(Exception):
    """Raised when token retrieval fails."""

class APIRequestError(Exception):
    """Raised when the API call fails."""

class XMLParseError(Exception):
    """Raised when XML parsing fails."""

class RelaticsClient:
    """Client for making OAuth2 get requests to relatics."""
    
    def __init__(self, client_id: str, client_secret: str, environment: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.environment = environment
    
    def get_request(self, workspace_id: str, operation: str, parameters: Dict[str, str] = {}) -> ET.Element:
        """
        Executes a GET request to the Relatics DataExchange API.

        Args:
            workspace_id: Workspace identifier
            operation: API operation name
            parameters: Query parameters

        Returns:
            Parsed XML root element
        """
        api_endpoint = f"https://{self.environment}.relaticsonline.com/DataExchange/{workspace_id}/{operation}"
        
        access_token, token_type = self._get_token()
        
        headers = {
            "Authorization": f"{token_type} {access_token}",
            "Content-Type": "application/json",
        }
        
        body = {
            "Parameters": parameters
        }
        
        try:
            api_response = requests.get(api_endpoint, headers=headers, json=body)
        except requests.RequestException as e:
            raise APIRequestError(f"API Request failed: {str(e)}") from e
        
        if api_response.status_code != 200:
            raise APIRequestError(f"API request failed with status code {api_response.status_code}: {api_response.text}")
                
        try:
            return ET.fromstring(api_response.content)
        except ET.ParseError as e:
            raise XMLParseError("Invalid XML in API response") from e
    
    def _get_token(self) -> Tuple[str,str]:
        """Retrieves OAuth2 token."""
        
        token_endpoint = f"https://{self.environment}.relaticsonline.com/oauth2/token"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded"
        }

        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        
        try:
            token_response = requests.post(token_endpoint, data=data, headers=headers)
        except requests.RequestException as e:
            raise TokenRequestError("Error while requesting token") from e
            
        if token_response.status_code != 200:
            raise TokenRequestError(f"Token request failed with status code {token_response.status_code}: {token_response.text}")

        token_json = token_response.json()
        access_token = token_json.get('access_token')
        token_type = token_json.get('token_type')

        if not access_token or not token_type:
            raise TokenRequestError("Missing access_token or token_type in response")
        
        return access_token, token_type 