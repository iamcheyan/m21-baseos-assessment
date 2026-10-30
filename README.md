# FiiO M21 + BaseOS/PocketJS 设备评估

调查日期：2026-10-30

## 结论摘要

**当前判断：暂不建议将 FiiO M21 直接定为 BaseOS 首个触屏设备。** 它已有可分析的官方 Android 13 OTA：FW1.0.8 包内解析出 19 个分区、A/B OTA metadata 和 AVB 签名描述符，并成功提取 boot、init_boot、vendor_boot、dtbo、vbmeta 等镜像。官方也记录 Fastboot Mode，社区有设备处于 unlocked 状态的个案。但仍没有证据证明该设备支持主机端 `fastboot boot baseos.img`。

Linux 侧没有发现 M21 专用 Linux DTS、可直接用的板级驱动集合或 mobile Linux 移植。SM6225 有实验性近主线内核工作，但不能替代 M21 板级支持。屏幕、触摸、四颗 CS43198 DAC 与模拟放大链、无线、电源与充电仍需逐项验证。

## 评分与建议

| 项目 | 评估 |
|---|---|
| Device Compatibility Score | **35/100（低置信度）**。固件可离线分析是利好，但 custom boot 和驱动仍未实测。 |
| Bootloader Risk | **高**。官方说明存在 fastboot 菜单，有解锁个案；解锁流程和 `fastboot boot` 未证实。 |
| BSP Risk | **很高**。未找到 M21 可用的 Linux DTS/驱动集合；音频部分尤其关键。 |
| Linux Porting Difficulty | **很高**。需先解决引导、内核/DTS 和板级驱动，再做 userspace。 |
| PocketJS Deployment Difficulty | **中高**。PJOS 已证明 PocketJS 能在另一台 ARM64 Linux 设备上启动；M21 显示/输入/图形 API 与 ABI 尚无验证。 |
| 推荐作为 BaseOS 首个 Touch Device | **暂不推荐**。先以实机完成只读 fastboot 检查；若不能证明临时启动，再停止 M21 主线。 |

这不是对设备最终不可行的判断；它反映公开证据不足且先决条件尚未实测。

## 1. 设备事实

FiiO 官方规格列出 Snapdragon 680、Android 13、4 GB RAM、64 GB 存储、750×1334 显示屏；官方产品规格列出四颗 CS43198 DAC。[1][2]

FiiO 官方升级说明要求把固件 ZIP 放在内部存储或 SD 卡，通过 Technical Support → Firmware Upgrade → Local Upgrade 安装，且不要解压升级包。官方恢复说明记载音量减键加 USB 可进 recovery；电源键加音量加、音量减可进 fastboot 菜单，再用实体按键选择 Activate rescue mode。[3] 这证明存在厂商 fastboot/rescue UI，不证明主机端 fastboot 下载/启动/刷写能力。

## 2. Bootloader、解锁与临时启动

- **Fastboot Mode：有官方操作说明。** 是菜单级证据，本次未连接 M21 实测主机协议。[3]
- **OEM Unlock / 解锁流程：未知。** 没找到 FiiO 针对 M21 的 OEM unlocking、`fastboot flashing unlock` 或解锁擦除行为说明。
- **用户成功解锁：有个案报告。** Reddit 用户报告 M21 bootloader 为 `DEVICE STATE = unlocked`、`SECURE BOOT = no`；Head-Fi 附件也出现类似信息。这些报告没有可复现解锁步骤，不能代表所有设备或固件版本。[4][5]
- **`fastboot boot xxxx.img`：未找到成功案例或厂商支持说明。** Root/Magisk 的刷写个案不能证明可临时启动 Linux 镜像。[4]

Android 通用文档描述 OEM unlocking 与 `fastboot flashing unlock` 的通用机制；它不能证明 M21 实现了该功能。[6]

## 3. 官方固件与实际解析结果

官方论坛提供 FW1.0.8 全量 OTA ZIP。[7] 已将完整包下载至 HX90 数据盘，大小 **1,657,748,858 bytes**，SHA-256：`1d3ed710702e4514ac39a75b3f01834daccd64073339f095ab9dd72ffc97cd6b`。`payload_properties.txt` 的 `FILE_HASH` 解码后与 payload.bin 的 SHA-256 相符，大小也一致。OTA 是 Android SignApk 签名容器；`unzip -t` 对签名尾记录返回非零，但 zipinfo 列出 7 个成员、payload 可读且 manifest 可解析。因此保留原包及哈希，不以该工具退出码推断损坏。

OTA metadata 显示：`MODEL_NAME=FiiO M21`、`pre-device=bengal_515`、`ota-type=AB`、SDK 33（Android 13）、安全补丁级别 2023-02-05。

`payload-dumper-go` 解析到 19 个分区：`abl`, `boot`, `dtbo`, `init_boot`, `modem`, `odm`, `product`, `recovery`, `rpm`, `system`, `system_dlkm`, `system_ext`, `vbmeta`, `vbmeta_system`, `vendor`, `vendor_boot`, `vendor_dlkm`, `xbl`, `xbl_config`。

