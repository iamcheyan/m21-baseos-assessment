# ③ 显示与触摸

调查日期：2026-10-30。无实机。DT 证据在 `evidence/m21-dtbo-entry40-khajew-idp-nopmi.dts`。

---

## 1. 结论先行

| 问题 | 结论 | 置信度 |
|---|---|---|
| 分辨率 | **750 × 1334**（`panel-width=0x2ee`、`panel-height=0x536`） | 高（DT）+ 高（官方规格 [S1]） |
| 尺寸 / DPI | 4.7"，**≈326 ppi**（计算值）；Android 密度档应为 **xhdpi(320)** 或 **xxhdpi(480)**，未见 `ro.sf.lcd_density` | 中（推断） |
| 刷新率 | **60 Hz**（`panel-framerate=0x3c`） | 高 |
| 面板型号 | `nt35521z_750p`（`nt35521z hk 750p` 为变体） | 高（DT） |
| 面板驱动形态 | 通用 DSI 面板解析器 + DT 数据；`msm_drm.ko` 内**无面板名硬编码** | 高 |
| 触摸控制器 | **goodix GT9xx @ i2c 0x5d**（推断）；`focaltech@38` 亦声明但**驱动不在任何镜像里** | 高（节点）/中（实际贴片） |
| 触摸协议 | **标准 evdev MT protocol B**（`input_mt_init_slots`/`input_mt_report_slot_state`/`input_mt_sync_frame`），5 点 | 高（模块符号） |
| 旋转 | DT 里 `swap-x2y=0`、`inversion-x=0`；Android 侧 `persist.demo.hdmirotationlock=false`。**M21 是竖屏 750×1334 原始方向** | 中 |
| 背光 | PWM（`bl_ctrl_pwm`），1..4095 级；OrangeFox 用 `/sys/class/backlight/panel0-backlight/brightness`（255 级） | 高（DT）/中（节点名） |
| 熄屏 | `qcom,mdss-dsi-off-command` + `panel_event_notifier.ko`（DPMS 事件） | 高 |
| **PocketJS 最小显示路径** | **DRM/KMS（`/dev/dri/card0`）**，非 fbdev | 高 |

**一句话**：显示是标准 Qualcomm SDE/DSI + DT 面板数据，**M21 上不存在 `/dev/fb0`**，PocketJS 必须用 DRM 后端；触摸是标准 evdev MT-B，但只有 goodix 驱动可用。

---

## 2. 显示：三层证据

### 2.1 面板时序（DT，`nt35521z_750p`）

| 属性 | 值 | 含义 |
|---|---|---|
| `panel-type` | `dsi_video_mode` | 视频模式（非 command mode），持续刷新 |
| `panel-width` / `height` | 750 / 1334 | 物理像素 |
| `panel-framerate` | 60 | Hz |
| `bpp` | 24 | DSI 像素格式 RGB888 |
| `display-topology` | `<1 0 1>` | 1 个 LM、无 DSC、1 个 intf |
| `h-pulse/front/back` | 32 / 36 / 36 | 行时序 |
| `v-pulse/front/back` | 2 / 9 / 7 | 帧时序 |
| `bl-pmic-control-type` | `bl_ctrl_pwm` | 背光走 PMIC PWM |
| `bl-max-level` / `min` | 4095 / 1 | 12 bit 占空比 |
| `reset-sequence` | `1 20 0 10 1 20` | 复位时序（ms） |
| `5v-boost-gpio` | 28 | 面板 5V 升压使能 |
| `platform-reset-gpio` | 82 | 面板复位 |
| `te-using-te-pin` | (空) | 视频模式不需要 TE |

DPI 计算：`√(750² + 1334²) / 4.7 = 325.6`。

### 2.2 面板选择（FiiO 私有）

```
lcd_id    → 4 bit 硬件 ID，GPIO 111/60/54/31
lcm-panel-node → 4 条候选，按 ID 选 dtbo 里的 panel 节点名
```

