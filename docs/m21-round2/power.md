# ⑥ 电源：电池、充电、suspend、RTC

调查日期：2026-10-30。无实机。DT 证据见 `evidence/m21-dtbo-entry40-khajew-idp-nopmi.dts`。

---

## 1. 结论先行

| 问题 | 结论 | 置信度 |
|---|---|---|
| 电池节点 | **`/sys/class/power_supply/battery/`**（由 `fiio_charge_manager` 聚合，`fcm-name="battery"`） | 高（DT + OrangeFox 注释） |
| 电量计 IC | **CW221X**（`cellwise,cw221X`，i2c-1 0x64），驱动 `cw221X_fuel_gauge.ko` 在 `vendor_dlkm` | 高 |
| 充电 IC | **SGM41510**（`sgm,sgm41510`，i2c-1 0x6B），驱动 `sgm41510_charger.ko` | 高 |
| PD/Type-C | **FUSB302**（i2c-0 0x22）+ **AW35615**（i2c-1 0x22，PD 协商） | 高 |
| 充电参数 | 满充判定 4.345 V / 128 mA、8 段温度窗口（15/25/45/50/60 °C）、`fcm-poll-interval=5000 ms` | 高 |
| suspend | `CONFIG_SUSPEND=y`、`CONFIG_PM_SLEEP=y`；`fiio_wakeup.ko` 有 suspend/resume 钩子；按键全部 `gpio-key,wakeup` | 高 |
| RTC | **PM6125 RTC**（`compatible="qcom,pm8941-rtc"`），驱动 `rtc-pm8xxx.ko` 在 `vendor_dlkm`；`CONFIG_RTC_HCTOSYS=y` | 高 |
| 双 Type-C | 规格页：`Type-C USB3.0*1`（数据+充电）+ `Type-C POWER IN*1`（独立供电） | 高（规格） |
| Desktop 模式 | `power_board` 的 `dc_bat_sw`/`pd_vbus_sw`/`otg_sel`/`otg_en` GPIO 实现"直供旁路" | 高（DT）/中（行为） |

**一句话**：电源子系统**比 H700 更标准**——有独立的电量计、充电 IC、PD 控制器、PMIC RTC，且 FiiO 用 `fiio_charge_manager` 把状态统一到 `/sys/class/power_supply/battery/`。BaseOS 侧只需读这一个目录。

---

## 2. 硬件拓扑

```
USB-C #1 (数据+充电) ──► FUSB302 (i2c-0 0x22, Type-C CC)
                       └► AW35615 (i2c-1 0x22, PD)
USB-C #2 (POWER IN) ──► PD 协商 ──► sgm41510 充电
                                        │
                                        ▼
                                  电池（4000 mAh, 规格页）
                                        │
                        CW221X 电量计 (i2c-1 0x64) ──► fiio_charge_manager
                                        │
                                        ▼
                          /sys/class/power_supply/battery/
                             capacity, status, voltage_now, current_now, temp
```

`power_board` 的 5 个 GPIO 控制供电路径切换：

```
gpio,dc_bat_sw   = 19    ← DC（桌面）与电池之间切换
gpio,battery_id  = 67    ← 电池识别（原装/非原装）
gpio,otg_sel     = 84    ← OTG 输出选择
gpio,pd_vbus_sw  = 106   ← PD VBUS 切换
gpio,otg_en      = 110   ← OTG 使能
```

**这就是"Desktop 模式"的硬件基础**：外接电源时切到 DC 直供，绕过电池（规格页宣传 "Patented desktop mode / Battery protection expert" [S1]）。

---

## 3. `fiio_charge_manager`：DT 里的完整充电策略

（DT 原始十六进制与换算值并列，便于复核。）

```
fcm-name             = "battery"
fcm-poll-interval    = 5000 ms     (0x1388)
fcm-poll-mode        = 1
fcm-battery-stat     = 2
fcm-chargers         = "sgm41510-charger"
fcm-fuel-gauge       = "cw221X-bat"
fcm-num-chargers     = 1

# 满充判定
fcm-fullbatt-voltage       = 4,345,000 uV  = 4.345 V   (0x424ca8)
fcm-fullbatt-current       = 128,000 uA                (0x1f400)
fcm-fullbatt-capacity      = 100 %                     (0x64)
fcm-fullbatt-vchkdrop-ms   = 30,000 ms                 (0x7530)
fcm-fullbatt-vchkdrop-volt = 100,000 uV                (0x186a0)

# 温度窗口（单位 0.1 °C）
low-extreme = 20.0 (0xc8)   low-stop = 0.0 (0x00)
low-cold    = 15.0 (0x96)   low-cool = 25.0 (0xfa)
normal      = 45.0 (0x1c2)  hight-limit = 50.0 (0x1f4)  hight-stop = 60.0 (0x258)
temp-diff = 5  temp-thrd = 5

# 各温度段的电流上限（uA，FDT 原始 uint32 解析）
cold-current    =   800,000 uA = 800 mA   (0x000c3500)
cool-current    = 2,000,000 uA = 2000 mA  (0x001e8480)
normal-current  = 3,648,000 uA = 3648 mA  (0x0037aa00)
warm-current    =   800,000 uA = 800 mA   (0x000c3500)
hot-current     = 0 uA                    (0x00000000)
unknown-current = 3,648,000 uA = 3648 mA  (0x0037aa00)
fast-current    = 3,648,000 uA = 3648 mA  (0x0037aa00)
fcm-battery-temp-compensation-enable = true
fcm-fix-request-voltage-gear = 9
```

