# ② 内核：版本、源码可得性、GKI、DTB 节点

调查日期：2026-10-30。无实机。证据文件在 `evidence/`。

---

## 1. 结论先行

| 问题 | 结论 | 置信度 |
|---|---|---|
| 内核版本 | **5.15.41**，`5.15.41-android13-8-g9ded8564ff52-dirty` | **高**（从 `boot.img` 内 `IKCFG_ST` 解出 config，且 5 个 .ko 的 `vermagic` 一致） |
| 是否 GKI | **是**。`CONFIG_GKI_HIDDEN_*=y` 一整套 + 驱动全部 =m（只有 `ZRAM`/`ZSMALLOC` 两个 =m 之外的内建模块） | **高** |
| 厂商 kernel 源码 | **不可得**。`FiiOapp/FiiO_Kernel_OpenSource` 最后一次 push 是 **2017-11-02**，README 是 Linux 2.6 模板 | **高** |
| 编译工具链 | clang 14.0.7 / Android r450784e（kernel config `CONFIG_CC_VERSION_TEXT`） | 高 |
| Kernel .config 可得 | **可得**且已提取（6574 行，`evidence/kernel-config-5.15.41-android13-8.txt`） | 高 |
| DTS/DTB | `vendor_boot` 内 dtb 是 **3 个 DTB 的拼接**（Khaje/Khajep/Khajeq SoC）+ `dtbo.img` **42 个 overlay** | 高 |
| 显示节点 | `qcom,mdss_mdp` / `qcom,dsi-display-primary` / 11 个 DSI 面板 + 4 个 FiiO 面板表 | 高 |
| 触摸节点 | M21 走 **goodix gt9xx @ i2c-3 0x5d**（`fiio_ts_core` 选择）；`focaltech@38` 也声明但**驱动不在镜像内** | 高（节点）/高（驱动缺失） |
| 音频节点 | `bengal-asoc-snd`（`bengal-idp-snd-card`）+ 4×`cs43198` + `gw-fpga` + `anolog_board` | 高 |
| 电源节点 | `sgm41510` 充电 + `cw221X` 电量计 + `fiio_charge_manager` + `power_board` | 高 |
| 按键节点 | `gpio_keys` 6 键（含 `KEY_PREVIOUSSONG`/`KEY_PLAYPAUSE`/`KEY_NEXTSONG`）+ `headset-adc-keys` | 高 |
| 与 H700/RG34XX 的差异 | 见 §7，**不是"多几个驱动"，是整条 BSP 换掉了** | 高 |

**一句话**：内核是标准 Android 13 GKI 5.15.41，**源码拿不到但二进制完整、config 可得、DTB 可解析、vendor 模块 ABI 已被同平台实测证明可用**。对 BaseOS 而言"不需要重编内核"是完全可行的方案；需要自定义内核时（例如加 fbdev 支持），JM21 的 Plan-B 已证明公开 CAF 5.15 树 + 同一 `.config` 能加载 FiiO 模块。

---

## 2. 内核身份

### 2.1 版本与 config 提取

`boot.img` 是纯 kernel（`ramdisk_size=0`），kernel 内嵌 `IKCFG_ST` 压缩配置块：

```
$ python3 -c "d=open('boot.img','rb').read(); k=d[4096:4096+49646080]; print(k.find(b'IKCFG_ST'))"
27542624
```

解出 187,988 字节 config，头部：

```
# Automatically generated file; DO NOT EDIT.
# Linux/arm64 5.15.41 Kernel Configuration
#
CONFIG_CC_VERSION_TEXT="Android (8508608, based on r450784e) clang version 14.0.7 ..."
```

`vermagic` 在 5 个不同模块中完全一致（`modinfo`）：

```
vermagic: 5.15.41-g9ded8564ff52-dirty SMP preempt mod_unload modversions aarch64
```

`machine_dlkm.ko`、`cs43198.ko`、`msm_drm.ko`、`goodix_gt9xx_ts.ko`、`lcd_id.ko` 全部相同 → **boot.img 里的 kernel 就是这些模块编译时的那一棵**。

### 2.2 GKI 判据

