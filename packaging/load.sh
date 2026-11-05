#!/usr/bin/bash
set -euo pipefail
kernel=$(uname -r)
base=/var/lib/aic8800-ugreen
payload="$base/$kernel"
if [ ! -d "$payload" ]; then
    echo "AIC8800: no modules built for $kernel; rebuild the saved UGREEN sources."
    exit 1
fi
cd "$payload"
sha256sum --status -c SHA256SUMS
for name in aic_load_fw aic8800_fdrv; do
    file="$payload/$name.ko"
    ver=$(modinfo -F vermagic "$file")
    [ "${ver%% *}" = "$kernel" ] || { echo 'Kernel mismatch'; exit 1; }
    if [ -d "/sys/module/$name" ]; then
        expected=$(modinfo -F srcversion "$file")
        actual=$(cat "/sys/module/$name/srcversion")
        [ "$expected" = "$actual" ] || {
            echo "A different $name is already loaded; no modules were unloaded."
            exit 1
        }
    fi
done
modprobe cfg80211
if [ ! -d /sys/module/aic_load_fw ]; then
    insmod "$payload/aic_load_fw.ko" aic_fw_path="$payload/aic8800D80"
else
    # Move future firmware requests away from the temporary test directory.
    printf '%s' "$payload/aic8800D80" > /sys/module/aic_load_fw/parameters/aic_fw_path
fi
if [ ! -d /sys/module/aic8800_fdrv ]; then
    insmod "$payload/aic8800_fdrv.ko"
fi
echo "UGREEN CM762 modules ready for $kernel"