已提取 `abl.img`, `boot.img`, `dtbo.img`, `init_boot.img`, `recovery.img`, `vbmeta.img`, `vbmeta_system.img`, `vendor_boot.img`，保存在数据盘且纳入 SHA256SUMS。

### AVB / Verified Boot

`avbtool info_image` 的结果：

- `vbmeta.img`：minimum libavb **1.0**；算法 **SHA256_RSA4096**；release `avbtool 1.2.0`；有指向 `vbmeta_system` 的 chain descriptor，以及 boot/dtbo/init_boot/recovery/vendor_boot 的 hash descriptor、odm/system_dlkm/vendor/vendor_dlkm 的 hashtree descriptor。
- `vbmeta_system.img`：minimum libavb **1.0**；算法 **SHA256_RSA2048**；rollback index 1675555200；有 product/system/system_ext 的 hashtree descriptor。
- 这证明 OTA 包有 AVB 元数据和分区验证描述符；不能单独证明设备当前锁定状态、启动 enforcement、运行时 AVB 版本或能否启动自定义镜像。
- `ota-type=AB` 证明更新 metadata 标为 AB OTA；不能据此列出物理槽位分区。payload 名称无 `_a`/`_b` 后缀。
- payload 清单没有 `super`；只能确认 OTA payload 未列 `super` 分区，不能单凭此断言设备绝无 dynamic partitions。

A/B metadata 与分区名不足以完全重建实际槽位映射。完整 boot chain 仍需设备实测确认。

## 4. 启动链

直接证据是 OTA 的 `bengal_515` Android 13 metadata、19 个 payload 分区、AVB 1.0 metadata，以及厂商 recovery/fastboot 菜单操作。完整 `BootROM → Qualcomm XBL/ABL 等阶段 → boot image → Android` 序列、各阶段实现、签名 enforcement 和启动参数没有设备实测/串口证据支持，不能将常见 Qualcomm 启动链当作 M21 已验证事实。

## 5. BSP 与硬件驱动

| 硬件 | 当前证据与缺口 |
|---|---|
| Display / Touch | 无 M21 Linux DTS、面板型号、触摸控制器或 Linux 驱动验证。 |
| DAC / Audio Codec | FiiO 规格为四颗 CS43198 和模拟放大器；未找到该 M21 音频拓扑的 Linux ASoC machine driver、路由和固件证据。[2] |
| Battery / Charging | 无电量计、充电芯片、USB-C 供电旁路及 suspend/wakeup 的 Linux 验证。 |
| Wi‑Fi / Bluetooth | 未找到 M21 无线芯片型号、固件文件或 Linux 接入验证。Android 可用不代表 Linux 可用。 |
| USB / Storage | OTA 提供 Android 分区更新；Linux gadget/host、存储控制器、槽位和设备树映射仍未验证。 |

已下载 FiiO 公开 kernel source 仓库说明作为线索；仓库年代较早，**未验证为 M21 的 5.15.41 kernel source**，不把它当成可用 M21 BSP。[8] SM6225 实验性 v6.1 内核树有助 SoC 层调查；Moto G32 等同 SoC Android BSP 仅供参考，板级硬件不同不可直接复用。[9][10]

未发现 M21 的 postmarketOS、Ubuntu Touch、Droidian 或 Mobian 移植记录。Mobian 指出 mainline kernel 支持也不保证周边驱动足够形成可用移植。[11][12]

## 6. 官方 Kernel + 自定义 RootFS 可行性

**原则上可行，M21 上尚未证明。** 若 bootloader 接受并启动官方内核，且能提供兼容 initramfs、设备树、内核命令行和所需固件，Linux userspace 可由 BusyBox/systemd rootfs 提供。实际障碍是尚未证明可从主机端临时启动自定义镜像，也没有 M21 Linux DTS/驱动和完整槽位/启动参数资料。

保留 Android kernel 不自动等于任意 rootfs 可用：内核配置、initramfs、vendor 模块 ABI、Android binder/HAL 依赖和 SELinux/AVB 都可能限制替换路径。即使 shell 启动成功，没有触摸、Wi‑Fi、音频和电源管理仍不能达到目标。

## 7. `baseos.img` 最小启动路线

在验证 `fastboot boot` 前不写设备分区。若且仅若主机 fastboot 能识别设备且 bootloader 接受临时启动：留存并校验 boot 组件、DTB/DTBO 与 vbmeta；研究 boot image header、init_boot/vendor_boot ramdisk、参数和设备树；再以官方 kernel + 只提供串口/ADB shell 的最小 initramfs 做非持久启动。成功后逐步验证只读挂载、显示、触摸和网络，再处理音频。未确认恢复条件时不解锁、不 flash、不 erase。

目前不能给出保证可启动的 baseos.img 配方；组件已提取，但 fastboot 能力和设备树/boot 参数仍未知。

## 8. MVP 阶段

