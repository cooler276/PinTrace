# 用語集

本書の各文書で使う用語。説明はこのファームウェアでの意味に限る。

## 通信
| 用語 | 意味 | 参照 |
|---|---|---|
| CRTP | Crazy RealTime Protocol。PC と機体の間のパケットプロトコル。ポート 4 ビット + チャネル 2 ビット + データ 30 バイト | [communication.md](../02_dataflow/communication.md), [crtp_ports.md](../04_interfaces/crtp_ports.md) |
| syslink | STM32 と nRF51 の間の UART 上のプロトコル。無線、電源管理、1-Wire、システム情報を運ぶ | [communication.md](../02_dataflow/communication.md) |
| CPX | Crazyflie Packet eXchange。AI デッキの ESP32 / GAP8、Wi-Fi ホスト、STM32 の間でパケットを中継するプロトコル | [communication.md](../02_dataflow/communication.md) |
| リンク（link） | CRTP の物理的な経路（radiolink / usblink / cpxlink）。`struct crtpLinkOperations` で抽象化される | [comm_stack.md](../03_functions/comm_stack.md) |
| Crazyradio | PC に挿す USB の無線ドングル | [system_context.md](../00_overview/system_context.md) |
| ESB | Enhanced ShockBurst。Nordic の 2.4 GHz の無線プロトコル。Crazyradio と nRF51 が使う | — |
| P2P | nRF51 経由の機体同士の直接通信 | [communication.md](../02_dataflow/communication.md) |
| TOC | Table Of Contents。param / log の変数の目次。ID は配列の添字 | [param_log.md](../04_interfaces/param_log.md) |

## 制御
| 用語 | 意味 | 参照 |
|---|---|---|
| スタビライザ（stabilizer） | 1 kHz の制御ループ（センサ → 推定 → 制御 → モータ）と、それを実行するタスク | [control_loop.md](../02_dataflow/control_loop.md) |
| setpoint | 目標値（位置・速度・姿勢・推力など）と、軸ごとのモード（`modeAbs` / `modeVelocity` / `modeDisable`） | [setpoint.md](../02_dataflow/setpoint.md) |
| state | 推定状態（姿勢、位置、速度、加速度） | [control_loop.md](../02_dataflow/control_loop.md) |
| control | コントローラの出力。Legacy（roll/pitch/yaw/thrust）、ForceTorque、Force の 3 モード | [control_loop.md](../02_dataflow/control_loop.md) |
| commander | setpoint を優先度つきで保持するモジュール | [setpoint.md](../02_dataflow/setpoint.md) |
| 低レベル commander | PC が CRTP で setpoint を連続送信する方式（port 3 / 7） | [setpoint.md](../02_dataflow/setpoint.md) |
| high-level commander（HL） | 離陸・着陸・移動・軌道追従のコマンドから、機体内で setpoint を生成する方式（port 8） | [commander.md](../03_functions/commander.md) |
| planner | HL の軌道生成器。7 次多項式の区間軌道 | [commander.md](../03_functions/commander.md) |
| power distribution | 制御出力を 4 モータの推力に分配する処理（ミキシング） | [power_distribution.md](../03_functions/power_distribution.md) |
| 電池補償 | 電池電圧の低下に合わせて PWM の比率を上げ、推力を一定に保つ処理 | [power_distribution.md](../03_functions/power_distribution.md) |
| idle thrust | モータの最小出力（cf2 は 0） | [power_distribution.md](../03_functions/power_distribution.md) |
| PID / Mellinger / INDI / Brescianini / Lee | コントローラの種類 | [controller.md](../03_functions/controller.md) |
| OOT（out-of-tree） | ファームウェアのソースツリーの外で作るアプリ、コントローラ、推定器 | [app_api.md](../04_interfaces/app_api.md) |

## 推定・測位
| 用語 | 意味 | 参照 |
|---|---|---|
| estimator | 状態推定器。Complementary / Kalman / UKF / OOT | [estimator.md](../03_functions/estimator.md) |
| Complementary | IMU と気圧計による軽量な推定器（姿勢と高度） | [estimator.md](../03_functions/estimator.md) |
| Kalman（EKF） | 拡張カルマンフィルタの推定器。位置・速度・姿勢の誤差を状態とする | [estimator.md](../03_functions/estimator.md) |
| 計測値キュー（measurementsQueue） | 推定器に計測値を渡す共通のキュー（長さ 20） | [estimator.md](../03_functions/estimator.md) |
| 計測モデル（mm_*） | Kalman の計測値の種類ごとの更新式 | [estimator.md](../03_functions/estimator.md) |
| 外れ値フィルタ（outlier filter） | TDoA と Lighthouse の計測値の異常値を除く | [estimator.md](../03_functions/estimator.md) |
| LPS / Loco | Loco Positioning System。UWB による測位 | [positioning.md](../03_functions/positioning.md) |
| UWB | Ultra Wide Band。Loco デッキの DW1000 が使う無線 | [positioning.md](../03_functions/positioning.md) |
| TWR | Two Way Ranging。アンカーとの往復で距離を測る方式 | [positioning.md](../03_functions/positioning.md) |
| TDoA2 / TDoA3 | Time Difference of Arrival。複数アンカーからの到達時間差で測位する方式（2 と 3 は版） | [positioning.md](../03_functions/positioning.md) |
| アンカー（anchor） | Loco の位置が既知の固定局 | [positioning.md](../03_functions/positioning.md) |
| Lighthouse | 赤外線のスイープを出すベースステーションによる測位 | [positioning.md](../03_functions/positioning.md) |
| ベースステーション（base station） | Lighthouse の発信機（V1 / V2） | [positioning.md](../03_functions/positioning.md) |
| スイープ角（sweep angle） | ベースステーションの光の面が受光センサを通過した角度 | [positioning.md](../03_functions/positioning.md) |
| OOTX | Lighthouse のベースステーションが光で送る較正データ | [positioning.md](../03_functions/positioning.md) |
| Flow | オプティカルフローによる水平速度の計測 | [positioning.md](../03_functions/positioning.md) |
| ToF | Time of Flight。レーザー測距 | [positioning.md](../03_functions/positioning.md) |
| MoCap | モーションキャプチャ。外部のカメラで測った位置を CRTP port 6 で送る | [positioning.md](../03_functions/positioning.md) |

