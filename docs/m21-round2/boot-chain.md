# ① 启动链：M21 的 bootloader、解锁与替换 boot/rootfs

调查日期：2026-10-30。**所有结论均由固件离线解析或公开文档得出；无 M21 实机。** 每条标注证据与置信度。

置信度定义：**高** = 直接读到官方镜像/官方文档原文；**中** = 社区实测记录（可复核的原始输出）；**低** = 间接推断。

---

## 1. 结论先行

| 问题 | 结论 | 置信度 |
|---|---|---|
| 是否 Android Fastboot（非仅厂商菜单） | **是 Android ABL fastboot**。官方说明的 "fastboot 模式" 与 AOSP 解锁语义一致；ABL 用 QCT **测试密钥**签名，未用生产 release key | 高（签名）/中（协议行为） |
| `fastboot devices` / `getvar all` 是否可用 | **预期可用，未实测**（JM21 同平台已实测 `fastboot boot` 成功） | 中 |
| `fastboot boot <img>` | **JM21 已实测成功（含自定义内核）**；M21 无直接记录 | 中（JM21）/低（M21） |
| `fastboot flash` | JM21 社区已实测（Magisk patch init_boot、刷 recovery、刷 system） | 中 |
| `fastboot flashing unlock` | **预期可用**：签名是 dev-keys + `SECURE BOOT = no` 的社区记录；但**没有 M21 的 `flashing unlock` 原始输出** | 中 |
| 能否替换 boot / rootfs | **能**（三条独立路径，见 §5），代价是解锁 + 关 AVB 校验 | 中 |
| 双系统 / SD 启动 | **可行且推荐**（rootfs 放 microSD，不碰 Android 分区），但需自定义 initramfs 与 cmdline，未实测 | 低（方案）/中（硬件支持） |
| EDL 救砖 | **没有公开 QFIL/firehose 包**；OTA 内无 `prog_firehose`。救砖只能靠 recovery sideload 官方 OTA | 高 |

**一句话**：M21 的启动链控制权**大概率可以拿到**，而且比第一轮判断的乐观——依据是同一 ABL/同一 vendor tree 的 JM21 已被社区实测 `fastboot boot` 自定义内核成功；M21 缺的只是"有人在同一台机器上跑一遍"。

---

## 2. 证据：OTA 与镜像结构

`payload.bin` 解析结果（`firmware/analysis-results.txt`，本仓库 `docs/m21-round2/evidence/` 亦收录关键片段）：

```
MODEL_NAME=FiiO M21
pre-device=bengal_515
ota-type=AB
post-sdk-level=33
post-security-patch-level=2023-02-05
post-build=qti/bengal_515/bengal_515:13/TKQ1.230110.001/eng.fiio.20260428.170642:user/dev-keys
```

- `ota-type=AB` → **A/B 双槽**，`boot_a/boot_b`、`init_boot_a/_b`、`vendor_boot_a/_b`、`recovery_a/_b` 各自独立。
- `user/dev-keys` → 整包用**开发密钥**签名，不是 `release-keys`。这对自定义镜像是**最有利**的情形：AVB 链条上的公钥来自测试链（见 §3）。
- payload 19 个分区，**没有 `super` 分区名**（`firmware/payload-partitions.txt`），说明动态分区在 payload 里以逻辑分区形式承载（`system`/`vendor`/`product`/`odm`/`system_ext` 直接列出）。

各启动镜像头部（`evidence/boot-info.txt`、`init-boot-info.txt`、`vendor-boot-info.txt`）：

| 镜像 | magic | header | 关键字段 |
|---|---|---|---|
| `boot.img` | `ANDROID!` | 4 | `kernel_size=49,646,080`、**`ramdisk_size=0`**、cmdline 空 |
| `init_boot.img` | `ANDROID!` | 4 | `kernel_size=0`、`ramdisk_size=2,005,924` |
| `vendor_boot.img` | `VNDRBOOT` | 4 | `dtb_size=1,006,645`、`vendor_ramdisk=7,458,706`、`page=4096` |
| `recovery.img` | `ANDROID!` | 4 | `kernel_size=0`、`ramdisk_size=14,534,420` |

