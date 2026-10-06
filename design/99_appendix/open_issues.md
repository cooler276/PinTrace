# 未解決事項と設計上の注目点

本書は、各文書の「未解決事項」を集約したものである。後半は `python tools/collect_open_issues.py` で自動生成しているので、直接編集しない（各文書の側を直してから再生成する）。

## 解析で見つかった設計上の注目点

ソースを読む中で見つかった、安全性や信頼性に関わる挙動。いずれも静的解析による指摘で、実機では確認していない。

| # | 内容 | 影響 | 詳細 |
|---|---|---|---|
| 1 | param `motorPowerSet.enable` による上書きは `motorsStop()` の中でも効き、supervisor のモータ停止より優先される | PC から param 1 つで、ロック状態でもモータを回せる | [power_distribution.md](../03_functions/power_distribution.md) |
| 2 | デッキ同士で資源（GPIO、UART など）が競合するか、要求する推定器が食い違うと、**全デッキ**が初期化されない | デッキの組み合わせによっては、測位などが丸ごと無効になる | [deck_api.md](../04_interfaces/deck_api.md) |
| 3 | CRTP の受信ポートのキューが満杯になると、`CRTP-RX` タスクがブロックする | たとえば param の処理が詰まると、setpoint の受信も止まる | [tasks.md](../01_runtime/tasks.md) |
| 4 | 無線の送信は、nRF51 からパケットを受信したときに 1 個だけ返す方式 | PC がポーリングを止めると、log などの下りの送信も止まる | [communication.md](../02_dataflow/communication.md) |
| 5 | syslink の送信の排他がミューテックスではなくバイナリセマフォ | 優先度逆転が起こりうる | [tasks.md](../01_runtime/tasks.md) |
| 6 | 低レベルの setpoint を 1 回でも受けると、high-level commander が停止し、明示的に優先度を戻すまで無視される | 操縦の切り替え時の挙動に注意が必要 | [setpoint.md](../02_dataflow/setpoint.md) |
| 7 | 推定器の計測値キュー（長さ 20）は、満杯になると待たずに捨てる | Kalman が数 ms 止まると IMU の値が失われる（推測） | [estimator.md](../03_functions/estimator.md) |
| 8 | 機体を静止させないとジャイロの較正が終わらず、制御ループが始まらない | 起動時の操作手順に影響 | [startup.md](../01_runtime/startup.md) |
| 9 | 永続ストレージの `flush` が何もしない | 電源断時のデータ破損のリスク（未評価） | [storage_mem.md](../03_functions/storage_mem.md) |
| 10 | ソースのコメントと値の不一致（電池電圧のフィルタ係数） | 保守性 | [control_loop.md](../02_dataflow/control_loop.md) |

## 公式ドキュメントとの主な差異

| 内容 | 詳細 |
|---|---|
| コントローラは公式では 3 種類、ソースでは 5 種類（+ Out-of-tree） | [architecture.md](../00_overview/architecture.md) |
| 推定器は公式では 2 種類、ソースでは 3 種類（+ Out-of-tree） | 同上 |
| スタビライザの流れの図に、supervisor による setpoint の置き換えと衝突回避がない | [control_loop.md](../02_dataflow/control_loop.md) |

<!-- AUTO-GENERATED BELOW: python tools/collect_open_issues.py -->

## 文書ごとの未解決事項（72 件）

### [アーキテクチャ概要](../00_overview/architecture.md)

- `platformInit()` で機種の文字列がどのテーブル項目にも一致しないと、`main()` は無限ループで停止する（`main.c:52`〜`56`）。OTP に書かれる文字列のフォーマットは未確認。**（推測）** `platformParseDeviceTypeString()` が先頭の `"0;"` を検査しているので、`"0;CF21;..."` のような形式と考えられる（`platform.c:48`〜`68`）（→ `01_runtime/startup.md`）。
- リンクが切り替わる前に、切り替え前のリンクで送信待ちだったパケットがどう扱われるかは未確認（→ `02_dataflow/communication.md`）。

### [システムコンテキスト](../00_overview/system_context.md)

- CF2.1 のオンボードのセンサが BMI088 + BMP388 である点は、ドライバの名前（`sensors_bmi088_bmp3xx`）からの判断で、回路図では確認していない。
- CF2.1+（`CONFIG_CRAZYFLIE_21_PLUS=y`）のファームウェア上の差分は、プロペラの推力モデルの定数だけであることを確認した（→ [../03_functions/power_distribution.md](../00_overview/../03_functions/power_distribution.md)）。その他のハードウェア上の差分は未確認。

