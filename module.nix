flake: { config, pkgs, lib, ... }:

with lib;

let
  inherit (flake.packages.${pkgs.stdenv.hostPlatform.system}) seed-exporter;
  cfg = config.services.seed-exporter;
in
{
  options = {
    services.seed-exporter = {
      enable = mkEnableOption "seed-exporter";

      schedule = mkOption {
        type = types.str;
        default = "*-*-* 12:00:00 UTC";
        example = "daily";
        description = mdDoc "Systemd OnCalendar interval for running the exporter.";
      };

      logLevel = mkOption {
        type = types.str;
        default = "INFO";
        example = "DEBUG";
        description = mdDoc "Log verbosity for console.";
      };

      crawlerPath = mkOption {
        type = types.path;
        default = "/home/p2p-crawler/";
        example = "/scratch/results/p2p-crawler";
        description = mdDoc "Directory containing p2p-crawler results.";
      };

      resultPath = mkOption {
        type = types.path;
        default = "/home/seed-exporter/";
        example = "/scratch/results/seed-exporter";
        description = mdDoc "Result directory.";
      };

      uploadResult = {
        enable = mkEnableOption "upload result";
        ftp = {
          address = mkOption {
            type = types.nullOr types.str;
            default = null;
            example = "127.0.0.1";
            description = mdDoc "Address of the FTP server to upload the results to.";
          };
          port = mkOption {
            type = types.nullOr types.port;
            default = 21;
            example = 42;
            description = mdDoc "Port of the FTP server to upload the results to.";
          };
          username = mkOption {
            type = types.nullOr types.str;
            default = null;
            example = "user";
            description = mdDoc "FTP server username";
          };
          passwordFile = mkOption {
            type = types.nullOr types.str;
            default = null;
            example = "/path/to/password";
            description = mdDoc "FTP server filename";
          };
          destination = mkOption {
            type = types.nullOr types.str;
            default = null;
            example = "/path/to/result";
            description = mdDoc "FTP server destination path";
          };
        };
      };
    };
  };

  config = mkIf cfg.enable {
    assertions = [
      {
        assertion = !cfg.uploadResult.enable || (
          cfg.uploadResult.ftp.address != null &&
            cfg.uploadResult.ftp.port != null &&
            cfg.uploadResult.ftp.username != null &&
            cfg.uploadResult.ftp.passwordFile != null &&
            cfg.uploadResult.ftp.destination != null
        );
        message = "All FTP options must be set if seed-exporter.uploadResult.enable is true.";
      }
    ];

    users = {
      users.seed-exporter = {
        isSystemUser = true;
        group = "seed-exporter";
        home = "/home/seed-exporter";
        createHome = true;
        homeMode = "755";
      };
      groups.seed-exporter = { };
    };


    systemd.timers.seed-exporter = {
      wantedBy = [ "timers.target" ];
      timerConfig =
        {
          OnCalendar = cfg.schedule;
          Unit = [ "seed-exporter.service" ];
        };
    };

    systemd.services.seed-exporter = {
      description = "seed-exporter";
      after = [ "network-online.target" ];
      serviceConfig = {
        ExecStart = ''${seed-exporter}/bin/seed-exporter \
          --log-level ${cfg.logLevel} \
          --crawler-path ${cfg.crawlerPath} \
          --result-path ${cfg.resultPath} \
          ${optionalString (cfg.uploadResult.enable != null) "--upload-result --ftp-address ${cfg.uploadResult.ftp.address} --ftp-port ${toString cfg.uploadResult.ftp.port} --ftp-username ${cfg.uploadResult.ftp.username} --ftp-password-file ${cfg.uploadResult.ftp.passwordFile} --ftp-destination ${cfg.uploadResult.ftp.destination} "}
        '';
        ReadWriteDirectories = "/home/seed-exporter/";
        User = "seed-exporter";
        Group = "seed-exporter";
      };
    };
  };
}