```
CONFIG_GKI_HIDDEN_DRM_CONFIGS=y
CONFIG_GKI_HIDDEN_SND_CONFIGS=y
CONFIG_GKI_HIDDEN_SND_SOC_CONFIGS=y
CONFIG_GKI_HIDDEN_QCOM_CONFIGS=y
CONFIG_GKI_HIDDEN_MEDIA_CONFIGS=y
... （共 20 个 GKI_HIDDEN_*）
CONFIG_ANDROID_KABI_RESERVE=y
CONFIG_MODVERSIONS=y
CONFIG_LTO_CLANG_FULL=y
CONFIG_CFI_CLANG=y
CONFIG_CFI_CLANG_SHADOW=y
CONFIG_SHADOW_CALL_STACK=y
CONFIG_KASAN=y
```

全 config 里 `=m` 只有 **2 个**（`ZSMALLOC`、`ZRAM`）；**所有硬件驱动都以 .ko 形式外置**，包括 `msm_drm`、`machine_dlkm`、`pinctrl-*`、`ufs_qcom`。这是"GKI 内核 + vendor_dlkm 提供全部驱动"的标准结构。

**对 BaseOS 的含义**：内核本体极小（`Image` 49.6 MB，含 KASAN debug），**几乎不含驱动**。要显示画面必须加载 `/vendor_dlkm` 里的 `msm_drm.ko`（39.7 MB，含 KMS + DSI + 面板解析 + SDE）。这不是"可选优化"，是硬依赖。

### 2.3 模块签名策略

```
CONFIG_MODULE_SIG=y
CONFIG_MODULE_SIG_ALL=y
CONFIG_MODULE_SIG_SHA1=y
CONFIG_MODULE_SIG_PROTECT=y
# CONFIG_MODULE_SIG_FORCE is not set      ← 关键
```

`MODULE_SIG_FORCE` 未设置 → **未签名的自编模块可以加载**（同 JM21 Plan-B 的实测结论）。这为"往 BaseOS 里加一个小模块"（例如把 fbdev 模拟补进来）留了门。

### 2.4 厂商源码可得性

```
$ gh api repos/FiiOapp/FiiO_Kernel_OpenSource --jq '{pushed_at,description,size}'
pushed_at = 2017-11-02T10:46:09Z
description = FiiO kernel OpenSource
size = 92987
```

README 内容是 Linux 2.6 的通用模板（`linux/FiiO-Kernel-OpenSource-README.md` 原文：`Linux kernel release 2.6.xx`）。

**结论：厂商 5.15.41 源码不可得，也不存在"没找对仓库"的可能**（账号下只有一个 kernel 仓库，最后活动 9 年前）。这一点与第一轮一致，且第一轮结论**有效**。

替代路径（按可用性排序）：

| 路径 | 可用性 | 证据 |
|---|---|---|
| 直接用 stock kernel（不重编） | 可用 | `boot.img` 完整，模块 ABI 自洽 |
| 公开 CAF 5.15 树 + 同一 `.config`，强制 vermagic | **同平台已实测可加载 FiiO 模块** | JM21 `docs/45` §7：CRC 0 个不符 |
| 向 FiiO 索取 GPL 源码 | 未响应（JM21 社区已发请求，`outbox/06-followup-gpl-D+15-EN.txt`） | 推断：短期无望 |
| mainline | **不可用**：`sm6225.dtsi` 无 `mdss`/`dsi` 节点（grep=0），无音频 | 高 |

---

## 3. DTB：三层结构

`vendor_boot.img` 的 `dtb_size=1,006,645`，实际是 **3 个 DTB 首尾拼接**：

```
dtb#0 offset=0       size=265319  model="Qualcomm Technologies, Inc. Khaje SoC"
dtb#1 offset=530741  size=58769   model="Qualcomm Technologies, Inc. Khajep QRD"
dtb#2 offset=799053  size=207592  model="Qualcomm Technologies, Inc. Khajeq SoC"
```

`dtbo.img` 是 **42 个 overlay**（`evidence/dtbo-entry-index.txt`），全部 `id=0 rev=0`（按 `qcom,board-id` 匹配）。关键条目：

| entry | model | msm-id | board-id | 特征 |
|---|---|---|---|---|
| 12 | Khajeg IDP nopmi | 0x249 | 0x10022 | `fiio,dac-core`、goodix、**无 focaltech** |
| 13 | Khajeg IDP | 0x249 | 0x10022 | goodix + focaltech + 完整 mdss |
| 16 | Khajeg IDPS + 90Hz | 0x249 | 0x10122 | 同上 |
| 22 | KHAJEP IDP nopmi | 0x231 | 0x10022 | 同 12 |
| 31 | KHAJEQ IDP nopmi | 0x232 | 0x10022 | 同 12 |
| **40** | **KHAJEW IDP nopmi** | 0x24a / 0x206 | 0x10022 | **focaltech 启用、focaltech 与 goodix 并存** |

