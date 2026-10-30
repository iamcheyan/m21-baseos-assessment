# FiiO M21 + BaseOS/PocketJS 设备评估

调查日期：2026-10-30

## 结论摘要

**当前判断：不建议将 FiiO M21 选为 BaseOS 首个触屏设备，除非先用手头实机证明可从主机侧启动自定义镜像。** M21 有一个重要利好：厂商文档确认存在 Fastboot Mode，社区亦有 M21 设备显示 `unlocked` 的报告。但没有查到任何可复现的 M21 `fastboot boot baseos.img` 成功记录。Fastboot 菜单中有“Activate rescue mode”不等于支持标准主机端 fastboot 启动命令。

M21 官方全量固件包约 1.66 GB，可从厂商链接下载；然而本次只确认 HTTP Range 可读，未下载完整包，也未成功读取 ZIP 中央目录。因此 payload、分区镜像、动态分区、A/B、AVB 版本等均**未确认**。报告不把 Android 13 或同 SoC 设备推断当成 M21 实测事实。

Linux 侧也没有发现 M21 专用的设备树、内核源码发布、移动 Linux 移植或可用 BSP。Snapdragon 680（SM6225）有实验性近主线内核工作，但不能代替该播放器的板级支持。屏幕、触摸、四颗 CS43198 DAC 与模拟放大链、无线、充电和电源管理均需逐项验证。

## 评分与建议

| 项目 | 评估 |
|---|---|
| Device Compatibility Score | **30/100（低置信度）**。硬件规格适合做紧凑播放器，但关键启动和设备树事实未知。 |
| Bootloader Risk | **高**。存在 fastboot 模式和解锁个案；解锁流程、当前量产状态、`fastboot boot` 均未证实。 |
| BSP Risk | **很高**。未找到 M21 可用的 Linux DTS/驱动集合；音频部分尤其关键。 |
| Linux Porting Difficulty | **很高**。需要先解决引导、内核/DTS 和板级驱动，再做 userspace。 |
| PocketJS Deployment Difficulty | **中高**。PJOS 已证明 PocketJS 能在另一台 ARM64 Linux 设备上启动；M21 的显示/输入/图形 API 与 ABI 尚无验证。 |
| 推荐作为 BaseOS 首个 Touch Device | **暂不推荐**。先把它作为探索候选，完成 Stage 0 的只读 bootloader 与固件检查后再决定。 |

这不是对设备最终不可行的判断；它反映公开证据不足且先决条件尚未实测。

## 1. 设备事实

FiiO 官方规格列出 Snapdragon 680、Android 13、4 GB RAM、64 GB 存储、750×1334 显示屏；官方产品规格列出四颗 CS43198 DAC。规格页能确认产品配置，不能证明 Linux 驱动或启动方式。[1][2]

FiiO 官方更新说明提供在线与本地升级，要求将固件 ZIP 放在内部存储或 SD 卡、通过 Technical Support → Firmware Upgrade → Local Upgrade 安装，并提示不要解压升级包。[3] 官方故障恢复说明记载：音量减键加 USB 可进入 recovery；电源键加音量加、音量减可进入 fastboot 菜单，然后可用实体键选择 Activate rescue mode。[3] 这只能证明厂商用户流程中存在 fastboot 菜单，未证明主机端 `fastboot devices`、`fastboot boot` 或可写分区命令可用。

## 2. Bootloader、解锁与临时启动

- **Fastboot Mode：有官方操作说明。** 这是菜单级证据，不是主机协议能力的完整验证。[3]
- **OEM Unlock / 解锁流程：未知。** 没有找到 FiiO 针对 M21 的 OEM unlocking、`fastboot flashing unlock` 或解锁擦除行为说明。
- **用户成功解锁：有个案报告。** Reddit 用户报告 M21 bootloader 状态为 `DEVICE STATE = unlocked`、`SECURE BOOT = no`；Head-Fi 附件也出现类似设备信息。这些报告没有给出可复现解锁步骤，不足以证明所有批次或出厂状态一致。[4][5]
- **`fastboot boot xxxx.img`：未找到 M21 成功案例或厂商支持说明。** 也未找到可验证的 `fastboot flash` M21 案例。root/Magisk 个案中的刷写叙述不能证明完整替换系统或临时启动自定义 Linux 镜像。[4]

