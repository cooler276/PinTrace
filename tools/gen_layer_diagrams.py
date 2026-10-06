"""Generate the layered block diagrams for design/00_overview/layers.md.

One definition of layers / nodes / edges below produces three Graphviz files
(and their SVGs) in design/00_overview/:

  layers_call.dot       call / dependency edges only
  layers_dataflow.dot   data-flow edges only (what data reaches whom)
  layers_combined.dot   both in one picture

Layout is always top (L5) to bottom (L0). Call edges drive the layout;
upward calls are drawn with dir=back. Data edges never drive the layout
(constraint=false), so both diagrams keep the same node placement.

Usage: python tools/gen_layer_diagrams.py [--png DIR]   (PNG copies for review)
"""
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "design" / "00_overview"
DOT = r"C:\Program Files\Graphviz\bin\dot.exe"
FONT = "Yu Gothic UI"

# (id, label, fill, border), top to bottom
LAYERS = [
    ("L5", "L5 アプリケーション層", "#fdeef7", "#d49ac0"),
    ("L4", "L4 デッキ層", "#eaf7f2", "#8cc7ae"),
    ("L3", "L3 基盤サービス層", "#fff4e6", "#e0b27a"),
    ("L2", "L2 ハード抽象化層", "#e9f6fb", "#86bfd6"),
    ("L1D", "L1 ドライバ層（デバイスドライバ）", "#edf7e9", "#99c98a"),
    ("L1B", "L1 ドライバ層（バスドライバ）", "#e3f1dc", "#86b877"),
    ("L0", "L0 プラットフォーム・OS 層", "#f1efff", "#aaa1dd"),
    ("HW", "HW ハードウェア", "#f2f2f2", "#9a9a9a"),
]

# layer -> rows (each row is one rank) of (node id, label)
NODES = {
    "L5": [
        [("APP", "アプリ層\n(cf2 では無効)"), ("HLC", "high-level commander\n+ planner"),
         ("LLC", "低レベル commander"), ("LOC", "測位\nlighthouse / localization"),
         ("STAB", "スタビライザ\n1 kHz ループ")],
        [("CMD", "commander\n(優先度管理)"), ("EST", "状態推定"), ("SUP", "supervisor"),
         ("CA", "衝突回避"), ("CTRL", "制御"), ("PD", "出力分配")],
    ],
    "L4": [[("DMGR", "デッキ管理\n検出・照合"), ("DDRV", "デッキドライバ\nFlow / Loco / LH ..."),
            ("DAPI", "デッキ API\nGPIO / SPI / ADC")]],
    # peer_localization.c only stores up to 10 neighbours' positions (no decision, no task),
    # so it is a shared data table in the service layer, not an application
    "L3": [[("SYS", "system\n起動・自己テスト"), ("CRTP", "CRTP ルータ\n+ console"), ("PL", "param / log"),
            ("MEM", "mem"), ("PEER", "周辺機体の位置テーブル\npeer localization"), ("WRK", "worker"),
            ("UTL", "共通部品\nutils")]],
    "L2": [[("SENS", "センサ統合"), ("LINK", "CRTP リンク\nradiolink / usblink"), ("SLK", "syslink"),
            ("PM", "電源管理"), ("STO", "ストレージ"), ("LEDS", "LED / ブザー")]],
    # device drivers: interpret the registers of one chip
    "L1D": [[("DEV_IMU", "IMU ドライバ\nbmi088 / bmp3"), ("DEV_EEP", "EEPROM ドライバ\neeprom / configblock"),
             ("DEV_MOT", "モータドライバ\nmotors")]],
    # bus drivers: move bytes over one bus (one node per bus instance: same code, separate data)
    "L1B": [[("I2C3DRV", "I2C3 ドライバ\ni2cdev / i2c_drv"), ("I2C1DRV", "I2C1 ドライバ\ni2cdev / i2c_drv"),
             ("UART", "uart_syslink\n(USART6)"), ("EXTI", "exti\n割り込みの振り分け"), ("WDG", "watchdog")]],
    "L0": [[("PLAT", "platform\n機種差分"), ("RTOS", "FreeRTOS"), ("LIB", "ベンダライブラリ\nStdPeriph / USB / CMSIS")]],
    "HW": [
        # inside the MCU
        [("P_USART6", "USART6 + DMA"), ("P_USB", "USB OTG FS"), ("P_I2C1", "I2C1 + DMA"), ("P_SPI1", "SPI1 + DMA"),
         ("P_I2C3", "I2C3 + DMA"), ("P_EXTI", "EXTI"), ("P_TIM", "TIM2 / TIM4\nPWM")],
        # outside the MCU
        [("X_NRF", "nRF51"), ("X_EEP", "EEPROM チップ\n24AA64F"), ("X_DECK", "デッキ"),
         ("X_IMU", "BMI088 / BMP388"), ("X_MOT", "ブラシモータ ×4")],
    ],
}
EMPHASIS = {"STAB": "#ffe3f1"}

