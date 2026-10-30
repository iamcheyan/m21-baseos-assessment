# FiiO M21 作为 BaseOS / PocketJS Touch Device：第二轮可行性评估

调查日期：2026-10-30。**无实机**。所有"需实机"项显式标注，验证步骤见各文档末节。
第一轮产物：仓库根 `README.md`（commit `d5f6ea7`）。本轮全部在 `docs/m21-round2/`。

---

## 结论档位：**有条件可行**

| 判定 | 内容 |
|---|---|
| **档位** | **有条件可行（Conditional GO）** |
| 一句话 | 启动链与显示/输入的把握足够开工；**唯一的大工作量在前置条件"音频用户态栈"**；而 PocketJS 的第一阶段**不需要**音频 |
| 开工前必须满足 | 4 条前置条件（见 §3） |
| 不满足时的退路 | 退回"只做 Music Player 前端 + 外部播放器"，或换设备（见 §7） |

---

## 1. 九个必答问题（每条的结论 + 置信度）

| # | 问题 | 结论 | 置信度 | 详见 |
|---|---|---|---|---|
| 1 | **启动链** | Android ABL fastboot；A/B + 动态分区；ABL 用 QCT **test key** 签名；`fastboot boot` 在同 vendor tree 的 JM21 上**已实测成功** | 中（M21 无直接实测） | `boot-chain.md` |
| 2 | **内核** | stock **5.15.41 GKI**，config 可得、**源码不可得**（厂商仓库停在 2017）；DTB 三层结构；所有硬件驱动在 `vendor_dlkm`（226 个 .ko） | 高 | `kernel.md` |
| 3 | **显示与触摸** | 750×1334@60Hz，**只有 DRM 没有 fbdev**；触摸 goodix GT9xx，**标准 evdev MT-B**；背光 PWM | 高（DT）/中（实机贴片） | `display-touch.md` |
| 4 | **音频** | 硬件与驱动全在（4×CS43198 + FPGA + Bolero techpack）；**用户态完全缺失**（无 libasound，Android 用 tinyalsa+HAL） | 高（结构）/低（BaseOS 可用性） | `audio.md` |
| 5 | **输入** | 6 个媒体键（VOL±/PREV/NEXT/PLAY/多功能）+ 耳机线控 3 键 + 触摸；**无旋钮**；全部标准 evdev | 高 | `input.md` |
| 6 | **电源** | `/sys/class/power_supply/battery/`（CW221X 电量计 + SGM41510 充电）；suspend 支持；PMIC RTC；**内核无 devtmpfs** | 高 | `power.md` |
| 7 | **存储与刷机风险** | microSD 引导可做到 **eMMC 零写入**；回滚材料可从 OTA 离线解出；**EDL 不可用**（无 firehose） | 高 | `storage-risk.md` |
| 8 | **PocketJS 落地** | runtime 已含 DRM/fbdev/evdev 三后端，**PocketJS 侧改动极小**；差距集中在 BaseOS（12 项，3 项是"现有假设失效"） | 高 | `pocketjs-gap.md` |
| 9 | **结论** | 有条件可行，前置条件见 §3 | — | 本文 |

---

## 2. 关键判断与依据（每条一句话 + 证据）

1. **启动链可拿**：ABL 用 `QCT Root CA 1 / General Use Test Key` 签名（`evidence/abl-embedded-certs.txt`），不是生产 release key；同 vendor tree 同 SoC 的 JM21 已 `fastboot boot` 自定义内核成功（[C1]）。→ 风险从"未知"降到"中"。
2. **不需要 mainline，也不需要重编内核**：stock kernel 完整可用，模块 ABI 自洽（5 个模块 vermagic 一致），`MODULE_SIG_FORCE` 未设（`kernel.md` §2.3）。
3. **显示必须走 DRM**：`# CONFIG_FB is not set`，`DRM_FBDEV_EMULATION` 不存在，`msm_drm.ko` 不引用 `drm_fbdev_generic_setup`。→ 这点与 H700 完全相反。
4. **触摸比 H700 好**：H700 根本没编触摸（`# CONFIG_INPUT_TOUCHSCREEN is not set`），M21 有 goodix MT-B。
5. **音频是唯一的大坑**：30+ 模块 + ADSP 固件 + FiiO 私有 kcontrol，且用户态要从零搭。
6. **PocketJS 不依赖音频**：H700 的 profile 只有 `["input.buttons","text.glyphs.baked"]`（[R1]），播放靠外部 mpv。
7. **变砖风险可控**：microSD 引导 + 只改 `init_boot_a` 一个分区；`xbl`/`abl`/`rpm` 绝不碰。
8. **EDL 指望不上**：OTA 内 `prog_firehose` / `rawprogram` / `firehose` 全部 0 命中。