Android 通用文档说明解锁能力由设备实现，通常需启用 OEM unlocking 并执行 `fastboot flashing unlock`；这是平台通用机制，不证明 M21 实现了它。[6]

## 3. 官方固件结构与分区分析

FiiO 官方论坛固件页面列出增量 ZIP 和完整 ZIP，例如 FW1.0.8 全量包 `M21-update-1.0.8.zip`。[7] 对其下载地址执行 HTTP Range 探测返回 206，文件总长度为 **1,657,748,858 字节**。这只证明链接可响应及文件大小，不是文件完整性验证。

**未完成固件内部分析：**本次未把 1.66 GB 文件完整下载，也未能从末尾 Range 数据解析出有效 ZIP64 中央目录。因此目前不能声称包内有或没有 `payload.bin`、`boot.img`、`vendor_boot.img`、`vbmeta.img`、`dtbo.img`、`super.img`，亦不能列出包内分区。官方页面说“不要解压”是面向升级用户的操作指引，不等价于包一定加密或不能分析。

建议后续在下载完成并校验包结构后，检查 ZIP/ZIP64 中央目录、`payload.bin` manifest、`META-INF`、升级脚本以及可提取镜像；记录 URL、时间、字节数和 SHA-256。不要向设备写入任何内容。

| 项目 | 状态 |
|---|---|
| payload.bin | 未确认 |
| boot.img / vendor_boot.img | 未确认 |
| vbmeta.img / dtbo.img | 未确认 |
| super.img / Dynamic Partitions | 未确认 |
| A/B slots | 未确认 |
| AVB 版本与 Verified Boot 当前状态 | 未确认；仅有社区报告的 secure boot 状态 |
| 完整分区清单 | 未确认 |

## 4. 启动链

目前可证据化的只有 Android 产品信息，以及厂商提供的 recovery / fastboot 菜单进入方式。完整的 `BootROM → Qualcomm XBL/ABL 等阶段 → boot image → Android` 链条、具体 bootloader 类型、签名校验与 AVB 细节没有 M21 固件/串口/分区证据支持。因此不把常见 Qualcomm Android 启动链写成已确认的 M21 启动链。

“SM_EMMC”一类 bootloader 字段（若设备个案中出现）也不能单独证明有无 A/B、super 或 AVB。

## 5. BSP 与硬件驱动

| 硬件 | 当前证据与缺口 |
|---|---|
| Display / Touch | 无 M21 DTS、面板型号、触摸控制器或 Linux 驱动验证。750×1334 规格不构成驱动证据。 |
| DAC / Audio Codec | FiiO 规格为四颗 CS43198 与放大器组合；未找到此 M21 音频拓扑的 Linux ASoC machine driver、路由和固件证据。[2] |
| Battery / Charging | 无电量计、充电芯片、USB-C 供电旁路及 suspend/wakeup 的 Linux 验证。 |
| Wi‑Fi / Bluetooth | 未找到 M21 无线芯片型号、固件文件或 Linux 接入验证。Android 可用不代表 Linux 可用。 |
| USB / Storage | Android 更新和数据传输可用；Linux gadget/host、存储控制器与分区映射未验证。 |

postmarketOS 有 SM6225 实验性近主线内核包/开发树；这提供 SoC 调查入口，不是 M21 设备支持。Moto G32 等其他 SM6225 设备的 Android BSP 也只适合作为芯片族参考，不能复用为 M21 板级驱动。[8][9]

