# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.2] - 2024-08-27

- Fix bug where newline character was missing from final line of
  `FormattedOutputWriter`'s output

## [1.2.1] - 2024-08-23

- Fix bug where wrong column was used for node service data
- Collect and output statistics on node evaluation results

## [1.2.0] - 2024-08-23

- Consider non-standard ports bad
- Consider connection times during node quality check
  - IPv4, IPv6 and CJDNS: Bitcoin Core defaults to a [5s timeout][bitcoind clearnet
    timeout] for these networks. Since responsive seed nodes are preferred, this
    threshold is reduced by 50%.
  - Onion and I2P: Bitcoin Core defaults to a [20s timeout][bitcoind socks5 timeout] for
    socks5 connections. Since Onion and I2P network performance are prone to variations
    (intraday fluctuations caused by usage profiles during working ours of different
    geographic regions, attacks on the networks, etc.), connection times are granted 20%
    of slack.

## [1.1.1] - 2024-08-19

- Fix: change column order of blocks and services in `FormattedOutputWriter`
- Introduce changelog

## [1.1.0] - 2024-08-02

- Output version in log
- Fix: Bug in `config.py` error message

## [1.0.0] - 2024-08-02

- Initial release

[bitcoind clearnet timeout]: https://github.com/bitcoin/bitcoin/blob/55d663cb15151773cd043fc9535d6245f8ba6c99/src/netbase.h#L26
[bitcoind socks5 timeout]: https://github.com/bitcoin/bitcoin/blob/bc87ad98543299e1990ee1994d0653df3ac70093/src/netbase.cpp#L40C27-L40C48
