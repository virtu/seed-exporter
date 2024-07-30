"""This module contains configuration options for the seed exporter."""

import argparse
import datetime
import importlib.metadata
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path, PosixPath

__version__ = importlib.metadata.version(__package__ or __name__)


@dataclass
class ComponentConfig:
    """Base class for components."""

    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)

    def __str__(self):
        """Return string representation.

        - Redact password fields
        - Pretty-print datetime and PosixPath objects
        """
        parts = []
        for field in fields(self):
            value = getattr(self, field.name)
            if field.name == "password":
                parts.append(f"{field.name}=<redacted>")
            elif isinstance(value, datetime.datetime):
                parts.append(f"{field.name}={value.isoformat(timespec='seconds')}Z")
            elif isinstance(value, PosixPath):
                parts.append(f"{field.name}={value.name}")
            else:
                parts.append(f"{field.name}={value}")
        return ", ".join(parts)


@dataclass
class FTPConfig(ComponentConfig):
    """FTP-related settings."""

    address: str
    port: int
    user: str
    password: str
    destination: str

    @classmethod
    def parse(cls, args):
        """Create class instance from arguments."""
        return cls(
            address=args.ftp_address,
            port=args.ftp_port,
            user=args.ftp_user,
            password=args.ftp_password,
            destination=args.ftp_destination,
        )


@dataclass
class Config(ComponentConfig):
    """Exporter settings."""

    timestamp: datetime.datetime
    log_level: int
    crawler_path: str
    result_path: str
    upload: bool
    ftp: FTPConfig

    @classmethod
    def parse(cls, args):
        """Create class instance from arguments."""
        return cls(
            timestamp=datetime.datetime.utcnow(),
            log_level=args.log_level.upper(),
            crawler_path=args.crawler_path,
            result_path=args.result_path,
            upload=args.upload_result,
            ftp=FTPConfig.parse(args),
        )


def parse_args():
    """Parse command-line arguments."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--log-level",
        type=str,
        default=os.environ.get("LOG_LEVEL", "INFO"),
        help="Logging verbosity",
    )

    parser.add_argument(
        "--crawler-path",
        type=Path,
        default="/home/p2p-crawler",
        help="Directory containing p2p-crawler results",
    )

    parser.add_argument(
        "--result-path",
        type=Path,
        default="/home/seed-exporter",
        help="Directory for results",
    )

    parser.add_argument(
        "--upload-result",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Upload results to FTP (default: disabled)",
    )

    parser.add_argument(
        "--ftp-address",
        type=str,
        default=None,
        help="FTP server address",
    )

    parser.add_argument(
        "--ftp-port",
        type=str,
        default=None,
        help="FTP server port",
    )

    parser.add_argument(
        "--ftp-user",
        type=str,
        default=None,
        help="FTP server user",
    )

    parser.add_argument(
        "--ftp-password",
        type=str,
        default=None,
        help="FTP server password",
    )

    parser.add_argument(
        "--ftp-destination",
        type=str,
        default=None,
        help="FTP server file destination",
    )

    args = parser.parse_args()
    return args


def get_config():
    """Parse command-line arguments and get configuration settings."""

    args = parse_args()
    conf = Config.parse(args)
    return conf
