# SOURCES

所有引用、命令输出与文件路径。访问/生成日期见每节。

约定：

- **[FW]** = 从官方 OTA 镜像解析得到（可复现，命令写在 `evidence/`）；
- **[DOC]** = 官方网页/手册；
- **[COMM]** = 社区仓库或实测记录（可复核）；
- **[LOCAL]** = 本机只读参考仓库的源码行；
- **[UNVERIFIED]** = 推断，无直接来源。

---

## 1. 官方固件（本轮实际下载与解析）

| 项 | 值 | 日期 |
|---|---|---|
| OTA URL | `http://m21pack.fiio.net/beta/M21-update-1.0.8.zip` | 2026-10-30 |
| 大小 | 1,657,748,858 bytes | 同上 |
| SHA-256 | `1d3ed710702e4514ac39a75b3f01834daccd64073339f095ab9dd72ffc97cd6b` | 同上 |
| payload SHA-256 | `e65f64e1453b4c397bc35f18180691fffc70022972b43c9ccc0e0e5ce0fd2ea0` | 同上 |
| 本地路径 | `/storage/research/m21-baseos-assessment/firmware/M21-update-1.0.8.zip` | — |
| 解出分区 | `/storage/research/m21-baseos-assessment/firmware/r2-extract/`（本轮新增：`vendor_dlkm`、`vendor`、`odm`、`system_dlkm`、`system`、`xbl`、`xbl_config`、`abl`、`modem`、`dtbo`） | 2026-10-30 |

**来源页**：FiiO 官方固件列表 `https://forum.fiio.com/note/showNoteContent.do?id=202505140958060216556&tid=17`（本机直连超时，OTA 直链可用）。

### 1.1 解析命令（可复现）

```bash
# payload 分区列表
payload-dumper-go -l M21-update-1.0.8.zip

# 按需提取
payload-dumper-go -o r2-extract -p vendor_dlkm,system_dlkm,dtbo M21-update-1.0.8.zip
payload-dumper-go -o r2-extract -p vendor,odm M21-update-1.0.8.zip
payload-dumper-go -o r2-extract -p xbl,xbl_config,abl,modem M21-update-1.0.8.zip
payload-dumper-go -o r2-extract -p system M21-update-1.0.8.zip

# ext4 只读浏览（不挂载）
debugfs -R "ls /lib/modules" vendor_dlkm.img
debugfs -R "cat /lib/modules/modules.load" vendor_dlkm.img

# 内核 config（boot.img 内嵌 IKCFG_ST）
python3 - <<'PY'
d=open('boot.img','rb').read(); k=d[4096:4096+49646080]
s=k.find(b'IKCFG_ST'); import gzip; open('kernel.config','wb').write(gzip.decompress(k[s+8:]))
PY

# DTB 拆分（vendor_boot 的 dtb 是 3 个 DTB 拼接）
python3 - <<'PY'
import struct
d=open('dtb','rb').read(); off=0; n=0
while off < len(d):
    if d[off:off+4] != b'\xd0\x0d\xfe\xed':
        nxt = d.find(b'\xd0\x0d\xfe\xed', off)
        if nxt < 0: break
        off = nxt; continue
    total = struct.unpack('>I', d[off+4:off+8])[0]
    open(f'dtb{n}.dtb','wb').write(d[off:off+total]); n += 1
    off += (total + 3) & ~3
PY

# DTB → DTS
dtc -I dtb -O dts -o dtb0.dts dtb0.dtb    # dtc 1.7.2 (nixpkgs#dtc)

# DTBO 条目提取（用 ocnaibill 项目的只读脚本）
python3 dt_dump.py dtbo.img --list
python3 dt_dump.py dtbo.img --dump 40 > entry40.tree

# 模块元数据
modinfo -F vermagic cs43198.ko
nm -u msm_drm.ko | grep -i fb_helper

# ABL 内嵌证书
openssl x509 -inform DER -in c0.der -noout -subject -issuer -dates
```

### 1.2 本轮新增的 evidence 文件（`docs/m21-round2/evidence/`）

