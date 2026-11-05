#!/usr/bin/bash
set -euo pipefail
umask 022
[ "$(id -u)" = 0 ] || { echo 'Run using sudo bash'; exit 1; }
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
kernel=$(cat "$source_dir/KERNEL")
[ "$(uname -r)" = "$kernel" ] || { echo 'Kernel changed; rebuild before installing'; exit 1; }
command -v usb_modeswitch >/dev/null
[ -x /usr/bin/usb_modeswitch ]
systemctl cat NetworkManager.service >/dev/null
cd "$source_dir"
sha256sum -c SHA256SUMS
[ ! -L /var/lib/aic8800-ugreen ]
[ ! -L /etc/aic8800-ugreen ]
backup=$(mktemp -d /var/tmp/aic8800-install-backup.XXXXXX)
chmod 700 "$backup"
printf 'Backup: %s\n' "$backup"
for target in /var/lib/aic8800-ugreen /etc/aic8800-ugreen /etc/systemd/system/aic8800-ugreen.service /etc/udev/rules.d/70-aic8800-ugreen.rules /etc/systemd/system/multi-user.target.wants/aic8800-ugreen.service; do
    if [ -e "$target" ] || [ -L "$target" ]; then
        cp -a --parents "$target" "$backup/"
        printf '%s\n' "$target" >> "$backup/existing-paths.txt"
    fi
done
systemctl is-enabled aic8800-ugreen.service > "$backup/previous-enabled.txt" 2>&1 || true
systemctl is-active aic8800-ugreen.service > "$backup/previous-active.txt" 2>&1 || true
install -d -m 755 /var/lib/aic8800-ugreen /etc/aic8800-ugreen
stage=$(mktemp -d /var/lib/aic8800-ugreen/stage.XXXXXX)
cp -a "$source_dir/payload/." "$stage/"
chown -R root:root "$stage"
find "$stage" -type d -exec chmod 755 {} +
find "$stage" -type f -exec chmod 644 {} +
if [ -e "/var/lib/aic8800-ugreen/$kernel" ]; then
    mv "/var/lib/aic8800-ugreen/$kernel" "$backup/replaced-payload"
fi
mv "$stage" "/var/lib/aic8800-ugreen/$kernel"
install -m 644 "$source_dir/load.sh" /etc/aic8800-ugreen/load.sh
install -m 644 "$source_dir/aic8800-ugreen.service" /etc/systemd/system/aic8800-ugreen.service
install -m 644 "$source_dir/70-aic8800-ugreen.rules" /etc/udev/rules.d/70-aic8800-ugreen.rules
# Preserve the full provenance and rollback instructions with the installed files.
install -m 644 "$source_dir/README.md" /var/lib/aic8800-ugreen/README.md
install -m 644 "$source_dir/disable.sh" /etc/aic8800-ugreen/disable.sh
printf '%s\n' "$backup" > /etc/aic8800-ugreen/last-backup
if command -v restorecon >/dev/null; then
    restorecon -R /etc/aic8800-ugreen /etc/systemd/system/aic8800-ugreen.service /etc/udev/rules.d/70-aic8800-ugreen.rules /var/lib/aic8800-ugreen || true
fi
systemctl daemon-reload
udevadm control --reload-rules
# No udev trigger: do not disturb the currently working Wi-Fi connection.
systemctl enable aic8800-ugreen.service
systemctl start aic8800-ugreen.service
systemctl --no-pager --full status aic8800-ugreen.service
nmcli device status
printf '\nInstallation complete for %s. Backup: %s\n' "$kernel" "$backup"
echo 'No reboot or module unload was performed. Test boot persistence only when you choose to reboot.'
