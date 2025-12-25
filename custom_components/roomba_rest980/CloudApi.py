"""iRobot Cloud API implementation for retrieving pmaps and other cloud data.

Based on reverse engineering of the iRobot mobile app.
"""

from datetime import UTC, datetime
import hashlib
import hmac
import json
from json.decoder import JSONDecodeError
import logging
from pathlib import Path
from typing import Any
import urllib.parse
import uuid

import aiofiles
import aiohttp

_LOGGER = logging.getLogger(__name__)

# Debug: Save UMF data to file for analysis
DEBUG_SAVE_UMF = False
DEBUG_UMF_PATH = Path("/workspaces/ha-core/config/debug_umf_data.json")


class CloudApiError(Exception):
    """Custom exception for Cloud API errors."""


class AuthenticationError(CloudApiError):
    """Authentication related errors."""


class AWSSignatureV4:
    """AWS Signature Version 4 implementation for signing requests."""

    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        session_token: str | None = None,
    ):
        """Initialize AWS Signature V4 signer with credentials."""
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.session_token = session_token

    def _hmac_sha256(self, key: bytes, data: str) -> bytes:
        """HMAC SHA256 helper."""
        return hmac.new(key, data.encode("utf-8"), hashlib.sha256).digest()

    def _sha256_hex(self, data: str) -> str:
        """SHA256 hex helper."""
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    def _get_signature_key(self, date_stamp: str, region: str, service: str) -> bytes:
        """Generate AWS Signature V4 signing key."""
        k_date = self._hmac_sha256(f"AWS4{self.secret_access_key}".encode(), date_stamp)
        k_region = self._hmac_sha256(k_date, region)
        k_service = self._hmac_sha256(k_region, service)
        return self._hmac_sha256(k_service, "aws4_request")

    def _get_date_stamp(self, date: datetime) -> str:
        """Generate date stamp YYYYMMDD."""
        return date.strftime("%Y%m%d")

    def _get_amz_date(self, date: datetime) -> str:
        """Generate x-amz-date YYYYMMDD'T'HHMMSS'Z'."""
        return date.strftime("%Y%m%dT%H%M%SZ")

    def generate_signed_headers(
        self,
        method: str,
        service: str,
        region: str,
        host: str,
        path: str,
        query_params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        payload: str = "",
    ) -> dict[str, str]:
        """Generate AWS SigV4 signed headers for a request."""
        if query_params is None:
            query_params = {}
        if headers is None:
            headers = {}

        now = datetime.now(tz=UTC)
        amz_date = self._get_amz_date(now)
        date_stamp = self._get_date_stamp(now)

        # Step 1: HTTP Method
        http_method = method.upper()

        # Step 2: Canonical URI
        canonical_uri = urllib.parse.quote(path, safe="/")

        # Step 3: Canonical Query String
        sorted_query_keys = sorted(query_params.keys())
        canonical_query_string = "&".join(
            [
                f"{urllib.parse.quote(key, safe='~')}={urllib.parse.quote(str(query_params[key]), safe='~')}"
                for key in sorted_query_keys
            ]
        )

        # Step 4: Canonical Headers
        merged_headers = {"host": host, "x-amz-date": amz_date, **headers}

        sorted_header_keys = sorted([k.lower() for k in merged_headers])
        canonical_headers = (
            "\n".join([f"{key}:{merged_headers[key]}" for key in sorted_header_keys])
            + "\n"
        )
        signed_headers = ";".join(sorted_header_keys)

        # Step 5: Payload hash
        payload_hash = self._sha256_hex(payload)

        # Step 6: Canonical request
        canonical_request = f"{http_method}\n{canonical_uri}\n{canonical_query_string}\n{canonical_headers}\n{signed_headers}\n{payload_hash}"

        # Step 7: String to sign
        algorithm = "AWS4-HMAC-SHA256"
        credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
        canonical_request_hash = self._sha256_hex(canonical_request)

        string_to_sign = (
            f"{algorithm}\n{amz_date}\n{credential_scope}\n{canonical_request_hash}"
        )

        # Step 8: Calculate signature
        signing_key = self._get_signature_key(date_stamp, region, service)
        signature = hmac.new(
            signing_key, string_to_sign.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        # Step 9: Authorization header
        authorization_header = f"{algorithm} Credential={self.access_key_id}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}"

        final_headers = {**merged_headers, "Authorization": authorization_header}

        if self.session_token:
            final_headers["x-amz-security-token"] = self.session_token

        return final_headers


class iRobotCloudApi:
    """iRobot Cloud API client for authentication and data retrieval."""

    def __init__(
        self,
        username: str,
        password: str,
        session: aiohttp.ClientSession | None = None,
    ):
        """Initialize iRobot Cloud API client with credentials."""
        self.username = username
        self.password = password
        self.session = session or aiohttp.ClientSession()
        self._should_close_session = session is None

        # Configuration
        self.config = {"appId": str(uuid.uuid4()), "deviceId": str(uuid.uuid4())}

        # Authentication data
        self.uid = None
        self.uid_signature = None
        self.signature_timestamp = None
        self.credentials = None
        self.deployment = None
        self.robots = {}

        # Headers for requests
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "iRobot/7.16.2.140449 CFNetwork/1568.100.1.2.1 Darwin/24.0.0",
        }

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._should_close_session and self.session:
            await self.session.close()

    async def discover_endpoints(self) -> dict[str, Any]:
        """Discover deployment endpoints."""
        discovery_url = (
            "https://disc-prod.iot.irobotapi.com/v1/discover/endpoints?country_code=US"
        )

        async with self.session.get(discovery_url) as response:
            if response.status != 200:
                raise CloudApiError(f"Discovery failed: {response.status}")

            endpoints = await response.json()
            self.deployment = endpoints["deployments"][endpoints["current_deployment"]]

            _LOGGER.debug("Discovered deployment: %s", endpoints["current_deployment"])
            return endpoints

    async def login_gigya(self, api_key: str) -> dict[str, Any]:
        """Login to Gigya authentication service."""
        gigya_endpoints = await self.discover_endpoints()
        gigya = gigya_endpoints["gigya"]
        base_acc = f"https://accounts.{gigya['datacenter_domain']}/accounts."

        login_data = {
            "loginMode": "standard",
            "loginID": self.username,
            "password": self.password,
            "include": "profile,data,emails,subscriptions,preferences,",
            "includeUserInfo": "true",
            "targetEnv": "mobile",
            "source": "showScreenSet",
            "sdk": "ios_swift_1.3.0",
            "sessionExpiration": "-2",
            "apikey": api_key,
        }

        async with self.session.post(
            f"{base_acc}login",
            headers=self.headers,
            data=urllib.parse.urlencode(login_data),
        ) as response:
            response_text = await response.text()
            _LOGGER.debug("Gigya login response status: %d", response.status)
            _LOGGER.debug("Gigya login response: %s", response_text)

            try:
                login_result = json.loads(response_text)
            except JSONDecodeError as e:
                raise AuthenticationError(
                    f"Invalid JSON response from Gigya login: {response_text}"
                ) from e

            if login_result.get("errorCode", 0) != 0:
                raise AuthenticationError(f"Gigya login failed: {login_result}")

            # Check if required keys exist
            if "UID" not in login_result:
                raise AuthenticationError(
                    f"Missing 'UID' in Gigya response: {login_result}"
                )

            if "UIDSignature" not in login_result:
                raise AuthenticationError(
                    f"Missing 'UIDSignature' in Gigya response: {login_result}"
                )

            if "signatureTimestamp" not in login_result:
                raise AuthenticationError(
                    f"Missing 'signatureTimestamp' in Gigya response: {login_result}"
                )

            self.uid = login_result["UID"]
            self.uid_signature = login_result["UIDSignature"]
            self.signature_timestamp = login_result["signatureTimestamp"]

            _LOGGER.debug(
                "Gigya login successful for: %s", login_result["profile"]["email"]
            )
            return login_result

    async def login_irobot(self) -> dict[str, Any]:
        """Login to iRobot cloud service."""
        if not self.deployment:
            await self.discover_endpoints()

        login_data = {
            "app_id": f"IOS-{self.config['appId']}",
            "app_info": {
                "device_id": f"IOS-{self.config['deviceId']}",
                "device_name": "iPhone",
                "language": "en_US",
                "version": "7.16.2",
            },
            "assume_robot_ownership": "0",
            "authorizer_params": {"devices_per_token": 5},
            "gigya": {
                "signature": self.uid_signature,
                "timestamp": self.signature_timestamp,
                "uid": self.uid,
            },
            "multiple_authorizer_token_support": True,
            "push_info": {
                "platform": "APNS",
                "push_token": "eb6ce9172e5fde9fe4c9a2a945b35709f73fb8014eb7449d944c6c89eeb472fb",
                "supported_push_types": [
                    "mkt_mca",
                    "cr",
                    "cse",
                    "bf",
                    "uota",
                    "crae",
                    "ae",
                    "crbf",
                    "pm",
                    "teom",
                    "te",
                    "dt",
                    "tr",
                    "ir",
                    "mca",
                    "mca_pn_hd",
                    "shcp",
                    "shar",
                    "shas",
                    "scs",
                    "lv",
                    "ce",
                    "ri",
                    "fu",
                ],
            },
            "skip_ownership_check": "0",
        }

        async with self.session.post(
            f"{self.deployment['httpBase']}/v2/login",
            headers={"Content-Type": "application/json"},
            json=login_data,
        ) as response:
            response_text = await response.text()
            _LOGGER.debug("iRobot login response status: %d", response.status)
            _LOGGER.debug("iRobot login response: %s", response_text)

            try:
                login_result = json.loads(response_text)
            except JSONDecodeError as e:
                raise AuthenticationError(
                    f"Invalid JSON response from iRobot login: {response_text}"
                ) from e

            if login_result.get("errorCode"):
                raise AuthenticationError(f"iRobot login failed: {login_result}")

            # Check if required keys exist
            if "credentials" not in login_result:
                msg = login_result["errorMessage"] or login_result
                if "mqtt slot" in msg:
                    msg = f"The cloud authentication has been rate-limited. Try closing the iRobot app or trying again later. ({login_result['errorMessage']})"
                raise AuthenticationError(f"{msg}")

            if "robots" not in login_result:
                raise AuthenticationError(
                    f"Missing 'robots' in login response: {login_result}"
                )

            self.credentials = login_result["credentials"]
            self.robots = login_result["robots"]

            _LOGGER.debug("iRobot login successful, found %d robots", len(self.robots))
            return login_result

    async def authenticate(self) -> dict[str, Any]:
        """Complete authentication flow."""
        # Discover endpoints first
        endpoints = await self.discover_endpoints()

        # Login to Gigya
        await self.login_gigya(endpoints["gigya"]["api_key"])

        # Login to iRobot
        return await self.login_irobot()

    async def _aws_request(
        self, url: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Make an authenticated AWS request."""
        if not self.credentials:
            raise AuthenticationError("Not authenticated. Call authenticate() first.")

        region = self.credentials["CognitoId"].split(":")[0]

        # Parse URL
        parsed_url = urllib.parse.urlparse(url)

        # Create AWS signer
        signer = AWSSignatureV4(
            access_key_id=self.credentials["AccessKeyId"],
            secret_access_key=self.credentials["SecretKey"],
            session_token=self.credentials["SessionToken"],
        )

        # Generate signed headers
        query_params = params or {}
        signed_headers = signer.generate_signed_headers(
            method="GET",
            service="execute-api",
            region=region,
            host=parsed_url.netloc,
            path=parsed_url.path,
            query_params=query_params,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "user-agent": "aws-sdk-iOS/2.27.6 iOS/18.0.1 en_US",
            },
            payload="",
        )

        # Build final URL with query parameters
        if query_params:
            query_string = urllib.parse.urlencode(query_params)
            final_url = f"{url}?{query_string}"
        else:
            final_url = url

        async with self.session.get(final_url, headers=signed_headers) as response:
            if response.status != 200:
                if response.status == 403:
                    await self.authenticate()
                    _LOGGER.info("Reauthenticating API")
                    return await self._aws_request(url, params)
                raise CloudApiError(f"AWS request failed: {response.status}")

            return await response.json()

    async def get_mission_history(self, blid: str) -> dict[str, Any]:
        """Get mission history for a robot."""
        url = f"{self.deployment['httpBaseAuth']}/v1/{blid}/missionhistory"
        params = {
            "app_id": f"IOS-{self.config['appId']}",
            "filterType": "omit_quickly_canceled_not_scheduled",
            "supportedDoneCodes": "dndEnd,returnHomeEnd",
        }

        return await self._aws_request(url, params)

    async def get_pmaps(self, blid: str) -> list[dict[str, Any]]:
        """Get persistent maps (pmaps) for a robot."""
        url = f"{self.deployment['httpBaseAuth']}/v1/{blid}/pmaps"
        params = {"visible": "true", "activeDetails": "2"}

        return await self._aws_request(url, params)

    async def get_pmap_umf(
        self, blid: str, pmap_id: str, version_id: str
    ) -> dict[str, Any]:
        """Get UMF (Unified Map Format) data for a specific pmap."""
        url = f"{self.deployment['httpBaseAuth']}/v1/{blid}/pmaps/{pmap_id}/versions/{version_id}/umf"
        params = {"activeDetails": "2"}

        umf_data = await self._aws_request(url, params)

        # Save UMF data for debugging/camera development
        # TODO: Enable during development.
        # await self._save_umf_data_for_debug(pmap_id, umf_data)

        return umf_data

    async def get_favorites(self) -> dict[str, Any]:
        """Get favorite cleaning routines."""
        url = f"{self.deployment['httpBaseAuth']}/v1/user/favorites"
        return await self._aws_request(url)

    async def get_schedules(self) -> dict[str, Any]:
        """Get automated cleaning routines."""
        url = f"{self.deployment['httpBaseAuth']}/v1/user/automations"
        return await self._aws_request(url)

    async def get_robot_data(self, blid: str) -> dict[str, Any]:
        """Get comprehensive robot data including pmaps and mission history."""
        if blid not in self.robots:
            raise CloudApiError(f"Robot {blid} not found in authenticated robots")

        robot_data = {
            "robot_info": self.robots[blid],
            "mission_history": await self.get_mission_history(blid),
            "pmaps": await self.get_pmaps(blid),
        }

        # Get UMF data for active pmaps
        for pmap in robot_data["pmaps"]:
            if pmap.get("active_pmapv_id"):
                try:
                    robot_data[f"pmap_umf_{pmap['pmap_id']}"] = await self.get_pmap_umf(
                        blid, pmap["pmap_id"], pmap["active_pmapv_id"]
                    )
                except CloudApiError as e:
                    _LOGGER.warning(
                        "Failed to get UMF for pmap %s: %s", pmap["pmap_id"], e
                    )

        return robot_data

    retry_count = 0

    async def get_all_robots_data(self) -> dict[str, dict[str, Any]]:
        """Get data for all authenticated robots."""
        if not self.robots:
            if self.retry_count == 3:
                raise CloudApiError("No robots found. Authenticate first.")
            self.retry_count += 1
            await self.authenticate()
            return await self.get_all_robots_data()

        all_data = {}
        for blid in self.robots:
            try:
                all_data[blid] = await self.get_robot_data(blid)
                _LOGGER.debug("Retrieved data for robot %s", blid)
            except CloudApiError as e:
                _LOGGER.error("Failed to get data for robot %s: %s", blid, e)
                all_data[blid] = {"error": str(e)}

        all_data["schedules"] = await self.get_schedules()
        return all_data

    async def _save_umf_data_for_debug(
        self, pmap_id: str, umf_data: dict[str, Any]
    ) -> None:
        """Save UMF data to file for debugging purposes."""
        if not DEBUG_SAVE_UMF:
            return

        try:
            # Create debug data structure
            debug_data = {
                "timestamp": datetime.now(UTC).isoformat(),
                "pmap_id": pmap_id,
                "umf_data": umf_data,
            }

            # Load existing data if file exists
            existing_data = []
            if DEBUG_UMF_PATH.exists():
                try:
                    async with aiofiles.open(DEBUG_UMF_PATH) as f:
                        content = await f.read()
                        existing_data = json.loads(content)
                        if not isinstance(existing_data, list):
                            existing_data = [existing_data]
                except (JSONDecodeError, OSError):
                    existing_data = []

            # Add new data
            existing_data.append(debug_data)

            # Keep only the latest 10 entries to avoid huge files
            if len(existing_data) > 10:
                existing_data = existing_data[-10:]

            # Save back to file
            async with aiofiles.open(DEBUG_UMF_PATH, "w") as f:
                await f.write(json.dumps(existing_data, indent=2, default=str))

            _LOGGER.debug("Saved UMF data for pmap %s to %s", pmap_id, DEBUG_UMF_PATH)

        except (OSError, Exception) as e:
            _LOGGER.warning("Failed to save UMF debug data: %s", e)
