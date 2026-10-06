# CRTP ポートとチャネル

## 概要
CRTP は PC と機体の間のパケットプロトコルで、ヘッダの 4 ビットのポートと 2 ビットのチャネルで宛先を指定する。
パケットの形式、ルータの動作、リンクは [../02_dataflow/communication.md](../02_dataflow/communication.md) を参照。
本書では、ポートごとのチャネルとコマンドの一覧をまとめる。

- CRTP のプロトコルバージョン: **12**（`src/modules/interface/crtp.h` の `CRTP_PROTOCOL_VERSION`）。PC は port 13 の `getProtocolVersion` で取得する。
- データ部は最大 30 バイト。

## ポートの一覧

| ポート | 名前 | 方向 | 処理するモジュール | 詳細 |
|---|---|---|---|---|
| 0 | CONSOLE | 機体 → PC | `console.c` | 下記 |
| 2 | PARAM | 双方向 | `param_task.c`, `param_logic.c` | 下記、[param_log.md](param_log.md) |
| 3 | SETPOINT | PC → 機体 | `crtp_commander.c`, `crtp_commander_rpyt.c` | [../02_dataflow/setpoint.md](../02_dataflow/setpoint.md) |
| 4 | MEM | 双方向 | `crtp_mem.c`, `mem.c` | [../03_functions/storage_mem.md](../03_functions/storage_mem.md) |
| 5 | LOG | 双方向 | `log.c` | 下記、[param_log.md](param_log.md) |
| 6 | LOCALIZATION | 双方向 | `crtp_localization_service.c` | [../03_functions/positioning.md](../03_functions/positioning.md) |
| 7 | SETPOINT_GENERIC | PC → 機体 | `crtp_commander.c`, `crtp_commander_generic.c` | [../02_dataflow/setpoint.md](../02_dataflow/setpoint.md) |
| 8 | SETPOINT_HL | PC → 機体 | `crtp_commander_high_level.c` | 下記 |
| 9 | SUPERVISOR | 双方向 | `crtp_supervisor.c` | 下記 |
| 13 | PLATFORM | 双方向 | `platformservice.c` | 下記 |
| 15 | LINK | 双方向 | `crtpservice.c` | 下記 |

ポート 1, 10, 11, 12, 14 は未使用（`src/modules/interface/crtp.h:42`〜`52`）。

## port 0: CONSOLE
| チャネル | 内容 |
|---|---|
| 0 | テキスト（`DEBUG_PRINT` の出力）。改行か 30 バイトで 1 パケット。送信キューが残り 1 のときは `<F>` を付けて以降の欠落を示す |

## port 2: PARAM
| チャネル | 名前 | 内容 |
|---|---|---|
| 0 | `TOC_CH` | 目次（TOC）: `CMD_GET_ITEM_V2`（2）で項目の型・グループ・名前、`CMD_GET_INFO_V2`（3）で項目数と CRC |
| 1 | `READ_CH` | 値の読み出し（ID 指定） |
| 2 | `WRITE_CH` | 値の書き込み（ID 指定） |
| 3 | `MISC_CH` | その他のコマンド（下表） |

| MISC コマンド | 値 | 内容 |
|---|---|---|
| `MISC_SETBYNAME` | 0 | グループ名と名前で値を書き込む |
| `MISC_VALUE_UPDATED` | 1 | 機体側で値が変わったことの通知（機体 → PC） |
| `MISC_GET_EXTENDED_TYPE` / `_V2` | 2 / 7 | 拡張型（永続化可否など）の取得 |
| `MISC_PERSISTENT_STORE` | 3 | 値を EEPROM に保存 |
| `MISC_PERSISTENT_GET_STATE` | 4 | 保存済みかどうかと、保存値・既定値の取得 |
| `MISC_PERSISTENT_CLEAR` | 5 | 保存値の削除 |
| `MISC_GET_DEFAULT_VALUE` / `_V2` | 6 / 8 | 既定値の取得 |

根拠: `src/modules/interface/param.h:95`〜`108`, `src/modules/src/param_task.c:91`〜`112`, `param_logic.c:56`〜`61`

## port 5: LOG
| チャネル | 名前 | 内容 |
|---|---|---|
| 0 | `TOC_CH` | 目次: `CMD_GET_ITEM_V2`（2）、`CMD_GET_INFO_V2`（3） |
| 1 | `CONTROL_CH` | ログブロックの操作（下表） |
| 2 | `LOG_CH` | ログのデータ（機体 → PC）: ブロック ID、タイムスタンプ、変数の値 |

| CONTROL コマンド | 値 | 内容 |
|---|---|---|
| `CONTROL_DELETE_BLOCK` | 2 | ブロックの削除 |
| `CONTROL_START_BLOCK` | 3 | ブロックの送信開始（周期を指定） |
| `CONTROL_STOP_BLOCK` | 4 | ブロックの送信停止 |
| `CONTROL_RESET` | 5 | 全ブロックの削除 |
| `CONTROL_CREATE_BLOCK_V2` | 6 | ブロックの作成（変数 ID と型の列） |
| `CONTROL_APPEND_BLOCK_V2` | 7 | ブロックへの変数の追加 |
| `CONTROL_START_BLOCK_V2` | 8 | ブロックの送信開始（周期の分解能が異なる **（推測）**） |

