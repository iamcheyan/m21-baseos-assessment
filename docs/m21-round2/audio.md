# ④ 音频：ALSA / PulseAudio / 耳机 / 蓝牙 / DAC 模式

调查日期：2026-10-30。无实机。音频是 M21 最复杂、也是整条路线最大的未知项。

---

## 1. 结论先行

| 问题 | 结论 | 置信度 |
|---|---|---|
| ALSA 在内核侧可用吗 | **可用**。`CONFIG_SND=y`、`CONFIG_SND_SOC=y`、techpack 模块（`machine_dlkm`、`bolero_cdc_dlkm`、`wcd937x_dlkm`、`swr_*`、`spf_core_dlkm`、`adsp_loader_dlkm` …）全在 `vendor_dlkm` | 高 |
| 声卡名 | `bengal-idp-snd-card`（DT `qcom,model`）；`machine_dlkm.ko` 的 of alias 是 `qcom,bengal-asoc-snd` | 高 |
| 用户态 ALSA 库 | **`libasound.so.2` 不存在**（`vendor.img`/`system.img` 均 0 命中）；Android 用 **`libtinyalsa.so`** | 高 |
| PulseAudio | 不存在 | 高 |
| PipeWire | 不存在 | 高 |
| 耳机检测 | `fiio_headset_jack`（`hs35_det_gpio=102`, `bal44_det=103`, ADC `dc_det1`）+ `fsa4480-i2c`（模拟开关） | 高 |
| 硬件音量 | 两套：① `cs43198.ko` 的 ALSA kcontrol（dB 级）② `fiio_gpio_key` 的 `KEY_VOLUMEUP/DOWN` | 高 |
| DAC 模式 | 4×CS43198 经 FPGA（`gw-fpga`）从 SoC I2S 取数；DSD 由 `dac_core_module` 切 | 高（结构）/低（BaseOS 侧能否驱动） |
| 蓝牙 | `BT_QCA`/`BT_HCIUART_QCA` 编入内核；`persist.vendor.qcom.bluetooth.soc=cherokee`；BT 固件在独立 `bluetooth` 分区 | 高（组件）/中（BaseOS 侧可用性） |
| **BaseOS 侧风险** | **最高**。需要：20+ 模块按序 + ADSP 固件 + `mixer_paths` 路由 + 自建 ALSA 用户态 + FiiO 私有 sysfs 控制 | — |

**一句话**：音频的"硬件与驱动全都在"，但**用户态完全没有现成可用的栈**——Android 走 tinyalsa + HAL，BaseOS 必须自己搭 ALSA（或 tinyalsa）。这是整条路线里工作量最大、最可能卡住的一环。

---

## 2. 硬件拓扑（DT + 模块实测）

```
SoC LPASS (I2S/TDM)
   │
   ├─► Gowin FPGA (SPI, i2c-2 0x36, fw "gw_fpga_firmware_m21.fw")
   │      │  角色：音频数据的时钟/格式转换与路由（FiiO 私有）
   │      ▼
   ├─► CS43198 #0 (i2c-2 0x30, id=0) ─┐
   ├─► CS43198 #1 (i2c-2 0x31, id=1) ─┤  4× DAC，差分/并联
   ├─► CS43198 #2 (i2c-2 0x32, id=2) ─┤
   └─► CS43198 #3 (i2c-2 0x33, id=3) ─┘
                     │
                     ▼
            anolog_board (11 GPIO 控制)
              dac_rst=2, dac_pwr=79, dac_4v2_pwr=22, ang_pwr=86,
              outsel_bal=29, outsel_po=104, thx_hvcc_sw=85,
              out_en=20, po_pwr_en=69, bal_pwr_en=70,
              lo_po_sel=30, lo_po_sw_en=25
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
   OPA1692 ×2 + SGM8262-2 ×2   3.5mm PO/LO/SPDIF + 4.4mm BAL PO/LO
```

官方规格（[S2]）确认：`DAC: CS43198*4, Amp: OPA1692*2+SGM8262-2*2`，输出 `3.5mm PO/LO/SPDIF + 4.4mm BAL PO/LO`。

**注意**：JM21 是 2 DAC，M21 是 4 DAC（DT 里 4 个节点，模块名 `anolog_board_m21`）。所以 JM21 的音频实测数据**不能直接照搬**到 M21，但拓扑与驱动型号一致。

---

## 3. 模块清单与加载链

`vendor_dlkm` 里音频相关模块（`evidence/vendor-dlkm-module-list.txt`）：