| 文件 | 内容 | 生成方式 |
|---|---|---|
| `dtbo-entry-index.txt` | 42 个 DTBO 条目（id/rev/size/roots） | `dt_dump.py dtbo.img --list` |
| `m21-dtbo-entry40-khajew-idp-nopmi.dts` | entry 40 完整 DTS（4.2 万行） | `dt_dump.py --dump 40` → `dtc` |
| `m21-dtbo-entry12-khajeg-idp-nopmi.dts` | entry 12 完整 DTS | 同上 |
| `kernel-config-5.15.41-android13-8.txt` | 内核 config（6574 行） | boot.img `IKCFG_ST` |
| `vendor-boot-bootconfig.txt` | vendor_boot bootconfig 原文 | `mkbootimg` 解包 |
| `vbmeta-info.txt` | AVB 描述符 | `avbtool info_image` |
| `boot-info.txt` / `init-boot-info.txt` / `vendor-boot-info.txt` | 三个镜像的头部 | `unpack_bootimg` |
| `vendor-dlkm-module-list.txt` | vendor_dlkm 的 226 个 .ko | `debugfs -R "ls /lib/modules"` |
| `vendor-dlkm-modules.load` | 模块加载顺序（259 行） | `debugfs -R "cat ..."` |
| `abl-embedded-certs.txt` | ABL 内嵌 X.509 证书链 | `openssl x509` |
| `xbl-sahara-strings.txt` | xbl 的 Sahara/EDL 字符串 + fastboot 关键词计数 | `strings` + Python |
| `spec-parse.log` | SPEC 解析器两次运行 + 反面用例 | `parse_spec.py` |
| `profile-validate.log` | 用上游 PocketJS 校验器验证导出的 profile | `bun verify-m21.ts` |

---

## 2. 官方文档

| 编号 | URL | 访问日期 | 状态 | 用于 |
|---|---|---|---|---|
| [S1] | `https://www.fiio.com/m21` | 2026-10-30 | 200，已提取正文 | 硬件配置（750×1334、Snapdragon 680、4×CS43198、4000 mAh、64 GB、4 GB RAM、microSD 2 TB、Desktop 模式） |
| [S2] | `https://www.fiio.com/m21_parameters` | 2026-10-30 | 200，已提取正文 | 按键清单、Wi-Fi 2.4/5 GHz、BT 5.0 编解码、采样率上限、充电 1.5 h |
| [S3] | `https://www.fiio.com/newsinfo/1045496.html` | 2026-10-30 | 200，已提取正文 | recovery 进入方式（音量减 + 插 USB）、fastboot 进入方式（电源 + 音量加减）、"Activate rescue mode" |
| [S4] | `https://github.com/FiiOapp/FiiO_Kernel_OpenSource` | 2026-10-30 | GitHub API 元数据：`pushed_at=2017-11-02` | 厂商 kernel 源码不可得 |
| [S5] | `https://fiio-instruction.fiio.net/快速入门/2025/M21.pdf` | 2026-10-30（round1 下载） | 1 page, CorelDRAW, 无文本层 | 只能作图片参考，未提取文字 |
| [S6] | `https://source.android.com/docs/core/architecture/bootloader/locking_unlocking` | 参考（通用） | — | AOSP 解锁语义背景 |

**注意**：`[S3]` 的原文确认 "fastboot mode" 是**设备上的一个菜单**（用音量键选择 "Activate rescue mode"），这与"host 端 fastboot 协议可用"是两件事。本文对 M21 的 fastboot 协议判断**依赖 JM21 的社区实测**（见 §3），不依赖 `[S3]`。

---

## 3. 社区仓库与实测记录（第二轮新增或复核）

| 编号 | 来源 | 类型 | 用于 | 复核结果 |
|---|---|---|---|---|
| [C1] | `https://github.com/ocnaibill/jm21-tree`（本地归档 `archive/fiio/repositories/ocnaibill_jm21-tree/`） | JM21 逆向工程全集（50+ 文档） | `docs/45-plano-b-kernel.md`：`fastboot boot` 自定义内核的原始输出、CRC 对照表、音频实测；`docs/01-hardware.md`：i2cdetect 实测；`docs/07`：风险矩阵 | **本轮首次深入使用**；这是最重要的外部证据 |
| [C2] | `https://github.com/Lannamokia/jm21-orangefox`（本地 `archive/fiio/repositories/jm21-orangefox/`） | OrangeFox device tree | `BoardConfig.mk` 的分区尺寸（注明出自 `fastboot getvar all`）、背光节点 `/sys/class/backlight/panel0-backlight`、电池节点 `/sys/class/power_supply/battery/capacity` | 已核对行号 |
| [C3] | `https://cdn.head-fi.org/a/12820990.txt` | 设备 dump（bootloader 信息 + 模块列表） | `DEVICE STATE = unlocked`、`SECURE BOOT = no` | ⚠ **本轮复核发现该 dump 是 JM21 不是 M21**（模块名 `anolog_board_jm21`/`power_board_jm21`）。见 `storage-risk.md` §7 |
| [C4] | `https://www.reddit.com/r/Magisk/comments/1lr33vn/` | M21 root 讨论 | round1 引用 | ⚠ 2026-10-30 访问返回 403（登录墙 / `api.reddit.com` 亦 403），**无法复核** |
| [C5] | `https://note.com/adotann/n/n50153999ce31`（本地归档 `archive/fiio/community/jm21-modification-note-*.html`） | JM21 优化博客 | "出厂 BLU"、"SE Linux permissive"、"`fastboot boot` 可临时 root"、"GKI·DSU 支持" | 已提取原文（日文） |
| [C6] | `https://github.com/WheresWaldo/FiiOat` | Magisk 调优模块（M21/JM21） | 证明 M21 可 root | 元数据：`"For FiiO M21/JM21"` |
| [C7] | `https://github.com/Masttermind-wwww/Self-defining-button-module-for-FiiO-JM21` | 按键交换模块 | `gpio-keys.kl` 里的 114/115/163/164/165 映射 | 已读 README；与 DT 键码一致 |
| [C8] | `https://www.aliexpress.com/s/wiki-ssr/article/fiio-m21-root` | AI 生成的 wiki | — | **不采信**（页面自带 "generated by AI" 声明） |

