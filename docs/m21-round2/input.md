# ⑤ 输入：物理按键、旋钮、容量键 → PocketJS Input API

调查日期：2026-10-30。无实机。DT 证据见 `evidence/m21-dtbo-entry40-khajew-idp-nopmi.dts`。

---

## 1. 结论先行

| 问题 | 结论 | 置信度 |
|---|---|---|
| 物理按键 | **6 个 gpio-keys**：VOL+ / VOL− / PREV / NEXT / PLAY / `key_rev` | 高（DT） |
| `key_rev` 是什么 | DT 里 `linux,code = 0x179 = KEY_TV(377)`，`gpio = 75`，下降沿。**推断**是 FiiO 的"多功能键"（规格页写 "Multifunction button*1"） | 中 |
| HOLD 拨杆 | `fiio_sw_hold`（GPIO 18）——**不是 input 设备**，是 FiiO 私有驱动 | 高 |
| D.MODE 拨杆 | 规格页写有；DT 未见独立节点 → **推断**走 `fiio_external_key`（`detsw_en=21`） | 低 |
| 旋钮/滚轮 | **没有**。M21 无 rotary encoder 节点，规格页写 "Volume control type: Button control" | 高 |
| 容量键 | N/A（这是手机概念）。M21 无 | 高 |
| 耳机线控 | `headset-adc-keys`：VOL+ / VOL− / `KEY_MEDIA`(226)，通过 PM6125 ADC 分压 | 高 |
| 触摸 | goodix GT9xx，标准 evdev MT-B | 高（见 display-touch.md） |
| **映射到 PocketJS** | 按键：**直接可用**（`input.buttons`）；触摸：**可用但受 10-bit 坐标约束** | 高 |

**一句话**：M21 的输入比 H700 **更完整**——6 个专用媒体键 + 触摸屏，全部是标准 evdev。PocketJS 的 evdev 解码器已经支持（按键表 768 项、触摸 MT-B）。**唯一的坑**：`KEY_TV(377)` 不在任何 PocketJS 语义按钮里，需要映射或忽略。

---

## 2. 按键全表

### 2.1 gpio-keys（`fiio_gpio_key` 驱动）

| DT label | GPIO | `linux,code` | 键名 | 物理位置（推断） |
|---|---|---|---|---|
| `volume_up` | 96 | `0x73` = 115 | `KEY_VOLUMEUP` | 侧面上 |
| `volume_down` | 97 | `0x72` = 114 | `KEY_VOLUMEDOWN` | 侧面下 |
| `pre_key` | 108 | `0xa5` = 165 | `KEY_PREVIOUSSONG` | 正面左 |
| `next_key` | 27 | `0xa3` = 163 | `KEY_NEXTSONG` | 正面右 |
| `play_key` | 24 | `0xa4` = 164 | `KEY_PLAYPAUSE` | 正面中 |
| `key_rev` | 75 | `0x179` = 377 | `KEY_TV` | 侧面/顶部（多功能） |

`gpio-key,wakeup` 全部设置 → **任意键可唤醒**（配合 suspend 用）。
`debounce-interval = 15 ms`。

### 2.2 headset-adc-keys（模拟耳机线控）

```
io-channels = <&pm6125_vadc 18>   io-channel-names = "pm6125_amux1_gpio3"
keyup-threshold-microvolt = 1152000 (1.152 V)
vol_down: press-threshold 400000 uV,  linux,code = 114
vol_up:   press-threshold 144000 uV,  linux,code = 115
vol_media: press-threshold 0 uV,      linux,code = 226 (KEY_MEDIA)
```

→ 3.5mm 有线耳机的线控可用（`KEY_MEDIA` 是单键耳机）。

### 2.3 HOLD 拨杆与外部键

```
fiio_sw_hold {
  compatible = "fiio,sw_hold";
  gpios = <&tlmm 18 0>;
  pinctrl-names = "default","sleep";
}
fiio_external_key {
  compatible = "fiio,external_key";
  detsw_en = <&tlmm 21 0>;
  outside_hold_gpio = <&tlmm 32 0>;
  hall_det_gpio = <&tlmm 109 0>;
  io-channels = <&pm6125_vadc 20>, io-channel-names = "ext_key_det";
}
```

`fiio_externel_key.ko` 的字符串揭示其功能集：