M21（`bengal_515`, `qhardware=SC200VWF`）落在哪一条**未在实机确认**。判据：JM21 的实机 DT（`ocnaibill` 项目 `analysis/fw-1.1.1/dtbo-jm21-full.dts`）与 entry 40 完全同构（model `KHAJEW IDP nopmi`、msm-id `<0x24a 0x10000 0x206 0x10000>`、有 focaltech），而 M21 与 JM21 同为 `bengal_515` 且模块名从 `*_jm21` 换成 `*_m21` → **推断 M21 也落在 entry 40**，置信度中。

---

## 4. 关键节点清单（从 entry 40 提取，`evidence/m21-dtbo-entry40-khajew-idp-nopmi.dts`）

### 4.1 显示

```
qcom,mdss_mdp（SoC 级，dtb0）
  └ qcom,dsi-display-primary  (label="primary", qcom,platform-te-gpio, vddio-supply)
  └ 11 个面板节点：td4330_truly_v2_cmd/video, nt36672e_90Hz/120Hz, sim,
       ili9881d_720p, yx60031_1080p, nt35521z_750p, nt35521z_hk_750p,
       st7703_750p, jd9365da_750p, bm4731_750p
```

FiiO 自己的面板选择表（`lcm-panel-node` + `lcd_id`）：

```
lcd_id { lcd,id_0/1/2/3 = GPIO 111/60/54/31 }   ← 板上 4 bit 硬件 ID
lcm-panel-node {
  panel@panel1 = "qcom,mdss_dsi_td4310_1080p_video"    value 0000  ← ⚠ 该节点在 DTBO 中不存在
  panel@panel2 = "qcom,mdss_dsi_yx60031_1080p_video"   value 0001
  panel@panel3 = "qcom,mdss_dsi_nt35521z_750p_video"   value 0111
  panel@panel4 = "qcom,mdss_dsi_nt35521z_hk_750p_video" value 0110
}
```

⚠ **`td4310_1080p` 在 42 个 DTBO 里没有任何定义**（对每个 entry 做 `qcom,mdss_dsi_*_video {` 提取，只有 11 个名字，无 td4310）。这是厂商遗留的悬空引用。对 M21（750×1334）无关，因为 M21 只可能用 `nt35521z_750p` 或 `nx35521z_hk_750p`。

`nt35521z_750p` 的实测参数（DT 属性）：

```
panel-type    = "dsi_video_mode"
panel-width   = 0x2ee = 750
panel-height  = 0x536 = 1334
framerate     = 0x3c  = 60
bpp           = 0x18  = 24
bl-pmic-control-type = "bl_ctrl_pwm"
bl-max-level  = 0xfff (4095), bl-min-level = 1
reset-sequence= <1 20 0 10 1 20>  (ms)
h: pulse 32 / front 36 / back 36
v: pulse 2 / front 9 / back 7
```

→ 标称 **750×1334 @ 60 Hz**，PWM 背光 1..4095 级。与 FiiO 规格页 "4.7-inch (750x1334)" 一致 [S1]。DPI = √(750²+1334²)/4.7 ≈ **326**。

### 4.2 触摸

M21 entry 40 里**两个控制器都声明**，靠 `qcom,i2c-touch-active` 选：

```
fragment@13:  status="okay", qcom,i2c-touch-active="synaptics,tcm-i2c"
              synaptics_tcm@20 / novatek@62
fragment@14:  synaptics_tcm@20 disabled / novatek@62 disabled
fragment@40:  status="okay", qcom,i2c-touch-active="focaltech,fts"
              focaltech@38 { reg=0x38, irq=gpio80, reset=gpio71,
                             display-coords=<0 0 0x2d0 0x500>,  ← 720×1280
                             max-touch-number=5, have-key, keys=<0x8b 0xac 0x9e> }
fragment@19:  status="okay", goodix_gt9xx@5d { reg=0x5d, irq=gpio80, reset=gpio71,
                             touchscreen-size-x=0x2ee(750), y=0x536(1334),
                             max-id=0x0b, max-w=0x200, max-p=0x200,
                             key-map=<0x44 0xa5 0xa4 0xa3 0x57 0x58>,
                             swap-x2y=0, inversion-x=0, int-sync=1 }
fragment@41:  synaptics/novatek disabled
```