| 阶段 | 目标 | 依赖 | 风险 | 验证方式 |
|---|---|---|---|---|
| Stage 0：只读门槛 | 记录版本；只读 fastboot enumeration/getvar；整理 OTA | M21 实机、USB、platform-tools | 主机 fastboot 不可用；版本差异 | 保存 getvar、固件哈希和 payload 清单，不写设备 |
| Stage 1：启动探针 | 官方内核加自定义 initramfs 临时启动到 shell | Stage 0 证实 `fastboot boot` | 命令拒绝或启动失败，恢复困难 | 确认救援路径后进行非持久启动，记录 ADB/串口 |
| Stage 2：板级基础 | 显示、触摸、USB、存储、Wi‑Fi、BT、电量、休眠 | DTS、内核驱动、固件 | Android-only 驱动/私有固件缺失 | 实机逐项验证节点、触摸、网络、睡眠唤醒 |
| Stage 3：音频 | ALSA/ASoC 到 CS43198 与耳机输出 | codec + machine driver、DSP/固件、路由 | 多 DAC 与放大链复杂 | 低音量测试、声道/采样率/音量、唤醒测试 |
| Stage 4：PocketJS Desktop | PocketJS 触屏 UI、媒体扫描、Music Player MVP | 前阶段可用、KMS/fbdev 与 Rust ABI 适配 | GPU/KMS、ABI、功耗和性能 | 冷启动、触摸、播放/暂停/音量、长播与唤醒实测 |

Stage 1 是 go/no-go。若 `fastboot boot` 不可用，而目标继续禁止直接 flash，就应停止 M21 主线，选已有 BaseOS 支持且可恢复的 Linux 设备。

## 9. 下一步最值得验证的三件事

1. **实机只读 fastboot 检查**：确认主机枚举与 getvar；不运行 unlock/flash/erase。
2. **理解 AB/动态分区**：继续解析 metadata.pb、fstab、boot/vendor_boot ramdisk、super 线索和实际 slot 信息。
3. **采集板级资料**：原厂系统只读收集 `/proc/config.gz`、`/sys/firmware/devicetree/base`、`/proc/cmdline`、input、ALSA、无线固件及充电节点，确认显示、触摸、无线、电源及 DAC 接法。

## 10. 与本地 BaseOS 项目的关系

PJOS-LINUX 已保存 PocketJS 在 Anbernic RG34XX（H700）BaseOS 上启动、自启动的实机证据；这证明特定 Linux 硬件上的前端路线，不证明 M21 兼容。资料仍记载 Library 扫描和媒体播放器未完成。[13] 可复用运行时/界面经验，但需单独开展 Qualcomm 板级 bring-up。

## Sources

[1] FiiO M21 product: https://www.fiio.com/m21
[2] FiiO M21 specifications: https://www.fiio.com/m21_parameters
[3] FiiO M21 update/recovery: https://www.fiio.com/newsinfo/1045496.html
[4] Reddit M21 root attempt: https://www.reddit.com/r/Magisk/comments/1lr33vn/help_rooting_digital_audio_player_fiio_m21/
[5] Head-Fi M21 thread/attachment: https://www.head-fi.org/threads/fiio-m21-qualcomm-snapdragon-680-fiio-android-portable-music-player-is-available/page-109 ; https://cdn.head-fi.org/a/12820990.txt
[6] Android bootloader unlock docs: https://source.android.com/docs/core/architecture/bootloader/locking_unlocking
[7] FiiO firmware listing and FW1.0.8 OTA: https://forum.fiio.com/note/showNoteContent.do?id=202505140958060216556&tid=17 ; http://m21pack.fiio.net/beta/M21-update-1.0.8.zip
[8] FiiO kernel source (M21 applicability unverified): https://github.com/FiiOapp/FiiO_Kernel_OpenSource
[9] SM6225 exploratory kernel: https://gitlab.com/TQMatvey/linux-sm6225/tree/v6.1-sm6225
[10] LineageOS Moto G32 metadata: https://github.com/LineageOS/lineage_wiki/blob/main/_data/devices/devon.yml
[11] Ubuntu Touch devices: https://devices.ubuntu-touch.io/installer/
[12] Mobian porting overview: https://blog.mobian.org/posts/2023/03/07/porting-to-new-devices
[13] PJOS-LINUX first-boot evidence: `project-context/PJOS-baseos-first-boot-evidence.md` in the HX90 archive.

## 本地资料

所有 OTA、提取镜像、来源、分析输出和 SHA256SUMS 在 HX90 数据盘 `/storage/research/m21-baseos-assessment/`。官方 OTA 和用户手册已保存；README 记录文件及校验信息。

## 证据边界

固件分区与 AVB 描述符来自实际下载的官方 FW1.0.8 OTA。没有 M21 实机，未做 fastboot、OEM unlock、custom boot、显示/触摸、无线、音频或电源测试；未向设备写入。FiiO 部分网页在 HX90 返回 HTTP 429，community 解锁信息是个案报告。