# Call / dependency edges: (caller, callee, label, kind)
#   kind "down": normal (upper calls lower or same layer)
#   kind "up":   lower-layer code calls upper-layer code (layer violation)
CALLS = [
    ("APP", "HLC", "", "down"),
    ("HLC", "CMD", "", "down"),
    ("LLC", "CMD", "", "down"),
    ("STAB", "CMD", "", "down"),
    ("STAB", "HLC", "GetSetpoint", "down"),      # stabilizer.c:335
    ("STAB", "EST", "", "down"),
    ("STAB", "SUP", "", "down"),
    ("STAB", "CA", "", "down"),
    ("STAB", "CTRL", "", "down"),
    ("STAB", "PD", "", "down"),
    ("CA", "PEER", "", "down"),                  # collision_avoidance.c:323
    ("LOC", "PEER", "", "down"),                 # crtp_localization_service.c:251, :366
    ("LOC", "EST", "", "down"),                  # estimatorEnqueuePosition/Pose
    ("STAB", "SENS", "", "down"),
    ("PD", "DEV_MOT", "", "down"),               # motorsSetRatio: stabilizer.c:221-227
    ("PD", "PM", "", "down"),
    ("DMGR", "DDRV", "init", "down"),
    ("DDRV", "DAPI", "", "down"),
    ("DAPI", "LIB", "SPI1 を直接操作", "down"),  # deck_spi.c drives SPI1 itself
    ("DMGR", "SLK", "1-Wire", "down"),
    ("DMGR", "I2C1DRV", "DeckCtrl", "down"),     # deck_backend_deckctrl.c:117
    ("DDRV", "EST", "estimatorEnqueue", "up"),   # e.g. flowdeck_v1v2.c:158
    ("SYS", "STAB", "stabilizerInit", "up"),     # system.c:210
    ("SYS", "DMGR", "deckInit", "up"),           # system.c:208
    ("CRTP", "LLC", "port 3 / 7 CB", "up"),      # crtp_commander.c:47-48
    ("CRTP", "LOC", "port 6 CB", "up"),          # crtp_localization_service.c:171
    ("CRTP", "LINK", "", "down"),
    ("PL", "WRK", "", "down"),
    ("PL", "STO", "", "down"),
    ("SENS", "DEV_IMU", "", "down"),             # bmi088_get_gyro_data: sensors_bmi088_bmp3xx.c:241
    ("SENS", "EST", "estimatorEnqueue", "up"),   # sensors_bmi088_bmp3xx.c:334-363
    ("LINK", "SLK", "", "down"),
    ("PM", "SLK", "", "down"),
    ("SLK", "UART", "", "down"),
    ("STO", "DEV_EEP", "", "down"),              # storage.c:67-98 -> eepromRead/WriteBuffer
    ("DEV_IMU", "I2C3DRV", "", "down"),          # bus adapter bmi088_burst_read -> i2cdevReadReg8(I2C3_DEV)
    ("DEV_EEP", "I2C1DRV", "", "down"),          # eeprom.c: i2cdev on I2C1
    ("EXTI", "SENS", "EXTI14_Callback", "up"),   # exti.c:181 -> sensors.c:226
    ("I2C3DRV", "LIB", "", "down"),
    ("I2C1DRV", "LIB", "", "down"),
    ("UART", "LIB", "", "down"),
    ("DEV_MOT", "LIB", "", "down"),
    ("EXTI", "LIB", "", "down"),
    ("WDG", "LIB", "", "down"),
    ("SYS", "WDG", "watchdogInit", "down"),      # system.c:347
    ("LINK", "LIB", "USB スタック", "down"),       # usb.c uses STM32_USB_OTG_Driver
    ("WRK", "RTOS", "全タスクが使用", "down"),
    ("SYS", "PLAT", "", "down"),
    # register access: the vendor library programs the peripherals
    ("LIB", "P_USART6", "", "down"),
    ("LIB", "P_USB", "", "down"),
    ("LIB", "P_I2C1", "", "down"),
    ("LIB", "P_SPI1", "", "down"),
    ("LIB", "P_I2C3", "", "down"),
    ("LIB", "P_EXTI", "", "down"),
    ("LIB", "P_TIM", "", "down"),
]

