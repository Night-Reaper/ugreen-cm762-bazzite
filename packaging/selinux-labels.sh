#!/usr/bin/bash
# Persistent file labels for this project's modules and vendor firmware only.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo 'Run using sudo bash'; exit 1; }
base=/var/lib/aic8800-ugreen
[ -d "$base" ] || { echo 'Driver payload is not installed'; exit 1; }
command -v semanage >/dev/null || {
    echo 'semanage is required (Fedora: policycoreutils-python-utils). No policy was changed.'
    exit 1
}
command -v restorecon >/dev/null
backup=$(mktemp -d /var/tmp/aic8800-selinux-backup.XXXXXX)
chmod 700 "$backup"
semanage export > "$backup/semanage-before.txt"
cp -a --parents /etc/selinux/targeted/contexts/files/file_contexts.local "$backup/" 2>/dev/null || true
find "$base" -type f \( -name '*.ko' -o -path '*/aic8800D80/*' \) -exec ls -lZ {} + > "$backup/labels-before.txt"
printf 'SELinux backup: %s\n' "$backup"
set_label() {
    local pattern="$1" label="$2"
    if semanage fcontext -l -C | cut -d ' ' -f 1 | grep -Fx -- "$pattern" >/dev/null; then
        semanage fcontext -m -f f -t "$label" "$pattern"
    else
        semanage fcontext -a -f f -t "$label" "$pattern"
    fi
}
set_label '/var/lib/aic8800-ugreen/[^/]+/aic(8800_fdrv|_load_fw)\.ko' modules_object_t
set_label '/var/lib/aic8800-ugreen/[^/]+/aic8800D80/[^/]+' lib_t
restorecon -RFv "$base"
echo 'Module and firmware labels corrected. SELinux enforcement is unchanged.'
