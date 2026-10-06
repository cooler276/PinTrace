"""Input -> decision -> output path analysis (sense / decide / act).

Builds a data-flow graph from tools/gen_layer_diagrams.py (DATA) plus the
extra edges below (explicit input sources, output sinks, param writes, time),
then for every source x sink pair:
  * finds the shortest path and the decision blocks (L5 nodes) on it
  * checks whether a path exists that avoids every L5 node
and, for the motor output, lists every way the final edge can be reached,
separating edges gated by the supervisor from ungated ones.

Outputs
  design/02_dataflow/io_paths.md      (section below the AUTO-GENERATED marker)
  design/02_dataflow/io_paths.dot/.svg

Usage: python tools/io_paths.py [--png DIR]
"""
import argparse
import collections
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_layer_diagrams as g  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "design" / "02_dataflow"
DOC = OUT_DIR / "io_paths.md"
MARKER = "<!-- AUTO-GENERATED BELOW: python tools/io_paths.py -->"

# ---- explicit endpoints -------------------------------------------------------
SOURCES = {  # id: (label, kind)
    "S_IMU":  ("IMU・気圧計\nBMI088 / BMP388", "センサ"),
    "S_DECK": ("デッキのセンサ", "センサ"),
    "S_EEP":  ("EEPROM（読み出し）", "記憶"),
    "S_NRF":  ("nRF51 からの受信\n無線・電池・ボタン・1-Wire", "通信"),
    "S_USB":  ("USB からの受信", "通信"),
    "S_TIME": ("時間\n(tick・タイマ)", "時間"),
}
SINKS = {
    "K_MOT":  ("モータ", "アクチュエータ"),
    "K_LED":  ("LED・ブザー", "表示"),
    "K_EEP":  ("EEPROM（書き込み）", "記憶"),
    "K_NRF":  ("nRF51 への送信\nテレメトリ・シャットダウン応答", "通信"),
    "K_USB":  ("USB への送信", "通信"),
}

# DATA's external hardware nodes become explicit endpoints in this analysis
RENAME = {"X_IMU": "S_IMU", "X_DECK": "S_DECK", "X_NRF": "S_NRF", "X_EEP": "S_EEP", "P_USB": "S_USB",
          "X_MOT": "K_MOT"}
# the point where the supervisor gates the motor output (motor driver)
MOTOR_IN = "DEV_MOT"

# Bidirectional blocks are split by direction, otherwise the graph contains
# paths that do not exist (e.g. a packet sent to syslink coming back as received).
SPLIT_NODES = {  # id: (label, base layer node)
    "SLK_RX":  ("syslink（受信）", "SLK"),
    "SLK_TX":  ("syslink（送信）", "SLK"),
    "LINK_RX": ("CRTP リンク（受信）", "LINK"),
    "LINK_TX": ("CRTP リンク（送信）", "LINK"),
    "CRTP_RX": ("CRTP ルータ（受信）", "CRTP"),
    "CRTP_TX": ("CRTP ルータ（送信）", "CRTP"),
    "PARAM":   ("param（実行時の書き込み）", "PL"),
    "PBOOT":   ("param（起動時の永続値の復元）", "PL"),
    "LOG":     ("log", "PL"),
}
# DATA edges rewritten with the split nodes: (a, b) -> list of (a', b', data)
DATA_SPLIT = {
    ("UART", "SLK"): [("UART", "SLK_RX", "syslink")],
    ("S_USB", "LINK"): [("S_USB", "LINK_RX", "CRTP (USB)")],
    ("SLK", "LINK"): [("SLK_RX", "LINK_RX", "CRTP")],
    ("SLK", "PM"): [("SLK_RX", "PM", "電池の状態")],
    ("SLK", "DMGR"): [("SLK_RX", "DMGR", "1-Wire")],
    ("LINK", "CRTP"): [("LINK_RX", "CRTP_RX", "CRTP")],
    ("CRTP", "LLC"): [("CRTP_RX", "LLC", "port 3 / 7")],
    ("CRTP", "HLC"): [("CRTP_RX", "HLC", "port 8")],
    ("CRTP", "LOC"): [("CRTP_RX", "LOC", "port 6")],
    ("CRTP", "MEM"): [("CRTP_RX", "MEM", "port 4")],
    ("CRTP", "PL"): [("CRTP_RX", "PARAM", "port 2"), ("CRTP_RX", "LOG", "port 5 (設定)")],
    ("STO", "PL"): [("STO", "PBOOT", "永続 param")],
}

