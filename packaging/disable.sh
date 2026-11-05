#!/usr/bin/bash
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo 'Run using sudo bash'; exit 1; }
backup=$(mktemp -d /var/tmp/aic8800-disable-backup.XXXXXX)
chmod 700 "$backup"
cp -a --parents /etc/aic8800-ugreen /etc/systemd/system/aic8800-ugreen.service /etc/udev/rules.d/70-aic8800-ugreen.rules "$backup/"
systemctl disable --now aic8800-ugreen.service
mv /etc/udev/rules.d/70-aic8800-ugreen.rules "$backup/disabled-70-aic8800-ugreen.rules"
udevadm control --reload-rules
printf 'Autoload and USB switch disabled. Backup: %s\n' "$backup"
echo 'Installed payload and loaded modules retained. No Wi-Fi disconnect or reboot performed.'