**这条结构决定了 BaseOS 的投递方式**（Android 13 GKI 三段式）：

```
ABL 取 kernel   ← boot_<slot>          （纯 arm64 Image，无 ramdisk）
ABL 取 ramdisk  ← init_boot_<slot>      （first-stage initramfs，Magisk 就放这里）
ABL 取 dtb+ramdisk ← vendor_boot_<slot> （DTB + vendor 模块 + bootconfig）
```

`vendor_boot` 的 bootconfig（`evidence/vendor-boot-bootconfig.txt` 全文）：

```
androidboot.hardware=qcom
androidboot.memcg=1
androidboot.load_modules_parallel=true
androidboot.usbcontroller=4e00000.dwc3
androidboot.qhardware=SC200VWF
```

- `qhardware=SC200VWF` 是**板级硬件 ID**，可作为"确实是 M21 固件"的判据。
- `androidboot.usbcontroller=4e00000.dwc3` → USB 控制器是 dwc3，`CONFIG_USB_CONFIGFS=y` 已在 kernel config 中（见 kernel.md），**gadget（adb/rndis/mass storage）可在 Linux 侧复用**。

---

## 3. AVB 与签名链（`evidence/vbmeta-info.txt`）

```
vbmeta:  min libavb 1.0, SHA256_RSA4096, flags 0, rollback index 0, avbtool 1.2.0
         chain → vbmeta_system (rollback idx location 2, RSA2048)
         hash descriptors: boot, dtbo, init_boot, recovery, vendor_boot
         hashtree: odm, system_dlkm, vendor, vendor_dlkm
vbmeta_system: RSA2048, rollback 1675555200 (= 2023-02-05)
         hashtree: product, system, system_ext
```

`flags 0` → **verity 与验证都处于"启用"声明状态**。这意味着：

- 锁定时只接受与 `vbmeta` 完全匹配的镜像；
- 解锁后 Android 进入 `verifiedbootstate=orange`，通常**停止校验**（AOSP 行为，[S11]）——这正是自定义镜像的入口。

ABL 自身的签名链（`evidence/abl-embedded-certs.txt`，用 `openssl x509` 读 `abl.img` 内嵌 DER）：

```
subject: CN=SecTools Test User, O=SecTools        (2026-04-28 → 2046-04-23)
issuer : CN=QUALCOMM Attestation CA
root   : CN=QCT Root CA 1, OU="General Use Test Key (for testing 13 only)"
         (2018-12-13 → 2038-12-08)
```

**判读**：ABL 由 QCT **General Use Test Key** 签发，不是 OEM 生产密钥。AOSP/Qualcomm 的约定是：**test key 签名的 bootloader 不启用 "unlock 需 OEM 授权" 的强制门禁**，`fastboot flashing unlock` 一般直接可用（相比 release key 设备需要 `ro.oem_unlock_supported=1` 且可能被厂商关闭）。**推断（未验证）**：M21 的 unlock 阻力低于普通手机。

---

## 4. 铁证：同一启动链的 JM21 已跑通自定义内核

这不是推断，是社区实测记录（[S7] `docs/45-plano-b-kernel.md` §8，原文含 `fastboot` 输出）：

```
mkbootimg --header_version 4 --kernel Image --os_version 13.0.0 --os_patch_level 2023-02
fastboot boot boot_ours.img
Sending 'boot.img' (39708 KB)  OKAY
Booting                        OKAY

Linux version 5.15.41-g9ded8564ff52-dirty (ocnaibill@makise)
clang 14.0.7 — #3 SMP PREEMPT Sat Oct 24 14:07:42 -03 2026
```