两条 I2C 总线映射（`__fixups__`）：fragment 19 与 40 都挂在 `qupv3_se2_i2c` → **同一条 i2c-2**。
但 JM21 实机 `i2cdetect` 记录（`docs/01-hardware.md`）：

```
i2c-3: 3-0038 fts   3-005d gt9xx
```

→ 实机上两者**都**在 i2c-3 上出现（0x38 + 0x5d），说明 FiiO 用 `fiio_ts_core`（`compatible="fiio,ts_core"`, `tp-vcc-name="pm8350c_l13"`）在运行时探测哪个真的应答。

**驱动可得性（关键）**：

| 驱动 | 镜像里有没有 |
|---|---|
| `goodix_gt9xx_ts.ko` | **有**（`vendor_dlkm` + `vendor_boot` ramdisk，1,433,248 B，`depends: fiio_primary_modules`） |
| `ts_core.ko` | **有**（363,256 B，description="touch screen switch driver"） |
| focaltech FTS | **没有**。对 226 个 .ko 全量 `cat | grep focaltech` = 0 命中；对 `vendor_dlkm.img`/`vendor.img`/`odm.img`/`system_dlkm.img` 原始字节扫描 `focaltech` = 0；kernel `Image` 内 `focaltech` = 0。kernel config 里 `# CONFIG_TOUCHSCREEN_STMFTS is not set` |

→ **M21 的触摸必须走 goodix 路径**（若实机贴的是 focaltech 屏，则触摸在 Linux 侧不可用，除非能找到 FTS 驱动）。`goodix` 用 `input_mt_init_slots` / `input_mt_report_slot_state` / `input_mt_sync_frame`（模块字符串确认）→ **标准 evdev MT protocol B**，多点 + slot 上报。

面板与触摸的交叉约束：goodix 的 `touchscreen-size-x/y = 750/1334` 与 `nt35521z_750p` 匹配；focaltech 的 `display-coords = 720×1280` **不匹配** → 进一步支持"M21 贴 750×1334 屏 + goodix"的推断。

### 4.3 音频

```
SoC 级（dtb0）：/soc/spf_core_platform/sound  compatible="qcom,bengal-asoc-snd"
                bolero-codec / rx-macro / va-macro / rx_swr_master
Overlay 40：    snd_soc_dummy, fiio_config, fiio_wakeup
                mp: qcom,model = "bengal-idp-snd-card"
```

外置 DAC/放大器（`anolog_board`）：

```
cs43198@30/31/32/33   ← 4 颗，i2c-2，id 0..3
gw-fpga@36 (spi)      ← Gowin FPGA，firmware "gw_fpga_firmware_m21.fw"
fpga_audio_interface_hal
fiio_headset_jack     ← hs35_det_gpio=102, bal44_det=103, adc io-channel 18
anolog_board          ← 11 个 GPIO：dac_rst/outsel_bal/outsel_po/ang_pwr/dac_pwr/
                         dac_4v2_pwr/thx_hvcc_sw/out_en/po_pwr_en/bal_pwr_en/
                         lo_po_sel/lo_po_sw_en
```

`gw_fpga_firmware_m21.fw` 在 `/vendor/firmware/` 内（实测存在，与 `adsp.b00..b20`、`wlan/`、`wlanmdsp.otaupdate` 同目录）。

### 4.4 电源

```
fiio_charge_manager  fcm-chargers="sgm41510-charger", fcm-fuel-gauge="cw221X-bat"
                     fcm-battery-stat=2, poll=5000ms, fullbatt 4345mV/128000uA
charger@6B           sgm,sgm41510  (i2c-1, 0x6B)
cw221X@64            cellwise,cw221X (i2c-1, 0x64)
power_board          gpio: dc_bat_sw=19, battery_id=67, otg_sel=84,
                     pd_vbus_sw=106, otg_en=110；extcon=fusb302
fusb30x@22           fairchild,fusb302 (i2c-0)
aw35615@22           awinic,aw35615 (PD)
led                  gpio green=65 red=93 blue=112, led_vdd=2
pm6125_rtc           compatible="qcom,pm8941-rtc"（PMIC RTC）
```

### 4.5 按键