# Physical wiring between MCU peripherals and external devices (drawn as plain lines)
WIRES = [
    ("P_USART6", "X_NRF", "UART"),
    ("P_I2C1", "X_EEP", "I2C"),
    ("P_I2C1", "X_DECK", "I2C"),
    ("P_SPI1", "X_DECK", "SPI"),
    ("P_I2C3", "X_IMU", "I2C"),
    ("P_EXTI", "X_IMU", "INT"),
    ("P_TIM", "X_MOT", "PWM"),
]

# Data-flow edges: (from, to, data)
# Audited 2026-09-28: every edge below was checked against the source that the
# receiving side actually READS the data (not just receives it as an argument).
DATA = [
    # sensing: chip -> I2C3 -> bus driver -> device driver -> HAL
    ("X_IMU", "P_I2C3", "I2C 信号"),
    ("P_I2C3", "I2C3DRV", "DMA 転送"),         # DMA1 Stream2: i2c_drv.c:145, :203
    ("I2C3DRV", "DEV_IMU", "レジスタ値"),       # i2cdevReadReg8 -> bmi088_burst_read: sensors_bmi088_bmp3xx.c:190-193
    ("DEV_IMU", "SENS", "生データ"),            # bmi088_get_gyro/accel_data: sensors_bmi088_bmp3xx.c:241-246
    ("X_IMU", "P_EXTI", "data ready (INT)"),    # PC14: sensors_bmi088_bmp3xx.c:581-589
    ("P_EXTI", "EXTI", "割り込み"),
    ("EXTI", "SENS", "IMU 割り込み"),            # exti.c:181 -> sensors.c:226
    ("SENS", "EST", "gyro / acc / baro"),       # sensors_bmi088_bmp3xx.c:334-363
    ("SENS", "SUP", "acc"),                     # tumble check uses data->acc: supervisor.c:311-321
    # NOTE: collisionAvoidanceUpdateSetpoint() receives sensorData but never reads it
    #       (collision_avoidance.c:97-253), so there is no SENS -> CA edge.
    ("SENS", "CTRL", "gyro"),                   # controller_pid.c:142
    ("DDRV", "EST", "flow / 距離 / TDoA"),
    ("LOC", "EST", "位置 / 姿勢 / sweep"),
    # state
    ("EST", "CMD", "state"),                    # commander.c:108 (lastState, handed to HL on relax)
    ("EST", "HLC", "state"),                    # trajectory start point: crtp_commander_high_level.c:359-362
    ("EST", "CA", "state"),                     # collision_avoidance.c:117
    ("EST", "CTRL", "state"),                   # stabilizer.c:356
    ("SUP", "EST", "飛行中フラグ"),              # estimator_kalman.c:236
    # setpoint chain (stabilizer.c:332-356)
    ("CRTP", "LLC", "port 3 / 7"),
    ("CRTP", "HLC", "port 8"),
    ("LLC", "CMD", "setpoint"),
    ("HLC", "CMD", "setpoint"),
    ("CMD", "SUP", "setpoint (監視)"),
    ("CMD", "CA", "setpoint"),
    ("CA", "SUP", "修正 setpoint"),
    ("SUP", "CTRL", "最終 setpoint"),
    ("SUP", "LLC", "受付停止"),                  # crtpCommanderBlock, stabilizer.c:333
    # other drones
    ("CRTP", "LOC", "port 6"),
    ("LOC", "PEER", "他の機体の位置"),
    ("PEER", "CA", "他の機体の位置"),
    # actuation
    ("CTRL", "PD", "control"),
    ("PM", "PD", "電池電圧"),
    ("PD", "DEV_MOT", "PWM 比率"),              # motorsSetRatio: stabilizer.c:221-227
    ("SUP", "DEV_MOT", "停止"),                  # motorsStop: stabilizer.c:360-367
    ("DEV_MOT", "P_TIM", "比較レジスタ"),        # setCompare: motors.c:748-753
    ("P_TIM", "X_MOT", "PWM 信号"),
    # decks (SPI decks; I2C decks share I2C1 and are left out to avoid mixing with EEPROM data)
    ("X_DECK", "P_SPI1", "SPI 信号"),
    ("P_SPI1", "DAPI", "DMA 転送"),             # DMA2 Stream0: deck_spi.c:57
    ("DAPI", "DDRV", "デッキのデータ"),          # spiExchange, e.g. pmw3901
    # communication / services
    ("X_NRF", "P_USART6", "UART 信号"),
    ("P_USART6", "UART", "受信割り込み"),         # USART6_IRQHandler: uart_syslink.c:634-637
    ("UART", "SLK", "syslink"),
    ("P_USB", "LINK", "CRTP (USB)"),             # usb.c:645
    ("SLK", "LINK", "CRTP"),
    ("SLK", "PM", "電池の状態"),
    ("SLK", "DMGR", "1-Wire"),
    ("LINK", "CRTP", "CRTP"),
    ("CRTP", "PL", "port 2 / 5"),
    ("CRTP", "MEM", "port 4"),
    ("X_EEP", "P_I2C1", "I2C 信号"),
    ("P_I2C1", "I2C1DRV", "DMA 転送"),          # DMA1 Stream0: i2c_drv.c:180
    ("I2C1DRV", "DEV_EEP", "バイト列"),
    ("DEV_EEP", "STO", "保存値"),                # storage.c:67-73
    ("STO", "PL", "永続 param"),
]