```
EXT_KEY_TYPE / EXT_KEY_TAPE_ADD / EXT_KEY_TAPE_RED
EXT_KEY_HOLD_LONGSHUT / EXT_KEY_HOLD_LONGEXIT
EXT_KEY_MY_FAV
ext_key_long_press_work1/2   (双长按工作队列)
hall_det (霍尔传感器)
```

→ **HOLD 拨杆 = `sw_hold`**（静音/锁键）；`external_key` 支持**长按**（长按关机 / 长按退出）、**磁带键**（RED/ADD，复古卡带壳上的按键）、**收藏键**，以及**霍尔传感器**（合盖检测，用于复古卡带保护壳）。

**这些不是标准 evdev**，是 FiiO 私有驱动 + sysfs。BaseOS 侧需要写一个小的适配层（读 sysfs 或注册 input）才能用。

### 2.4 sysfs 控制面

`fiio_underlay_modules.ko` 暴露 `/sys/devices/platform/soc/soc:fiio_attr/…`（JM21 dossiê `docs/18`）。`fiio_gpio_key.ko` 有 `input_keymap_entry` 与 `keycodemax` → **支持运行时改键码**（`EVIOCSKEYCODE` 或 sysfs）。

对 BaseOS 极有利：**可以在不重编驱动的情况下改键映射**。

---

## 3. PocketJS 侧：现有能力 vs 缺口

### 3.1 现有能力（已核实到源码行）

`rocknix/build.../platforms/linux/evdev/src/lib.rs`：

```rust
struct State {
    keys: [bool; 768],           // ← 键码表到 768，KEY_TV(377) 在范围内
    touches: [Touch; 16],
    pointer: [f32; 2],
    pointer_buttons: u32,
}
...
(1, key) if (key as usize) < self.current.keys.len() => {
    self.current.keys[key as usize] = value != 0      // 任意 EV_KEY
}
(3, 47) => { self.multitouch = true; self.slot = value as usize; }        // ABS_MT_SLOT
(3, 57) => { ... tracking = Some(value); }                                // ABS_MT_TRACKING_ID
(3, 53 | 54) => { ... x/y }                                               // ABS_MT_POSITION
(1, 330) if !self.multitouch => { ... BTN_TOUCH }                          // 单点回退
```

**结论**：evdev 层是"全量按键 + MT-B"，**不需要为 M21 改任何代码**。

映射到 PocketJS 语义按钮（`pocket_spec::btn`）的是上层。H700 的补丁 `PJOS-LINUX/src/apply-pocketjs-input.py` 就是干这个的——但那套补丁**是针对 H700 树外 DTB 的键码**（`BTN_SOUTH/WEST/...`），M21 的键码完全不同（`KEY_MEDIA` 系列）。

### 3.2 缺口清单

| # | 缺口 | 影响 | 工作量 |
|---|---|---|---|
| I1 | `KEY_PLAYPAUSE/PREVIOUSSONG/NEXTSONG` → PocketJS 的 `btn::START/LTRIGGER/RTRIGGER/...` 映射未定义 | 6 个键用不上 | 小（一张表） |
| I2 | `KEY_TV(377)` 无语义 | `key_rev` 用不上 | 小（映射成 MENU 或忽略） |
| I3 | 音量键是"系统键"，默认可能被 Runtime 当普通 key 吞掉 | 音量不变 | 小（映射到 audio.setVolume） |
| I4 | 触摸逻辑视口必须 ≤1024（750×1334 超限） | 触摸不可用 | 中（需 375×667@2x profile） |
| I5 | HOLD / D.MODE / 霍尔 / 长按 都不是 evdev | 这些功能缺失 | 中（写 sysfs 适配） |
| I6 | `keyboardd` 无 evdev 桥（`docs/KNOWN-LIMITS.md:17-18` "no evdev bridge is included"） | 软键盘无法用物理键驱动 | 小（M21 有触屏，非必需） |

### 3.3 建议的映射表（草案）

| evdev | PocketJS 语义 | 说明 |
|---|---|---|
| `KEY_PLAYPAUSE` (164) | `btn::START` 或专用 `play_pause` | Music Player 主操作 |
| `KEY_PREVIOUSSONG` (165) | `btn::LTRIGGER`（或专用 `prev`） | |
| `KEY_NEXTSONG` (163) | `btn::RTRIGGER`（或专用 `next`） | |
| `KEY_VOLUMEUP` (115) | 不映射到按钮 → 直接调 `audio.setVolume(+1)` | 系统级 |
| `KEY_VOLUMEDOWN` (114) | 同上 | |
| `KEY_TV` (377) | `btn::MENU`（需 PocketJS 有 MENU 语义）或忽略 | 待定 |
| `KEY_MEDIA` (226) | 同 `PLAYPAUSE`（耳机线控） | |
| 触摸 MT-B | 原生 touch 事件 | 需要 375×667@2x |

