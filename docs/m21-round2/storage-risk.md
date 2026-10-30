# ⑦ 存储与刷机风险

调查日期：2026-10-30。无实机，**未对任何设备执行写操作**。本文只描述可从固件推导的事实与风险模型。

---

## 1. 结论先行

| 问题 | 结论 | 置信度 |
|---|---|---|
| 分区结构 | **A/B + 动态分区（super 5,371,461,632 B = 5.00 GiB）** | 高 |
| `super` 在 payload 里 | ❌ 不在（payload 只含**逻辑分区** `system`/`vendor`/`product`/`odm`/`system_ext`） | 高 |
| 保留原厂系统 | **有两条**：① A/B 槽（改 A 保 B）② microSD 放 rootfs，不动 eMMC | 高 |
| 回滚 | 完整 OTA 包 + `adb sideload`，或 `fastboot flash` 从 payload 解出的原镜像 | 高 |
| **变砖风险等级** | **中**（只要不碰 `xbl*` / `abl*` / `rpm`） | 中 |
| EDL 救砖 | **不可用**（无公开 QFIL/firehose 包，OTA 内 0 命中） | 高 |
| 最危险的三个操作 | `flash xbl*`、`flash abl*`、`flashing unlock` 后不做备份 | 高 |

---

## 2. 分区表（从 payload + OrangeFox 交叉验证）

### 2.1 payload 里的 19 个分区（`firmware/payload-partitions.txt`）

```
abl        217 kB
boot       101 MB
dtbo       8.4 MB
init_boot  8.4 MB
modem      36 MB
odm        1.2 MB
product    244 MB
recovery   101 MB
rpm        229 kB
system     2.3 GB
system_dlkm 434 kB
system_ext 524 MB
vbmeta     8.2 kB
vbmeta_system 4.1 kB
vendor     652 MB
vendor_boot 101 MB
vendor_dlkm 757 MB
xbl        3.2 MB
xbl_config 45 kB
```

**没有 `super`**，但有 5 个逻辑分区（`system`/`system_ext`/`product`/`vendor`/`odm` 中的前 5 个 + `system_dlkm`/`vendor_dlkm`）→ 这些在设备上位于 `super` 内。

### 2.2 OrangeFox 的实测尺寸（`BoardConfig.mk:44-50`，注释明确写 "from `fastboot getvar all`"）

```
BOARD_BOOTIMAGE_PARTITION_SIZE         = 100663296    (96 MiB)
BOARD_RECOVERYIMAGE_PARTITION_SIZE     = 104857600    (100 MiB)
BOARD_DTBOIMG_PARTITION_SIZE           = 25165824     (24 MiB)
BOARD_INIT_BOOT_IMAGE_PARTITION_SIZE   = 8388608      (8 MiB)
BOARD_VENDOR_BOOTIMAGE_PARTITION_SIZE  = 100663296    (96 MiB)
BOARD_SUPER_PARTITION_SIZE             = 5371461632   (5.00 GiB)
BOARD_USES_METADATA_PARTITION          = true
```

⚠ **`dtbo` 分区 24 MiB，但 payload 里的 `dtbo.img` 只有 8.4 MB**（实际 2,771,658 B 有效 + 稀疏填充）。这说明 **dtbo 有 15 MB 空闲**，可用于放额外的 overlay（对 BaseOS 有利）。

### 2.3 物理分区（从 fstab 推断完整列表）

`vendor_boot` 的 `fstab.emmc` 与 OrangeFox 的 `recovery.fstab` 揭示：

```
逻辑分区（super 内）：system, system_ext, vendor, vendor_dlkm, system_dlkm, odm, product
物理分区：userdata(ext4), metadata(f2fs), misc, persist, fiioconfig, modem,
          dsp, bluetooth, boot, init_boot, vendor_boot, dtbo, vbmeta,
          vbmeta_system, recovery, abl, xbl, xbl_config, rpm
```