CALL_COLOR, UP_COLOR, DATA_COLOR = "#666666", "#c05050", "#2f6fb3"


def header(title):
    return [
        f"// {title}",
        "// 生成元: tools/gen_layer_diagrams.py（このファイルは直接編集しない）",
        "digraph layers {",
        f'  graph [rankdir=TB, newrank=true, compound=true, nodesep=0.25, ranksep=0.6, '
        f'fontname="{FONT}", fontsize=12, labeljust=l, splines=spline];',
        f'  node [shape=box, style="rounded,filled", fillcolor=white, fontname="{FONT}", fontsize=10, height=0.4];',
        f'  edge [fontname="{FONT}", fontsize=8, arrowsize=0.6];',
    ]


def clusters():
    out = []
    for lid, label, fill, border in LAYERS:
        out.append(f'  subgraph cluster_{lid} {{')
        out.append(f'    label="{label}"; style="rounded,filled"; fillcolor="{fill}"; color="{border}";')
        for row in NODES[lid]:
            for nid, text in row:
                extra = f', fillcolor="{EMPHASIS[nid]}", penwidth=1.5' if nid in EMPHASIS else ""
                out.append(f'    {nid} [label="{text}"{extra}];')
            out.append("    { rank=same; " + " ".join(n for n, _ in row) + "; }")
        out.append("  }")
    return out


