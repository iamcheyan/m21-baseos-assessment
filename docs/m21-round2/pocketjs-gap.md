# ⑧ PocketJS 落地：BaseOS 侧需要提供什么，与 PJOS-LINUX 的差距

调查日期：2026-10-30。无实机。PJOS/rocknix 侧引用均来自只读仓库的源码行。

---

## 1. 结论先行

| 结论 | 内容 |
|---|---|
| PocketJS 需要的**核心**只有两样 | ① 一块能 mmap 的显示 surface（DRM 或 fbdev）② 一组 evdev 输入源 |
| 这两样 M21 都有 | DRM（`/dev/dri/card0`，需加载 `msm_drm.ko`）+ evdev（goodix + gpio-keys） |
| 音频**不是** PocketJS 核心的硬依赖 | H700 的 profile 只声明 `["input.buttons","text.glyphs.baked"]`，**没有** `audio.pcm`/`media.playback`；播放靠外部播放器 |
| 所以最小可用路径是 | **DRM 出画面 + evdev 收按键/触摸 + 外部播放器出声** |
| 与 PJOS-LINUX 的差距 | 见 §5 清单：**12 项**，其中 3 项是"现有实现直接失效"（fbdev 假设、devtmpfs 假设、sunxi 专有代码） |

**一句话**：PocketJS 本身对 M21 的适配成本**远低于预期**——runtime 已含 DRM/fbdev/evdev 三个后端，`--fb`/`--card`/`--input` 都是运行期参数。真正的工作量在 **BaseOS 层**（内核模块加载顺序、设备节点、音频栈），不在 PocketJS。

---

## 2. PocketJS 的实际需求（源码核实）

### 2.1 显示

`programs/linux-kms/src/main.rs` 的 CLI：

```
pocket-linux-kms [--package app.pocket] [--card /dev/dri/card0] [--fb /dev/fb0]
                 [--input /dev/input/eventN] [--frames N] [--check | --headless]
```

- 默认先试 DRM，失败回退 fbdev（帮助文本原文："DRM falls back to fbdev"）。
- **两个后端 crate 都在同一二进制里**：`pocket-linux-drm`、`pocket-linux-fbdev`（`Cargo.toml` 里都是非 optional 依赖）。

**对 M21**：只需给 `--card /dev/dri/card0`，无需 fbdev。

### 2.2 输入

- `--input` 可重复，最多 16 个源（`inputs.len() > 16` 报错）。
- 未指定时自动扫 `/dev/input`（`std::fs::read_dir("/dev/input")` 后排序）。
- 支持三类：`InputClasses::BUTTONS | POINTER | CONTACT`（触摸）。

**对 M21**：`--input /dev/input/eventX`（按键）+ `--input /dev/input/eventY`（goodix），或干脆自动扫。

### 2.3 profile（编译期）

`programs/linux-kms/src/main.rs` 的 `supported()`：

```rust
if profile.dynamic_viewport.is_some()
    || profile.auxiliary.is_some()
    || !INPUT_CLASSES.contains(profile.required_inputs) {
    return Err(...)
}
```

→ **只支持一个固定显示 + buttons/pointer/contact**。这正是 M21 的形态（单屏 750×1334 + 按键 + 触摸）。

### 2.4 音频

- `--features alsa` 编译期开关：`alsa = ["dep:pocket-linux-alsa"]`。
- H700 的构建**没开**这个 feature（profile 未声明 `audio.pcm`）。
- 所以 PocketJS 在 H700 上**不负责出声**——出声靠 `xmplayer` 等外部程序。

**对 M21**：与 H700 相同策略即可（外部播放器），避免为 PocketJS 开 alsa feature。

---

## 3. BaseOS 侧需要提供的最小集合