```
machine_dlkm.ko            ALSA SoC machine driver, alias platform:bengal-asoc-snd
bolero_cdc_dlkm.ko         Bolero codec 核心
wcd937x_dlkm.ko            WCD937x codec
wcd937x_slave_dlkm.ko      WCD937x slave
wcd_core_dlkm.ko           WCD common
wcd9xxx_dlkm.ko
va_macro_dlkm.ko           VA macro
rx_macro_dlkm.ko           RX macro
tx_macro_dlkm.ko           TX macro
swr_dlkm.ko                SoundWire
swr_ctrl_dlkm.ko
spf_core_dlkm.ko           SPF (Audio DSP framework)
q6_dlkm.ko                 ADSP Q6
q6_notifier_dlkm.ko
q6_pdr_dlkm.ko
adsp_loader_dlkm.ko        ADSP 固件加载
snd_event_dlkm.ko
mbhc_dlkm.ko               Multi-button headset control
audio_pkt_dlkm.ko
audio_prm_dlkm.ko
audpkt_ion_dlkm.ko
pinctrl_lpi_dlkm.ko
gpr_dlkm.ko
qcom_q6v5.ko / qcom_q6v5_pas.ko   ADSP remoteproc
frpc-adsprpc.ko
```

FiiO 私有（`vendor_dlkm`）：

```
fiio_primary_modules.ko    1,416,776 B   所有 fiio_* 的基础
cs43198.ko                   401,880 B   Cirrus CS43198 codec（author: mxc@fiio.net）
dac_core_module.ko                       DAC 抽象 + DSD 切换
anolog_board_m21.ko          467,272 B   模拟板（GPIO 时序）
gw-fpga.ko                               Gowin FPGA
fpga_audio_interface.ko
fpga_interface.ko
fiio_headset_jack.ko         409,584 B   耳机/平衡检测
fiio_snd_soc_dummy_dai.ko    330,016 B   虚拟 DAI（"snd_soc_dummy"）
fiio_config.ko
fiio_underlay_modules.ko     658,264 B   sysfs `/sys/devices/platform/soc/soc:fiio_attr/…`
```

`machine_dlkm.ko` 的依赖（`modinfo -F depends`）：

```
snd_event_dlkm,fsa4480-i2c,wcd_core_dlkm,wcd937x_dlkm,bolero_cdc_dlkm,
audio_prm_dlkm,audpkt_ion_dlkm,spf_core_dlkm
```

**加载顺序**抄 `vendor_dlkm` 的 `modules.load`（`evidence/vendor-dlkm-modules.load`），它在 187/188 行附近按依赖排好：

```
q6_notifier_dlkm → spf_core_dlkm → … → q6_dlkm → adsp_loader_dlkm → …
→ swr_dlkm → swr_ctrl_dlkm → wcd_core_dlkm → wcd9xxx_dlkm
→ machine_dlkm → bolero_cdc_dlkm → … → wcd937x_dlkm → wcd937x_slave_dlkm
```

⚠ 注意 `modules.load` 里音频段**重复出现两次**（187-194 与 220-227），音频 techpack 被列了两遍。BaseOS 侧直接照抄不会被这个影响（第二次加载会返回 `EEXIST`），但说明厂商脚本不是完全干净。

---

## 4. ADSP 固件

`vendor.img:/firmware/` 内（实际目录列举）：

```
adsp.b00 … adsp.b20   （分段固件，由 qcom_q6v5_pas 加载）
a610_zap.b00/b01/b02  （GPU zap shader）
wlan/  wlanmdsp.otaupdate
gw_fpga_firmware_m21.fw   （FPGA bitstream）
```

`adsp.b*` 一共 21 段（无 b11，与 Qualcomm 分段惯例一致）。**BaseOS 需要把 `/vendor/firmware` 挂上或复制进 rootfs**，否则 ADSP 起不来 → 没有声卡。

---

## 5. 用户态：Android 的栈 vs BaseOS 需要的栈

### 5.1 Android 侧（现成，但我们用不上）

| 层 | 文件 | 说明 |
|---|---|---|
| HAL | `audio.primary.bengal.so`（HIDL 7.0） | 在 `/vendor/lib/hw/`（推断，未逐文件核） |
| 库 | `libtinyalsa.so`（`/lib/libtinyalsa.so` 29,340 B + `/lib64/` 45,016 B） | 直接 ioctl `/dev/snd/*` |
| 路由 | `/vendor/etc/mixer_paths_bengal_idp.xml`（3,722 行，810 个 `<ctl>`） | 声卡被当 **IDP** 用 |
| 策略 | `/vendor/etc/audio_policy_configuration.xml` | 采样率/设备/直通声明 |
| 属性 | `vendor.audio.hal.period_size=192`、`period_multiplier=3` | HAL 周期 |
| 无 | **`libasound.so.2`**（0 命中） | 说明 Android 侧完全不用 alsa-lib |

`libtinyalsa.so` 导出（`readelf -sW`）：