def skeleton():
    """Invisible edges that pin the vertical order of all ranks."""
    ranks = [row[0][0] for lid, *_ in LAYERS for row in NODES[lid]]
    return ["  " + " -> ".join(ranks) + " [style=invis, weight=10];"]


def call_edges(faint=False):
    out = []
    for a, b, label, kind in CALLS:
        lab = f', label="{label}"' if label else ""
        if kind == "up":
            color = UP_COLOR
            # layout from upper node (b) to lower node (a); arrowhead points at b
            out.append(f'  {b} -> {a} [dir=back, style="dashed,bold", color="{color}", fontcolor="{color}"{lab}];')
        else:
            color = "#aaaaaa" if faint else CALL_COLOR
            out.append(f'  {a} -> {b} [color="{color}", fontcolor="{color}"{lab}];')
    return out


def wire_edges():
    """Physical wiring (not a call, not software data flow)."""
    return [f'  {a} -> {b} [dir=none, style=dotted, penwidth=1.4, color="#8a8a8a", fontcolor="#8a8a8a", '
            f'label="{t}"];' for a, b, t in WIRES]


def layout_only_call_edges():
    """Call edges as invisible layout hints (so every diagram has the same layout)."""
    out = []
    for a, b, _, kind in CALLS:
        s, t = (b, a) if kind == "up" else (a, b)
        out.append(f"  {s} -> {t} [style=invis];")
    return out


def data_edges(labels=True, skip=()):
    out = []
    for a, b, d in DATA:
        if (a, b) in skip:
            continue
        lab = f', label="{d}"' if labels else ""
        out.append(f'  {a} -> {b} [color="{DATA_COLOR}", fontcolor="{DATA_COLOR}", penwidth=1.6, '
                   f'constraint=false{lab}];')
    return out


def combined_edges():
    """Call edges (grey) + data edges (blue). A call and a data flow between the
    same two nodes in the same direction are merged into one blue solid edge."""
    data_pairs = {(a, b) for a, b, _ in DATA}
    out, merged = [], set()
    for a, b, label, kind in CALLS:
        if (a, b) in data_pairs:
            merged.add((a, b))
            if kind == "up":
                out.append(f'  {b} -> {a} [dir=back, color="{DATA_COLOR}", penwidth=1.8, style=bold];')
            else:
                out.append(f'  {a} -> {b} [color="{DATA_COLOR}", penwidth=1.8];')
        elif kind == "up":
            out.append(f'  {b} -> {a} [dir=back, style="dashed,bold", color="{UP_COLOR}"];')
        else:
            out.append(f'  {a} -> {b} [color="#b0b0b0"];')
    return out + data_edges(labels=False, skip=merged)


def layer_of(nid):
    for lid, *_ in LAYERS:
        if any(nid == n for row in NODES[lid] for n, _ in row):
            return lid
    raise KeyError(nid)


def write_dataflow(name):
    """Data-flow only, laid out left to right. Layer is shown by fill colour."""
    fill = {lid: f for lid, _, f, _ in LAYERS}
    border = {lid: b for lid, _, _, b in LAYERS}
    labels = {n: t for lid in NODES for row in NODES[lid] for n, t in row}
    used = sorted({n for a, b, _ in DATA for n in (a, b)}, key=lambda n: [l for l, *_ in LAYERS].index(layer_of(n)))
    lines = [
        "// データフロー（層の配置ではなく、データの流れの向きに配置）",
        "// 生成元: tools/gen_layer_diagrams.py（このファイルは直接編集しない）",
        "digraph dataflow {",
        f'  graph [rankdir=LR, nodesep=0.3, ranksep=0.7, fontname="{FONT}", fontsize=12, splines=spline];',
        f'  node [shape=box, style="rounded,filled", fontname="{FONT}", fontsize=10, height=0.4];',
        f'  edge [fontname="{FONT}", fontsize=8, arrowsize=0.6, color="{DATA_COLOR}", fontcolor="{DATA_COLOR}"];',
    ]
    for n in used:
        lid = layer_of(n)
        pen = ", penwidth=1.5" if n in EMPHASIS else ""
        lines.append(f'  {n} [label="{lid}: {labels[n]}", fillcolor="{fill[lid]}", color="{border[lid]}"{pen}];')
    for a, b, d in DATA:
        lines.append(f'  {a} -> {b} [label="{d}"];')
    # legend
    lines.append('  subgraph cluster_legend { label="層の色"; fontsize=10; color="#cccccc";')
    for lid, label, f, b in LAYERS:
        lines.append(f'    leg_{lid} [label="{label}", fillcolor="{f}", color="{b}", fontsize=9];')
    lines.append("    " + " -> ".join(f"leg_{l}" for l, *_ in LAYERS) + " [style=invis];")
    lines.append("  }")
    lines.append("}")
    path = OUT / f"{name}.dot"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    subprocess.run([DOT, "-Tsvg", str(path), "-o", str(path.with_suffix(".svg"))], check=True)
    return path


