---
schema: pjos.device-profile/2
revision: 2
status: draft
confidence: medium
generated: "2026-10-30"
basis: "offline analysis of FiiO M21 FW1.0.8 OTA; no device on hand"

identity:
  id: m21
  model: "FiiO M21"
  model_string: "M21"
  vendor: FiiO
  ota_pre_device: bengal_515
  ota_model_name: "FiiO M21"
  hardware_id_prop: ro.boot.qhardware
  hardware_id_value: SC200VWF
  ota_build: "qti/bengal_515/bengal_515:13/TKQ1.230110.001/eng.fiio.20260428.170642:user/dev-keys"
  ota_fingerprint_short: fiio04281804
  firmware_version: "1.0.8"

soc:
  vendor: qualcomm
  name: sm6225
  marketing: "Snapdragon 680"
  dt_compatible:
    - qcom,khajew-idp
    - qcom,khaje
    - qcom,idp
  dt_model: "Qualcomm Technologies, Inc. KHAJEW IDP nopmi"
  board_id: 65570
  msm_id: [586, 518]
  cpu: "4x Cortex-A73 + 4x Cortex-A53"
  gpu: "Adreno 610"
  gpu_driver: msm_kgsl
  ram_mb: 4096
  storage_gb: 64

kernel:
  source: vendor
  version: "5.15.41"
  release_string: "5.15.41-android13-8-g9ded8564ff52-dirty"
  vermagic: "5.15.41-g9ded8564ff52-dirty SMP preempt mod_unload modversions aarch64"
  gki: true
  gki_hidden_configs: true
  config_available: true
  config_source: "/proc/config.gz embedded in boot.img (IKCFG_ST)"
  source_available: false
  source_note: "FiiOapp/FiiO_Kernel_OpenSource last pushed 2017-11-02, Linux 2.6 template README"
  toolchain: "clang 14.0.7 (Android r450784e)"
  lto: full
  cfi: true
  module_sig_force: false
  modversions: true
  devtmpfs: false
  fbdev: false
  drm: true
  drm_msm_builtin: false
  image_bytes: 49646080

boot:
  scheme: android_abl
  ab_slots: true
  dynamic_partitions: true
  super_bytes: 5371461632
  avb:
    present: true
    vbmeta_algorithm: SHA256_RSA4096
    vbmeta_flags: 0
    vbmeta_rollback_index: 0
    vbmeta_system_algorithm: SHA256_RSA2048
    vbmeta_system_rollback_index: 1675555200
    signing_class: dev-keys
    abl_signed_with: "QCT Root CA 1 / General Use Test Key (for testing 13 only)"
  partitions:
    kernel_source: boot
    first_stage_ramdisk: init_boot
    vendor_ramdisk_and_dtb: vendor_boot
    dtbo_bytes_allocated: 25165824
    boot_bytes_allocated: 100663296
    init_boot_bytes_allocated: 8388608
    vendor_boot_bytes_allocated: 100663296
  fastboot:
    devices_evidence: community_jm21
    getvar_evidence: community_jm21
    boot_evidence: community_jm21
    flash_evidence: community_jm21
    unlock_evidence: none_for_m21
  edl:
    sahara_present: true
    firehose_package_available: false
    recoverable_by_edl: false

display:
  backend: drm
  node: /dev/dri/card0
  connector_hint: DSI-1
  panel_dt_name: qcom,mdss_dsi_nt35521z_750p_video
  panel_dt_alternate: qcom,mdss_dsi_nt35521z_hk_750p_video
  panel_selection: "fiio,lcd_id 4-bit hardware strap"
  panel_verified_on_device: false
  physical_width: 750
  physical_height: 1334
  refresh_hz: 60
  bpp: 24
  diagonal_inch: 4.7
  dpi: 326
  orientation: portrait
  rotation_ccw: 0
  swap_xy: false
  invert_x: false
  vsync: pageflip
  backlight:
    control: pwm
    node: /sys/class/backlight/panel0-backlight/brightness
    max: 255
    dt_max_level: 4095
    node_name_verified: false
  blank:
    mechanism: dsi_off_command
    notifier_module: panel_event_notifier