---

## 3. 前置条件（开工前必须满足）

| # | 条件 | 为什么 | 验证方式 |
|---|---|---|---|
| **P1** | 实机只读侦察完成 | 所有结论建立在"固件+同平台类推"上，缺 M21 的直接数据 | 跑完 `boot-chain.md` V1–V4、`kernel.md` K1–K5、`display-touch.md` D5–D8、`audio.md` A1–A5、`power.md` P1–P3、`input.md` I1–I2 |
| **P2** | 确认触摸控制器是 **goodix** 而非 focaltech | focaltech 驱动在所有镜像里都不存在；若是 focaltech 屏则触摸不可用（除非自编驱动） | `adb shell dmesg \| grep -iE 'fts|goodix'` + `/proc/bus/input/devices` |
| **P3** | 完成 P0 备份 | `fiioconfig` / `persist` / `modem` 丢了不可恢复 | `storage-risk.md` §5 的 S5–S6 |
| **P4** | 确认 `/dev/dri/card0` 在 Android 下存在 | 证明 `msm_drm.ko` 的加载链与 KMS 可用 | `adb shell ls /sys/class/drm/`（非 root 通常可读） |

**P1–P2 是真正的 go/no-go**；P3 是安全前提；P4 是技术前提。

---

## 4. 与第一轮的差异 Top 3

| # | 第一轮 | 第二轮 | 证据 |
|---|---|---|---|
| **1** | 显示路径未区分 fbdev/DRM，隐含可以沿用 H700 的 fbdev | **M21 没有 `/dev/fb0`**：`CONFIG_FB` 未编入、无 `DRM_FBDEV_EMULATION`、`msm_drm.ko` 不引用 fbdev helper → **必须 DRM** | `kernel.md` §6 |
| **2** | 把 `cdn.head-fi.org/a/12820990.txt` 当 M21 的 `DEVICE STATE = unlocked` 证据 | 该 dump 的模块名是 `anolog_board_jm21`/`power_board_jm21` → **是 JM21**；M21 的同类证据目前没有 | `storage-risk.md` §7 |
| **3** | "没有证据证明支持 `fastboot boot`" → Stage 1 是 go/no-go，不可用就停 | **JM21 同平台已实测 `fastboot boot` 自定义内核成功**（含 vendor 模块加载、PCM/DSD 出声） → 风险降级，路线改为 init_boot 优先 | `boot-chain.md` §4 |

完整逐条对照见 `DIFF-vs-round1.md`。

---

## 5. 最大的三个技术风险

| # | 风险 | 影响 | 缓解 |
|---|---|---|---|
| **R1** | **音频用户态栈缺失**：无 `libasound.so.2`；Android 走 tinyalsa+HAL；30+ 模块 + ADSP + FiiO 私有 kcontrol | Music Player 无声 | 第一阶段跳过（外部 mpv）；第二阶段自建 alsa-lib 或 tinyalsa |
| **R2** | **EDL 不可写**：无 firehose 包 | 碰了引导链 = 真砖 | 严格红线（`storage-risk.md` §4）；只改 `init_boot`；完整备份 |
| **R3** | **触摸 IC 可能是 focaltech**，其驱动在所有镜像为 0 命中 | 触屏不可用 | P2 先验证；若真是 fts，可用主线 `CONFIG_TOUCHSCREEN_FTS` 自编模块（`MODULE_SIG_FORCE` 未设） |

次要风险：`fastboot boot` 可能忽略 ramdisk（R5）、M21 用哪条 DTBO overlay 未确认（R6）、DT 里的 `td4310` 悬空引用（R7）。

---

## 6. 推荐路径（最小风险 + 最快见效）