**注意 `fiioconfig` 分区**（`/mnt/vendor/fiioconfig`）——这是 FiiO 独有的配置分区，**存放校准数据**（DAC 参数、电池曲线等）。JM21 dossiê 明确警告："gravar `fiioconfig` = **crítico**，只有备份后才能写"。

---

## 3. 保留原厂系统的三条策略（按安全度排序）

### 策略 1（最安全）：microSD 引导，eMMC 零写入 ★

```
eMMC: 完全不动
microSD: 分区1 = initramfs / boot 资产；分区2 = rootfs（ext4）
投递方式: 不改任何分区 → 靠 fastboot boot 临时加载（但见 boot-chain §4 的限制）
或:      改 init_boot_a（唯一写入）→ init 里 mount microSD → switch_root
```

- 优点：**原厂系统 100% 完好**，`fastboot --set-active` / 重刷 `init_boot` 即恢复。
- 缺点：需改 `init_boot_a`（写入 1 个分区，8 MiB）。

### 策略 2：A/B 双槽隔离

```
slot A: 保持官方（boot_a/init_boot_a/vendor_boot_a 不动）
slot B: BaseOS（boot_b/init_boot_b/vendor_boot_b）
切换:   fastboot --set-active=a|b
```

- 优点：切换零成本，回滚一条命令。
- 缺点：需写 3 个 `_b` 分区 + `vbmeta`（要么匹配重算，要么关校验）。
- 注意：`system_b` 等逻辑分区不需要动（BaseOS 不用 super）。

### 策略 3：整盘替换（不推荐）

- 重写 GPT、覆盖 `super`。
- 风险高、收益低——BaseOS 不需要 Android 的任何分区。

**推荐策略 1**，理由：改动面最小（1 个分区），且 microSD 是 M21 的官方卖点（支持 2 TB [S2]），读写性能足够跑 PocketJS（UI 是 60 fps 的 2D 合成，不是视频解码）。

---

## 4. 变砖风险矩阵

| 操作 | 影响面 | 可逆 | 救砖路径 | 风险 |
|---|---|---|---|---|
| `fastboot getvar all` | 无 | — | — | **无** |
| `fastboot boot <img>` | 无写入 | — | 断电重启 | **无** |
| `adb reboot recovery` / `sideload` | 无（除非装包） | — | — | 低 |
| `fastboot flash init_boot_a` | 1 分区 | 是（重刷原镜像） | OTA / fastboot | **低** |
| `fastboot flash boot_a` | 1 分区 | 是 | 同上 | 低 |
| `fastboot flash dtbo_a` | 1 分区 | 是 | 同上 | 低（且 24 MiB 有余量） |
| `fastboot flash vendor_boot_a` | 1 分区 | 是 | 同上 | 中（含 vendor 模块，错了没显示/没音频） |
| `fastboot flash vbmeta` | 校验链 | 是（OTA 有原文件） | 同上 | 中 |
| `fastboot --disable-verity --disable-verification flash vbmeta` | 校验链 | 是 | 同上 | 中（**必要步骤**，但会降低安全性） |
| `fastboot flashing unlock` | 擦 userdata | **否** | — | 中（**数据丢失**） |
| `fastboot flash system/vendor/product` | super 内 | 是（重新走 OTA） | OTA sideload | 中高（可能破坏 super 元数据） |
| `fastboot flash super` | 整个 super | 是（但其 5 GB，需完整镜像） | OTA | 高 |
| `fastboot flash xbl` / `xbl_config` | 引导链 | **否** | **无 EDL = 真砖** | **极高** |
| `fastboot flash abl` | 引导链 | **否** | 同上 | **极高** |
| `fastboot flash rpm` | 引导链 | **否** | 同上 | **极高** |
| 写 `fiioconfig` | 校准数据 | **否** | **无备份 = 永久丢校准** | **极高** |
| 写 `persist` | DRM/序列号 | **否** | 同上 | **极高** |

**红线清单（绝不执行）**：

