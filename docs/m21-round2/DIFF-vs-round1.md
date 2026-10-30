# 与第一轮的差异

第一轮：commit `d5f6ea7`（`README.md`，143 行）。本轮：`docs/m21-round2/`。

---

## 0. 总结：第一轮的偏差是什么

第一轮把评估基准设成 **"能否 mainline 化 / 有没有完整 DTS 与 BSP"**，于是：

- 结论压在"Linux Porting Difficulty 很高"、"BSP Risk 很高"；
- `fastboot boot` 因为"M21 没有直接证据"被判为未知；
- 主线化缺失被当成否决项。

**本项目的目标其实是 `Bootloader → Linux → PocketJS Desktop → Music Player`。** 换基准后，判断的重心整体移到"启动控制权 + 用户态能否拼出来"，主线化降为加分项。因此本轮大量结论**方向不变但权重反转**，另有 **3 处事实性修正**。

---

## 1. Top 3 修正（会改变决策的）

### 修正 1：显示路径完全反转 —— M21 没有 `/dev/fb0`

| | 第一轮 | 第二轮 |
|---|---|---|
| 说法 | "PocketJS 触屏 UI…KMS/fbdev 与 Rust ABI 适配"（未区分） | **M21 的 stock kernel `CONFIG_FB` 未编入，`DRM_FBDEV_EMULATION` 不存在，`msm_drm.ko` 不引用 `drm_fbdev_generic_setup`** → 没有 `/dev/fb0` |
| 证据 | — | kernel config（`# CONFIG_FB is not set`）、`nm -u msm_drm.ko`、kernel `Image` 内 `find` 为 -1 |
| 影响 | 以为可以沿用 H700 的 fbdev 路线 | **必须走 DRM/KMS**；PJOS 的 `docs/13` G1 假设（fbdev）在 M21 上直接失效 |

这是本轮最有价值的发现：**H700 与 M21 在显示上是两个互斥的世界**（H700 只有 fb0，M21 只有 card0）。

### 修正 2："SECURE BOOT = no / DEVICE STATE = unlocked" 证据是 **JM21 的，不是 M21 的**

| | 第一轮 | 第二轮 |
|---|---|---|
| 说法 | 引用 `cdn.head-fi.org/a/12820990.txt` 作为 M21 "DEVICE STATE = unlocked" 的个案证据 | 该 dump 的 kernel 模块名是 **`anolog_board_jm21` / `power_board_jm21`** → 是 JM21 |
| 证据 | 第一轮 README §2 的 [4][5] | `grep 'anolog_board\|power_board'` 命中 `*_jm21`；全文无 "M21" 型号串 |
| 影响 | 把 JM21 的证据当作 M21 的 | **降级为推断**：M21 可解锁的把握从"有个案"变成"同平台类推" |

同时：第一轮引用的 Reddit 链接 **2026-10-30 已 403**（登录墙 + `api.reddit.com` 亦 403），**无法复核**。AliExpress 的 "M21 root" 页面自带 AI 生成声明，不采信。

### 修正 3：`fastboot boot` 的证据等级 —— 从"未找到成功案例"变成"同平台已实测成功"

| | 第一轮 | 第二轮 |
|---|---|---|
| 说法 | "**没有证据**证明该设备支持主机端 `fastboot boot baseos.img`"（结论：Stage 1 是 go/no-go，若不可用就停） | **JM21（同 `bengal_515`、同 kernel vermagic、同 ABL）已实测 `fastboot boot` 自定义内核成功**，并加载了全部 FiiO 模块、PCM/DSD 出声 |
| 证据 | — | [C1] `docs/45-plano-b-kernel.md` §8 的 `Sending/Booting OKAY` 原文 + `Linux version … #3 SMP PREEMPT` 编译日期 |
| 影响 | 把"未知"当"高风险" | 风险等级从 **高** 降到 **中**；并从"必须先用 fastboot boot 验证否则停止"改为"先做只读 getvar，再决定是否走 init_boot 路线" |

---

## 2. 逐条对照第一轮的结论

第一轮 README 的 10 节，逐条给"仍有效 / 需修正 / 失效"。

| 第一轮章节 | 结论 | 本轮判定 | 说明 |
|---|---|---|---|
| §1 设备事实 | Snapdragon 680 / A13 / 4 GB / 64 GB / 750×1334 / 4×CS43198 | ✅ **有效** | 本轮用官方页 [S1][S2] 复核；补上 4000 mAh、microSD 2 TB、DPI≈326、60 Hz |
| §2 Bootloader、解锁与临时启动 | "fastboot 有官方菜单级证据；解锁未知；`fastboot boot` 未找到案例" | ⚠ **部分修正** | fastboot 部分不变；**解锁与 `fastboot boot` 依据 JM21 实测上调**（见修正 3）；"unlocked 个案"降级（见修正 2） |
| §3 官方固件与解析 | 19 分区、AVB 1.0、RSA4096、dev-keys、A/B | ✅ **有效** | 本轮完整复核；补出 `flags 0`、`super=5.00 GiB`、dtbo 分区 24 MiB（镜像只用 8.4 MB） |
| §4 启动链 | "完整启动链无实测，不能当已验证" | ⚠ **部分修正** | 方法学正确，但**漏掉了 JM21 的 `fastboot boot` 实测**（本轮补充） |
| §5 BSP 与硬件驱动 | "无 M21 Linux DTS/驱动；音频尤其关键" | ❌ **结论方向需改写** | **驱动全都存在**（`vendor_dlkm` 226 个 .ko，含 `msm_drm`、`goodix`、`cs43198`、`machine_dlkm`）；缺的不是驱动，是**加载顺序与用户态** |
| §6 官方 Kernel + 自定义 RootFS | "原则上可行，M21 上尚未证明" | ⚠ **上调为"同平台已证明"** | JM21 的 Plan-B 已跑通自定义内核 + vendor 模块 + 音频 |
| §7 `baseos.img` 最小启动路线 | "未验证 fastboot 前不写设备；先做串口/ADB shell 探针" | ✅ **有效**（方法），❌ **配方需改** | 方法学保留；但"官方 kernel + 最小 initramfs 临时启动"这条**在 JM21 上验证过会失败**（ramdisk 被忽略），应改为 init_boot 路线 |
| §8 MVP 阶段 | Stage 0–4 | ✅ **有效**，需插入 S2.5 | 本轮保留五阶段并细化为 S0–S7（加入"DRM 出画面"作为独立里程碑） |
| §9 下一步三件事 | 只读 fastboot / 理解 AB 与动态分区 / 采集板级资料 | ✅ **有效** | 本轮把"采集板级资料"具体化为 9 个主题的验证清单（见各文档 §"待实机验证"） |
| §10 与本地 BaseOS 项目关系 | "PJOS 已证明 H700 上 PocketJS 可启动；可复用经验，需单独板级 bring-up" | ✅ **有效并强化** | 本轮把"差距"量化为 **12 项**（`pocketjs-gap.md` §5），其中 3 项是"现有实现直接失效" |

