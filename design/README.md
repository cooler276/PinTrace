# crazyflie-firmware 機能設計書（リバースエンジニアリング）

- 対象: `crazyflie-firmware` @ `9cf9d86c`（2026-09-24）
- 基準構成: cf2（`configs/cf2_defconfig`）
- 作成方針: [../CLAUDE.md](../CLAUDE.md)

## 構成と進捗

凡例: ⬜ 未着手 / 🟨 作成中 / ✅ 初版完了

| # | ドキュメント | 内容 | 状態 |
|---|---|---|---|
| 00 | [`00_overview/system_context.md`](00_overview/system_context.md) | システムと外部（PC クライアント、無線、デッキ、センサ）の関係 | ✅ |
| 00 | [`00_overview/function_list.md`](00_overview/function_list.md) | 機能一覧（21 機能の概要・ソース・タスク） | ✅ |
| 00 | [`00_overview/layers.md`](00_overview/layers.md) | 階層構造（依存関係にもとづく 6 層の整理） | ✅ |
| 00 | [`00_overview/architecture.md`](00_overview/architecture.md) | レイヤ構成（platform / hal / drivers / modules / deck / utils）と全体ブロック図 | ✅ |
| 01 | [`01_runtime/startup.md`](01_runtime/startup.md) | 起動シーケンス（`main` から `systemTask`、各モジュールの init/test） | ✅ |
| 01 | [`01_runtime/tasks.md`](01_runtime/tasks.md) | FreeRTOS タスクの一覧（優先度、周期、スタック）とタスク間通信（キュー、セマフォ） | ✅ |
| 02 | [`02_dataflow/control_loop.md`](02_dataflow/control_loop.md) | センサ → 状態推定 → 制御 → 出力分配 → モータ の流れ（stabilizer ループ） | ✅ |
| 02 | [`02_dataflow/setpoint.md`](02_dataflow/setpoint.md) | 目標値の経路（CRTP commander / high-level commander / app → commander） | ✅ |
| 02 | [`02_dataflow/io_paths.md`](02_dataflow/io_paths.md) | 入力 → 判断 → 出力の経路の列挙と、判断を通らない経路の点検 | ✅ |
| 02 | [`02_dataflow/communication.md`](02_dataflow/communication.md) | 無線・USB・CPX の受信/送信経路と CRTP ポートの振り分け | ✅ |
| 03 | `03_functions/*.md` | 機能ブロックごとの詳細（下表） | ✅ |
| 04 | [`04_interfaces/crtp_ports.md`](04_interfaces/crtp_ports.md) | CRTP ポートとチャネルの一覧 | ✅ |
| 04 | [`04_interfaces/param_log.md`](04_interfaces/param_log.md) | param/log の仕組みと主要なグループ | ✅ |
| 04 | [`04_interfaces/deck_api.md`](04_interfaces/deck_api.md) | デッキの検出（OneWire / DeckCtrl）とドライバ API | ✅ |
| 04 | [`04_interfaces/app_api.md`](04_interfaces/app_api.md) | アプリ層 API（`app_api/`） | ✅ |
| 05 | [`05_hardware/peripherals.md`](05_hardware/peripherals.md) | MCU ペリフェラルの割り当て（SPI/I2C/UART/TIM/DMA） | ✅ |
| 05 | [`05_hardware/pin_map.md`](05_hardware/pin_map.md) | ピン割り当て（MCU ピン、デッキピン） | ✅ |
| 99 | [`99_appendix/glossary.md`](99_appendix/glossary.md) | 用語集 | ✅ |
| 99 | [`99_appendix/open_issues.md`](99_appendix/open_issues.md) | 全体の未解決事項 | ✅ |

### 03 機能ブロック

| ドキュメント | 主なソース | 状態 |
|---|---|---|
| [`sensors.md`](03_functions/sensors.md) | `src/hal/src/sensors*.c`, `src/drivers/bosch/` | ✅ |
| [`estimator.md`](03_functions/estimator.md) | `src/modules/src/estimator/`, `kalman_core/`, `outlierfilter/` | ✅ |
| [`controller.md`](03_functions/controller.md) | `src/modules/src/controller/` | ✅ |
| [`commander.md`](03_functions/commander.md) | `src/modules/src/commander.c`, `crtp_commander*.c`, `planner.c` | ✅ |
| [`power_distribution.md`](03_functions/power_distribution.md) | `src/modules/src/power_distribution*.c`, `src/drivers/src/motors.c` | ✅ |
| [`supervisor.md`](03_functions/supervisor.md) | `src/modules/src/supervisor*.c` | ✅ |
| [`positioning.md`](03_functions/positioning.md) | `lighthouse/`, `src/deck/drivers/src/lps*.c`, `src/utils/src/tdoa/` | ✅ |
| [`comm_stack.md`](03_functions/comm_stack.md) | `crtp.c`, `radiolink.c`, `usblink.c`, `syslink.c`, `cpx/` | ✅ |
| [`storage_mem.md`](03_functions/storage_mem.md) | `storage.c`, `mem.c`, `src/utils/src/kve/` | ✅ |
| [`power_management.md`](03_functions/power_management.md) | `pm_stm32f4.c`, `syslink` 経由の nRF51 連携 | ✅ |
| [`decks.md`](03_functions/decks.md) | `src/deck/` | ✅ |

## ドキュメントの雛形
[_template.md](_template.md)