# Hand-placed positions (inches) for the layered data-flow view.
# Inputs rise on the left, decisions run left -> right in L5, outputs fall on the right.
POS_DATAFLOW = {
    # L5: top row = setpoint sources, middle row = control chain, lower = estimation / localization
    "LLC": (2.4, 9.7), "HLC": (4.8, 9.7), "CMD": (7.4, 9.7),
    "CA": (7.4, 8.5), "SUP": (9.6, 8.5), "CTRL": (11.8, 8.5), "PD": (13.8, 8.5),
    "EST": (3.6, 7.4), "LOC": (6.0, 7.0),
    # L4
    "DMGR": (0.6, 5.7), "DDRV": (8.0, 5.7), "DAPI": (9.8, 5.7),
    # L3
    "CRTP": (2.0, 4.3), "PL": (3.9, 4.3), "MEM": (5.6, 4.3), "PEER": (7.4, 4.3),
    # L2
    "SLK": (0.6, 2.8), "LINK": (2.2, 2.8), "STO": (3.9, 2.8), "SENS": (6.6, 2.8), "PM": (11.4, 2.8),
    # L1 device drivers
    "DEV_EEP": (3.9, 1.3), "DEV_IMU": (6.6, 1.3), "DEV_MOT": (13.8, 1.3),
    # L1 bus drivers
    "UART": (0.6, -0.2), "I2C1DRV": (3.9, -0.2), "I2C3DRV": (6.6, -0.2), "EXTI": (8.4, -0.2),
    # HW: inside the MCU
    "P_USART6": (0.6, -2.9), "P_USB": (2.2, -2.9), "P_I2C1": (3.9, -2.9), "P_I2C3": (6.6, -2.9),
    "P_EXTI": (8.4, -2.9), "P_SPI1": (9.8, -2.9), "P_TIM": (13.8, -2.9),
    # HW: outside the MCU
    "X_NRF": (0.6, -4.1), "X_EEP": (3.9, -4.1), "X_IMU": (7.5, -4.1), "X_DECK": (9.8, -4.1), "X_MOT": (13.8, -4.1),
}
# y range (inches, same coordinates as POS_DATAFLOW) of each layer band in that view
BANDS = {"L5": (6.55, 10.2), "L4": (5.1, 6.35), "L3": (3.7, 4.9), "L2": (2.2, 3.4),
         "L1D": (0.7, 1.9), "L1B": (-0.8, 0.4), "L0": (-2.0, -1.0), "HW": (-4.75, -2.35)}
# note placed in the L0 band of the layered data-flow view (no data passes through L0)
L0_NOTE = ("L0 のベンダライブラリ（StdPeriph）はペリフェラルの設定・起動だけを行う。"
           "データは DMA がペリフェラルからメモリへ直接転送するので、この図の矢印は L0 を素通りする")