### [起動シーケンス](../01_runtime/startup.md)

- 自己テストに失敗したときに動いているタスクの全体整理は未実施。確認済みなのは次の点である。`CRTP-RX`（`crtp.c:170`〜`200`）と `PARAM`（`param_task.c:76`〜`120`）は `systemWaitStart()` を呼ばないので、失敗中でも param の書き込みは届く。一方、`STABILIZER`、`SENSORS`、`KALMAN`、`PWRMGNT` やデッキのタスクの多くは `systemWaitStart()` で止まったままになる。
- ブートローダ状態の RAM 上の位置（`BL_STATE_PTR`）と、リセットで消えない理由（リンカスクリプトの `NOINIT` 領域と推測）は未確認。
- `deckInit()` が長くかかる理由（`system.c:204` のコメント）の詳細は未確認。

### [FreeRTOS タスクとタスク間通信](../01_runtime/tasks.md)

- `syslinkAccess` はバイナリセマフォなので、優先度の低いタスク（例: `PWRMGNT`、優先度 0）が送信中に、優先度の高いタスクが待たされる優先度逆転が起こりうる。実害があるかは未評価。
- 各タスクのスタック使用量の実測値（`uxTaskGetStackHighWaterMark`）は未取得。実機がないため、静的解析の範囲では確認できない。
- `PASSTHROUGH` タスクが優先度 5（スタビライザと同じ）である理由は未確認（→ ESC 設定の中継で、タイミングに厳しい可能性）。
- `KALMAN` が 1 ms 以内に 1 周を終えられない場合、`runTaskSemaphore`（バイナリ）の解放が重なって、何回分かが失われる。そのときの推定精度への影響は未評価（→ `02_dataflow/control_loop.md`）。
- log の変数が制御周期の途中で読まれる可能性（上記の推測）の検証（→ `04_interfaces/param_log.md`）。

### [通信経路（無線・USB・CPX と CRTP）](../02_dataflow/communication.md)

- 無線の送信が受信に同期する方式の根拠は STM32 側のコードだけで、nRF51 のファームウェア（別リポジトリ）は確認していない。
- CRTP のリンクを切り替えるとき、旧リンクの送信待ちのパケット（radiolink の `txQueue` など）が破棄されるか、残るかは未確認。
- `linkSource` の動作の詳細は未確認。

### [制御ループのデータフロー（センサ → モータ）](../02_dataflow/control_loop.md)

- `state_t.attitude` の pitch は「旧 CF2 座標系で反転」とコメントされている（`stabilizer_types.h:178`）。どのモジュールがこの反転を前提にしているか（PID は `-sensors->gyro.y` を使う: `controller_pid.c:142`）の全体整理は未実施（→ `03_functions/controller.md`）。
- `batteryCompensation` の電圧のローパス係数のコメントは「0.2 で約 10 ステップ」だが、実際の係数は 0.01 で、コメントと値が一致していない（`stabilizer.c:211`）。
- Kalman が 1 ms 以内に終わらない場合、スタビライザは古い state を使い続ける。その遅延の実測値は未取得。
- cf2 の設定では `CONFIG_MOTORS_ESC_PROTOCOL_ONESHOT125=y` になっているが、cf2 はブラシモータである。ESC プロトコルの設定がブラシモータの出力に影響するかは未確認（→ `03_functions/power_distribution.md`）。

### [入出力の経路（入力 → 判断 → 出力）](../02_dataflow/io_paths.md)

- 分析のグラフは主な矢印だけで作っており、網羅していない。とくに param による書き込み先は代表的なものだけである（全ての param の書き込み先を入れると、param から全モジュールへの矢印になる）。
- デッキのアクチュエータ（LED リング、Buzzer など）は、出力先として入れていない。

### [目標値（setpoint）の経路](../02_dataflow/setpoint.md)

- 低レベル commander から HL に戻るには、`commanderRelaxPriority()` の呼び出しが必要だが、cflib がどの操作でメタコマンドを送るかは、ファームウェアの範囲外なので未確認。
- `commanderSetSetpoint` は「potential race but without effect on functionality」とコメントされている（`commander.c:83`）。setpoint と優先度の 2 つのキューを別々に上書きするので、2 つの入力元がほぼ同時に書き込むと、setpoint と優先度が別の入力元のものになりうる。影響の評価は未実施。
- `yawModeUpdate()`（`crtp_commander_rpyt.c:221`）の各モードの意味は未確認。
- 各 HL コマンドのパケット形式は [../04_interfaces/crtp_ports.md](../02_dataflow/../04_interfaces/crtp_ports.md) にまとめた。`COMMAND_SPIRAL` の軌道生成の中身は未確認。