**这是 FiiO 的自研策略**（不是 Qualcomm 的 `qcom,qpnp-smb5`）。`fiio-charger-manager.ko`（661,552 B）实现它。对 BaseOS 的含义：**充电行为由内核驱动自动管理，用户态不需要干预**——只要驱动加载了，插电就充。

---

## 4. 电池上报路径（关键证据）

OrangeFox 的 `BoardConfig.mk` 有一段直接说明（`jm21-orangefox/device/fiio/jm21/BoardConfig.mk`）：

```
# Read the battery percentage straight from /sys/class/power_supply/battery/
# capacity. Without this TWRP uses the health HAL, which is shipped "disabled"
# and never started in this ramdisk, so the background battery monitor blocks
# forever on android.hardware.health@2.0::IHealth/default and no percentage is
# ever shown. The sysfs node is present and valid on this device.
```

两个结论：

1. **`/sys/class/power_supply/battery/capacity` 存在且有效**（在无 HAL 的环境下也能读）；
2. **Android 的 health HAL 在本机是 "disabled" 状态** → BaseOS 不依赖 HAL，直接 sysfs 即可。

这是整个评估里少见的"**BaseOS 侧比 Android 侧更简单**"的例子。

---

## 5. suspend / resume

| 组件 | 状态 | 证据 |
|---|---|---|
| `CONFIG_SUSPEND=y` | ✅ | kernel config |
| `CONFIG_PM_SLEEP=y` / `PM_SLEEP_SMP=y` | ✅ | 同上 |
| `CONFIG_HIBERNATION=y` | ✅（Android 一般关，这里开着） | 同上 |
| `CONFIG_PM_AUTOSLEEP` | ❌ 未设 | 同上 |
| `CONFIG_CPU_IDLE` + `ARM_CPUIDLE` + governor menu/TEO | ✅ | 同上 |
| `qcom_lpm.ko`（Low Power Modes） | ✅ | `vendor_dlkm` |
| `smp2p_sleepstate.ko` | ✅ | 同上 |
| `soc_sleep_stats.ko` | ✅ | 同上 |
| `fiio_wakeup.ko` | ✅ 有 `fiio_wakeup_module_suspend/resume`、`active_wakeup_store`、`screen_off_suspend_counter` | 模块字符串 |
| 按键唤醒 | ✅ 6 个 gpio-key 全有 `gpio-key,wakeup` | DT |
| 触摸唤醒 | ✅ `goodix,slide-wakeup=1` | DT |
| 面板 LP11 | ✅ `qcom,mdss-dsi-lp11-init` | DT |

`fiio_wakeup.ko` 的字符串揭示 FiiO 的自定义语义：

```
active wakeup counter = %d
data->screen_off_suspend_counter %d
fiio_wakeup_stay_lock / fiio_wakeup_relax_lock
```

→ 这是**wake lock 计数**：屏幕关掉后如果还有音频在播，阻止进入深度 suspend。对 Music Player 场景**非常重要**（息屏继续放歌）。BaseOS 侧要复现这个行为需要读/写该 sysfs。

**风险**：Android 的 suspend 依赖 `wakeup_sources` 与 `autosleep`。BaseOS（busybox init，无 systemd-logind）需要自己调 `echo mem > /sys/power/state`，且要处理"息屏放歌时不 suspend"的逻辑——**这正是 `fiio_wakeup` 提供的**，但要先搞清楚它的 sysfs 接口（待实机）。

---

## 6. RTC

```
DT:  qcom,pm6125_rtc { compatible = "qcom,pm8941-rtc"; interrupts = <0 0x61 1 0>; }
驱动: rtc-pm8xxx.ko（vendor_dlkm）
内核: CONFIG_RTC_CLASS=y, CONFIG_RTC_HCTOSYS=y, HCTOSYS_DEVICE="rtc0"
      CONFIG_RTC_SYSTOHC=y
```