```
fastboot flash xbl / xbl_config / abl / rpm / tz / hyp / devcfg
fastboot erase xbl / abl / rpm
adb shell dd ... of=/dev/block/bootdevice/by-name/{xbl,abl,rpm,fiioconfig,persist}
```

---

## 5. 备份优先级（在第一次写之前必做）

| 优先级 | 分区 | 大小 | 为什么 | 方法 |
|---|---|---|---|---|
| **P0** | `fiioconfig` | 小 | 校准数据，丢了不可恢复 | `adb shell su -c 'dd if=/dev/block/by-name/fiioconfig of=/sdcard/fiioconfig.img'` |
| **P0** | `persist` | 小 | DRM/序列号 | 同上 |
| **P0** | `modem`（含 `modemst1/2`） | 36 MB | 基带校准 | 同上 |
| **P1** | `boot_a` / `init_boot_a` / `vendor_boot_a` / `dtbo_a` / `vbmeta` / `vbmeta_system` | ~120 MB | 回滚直接刷 | `payload-dumper-go` 从 OTA 解即可（**不需要设备**） |
| **P1** | 完整 `payload.bin` | 1.65 GB | 万能恢复 | 已下载（`SHA-256 1d3ed710…`） |
| **P2** | `userdata` | ~52 GB | 用户数据 | `adb pull` 或 `adb backup` |
| **P3** | `super` 全镜像 | 5 GB | 极端情况 | `adb shell su -c 'dd if=/dev/block/by-name/super'`（需大 SD 卡） |

**关键洞察**：P1 的所有镜像都可以**从 OTA 离线解出，不需要先 root 设备**（`payload-dumper-go` 已经在 HX90 上跑通过，见 `docs/m21-round2/SPEC.md` 附带的提取记录）。所以"回滚材料"在动手前就已经齐了。

JM21 社区有现成的完整备份流程（`docs/42-backup-completo.md`），可直接复用。

---

## 6. 救砖路径（按可用性排序）

### 路径 1：recovery + sideload（**首选**）

```bash
adb reboot recovery           # 或 音量减 + 插 USB（官方说明 [S3]）
# recovery 菜单选 "Apply update from ADB"
adb sideload M21-update-1.0.8.zip
```

- 前提：recovery 分区完好（我们不改它）。
- 成功率：高（官方 OTA 签名匹配）。
- 注意：`unzip -t` 对签名尾返回非零是正常的（见 round1 分析），**不要**因此认为包坏了。

### 路径 2：fastboot 刷回原镜像

```bash
fastboot getvar current-slot        # 确认槽位
fastboot flash boot        boot.img
fastboot flash init_boot   init_boot.img
fastboot flash vendor_boot vendor_boot.img
fastboot flash dtbo        dtbo.img
fastboot flash vbmeta      vbmeta.img
```

- 前提：bootloader 解锁（否则 `flash` 被拒，但 `boot` 可能仍可用）。
- 前提：镜像从 OTA 解出，**与设备当前版本一致或更新**（AVB rollback index 会拒绝旧版本）。

### 路径 3：A/B 槽切换

```bash
fastboot --set-active=b    # 或 a
```

- 前提：另一槽完好。
- 优点：零秒级、零风险。

### 路径 4：EDL（**不可用**）

`xbl.img` 里有 Sahara 协议（`evidence/xbl-sahara-strings.txt`：`Sahara: Hello pkt sent`、`sbl1_sahara.c`、`sbl1_hw_dload_init`），说明 SoC 侧具备 9008 模式。但：

```
$ grep -c -a prog_firehose M21-update-1.0.8.zip    → 0
$ grep -c -a rawprogram    M21-update-1.0.8.zip    → 0
$ grep -c -a firehose      M21-update-1.0.8.zip    → 0
```

