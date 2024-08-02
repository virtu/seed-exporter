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
        """
        Return string representation.
        Pretty-print datetime and PosixPath objects.
        """
        parts = []
        for field in fields(self):
            value = getattr(self, field.name)
            if isinstance(value, datetime.datetime):
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
    username: str
    password: str
    destination: Path

    def __str__(self):
        """Return string representation, ensuring redaction of critital data."""
        return (
            f"FTPConfig(address=***, port={self.port}, username=***, "
            f"password=***, destination={self.destination})"
        )

    @staticmethod
    def get_ftp_password(args: argparse.Namespace) -> str:
        """Read FTP password from file."""
        file = Path(args.ftp_password_file)
        if not file.exists() or not file.is_file():
            raise ValueError(f"Password file {file} does not exist.")
        with file.open("r", encoding="UTF-8") as f:
            return f.read().strip()

    @classmethod
    def parse(cls, args):
        """Create class instance from arguments."""

        if not args.upload_result:
            return FTPConfig("", 0, "", "", Path("/"))

        for arg in [attr for attr in dir(args) if attr.startswith("ftp_")]:
            if not getattr(args, arg):
                raise ValueError(
                    f"--{arg.replace('_', '-')} is required when --upload-result is set."
                )

        return cls(
            address=args.ftp_address,
            port=args.ftp_port,
            username=args.ftp_username,
            password=FTPConfig.get_ftp_password(args),
            destination=Path(args.ftp_destination),
        )


@dataclass
class Config(ComponentConfig):
    """Exporter settings."""

    timestamp: datetime.datetime
    log_level: int
    crawler_path: Path
    result_path: Path
    upload: bool
    ftp: FTPConfig

    @classmethod
    def parse(cls, args):
        """Create class instance from arguments. Fail early if specified paths
        do not exist."""

        if not Path(args.crawler_path).exists():
            raise ValueError(f"--crawler-path {args.crawler_path} does not exist.")
        if not Path(args.result_path).exists():
            raise ValueError(f"--result-path {args.crawler_path} does not exist.")

        return cls(
            timestamp=datetime.datetime.utcnow(),
            log_level=args.log_level.upper(),
            crawler_path=Path(args.crawler_path),
            result_path=Path(args.result_path),
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
        type=str,
        default="/home/p2p-crawler",
        help="Directory containing p2p-crawler results",
    )

    parser.add_argument(
        "--result-path",
        type=str,
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
        type=int,
        default=21,
        help="FTP server port",
    )

    parser.add_argument(
        "--ftp-username",
        type=str,
        default=None,
        help="FTP server user",
    )

    parser.add_argument(
        "--ftp-password-file",
        type=str,
        default=None,
        help="File containing FTP server password",
    )

    parser.add_argument(
        "--ftp-destination",
        type=str,
        default="public_html/seeds.txt.gz",
        help="FTP server file destination",
    )

    args = parser.parse_args()
    return args


def get_config():
    """Parse command-line arguments and get configuration settings."""

    args = parse_args()
    conf = Config.parse(args)
    return conf