→ 开机自动从 `rtc0` 设置系统时间（`hctosys`），关机时 `hwclock -w` 写回。BaseOS 的 `hwclock -u -s`（PJOS 已有此步骤）可以直接用。

**无独立 RTC 电池的说明**：PMIC RTC 通常靠主电池维持，换电池会丢时间。M21 不可拆电池（推断），影响小。

---

## 7. ⚠ 重大发现：内核**没有 devtmpfs**

```
# CONFIG_DEVTMPFS is not set
# CONFIG_UEVENT_HELPER is not set
```

Android 的 `/dev` 由 **ueventd**（userspace）根据 `/sys` 的 uevent 逐个 `mknod` 创建，因此内核里关掉了 devtmpfs。

**这对 BaseOS 是硬约束**：

| 方案 | 做法 | 评价 |
|---|---|---|
| A. initramfs 自带静态设备节点 | 预置 `/dev/{console,null,zero,full,random,urandom,tty,pts,fb,dri,input,snd,...}`，`mknod` 硬编码 major/minor | 脆弱：`/dev/dri/card0`、`/dev/input/eventN`、`/dev/snd/pcmC0D0p` 的次设备号**运行期才知道** |
| B. 用 `mdev` | busybox `mdev -s` 扫 `/sys` 建节点 | **可行**（`CONFIG_SYSFS=y`，mdev 只依赖 sysfs） |
| C. 自写 ueventd 简化版 | 读 `/sys/class/*/*/dev`，`mknod` | 可行，约 100 行 |
| D. 自编内核加 `CONFIG_DEVTMPFS=y` | Plan-B 路线（需自定义内核） | 最干净，但引入内核风险 |

**推荐 B**（busybox `mdev`）：零代码、只依赖 sysfs、在 initramfs 里一行 `mdev -s` 即可。PJOS-LINUX 当前**依赖 devtmpfs**（`docs/01-rootfs-and-init.md:130-131` 明确写 "There is no udev or mdev; devtmpfs provides device nodes"）——**这条假设在 M21 上不成立**，是本轮发现的第二个"PJOS 现有实现直接失效"的点（第一个是 fbdev）。

---

## 8. 与 H700 的电源对比

| 项 | H700 / RG34XX | M21 |
|---|---|---|
| PMIC | AXP2202 | PM6125 + PM7250B + 独立 SGM41510/CW221X |
| 电池节点 | `/sys/class/power_supply/axp2202-battery/` | `/sys/class/power_supply/battery/` |
| 电量计 | AXP2202 内置 | **独立 CW221X**（更准） |
| 充电策略 | AXP2202 内置 | FiiO 自研 `fiio_charge_manager`（8 档温度窗口） |
| 震动 | `axp2202-battery/moto` sysfs | `leds-qpnp-vibrator-ldo.ko`（推断，未在 DT 见 vibrator 节点） |
| suspend 阻止 | 无 | `fiio_wakeup` 的 wake lock 计数 |
| RTC | 外部 `pcf8563`（i2c 5-0051） | **PMIC 内置**（更简单） |
| devtmpfs | ✅ 有 | ❌ **没有**（见 §7） |
| Desktop 直供 | 无 | ✅ 有（专利功能） |

---

## 9. 待实机验证

| # | 命令 | 期望 | 用途 |
|---|---|---|---|
| P1 | `adb shell ls /sys/class/power_supply/` | `battery`（可能还有 `usb`、`dc`、`pc_port`） | 确认节点名 |
| P2 | `adb shell cat /sys/class/power_supply/battery/{capacity,status,voltage_now,current_now,temp,health}` | 有效值 | 确认可用字段 |
| P3 | `adb shell ls /sys/power/` + `cat /sys/power/state` | `freeze mem disk` | 确认 suspend 模式 |
| P4 | `adb shell cat /sys/power/wakeup_count` + `cat /sys/power/wake_lock` | 内容 | 确认 wake lock 机制 |
| P5 | `adb shell ls /sys/devices/platform/soc/soc:fiio_attr/` | FiiO 私有属性（可能有 wakeup/charge 项） | 拿 `fiio_wakeup` 接口 |
| P6 | `adb shell ls -l /dev/rtc*` + `hwclock -r` | `rtc0` 可读 | 确认 RTC |
| P7 | `adb shell dmesg \| grep -iE 'fiio_wakeup\|wakeup_source'` | 驱动日志 | 确认 wake lock 行为 |
| P8 | 息屏放歌 10 分钟，看 `dmesg` 是否有 suspend 尝试 | 无 suspend 或快速 resume | 验证 §5 的假设 |
