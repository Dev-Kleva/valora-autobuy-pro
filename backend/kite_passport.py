import requests
import json
import os
import shutil
import shlex
import subprocess
from typing import Dict, Optional, List
import logging
from dotenv import load_dotenv

backend_dir = os.path.dirname(__file__)
root_env = os.path.join(backend_dir, os.pardir, ".env")
backend_env = os.path.join(backend_dir, ".env")
load_dotenv(root_env)
load_dotenv(backend_env, override=True)

logger = logging.getLogger(__name__)

class KitePassport:
    """
    Wrapper for Kite Agent Passport API operations.
    Provides programmatic access to Passport API for agent automation.
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or os.getenv("KITE_PASSPORT_BASE_URL") or "https://passport.dev.gokite.ai"
        self.wsl_distro = None
        self.wsl_user = None
        self.wsl_exe = None
        self._load_config()
        self.kpass_path = self._find_kpass_executable()
        print(f"Debug: resolved kpass path = {self.kpass_path}")

    def _load_config(self):
        """Load Passport configuration from .kite-passport directory."""
        print("Debug: in _load_config")
        print(f"Debug: cwd = {os.getcwd()}")
        config_dir = os.path.join(os.getcwd(), ".kite-passport")
        config_file = os.path.join(config_dir, "config.json")
        print(f"Debug: config_file = {config_file}")
        print(f"Debug: exists = {os.path.exists(config_file)}")

        if not os.path.exists(config_file):
            raise RuntimeError(
                "Kite Passport not configured. Please run: "
                "curl -fsSL https://agentpassport.ai/install.sh | bash"
            )

        try:
            with open(config_file, 'r') as f:
                self.config = json.load(f)
            self.jwt_token = self.config.get("jwt")
            if not self.jwt_token:
                raise RuntimeError("No JWT token found in Passport config")
        except Exception as e:
            raise RuntimeError(f"Failed to load Passport config: {str(e)}")

    def _decode_wsl_output(self, raw: Optional[bytes]) -> str:
        """Decode wsl.exe output, handling UTF-16-LE with null bytes."""
        if raw is None:
            return ""
        if b"\x00" in raw:
            try:
                return raw.decode('utf-16-le', errors='ignore').strip()
            except UnicodeDecodeError:
                return raw.decode('utf-16', errors='ignore').strip()
        try:
            return raw.decode('utf-8', errors='ignore').strip()
        except UnicodeDecodeError:
            return raw.decode('latin-1', errors='ignore').strip()

    def _find_wsl_executable(self) -> Optional[str]:
        """Find the WSL executable even when System32 redirection hides it."""
        wsl_exe = shutil.which("wsl")
        if wsl_exe:
            return wsl_exe

        windows_dir = os.environ.get("SYSTEMROOT") or os.environ.get("WINDIR") or "C:\\Windows"
        candidates = [
            os.path.join(windows_dir, "System32", "wsl.exe"),
            os.path.join(windows_dir, "Sysnative", "wsl.exe"),
            os.path.join(windows_dir, "SysWOW64", "wsl.exe"),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None

    def _get_wsl_users(self, wsl_exe: str, distro: str) -> List[Dict[str, str]]:
        """Enumerate non-system users inside a WSL distro."""
        try:
            result = subprocess.run(
                [wsl_exe, "-d", distro, "bash", "-lc",
                 "awk -F: '$3>=1000 && $1 != \"nobody\" {print $1 \"\x1f\" $6}' /etc/passwd"],
                capture_output=True,
                timeout=10,
            )
            output = self._decode_wsl_output(result.stdout)
            users = []
            for line in output.splitlines():
                if "\x1f" not in line:
                    continue
                username, homedir = line.split("\x1f", 1)
                users.append({"name": username.strip(), "home": homedir.strip()})
            return users
        except (subprocess.SubprocessError, OSError):
            return []

    def _find_kpass_in_wsl(self, wsl_exe: str, distro: str, user: Optional[str] = None) -> Optional[str]:
        """Find a kpass executable inside a WSL distro and optional user session."""
        cmd = [wsl_exe, "-d", distro]
        if user:
            cmd += ["-u", user]
        cmd += ["bash", "-lc", "command -v kpass"]
        try:
            result = subprocess.run(cmd, capture_output=True, timeout=10)
            if result.returncode == 0:
                return self._decode_wsl_output(result.stdout)
        except (subprocess.SubprocessError, OSError):
            pass
        return None

    def _find_kpass_in_wsl_home(self, wsl_exe: str, distro: str, home_dir: str) -> Optional[str]:
        """Check common install locations under a WSL home directory."""
        paths = [
            os.path.join(home_dir, ".local", "bin", "kpass"),
            os.path.join(home_dir, ".kpass", "bin", "kpass"),
        ]
        for candidate in paths:
            cmd = [wsl_exe, "-d", distro, "bash", "-lc", f"if [ -x '{candidate}' ]; then printf '%s' '{candidate}'; fi"]
            try:
                result = subprocess.run(cmd, capture_output=True, timeout=10)
                candidate_path = self._decode_wsl_output(result.stdout)
                if candidate_path:
                    return candidate_path
            except (subprocess.SubprocessError, OSError):
                pass
        return None

    def _find_kpass_executable(self) -> str:
        """Resolve the kpass executable path from the current environment."""
        import platform
        is_windows = platform.system() == "Windows"
        is_wsl = False

        try:
            with open('/proc/version', 'r') as f:
                is_wsl = 'microsoft' in f.read().lower()
        except OSError:
            pass

        env_path = os.getenv("KITE_PASSPORT_CLI_PATH")
        if env_path and os.path.isfile(env_path) and os.access(env_path, os.X_OK):
            return env_path

        for candidate_name in ("kpass", "kpass.exe"):
            candidate = shutil.which(candidate_name)
            if candidate:
                return candidate

        possible_paths = [
            os.path.expanduser("~/.local/bin/kpass"),
            os.path.expanduser("~/.local/bin/kpass.exe"),
            os.path.expanduser("~/.kpass/bin/kpass"),
            os.path.expanduser("~/.kpass/bin/kpass.exe"),
            "/usr/local/bin/kpass",
            "/usr/bin/kpass",
        ]
        for path in possible_paths:
            if path and os.path.isfile(path) and os.access(path, os.X_OK):
                return path

        # If running on Windows, try to see whether kpass is installed inside WSL.
        if is_windows:
            wsl_exe = self._find_wsl_executable()
            self.wsl_exe = wsl_exe
            if wsl_exe:
                try:
                    distro_result = subprocess.run(
                        [wsl_exe, "-l", "-q"],
                        capture_output=True,
                        timeout=10,
                    )
                    distro_stdout = self._decode_wsl_output(distro_result.stdout)
                    distros = [line.strip() for line in distro_stdout.splitlines() if line.strip() and not line.strip().startswith("docker-")]
                except (subprocess.SubprocessError, OSError):
                    distros = []

                env_user = os.getenv("KITE_PASSPORT_WSL_USER")
                candidate_users = [env_user] if env_user else []

                for distro in distros:
                    # First try the explicitly configured WSL user.
                    for user in candidate_users:
                        if not user:
                            continue
                        wsl_kpass = self._find_kpass_in_wsl(wsl_exe, distro, user)
                        if wsl_kpass:
                            self.wsl_distro = distro
                            self.wsl_user = user
                            return wsl_kpass

                    distro_users = self._get_wsl_users(wsl_exe, distro)
                    for user_info in distro_users:
                        user = user_info.get("name")
                        if not user or user in candidate_users:
                            continue
                        wsl_kpass = self._find_kpass_in_wsl(wsl_exe, distro, user)
                        if wsl_kpass:
                            self.wsl_distro = distro
                            self.wsl_user = user
                            return wsl_kpass

                        home_dir = user_info.get("home")
                        if home_dir:
                            home_path = self._find_kpass_in_wsl_home(wsl_exe, distro, home_dir)
                            if home_path:
                                self.wsl_distro = distro
                                self.wsl_user = user
                                return home_path

                    # Finally try the default distro shell.
                    wsl_kpass = self._find_kpass_in_wsl(wsl_exe, distro, None)
                    if wsl_kpass:
                        self.wsl_distro = distro
                        return wsl_kpass

                    for user_info in distro_users:
                        home_dir = user_info.get("home")
                        if home_dir:
                            home_path = self._find_kpass_in_wsl_home(wsl_exe, distro, home_dir)
                            if home_path:
                                self.wsl_distro = distro
                                self.wsl_user = user_info.get("name")
                                return home_path

        if is_windows or is_wsl:
            wsl_paths = [
                os.path.expanduser("~/.local/bin/kpass"),
                os.path.expanduser("~/.kpass/bin/kpass"),
                "/usr/local/bin/kpass",
                "/usr/bin/kpass",
            ]
            for wsl_path in wsl_paths:
                if wsl_path and os.path.isfile(wsl_path) and os.access(wsl_path, os.X_OK):
                    return wsl_path

        raise RuntimeError(
            "kpass CLI is not installed or not found in PATH. "
            "Install Kite Passport CLI and ensure it is available as `kpass` or set KITE_PASSPORT_CLI_PATH."
        )

    def _api_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make authenticated API request to Passport service."""
        tried = []
        endpoints = [endpoint] + self._get_fallback_endpoints(endpoint)

        for endpoint_to_try in endpoints:
            url = f"{self.base_url}{endpoint_to_try}"
            headers = {
                "Authorization": f"Bearer {self.jwt_token}",
                "Content-Type": "application/json"
            }

            try:
                if method == "GET":
                    response = requests.get(url, headers=headers, params=data)
                elif method == "POST":
                    response = requests.post(url, headers=headers, json=data)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                response.raise_for_status()
                try:
                    return response.json()
                except ValueError:
                    return {"status": response.text}
            except requests.exceptions.HTTPError as http_err:
                status_code = getattr(http_err.response, 'status_code', None)
                tried.append((endpoint_to_try, status_code, str(http_err)))
                if status_code == 404:
                    continue
                logger.error(f"API request failed for {endpoint_to_try}: {http_err}")
                raise RuntimeError(f"Passport API request failed: {str(http_err)}")
            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed for {endpoint_to_try}: {e}")
                raise RuntimeError(f"Passport API request failed: {str(e)}")

        raise RuntimeError(
            f"Passport API request failed for endpoints: {tried}. "
            f"Check KITE_PASSPORT_BASE_URL and whether Passport API paths are correct."
        )

    def _get_fallback_endpoints(self, endpoint: str) -> List[str]:
        fallback_map = {
            "/me": ["/api/v1/me", "/auth/me", "/user/me", "/api/me"],
            "/health": ["/api/v1/health", "/status", "/api/health", "/api/status"],
            "/wallet/balance": ["/api/v1/wallet/balance", "/balance", "/api/wallet/balance"],
            "/agents": ["/api/v1/agents", "/api/agents", "/agent/list"],
            "/services": ["/api/v1/services", "/api/services", "/service/list"],
            "/agent/execute": ["/api/v1/agent/execute", "/execute", "/api/agent/execute"],
        }
        return fallback_map.get(endpoint, [])

    def get_version(self) -> str:
        """Return kpass CLI version info."""
        try:
            response = self._run_kpass(["version"])
            if isinstance(response, dict) and "stdout" in response:
                return response["stdout"]
            if isinstance(response, str):
                return response
            return json.dumps(response)
        except Exception as e:
            raise RuntimeError(f"Failed to determine kpass version: {str(e)}")

    def _run_kpass(self, args: List[str], input_data: Optional[str] = None) -> Dict:
        """
        Run kpass CLI commands and return structured output.
        Supports agent execution commands.
        Uses WSL on Windows systems when kpass is installed in WSL.
        """
        if not args:
            return {"error": "No command specified"}

        # Check if we're on Windows and the resolved path points into WSL.
        import platform
        is_windows = platform.system() == "Windows"

        if is_windows and self.kpass_path.startswith("/"):
            wsl_exe = self.wsl_exe or shutil.which("wsl")
            if not wsl_exe:
                raise RuntimeError("WSL executable not found while attempting to run kpass in WSL.")

            cmd = [wsl_exe]
            if self.wsl_distro:
                cmd += ["-d", self.wsl_distro]
            if self.wsl_user:
                cmd += ["-u", self.wsl_user]
            cmd += ["bash", "-lc", shlex.join([self.kpass_path] + args)]
        else:
            cmd = [self.kpass_path] + args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env=os.environ,
            )
        except FileNotFoundError as e:
            raise RuntimeError(f"kpass CLI not found: {e}")
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"kpass CLI timed out: {e}")

        if result.returncode != 0:
            stderr = result.stderr.strip() or result.stdout.strip()
            raise RuntimeError(f"kpass command failed ({result.returncode}): {stderr}")

        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "returncode": result.returncode,
            }

    def _parse_session_params(self, args: List[str]) -> Dict:
        """Parse session creation parameters."""
        params = {}
        i = 0
        while i < len(args):
            if args[i].startswith("--"):
                key = args[i][2:]  # Remove --
                if i + 1 < len(args) and not args[i + 1].startswith("--"):
                    params[key] = args[i + 1]
                    i += 2
                else:
                    i += 1
            else:
                i += 1
        return params

    def _parse_agent_params(self, args: List[str]) -> Dict:
        """Parse agent registration parameters."""
        params = {"name": args[0] if args else "AutoBuy Agent"}
        i = 1
        while i < len(args):
            if args[i] == "--description" and i + 1 < len(args):
                params["description"] = args[i + 1]
                i += 2
            else:
                i += 1
        return params

    # Authentication & User Management
    def signup_init(self, email: str) -> Dict:
        """Initialize signup process with email."""
        return self._api_request("POST", "/api/v1/auth/signup/init", {"email": email})

    def signup_poll(self, code: str) -> Dict:
        """Poll for signup completion with verification code."""
        return self._api_request("POST", "/api/v1/auth/signup/poll", {"code": code})

    def signup_exchange(self, code: str) -> Dict:
        """Exchange verification code for access token."""
        return self._api_request("POST", "/api/v1/auth/signup/exchange", {"code": code})

    def login_init(self) -> Dict:
        """Initialize login process."""
        return self._api_request("POST", "/api/v1/auth/login/init")

    def login_verify(self, code: str) -> Dict:
        """Verify login with code."""
        return self._api_request("POST", "/api/v1/auth/login/verify", {"code": code})

    def get_user_info(self) -> Dict:
        """Get current user information."""
        return self._api_request("GET", "/me")

    # Wallet Operations
    def get_wallet_balance(self) -> Dict:
        """Get wallet balance information via kpass CLI."""
        return self._run_kpass(["wallet", "balance"])

    def send_payment(self, to_address: str, amount: str, asset: str = 'USDC') -> Dict:
        """Send payment from wallet."""
        return self._api_request("POST", "/api/v1/wallet/send", {
            "to": to_address,
            "amount": amount,
            "asset": asset
        })

    # Agent Management
    def register_agent(self, name: str, description: str) -> Dict:
        """Register this application as a Kite agent."""
        return self._api_request("POST", "/api/v1/agents", {
            "name": name,
            "description": description
        })

    def list_agents(self) -> Dict:
        """List registered agents."""
        return self._api_request("GET", "/api/v1/agents")

    # Session Management
    def create_session(self, *args, **kwargs):
        raise RuntimeError(
            "Passport no longer supports session-based API. "
            "Use agent-based execution via kpass (agent model)."
        )

    def get_session_status(self, *args, **kwargs):
        raise RuntimeError(
            "Passport no longer supports session-based API. "
            "Use agent-based execution via kpass (agent model)."
        )

    def list_sessions(self, *args, **kwargs):
        raise RuntimeError(
            "Passport no longer supports session-based API. "
            "Use agent-based execution via kpass (agent model)."
        )

    def use_session(self, *args, **kwargs):
        raise RuntimeError(
            "Passport no longer supports session-based API. "
            "Use agent-based execution via kpass (agent model)."
        )

    def list_user_sessions(self, *args, **kwargs):
        raise RuntimeError(
            "Passport no longer supports session-based API. "
            "Use agent-based execution via kpass (agent model)."
        )

    # Service Discovery
    def discover_services(self, query: Optional[str] = None,
                         payment_approach: Optional[str] = None,
                         asset: Optional[str] = None,
                         limit: int = 10) -> Dict:
        """
        Discover available services on Kite network.

        Args:
            query: Search query for services
            payment_approach: Filter by payment method
            asset: Filter by payment asset
            limit: Maximum results to return
        """
        params = {"limit": limit}
        if query:
            params["query"] = query
        if payment_approach:
            params["payment_approach"] = payment_approach
        if asset:
            params["asset"] = asset

        return self._api_request("GET", "/api/v1/services", params)

    def get_service_details(self, service_id: str) -> Dict:
        """Get detailed information about a specific service."""
        return self._api_request("GET", f"/api/v1/services/{service_id}")

    # Agent Execution (for automated payments)
    def execute_agent_request(self, service_query: str, payment_amount: float,
                            payment_asset: str, recipient_address: str,
                            user_address: Optional[str] = None,
                            parameters: Optional[Dict] = None) -> Dict:
        """
        Execute a paid request through Passport using the Passport wallet CLI.
        This uses `kpass wallet send` for direct stablecoin transfers.

        Args:
            service_query: Description of the payment action (for logging)
            payment_amount: Payment amount in stablecoins
            payment_asset: Asset symbol (e.g., 'USDC')
            recipient_address: Recipient wallet address
            user_address: Wallet address of the payer (optional)
            parameters: Additional request parameters
        """
        import time

        try:
            # Build scoped execution parameters
            execution_params = {
                "service": service_query,
                "amount": str(payment_amount),
                "asset": payment_asset,
                "recipient": recipient_address,
                "user_address": user_address,
                "timestamp": int(time.time()),
            }
            if parameters:
                execution_params.update(parameters)

            # Execute via kpass wallet send using Passport wallet credentials.
            # Passport agent/workflow execution for direct transfers is not available
            # through the deprecated `agent:execute` flags, so use wallet send instead.
            # Use --no-interactive to prevent waiting for user confirmation in automated flows.
            args = [
                "wallet", "send",
                "--to", recipient_address,
                "--amount", f"{payment_amount:.6f}",
                "--asset", payment_asset,
                "--no-interactive",
                "--output", "json",
            ]

            result = self._run_kpass(args)

            # Parse result for transaction hash and status
            tx_hash = result.get("tx_hash") or result.get("transaction_hash")
            if tx_hash:
                return {
                    "tx_hash": tx_hash,
                    "status": "success",
                    "recipient": recipient_address,
                    "amount": payment_amount,
                    "asset": payment_asset,
                    "message": f"Passport agent executed: {service_query}",
                    "scoped_controls": execution_params,
                    "execution_result": result,
                }
            else:
                # If no tx_hash, it might be pending or failed
                return {
                    "status": "pending" if "pending" in str(result).lower() else "error",
                    "recipient": recipient_address,
                    "amount": payment_amount,
                    "asset": payment_asset,
                    "message": f"Passport agent request submitted: {service_query}",
                    "scoped_controls": execution_params,
                    "execution_result": result,
                    "error": result.get("error") or "No transaction hash returned",
                }

        except Exception as e:
            raise Exception(f"Passport agent execution failed: {str(e)}")

    def discover_services(self, query: str, payment_approach: str = "wallet") -> Dict:
        """
        Discover available services matching a query.

        Args:
            query: Search query for services
            payment_approach: Payment approach (wallet, session, etc.)
        """
        params = {
            "query": query,
            "payment_approach": payment_approach
        }
        return self._api_request("GET", "/services", params)

    # Health & Status
    def check_health(self) -> Dict:
        """Check Kite network health."""
        return self._api_request("GET", "/health")

# Global instance for easy access
# _passport_instance = None

def get_passport(base_url: Optional[str] = None) -> KitePassport:
    """Get or create KitePassport instance."""
    # global _passport_instance
    # if _passport_instance is None:
    #     # Use provided base_url, or fallback to environment variable
    #     if base_url is None:
    #         base_url = os.getenv("KITE_PASSPORT_BASE_URL")
    #     _passport_instance = KitePassport(base_url)
    # return _passport_instance
    if base_url is None:
        base_url = os.getenv("KITE_PASSPORT_BASE_URL")
    return KitePassport(base_url)