| # | 需要的东西 | M21 现状 | 落地方式 |
|---|---|---|---|
| B1 | 内核 | stock 5.15.41 可用 | 不重编（首选） |
| B2 | `boot.img` 里的 kernel | 49.6 MB `Image` | 直接用 |
| B3 | `vendor_boot` 的 DTB | 3 个 DTB 拼接，entry 40/12 候选 | 不动（保留 stock） |
| B4 | `msm_drm.ko` + 8 个依赖 | 在 `vendor_dlkm` | 按 `modules.load` 顺序 insmod |
| B5 | `goodix_gt9xx_ts.ko` + `ts_core.ko` | 在 `vendor_dlkm` + `vendor_boot` ramdisk | 同上 |
| B6 | `fiio_primary_modules.ko` 等 | 在 `vendor_dlkm` | 先加载（是其他 fiio 模块的依赖） |
| B7 | `/dev` 节点 | **内核无 devtmpfs** | busybox `mdev -s`（见 power.md §7） |
| B8 | initramfs（first stage） | 我们自己写 | `init_boot` 分区塞 busybox + init 脚本 |
| B9 | rootfs | 我们自己写 | microSD ext4，PJOS 的 overlay 可复用（需去 H700 化） |
| B10 | `/vendor/firmware` | 在 `vendor` 分区 | 挂载 `vendor` 分区（只读）即可，无需复制 |
| B11 | 声卡 + kcontrol | 需 30+ 模块 + ADSP 固件 | **第一阶段可跳过**（外部播放器自己管） |
| B12 | 电源/亮度 sysfs | 标准 | 直接读 |

---

## 4. 关键设计决策

### 4.1 rootfs 与 firmware 的来源

M21 的 `/vendor`、`/vendor_dlkm` 是**逻辑分区（在 super 内）**。BaseOS 若要加载 vendor 模块，必须：

- **方案 A**：从 Android 的 `super` 里读出 `vendor_dlkm`（`fastboot`/`adb` 可读），复制到 microSD 上，用 `insmod /mnt/sd/vendor_dlkm/lib/modules/xxx.ko`。
- **方案 B**：用 device-mapper 在 boot 时挂载 Android 的 `super` 内的 `vendor_dlkm` 逻辑分区（需要 `dm-linear` + 手动构造 table，复杂）。
- **方案 C**：把 `vendor_dlkm.img`（757 MB）直接做成 microSD 上的一个镜像文件，loop mount。

**推荐 A**（最简单、最可控）：一次性把需要的 `.ko`（约 60 个，< 100 MB）与 `/vendor/firmware`（`adsp.b*` + `gw_fpga_firmware_m21.fw`）复制到 microSD 的 `/lib/firmware`、`/lib/modules/5.15.41-g9ded8564ff52-dirty/`，之后完全脱离 Android 分区。

> ⚠ 法律/许可提醒：vendor 模块是 FiiO/Qualcomm 的二进制，随设备分发在自有设备上是常规做法（等同 Android 的 vendor 分区），但**不要**把镜像公开发布。这一点与 PJOS 的 H700 现状一致（`manifest/harvest.list` 从厂商固件 harvest）。

### 4.2 加载顺序

`vendor_dlkm` 的 `modules.load`（259 行，`evidence/vendor-dlkm-modules.load`）就是答案。**照抄，不要自己排**。它有 `modules.softdep` 配合。

BaseOS 的 init 里：

```sh
MODDIR=/lib/modules/5.15.41-g9ded8564ff52-dirty
while read -r m; do
    [ -f "$MODDIR/$m" ] && insmod "$MODDIR/$m" 2>/dev/null
done < /etc/m21-modules.load
```

（必须忽略失败——259 个模块里有大量与本机无关的，例如 `camera.ko`。）

### 4.3 显示启动顺序

```
1. mount devtmpfs 替代物（mdev -s）
2. insmod pinctrl/regulator/clock 基础 → msm_drm.ko 的依赖链
3. insmod panel_event_notifier → msm_drm
4. 检查 /dev/dri/card0 出现
5. 检查 /sys/class/drm/card0-DSI-1/status == connected
6. 启动 pocket-linux-kms --card /dev/dri/card0
```