input:
  keyboard_name: null
  event_hint: null
  touch:
    present: true
    verified_on_device: false
    controller_primary: goodix_gt9xx
    controller_primary_addr: "i2c-3 0x5d"
    controller_secondary: focaltech_fts
    controller_secondary_addr: "i2c-3 0x38"
    controller_secondary_driver_present: false
    protocol: evdev_mt_b
    max_contacts: 5
    abs_x: [0, 750]
    abs_y: [0, 1334]
    swap_xy: false
    invert_x: false
    wakeup: slide
  buttons:
    - {name: volume_up,   gpio: 96,  key: KEY_VOLUMEUP,     code: 115, wakeup: true}
    - {name: volume_down, gpio: 97,  key: KEY_VOLUMEDOWN,   code: 114, wakeup: true}
    - {name: previous,    gpio: 108, key: KEY_PREVIOUSSONG, code: 165, wakeup: true}
    - {name: next,        gpio: 27,  key: KEY_NEXTSONG,     code: 163, wakeup: true}
    - {name: play_pause,  gpio: 24,  key: KEY_PLAYPAUSE,    code: 164, wakeup: true}
    - {name: multifunction, gpio: 75, key: KEY_TV,          code: 377, wakeup: true}
  headset_buttons:
    - {name: volume_up,   key: KEY_VOLUMEUP,   code: 115}
    - {name: volume_down, key: KEY_VOLUMEDOWN, code: 114}
    - {name: media,       key: KEY_MEDIA,      code: 226}
  analog: false
  pointer: false
  rotary: false
  keymap_remappable_at_runtime: true
  hold_switch:
    present: true
    driver: fiio_sw_hold
    gpio: 18
    exposes_evdev: false
  hall_sensor:
    present: true
    driver: fiio_externel_key
    gpio: 109
    exposes_evdev: false

audio:
  backend: alsa
  userspace_libasound_present: false
  userspace_tinyalsa_present: true
  card_dt_model: bengal-idp-snd-card
  card_of_alias: qcom,bengal-asoc-snd
  module_count_required: 30
  codec:
    - {chip: CS43198, count: 4, bus: "i2c-2", addrs: [48, 49, 50, 51], driver: cs43198}
  fpga:
    present: true
    chip: gowin
    bus: spi
    i2c_addr: 54
    firmware: gw_fpga_firmware_m21.fw
  amp: ["OPA1692 x2", "SGM8262-2 x2"]
  headset_detect:
    driver: fiio_headset_jack
    gpio_35mm: 102
    gpio_balanced: 103
    adc_channel: dc_det1
  outputs: [3.5mm_po, 3.5mm_lo, 3.5mm_spdif, 4.4mm_bal_po, 4.4mm_bal_lo]
  volume:
    hardware_keys: [KEY_VOLUMEUP, KEY_VOLUMEDOWN]
    dac_kcontrol: true
    kcontrol_names_verified: false
  bluetooth:
    present: true
    version: "5.0"
    soc: cherokee
    firmware_partition: bluetooth
    codecs_tx: [SBC, AAC, aptX, aptX_HD, LDAC, LHDC]
    codecs_rx: [SBC, AAC, LDAC]
  dsd_native: true
  usb_dac_gadget: true
  verified_on_baseos: false

power:
  battery:
    capacity_mah: 4000
    node_dir: /sys/class/power_supply/battery
    fuel_gauge: cw221X
    charger: sgm41510
    pd_controller: [fusb302, aw35615]
    charge_manager: fiio_charge_manager
    poll_interval_ms: 5000
    temp_windows: 8
  suspend:
    supported: true
    states: [freeze, mem, disk]
    wakeup_buttons: all
    wakeup_touch: true
    wakelock_driver: fiio_wakeup
  rtc:
    present: true
    driver: rtc-pm8xxx
    device: rtc0
    hctosys: true
  desktop_bypass: true

storage:
  internal_gb: 64
  microsd: true
  microsd_max_tb: 2
  rootfs_media_recommended: microsd
  filesystems_supported: [ext4, f2fs, vfat, exfat, erofs, squashfs, overlayfs]
  preserved_partitions_critical: [fiioconfig, persist, modem, modemst1, modemst2]
  never_write_partitions: [xbl, xbl_config, abl, rpm, tz, hyp, devcfg, fiioconfig, persist]

network:
  wifi:
    present: true
    bands: ["2.4GHz", "5GHz"]
    driver_module: qca_cld3_wlan
    cfg80211_builtin: false
  bluetooth:
    present: true
    soc: cherokee
  usb_gadget:
    controller: "4e00000.dwc3"
    configfs: true
    functions: [adb, acm, ncm, ecm, eem, mass_storage, ffs, midi, hid, uac2, uvc]

capabilities:
  display.drm: "yes"
  display.fbdev: "no"
  display.backlight: "yes"
  display.rotation: "no"
  input.buttons: "yes"
  input.touch: "yes"
  input.analog: "no"
  input.pointer: "no"
  input.rotary: "no"
  audio.playback: "unknown"
  audio.volume_hw: "yes"
  audio.headphone_detect: "yes"
  audio.bluetooth: "unknown"
  audio.dsd: "unknown"
  power.battery: "yes"
  power.charger: "yes"
  power.suspend: "yes"
  power.rtc: "yes"
  net.wifi: "unknown"
  net.bluetooth: "unknown"
  storage.microsd: "yes"
  storage.usb_gadget: "yes"

pocketjs:
  runtime_target_suggested: m21-drm
  form: takeover
  tick_hz: 60
  display:
    physical_viewport: [750, 1334]
    logical_viewports: [[375, 667]]
    raster_density: 2
    presentations: [native, integer-fit]
  capabilities:
    - input.buttons
    - input.touch
    - text.glyphs.baked
  profile_validated: true
  profile_validator: "rocknix build tree framework/src/profile.ts validatePocketProfile"
  notes: "logical viewport height must stay <= 1024 because touch coordinates use 10-bit frame encoding"