### [通信スタックの実装（CRTP ルータ・リンク・コンソール）](../03_functions/comm_stack.md)

- `crtpReset()`（`crtp.c:226`〜`232`）の呼び出し元と、リセットの契機は未確認。
- 送信キューに優先度がない点が、実際に param の応答遅延などを起こすかは未評価。
- 各リンク（usblink、cpxlink）の `isConnected()` の判定方法は未確認。

### [コマンダ（commander / high-level commander / planner）](../03_functions/commander.md)

- `COMMAND_SPIRAL` の軌道生成の詳細は未確認。
- 軌道が 4096 バイトに収まらない場合の扱い（エラー応答の有無）は未確認。

### [制御（controller）](../03_functions/controller.md)

- Mellinger と INDI は `controlModeLegacy`（int16 の roll/pitch/yaw）を出力しており、Force / Torque の出力を使っていない。物理量から int16 への換算の方法は未確認。
- Brescianini と Lee の制御則、INDI の位置制御の詳細は未確認。
- 各コントローラが setpoint のどのモード（`modeAbs` / `modeVelocity` / `modeDisable`）の組み合わせに対応しているかの一覧は未作成。
- `thrustBase` の既定値（`PID_VEL_THRUST_BASE`）と、気圧で高度を保持するときの値（`PID_VEL_THRUST_BASE_BARO_Z_HOLD`）の使い分けの条件は未確認（`position_controller_pid.c:158`〜`160`）。

### [拡張デッキ](../03_functions/decks.md)

- 取り付けられるデッキは最大 4 枚（`DECK_MAX_COUNT`）。同じデッキを 2 枚付けた場合は、同じドライバの `init` が 2 回呼ばれる。多くのドライバは `isInit` で 2 回目を無視する **（推測）** が、個別には未確認。
- 表のうち、UART1 を使う Lighthouse と bcCam、UART2 を使う AI deck と Buzzer は、同時に付けると競合で全デッキが無効になる。

### [状態推定（estimator）](../03_functions/estimator.md)

- `useBaroUpdate` を切り替える param（またはデッキ）の特定は未実施。
- 速度が機体座標である点（`PX`〜`PZ`）は Kalman の実装の一般的な形からの判断で、`kalman_core.c` の予測式での確認は未実施。
- Complementary が水平位置を扱わないことの確認（`position_estimator_altitude.c` の中身）は未実施。
- 計測値キューが満杯になる頻度（log `estimator.rtRej`）は、実機がないので未評価。IMU だけで 1 kHz × 2〜3 件が入るので、長さ 20 のキューは Kalman が約 7 ms 止まると溢れる計算になる **（推測）**。

### [測位（Flow / Loco / Lighthouse / 外部測位）](../03_functions/positioning.md)

- Loco の各アルゴリズム（TWR、TDoA2、TDoA3）のメッセージの流れは未整理。
- Lighthouse のジオメトリ推定（ベースステーションの位置の求め方）は PC 側の処理と推測しており、ファームウェア内に推定処理があるかは未確認。
- `loco.fwdToEstimator` を 0 にしたときに Loco の計測値がどこへ行くか（ログのみか）は未確認。

### [出力分配とモータ（power distribution / motors）](../03_functions/power_distribution.md)

- `motorPowerSet` の上書きが supervisor の停止より優先される点（上記）が、意図された仕様かどうかは、ソースのコメントからは判断できない。
- ONESHOT125 の設定がブラシモータの出力に影響しないことの確認は未実施。
- M1〜M4 の機体上の位置と回転方向（ミキシングの符号との対応）は、ソースだけでは確認できない。

### [電源管理（pm）](../03_functions/power_management.md)

- `CONFIG_PM_AUTO_SHUTDOWN` を有効にした場合、無操作の判定は `commanderGetInactivityTime()`（最後の setpoint からの時間）で行う。地上で PC から param / log だけを使っていると 5 分で電源が切れる **（推測）**。
- 危険電圧でも STM32 側から電源を切らない cf2 で、nRF51 側に独自の低電圧遮断があるかは、nRF51 のファームウェア（別リポジトリ）を見ないとわからない。
- `PM_BAT_LOW_TIMEOUT` の値と、`batteryLowTimeStamp` の更新条件（`pm_stm32f4.c:430`〜`436`）の正確な関係は未確認。
- 外部電池の電圧・電流の測定（`pmEnableExtBatteryVoltMeasuring` など）の使い方は未確認。

### [センサ（IMU・気圧計）](../03_functions/sensors.md)