# ---- extra data edges (from, to, data, evidence) ------------------------------
EXTRA = [
    # inputs (the SPI path of the decks is in DATA; I2C decks share I2C1 with the EEPROM,
    # so they are drawn directly to keep EEPROM data and deck data apart)
    ("S_DECK", "DDRV", "I2C (ToF など)", "zranger2.c, multiranger.c"),
    ("DEV_EEP", "SENS", "較正角 (configblock)", "sensors_bmi088_bmp3xx.c:550"),
    ("DEV_EEP", "SLK_TX", "無線の設定 (nRF51 へ)", "radiolink.c:101-103"),
    ("S_TIME", "SUP", "経過時間 (タイムアウト)", "supervisor.c:594"),
    ("S_TIME", "PM", "無操作時間", "pm_stm32f4.c:496"),
    ("S_TIME", "LOG", "log の周期", "log.c:377"),
    ("S_TIME", "HLC", "軌道の時刻", "crtp_commander_high_level.c:351 (usecTimestamp)"),
    ("S_TIME", "CA", "他の機体の位置の鮮度 (5 秒)", "collision_avoidance.c:315-331"),
    # param writes at run time (param_logic.c: WRITE_CH / SETBYNAME)
    ("PARAM", "CTRL", "ゲイン", "pid_rate.* など"),
    ("PARAM", "EST", "kalman.*", "estimator_kalman.c:533"),
    ("PARAM", "SUP", "stabilizer.stop など", "supervisor.c:699"),
    ("PARAM", "CA", "colAv.enable", "collision_avoidance.c:398"),
    ("PARAM", "PD", "idleThrust", "power_distribution_quadrotor.c:216"),
    ("PARAM", "LLC", "flightmode.*", "crtp_commander_rpyt.c:239"),
    ("PARAM", "PM", "電圧しきい値", "pm_stm32f4.c:563"),
    ("PARAM", "DEV_MOT", "motorPowerSet", "motors.c:702-738"),
    # param restored at boot: only PARAM_PERSISTENT ones (motorPowerSet is not persistent)
    ("PBOOT", "CTRL", "ゲイン (永続)", "controller の PARAM_PERSISTENT"),
    ("PBOOT", "EST", "kalman.* (永続)", "estimator_kalman.c:549-617"),
    ("PBOOT", "SUP", "supervisor.* (永続)", "supervisor.c:745-766"),
    ("PBOOT", "PD", "idleThrust (永続)", "power_distribution_quadrotor.c:216"),
    ("PBOOT", "PM", "電圧しきい値 (永続)", "pm_stm32f4.c:567-571"),
    # log reads module variables
    ("SENS", "LOG", "acc / gyro / baro", "stabilizer.c:617-708"),
    ("EST", "LOG", "stateEstimate", "stabilizer.c:732"),
    ("CTRL", "LOG", "controller", "controller_pid.c"),
    ("PD", "LOG", "motor", "stabilizer.c:891"),
    ("SUP", "LOG", "supervisor", "supervisor.c:707"),
    ("PM", "LOG", "pm", "pm_stm32f4.c:511"),
    ("LOC", "LOG", "lighthouse / locSrv", "lighthouse_core.c:648"),
    # outputs: communication
    ("LOG", "CRTP_TX", "log データ", "log.c:559"),
    ("PARAM", "CRTP_TX", "param の応答", "param_logic.c"),
    ("MEM", "CRTP_TX", "メモリの読み出し", "crtp_mem.c"),
    ("CRTP_TX", "LINK_TX", "送信パケット", "crtp.c:143-168"),
    ("LINK_TX", "SLK_TX", "RADIO_RAW", "radiolink.c:234-251"),
    ("LINK_TX", "K_USB", "送信パケット", "usb.c:816"),
    ("SLK_TX", "K_NRF", "syslink", "syslink.c:143-165"),
    # auto shutdown (pmSystemShutdown) is compiled out in cf2 (CONFIG_PM_AUTO_SHUTDOWN not set);
    # what remains is the ACK to a shutdown request from the nRF51
    ("PM", "SLK_TX", "シャットダウン応答 (ACK)", "pm_stm32f4.c:pmGracefulShutdown"),
    # outputs: storage
    ("PARAM", "STO", "param の永続化", "param_logic.c:716"),
    ("LOC", "STO", "Lighthouse の較正・位置", "lighthouse_storage.c:65-76"),
    ("STO", "K_EEP", "書き込み", "storage.c:92-98"),
    # outputs: LED / sound
    ("PM", "K_LED", "充電・低電圧", "pm_stm32f4.c:446-463"),
    ("LINK_RX", "K_LED", "通信表示", "radiolink.c:177"),
    ("SENS", "K_LED", "較正完了", "sensors_bmi088_bmp3xx.c:757"),
    ("SYS", "K_LED", "自己テスト結果", "system.c:301-311"),
    ("CRTP_RX", "K_LED", "ユーザ通知 (port 13)", "platformservice.c:223"),
]

