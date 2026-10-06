# 機能一覧

cf2 構成の機能の一覧。各機能の詳細は、リンク先の文書を参照。

| # | 機能 | 概要 | 主なソース | 動作するタスク / 周期 | 詳細 |
|---|---|---|---|---|---|
| 1 | 起動・システム管理 | 機種判定、各モジュールの初期化と自己テスト、全タスクの一斉スタート、ウォッチドッグ | `init/main.c`, `modules/src/system.c`, `platform/` | SYSTEM（起動時のみ） | [startup.md](../01_runtime/startup.md) |
| 2 | センサ取得 | IMU・気圧計の読み出し、バイアス補正、フィルタ | `hal/src/sensors*.c` | SENSORS / 1 kHz（IMU 割り込み） | [sensors.md](../03_functions/sensors.md) |
| 3 | 状態推定 | 姿勢・位置・速度の推定（Complementary / Kalman） | `modules/src/estimator/`, `kalman_core/` | STABILIZER 内 / KALMAN（予測 100 Hz） | [estimator.md](../03_functions/estimator.md) |
| 4 | 目標値管理（commander） | 複数の入力元の setpoint を優先度つきで保持 | `modules/src/commander.c`, `crtp_commander*.c` | CRTP-RX（受信時） | [setpoint.md](../02_dataflow/setpoint.md) |
| 5 | 自律飛行（high-level commander） | 離陸・着陸・移動・軌道追従の軌道生成 | `crtp_commander_high_level.c`, `planner.c` | CMDHL / 100 Hz | [commander.md](../03_functions/commander.md) |
| 6 | 安全監視（supervisor） | アーム、転倒、setpoint 途絶、緊急停止の状態管理 | `modules/src/supervisor*.c` | STABILIZER 内 / 25 Hz | [supervisor.md](../03_functions/supervisor.md) |
| 7 | 姿勢・位置制御 | PID ほか 5 種類のコントローラ | `modules/src/controller/` | STABILIZER 内 / 500 Hz・100 Hz | [controller.md](../03_functions/controller.md) |
| 8 | 出力分配・モータ制御 | 4 モータへのミキシング、電池補償、PWM 出力 | `power_distribution_quadrotor.c`, `drivers/src/motors.c` | STABILIZER 内 / 1 kHz | [power_distribution.md](../03_functions/power_distribution.md) |
| 9 | 衝突回避 | 他の機体の位置から setpoint を修正（既定は無効） | `collision_avoidance.c` | STABILIZER 内 | [control_loop.md](../02_dataflow/control_loop.md) |
| 10 | 測位 | Flow・Loco・Lighthouse・外部測位の計測値を推定器へ | `deck/drivers/src/`, `modules/src/lighthouse/`, `crtp_localization_service.c` | FLOW / LPS / LH など | [positioning.md](../03_functions/positioning.md) |
| 11 | 通信（CRTP） | 無線・USB・CPX のリンク選択とポートへの振り分け | `modules/src/crtp.c`, `hal/src/radiolink.c`, `usblink.c` | CRTP-RX / CRTP-TX | [communication.md](../02_dataflow/communication.md) |
| 12 | nRF51 連携（syslink） | nRF51 との UART 通信（無線、電源、1-Wire） | `hal/src/syslink.c`, `drivers/src/uart_syslink.c` | SYSLINK | [communication.md](../02_dataflow/communication.md) |
| 13 | param | 設定値の読み書き、EEPROM への永続化 | `param_logic.c`, `param_task.c` | PARAM | [param_log.md](../04_interfaces/param_log.md) |
| 14 | log | 変数の周期送信（ログブロック） | `modules/src/log.c` | LOG / タイマ → WORKER | [param_log.md](../04_interfaces/param_log.md) |
| 15 | メモリアクセス（mem） | PC から EEPROM・軌道・デッキなどのメモリを読み書き | `crtp_mem.c`, `mem.c` | MEM | [storage_mem.md](../03_functions/storage_mem.md) |
| 16 | 永続ストレージ | EEPROM 上の設定ブロックとキーと値のストア | `hal/src/storage.c`, `utils/src/kve/` | 呼び出し元のタスク | [storage_mem.md](../03_functions/storage_mem.md) |
| 17 | 電源管理 | 電池の状態、低電圧の警告（自動電源オフは cf2 では無効） | `hal/src/pm_stm32f4.c` | PWRMGNT / 10 Hz | [power_management.md](../03_functions/power_management.md) |
| 18 | デッキ管理 | デッキの検出、ドライバの照合、資源の競合の検査 | `deck/core/`, `deck/backends/` | SYSTEM（起動時のみ） | [deck_api.md](../04_interfaces/deck_api.md) |
| 19 | コンソール | `DEBUG_PRINT` を PC へ送信 | `modules/src/console.c` | 呼び出し元のタスク | [comm_stack.md](../03_functions/comm_stack.md) |
| 20 | LED・音 | LED のシーケンス、ブザー | `hal/src/ledseq.c`, `sound_cf2.c` | LEDSEQCMD / タイマ | [tasks.md](../01_runtime/tasks.md) |
| 21 | アプリ層 | 外部のアプリの `appMain()` を実行（cf2 では無効） | `app_handler.c`, `app_api/` | APP | [app_api.md](../04_interfaces/app_api.md) |

ソースのパスは `crazyflie-firmware/src/` からの相対パス（`app_api/` はリポジトリのルート直下）。