```
gpio_keys:
  volume_up    GPIO 96   KEY_VOLUMEUP     (115)
  volume_down  GPIO 97   KEY_VOLUMEDOWN   (114)
  pre_key      GPIO 108  KEY_PREVIOUSSONG (165)
  next_key     GPIO 27   KEY_NEXTSONG     (163)
  play_key     GPIO 24   KEY_PLAYPAUSE    (164)
  key_rev      GPIO 75   KEY_TV(0x179=377)
headset-adc-keys (模拟耳机线控键): vol_down/vol_up/vol_media(KEY_MEDIA=226)
fiio_sw_hold   GPIO 18   ← HOLD 拨杆
fiio_external_key：detsw_en=21, outside_hold=32, hall_det=109, ext_key_det(ADC ch 20)
```

`sys/module` 实测（JM21 `docs/01`）证明 `fiio_gpio_key`、`fiio_sw_hold`、`fiio_externel_key` 三者都会注册 input 设备。

---

## 5. 与 H700 / RG34XX 的差异

| 维度 | H700 (RG34XX) | M21 (SM6225) | 影响 |
|---|---|---|---|
| 内核版本 | 厂商 **4.9.170** | 厂商 **5.15.41 GKI** | 4.9 有 `/dev/fb0`；5.15 GKI **没有 `CONFIG_FB`** |
| 内核来源 | 全志 | Qualcomm，**GKI + vendor_dlkm** | 驱动全是 .ko，必须配齐加载顺序 |
| 显示子系统 | sun4i DRM（TCON/DE2）或 fbdev | **msm/SDE + DSI**（`msm_drm.ko` 39.7 MB） | 完全不同的 API 与面板描述方式 |
| 显示节点 | `/dev/fb0`（无 `/dev/dri`） | **`/dev/dri/card0`**（SDE KMS），`/dev/fb0` **预期不存在**（见 §6） | PocketJS 必须走 DRM 后端 |
| 面板定义 | 通用 `panel-mipi-dpi-spi` + `.panel` 固件文件 | 面板是**编译进 `msm_drm.ko` 的 DT 节点** | 换屏需重编 msm_drm（或只改 DTBO） |
| 触摸 | **无**（`# CONFIG_INPUT_TOUCHSCREEN is not set`） | goodix GT9xx + `ts_core`，MT protocol B | **M21 反而更完整** |
| 音频 | SoC 内置 `sun4i-codec` | LPASS/Bolero + WCD937x + **外置 4×CS43198 + FPGA** | 需要 20+ 个 techpack 模块按序加载 + ADSP 固件 |
| 音频用户空间 | 直接 `hw:audiocodec`，无 Pulse/PipeWire | Android 用 **tinyalsa**（`libtinyalsa.so` 存在），**无 `libasound.so.2`** | BaseOS 必须自带 ALSA 用户态 |
| 电源 | AXP2202（`/sys/class/power_supply/axp2202-battery`） | PM6125 + **SGM41510 + CW221X + FUSB302/AW35615**（FiiO 自定义驱动） | 电池节点名字完全不同 |
| 引导 | boot0 + U-Boot，**extlinux.conf**，SD 即系统盘 | ABL + fastboot，**GPT + A/B + AVB** | 引导方案完全不同（见 boot-chain.md） |
| 可刷性 | 只刷 SD 卡，机器内部不动 | 需解锁 + 写分区（或 init_boot） | 风险模型不同 |
| 模块 ABI | `4.9.170 ... modversions` | `5.15.41-g...-dirty ... modversions` | 都需要 vermagic+CRC 完全匹配 |

**关键差异（会决定工作量）**：

1. **H700 靠 fbdev，M21 靠 DRM**。PocketJS 两个后端都有（`platforms/linux/{drm,fbdev}`），但 DRM 后端要求 KMS 可用 + dumb buffer 可分配 + 有匹配 profile 的 mode。`msm_drm.ko` 有 `msm_gem_dumb_create`、`msm_gem_prime_import`、`drm_atomic_*`（符号确认），具备条件。
2. **H700 的 PJOS 补丁全是 sunxi 专有**（`src/h700-speaker-amp`、`h700-late-usb`、`axp-off`、`baseos-regs` 读 DE/TCON 寄存器）。这些在 M21 上**一个都用不了**。
3. **M21 的 `vendor_dlkm` 有 226 个 .ko**，H700 的 rootfs 只带 2 个 `.ko`（`h700_late_usb.ko`、`mali_kbase.ko`）。BaseOS 在 M21 上必须处理"几十个模块的加载顺序"，`modules.load` / `modules.softdep` 必须照抄（`evidence/vendor-dlkm-modules.load`）。

---

