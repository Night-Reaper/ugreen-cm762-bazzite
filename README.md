# UGREEN AX900 CM762 on Bazzite / Linux 7.2

A reproducible build and persistent local installation of UGREEN's official CM762 driver, adapted to Linux 7.2. Instructions in English are below.

## Проверенная конфигурация

| Компонент | Проверено |
|---|---|
| Адаптер | UGREEN AX900 CM762 |
| USB ID | `a69c:5723` (установочный диск) → `a69c:8d80` (загрузчик) |
| Чип | AIC8800D80, `chip_id=7`, `chip_mcu_id=1` |
| ОС | Bazzite 44.20261012.0, Kinoite |
| Ядро | `7.2.9-ogc3.1.fc44.x86_64` |
| Комплект производителя | UGREEN AX900 LinuxDriver V1.1, release `2025_0605_3d4cc869` |
| Результат | Создан `wlan0`, подключение через NetworkManager; пользователь подтвердил работу Wi-Fi |

Это не гарантия поддержки всех адаптеров AX900/CM762 или всех ядер 7.x. В проверенной системе Secure Boot и SELinux были отключены изначально; проект их не отключает. Подпись модулей для Secure Boot здесь не реализована. Работа после перезагрузки пока не подтверждена отдельным тестом.

## Что было сломано

Radxa SDK V5 загружал основной образ размером 358072 байта и зависал на записи `0x170000`. После отключения питания и переключения USB выяснилось, что устройство — MCU1. Комплект UGREEN с собственными согласованными загрузчиком и firmware (основной образ 324720 байт) успешно создал Wi-Fi интерфейс. Одного размера файла недостаточно для установления совместимости: не смешивайте firmware разных комплектов.

Патч адаптирует callback-интерфейсы cfg80211 и структуру TDLS к Linux 7.2, заменяет отсутствующий `strncpy`, устраняет перекрывающий `sprintf` и повторное добавление каталога firmware. Загрузчик возвращает ошибку тайм-аута вместо продолжения работы с незаполненным ответом.

## Сборка без root