---

## 4. 本机只读参考仓库（源码行引用）

### 4.1 `PJOS-LINUX`

| 编号 | 路径 | 用于 |
|---|---|---|
| [P1] | `docs/13-pocketjs-on-baseos.md` | H700 上 `/dev/fb0`、无 `/dev/dri`、DRM→fbdev 回退、`apply-pocketjs-input.py` 的存在 |
| [P2] | `docs/evidence/2026-10-30-baseos-first-boot/README.md` | PocketJS 在 RG34XX 上首启的实测（framebuffer 截帧、`display: fbdev (timer pacing)`） |
| [P3] | `docs/15-bsp-architecture.md` | Device Profile v2 设计、`bsp.json`/`board.json`/`capabilities.json` 字段、`baseosctl` 设计、"现在没有 BSP" 自评 |
| [P4] | `docs/01-rootfs-and-init.md:130-131` | "There is no udev or mdev; devtmpfs provides device nodes" ← **M21 上不成立** |
| [P5] | `docs/00-boot-chain-and-partitions.md` | H700 的 boot0/U-Boot/extlinux/GPT 结构 |
| [P6] | `tools/device_profile.py` | `devices.json` v1 的 10 个必需字段 |
| [P7] | `work/pocketjs-runtime/pocket-linux-kms` | 二进制；`readelf -d` 显示 `NEEDED: libgcc_s.so.1, libm.so.6, libc.so.6`；`readelf -V` 最高 `GLIBC_2.44` |
| [P8] | `overlay/etc/inittab:4` | `::respawn:/sbin/frontend-session`（busybox init 自启动） |
| [P9] | `manifest/harvest.list` | H700 的厂商库白名单（M21 需另开一份） |

### 4.2 `rocknix`

| 编号 | 路径 | 用于 |
|---|---|---|
| [R1] | `projects/ROCKNIX/packages/apps/pocketjs-runtime/profile.ts` | H700 profile：`capabilities: ["input.buttons","text.glyphs.baked"]`（**无** audio） |
| [R2] | `projects/ROCKNIX/packages/apps/pocketjs-runtime/package.mk` | `--target rocknix-h700-kms`、`--features` 未开 alsa |
| [R3] | `build.ROCKNIX-SM8550.aarch64/build/pocketjs-runtime-<sha>/programs/linux-kms/src/main.rs` | CLI（`--card/--fb/--input/--frames/--check/--headless/--pcm-test`）、`INPUT_CLASSES`、`supported()` 的 profile 约束、最多 16 个 evdev 源、`/dev/input` 自动扫描 |
| [R4] | 同上 `platforms/linux/evdev/src/lib.rs` | 768 项按键表、`ABS_MT_SLOT/TRACKING_ID/POSITION_X/Y` 解码、`BTN_TOUCH` 单点回退、16 contacts |
| [R5] | 同上 `platforms/linux/fbdev/src/lib.rs` | `Geometry::validate()` 只接受 16/24/32 bpp、stride/pixel 校验 |
| [R6] | 同上 `contracts/spec/profile.ts` | `pocketProfileSchema`、`PROFILE_CAPABILITY_BITS`、`validatePocketProfile` 的 10-bit 触摸约束 |
| [R7] | 同上 `contracts/spec/platform-types.ts` | `TARGET_FORMS`、`PRESENTATIONS`、`POCKET_CAPABILITIES`（30 项） |
| [R8] | 同上 `platforms/linux/alsa/Cargo.toml` + `programs/linux-kms/Cargo.toml` | `alsa = ["dep:pocket-linux-alsa"]` 是**可选 feature** |
| [R9] | `projects/ROCKNIX/devices/H700/linux/linux.aarch64.conf:2883` | `# CONFIG_INPUT_TOUCHSCREEN is not set`（H700 无触摸） |
| [R10] | `projects/ROCKNIX/devices/SM6115/options:34` + `config.xml:96` | rocknix 的 Qualcomm 目标用 `BOOTLOADER="arm-efi"` + `mkimage_options="abl,bls,dtb"` |
| [R11] | `projects/ROCKNIX/packages/tools/openabl/package.mk:16` | 按 `${DEVICE}` 取 `abl_signed-${DEVICE}.elf` → **无 SM6225 变体** |
| [R12] | `projects/ROCKNIX/packages/rocknix/sources/scripts/installtointernal:10-20` | 白名单 `SM6115|SM8250|SM8550|SM8650|SM8750|SM4450`，**SM6225 会 exit 1** |