# edges whose data only passes when the gate node allows it
GATES = {
    ("PD", "DEV_MOT"): ("SUP", "supervisorAreMotorsAllowedToRun()", "stabilizer.c:360-367"),
    ("LLC", "CMD"): ("SUP", "crtpCommanderBlock(!canFly)", "stabilizer.c:333"),
    ("HLC", "CMD"): ("SUP", "canFly && ...", "stabilizer.c:335"),
}
# edges that can only stop / reduce the output, never drive it
STOP_ONLY = {("SUP", "DEV_MOT")}


def build():
    edges = []
    for a, b, d in g.DATA:
        a, b = RENAME.get(a, a), RENAME.get(b, b)
        for a2, b2, d2 in DATA_SPLIT.get((a, b), [(a, b, d)]):
            edges.append((a2, b2, d2, "図 B"))
    edges += EXTRA
    split_left = {n for a, b, *_ in edges for n in (a, b)} & {"SLK", "LINK", "CRTP", "PL"}
    assert not split_left, f"unsplit bidirectional nodes remain: {split_left}"
    labels = {n: t for lid in g.NODES for row in g.NODES[lid] for n, t in row}
    labels.update({k: v[0] for k, v in {**SOURCES, **SINKS}.items()})
    labels.update({k: v[0] for k, v in SPLIT_NODES.items()})
    layer = {n: lid for lid in g.NODES for row in g.NODES[lid] for n, _ in row}
    layer.update({k: layer[v[1]] for k, v in SPLIT_NODES.items()})
    adj = collections.defaultdict(list)
    for a, b, *_ in edges:
        adj[a].append(b)
    return edges, adj, labels, layer


# Interrupt lines only trigger a read; when showing an example path, prefer the
# path that carries the data (I2C) and fall back to the trigger path.
TRIGGER_NODES = frozenset({"P_EXTI", "EXTI"})


def shortest(adj, s, t, banned=frozenset()):
    return (_bfs(adj, s, t, banned | TRIGGER_NODES) if s not in TRIGGER_NODES else None) \
        or _bfs(adj, s, t, banned)


def _bfs(adj, s, t, banned=frozenset()):
    prev, q, seen = {}, collections.deque([s]), {s}
    while q:
        u = q.popleft()
        if u == t:
            path = [t]
            while path[-1] != s:
                path.append(prev[path[-1]])
            return path[::-1]
        for v in adj[u]:
            if v not in seen and v not in banned:
                seen.add(v)
                prev[v] = u
                q.append(v)
    return None


def fmt(path, labels):
    return " → ".join(labels[n].split("\n")[0] for n in path)