- `sensors_mpu9250_lps25h.c`（CF2.0）の処理の詳細は、BMI088 版と同様と推測しているが、未確認。
- `sensorsTask` が I2C3 の読み出しに要する時間と、1 ms の周期に対する余裕は未評価。
- `isSensorsSuspended()`（`stabilizer.c:276`）でセンサをサスペンドする契機（**（推測）** DFU や電源オフの前）は未確認。

### [永続ストレージとメモリサブシステム](../03_functions/storage_mem.md)

- EEPROM の 0x0000〜0x03FF のうち、設定ブロックが使う範囲以外の用途は未確認。
- `flushEeprom` が何もしない件（書き込みの完了を待たない）による、電源断時のデータ破損のリスクは未評価。
- 設定ブロックの読み出しに失敗したときの既定値の内容は未確認。

### [スーパーバイザ（supervisor）](../03_functions/supervisor.md)

- 緊急停止ウォッチドッグは、CRTP で一度でも通知を受けると有効になり、以後 1000 ms 通知がないと緊急停止になる（`supervisor.c:361`〜`370`）。通知は port 9 の `CMD_EMERGENCY_STOP_WATCHDOG`（0x04）と port 6 の `EMERGENCY_STOP_WATCHDOG` の 2 経路がある（[../04_interfaces/crtp_ports.md](../03_functions/../04_interfaces/crtp_ports.md)）。一度有効にしたウォッチドッグを無効に戻す方法があるかは未確認。

### [アプリ層 API](../04_interfaces/app_api.md)

- アプリから `commanderSetSetpoint()` を直接呼ぶことは公式 API に含まれていない。低レベルの setpoint をアプリから出す正式な方法（サンプルの有無）は未確認。
- `app_api` に含まれない関数をアプリが呼んだ場合の互換性の扱い（`docs/development/apis_versions_deprecation.md`）は未確認。

### [CRTP ポートとチャネル](../04_interfaces/crtp_ports.md)

- log の `CONTROL_START_BLOCK` と `CONTROL_START_BLOCK_V2` の違いは未確認。
- 各コマンドのエラー応答（`docs/functional-areas/crtp/crtp_error_numbers.md` の番号）の使われ方は未整理。
- port 6（localization）の各種類のパケット形式の詳細は未整理。

### [デッキ API（検出・ドライバ・周辺機能）](../04_interfaces/deck_api.md)

- 競合や推定器の不一致で全デッキが無効になったとき、自己テスト（`deckTest()`）が失敗扱いになるか（= 機体が起動しないか）は未確認。
- DeckCtrl のアドレス割り当てのプロトコルの詳細は未確認（→ `docs/functional-areas/deckctrl_protocol.md`）。
- バックエンドの列挙の順序（1-Wire と DeckCtrl のどちらが先か）はリンカの配置順で決まる。

### [param / log](../04_interfaces/param_log.md)

- TOC の ID の並び順を決めるのはリンカ（`KEEP(*(.param.*))`）で、ソート指定がない。ビルドごとにグループの順序が変わりうるかは未確認。
- `LOG_BY_FUNCTION` の変数（関数の戻り値）が、`WORKER` タスクの文脈で呼ばれることによる副作用の有無は未確認。

### [MCU ペリフェラルの割り当て（cf2）](../05_hardware/peripherals.md)

- 割り込みの優先度（NVIC の設定、`src/drivers/src/nvic.c` と各ドライバ）の一覧は未作成。FreeRTOS の API を呼ぶ割り込みは `configMAX_SYSCALL_INTERRUPT_PRIORITY` 以下である必要がある。
- USB のピン、LED のピン以外の GPIO（nRF51 との制御線など）の一覧は未作成。
- SPI3 と I2C1 の DMA 競合が、実際に同時使用されうる構成（デッキの組み合わせ）があるかは未確認。

### [ピン割り当て（cf2）](../05_hardware/pin_map.md)

- 表に挙げていないピン（nRF51 のリセット・ブートの制御線、デッキの 1-Wire など）の有無は未確認。1-Wire は nRF51 側に接続されているため、STM32 のピンは使わない **（推測）**。
- LED リング（IO2, IO3）と Loco（IO1〜IO3）、Flow（IO3）は IO ピンが重なるので、同時に付けると競合の検査で全デッキが無効になる（[../04_interfaces/deck_api.md](../05_hardware/../04_interfaces/deck_api.md)）。Loco の代替ピン構成（`CONFIG_LOCODECK_ALT_PIN_RESET` など）はこの競合を避けるためと考えられる **（推測）**。
