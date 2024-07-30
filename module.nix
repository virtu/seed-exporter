flake: { config, pkgs, lib, ... }:

with lib;

let
  inherit (flake.packages.${pkgs.stdenv.hostPlatform.system}) seed-exporter;
  cfg = config.services.seedExporter;
in
{
  options = {
    services.seedExporter = {
      enable = mkEnableOption "seed-exporter";

      schedule = mkOption {
        type = types.str;
        default = "*-*-* 04:00:00 UTC";
        example = "daily";
        description = mdDoc "Systemd OnCalendar interval for running the exporter.";
      };

      logLevel = mkOption {
        type = types.str;
        default = "INFO";
        example = "DEBUG";
        description = mdDoc "Log verbosity for console.";
      };

      inputDataPath = mkOption {
        type = types.path;
        default = "/home/p2p-crawler/";
        example = "/scratch/results/p2p-crawler";
        description = mdDoc "Directory containing p2p-crawler results.";
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
          user = mkOption {
            type = types.nullOr types.str;
            default = null;
            example = "user";
            description = mdDoc "FTP server username";
          };
          password = mkOption {
            type = types.nullOr types.str;
            default = null;
            example = "password";
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
      # TODO: untested
      {
        assertion = !config.uploadResult.enable || (
          config.uploadResult.ftp.address != null &&
            config.uploadResult.ftp.port != null &&
            config.uploadResult.ftp.user != null &&
            config.uploadResult.ftp.password != null &&
            config.uploadResult.ftp.destination != null
        );
        message = "All FTP options must be set if seed-exporter.uploadResult.enable is true.";
      }
    ];

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
          --input ${cfg.inputDataPath} \
          # TODO: untested
          ${optionalString (cfg.uploadResult.enable != null) "--upload-result --ftp-address ${cfg.uploadResult.address} --ftp-port ${cfg.uploadResult.ftp.port} --upload-user ${cfg.uploadResult.ftp.user} --upload-password ${cfg.uploadResult.ftp.password} --upload-path ${cfg.uploadResult.ftp.destination} "}
        '';
      };
    };
  };
}