Скачайте **Linux-драйвер V1.1 для CM762-35264/CM763-35265** с [официальной страницы UGREEN](https://www.lulian.cn/download/462.html). Установщики производителя и DEB-пакет не запускайте.

Проверенный архив: `UGREEN_AIC-AX900_LinuxDriver_V1.1.zip`.

```text
SHA256: 85d3e0d62d82f874ad3aa3fe12061658aeca570adfeccff526c055a5e6218bd6
```

Нужны Python 3.11+, Git, make, GCC и инструменты сборки соответствующего ядра, kmod (`modinfo`), usb_modeswitch, systemd и NetworkManager. Каталог `/lib/modules/$(uname -r)/build` должен содержать development-файлы **именно работающего ядра**. Для нестандартного `ogc`-ядра обычный Fedora kernel-devel другой версии не подходит. Bazzite использует образную систему: способы получения инструментов зависят от вашего образа; сборка через пакетный менеджер контейнера не устанавливает драйвер на хост.

В каталоге этого репозитория:

```bash
python3 scripts/build.py '/путь/к/UGREEN_AIC-AX900_LinuxDriver_V1.1.zip'
```

Сборщик проверит SHA256, распакует архив в новый `build/`, применит патч и соберёт оба модуля. Ничего не устанавливает, сеть не использует, существующий каталог сборки не перезаписывает. Для новой попытки используйте `--output build-next`.

## Постоянная локальная установка в Bazzite

Сначала проверьте собранный комплект на своей ревизии. На подтверждённой выше конфигурации он работает. Сохраните альтернативный доступ в интернет на время первичной проверки.

```bash
sudo bash build/install/install.sh
```

Установка сохраняет существующие файлы в `/var/tmp/aic8800-install-backup.*`, проверяет хеши, помещает модули и firmware в `/var/lib/aic8800-ugreen/<kernel>/`, включает systemd-службу и добавляет точечное правило переключения USB `a69c:5723` стандартным EJECT. Доступный только для чтения `/usr` не изменяется. Это **локальная systemd-установка**, а не RPM, DKMS или akmods.

Загруженные модули должны совпадать по `srcversion` с устанавливаемыми; иначе служба откажется работать и ничего не выгрузит. На исходной проверенной машине установка прошла без разрыва текущего Wi-Fi. При первой установке на другой машине возможна инициализация адаптера. Для горячего подключения из другого режима USB дополнительные правила не предоставляются.

Служба использует только модули для точной версии текущего ядра. Никаких `--force`, обновления flash, автоматической перезагрузки или отключения Secure Boot. SELinux в enforcing-режиме отдельно не проверялся и может потребовать настройки меток/политики.

```bash
systemctl status aic8800-ugreen.service --no-pager
nmcli device status
nmcli --wait 20 device wifi list ifname wlan0 --rescan yes
```

Замените `wlan0`, если имя отличается. Подключайтесь через настройки сети или `nmcli --ask`; не отправляйте пароль в issue. При следующей выбранной вами перезагрузке проверьте службу и Wi-Fi повторно. Не удаляйте каталог прежнего временного теста до переподключения адаптера/перезагрузки: текущий fdrv может ещё использовать его путь для userconfig.

## Обновление ядра

Автоматической пересборки нет. Новый kernel-devel должен соответствовать новому ядру; соберите заново в отдельный каталог и установите новый versioned payload. Совместимость с будущими API не гарантируется. Если модулей для запущенного ядра нет, служба завершится с понятной ошибкой, сохранив предыдущие файлы. Не обходите проверку vermagic. Изменение ядра не выполняется этим проектом.

## Отключение и резервные копии

```bash
sudo bash /etc/aic8800-ugreen/disable.sh
```

Скрипт сохранит конфигурацию, отключит службу и переместит только наше udev-правило в резервную копию. Модули в памяти и файлы останутся; текущая сеть не отключается. Путь к резервной копии установки — `/etc/aic8800-ugreen/last-backup`. Если наши файлы существовали до установки, восстанавливайте только их из этой копии, а не весь `/etc`.

## English quick start

Tested: UGREEN CM762, AIC8800D80 MCU1 (`chip_id=7`, `chip_mcu_id=1`), Bazzite 44, kernel `7.2.9-ogc3.1.fc44.x86_64`. The vendor-matched firmware and patched modules created `wlan0` and connected via NetworkManager. Post-reboot persistence remains unverified. Other hardware/kernel versions are not claimed as tested.

Download the exact V1.1 archive from the official UGREEN page above. Do not run the vendor installer or install its DEB package. With matching kernel development files and build dependencies available:

```bash
python3 scripts/build.py /path/to/UGREEN_AIC-AX900_LinuxDriver_V1.1.zip
sudo bash build/install/install.sh
```

The builder never runs as root and verifies the archive checksum. The installer backs up existing task-specific files, installs into persistent `/var/lib` and `/etc`, and enables the local loader service and a device-specific USB eject rule. It does not modify `/usr`, reboot, force-load modules or disable Secure Boot. Secure Boot signing and SELinux enforcing support are not provided/tested. Automatic rebuilds across kernel updates are not configured: rebuild for each exact kernel. Read the installer before running it.

Disable reversibly with `sudo bash /etc/aic8800-ugreen/disable.sh`. Retained loaded modules preserve the existing connection.

## Источники, лицензии и отчёты об ошибках

- [UGREEN CM762 Linux package](https://www.lulian.cn/download/462.html) — исходный комплект производителя.
- [Radxa AIC8800](https://github.com/radxa-pkg/aic8800) — первоначальная диагностика и история совместимости.
- [MCU1 investigation #58](https://github.com/shenmintao/aic8800d80/issues/58) — независимое исследование похожего ограничения V5; код этой ветки не включён.
- [rpm-ostree filesystem layout](https://coreos.github.io/rpm-ostree/administrator-handbook/#filesystem-layout) — причина установки в `/etc` и `/var`.

Репозиторий содержит только патч, скрипты и документацию. Firmware, ZIP/DEB производителя и готовые `.ko` не распространяются. Лицензии указаны в `LICENSE`; оригинальные copyright и лицензии производителя сохраняются.

Для issue приложите модель/ревизию, `uname -r`, `lsusb`, статус службы, этап сбоя и relevant kernel log. Удалите пароли, SSID/BSSID, MAC-адреса и USB-серийные номера из публичного отчёта. Не очищайте системный журнал ради диагностики. Локальные журналы с исходной машины не включены в репозиторий.