def analyse():
    edges, adj, labels, layer = build()
    l5 = frozenset(n for n, lid in layer.items() if lid == "L5")
    md = []

    # ---- matrix ----
    md.append("### 入力源 × 出力先\n")
    md.append("各セルは、最短経路で通る判断ブロック（L5）。`—` は経路なし。"
              "**⚠** は L5 を 1 つも通らずに届く経路があることを示す。\n")
    md.append("| 入力源 \\ 出力先 | " + " | ".join(SINKS[k][0].split("\n")[0] for k in SINKS) + " |")
    md.append("|---|" + "---|" * len(SINKS))
    bypass = []
    for s in SOURCES:
        cells = []
        for t in SINKS:
            p = shortest(adj, s, t)
            if not p:
                cells.append("—")
                continue
            dec = [labels[n].split("\n")[0] for n in p if n in l5]
            q = shortest(adj, s, t, banned=l5)
            mark = "⚠ " if q else ""
            if q:
                bypass.append((s, t, q))
            cells.append(mark + (", ".join(dec) if dec else "（直接）"))
        md.append(f"| {SOURCES[s][0].split(chr(10))[0]} | " + " | ".join(cells) + " |")
    md.append("")

    # ---- bypass list ----
    md.append("### 判断ブロック（L5）を通らない経路\n")
    md.append("分類: **要確認（安全）** = アクチュエータに届く、**確認（永続化）** = EEPROM への書き込みに届く、"
              "通常 = テレメトリ・表示・応答など、判断を通らないのが自然なもの。\n")
    md.append("| 分類 | 入力源 | 出力先 | 経路（例） |")
    md.append("|---|---|---|---|")

    def severity(t, q):
        if t == "K_MOT":
            return 0, "**要確認（安全）**"
        if t == "K_EEP":
            return 1, "**確認（永続化）**"
        return 2, "通常"

    for (_, sev), s, t, q in sorted(((severity(t, q), s, t, q) for s, t, q in bypass), key=lambda x: x[0][0]):
        md.append(f"| {sev} | {SOURCES[s][0].splitlines()[0]} | {SINKS[t][0].splitlines()[0]} | {fmt(q, labels)} |")
    md.append("")

    # ---- motor ----
    md.append("### モータに届く経路\n")
    tail = shortest(adj, MOTOR_IN, "K_MOT")
    md.append(f"モータドライバ（`{MOTOR_IN}`、supervisor のゲートがかかる地点）に入る矢印ごとに、supervisor による制御の有無と、"
              f"各入力源からの最短経路を示す。モータドライバから先は、全ての経路で共通（{fmt(tail, labels)}）。\n")
    md.append("| モータドライバへの矢印 | supervisor による制御 | 入力源ごとの最短経路 |")
    md.append("|---|---|---|")
    for a, b, d, ev in edges:
        if b != MOTOR_IN:
            continue
        if (a, b) in STOP_ONLY:
            gate = "（停止の指示そのもの）"
        elif (a, b) in GATES:
            n, how, where = GATES[(a, b)]
            gate = f"あり: `{how}`（`{where}`）"
        else:
            gate = "**なし**"
        rows = []
        for s in SOURCES:
            p = shortest(adj, s, a)
            if p:
                rows.append(f"{SOURCES[s][0].splitlines()[0]}: {fmt(p + [MOTOR_IN], labels)}")
        md.append(f"| {labels[a].splitlines()[0]} → モータドライバ（{d}） | {gate} | " + "<br/>".join(rows) + " |")
    md.append("")

    # ---- edge list ----
    md.append("### 分析に使った矢印\n")
    md.append(f"図 B（`tools/gen_layer_diagrams.py` の `DATA`）の {len(g.DATA)} 本を、双方向のブロック"
              f"（syslink、CRTP リンク、CRTP ルータ、param / log）を向きごとに分けて書き直し、"
              f"入出力・param・log・時間の {len(EXTRA)} 本を加えた {len(edges)} 本。追加分は次のとおり。\n")
    md.append("| 元 | 先 | データ | 根拠 |")
    md.append("|---|---|---|---|")
    for a, b, d, ev in EXTRA:
        md.append(f"| {labels[a].splitlines()[0]} | {labels[b].splitlines()[0]} | {d} | `{ev}` |")
    md.append("")
    return "\n".join(md), edges, labels, layer, bypass


def write_dot(edges, labels, layer, bypass, png_dir=None):
    fill = {lid: f for lid, _, f, _ in g.LAYERS}
    bypass_edges = {(p[i], p[i + 1]) for _, t, p in bypass if t == "K_MOT" for i in range(len(p) - 1)}
    L = ["// 入力 → 判断 → 出力（生成元: tools/io_paths.py）", "digraph io {",
         f'  graph [rankdir=LR, nodesep=0.25, ranksep=0.8, fontname="{g.FONT}", splines=spline];',
         f'  node [shape=box, style="rounded,filled", fontname="{g.FONT}", fontsize=10, height=0.4];',
         f'  edge [fontname="{g.FONT}", fontsize=8, arrowsize=0.6, color="#7a9cc6"];',
         '  subgraph cluster_in { label="入力源"; color="#999999"; style=dashed; rank=source;']
    for s, (lab, kind) in SOURCES.items():
        L.append(f'    {s} [label="{lab}\\n［{kind}］", fillcolor="#fff7cc", shape=box];')
    L.append("  }")
    L.append('  subgraph cluster_out { label="出力先"; color="#999999"; style=dashed; rank=sink;')
    for k, (lab, kind) in SINKS.items():
        L.append(f'    {k} [label="{lab}\\n［{kind}］", fillcolor="#e6f4d7"];')
    L.append("  }")
    used = {n for a, b, *_ in edges for n in (a, b)} - set(SOURCES) - set(SINKS)
    for n in sorted(used):
        L.append(f'  {n} [label="{layer[n]}: {labels[n]}", fillcolor="{fill[layer[n]]}"];')
    for a, b, d, _ in edges:
        attr = [f'label="{d}"']
        if (a, b) in GATES:
            attr += ['color="#2f6fb3"', "penwidth=1.6", f'label="{d}\\n(supervisor が許可)"']
        if (a, b) in STOP_ONLY:
            attr += ['color="#2f6fb3"', "style=dashed"]
        if (a, b) in bypass_edges:
            attr += ['color="#c05050"', 'fontcolor="#c05050"', "penwidth=2"]
        L.append(f"  {a} -> {b} [{', '.join(attr)}];")
    L.append("}")
    dot = OUT_DIR / "io_paths.dot"
    dot.write_text("\n".join(L) + "\n", encoding="utf-8")
    subprocess.run([g.DOT, "-Tsvg", str(dot), "-o", str(dot.with_suffix(".svg"))], check=True)
    if png_dir:
        subprocess.run([g.DOT, "-Tpng", "-Gdpi=90", str(dot), "-o", str(Path(png_dir) / "io_paths.png")], check=True)