## 安全・電源
| 用語 | 意味 | 参照 |
|---|---|---|
| supervisor | 機体の安全状態を管理する状態機械 | [supervisor.md](../03_functions/supervisor.md) |
| アーム（arming） | モータを回してよい状態にすること。cf2 は自動アーム | [supervisor.md](../03_functions/supervisor.md) |
| 転倒（tumble） | 傾きや逆さまの状態が一定時間続くこと | [supervisor.md](../03_functions/supervisor.md) |
| Locked | supervisor の終端状態。再起動が必要 | [supervisor.md](../03_functions/supervisor.md) |
| 緊急停止ウォッチドッグ | 一度有効にすると、1 秒ごとの通知がないと緊急停止する仕組み | [supervisor.md](../03_functions/supervisor.md) |
| health テスト | プロペラと電池の試験 | [control_loop.md](../02_dataflow/control_loop.md) |
| pm | 電源管理。電池の状態、低電圧、シャットダウン | [power_management.md](../03_functions/power_management.md) |

## デッキ
| 用語 | 意味 | 参照 |
|---|---|---|
| デッキ（deck） | 機体に積み重ねる拡張ボード | [decks.md](../03_functions/decks.md) |
| VID / PID | デッキの識別子（Bitcraze は VID 0xBC） | [deck_api.md](../04_interfaces/deck_api.md) |
| 1-Wire（OW） | デッキの識別メモリを読むバス。nRF51 がマスタ | [deck_api.md](../04_interfaces/deck_api.md) |
| DeckCtrl | I2C でデッキ上のマイコンを検出・制御する仕組み | [deck_api.md](../04_interfaces/deck_api.md) |
| 検出バックエンド | デッキを列挙する仕組み（1-Wire / DeckCtrl） | [deck_api.md](../04_interfaces/deck_api.md) |
| `usedPeriph` / `usedGpio` | ドライバが宣言する使用資源。競合の検査に使う | [deck_api.md](../04_interfaces/deck_api.md) |

## 基盤・OS
| 用語 | 意味 | 参照 |
|---|---|---|
| param | PC から読み書きできる設定値 | [param_log.md](../04_interfaces/param_log.md) |
| log | PC に周期的に送る変数 | [param_log.md](../04_interfaces/param_log.md) |
| ログブロック | log で一緒に送る変数の組 | [param_log.md](../04_interfaces/param_log.md) |
| 永続化（persistent） | param の値を EEPROM に保存し、起動時に復元すること | [storage_mem.md](../03_functions/storage_mem.md) |
| KVE | Key-Value EEPROM。EEPROM 上のキーと値のストア | [storage_mem.md](../03_functions/storage_mem.md) |
| 設定ブロック（configblock） | EEPROM の先頭の固定レイアウトの設定（無線、較正角） | [storage_mem.md](../03_functions/storage_mem.md) |
| mem（メモリサブシステム） | PC から CRTP port 4 で各種メモリを読み書きする仕組み | [storage_mem.md](../03_functions/storage_mem.md) |
| worker | 重い処理を肩代わりする汎用タスク（`workerSchedule()`） | [tasks.md](../01_runtime/tasks.md) |
| static_mem | FreeRTOS のタスクとキューを静的に確保するマクロ（`STATIC_MEM_*`） | [tasks.md](../01_runtime/tasks.md) |
| `systemWaitStart()` | 起動時の自己テストが終わるまで各タスクを待たせる関数 | [startup.md](../01_runtime/startup.md) |
| ledseq | LED の点滅パターン（シーケンス）の再生 | — |
| eventtrigger | イベントの記録の仕組み（リンカセクション `.eventtrigger`） | [architecture.md](../00_overview/architecture.md) |
| リンカセクションへの登録 | マクロで構造体を専用のセクションに置き、起動時に一覧として走査する仕組み（param、log、デッキドライバなど） | [architecture.md](../00_overview/architecture.md) |
| platform | 機体の種類（cf2、bolt、tag、flapper、cf21bl）。ビルドとの実行時の判定がある | [architecture.md](../00_overview/architecture.md) |

## ハードウェア
| 用語 | 意味 | 参照 |
|---|---|---|
| nRF51 | 無線と電源管理を担う Nordic 製の MCU | [system_context.md](../00_overview/system_context.md) |
| OTP | One-Time Programmable 領域。機種の文字列を書き込む | [startup.md](../01_runtime/startup.md) |
| IWDG | 独立ウォッチドッグ（約 100 ms） | [startup.md](../01_runtime/startup.md) |
| EXTI | 外部割り込み。IMU（EXTI14）や Loco で使う | [peripherals.md](../05_hardware/peripherals.md) |
| CCM | Core Coupled Memory（64 KB）。DMA からアクセスできない RAM | [tasks.md](../01_runtime/tasks.md) |
| ブラシモータ / ブラシレスモータ | cf2 はブラシモータ（PWM 直接駆動）。ブラシレスは ESC 経由（OneShot / DShot） | [power_distribution.md](../03_functions/power_distribution.md) |
| DShot / OneShot125 | ブラシレスの ESC へのプロトコル | [power_distribution.md](../03_functions/power_distribution.md) |