```
mixer_hw_open, mixer_ctl_get_value, mixer_ctl_get_percent, mixer_ctl_get_range_min/max,
mixer_read_event, pcm_open, pcm_write, pcm_close, pcm_get_htimestamp …
```

→ **tinyalsa 的 API 足以做播放与音量控制**，且它是轻量的（30–45 KB），非常适合 BaseOS。

### 5.2 BaseOS 需要的栈（三选一）

| 方案 | 组成 | 优点 | 缺点 |
|---|---|---|---|
| **A. 自带 alsa-lib + `aplay`** | 从 Alpine/Debian 交叉编或静态编 `alsa-lib` + `alsa-utils` | 生态最成熟，PocketJS 的 `--features alsa` 直接可用 | 需交叉编译；`alsa-lib` 约 1 MB |
| **B. 自带 tinyalsa** | 直接用 `libtinyalsa.so`（从 `/vendor` harvest）+ 自写 50 行播放器 | 极小，无编译 | 需自写 mixer/route 代码；PocketJS 的 alsa feature 用不了 |
| **C. PocketJS 内置 ALSA** | `pocket-linux-kms --features alsa`（`--pcm-test DEVICE` 已存在） | 不需要外部播放器 | feature 状态未知（见 pocketjs-gap.md） |

**推荐 A**（先求通）→ 再考虑 B 瘦身。

### 5.3 路由：必须处理的部分

`mixer_paths_bengal_idp.xml` 是 810 个 `<ctl>` 的集合，含 WCD937x 的标准路由（`HPHL_RDAC Switch`、`AUX_RDAC Switch`、`EAR_RDAC Switch` …）。

但我们**不是**走 WCD937x 的模拟输出——M21 的输出来自 4×CS43198，由 `cs43198.ko` 暴露自己的 ALSA kcontrol。`cs43198.ko` 的字符串：

```
cs43198_dac_dai_ops
cs43198_set_volume_db
cs43198_sw_mute
gain_pwr_update / gain_spe / pogain
filter / filters / filter_count
"[CS43198]: %s enter mute : %s"
"[CS43198]: %s, lvolume: 0x%02x, rvolume: 0x%02x, is_dsd = %d"
```

→ **kcontrol 名称需要实机 `amixer -c <card>` 才知道**（JM21 的 dossiê 记录了几个：`DAC Playback Volume`、`DAC line Out Volume`、`DAC Digital Filter Mode`、`DAC LR Balance`、`DAC PO Gain`，但这些是 `libfiioaudio.so` 里的名字，不一定是 hw kcontrol 名）。

**结论：BaseOS 侧音频必须先在实机上 `tinymix`/`amixer` 把 kcontrol 名字抓出来。** 这是不可跳过的步骤。

---

## 6. 耳机、蓝牙、硬件音量

### 6.1 耳机检测

```
fiio_headset_jack {
  compatible = "fiio,jack_det";
  hs-det-delay-ms = 150;
  io-channels = <&pm6125_vadc 18>, io-channel-names = "dc_det1";
  hs35_det_gpio = <102>;      hs35-det-threshold = 1;
  bal44_det = <103>;          bal44-det-threshold = 1;
  po-dc-det-max-threshold = 1200000uV;  po-dc-det-min-threshold = 300000uV;
  dc-det-filter-count = 10;
}
```

- 3.5mm 与 4.4mm 各有一个检测 GPIO，另有 ADC 做 DC 阻抗判断（识别耳机 vs 线路输出）。
- 模拟开关 `fsa4480-i2c`（0x42，SBU 切换）+ `aw35615`（PD）。
- **BaseOS 侧可通过 sysfs 读 jack 状态**（`fiio_underlay_modules` 暴露）。

### 6.2 蓝牙

| 组件 | 证据 |
|---|---|
| 内核：`CONFIG_BT=y`、`BT_HCIUART_QCA=y`、`BT_QCA=y`、`BT_HS` 未设 | kernel config |
| SoC：`persist.vendor.qcom.bluetooth.soc = cherokee` | vendor build.prop |
| 固件分区 | `fstab.emmc`: `/dev/block/bootdevice/by-name/bluetooth → /vendor/bt_firmware` (vfat) |
| 规格：BT 5.0，`AAC/SBC/aptX/aptX HD/LDAC/LHDC` 发送，`SBC/AAC/LDAC` 接收 [S2] | 官方 |
| 蓝牙音频 | `a2dp_audio_policy_configuration.xml`、`bt_fm_slim.ko`、`btpower.ko` | vendor |

**BaseOS 侧需要**：BlueZ + `bt_firmware` 分区挂载 + `btattach`/`hciattach` 到 QCA UART。JM21/JM21 社区未验证过。**推断**：可行，但需要 QCA 的 `.bin/.nvm` 从 `bt_firmware` 分区取。