- **没有 firehose programmer，EDL 无法写入**。
- 公开 SM6225 loader（`bkerler/Loaders`）存在，但需 Secure Boot 关闭才可用；**M21 的 `SECURE BOOT = no` 只在 JM21 的社区 dump 上被确认**（`cdn.head-fi.org/a/12820990.txt`，但那份 dump 的模块名是 `*_jm21`，**不是 M21**）。
- 风险：用错 loader 会让 Sahara 进入死锁状态，**比砖更糟**。

**结论：把 EDL 当成不存在来规划。** 这一条与第一轮结论一致（第一轮也判定"EDL 不可用"），**仍然有效**。

---

## 7. 关于 "SECURE BOOT = no" 证据的可靠性（重要更正）

第一轮引用了 Head-Fi 附件 `cdn.head-fi.org/a/12820990.txt`，称其证明 M21 "DEVICE STATE = unlocked / SECURE BOOT = no"。

**本轮复核发现该 dump 不是 M21**：

```
$ grep -n 'anolog_board\|power_board' headfi.txt
321:anolog_board_jm21        ← JM21 的模块名（M21 是 anolog_board_m21）
554:power_board_jm21
$ grep -nE 'PRODUCT_Name|VARRIANT|DEVICE STATE|SECURE BOOT' headfi.txt
 5: PRODUCT_Name = khaje
 6: VARRIANT = SM_ EMMC
10: SECURE BOOT = no
11: DEVICE STATE = unlocked
$ grep -n 'M21\|JM21' headfi.txt    → 无直接型号字符串
```

模块名 `anolog_board_jm21` / `power_board_jm21` 明确指向 **JM21**，不是 M21。

**所以：**

- `DEVICE STATE = unlocked` / `SECURE BOOT = no` 是 **JM21** 的证据；
- M21 的同类证据**目前没有**（Reddit 线程已 403 无法复核；AliExpress wiki 是 AI 生成，不采信）；
- **但**上述事实增强了"M21 大概率也可解锁"的推断（同 ABL/同 test key 签名），只是**不再是"直接证据"**。

这是本轮对第一轮结论的一处**降级修正**，记录在 `DIFF-vs-round1.md`。

---

## 8. 存储相关风险（非刷机）

| 风险 | 说明 | 缓解 |
|---|---|---|
| microSD 质量 | 系统盘在 SD 上，坏块/掉速直接影响体验 | 用 A2/U3 卡；rootfs 加 `errors=remount-ro` + 定期 fsck |
| SD 掉卡 | `/` 消失 → 内核 panic | rootfs 用 overlayfs（只读底层 + tmpfs 上层），减少写 |
| eMMC 剩余寿命 | BaseOS 不写 eMMC，无影响 | — |
| `fiioconfig` 被误挂载 | 只读挂载，绝不写 | fstab 里 `ro,nosuid,nodev` |
| 双系统时间冲突 | Android 与 Linux 的 RTC 时区约定 | BaseOS 用 UTC（`hwclock -u`），PJOS 已是此约定 |

---

## 9. 待实机验证

| # | 命令 | 期望 | 用途 |
|---|---|---|---|
| S1 | `adb shell ls -l /dev/block/by-name/` | 全部分区 + 大小 | **拿到真实分区表**（比 payload 更权威） |
| S2 | `adb shell cat /proc/partitions` | 同上 | 交叉验证 |
| S3 | `fastboot getvar all` | `current-slot`、`slot-count`、`secure`、`unlocked` | 确认 A/B 与锁状态 |
| S4 | `adb shell df -h /data /storage/*` | 空间 | 评估能否容纳备份 |
| S5 | `adb shell su -c 'dd if=/dev/block/by-name/fiioconfig of=/sdcard/fiioconfig.img'` | 成功 | **P0 备份** |
| S6 | `adb shell su -c 'dd if=/dev/block/by-name/persist of=/sdcard/persist.img'` | 成功 | **P0 备份** |
| S7 | `adb shell ls -l /dev/block/by-name/ \| grep -E 'xbl|abl|rpm'` | 存在 | 确认红线分区的实际名字 |
