"""Input column mapping used by all readers."""

from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class InputColumns:
    """Mapping for input columns."""

    IP_ADDRESS: ClassVar[str] = "address"
    PORT: ClassVar[str] = "port"
    NETWORK: ClassVar[str] = "network"
    TIMESTAMP: ClassVar[str] = "handshake_timestamp"
    SERVICES: ClassVar[str] = "services"
    BLOCKS: ClassVar[str] = "latest_block"
    VERSION: ClassVar[str] = "version"
    USER_AGENT: ClassVar[str] = "user_agent"