`msm_drm.ko` 的依赖（`modinfo`）：

```
qcom_iommu_util, msm_dma_iommu_mapping, fiio_primary_modules,
spmi-pmic-arb, pinctrl-msm, qcom_va_minidump, panel_event_notifier, qcom-scm
```

→ `fiio_primary_modules.ko` 是 `msm_drm.ko` 的**前置依赖**（FiiO 改了 DRM 驱动），必须提前加载。这是"FiiO 深度定制"的直接证据。

---

## 5. 与 PJOS-LINUX 的差距清单（12 项）

| # | PJOS 现状 | M21 需要 | 性质 | 工作量 |
|---|---|---|---|---|
| G1 | **依赖 `/dev/fb0`**（`docs/13` 实测只有 fb0，无 `/dev/dri`） | **必须走 DRM** | **现有假设失效** | 中（换后端 + 新 profile） |
| G2 | **依赖 devtmpfs**（`docs/01-rootfs-and-init.md:130-131`："There is no udev or mdev; devtmpfs provides device nodes"） | M21 **内核无 `CONFIG_DEVTMPFS`** | **现有假设失效** | 小（加 mdev） |
| G3 | `overlay/etc/init.d/rcS` 含 **sunxi 专有**逻辑（`h700_late_usb.ko`、`h700-speaker-amp-load`、`axp2202`） | 全部替换为 M21 的 | **现有代码不可用** | 中（BSP 分层，PJOS `docs/15` 已有设计） |
| G4 | `src/` 下 6 个 C 程序全是 H700/Allwinner（`axp-off`、`fcbsplash`、`baseos-regs` 读 DE/TCON 寄存器、`native-health`） | 全部不适用 | **现有代码不可用** | 中 |
| G5 | `manifest/harvest.list` 是 H700 的 ldd 闭包 | 需新开一份（M21 用 glibc 不同的 bionic 库） | 配置 | 中 |
| G6 | `devices.json` 只有 10 个字段（logo/旋转/wifi/bt） | 需 panel/input/audio/power/storage | 配置 | 小（`docs/15` 已设计 v2） |
| G7 | 音频：`hw:audiocodec` + 6 个 amixer 控件 | `bengal-idp-snd-card` + 30 模块 + `cs43198` kcontrol | 全新 | **大** |
| G8 | 触摸：**完全没有**（H700 `# CONFIG_INPUT_TOUCHSCREEN is not set`） | goodix MT-B + 375×667@2x profile | 新增（PocketJS 已支持） | 小 |
| G9 | 按键映射：H700 的 `apply-pocketjs-input.py` 打的是 `BTN_SOUTH/EAST/...` | M21 是 `KEY_MEDIA` 系列 | 新映射表 | 小 |
| G10 | 引导：boot0+U-Boot+extlinux，SD 即系统盘 | ABL+fastboot+init_boot | 全新 | 中 |
| G11 | 电源：`axp2202-battery` | `/sys/class/power_supply/battery/` | 节点改名 | 小 |
| G12 | `keyboardd` 未接线、无 evdev 桥 | M21 有触屏，非必需 | 可推迟 | — |

**3 项"现有假设失效"**：G1（fbdev）、G2（devtmpfs）、G3+G4（sunxi 代码）。这三项**不是"改配置"，是"换实现"**。

**好消息**：G1/G2 的替代方案都很轻（DRM 后端已存在；mdev 一行命令）。G3/G4 的工作量由 PJOS 自己的 BSP 分层设计（`docs/15-bsp-architecture.md`）承载——**M21 正是那个"第二台设备"的试金石**。

---

## 6. 现有 PocketJS 侧需要改的东西（很少）