⚠ 已发现缺陷：`panel@panel1 = "qcom,mdss_dsi_td4310_1080p_video"` 但该节点在 **42 个 DTBO entry 里均不存在**（脚本对每个 entry 提取 `qcom,mdss_dsi_*_video {`，只有 11 个名字）。这是厂商遗留悬空引用；M21（750×1334）不依赖它。

### 2.3 背光与熄屏

| 能力 | 路径/机制 | 证据 |
|---|---|---|
| 背光亮度 | PMIC PWM（`pm6125_pwm`），DT `bl_ctrl_pwm` | DT + `dtb0` 有 `qcom,pwms@b300` |
| 背光 sysfs | 预期 `/sys/class/backlight/panel0-backlight/brightness`（0..255） | OrangeFox `BoardConfig.mk:82-84` 明确用此路径 + `TW_MAX_BRIGHTNESS=255` |
| 熄屏 | DSI off command `[05 01 00 00 0a 00 02 28 00 / 05 01 00 00 05 00 02 10 00]`（display off / sleep in） | DT |
| 面板事件 | `panel_event_notifier.ko`（`DRM_PANEL_EVENT_UNBLANK/BLANK/BLANK_LP/FPS_CHANGE`） | 模块字符串 |
| 双击唤醒 | 规格页写 "Double tap to wake up: Supported" [S2]；DT 无独立节点 → 走 touch 驱动 `goodix,slide-wakeup=1` | 中 |

**`goodix,slide-wakeup = 1`** 说明触摸控制器本身能作为唤醒源。对 BaseOS 的息屏策略有用。

---

## 3. 触摸

### 3.1 驱动可用性（关键结论）

| candidate | DT 声明 | 驱动模块在镜像里 | 实测痕迹 |
|---|---|---|---|
| `goodix,gt9xx` @ 0x5d | ✅ entry 40 fragment 19，`status="okay"` | ✅ `goodix_gt9xx_ts.ko` (1,433,248 B) | JM21 `i2cdetect` 见 `3-005d gt9xx` |
| `focaltech,fts` @ 0x38 | ✅ entry 40 fragment 40，`status="okay"` | ❌ **全盘 0 命中** | JM21 `i2cdetect` 见 `3-0038 fts` |
| synaptics/novatek | ✅ 但 `status="disabled"` | ❌ | — |

扫描方法与结果（可复现）：

```
# 对 226 个 .ko 逐个 cat 后 grep
$ for n in $(debugfs -R "ls /lib/modules" vendor_dlkm.img | tr -s ' ' '\n' | grep '\.ko$'); do
    debugfs -R "cat /lib/modules/$n" vendor_dlkm.img | grep -q focaltech && echo "HIT $n"; done
（无输出）

# 对整个分区原始字节扫描
$ grep -c -a focaltech vendor_dlkm.img    → 0
$ grep -c -a focaltech vendor.img         → 0
$ grep -c -a focaltech odm.img            → 0
$ grep -c -a focaltech system_dlkm.img    → 0
$ grep -c -a focaltech boot.img(kernel)   → 0

# kernel config
$ grep -i 'CONFIG_TOUCHSCREEN_STMFTS' kernel.config
# CONFIG_TOUCHSCREEN_STMFTS is not set
```

**判读**：FiiO 在 DT 里同时声明了 focaltech 和 goodix（同一块板可能有多个屏幕供应商），但**只编了 goodix 的驱动**。若某台 M21 贴的是 focaltech 屏 → Linux 侧无触摸（除非补驱动，而 FTS 有开源主线驱动 `CONFIG_TOUCHSCREEN_FTS`，可自编模块加载，因为 `MODULE_SIG_FORCE` 未设）。

⚠ 注意：JM21 的 `i2cdetect` 显示**两个地址都有应答**（`3-0038 fts` 与 `3-005d gt9xx`），这可能是 i2c 总线上的误判（某些地址被多个 chip 占用）或板上有双控。**实机必须用 `dmesg` 与 `/proc/bus/input/devices` 确认谁真的注册了 input 设备**。

### 3.2 协议：标准 evdev MT-B

`goodix_gt9xx_ts.ko` 引用的符号（`strings`）：

