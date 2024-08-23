# Bitcoin seed node exporter

Analyze reachable node data produced by
[p2p-crawler][p2p-crawler-link] and extract suitable seed nodes in a
[`makeseeds.py`][makeseeds.py-link]-compatible format

## Features

- Supports all network types (IPv4, IPv6, CJDNS, Onion, I2P)
- Easy deployment of periodic scheduled runs via Nix flake providing a Nix module
- Automatic publication of results via FTP

## NixOS deployment

The repository includes Nix flake which provides a Nix module (see
[`module.nix`][module.nix-link] for details) for simple deployments. Just include the
flake, import the module and enable the service:

```nix
  imports = [
    seed-exporter.nixosModules.seed-exporter
  ];
  services.seed-exporter.enable = true;
```

By default, the service is scheduled to run at 12 noon every day. It will look for input
data produced by [p2p-crawler][p2p-crawler-link] in `/home/p2p-crawler` and write
results to `/home/seed-exporter`. These settings can be changed via the `schedule`,
`crawlerPath`, and `resultPath` settings (see [`module.nix`][module.nix-link] for
details).

The service can be configured to automatically publish results via FTP. The code was
designed to accept the required credentials from a file to make it compatible with
[SOPS-nix][sops-nix-link]-style secret management:

```nix
sops.secrets."seed-exporter/ftp-password".owner = config.users.users.seed-exporter.name;
services.seed-exporter = {
enable = true;
uploadResult = {
enable = true;
ftp = {
      address = "XX.XX.XX.XX";
      username = "johndoe";
      passwordFile = config.sops.secrets."seed-exporter/ftp-password".path;
      destination = "public_html/seeds.txt.gz";
    };
  };
};
```

## Usage

```text
usage: seed-exporter [-h] [--log-level LOG_LEVEL] [--crawler-path CRAWLER_PATH] [--result-path RESULT_PATH] [--upload-result | --no-upload-result]
                     [--ftp-address FTP_ADDRESS] [--ftp-port FTP_PORT] [--ftp-username FTP_USERNAME] [--ftp-password-file FTP_PASSWORD_FILE]
                     [--ftp-destination FTP_DESTINATION]

options:
  -h, --help            show this help message and exit
  --log-level LOG_LEVEL
                        Logging verbosity
  --crawler-path CRAWLER_PATH
                        Directory containing p2p-crawler results
  --result-path RESULT_PATH
                        Directory for results
  --upload-result, --no-upload-result
                        Upload results to FTP (default: disabled)
  --ftp-address FTP_ADDRESS
                        FTP server address
  --ftp-port FTP_PORT   FTP server port
  --ftp-username FTP_USERNAME
                        FTP server user
  --ftp-password-file FTP_PASSWORD_FILE
                        File containing FTP server password
  --ftp-destination FTP_DESTINATION
                        FTP server file destination
```

## License

This software is made available under the MIT license. See LICENSE for more details.

[p2p-crawler-link]: https://github.com/virtu/p2p-crawler
[makeseeds.py-link]: https://github.com/bitcoin/bitcoin/blob/55d663cb15151773cd043fc9535d6245f8ba6c99/contrib/seeds/makeseeds.py
[sops-nix-link]: https://github.com/Mic92/sops-nix
[module.nix-link]: https://github.com/virtu/seed-exporter/blob/master/module.nix