| # | 位置 | 改动 | 依据 |
|---|---|---|---|
| 1 | 新增 profile | `id: "m21-drm"`, `physicalViewport: [750,1334]`, `logicalViewports: [[375,667]]`, `rasterDensity: 2`, `capabilities: ["input.buttons","input.touch","text.glyphs.baked"]` | 已用真实校验器验证通过 |
| 2 | 兼容层 shim | `rocknix-services` / `heya-control` / `systemctl` 等（PJOS `docs/13` G3） | 与设备无关 |
| 3 | Library 扫描器 | Python → busybox sh/awk（PJOS `docs/13` G4） | 与设备无关 |
| 4 | 可选：按键语义扩展 | `KEY_PLAYPAUSE` → 建议新增 `media.*` 按钮位 | 见 input.md |

**不需要改**：evdev 解码器、DRM 后端、fbdev 后端、runtime 核心。

---

## 7. 音乐播放器的最小实现路径

PocketJS profile 不声明 `audio.pcm` 时，音乐播放靠**外部进程**。H700 上这是 `xmplayer`；M21 上可选：

| 方案 | 组成 | 依赖 | 评价 |
|---|---|---|---|
| **A. mpv + IPC** | mpv（ALSA 输出）+ PocketJS 前端发 JSON IPC | 需 mpv（约 30 MB 静态编） | **推荐**：`pocket-music` 仓库已有 mpv IPC 后端（`musicd/mpv.go`） |
| B. 自带 tinyalsa 播放器 | 50 行 C + `libtinyalsa.so` | 需自己写 | 轻但功能少 |
| C. PocketJS alsa feature | `--features alsa` + `audio.pcm` | feature 需实测 | 未知 |
| D. ffmpeg + aplay | shell 管道 | 简单但耗 CPU | 原型可用 |

**推荐 A**：`pocket-music` 的 `musicd` 已经是 Go + mpv + SQLite，接口完整（20+ REST 端点），只需把 mpv 的 `--ao` 指向正确 ALSA 设备。

`pocket-music` 的 `mpv.go:102`：

```go
cmd := exec.Command(env("MUSICD_MPV", "mpv"), "--no-terminal", "--idle=yes",
    "--ao="+m.output, "--input-ipc-server="+m.socket)
```

→ `MUSICD_MPV` 和 AO 都是环境变量，**换设备只需改配置**。

---

## 8. 分阶段落地（每阶段可独立验收）

| 阶段 | 目标 | 依赖 | 验收（可观测） |
|---|---|---|---|
| **S0** | 只读侦察 | 实机 + adb | `getprop`/`ls /sys` 抓完本文所有"待验证"项 |
| **S1** | Linux shell 起来 | init_boot 替换 | 串口或 USB gadget 上出现 busybox shell |
| **S2** | 显示 | `msm_drm.ko` 加载成功 | `/dev/dri/card0` 存在 + `modetest` 能出画面 |
| **S3** | 输入 | goodix + gpio_keys | `evtest` 能看到按键与触摸 |
| **S4** | PocketJS 出画面 | S2+S3 + 新 profile | 卡片启动器显示在 750×1334 屏上 |
| **S5** | 音频（PCM） | techpack 模块 + ADSP + mixer | `aplay` 出声 |
| **S6** | Music Player | S5 + mpv/musicd | 点歌能播、音量可调 |
| **S7** | 电源/息屏 | `fiio_wakeup` + suspend | 息屏继续放歌，按键唤醒 |

**S2 是整个项目的第一个真实里程碑**——它同时验证了"启动链、DRM 模块链、DTB panel 选择"三件事。

---

## 9. 待实机验证

| # | 命令 | 期望 | 用途 |
|---|---|---|---|
| J1 | 用 `SPEC.md` 的 profile 跑 `bun tools/pocket.ts check --target m21-drm` | 通过 | 确认 profile 合法 |
| J2 | `ls /dev/dri/` + `cat /sys/class/drm/*/status` | `card0`, `connected` | 确认 DRM |
| J3 | `modetest -M msm_drm -c` | 列出 connector/mode | 确认 KMS |
| J4 | `ls /lib/modules/$(uname -r)/` | vendor 模块 | 确认模块路径 |
| J5 | `cat /proc/modules \| wc -l` | 200+ | 确认模块加载数 |