---

## 3. 第一轮没有、本轮新增的事实

| # | 新事实 | 依据 |
|---|---|---|
| N1 | **stock kernel 无 `CONFIG_FB`**，`/dev/fb0` 不存在 | kernel config + `msm_drm.ko` 符号 |
| N2 | **stock kernel 无 `CONFIG_DEVTMPFS`** | kernel config `# CONFIG_DEVTMPFS is not set` |
| N3 | 触摸驱动**只有 goodix**，focaltech 全盘 0 命中 | 226 个 .ko 逐个 grep + 4 个分区原始字节扫描 |
| N4 | **`td4310_1080p` 是悬空引用**（DT 里 4 条面板表，其中一条指向不存在的节点） | 42 个 DTBO entry 全量提取 |
| N5 | 面板参数（60 Hz / 24 bpp / PWM 1..4095 / 前后肩具体值） | entry 40 DTS |
| N6 | 内核有 20 个 `CONFIG_GKI_HIDDEN_*`，`=m` 只有 2 个（`ZRAM`/`ZSMALLOC`） | kernel config |
| N7 | `MODULE_SIG_FORCE` 未设 → 自编模块可加载 | kernel config |
| N8 | `msm_drm.ko` **依赖 `fiio_primary_modules.ko`**（FiiO 改了 DRM） | `modinfo -F depends` |
| N9 | 无 `libasound.so.2`，Android 用 `libtinyalsa.so` | `vendor.img`/`system.img` 扫描 + `readelf` |
| N10 | **PocketJS 的 10-bit 触摸坐标约束**使 750×1334 无法直接做逻辑视口 | 上游 `validatePocketProfile` 实测 |
| N11 | 内核 `CONFIG_MODULE_SIG_PROTECT=y` 但 `SIG_FORCE` 未设 | kernel config |
| N12 | `xbl.img` 有 Sahara 字符串但**无 firehose** | `strings` + payload `grep=0` |
| N13 | 分区尺寸以 `fastboot getvar all` 为源（OrangeFox 注释） | `BoardConfig.mk:44-50` |
| N14 | `fiioconfig` 分区 = FiiO 校准数据 | `fstab.emmc` + JM21 dossiê 风险表 |
| N15 | M21 的 4 个 DAC 由 **FPGA（Gowin）** 中转 | entry 40 DTS + `fw` 文件名 `gw_fpga_firmware_m21.fw` |

---

## 4. 结论档位的变化

| | 第一轮 | 第二轮 |
|---|---|---|
| 总判断 | "暂不建议将 FiiO M21 直接定为 BaseOS 首个触屏设备"（device score 35/100） | **有条件可行**：启动链大概率可行，显示/输入可行，音频是唯一大工作量项 |
| 推荐首个动作 | 实机只读 fastboot 检查；若不能证明临时启动就停止 | **实机只读侦察（V1–V4 + K4/K5 + D5）→ 若确认则可直接进 init_boot 路线** |
| 是否要求 mainline | 隐含要求（BSP/DTS 完整度） | **明确不要求**；stock kernel 可用，主线化只作加分 |
| 音频定位 | "MVP Stage 3" | **第一阶段可跳过**（PocketJS profile 不依赖 audio；播放器走外部 mpv） |

---

## 5. 第一轮仍然完全有效的部分

- 方法学：先只读、先备份、EDL 不可用、不碰引导链分区——**全部保留**；
- OTA 解析与 AVB 结论（RSA4096 / dev-keys / rollback index）——**全部保留**；
- "官方 kernel + 自定义 rootfs 原则上可行"的判断——**保留并升级为已验证**；
- 五阶段 MVP 划分——**保留并细化**；
- "PJOS 的 H700 经验不能直接复用，需要板级 bring-up"——**保留，并量化为 12 项差距**。

---

## 6. 一句话

第一轮错在**基准**（把 mainline 化当门槛），而不是错在**事实**：它的固件分析依然准确。第二轮换了基准后发现，M21 的真实形态是"**驱动很全、用户态很缺、启动链与 JM21 共享**"——这比第一轮描绘的"什么都没有"要乐观，但比"H700 换块板"要难。