### 4.3 `pocket-*` / `pjos-input-framework`

| 编号 | 路径 | 用于 |
|---|---|---|
| [A1] | `pjos-input-framework/README.md:2-4` | "no source that must be merged" |
| [A2] | `PJOS-LINUX/runtime/keyboardd/keyboardd.go:45-50` | `CapTouch/CapDPad/CapGamepad/CapHardwareKeyboard` |
| [A3] | `pjos-input-framework/docs/KNOWN-LIMITS.md:17-18` | "no evdev bridge is included" |
| [A4] | `pocket-music/apps/pocket-music/backend/mpv.go:102` | mpv IPC 启动命令（`--ao=`、`--input-ipc-server=`） |
| [A5] | `pocket-settings/.../settingsd/main.go:26,206` | 7 个 mock profile，含 `M21: {Audio,Bluetooth,Battery,Storage}`（**无 Touchscreen/WiFi**） |
| [A6] | `pocket-galaxy/src/ui/input.ts` | 仓库内唯一的 touch/gesture 抽象（未导出复用） |

---

## 5. 本机环境与工具版本

| 项 | 值 |
|---|---|
| 主机 | HX90（NixOS，x86_64，kernel 6.12.108） |
| Python | 3.13.15（无系统 PyYAML；nixpkgs `python3.13-pyyaml-6.0.3` 通过 `PYTHONPATH` 使用） |
| nix | 2.34.8 |
| `dtc` | 1.7.2（`nix build nixpkgs#dtc`） |
| `payload-dumper-go` | 1.3.0（`nix build nixpkgs#payload-dumper-go`） |
| `kmod`（modinfo） | 31 |
| `lz4` | 1.10.0 |
| `openssl` | 3.6.3 |
| `poppler-utils` | 26.06.0（pdftotext/pdftotext） |
| `bun` | 1.4.2（用于跑 PocketJS 校验器） |
| `debugfs` | e2fsprogs（只读 `-R`，**未挂载任何镜像**） |

**未执行**：任何 `mount`、`mkfs`、`dd`、分区写操作。所有镜像仅用 `debugfs -R` 只读访问。

---

## 6. 明确标注为"推断（未验证）"的结论

以下结论**没有直接来源**，只有间接支撑：

| # | 推断 | 支撑 | 位置 |
|---|---|---|---|
| U1 | M21 使用 DTBO entry 40（`KHAJEW IDP nopmi`） | JM21 的实机 DT 与 entry 40 同构；M21 模块名 `*_m21` 与 `*_jm21` 对应 | kernel.md §3 |
| U2 | M21 触摸控制器是 goodix（而非 focaltech） | goodix 驱动存在、focaltech 驱动缺失、goodix 的 `touchscreen-size` 与面板匹配 | display-touch.md §3.1 |
| U3 | M21 bootloader 可 `fastboot flashing unlock` | ABL 用 QCT test key 签名；同平台 JM21 已解锁 | boot-chain.md §3 |
| U4 | `fastboot boot` 在 M21 上可用 | JM21 已实测；两者 ABL 来源相同 | boot-chain.md §4 |
| U5 | 背光节点是 `/sys/class/backlight/panel0-backlight` | OrangeFox 用此路径，但那是 JM21 的实测 | display-touch.md §2.3 |
| U6 | M21 用 `nt35521z_750p`（非 `_hk` 变体） | 分辨率 750×1334 与该面板匹配；变体差异未知 | display-touch.md §2.2 |
| U7 | Android 密度档是 xhdpi/xxhdpi | 326 dpi 计算值；未见 `ro.sf.lcd_density` | display-touch.md §1 |

这些全部列进了 `SPEC.md` 的 `risks` 与 `verified_on_device`，并有对应的实机验证步骤。