def write_motor_dot(edges, labels, layer, png_dir=None):
    """Only the shortest paths from every source to every edge entering the motor."""
    _, adj, _, _ = build()
    fill = {lid: f for lid, _, f, _ in g.LAYERS}
    data = {(a, b): d for a, b, d, _ in edges}
    keep, bypass_edges = set(), set()
    tail = shortest(adj, MOTOR_IN, "K_MOT")
    for a, b, d, _ in edges:
        if b != MOTOR_IN:
            continue
        for s in SOURCES:
            p = shortest(adj, s, a)
            if p:
                path = p + tail
                pairs = {(path[i], path[i + 1]) for i in range(len(path) - 1)}
                keep |= pairs
                if (a, b) not in GATES and (a, b) not in STOP_ONLY:
                    # colour only up to the motor driver; the tail after it is shared by every path
                    head = p + [MOTOR_IN]
                    bypass_edges |= {(head[i], head[i + 1]) for i in range(len(head) - 1)}
    nodes = {n for e in keep for n in e}
    L = ["// モータに届く経路（生成元: tools/io_paths.py）", "digraph motor {",
         f'  graph [rankdir=LR, nodesep=0.3, ranksep=0.6, fontname="{g.FONT}", splines=spline];',
         f'  node [shape=box, style="rounded,filled", fontname="{g.FONT}", fontsize=10, height=0.4];',
         f'  edge [fontname="{g.FONT}", fontsize=8, arrowsize=0.6, color="#7a9cc6", fontcolor="#557"];']
    L.append("  { rank=source; " + " ".join(s for s in SOURCES if s in nodes) + "; }")
    for n in sorted(nodes):
        if n in SOURCES:
            L.append(f'  {n} [label="{SOURCES[n][0]}\\n［{SOURCES[n][1]}］", fillcolor="#fff7cc"];')
        elif n in SINKS:
            L.append(f'  {n} [label="{SINKS[n][0]}", fillcolor="#e6f4d7", penwidth=2];')
        else:
            L.append(f'  {n} [label="{layer[n]}: {labels[n]}", fillcolor="{fill[layer[n]]}"];')
    for a, b in sorted(keep):
        attr = [f'label="{data[(a, b)]}"']
        if (a, b) in GATES:
            attr += ['color="#2f6fb3"', "penwidth=2", f'label="{data[(a, b)]}\\n(supervisor が許可したときだけ)"']
        if (a, b) in STOP_ONLY:
            attr += ['color="#2f6fb3"', "style=dashed", "penwidth=1.6"]
        if (a, b) in bypass_edges:
            attr += ['color="#c05050"', 'fontcolor="#c05050"', "penwidth=2.2"]
        L.append(f"  {a} -> {b} [{', '.join(attr)}];")
    L.append("}")
    dot = OUT_DIR / "io_motor.dot"
    dot.write_text("\n".join(L) + "\n", encoding="utf-8")
    subprocess.run([g.DOT, "-Tsvg", str(dot), "-o", str(dot.with_suffix(".svg"))], check=True)
    if png_dir:
        subprocess.run([g.DOT, "-Tpng", "-Gdpi=100", str(dot), "-o", str(Path(png_dir) / "io_motor.png")], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--png")
    a = ap.parse_args()
    body, edges, labels, layer, bypass = analyse()
    head = DOC.read_text(encoding="utf-8").split(MARKER)[0] if DOC.exists() else "# 入出力の経路\n\n"
    DOC.write_text(head.rstrip() + "\n\n" + MARKER + "\n\n" + body, encoding="utf-8")
    write_dot(edges, labels, layer, bypass, a.png)
    write_motor_dot(edges, labels, layer, a.png)
    print(f"{len(edges)} edges, {len(bypass)} bypass pairs -> {DOC.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