### 6.3 硬件音量

两条独立路径：

1. **GPIO 键**（`gpio_keys`）：`vol_up` GPIO 96 → `KEY_VOLUMEUP`(115)；`vol_down` GPIO 97 → `KEY_VOLUMEDOWN`(114)。这是**内核 input 事件**，BaseOS 的 PocketJS 可以直接消费（见 input.md）。
2. **DAC 内部音量**（`cs43198.ko`）：`cs43198_set_volume_db` + 5 张 121 级音量表（JM21 dossiê 逆向出 `vol_table_po_gain_l/m/h/sh/uh`）。这是**音质关键**，Android 通过 `AudioSystem.setMasterVolumeDac` 调用 HAL。

**对 PocketJS 的含义**：`KEY_VOLUMEUP/DOWN` 可以映射到 UI 音量条，但**真正的 DAC 音量必须走 kcontrol**（否则只是软件衰减，损失动态范围）。

### 6.4 DAC 模式（Pure Music / USB DAC / DSD）

| 模式 | 机制 | BaseOS 可行性 |
|---|---|---|
| PCM（44.1k–768k） | 标准 ALSA hw_params → I2S → FPGA → CS43198 | 可行（需 kcontrol 配 MCLK 家族） |
| DSD native（64/128/256） | `cs43198` 的 `is_dsd` 分支 + `dac_core_module` 专用 ioctl | **需自写**，ALSA 无标准 DSD 接口 |
| USB DAC（当声卡给 PC） | `CONFIG_USB_CONFIGFS_F_UAC2=y` 已编入 | 可行（gadget 模式） |
| DoP/D2P | Android HAL 内实现 | 需移植 |
| MQA | FiiO 私有（`docs/40-mqa.md`） | 放弃 |

**建议**：BaseOS 第一阶段只做 **PCM 播放**。DSD/USB DAC 作为第二阶段。这与"Music Player"目标一致——先能听歌。

---

## 7. 与 H700 的音频对比

| 项 | H700 | M21 |
|---|---|---|
| codec | SoC 内置 `sun4i-codec` | 外置 4×CS43198 + FPGA + Bolero |
| 声卡 | `audiocodec`（card 0） | `bengal-idp-snd-card` |
| 用户态 | 直接 `hw:audiocodec` + `/etc/asound.conf` hooks 层 | 无 libasound；只有 `libtinyalsa` |
| 音量 | `amixer -c 0 sset 'digital volume' 63` 等 6 个控件 | `cs43198` kcontrol + 5 张 dB 表 |
| 耳机检测 | `h700_speaker_amp.ko` 私有（依赖内核符号偏移） | `fiio_headset_jack` + `fsa4480`（标准 i2c） |
| 需要模块数 | 1（`h700_speaker_amp.ko`） | **30+**（techpack + FiiO） |
| 已验证 | RG34XX 上 `aplay` 出声 | **无**（M21/JM21 都只在 Android 下验证过） |

**关键差异**：H700 的音频是"一个内核模块 + 一个 amixer 命令"；M21 是"一整个 Android audio techpack"。这是 BaseOS 落地的**最大工作量项**。

---

## 8. 待实机验证

| # | 命令 | 期望 | 用途 |
|---|---|---|---|
| A1 | `adb shell cat /proc/asound/cards` | `0 [bengalidpsndca]: bengal-idp-snd-card` | 确认声卡注册 |
| A2 | `adb shell cat /proc/asound/pcm` | 列出 playback/capture PCM | 拿到 PCM 设备号 |
| A3 | `adb shell tinymix -D 0` | 全部 kcontrol 列表 | **抓 kcontrol 名字（关键）** |
| A4 | `adb shell dmesg \| grep -iE 'cs43198\|machine_dlkm\|adsp'` | probe 成功日志 | 确认驱动起 |
| A5 | `adb shell ls /sys/devices/platform/soc/soc:fiio_attr/` | FiiO 私有 sysfs 树 | 拿到 BaseOS 侧控制入口 |
| A6 | `adb shell cat /sys/class/switch/*/state`（或 `/sys/class/extcon/`） | 耳机插拔状态 | 耳机检测路径 |
| A7 | `adb shell dumpsys media.audio_flinger \| head -40` | 输出设备/采样率 | 当前路由 |
| A8 | `adb shell getprop \| grep -i dsd` | `persist.sys.fiio.config.dsd.native=256` 等 | 确认 DSD 配置 |
| A9 | 播放 44.1/48/96/192 kHz 文件 + `tinymix` 抓 `is_dsd`/MCLK | 采样率跟随 | 确认 bit-perfect 路径 |