```
input_mt_init_slots
input_mt_slot
input_mt_report_slot_state
input_mt_sync_frame
input_mt_sync
input_set_abs_params
input_set_capability
```

→ **protocol B**（slot + tracking id），标准多点触控。参数：

```
touchscreen-max-id  = 0x0b   (11)   ← 分配的 contact id 空间
touchscreen-size-x  = 0x2ee  (750)
touchscreen-size-y  = 0x536  (1334)
touchscreen-max-w   = 0x200  (512)
touchscreen-max-p   = 0x200  (512)
touchscreen-key-map = <0x44 0xa5 0xa4 0xa3 0x57 0x58>
                      = KEY_F10 / KEY_PREVIOUSSONG / KEY_PLAYPAUSE / KEY_NEXTSONG / KEY_F11 / KEY_F12
goodix,type-a-report = 0    ← protocol B（type A 会是 1）
goodix,int-sync      = 1
goodix,esd-protect   = 1
```

实际触点数上限：`focaltech,max-touch-number=5`（FTS 侧），goodix 侧由 `touchscreen-max-id=11` 决定 internal slot，但通常实配 5 点。

### 3.3 对 PocketJS 的含义

PocketJS 的 evdev 解码器（`platforms/linux/evdev/src/lib.rs`）已经实现 protocol B：

```rust
(3, 47) => { self.multitouch = true; self.slot = value as usize; }   // ABS_MT_SLOT
(3, 57) => { ... self.current.touches[self.slot].tracking = Some(value); }  // ABS_MT_TRACKING_ID
(3, 53 | 54) => { ... x/y }                                          // ABS_MT_POSITION_X/Y
(3, 0 | 1) if !self.multitouch => { ...x/y }                         // ABS_X/ABS_Y fallback
(1, 330) if !self.multitouch => { ... BTN_TOUCH }
```

**所以不需要写触摸驱动适配**，只需要：
1. 内核侧 goodix 驱动能 probe；
2. 传给运行时的 `AxisRange` 是 0..750 / 0..1334；
3. **profile 的 `input.touch` 约束**：见下。

### 3.4 ⚠ 硬约束：触摸坐标必须 ≤ 1024

用真实 PocketJS 校验器跑的结果（`rocknix` 构建树 `framework/src/profile.ts`）：

```
$ bun pv.ts
input.buttons                      => {"ok":true}
input.buttons,input.touch          => [{"code":"profile.touchViewport",
    "path":"/display/logicalViewports/1",
    "message":"touch coordinates must fit the 10-bit frame encoding"}]
```

验证边界：

```
logical 750x1024 => true
logical 750x1025 => [{"code":"profile.touchViewport","path":"/display/logicalViewports/0",...}]
```

**M21 的物理高度 1334 > 1024。** 这意味着：

- `physicalViewport: [750, 1334]` 可以（物理不受限）；
- 但**任何**声明了 `input.touch` 的 profile，其 `logicalViewports` 必须 ≤ 1024。

可用方案（择一）：

| 方案 | logicalViewports | rasterDensity | 效果 |
|---|---|---|---|
| A. 半分辨率逻辑视口 | `[[375, 667]]` | **2** | 750×1334 物理 = 375×667 逻辑，2× 采样。触摸 667 ≤ 1024 ✅ |
| B. 1:1 但裁到 1024 | `[[750, 1024]]` | 1 | 浪费 310 px |
| C. 不声明 `input.touch` | `[[750,1334]]` | 1 | 只能用按键（浪费触屏） |

**推荐 A**：`[375, 667] @ rasterDensity 2`。这既满足 10-bit 约束，又让 UI 元素获得 2× 采样（小屏高 DPI 本来就需要 2×）。已用真实校验器验证通过（见 `SPEC.md` 与 `evidence/profile-validate.log`）。

---

## 4. PocketJS 最小显示路径

```
/dev/dri/card0
   └ CRTC ← connector "DSI-1" ← mode "750x1334"
        ← plane ← dumb buffer (msm_gem_dumb_create)
        ← page flip (DRM_IOCTL_MODE_PAGE_FLIP)
```