即：**用公开 CAF 5.15 树编译的内核，通过 `fastboot boot` 在锁外加载运行，且成功加载了全部 FiiO vendor 模块（含 `cs43198`、`gw-fpga`），并实测 PCM 44.1k/384k 与 DSD64 出声。** 同一文档还核对了 AVB：5/5 hash descriptor 重算一致。

为什么这能支撑 M21 的结论：

| 维度 | JM21 | M21 | 证据 |
|---|---|---|---|
| OTA `pre-device` | `bengal_515` | `bengal_515` | 两边 metadata 一致 |
| SoC | khaje (SM6225) | khaje (SM6225) | DTBO `qcom,khaje*` |
| kernel | 5.15.41-g9ded8564ff52-dirty | **同一 vermagic** | 两边 .ko 的 `modinfo` |
| ABL | QCT test key, `DEVICE STATE=unlocked` | 同签名方式（推断） | 见 §3 |
| vendor 模块集 | `anolog_board_jm21`/`power_board_jm21` | `anolog_board_m21`/`power_board_m21` | 两边 modules.load |

**差异只在板级外设（2 DAC vs 4 DAC、面板/触摸不同），启动链本身是共用的。** 这是第二轮最重要的修正：第一轮把"没有 M21 的 fastboot 证据"当成"启动链未知"，但同 vendor tree 的同 SoC 设备已证明 ABL 行为。

⚠️ **必须区分的反例**：JM21 用 `fastboot boot` 加载"内核 + recovery ramdisk"时**失败**了（`docs/46-recovery-twrp.md`：bootloader 接受但回到 Android，无 UI）。这说明 **ABL 在 `fastboot boot` 时可能只取 boot 镜像里的 kernel，忽略其 ramdisk**。对 BaseOS 的直接后果见 §5 路径 B/C。

---

## 5. 替换 boot / rootfs 的三条路径

### 路径 A：`fastboot boot` 临时启动（零写入，先验证）

```
fastboot boot baseos-probe.img     # kernel=stock Image，dtb=vendor_boot 的 dtb
```
- 用途：只做"内核能起、串口/USB gadget 能挂"的探针。
- 限制：**ramdisk 是否被采纳未知**（§4 反例）。若被忽略，就只能靠 stock init 起 Android，拿不到 Linux shell。
- 风险：低（不写入；断电重启即恢复）。

### 路径 B：替换 `init_boot_<slot>`（最贴合 Android 13 的现实路径）★

Magisk 在 JM21 上正是这么做的（`init_boot_a` patch → root）。机制：

```
ABL → boot_<slot>(stock kernel) + init_boot_<slot>(我们的 first-stage init) + vendor_boot_<slot>
```

- 把 `init_boot` 的 ramdisk 换成"静态 busybox + 我们的 init"，init 里 mount microSD 上的 rootfs，`switch_root` 进 BaseOS。
- `init_boot` 分区 8,388,608 B（`payload` 里 `init_boot 8.4 MB`），**只放 init 与 busybox 足够**（约 1–2 MB）；不需要塞 39 MB 的 `msm_drm.ko`。
- 需要：解锁 + `fastboot flash init_boot` + 关 AVB 校验（`fastboot --disable-verity --disable-verification flash vbmeta` 或直接刷与镜像匹配的 vbmeta）。
- **优点**：stock kernel 不动、`vendor_boot` 不动 → 显示/音频所需的 DTB 与 vendor 模块全在原位。
- **风险**：中（写分区，但可回滚）。

### 路径 C：整包替换 `boot` + `init_boot` + `vendor_boot`

- 可用于自定义内核（Plan-B 路线，JM21 已验证 ABI 兼容）。
- 需要重算 vbmeta 或关校验。
- **优点**：可加 `CONFIG_DRM_FBDEV_EMULATION`、可定制 cmdline（`root=/dev/mmcblk1p1`）。
- **风险**：中高（三处写入，回滚需 OTA）。

### 双系统 / SD 启动