# Colour of each kind of flow in the layered data-flow view
FLOW_KINDS = {
    "sense":    ("#2f6fb3", "計測値・推定状態"),
    "setpoint": ("#d9822b", "目標値（setpoint）"),
    "actuate":  ("#3f9a4a", "出力（制御 → モータ）"),
    "safety":   ("#c03a3a", "安全（停止・受付停止）"),
    "service":  ("#8a8a8a", "通信・記憶・サービス"),
}


def flow_kind(a, b, d):
    if (a, b) in {("SUP", "DEV_MOT"), ("SUP", "LLC"), ("SUP", "EST")}:
        return "safety"
    if (a, b) in {("CTRL", "PD"), ("PD", "DEV_MOT"), ("PM", "PD"), ("DEV_MOT", "P_TIM"), ("P_TIM", "X_MOT")}:
        return "actuate"
    if (a, b) in {("CRTP", "LLC"), ("CRTP", "HLC"), ("LLC", "CMD"), ("HLC", "CMD"), ("CMD", "SUP"),
                  ("CMD", "CA"), ("CA", "SUP"), ("SUP", "CTRL")}:
        return "setpoint"
    if a in {"X_IMU", "P_I2C3", "I2C3DRV", "DEV_IMU", "P_EXTI", "EXTI", "SENS",
             "X_DECK", "P_SPI1", "DAPI", "DDRV", "EST"} or (a, b) in {("LOC", "EST"), ("PEER", "CA")}:
        return "sense"
    return "service"


def write_dataflow_layered(name):
    """Data flow on the layer layout, drawn with fixed positions (neato)."""
    labels = {n: t for lid in NODES for row in NODES[lid] for n, t in row}
    fill = {lid: f for lid, _, f, _ in LAYERS}
    border = {lid: b for lid, _, _, b in LAYERS}
    missing = {n for a, b, _ in DATA for n in (a, b)} - set(POS_DATAFLOW)
    assert not missing, f"no position for {missing}"
    L = ["// データフロー（層の配置を保った版、座標は POS_DATAFLOW）",
         "// 生成元: tools/gen_layer_diagrams.py（このファイルは直接編集しない）",
         "digraph dataflow_layered {",
         # sep/esep: smaller node margins, otherwise neato gives up routing around nodes
         f'  graph [splines=true, sep="+2", esep="+1", outputorder=edgesfirst, fontname="{FONT}", pad=0.3];',
         f'  node [shape=box, style="rounded,filled", fontname="{FONT}", fontsize=10, height=0.45, width=1.3, fixedsize=false];',
         f'  edge [fontname="{FONT}", fontsize=8, arrowsize=0.6, color="{DATA_COLOR}", fontcolor="#3b5f8a", penwidth=1.3];']
    for n, (x, y) in POS_DATAFLOW.items():
        lid = next(l for l in NODES if any(n == m for row in NODES[l] for m, _ in row))
        L.append(f'  {n} [label="{labels[n]}", pos="{x},{y}!", fillcolor=white, color="{border[lid]}", penwidth=1.4];')
    for a, b, d in DATA:
        color, _ = FLOW_KINDS[flow_kind(a, b, d)]
        width = 2.0 if flow_kind(a, b, d) in ("setpoint", "actuate", "safety") else 1.3
        L.append(f'  {a} -> {b} [label="{d}", color="{color}", fontcolor="{color}", penwidth={width}];')
    # note in the L0 band, placed between the vertical columns
    L.append(f'  l0note [shape=plaintext, style="", fontsize=8, fontcolor="#6b64a8", width=4.4, '
             f'label="{L0_NOTE[:38]}\\n{L0_NOTE[38:]}", pos="11.4,-1.5!"];')
    # legend: one row below the HW band, clear of every edge
    ly = BANDS["HW"][0] - 0.5
    for i, (kind, (color, text)) in enumerate(FLOW_KINDS.items()):
        x = 0.4 + i * 2.9
        L.append(f'  leg_a{i} [shape=point, width=0.01, pos="{x},{ly}!", color=white];')
        L.append(f'  leg_b{i} [shape=plaintext, label="{text}", fontsize=9, fontcolor="{color}", '
                 f'style="", width=1.6, pos="{x + 1.45},{ly}!"];')
        L.append(f'  leg_a{i} -> leg_b{i} [color="{color}", penwidth=2, arrowsize=0.5];')
    L.append("}")
    path = OUT / f"{name}.dot"
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
    neato = DOT.replace("dot.exe", "neato.exe")
    # neato shifts all coordinates on output; measure the shift from the laid-out positions
    import json
    laid = json.loads(subprocess.run([neato, "-Tjson", str(path)], check=True, capture_output=True).stdout)
    ref = next(o for o in laid["objects"] if o.get("name") in POS_DATAFLOW)
    px, py = map(float, ref["pos"].split(","))
    dx, dy = px - POS_DATAFLOW[ref["name"]][0] * 72, py - POS_DATAFLOW[ref["name"]][1] * 72
    svg = subprocess.run([neato, "-Tsvg", str(path)], check=True, capture_output=True).stdout.decode("utf-8")
    svg = add_bands(svg, fill, border, dx, dy)
    path.with_suffix(".svg").write_text(svg, encoding="utf-8")
    return path