未发现 M21 的 postmarketOS、Ubuntu Touch、Droidian 或 Mobian 设备移植记录。Mobian 的说明也强调，能启动 mainline kernel 不代表设备周边驱动足以形成可用移植。[10][11]

## 6. 官方 Kernel + 自定义 RootFS 可行性

**理论上可以，但目前没有可执行依据。** 若 Bootloader 接受并启动官方内核，且能提供兼容 initramfs、设备树、内核命令行及所需固件，Linux userspace 可以替换 Android userspace；BusyBox/systemd 本身不是主要障碍。实际障碍是尚未证明能够让内核启动到自定义 initramfs，也没有 M21 的设备树/驱动和分区/启动参数资料。

保留官方 Android kernel 也不自动等于可运行任意 rootfs：Android 内核配置、SELinux/AVB、initramfs、vendor 模块 ABI、Android binder/HAL 依赖和设备树都可能限制替换路径。即使 shell 能启动，没有触摸、Wi‑Fi、音频输出和电源管理，仍不能满足 PocketJS Desktop + Music Player 的目标。

## 7. `baseos.img` 最小安全启动方案

在验证 `fastboot boot` 前，不应向 M21 写分区。若且仅若主机端 fastboot 能识别设备，且该 bootloader 接受临时启动，可构建一份不带分区写入逻辑的实验镜像：

1. 从官方固件提取匹配版本的 boot 相关组件与 DTB/DTBO（若实际存在），保存哈希和原始副本。
2. 先研究 Android boot image header、启动参数和 initramfs；不要臆造分区名或 AVB 开关。
3. 以官方 kernel + 只输出串口/ADB shell 的最小 initramfs 试验；只有设备接受非破坏性 `fastboot boot` 才进行。
4. 初次成功后只验证只读挂载、CPU/内存、触摸输入、屏幕与网络；音频单独做低风险测试。
5. 每一步都保留官方恢复包和厂商 rescue 流程。没有真实设备与恢复条件，不尝试 flash、解锁或擦除。

目前无法给出能保证工作的 `baseos.img` 配方，因为关键镜像格式、DTB、命令行与 fastboot 能力都未确认。

## 8. MVP 阶段

| 阶段 | 目标 | 依赖 | 主要风险 | 验证方式 |
|---|---|---|---|---|
| Stage 0：只读可行性门槛 | 记录版本/序列号本地保存、fastboot enumeration/getvar、官方固件完整下载与分析 | M21 实机、USB、主机 platform-tools、固件下载空间 | 设备无主机 fastboot；固件包特殊格式 | `fastboot devices` 与只读 `getvar` 输出；ZIP/ZIP64 清单与哈希；不写设备 |
| Stage 1：内核/启动探针 | 证明官方内核能以自定义 initramfs 临时启动到 shell | Stage 0 证明临时启动；boot image/DTB 可提取 | 命令被拒、启动失败或恢复困难 | 仅在确认 fastboot boot 与救援方案后，启动不改分区的探针；记录串口/ADB/shell |
| Stage 2：板级基础 | 识别屏幕、触摸、USB、存储、Wi‑Fi、BT、电量与 suspend | DTS、内核驱动、固件 | Android-only 驱动/私有固件或节点缺失 | 逐项 sysfs/input/logcat 对照，LCD 点亮并读取触摸，网络与睡眠实测 |
| Stage 3：音频链 | 播放器以 ALSA/ASoC 路径输出到 CS43198 与耳机口 | codec driver、machine driver、DSP/firmware、路由 | 多 DAC 与模拟放大路径复杂，pop/no sound/音量异常 | 低音量测试音、左右声道/采样率/音量/休眠唤醒测试 |
| Stage 4：PocketJS Desktop | 启动 PocketJS、触摸 UI、媒体扫描和 Music Player MVP | 前述基础可用，KMS/fbdev 与 Rust ABI 适配 | GPU/KMS 或 ABI 不匹配、内存/功耗问题 | 在真实 M21 冷启动、触摸、列表播放、暂停/音量、长时间播放和睡眠唤醒验收 |