- 硬件层面**支持**：`fstab.emmc` 里有 `4784000.sdhci` 的 `sdcard1` voldmanaged 条目，DTB 里 `sdhci@4784000` 存在（`mmc1`），FiiO 规格写 microSD 最大 2TB [S1]。
- 推荐组合：**路径 B（改 init_boot）+ rootfs 放 microSD**。Android 分区一个字节不动（除 init_boot_a），`fastboot --set-active=b` 即回原厂。
- `root=` 指向 SD 需要在 cmdline 里给出，而 cmdline 来自 ABL + bootconfig；**修改 bootconfig 需要刷 `vendor_boot`**（bootconfig 长度 155 B，在 vendor_boot 尾部）。所以更省事的是：**init 里不依赖 `root=`**，用 initramfs 自己 mount SD 再 `switch_root`（完全用户态控制，与 cmdline 无关）。

---

## 6. 解锁与恢复（每步风险）

| 步骤 | 读/写 | 可逆 | 备注 |
|---|---|---|---|
| `fastboot getvar all` | 只读 | — | 先拿分区表/槽位/`current-slot` |
| `fastboot oem device-info` | 只读 | — | 直接读 `Device unlocked: true/false` |
| `adb reboot recovery` / `adb reboot bootloader` | 只读 | — | 不进 fastboot 菜单也可靠 |
| `fastboot boot <img>` | 不写 | 是 | 首选验证手段 |
| `fastboot flashing unlock` | 擦 userdata | **否**（数据丢） | 数据先备份 |
| `fastboot flash init_boot_a` | 写 | 是（重刷官方 OTA 对应镜像） | 路径 B |
| `fastboot flash boot_a` / `vendor_boot_a` | 写 | 是 | 路径 C |
| `fastboot flash vbmeta` | 写 | 是（OTA 里有 vbmeta.img） | 关校验 |
| `fastboot flash xbl*` / `abl*` / `rpm` | 写 | **否（无 EDL 包 = 真砖）** | **绝不** |

**救砖矩阵**（`storage-risk.md` 有完整版）：

1. 官方 OTA 完整包 + recovery sideload（签名匹配 `dev-keys`，`update_engine` 会校验）；
2. 同槽/对槽 `fastboot flash` 回官方镜像（payload-dumper 解出 `boot/init_boot/vendor_boot/vbmeta`）；
3. `fastboot --set-active=b` 切到未动过的槽；
4. **EDL：不可用**。`xbl.img` 里有 `sbl1_sahara.c`、`Sahara: Hello pkt sent`（`evidence/xbl-sahara-strings.txt`），说明 SoC 侧具备 Sahara/EDL 通道，但 **OTA 与公开渠道都没有 `prog_firehose`**（全盘 grep=0）。无 firehose 的 EDL 只能读不能写。

---

## 7. 待实机验证（按顺序，全部只读或可逆）

| # | 命令/操作 | 期望 | 若不符 |
|---|---|---|---|
| V1 | `adb shell getprop ro.boot.qhardware` | `SC200VWF` | 固件不是本文分析的版本 |
| V2 | `fastboot oem device-info` | 打印 `Device unlocked` | 记录实际值 |
| V3 | `fastboot getvar all` | 分区表含 `_a/_b`、`current-slot` | 存档全文 |
| V4 | `fastboot getvar unlocked` / `getvar secure` | 布尔 | — |
| V5 | `fastboot boot probe.img`（kernel=stock Image） | `Booting OKAY` + 设备起 Android | 说明 fastboot boot 被拒 |
| V6 | 同上但带 1 MB 测试 ramdisk | 观察 ramdisk 是否被执行（打印一行） | 验证 §4 的"忽略 ramdisk"假设 |
| V7 | `fastboot flashing unlock`（**会擦数据**） | — | 需用户明确同意后再做 |

V5/V6 是**整条路线的 go/no-go**，且都不写分区。