def add_bands(svg, fill, border, dx, dy):
    """Insert layer bands (rectangles + labels) behind the drawing.
    (dx, dy): shift in points between POS_DATAFLOW*72 and neato's output coordinates."""
    import re
    first = re.search(r"<polygon fill=\"white\"[^>]*>", svg)  # graph background
    xs = [x for x, _ in POS_DATAFLOW.values()]
    left, right = (min(xs) - 0.95) * 72 + dx, (max(xs) + 0.95) * 72 + dx
    names = {lid: label for lid, label, *_ in LAYERS}
    parts = []
    for lid, (y0, y1) in BANDS.items():
        top, h = -(y1 * 72 + dy), (y1 - y0) * 72
        parts.append(f'<rect x="{left:.1f}" y="{top:.1f}" width="{right - left:.1f}" height="{h:.1f}" rx="8" '
                     f'fill="{fill[lid]}" stroke="{border[lid]}" stroke-width="1"/>')
        parts.append(f'<text x="{left + 6:.1f}" y="{top + 13:.1f}" font-family="{FONT}" font-size="11" '
                     f'fill="#555">{names[lid]}</text>')
    return svg[:first.end()] + "\n" + "\n".join(parts) + svg[first.end():]


def write(name, title, body):
    path = OUT / f"{name}.dot"
    path.write_text("\n".join(header(title) + clusters() + body + skeleton() + ["}"]) + "\n", encoding="utf-8")
    subprocess.run([DOT, "-Tsvg", str(path), "-o", str(path.with_suffix(".svg"))], check=True)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png", help="also write PNG copies into this directory")
    a = ap.parse_args()
    paths = [
        write("layers_call", "呼び出し・依存", call_edges() + wire_edges()),
        write_dataflow("layers_dataflow"),
        write("layers_combined", "呼び出し・依存 + データフロー", combined_edges() + wire_edges()),
    ]
    lay = write_dataflow_layered("layers_dataflow_layered")
    print(lay.relative_to(ROOT), "+ .svg")
    if a.png:
        svg = lay.with_suffix(".svg")
        # render the post-processed SVG (with bands) to PNG for review
        subprocess.run([DOT.replace("dot.exe", "neato.exe"), "-Kneato", "-Tpng", "-Gdpi=100", str(lay), "-o",
                        str(Path(a.png) / "layers_dataflow_layered_nobands.png")], check=True)
        (Path(a.png) / "layers_dataflow_layered.svg").write_text(svg.read_text(encoding="utf-8"), encoding="utf-8")
    for p in paths:
        print(p.relative_to(ROOT), "+ .svg")
        if a.png:
            subprocess.run([DOT, "-Tpng", "-Gdpi=100", str(p), "-o", str(Path(a.png) / f"{p.stem}.png")], check=True)


if __name__ == "__main__":
    main()