## 6. 关键发现：stock kernel **没有 framebuffer**

这是本轮最重要的技术发现，直接改变 PocketJS 的落地方式。

```
CONFIG_DRM=y
CONFIG_DRM_MIPI_DSI=y
CONFIG_DRM_KMS_HELPER=y
CONFIG_DRM_PANEL=y
# CONFIG_DRM_MSM is not set        ← msm_drm 是 .ko
# CONFIG_FB is not set             ← 整个 fbdev 子系统都不在内核里
# CONFIG_SYSFB_SIMPLEFB is not set
  （config 中不存在 "DRM_FBDEV_EMULATION" 这一行）
```

`msm_drm.ko` 的未定义符号里**没有** `drm_fbdev_generic_setup`、`register_framebuffer`、`fb_helper_*`（`nm -u msm_drm.ko` 只查到 `backlight_device_*`）。内核对 `drm_fbdev_generic_setup` / `register_framebuffer` 也**没有导出**（在 `boot.img` 的 kernel 里 `find` 两者都是 -1）。

结论：**M21 上不存在 `/dev/fb0`**（正常情况下）。而 H700 上 **只**有 `/dev/fb0`。这正是两端的分水岭：

| 设备 | 显示节点 | PocketJS 后端 |
|---|---|---|
| H700/RG34XX | `/dev/fb0`（无 `/dev/dri`） | `platforms/linux/fbdev` |
| **M21** | **`/dev/dri/card0`**（无 `/dev/fb0`） | **`platforms/linux/drm`** |

`platforms/linux/drm` 已存在并被 H700 构建包含（只是运行期回退到 fbdev）。所以**不需要新写后端**，但需要：
1. 一个能匹配 750×1334 的 profile（`physicalViewport: [750,1334]`）；
2. 触摸坐标 ≤ 1024 的约束（见 `display-touch.md`）；
3. 若实机无 `card0`，则需自定义内核加 `CONFIG_DRM_FBDEV_EMULATION`（可能，因为 `MODULE_SIG_FORCE` 未设，见 §2.3）。

### 6.1 附：`msm_drm.ko` 是否含面板驱动

`strings msm_drm.ko | grep '* video mode dsi panel'` → **0 命中**；`nt35521z`/`td4310`/`yx60031` 等**全部 0**。
但 `dsi_panel_parse_*` 系列函数（`dsi_panel_parse_gpios`、`dsi_panel_parse_dsc_params`、`dsi_panel_parse_phy_timing` …）都在，且能读 `qcom,mdss-dsi-panel-name`。

→ **面板参数来自 DT（DTBO），驱动是通用的 DSI 面板解析器**。这是 Qualcomm 的 "single panel driver + DT panel data" 模型。因此**改屏只需改 DTBO，不需要重编 msm_drm**——这对 M21 极其有利（DTBO 可以 `fastboot flash dtbo`，且 8.4 MB 分区，不涉 AVB 链外的复杂操作）。

---

## 7. 待实机验证

| # | 命令 | 期望 | 说明 |
|---|---|---|---|
| K1 | `adb shell cat /proc/version` | `5.15.41-android13-8-g9ded8564ff52-dirty` | 确认版本 |
| K2 | `adb shell cat /proc/config.gz \| gunzip \| diff - evidence/...` | 与本文 config 一致 | 确认同一构建 |
| K3 | `adb shell ls /proc/device-tree/firmware/android/` | `qhardware`, `hardware` | 确认 bootconfig 落地 |
| K4 | `adb shell cat /proc/device-tree/qcom,board-id \| xxd` | 与 entry 40/12 之一匹配 | **确认 M21 用哪条 overlay** |
| K5 | `adb shell ls -l /sys/bus/i2c/devices/` | 看到 `2-0030`..`2-0033`（CS43198）、`3-005d`（goodix）或 `3-0038`（fts） | **确认触摸 IC 是 goodix 还是 focaltech** |
| K6 | `adb shell ls /sys/class/drm/` | `card0`, `card0-DSI-1` | 确认 DRM 拓扑 |
| K7 | `adb shell cat /sys/class/drm/card0-DSI-1/modes` | `750x1334` | 确认面板模式 |
| K8 | `adb shell ls /sys/class/backlight/` | `panel0-backlight`（OrangeFox 用此路径） | 确认背光节点 |
| K9 | `adb shell dmesg \| grep -iE 'fts\|goodix\|nt35521'` | 一行驱动 probe 日志 | 确认实际控制器 |