```
阶段 0  只读侦察（无写入）
        └ adb getprop / ls /sys / dmesg；fastboot getvar all
           产出：确定 overlay、触摸 IC、DRM 节点、声卡、电池节点

阶段 1  备份（无写入）
        └ fiioconfig / persist / modem → SD 卡
        └ OTA 解出 boot/init_boot/vendor_boot/dtbo/vbmeta → 回滚材料就位

阶段 2  显示先通（写 1 个分区）
        └ init_boot_a = busybox + init（mount SD rootfs → switch_root）
        └ rootfs 内按 modules.load 加载 vendor_dlkm，等 /dev/dri/card0
        └ 验收：modetest 出画面  ← 第一个真实里程碑

阶段 3  输入
        └ evtest 看到 6 键 + 触摸
        └ 验收：按键有事件、触摸有 ABS_MT

阶段 4  PocketJS
        └ 用 SPEC.md 的 profile（375×667@2x）编译/运行 pocket-linux-kms
        └ 验收：卡片启动器显示在 750×1334 屏上，触摸可导航

阶段 5  音频（唯一的大工作量）
        └ techpack 模块 + ADSP + mixer → aplay 出声
        └ 再上 mpv / musicd

阶段 6  电源/息屏
        └ fiio_wakeup 的 wake lock 语义 → 息屏放歌
```

**阶段 2 是整个项目的第一个真里程碑**：它同时验证启动链、模块链、DTB 面板选择三件事。

---

## 7. 若不满足前置条件：替代方案

| 情况 | 建议 |
|---|---|
| P2 失败（触摸是 focaltech 且无驱动） | 仍可做"纯按键 DAP"（6 个媒体键 + 触摸缺失），但触屏目标落空 → 换设备 |
| P4 失败（无 `/dev/dri/card0`） | 需自定义内核加 `CONFIG_DRM_FBDEV_EMULATION`（Plan-B 路线，JM21 已验证自研内核可启动） |
| R1 长期无解（音频起不来） | 保留 Android，把 PocketJS 作为 Android 上的一个 app（DSU 或直接安装）——但这偏离 BaseOS 目标 |
| 整体评估后仍想换设备 | 优先选**已有 Linux 触摸支持**的设备：rocknix 的 `SM6115` 目标已含 msm/DPU + 触摸驱动补丁集（[R9] 反向证据：H700 无触摸）；或直接用 H700 家族（现成） |

---

## 8. 交付物清单

| 文件 | 内容 |
|---|---|
| `README.md` | 本文件：结论 + 决策建议 |
| `boot-chain.md` | ① 启动链 |
| `kernel.md` | ② 内核 |
| `display-touch.md` | ③ 显示与触摸 |
| `audio.md` | ④ 音频 |
| `input.md` | ⑤ 输入 |
| `power.md` | ⑥ 电源 |
| `storage-risk.md` | ⑦ 存储与刷机风险 |
| `pocketjs-gap.md` | ⑧ PocketJS 落地差距 |
| `SPEC.md` | Device Profile 草案（YAML frontmatter，机器可读） |
| `SOURCES.md` | 全部来源 + 命令输出 + 推断标注 |
| `DIFF-vs-round1.md` | 与第一轮的逐条差异 |
| `tools/parse_spec.py` | SPEC 解析 + schema 校验（双 YAML 解析器交叉验证） |
| `tools/fixtures/spec-broken.md` | 反面用例（验证校验器真能报错） |
| `evidence/` | 15 个证据文件（DTBO 索引、两个 entry 的完整 DTS、kernel config、bootconfig、vbmeta、模块清单、ABL 证书、xbl 字符串、两份运行日志） |

---

## 9. 待实机验证清单（汇总，共 61 项）

按主题合并（详细命令在各文档）：

| 主题 | 项数 | 编号 |
|---|---|---|
| 启动链 | 7 | V1–V7 |
| 内核 | 9 | K1–K9 |
| 显示/触摸 | 9 | D1–D9 |
| 音频 | 9 | A1–A9 |
| 输入 | 7 | I1–I7 |
| 电源 | 8 | P1–P8 |
| 存储 | 7 | S1–S7 |
| PocketJS | 5 | J1–J5 |

**其中 12 项**同时记录在 `SPEC.md` 的 `verified_on_device.items` 里，全部 `done: false`；`parse_spec.py` 每次运行都会打印 `unverified: 12 item(s) still need hardware`。