依赖链：

| 环节 | M21 状态 | 依据 |
|---|---|---|
| `/dev/dri/card0` | 需加载 `msm_drm.ko`（39.7 MB，8 个依赖模块） | `modinfo` depends 链 |
| KMS modeset | `drm_atomic_*` 全套符号在 | `nm` |
| dumb buffer | `msm_gem_dumb_create` / `msm_gem_mmap` 在 | `nm msm_drm.ko` |
| mode 匹配 | `dsi-display-primary` 的 mode 来自面板 DT | DT |
| 输入 | `/dev/input/eventN`（goodix 注册） | 模块符号 |
| 触摸坐标 | `AxisRange 0..750 / 0..1334`，逻辑视口 ≤1024 | PocketJS 校验器 |

**为何不用 fbdev**：见 `kernel.md` §6 —— `CONFIG_FB` 未编入内核、`DRM_FBDEV_EMULATION` 不存在、`msm_drm.ko` 不引用 `drm_fbdev_generic_setup`。所以 `/dev/fb0` 在 M21 上不存在。

**若 DRM 走不通的兜底**：自编内核加 `CONFIG_DRM_FBDEV_EMULATION=y`（`MODULE_SIG_FORCE` 未设，且 Plan-B 已验证自编内核可启动）。但这会引入"自定义内核"这条额外风险，**只在 DRM 实测失败后才考虑**。

---

## 5. 与 H700 的对比（同一套 PocketJS）

| 项 | H700 | M21 |
|---|---|---|
| 节点 | `/dev/fb0` | `/dev/dri/card0` |
| 后端 crate | `pocket-linux-fbdev` | `pocket-linux-drm` |
| 分辨率 | 720×480（横屏） | 750×1334（竖屏） |
| 旋转 | `panel_rotation_ccw: 0` | 0（DT 未设 swap/inversion），**竖屏** |
| 触摸 | ❌ 无 | ✅ goodix MT-B |
| 触摸约束 | N/A | 逻辑视口 ≤1024 → 需 375×667@2x |
| 撕裂/双缓冲 | fbdev 已实现，真机未确认帧率 | DRM page-flip 原生垂直同步 |
| 背光 | 无 `/sys/class/backlight`，走 Allwinner `disp2` ioctl | 标准 `/sys/class/backlight/panel0-backlight` |

**净结论**：M21 在显示/触摸上**比 H700 更标准**（DRM + evdev MT + 标准 backlight class），但**方向不同**（竖屏 750×1334 vs 横屏 720×480），需要 PocketJS 侧新增一个竖屏 profile，而不是复用 `rocknix-h700-kms`。

---

## 6. 待实机验证

| # | 命令 | 期望 | 失败含义 |
|---|---|---|---|
| D1 | `adb shell cat /sys/class/drm/card0-DSI-1/modes` | `750x1334` | 面板不是 nt35521z |
| D2 | `adb shell cat /sys/class/drm/card0-DSI-1/status` | `connected` | DSI 链路问题 |
| D3 | `adb shell ls /sys/class/backlight/` | `panel0-backlight` | 背光节点名不同 |
| D4 | `adb shell cat /sys/class/backlight/*/max_brightness` | `255` 或 `4095` | 决定 DAL 的映射（4095 是 DT 值，255 是 OrangeFox 值） |
| D5 | `adb shell cat /proc/bus/input/devices` | 有 `goodix` 或 `fts` 的 input 设备 | **决定触摸是否可用** |
| D6 | `adb shell getevent -lp /dev/input/eventN` | 列出 `ABS_MT_POSITION_X/Y`，范围 0..750/0..1334 | 确认 MT 参数 |
| D7 | `adb shell getevent -lt` + 手指滑动 | 连续 slot 事件 | 确认 protocol B 实际工作 |
| D8 | `adb shell wm size` / `wm density` | `750x1334` / 密度值 | 拿到 Android 实际密度，用于选定 `rasterDensity` |
| D9 | `adb shell dumpsys display \| grep -i fps` | 60 | 确认刷新率 |