verified_on_device:
  overall: false
  items:
    - {item: fastboot_devices, done: false}
    - {item: fastboot_getvar_all, done: false}
    - {item: fastboot_boot, done: false}
    - {item: bootloader_unlock, done: false}
    - {item: drm_card0, done: false}
    - {item: panel_mode_750x1334, done: false}
    - {item: touch_evdev, done: false}
    - {item: audio_card, done: false}
    - {item: audio_playback, done: false}
    - {item: battery_sysfs, done: false}
    - {item: suspend_resume, done: false}
    - {item: rtc, done: false}

risks:
  - {id: R1, level: high,   text: "audio userspace stack absent (no libasound, Android uses tinyalsa+HAL)"}
  - {id: R2, level: high,   text: "no firehose package, EDL cannot write; brick unrecoverable if boot chain touched"}
  - {id: R3, level: medium, text: "touch controller may be focaltech on some units, whose driver is absent from all images"}
  - {id: R4, level: medium, text: "devtmpfs disabled in stock kernel, needs mdev or custom kernel"}
  - {id: R5, level: medium, text: "fastboot boot may ignore the boot image ramdisk (observed on JM21)"}
  - {id: R6, level: medium, text: "which DTBO overlay entry M21 selects is not confirmed"}
  - {id: R7, level: low,    text: "panel@panel1 in DT references a td4310 node that does not exist in any overlay"}
---

# M21 Device Profile 草案（BSP v2）

本文件上半部分是 **YAML frontmatter**，是唯一机器可读的事实来源；下半部分是人类可读的说明。
解析脚本：`docs/m21-round2/tools/parse_spec.py`（只依赖 PyYAML 或内置的最小解析器）。

## 为什么是这份结构

对齐 `PJOS-LINUX/docs/15-bsp-architecture.md` 的 Device Profile v2 设计：

| 该文档要求的分组 | 本文件对应键 |
|---|---|
| identity | `identity` |
| soc | `soc` |
| panel / display | `display` |
| input | `input` |
| audio | `audio` |
| power | `power` |
| network | `network` |
| storage | `storage` |
| capabilities | `capabilities`（三态 `yes` / `no` / `unknown`） |
| bsp（kernel_guard/modules/hw_init） | `kernel` + `boot` + `pocketjs` |

额外增加三组该文档未定义但对本次评估必要的：

- `boot`：Qualcomm 的引导链事实（A/B、AVB、fastboot 证据等级、EDL 可用性）；
- `pocketjs`：直接可用的 runtime profile（**已用真实校验器验证**）；
- `verified_on_device` + `risks`：把"未验证"变成**结构化事实**，避免下游把它当已验证。

## 三态约定

`capabilities` 里的值只允许 `yes` / `no` / `unknown`：

- `yes`：固件/DT/模块层面有直接证据，且路径明确；
- `no`：有直接反证（例如 `display.fbdev: no` —— `CONFIG_FB` 未编入）；
- `unknown`：组件存在但**能否在 BaseOS 下工作**未验证（例如 `audio.playback`）。

**`unknown` 不等于 `no`**，也不等于 `yes`。消费方必须显式处理三态。

## PocketJS profile 的合法性

`pocketjs` 段的 `display.logical_viewports = [[375, 667]]` 与 `raster_density = 2` 不是随手写的：

- 物理 750×1334；
- 但 PocketJS 的触摸坐标用 10-bit 帧编码，**逻辑视口任一维 > 1024 会被校验器拒绝**：
  ```
  logical 750x1024 => true
  logical 750x1025 => [{"code":"profile.touchViewport", ...}]
  ```
- 所以取 375×667（正好 1/2）配 `rasterDensity: 2`，既满足约束又保住物理分辨率。

验证方式见 `tools/verify_spec.py` 与 `evidence/profile-validate.log`。

## 与 PJOS `devices.json` v1 的关系

`devices.json` 现有 10 个字段（`id/model/stockmod_prefix/baseos_device/model_string/bootlogo_w/h/panel_rotation_ccw/wifi/bluetooth`）。
本 profile 中可无损映射的：

| v1 字段 | v2 路径 |
|---|---|
| `id` | `identity.id` |
| `model` | `identity.model` |
| `model_string` | `identity.model_string` |
| `panel_rotation_ccw` | `display.rotation_ccw` |
| `wifi` | `capabilities` 派生（见 `network.wifi.present`） |
| `bluetooth` | `network.bluetooth.present` |
| `bootlogo_width/height` | `display.physical_width/height` |

`stockmod_prefix` / `baseos_device` 在 M21 上**不适用**（那是 Allwinner 厂商镜像的概念），应为 `null`——这也是 v2 schema 需要显式允许 null 的理由之一。