确认 PocketJS 有哪些 `btn::` 常量（`pocket_spec::btn`）→ `CROSS`/`CIRCLE`/`SQUARE`/`TRIANGLE`/`LTRIGGER`/`RTRIGGER`/`START`/`SELECT`/`UP/DOWN/LEFT/RIGHT`（从 H700 补丁的 `old` 段可见）。**没有 `play_pause` 语义** → 建议用 `START`（在媒体上下文里语义自明），或提议 PocketJS 增加 `media.*` 按钮位。

---

## 4. 与 H700 的输入对比

| 项 | H700 / RG34XX | M21 |
|---|---|---|
| 按键数 | 12+（ABXY、十字、L/R、Start/Select、Menu、音量） | **6**（VOL±、PREV、NEXT、PLAY、key_rev）+ 耳机 3 |
| 键码风格 | `BTN_SOUTH/EAST/WEST/NORTH`（304-311） | `KEY_MEDIA` 系列（163-165, 114-115, 226, 377） |
| 触摸 | ❌ 无（`# CONFIG_INPUT_TOUCHSCREEN is not set`） | ✅ goodix MT-B |
| 摇杆 | ❌ 无（RG34XX 有 D-pad 无摇杆） | ❌ 无 |
| 旋钮 | ❌ 无 | ❌ 无 |
| HOLD 拨杆 | 有（部分机型），evdev 上报 | `fiio_sw_hold`（**非** evdev） |
| 键码可改 | 需重刷 DTB 或用 patch | ✅ `input_keymap_entry` 支持运行时改 |
| 对 PocketJS 的适配 | 需 patch 键码表（`apply-pocketjs-input.py`） | 只需**新增**一张映射表（不改解码器） |

**净结论**：M21 的按键**数量少但语义好**（媒体键对音乐播放器是天然的），且触摸补齐了导航能力。**不需要** H700 那种"改 DTB 键码 + patch Rust 解码器"的重活。

---

## 5. 输入路径全景（BaseOS 侧）

```
gpio_keys ─────┐
headset-adc ───┼─► evdev /dev/input/eventN ─► PocketJS evdev decoder
goodix MT ─────┘                                     │
                                                     ▼
fiio_sw_hold ──┐                              semantic buttons + contacts
fiio_external ─┼─► sysfs /sys/.../soc:fiio_attr/ ─► (需要自写 DAL)
fiio_gpio_key ─┘
```

BaseOS 侧只需要：
1. 挂载 `/dev/input`（devtmpfs，`CONFIG_DEVTMPFS` 状态见 power.md）；
2. 把 2–3 个 `eventN` 传给 `pocket-linux-kms --input`（支持最多 16 个源）；
3. （可选）写一个 `fiio-inputd` 读 sysfs，把 HOLD/长按转成 evdev `uinput`（`CONFIG_INPUT_UINPUT=y` **已编入**，见 kernel config）。

---

## 6. 待实机验证

| # | 命令 | 期望 | 用途 |
|---|---|---|---|
| I1 | `adb shell ls /dev/input/` + `cat /proc/bus/input/devices` | 看到 `gpio-keys`、`gpio_keys`、`goodix`、`fiio_gpio_key` | **确认设备数量与名称** |
| I2 | `adb shell getevent -lp /dev/input/eventX`（逐个） | `KEY_VOLUMEUP` … `KEY_TV` 全在 | 确认键码 |
| I3 | `adb shell getevent -lt` + 手按各键 | 事件序列 | 确认去抖/重复 |
| I4 | `adb shell cat /sys/devices/platform/soc/soc:fiio_attr/*/*` | FiiO 私有属性 | 拿到 HOLD/长按的读取方式 |
| I5 | 拨 HOLD，观察 `dmesg` + `/sys/.../sw_hold` | 状态变化 | 确认 HOLD 语义 |
| I6 | `adb shell ls /sys/class/input/` | `input0..inputN` + name | 交叉验证 |
| I7 | `adb shell dumpsys input` | 设备→keylayout 映射 | 确认 Android 侧用 `gpio-keys.kl` 还是 vendor 覆盖 |
