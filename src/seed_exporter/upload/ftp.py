"""Module to upload a file via FTP."""

import logging as log
from dataclasses import dataclass
from ftplib import FTP_TLS
from pathlib import Path

from seed_exporter.config import FTPConfig


@dataclass
class FtpUploader:
    """FTP Uploader class."""

    conf: FTPConfig

    def upload_file(self, src: Path):
        """Uploads a file to an FTP server."""
        if not src.exists() or not src.is_file():
            log.error("File %s does not exist or is not a file.", src.name)
            return False

        try:
            with FTP_TLS() as ftp:
                ftp.connect(self.conf.address, self.conf.port)
                ftp.login(self.conf.username, self.conf.password)
                with src.open("rb") as file:
                    ftp.cwd(str(self.conf.destination.parent))
                    ftp.storbinary(f"STOR {self.conf.destination.name}", file)
                ftp.quit()
            log.info(
                "Uploaded %s to ftp://<redacted>/%s (%.1fkB uploaded)",
                str(src),
                str(self.conf.destination),
                src.stat().st_size / 1024,
            )
            return True
        except Exception as e:  # pylint: disable=broad-except
            log.error("Failed to upload file %s: %s", src.name, e)
            return False
