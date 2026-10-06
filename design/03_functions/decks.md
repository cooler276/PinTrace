# 拡張デッキ

## 概要
デッキは機体の上下に取り付ける拡張ボードである。起動時に自動で検出され、VID / PID が一致するドライバが初期化される。
ドライバはリンカセクション `.deckDriver` に登録されるので、Kbuild に追加するだけで組み込まれる。

本書では、cf2 でビルドされるデッキドライバの一覧と、それぞれが使う資源・タスク・推定器をまとめる。
検出の仕組みとドライバの API は `04_interfaces/deck_api.md` を参照。

## 構成ファイル
| ディレクトリ | 役割 |
|---|---|
| `src/deck/core/` | デッキの列挙（`deck_info.c`）、ドライバの検索（`deck_drivers.c`）、初期化と試験（`deck.c`）、デッキのメモリ、デッキの故障監視（`deck_supervisor.c`） |
| `src/deck/backends/` | 検出バックエンド: 1-Wire（`deck_backend_onewire.c`）、DeckCtrl（`deck_backend_deckctrl.c`） |
| `src/deck/api/` | デッキ用の周辺機能の API（GPIO、アナログ、SPI、SPI3、DeckCtrl の GPIO） |
| `src/deck/drivers/src/` | 各デッキのドライバ |

## デッキドライバの一覧（cf2）

| デッキ | 名前 | VID/PID | 使用ペリフェラル | 使用 GPIO | 要求する推定器 | 生成するタスク |
|---|---|---|---|---|---|---|
| LED リング | `bcLedRing` | 0xBC/0x01 | TIMER3 | IO_2, IO_3 | — | （タイマ） |
| Buzzer | `bcBuzzer` | 0xBC/0x04 | TIMER5, UART2 | — | — | — |
| Loco | `bcLoco` | 0xBC/0x06 | SPI | IO_1〜IO_3 | Kalman | `LPS` |
| micro-SD | `bcUSD` | 0xBC/0x08 | SPI | IO_4 | — | `USDLOG`, `USDWRITE` |
| Z-ranger | `bcZRanger` | 0xBC/0x09 | I2C | — | — | `ZRANGER` |
| Flow v1 | `bcFlow` | 0xBC/0x0A | I2C, SPI | IO_3 | Kalman | `FLOW` |
| OA | `bcOA` | 0xBC/0x0B | I2C | — | — | `OA` |
| Multi-ranger | `bcMultiranger` | 0xBC/0x0C | I2C | — | — | `MR` |
| Z-ranger v2 | `bcZRanger2` | 0xBC/0x0E | I2C | — | — | `ZRANGER2` |
| Flow v2 | `bcFlow2` | 0xBC/0x0F | I2C, SPI | IO_3 | Kalman | `FLOW`（+ `ZRANGER2`） |
| Lighthouse | `bcLighthouse4` | 0xBC/0x10 | UART1 | — | Kalman | `LH` |
| Active marker | `bcActiveM` | 0xBC/0x11 | — | — | — | `ACTIVEMARKER-DECK` |
| AI deck | `bcAI` | 0xBC/0x12 | UART2 | IO_1, IO_4 | — | `CPX` ほか 4 つ |
| Color LED（下） | `bcColorLedBot` | 0xBC/0x13 | — | — | — | `COLORLED-DECK` |
| Color LED（上） | `bcColorLedTop` | 0xBC/0x14 | — | — | — | `COLORLED-DECK` |
| bcCam | `bcCam` | 0xBC/0x15 | UART1 | — | — | `bcCamUart` |
| RPM（試験用） | `bcRpm` | 0x00/0x00 | — | IO_2, IO_3, PA2, PA3 | — | — |
| 試験用 | `bcExpTest`, `bcBoltTest`, `bcExpTestRR`, `bcExpTestCfBl`, `bcRadioTest` | 0xBC/0xFF など | — | 全 GPIO など | — | `RADIOTEST` など |

根拠: 各ドライバの `static const DeckDriver` の定義（`src/deck/drivers/src/*.c`）。VID/PID が 0 のものは `CONFIG_DECK_FORCE` で強制しない限り検出されない。

## 資源の競合
「使用ペリフェラル」と「使用 GPIO」は、デッキ同士の競合を検出するための宣言である。起動時に検査され、I2C と SPI 以外で重なりがあると、**全デッキが初期化されない**（`src/deck/core/deck_info.c:187`〜`225`、[../04_interfaces/deck_api.md](../04_interfaces/deck_api.md)）。たとえば次の組み合わせは同じ資源を使う。

| 資源 | 使うデッキ |
|---|---|
| UART1 | Lighthouse、bcCam |
| UART2 | AI deck、Buzzer |
| SPI | Loco、micro-SD、Flow v1 / v2 |
| IO_3 | Loco、Flow、LED リング |
| I2C | Z-ranger、Multi-ranger、OA、Flow |

SPI や I2C はバスなので共有できる。一方、SPI の CS や割り込みなどに使う GPIO は共有できない（→ `05_hardware/pin_map.md`）。

## デッキ間の依存
- Flow v2 は、ToF センサの処理を Z-ranger v2 のドライバに委譲する（`deckFindDriverByName("bcZRanger2")`、`flowdeck_v1v2.c:212`〜`240`）。
- 推定器を要求するデッキ（Flow、Loco、Lighthouse）はすべて Kalman を要求するので、組み合わせても競合しない。

## デッキの故障監視
- `CONFIG_DECK_SUPERVISOR`（cf2 は有効）で、デッキが故障を報告すると supervisor の `DECK_FAULT` 条件が立つ（`src/modules/src/supervisor.c:513`〜`517`）。
- 飛行中にデッキの故障が起きると、ExceptFreeFall を経て Locked になる（[supervisor.md](supervisor.md)）。

## 設定・パラメータ

| 種別 | 名前 | 説明 |
|---|---|---|
| Kconfig | `CONFIG_DECK_*` | ビルドするデッキドライバ（cf2 では 20 種類以上が有効） |
| Kconfig | `CONFIG_DECK_FORCE` | 検出に関係なく初期化するドライバの名前（cf2 は `"none"`） |
| Kconfig | `CONFIG_DECK_BACKEND_ONEWIRE`, `CONFIG_DECK_BACKEND_DECKCTRL` | 検出バックエンド |
| param | `deck.<ドライバ名>` | デッキが検出・初期化されたか（読み取り専用） |

## 未解決事項
- 取り付けられるデッキは最大 4 枚（`DECK_MAX_COUNT`）。同じデッキを 2 枚付けた場合は、同じドライバの `init` が 2 回呼ばれる。多くのドライバは `isInit` で 2 回目を無視する **（推測）** が、個別には未確認。
- 表のうち、UART1 を使う Lighthouse と bcCam、UART2 を使う AI deck と Buzzer は、同時に付けると競合で全デッキが無効になる。