根拠: `src/modules/src/log.c:123`〜`136`

## port 8: SETPOINT_HL（high-level commander）
先頭バイトがコマンド番号（[../02_dataflow/setpoint.md](../02_dataflow/setpoint.md) の表）で、続くデータの構造は次のとおり（すべて packed、`float` は 32 ビット）。

| コマンド | データ構造 |
|---|---|
| 0 `SET_GROUP_MASK`（非推奨） | `groupMask` |
| 1 `TAKEOFF`（非推奨） | `groupMask, height, duration` |
| 2 `LAND`（非推奨） | `groupMask, height, duration` |
| 3 `STOP` | `groupMask` |
| 4 `GO_TO`（非推奨） | `groupMask, relative, x, y, z, yaw, duration` |
| 5 `START_TRAJECTORY`（非推奨） | `groupMask, relative, reversed, trajectoryId, timescale` |
| 6 `DEFINE_TRAJECTORY` | `trajectoryId, description`（メモリ上の位置、区間数、形式） |
| 7 `TAKEOFF_2` | `groupMask, height, yaw, useCurrentYaw, duration` |
| 8 `LAND_2` | `groupMask, height, yaw, useCurrentYaw, duration` |
| 9 `TAKEOFF_WITH_VELOCITY` | `groupMask, height, heightIsRelative, yaw, useCurrentYaw, velocity` |
| 10 `LAND_WITH_VELOCITY` | `groupMask, height, heightIsRelative, yaw, useCurrentYaw, velocity` |
| 11 `SPIRAL` | `groupMask, sideways, clockwise, phi, r0, rf, dz, duration` |
| 12 `GO_TO_2` | `groupMask, relative, linear, x, y, z, yaw, duration` |
| 13 `START_TRAJECTORY_2` | `groupMask, relativePosition, relativeYaw, reversed, trajectoryId, timescale` |

根拠: `src/modules/src/crtp_commander_high_level.c` の `struct data_*`

## port 9: SUPERVISOR
| チャネル | 名前 | 処理 | 内容 |
|---|---|---|---|
| 0 | `SUPERVISOR_CH_INFO` | キュー → `SUPERVISOR` タスク | 状態の問い合わせ |
| 1 | `SUPERVISOR_CH_COMMAND` | コールバック（`CRTP-RX`） | コマンド |

| 情報コマンド | 値 | 応答 |
|---|---|---|
| `CMD_CAN_BE_ARMED` 〜 `CMD_HL_CONTROL_DISABLED` | 0x01〜0x0B | 情報ビット（[../03_functions/supervisor.md](../03_functions/supervisor.md)）の各ビット |
| `CMD_GET_STATE_BITFIELD` | 0x0C | 情報ビット全体（16 ビット） |

| 操作コマンド | 値 | 内容 |
|---|---|---|
| `CMD_ARM_SYSTEM` | 0x01 | アーム / アーム解除 |
| `CMD_RECOVER_SYSTEM` | 0x02 | クラッシュからの復帰 |
| `CMD_EMERGENCY_STOP` | 0x03 | 緊急停止（→ Locked） |
| `CMD_EMERGENCY_STOP_WATCHDOG` | 0x04 | 緊急停止ウォッチドッグの通知。一度受けると以後 1 秒ごとの通知が必要になる |

応答にはコマンド番号に `CMD_RESPONSE`（0x80）を足した値を使う。

根拠: `src/modules/interface/crtp_supervisor.h:33`〜`54`, `src/modules/src/crtp_supervisor.c:115`〜`171`

## port 13: PLATFORM
| チャネル | 名前 | コマンド |
|---|---|---|
| 0 | `platformCommand` | 0: 連続波の出力（無線の試験）、1: アーム（非推奨、port 9 へ移行）、2: 復帰（非推奨）、3: ユーザへの通知 |
| 1 | `versionCommand` | 0: CRTP プロトコルのバージョン、1: ファームウェアのバージョン、2: 機種名 |
| 2 | `appChannel` | アプリ層との任意データ（cf2 ではアプリ層は無効） |

根拠: `src/modules/src/platformservice.c:53`〜`69`

## port 15: LINK
| チャネル | 名前 | 内容 |
|---|---|---|
| 0 | `linkEcho` | 受け取ったパケットを返す |
| 1 | `linkSource` | 下り方向の試験用パケットを返す |
| 2 | `linkSink` | 受け取って捨てる |

根拠: `src/modules/src/crtpservice.c:40`〜`92`

## 公式ドキュメントとの差異
- `docs/functional-areas/crtp/` の各ページとの突き合わせは未実施。

## 未解決事項
- log の `CONTROL_START_BLOCK` と `CONTROL_START_BLOCK_V2` の違いは未確認。
- 各コマンドのエラー応答（`docs/functional-areas/crtp/crtp_error_numbers.md` の番号）の使われ方は未整理。
- port 6（localization）の各種類のパケット形式の詳細は未整理。