Stage 1 是 go/no-go。若 `fastboot boot` 不可用，而用户目标又坚持禁止直接 flash，则应停止 M21 主线，转用已有 BaseOS 支持、可恢复的 Linux 设备。

## 9. 下一步最值得验证的三件事

1. **实测 fastboot 能力与解锁状态**：只读取设备枚举和 `getvar`；区分厂商屏幕菜单与主机 fastboot 协议。不得先运行 unlock/flash/erase。
2. **完成官方包下载与离线结构解析**：计算 SHA-256，解析 ZIP64；若有 payload，提取 manifest/分区清单并检查 boot/vbmeta/dtbo/super。公开页面提供完整包链接，但本次未完成下载解析。[7]
3. **收集 M21 板级资料**：官方 kernel source、`/proc/config.gz`、`/sys/firmware/devicetree/base`、`/proc/cmdline`、`/dev` 与 ALSA 卡信息；在原厂 Android 下只读采集，明确显示/触摸/无线/电源和 DAC 型号。

## 10. 与本地 BaseOS 项目的关系

本机 PJOS-LINUX 已记录 PocketJS 在 Anbernic RG34XX（H700）BaseOS 上启动并自动运行的证据；它证明了 PocketJS Linux 前端路线在一台特定硬件上的可行性，不证明 M21 支持。其记录仍指出 Library 扫描和媒体播放器未完成。[12] 因此 M21 评估应复用现有 Linux UI/运行时经验，但单独建立硬件 bring-up，不把 H700 的显示、输入、ABI 或音频结论迁移到 Qualcomm 设备。

## Sources

[1] FiiO M21 product page: https://www.fiio.com/m21
[2] FiiO M21 specifications: https://www.fiio.com/m21_parameters
[3] FiiO M21 update/recovery instructions: https://www.fiio.com/newsinfo/1045496.html
[4] Reddit M21 root attempt and reported unlocked state: https://www.reddit.com/r/Magisk/comments/1lr33vn/help_rooting_digital_audio_player_fiio_m21/
[5] Head-Fi M21 thread and bootloader attachment: https://www.head-fi.org/threads/fiio-m21-qualcomm-snapdragon-680-fiio-android-portable-music-player-is-available/page-109 ; https://cdn.head-fi.org/a/12820990.txt
[6] Android bootloader locking/unlocking documentation: https://source.android.com/docs/core/architecture/bootloader/locking_unlocking
[7] FiiO official M21 firmware listing: https://forum.fiio.com/note/showNoteContent.do?id=202505140958060216556&tid=17 ; full package URL: http://m21pack.fiio.net/beta/M21-update-1.0.8.zip
[8] postmarketOS SM6225 kernel package: https://pkgs.postmarketos.org/package/master/postmarketos/aarch64/linux-postmarketos-qcom-sm6225
[9] Experimental SM6225 kernel development: https://gitlab.com/TQMatvey/linux-sm6225 ; LineageOS Moto G32 device metadata: https://github.com/LineageOS/lineage_wiki/blob/main/_data/devices/devon.yml
[10] Ubuntu Touch supported device list: https://devices.ubuntu-touch.io/installer/
[11] Mobian porting overview: https://blog.mobian.org/posts/2023/03/07/porting-to-new-devices
[12] Local PJOS-LINUX BaseOS first-boot evidence: `docs/evidence/2026-10-30-baseos-first-boot/README.md`

## Evidence limits

Public web research and a 256 KiB HTTP Range probe were completed. The firmware server reported HTTP 200 and Content-Length 1,657,748,858 for a streaming request; the full package was not downloaded. A 65,536-byte tail range was returned, but did not expose a usable ZIP end record/ZIP64 directory in that response. Device-level fastboot, OEM unlock, custom boot, kernel, display, touch, wireless and audio tests were not performed. No M21 hardware was available in this workspace.
