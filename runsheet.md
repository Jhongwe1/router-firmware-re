# runsheet — 一行一行照做的作業單

> **這份檔案的目的:讓一個從來沒碰過這個專案的人,把命令複製貼上,得到可比對的輸出。**
> **它刻意冗長,而那是功能不是缺點** —— 每一個旗標都解釋、每一步都有逐字的預期輸出、
> 每一步都有停止條件。**不要壓縮它。**
> 它不解釋為什麼。**為什麼在 [`RUNBOOK.md`](RUNBOOK.md) —— 兩份檔案分工,不重複。**

## 先讀這 60 秒:你能重現到哪裡

**這個 repo 的一部分你重現不了,而這件事寫在這裡而不是讓你在第 40 步發現。**
這台裝置跑的 firmware **不在任何廠商下載頁上**,而它的 flash dump 帶有這一台
獨有的資料(`H601` 區的 MAC 與射頻校準)。完整的三層對照在
[`REPRODUCE.md`](REPRODUCE.md);一句話版本:

| 層 | 你需要 | 這份作業單的哪幾節 |
|---|---|---|
| **T1** | 一份 clone + 網路 | **`A1`** —— 而它包含 **205 個檢查**,一台裝置都不用 |
| **T2** | T1 + 你自己的 N150RT + 一條 CP2102(約 US$3) | `A2`–`A5`、`A12` |
| **T3** | T2 + USB 網卡 + 隔離網段 | `A6`–`A11` |

> **只做 T1 也值得。** T1 能重現的不是這個 repo 的數字,是**這個 repo 的儀器會在
> 該失敗的時候失敗** —— 95 個守衛案例的存在目的就是證明每一個拒絕是活的,
> 加上 110 個 fwrecon 測試。五分鐘,一份 clone。

## 這份檔案擁有什麼,以及誰擁有其他部分

**一份狀態一個擁有者。這份檔案擁有「確切的命令」,不擁有別的。**

| 檔案 | 擁有 |
|---|---|
| **本檔 Part A** | **確切的命令、逐字的預期輸出、停止條件、驗證步驟** ← 可編輯 |
| **本檔 Part B** | 每一週跑哪幾節、順序、本週額外步驟 ← **只追加** |
| [`RUNBOOK.md`](RUNBOOK.md) | **每一步為什麼存在**、坑的來歷、跨週推理 |
| [`BENCH-LOG.md`](BENCH-LOG.md) | 某一天**實際**打了什麼、實際看到什麼 ← 只追加 |
| [`test-cases.toml`](test-cases.toml) → [`test-ledger.md`](test-ledger.md) | 預測 / 反證條件 / 判定 / 證據 |
| [`PROGRESS.md`](PROGRESS.md) | gate、週、carried-forward |
| [`docs/disclosure.md`](docs/disclosure.md) | 每個發現的揭露狀態 |

**`make ci` 會跑 `tools/check-runsheet.py`**,它驗證本檔裡每一個 `make` 目標存在、
每一個檔案路徑存在、**每一支工具的每一個旗標真的在那支工具的 `--help` 裡**、
以及每一個 `§8.x.y` 交叉引用解析得到。**手寫可以;命令壞掉不能出貨。**

## 一個步驟長什麼樣

每一節都是同一個形狀,而**最後兩欄是這份檔案跟 RUNBOOK 的差別**:

| 欄位 | 意思 |
|---|---|
| **層** | `T1` / `T2` / `T3` —— 你手上有什麼才做得到 |
| **會不會改變裝置** | `純讀` / `改設定` / **`不可逆`**。看到 `不可逆` 就停下來讀完整節 |
| **做什麼** | 複製貼上。**`bash` / `powershell` 區塊是要跑的,`text` 區塊是預期輸出** —— 而 `make ci` 會擋掉沒有標註的區塊,因為「要跑的」和「會看到的」長得一樣是這份檔案最容易害人的地方 |
| **預期輸出** | **逐字**。你的工作是比對,不是判斷 |
| **驗證** | 一條額外的命令,把「我跑了」變成「它成功了」 |
| **❌ 停止條件** | 出現這個就**不要繼續**。這一欄是這份檔案最值錢的部分 |
| **⚠️ 坑** | 會咬你的那一件事,寫在會咬到的位置,附儀器 bug 編號 |
| **關掉的項目** | 這一節做完,**登記簿的哪幾列被關掉了** —— 見下 |
| **最後驗證** | 這一節的命令**最後一次真的被執行**是哪一天。舊的日期代表要小心 |

> **實體動作用 🔌 標記。** 那幾步腳本做不到,只有你的手做得到。

### 「關掉的項目」是一個承諾,而且它由機器維護

**[`test-ledger.md`](test-ledger.md) 裡每一個有結果的項目,都必須有一節可以走到它。**

那不是口號。`make ci` 跑的 `tools/check-runsheet.py` 雙向檢查:

1. 一節聲稱關掉的每一個編號,**必須真的在登記簿裡**(打錯字、憑空發明的編號,
   看起來跟真的覆蓋率一模一樣);
2. **登記簿裡每一個已執行的項目,必須至少被一節聲稱** —— 否則 CI 紅。
   真的沒有程序的,要寫進 `<!-- no-procedure: … -->` 區塊**並附理由**。

第二個方向才是重點。第一個方向在一份空的對應表上也會過。

> **這個檢查是作者在 2026-08-17 問出來的**:「我們不是關掉了 27 項嗎,
> 那不是應該有 27 個可以被重複執行的東西?」—— **是。而當時去量,這份檔案只提到 27 項裡的 1 項。**
> 補完之後才發現有兩節(`A1.6` `A1.7`)和一節(`A8.5`)**根本不存在**,
> 而 `A8.5` 是這個專案最強的那一條證據鏈。
> **「一個結果沒有人能走到它的程序」= 一個讀者只能相信你的主張**,而這整個 repo
> 就是為了不要那樣而排的。

---

# Part A — 程序

## A0 開工前:讓機器自己說它準備好了沒

| | |
|---|---|
| **層** | T1 / T2 / T3(各自檢查) |
| **會不會改變裝置** | 純讀,而且**完全不碰裝置** |
| **關掉的項目** | —（這一節不關掉登記簿項目） |
| **最後驗證** | 2026-08-17 |

**做什麼:**

```bash
make doctor
```

只想檢查某一層:

```bash
make doctor TIER=1
```

**預期輸出**(尾巴那一行是重點):

```text
  20 ok, 1 not applicable, 0 to fix
  ready for: whatever the tiers above allow.
```

**每一個 `FAIL` 都自帶修它的那一行命令。** 例如:

```text
  FAIL  no /dev/ttyUSB* — the serial adapter is not attached to this WSL instance
        -> PowerShell:  usbipd list  then  usbipd attach --wsl --busid <the 10c4:ea60 one>
```

> ❌ **有任何 `FAIL` 就不要往下。** 這一節存在的唯一理由,就是把「照做了但沒用」
> 變成「這一項壞了,而且這是修它的命令」。

> ⚠️ **`--` 不是 `FAIL`。** 它代表「這一層的東西你沒有,而那沒有錯」——
> 只有一份 clone 的讀者會看到 T2 / T3 全部是 `--`,那是正常的。

---

## A1 桌面側:從一份 clone 到全部報告(**不需要任何硬體**)

| | |
|---|---|
| **層** | **T1** |
| **會不會改變裝置** | 沒有裝置 |
| **關掉的項目** | —（這一節不關掉登記簿項目） |
| **最後驗證** | `ci` / `ledger` / `todo`:2026-08-17。`setup` / `fetch` / `unpack` / `recon`:2026-08-07(W01),本場未重跑 |

**這一節是整個 repo 唯一一段「clone 下來就跑得完」的部分。**

### A1.1 工具鏈

```bash
make setup
make verify
```

**預期**:`verify` 對每一支工具印一行,全部 `ok`,最後 `G0 green`。

> ⚠️ **`make setup` 之後要用登入 shell,而 `-lc` 一度不夠。**
> `binwalk` 裝在 `~/.cargo/bin`,而 PATH 的設定原本只寫進 `~/.bashrc` ——
> 那個檔案開頭有「非互動就 return」的守衛,所以 `bash -lc` 讀不到它。
> **2026-08-17 修掉了**(`setup-wsl.sh` 現在也寫進 `~/.profile`,並且自己驗一次)。
> 舊的環境跑一次 `bash tools/setup/setup-wsl.sh path` 就好。
> 從 Windows 呼叫一律用:
> ```text
> wsl -d Ubuntu-24.04 -- bash -lc 'cd /mnt/c/Users/Key20/Desktop/router && make ci'
> ```

### A1.2 韌體:抓下來,而且驗雜湊

```bash
make fetch
make unpack
```

**預期**:`fetch` 對每個檔案印 `sha256 OK`;`unpack` 印 `no symlinks in the extracted tree` 之類的結構檢查。

> ❌ **雜湊不符就停。** [`firmware/SOURCES.json`](firmware/SOURCES.json) 記錄了每一份
> 映像的來源與當時的雜湊。不符代表你拿到的不是同一個檔案,後面每一個結論都不可比。

### A1.3 報告

```bash
make recon
make check-reports
```

**預期**:`reports/` 底下的 JSON / MD 重新生成,`check-reports` 印
`reports OK — N fwrecon (schema 1.0), M Ghidra, 1 rtcase`。

### A1.4 ★ 這一節真正值得你花時間的東西

```bash
make ci
```

**預期**(尾巴):

```text
  33 passed, 0 failed        # test-rtcase.sh
  5 passed, 0 failed, 1 skipped
  15 passed, 0 failed        # test-bench-probe.sh
  7 passed, 0 failed         # test-loader-unpack.sh
  ok   local CI equivalents passed (container build not included)
```

**這 95 個守衛案例加上 110 個 fwrecon 測試,存在的目的不是證明工具會動,
是證明工具的每一個拒絕是活的。** 例如:

```bash
bash tools/test-loader-unpack.sh
```

它會建出五份**故意壞掉**的合成映像,確認解包器對每一種都拒絕、而且**拒絕的理由
是對的那一個**,最後用一份好的映像當正對照組。**一個只會拒絕的工具跟一個永遠
拒絕的工具,在只有負面案例的測試裡長得一模一樣。**

### A1.5 登記簿

```bash
make todo WEEK=W05
make ledger
```

**預期**:

```text
W05: 27/27 done, 0 outstanding
wrote test-ledger.md - 130 cases, 34 executed
```

---

## A1.6 從 dump 做的靜態判定 —— **不用接線,而它省掉一次開機**

| | |
|---|---|
| **層** | **T2**(要一份 dump,但**不用把裝置接起來**) |
| **會不會改變裝置** | 沒有碰裝置 |
| **關掉的項目** | `P9-1` |
| **最後驗證** | 2026-08-17 |

**這一節示範一件值得學的事:一個「裝置測試」有時候在桌面上就答完了,而且答得更好。**

`P9-1` 問的是「bootloader 能不能傳 `init=/bin/sh` 給 kernel」。直覺是接線、搶
bootloader、試著改 cmdline —— 一次完整的開機循環。**但那個問題在 dump 裡就有答案。**

### A1.6.1 bootloader 的第二階段

```bash
make loader-report
```

**預期**:

```text
reports/bootloader-unit-2018.json: stage 2 56,592 bytes, 328 strings, 0 cmdline hits
```

**`0 cmdline hits` 是這一節的結論**,而它的可信度來自同一行的另一半:
工具在**找不到 `?` 印的全部 17 個指令時會拒絕出報告**。所以那個 `0` 有對照組。

想自己看那 56,592 bytes 裡有什麼:

```bash
python3 tools/loader-unpack.py "$HOME/fwre-work/dumps/flash-n150rt-console-1.bin" --strings | less
```

> 🔴 **為什麼要解壓:整顆 4 MiB 裡 `grep FLR` 找不到東西。** `grep IPCONFIG`
> 也找不到,`grep "COMMAND MODE HELP"` 也找不到 —— 而那三個字每天都在 console 上。
> 原因是 `0x000000`–`0x0012F0` 只是第一階段(DRAM 訓練),
> **`0x0012F0` 起是一段 LZMA,17,334 → 56,592 bytes**,指令直譯器整個在裡面。
>
> **這個坑值得記住的形狀是**:一個 `grep` 找不到東西,可以是「不在那裡」,
> 也可以是「你在找一個壓縮過的東西」。這個 repo 用了三週的後者去支撐前者。

> ⚠️ **不要用 `--no-control` 之類的方式繞過拒絕。** 這份報告的頭號結果是一個
> **「不存在」**,而一個宣稱「這裡沒有 X」的報告,如果不能在同一次執行裡證明
> 自己找得到已知存在的東西,那個宣稱值零。

### A1.6.2 kernel 自己說它用什麼 cmdline

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

**預期**:

```text
kernel: LZMA at payload+0x2808, 3,374,772 bytes, declared size MATCHES
  control Linux version          present
  control swapper                present
  control Kernel command line    ABSENT
  0x2d8590  No init found.  Try passing init= option to kernel.
  0x2f9590  console=ttyS0,38400 root=/dev/mtdblock1
```

**三件事,而第三件解釋了第二件:**

1. `0x2f9590` 是**編進 kernel 的** cmdline,**沒有 `init=`**。
2. `0x2d8590` 的 `No init found.  Try passing init= option to kernel.` 說明
   **kernel 會認 `init=`** —— 缺的完全是 loader 那一側。
3. **`Kernel command line` 這個字串不在 image 裡**,所以開機 log 永遠不會印它。
   (`A10` 的腳本會為此報一行 `FAIL`,而在這台上那是預期的。)

> ✅ **`P9-1` 反證成立,而且是 `static` 證據** —— 登記簿為它宣告的 `exit_evidence`
> 就是 `static`,所以這個等級是可採信的。三個獨立儀器:loader 的字串空間、
> kernel 的 `.rodata`、以及裝置 console 的 `?`(`A3`)。**沒有共用程式碼。**

> 💡 **仍然存在的路徑,而它零 flash 寫入**:`AUTOBURN 0` → `LOADADDR` →
> TFTP 一份改過 cmdline 的 kernel 進 RAM → `J`。成本是要能重壓一份 kernel
> (那 38 個字元的字串沒有多餘空間放 ` init=/bin/sh`,得先確認後面有沒有留白)。
> **排 W07 之後,不是這一節的事。**

---

## A1.7 模擬環境:這台自己的 binary,跑在 x86 上

| | |
|---|---|
| **層** | **T2**(要一份 dump 與 root;**不用裝置**) |
| **會不會改變裝置** | 沒有碰裝置。**但它會改 dump 的副本** —— 見下 |
| **關掉的項目** | `P3-0`、`P3-6` |
| **最後驗證** | 2026-08-17 |

**大家說 Realtek SDK 模擬不起來,理由通常是 Lexra 指令集 —— 那個理由是錯的。**
真正卡住的是 `libapmib` 要讀 `/dev/mtdblock0`,而它用 `lseek`+`read` 讀,
**所以解法是提供一個檔案**,而那個檔案就是你在 `A5`/`A3` 讀出來的 dump。

```bash
make qemu-env      # 需要 sudo
make qemu-test
```

**預期**(`qemu-env` 的正對照組是三個值,不是一個):

```text
  control ok: TELNET_ENABLED=0
  control ok: IP_ADDR=10.1.1.1
  control ok: USER_NAME="admin"
  MIB lines from the vendor binary: 2317
  positive control passed
```

> 🔴 **為什麼對照組是三個值而不是一個。** 一個布林值、一個位址、一個字串 ——
> 三種不同的解碼路徑。只驗一個布林,解碼器把整張表讀歪了也會過。

**在裡面跑一次寫入,並且看它改了 flash 的哪幾個 byte:**

```bash
sudo bash tools/qemu-env.sh diff HW_WLAN0_WSC_PIN 87654321
```

**預期**:

```text
  3 bytes changed
    0x00648a  0x39 -> 0x31
    0x00648b  0x39 -> 0x00
    0x006493  0x0d -> 0x4e   <- H601 checksum
  checksum: delta 65, expected 65 -> balances
```

> 🔴 **`0x006493` 是 `H601` 區的 8-bit checksum,而「delta 與預期相符」是這一測
> 真正的產出** —— 它不是「我改了一個值」,是**「我知道這個區塊的完整性是怎麼算的」**。

> ⚠️ **復原檔案不等於復原狀態(儀器 bug 13)。** `flash`、`boa`、`sysconf` 把 MIB
> 表快取在 **System V 共享記憶體**裡,那屬於 host kernel,活得比每一個 guest process 久。
> 只改 `HW_WLAN0_REG_DOMAIN` 的一次執行,diff 裡出現了**上一次測試的** WPS PIN
> 七個 byte。**`qemu-env.sh reset` 必須同時清檔案和 shm,而那是兩件看起來像一件的事。**

> ❌ **`boa` 在這裡服務不了請求,而那不是設定錯誤。** 它死在
> `libapmib.so+0x27dc` 的 `sh s7,0(s8)` —— 一個 16-bit 對齊陷阱,標準 MIPS I 編碼
> (opcode `0x29`,手算過)。裝置的 kernel 會修它,`qemu-user` 沒有 guest kernel 可以修。
> **換 CPU model 沒有用。** 所以 HTTP 那幾輪只能在真機上做(`A8`)。

> ⚠️ **在這裡驗 payload 的引號與跳脫,不要在真機上現想。**
> 這台的 BusyBox 1.13.4 只編了 48 個 applet,**`id` 不是其中一個** ——
> `…;id > /var/web/x.txt;#` 會建出一個空檔案,而那跟「參數被過濾掉」看起來一模一樣。
> `cat /etc/version` 才是對的 payload:輸出同時證明執行成功並指出 build。

---

## A2 🔌 把 USB 裝置交給 WSL

| | |
|---|---|
| **層** | T2(序列)/ T3(再加網卡) |
| **會不會改變裝置** | 純讀 |
| **關掉的項目** | —（這一節不關掉登記簿項目） |
| **最後驗證** | 2026-08-17 |

**Windows PowerShell**(第一次要系統管理員,之後不用):

```powershell
usbipd list
```

**預期**——找出這兩行,記下 `BUSID`:

```text
BUSID  VID:PID    DEVICE                                          STATE
1-1    10c4:ea60  Silicon Labs CP210x USB to UART Bridge (COM3)    Not shared
2-4    0bda:8153  Realtek USB GbE Family Controller                Not shared
```

第一次:

```powershell
usbipd bind --busid 1-1
usbipd bind --busid 2-4
```

每次:

```powershell
usbipd attach --wsl --busid 1-1
usbipd attach --wsl --busid 2-4
```

**驗證**(WSL):

```bash
ls -l /dev/ttyUSB0
ip -br link | grep '^enx'
```

**預期**:

```text
crw-rw---- 1 root dialout 188, 0 ... /dev/ttyUSB0
enxfc19286184c9  DOWN  fc:19:28:61:84:c9 <BROADCAST,MULTICAST>
```

> 🔴 **網卡一定要交給 WSL,而且理由不只是方便。** 如果它留在 Windows 側,
> Windows 會從這台路由器拿到 DHCP 位址,而你的網路可能整個被它接走。
> 更糟的是**測試會看起來正常**:`ping` 會通,而唯一的破綻是 `ttl=63` 不是 64。
> 那是 `PROGRESS.md` 的儀器 bug 21,2026-08-17 實際發生過。

> ⚠️ **`attach` 綁在 WSL 這個 VM 上,VM 一停裝置就退回 Windows。**
> 另開一個視窗貼這一行然後不要關:
> ```powershell
> wsl -d Ubuntu-24.04 -- sleep 14400
> ```

**做完想還給 Windows:**

```powershell
usbipd detach --busid 1-1
usbipd detach --busid 2-4
```

---

## A3 🔌 抓 bootloader

| | |
|---|---|
| **層** | T2 |
| **會不會改變裝置** | 純讀 |
| **關掉的項目** | `P0-2` |
| **最後驗證** | 2026-08-17(當天成功兩次、失敗一次,失敗原因見下) |

**接線,用眼睛檢查**(電源還沒插):

- [ ] 網路線插在 **LAN** 埠(有數字標號那幾個),**WAN 埠什麼都沒插**
- [ ] CP2102 接 UART 排針的 **pin 2 / 3 / 4**,pin 1 是絲印**三角形**那一端
- [ ] **pin 1 的 `VCC` 不要接** —— 板子自己有電,接了會對打
- [ ] CP2102 的 `RX` → 板子 `TX`(pin 2);CP2102 的 `TX` → 板子 `RX`(pin 3);`GND` → `GND`(pin 4)
- [ ] **不要按 reset 鍵** —— 它會用出廠預設蓋掉現行設定
- [ ] **電源還沒插**

**做什麼**(先跑這個,**然後**才插電):

```bash
cd /mnt/c/Users/Key20/Desktop/router
python3 -u tools/console-dump.py catch --port /dev/ttyUSB0 --window 300 -v
```

**看到這一行才 🔌 插電:**

```text
  streaming ESC.  >>> POWER THE ROUTER ON NOW <<<
```

**預期輸出:**

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

> ⚠️ **搶 bootloader 是「連續送 ESC」,它只吃一個,其餘全排在輸入緩衝區裡。**
> 所以**搶到之後第一條手打的指令必定回 `Unknown command !`**。
> 工具的 `settle()` 會先送一個裸 `\r` 清掉;手打的話先按一次 Enter。
> (儀器 bug 7)

> ❌ **`the board booted past the interrupt window` → 板子沒有真的斷電過。**
> 2026-08-17 踩過:板子當時在跑 Linux,`catch` 抓到的是執行中的 console 對 ESC
> 的回應。**先確實拔掉電源、停 2 秒、再重跑這一節。**

> ❌ **`nothing came back at all` → TX/RX 接反、port 錯、或板子沒上電。**

> ⚠️ **抓不到不要重試超過三次。** 每一次都是一次完整開機。

---

## A4 🔌 網段:把網路卡設好,並且**證明**是直連

| | |
|---|---|
| **層** | T3 |
| **會不會改變裝置** | 純讀 |
| **前置** | `A2` 已經把網卡交給 WSL |
| **關掉的項目** | `P1-1` |
| **最後驗證** | 2026-08-17 |

**這一節做兩件事,而第二件比第一件重要:給網卡一個位址,然後證明封包是直接送到
裝置的,不是繞經別的地方。**

### A4.1 找出介面名字 —— 而它不叫 `eth1`

```bash
ip -br link
```

**預期**(三行,你要的是第三行):

```text
lo               UNKNOWN        00:00:00:00:00:00 <LOOPBACK,UP,LOWER_UP>
eth0             UP             00:15:5d:xx:xx:xx <BROADCAST,MULTICAST,UP,LOWER_UP>
enxfc19286184c9  DOWN           fc:19:28:61:84:c9 <BROADCAST,MULTICAST>
```

**逐欄解釋:**

| 欄 | 意思 |
|---|---|
| `lo` | loopback,本機自己。永遠在,跟這件事無關 |
| `eth0` | **WSL 自己的虛擬網卡**,通到 Windows 和外網。**不是你要的那個** |
| `enx…` | **USB 網卡。`enx` 後面那串就是它的 MAC** —— 這是 Linux 的「可預測命名」 |
| `DOWN` | 介面還沒啟動(下一步做) |
| `LOWER_UP` | **實體線路已經協商成功**。沒有這個字代表線沒插好、或對端沒上電 |

> 🔴 **它不叫 `eth1`,而這件事害過人。** 2026-08-17 的作業單寫死了 `eth1`,結果
> `Cannot find device "eth1"` 和 `ping 10.1.1.1` **同時成立** —— 因為封包繞經
> Windows 出去了。所以**永遠用 `ip -br link` 問,不要寫死名字**。

### A4.2 啟動介面並給位址

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

**逐行解釋:**

| 行 | 做什麼 |
|---|---|
| `IF="$(…awk…)"` | 抓第一個 `enx` 開頭的介面名字存進變數。`exit` 是「只要第一個」 |
| `ip link set … up` | 啟動介面 |
| `sleep 3` | **等協商。** 乙太網路要一兩秒握手,馬上查會看到還沒 `LOWER_UP` |
| `addr flush` | **清掉舊位址。** 不清的話上一場留下的 `10.1.1.100` 會疊上去,而 `ip addr add` 會回 `File exists` |
| `addr add 10.1.1.100/24` | 給自己一個同網段的位址。`/24` = 遮罩 255.255.255.0 |

**預期**:

```text
iface = enxfc19286184c9
enxfc19286184c9  UNKNOWN        fc:19:28:61:84:c9 <BROADCAST,MULTICAST,UP,LOWER_UP>
enxfc19286184c9  UNKNOWN        10.1.1.100/24
```

> ⚠️ **`UNKNOWN` 不是錯。** 那是 `operstate`,USB 網卡常常回 `UNKNOWN` 而實際上是通的。
> **看的是 `LOWER_UP`,不是 `UP`/`UNKNOWN`。**

> ❌ **`iface = ` 是空的 → 網卡不在 WSL 裡。** 回 `A2`,或跑 `make doctor TIER=3`。

> ❌ **沒有 `LOWER_UP` → 線沒插好,或裝置沒上電,或板子停在 bootloader
> 而 Ethernet 還沒初始化。** 板子在 `<RealTek>` 時通常是有的(開機 log 會印
> `---Ethernet init Okay!`),但 `IPCONFIG` 之前它不回應 IP。

**為什麼是 `10.1.1.100`**:這台的 LAN 位址是 `10.1.1.1`(從它自己的 `COMPCS` 解出來的,
不是猜的),DHCP 池是 `10.1.1.10`–`254`。`.100` 在池子裡但不會跟前幾個租約撞。
**如果你的機器不是 `10.1.1.1`**,先解出來:

```bash
"$HOME/fwre-work/venv/bin/python" -m fwrecon compcs \
    "$HOME/fwre-work/dumps/flash-n150rt-console-1.bin" --offset 0xC000 \
    --mib "$HOME/fwre-work/extracted/unit-2018/squashfs-root/lib/libapmib.so" \
    --disclosure protect -f md | grep -iE '^\| *IP_ADDR|^\| *SUBNET'
```

### A4.3 ★ 證明是直連 —— 這一步是整節的重點

```bash
ip route get 10.1.1.1
```

**預期 —— 必須長成這樣:**

```text
10.1.1.1 dev enxfc19286184c9 src 10.1.1.100 uid 1000
    cache
```

**不可以長成這樣:**

```text
10.1.1.1 via 172.18.128.1 dev eth0 src 172.18.136.170 uid 1000
```

> 🔴 **關鍵字是 `via`。有 `via` 就是繞道,沒有 `via` 才是直連。**
>
> 為什麼這件事致命:如果網卡留在 Windows 側,Windows 會從這台路由器拿到 DHCP
> 位址,而 WSL 的封包會被**路由**過去。在那個狀態下:
>
> - **隔離確認做不了** —— 你抓到的封包是 WSL 虛擬網卡的,不是那條線上的
> - **SSDP / 廣播一定失敗** —— multicast 不跨路由器,而失敗長得跟「服務沒開」一模一樣
> - **兩個來源 IP 會被 NAT 成同一個** —— `A11.5` 的 session 測試整個失效
> - **`nmap -sS` / `-sU` 不可信** —— 你量的是那條路徑,不是裝置
>
> **而 `ping` 會通。** 唯一的破綻是 `ttl=63` 而不是 64 —— 少的那一跳就是路由器。
> 這是 `PROGRESS.md` 的儀器 bug 21,2026-08-17 真的發生過,而它是靠讀路由表發現的,
> 不是靠看 `ping` 成功。

**`tools/bench-probe.py` 每一次執行都自己查這件事**並記進 transcript,
而且對 `ssdp` 那一組**直接拒絕執行**。所以那支工具的結果可以信;手打的不一定。

### A4.4 收尾:記下起點

```bash
cat "/sys/class/net/$IF/statistics/rx_packets"
```

**預期**:`0`

> ⚠️ **這個 `0` 不是問題,是 `A6` 的基準。** 那個計數器是 **kernel 自己數的**,
> 跟 `tcpdump` 不共用程式碼 —— 所以它是「這條線到底有沒有東西進來」的第二來源。
> `A6` 會再讀一次,而**它必須變大**。

---

## A5 🔌 64 KiB 設定區快照 + IoC 預檢

| | |
|---|---|
| **層** | T2 |
| **會不會改變裝置** | **純讀**(`FLR` + `DB`,不寫一個 byte) |
| **前置** | 板子停在 `<RealTek>`(`A3`) |
| **關掉的項目** | `P0-10` · `P0-5` |
| **最後驗證** | 2026-08-17 |

**這一節每一次動手前都跑,而且它便宜到沒有藉口不做:64 KiB 約 2 分鐘,
完整的 4 MiB 是 105 分鐘 —— 而會被改的只有那 64 KiB。**

### A5.1 那 64 KiB 裡有什麼

```text
0x000000 ─┬─ bootloader stage 1(DRAM 訓練)
0x0012F0 ─┤   LZMA stage 2:指令直譯器、TFTP、SPI 型號表(見 A1.6)
0x006000 ─┼─ H601   這一台的 MAC 與射頻校準  ★ 全世界只有這一份,reset 也不還原
0x008000 ─┼─ COMPDS 出廠預設設定
0x00C000 ─┼─ COMPCS 現行設定                 ← /config.dat 服務的就是它(A8.5)
0x010000 ─┴─ w6cg  網頁資源(不在這 64 KiB 裡)
```

**所以一份 64 KiB 快照同時是三件東西:**

1. **還原點** —— 寫壞了可以寫回來(`A12`)
2. **IoC 預檢的輸入** —— 現行設定 vs 出廠預設差幾筆
3. **「上一場到現在沒被動過」的證明** —— 跟上一份逐 byte 比

### A5.2 抓

```bash
SNAP="$HOME/fwre-work/dumps/config-region-$(date +%Y%m%d-%H%M)-pre.bin"
echo "writing to: $SNAP"
python3 -u tools/console-dump.py dump --at-prompt \
        --flash 0x0 --length 0x10000 --ram 0x81000000 --chunk 16384 \
        -o "$SNAP"
```

**逐個旗標:**

| 旗標 | 值 | 意思 |
|---|---|---|
| `--at-prompt` | — | **板子已經停在 `<RealTek>`,不要再搶一次。** 沒加的話它會等你上電 |
| `--flash 0x0` | flash 位移 | 從頭開始 |
| `--length 0x10000` | 65,536 | 只要那 64 KiB |
| `--ram 0x81000000` | RAM 目標位址 | `FLR` 先把 flash 讀進 RAM,再用 `DB` 印出來 |
| `--chunk 16384` | 每次 `DB` 印多少 | 太大 → 一次錯誤重讀很貴;太小 → 往返次數多。16 KiB 是量過的平衡點 |
| `-o` | 檔名 | **檔案已存在會拒絕覆蓋**,除非 `--force` |

**預期輸出:**

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
> 進同一個 RAM 位址,比對已知的 `0b f0 00 04`(那是 bootloader 開頭的一個 `j` 指令)。
> **對不上就丟例外,不會出檔案。**
>
> 為什麼需要它:`FLR` 會問 `(Y)es , (N)o ?` 並且**把下一行整個吃掉當答案**。
> 如果那個 `Y` 沒被接受,`FLR` 根本沒生效,而接下來的 `DB` 印出來的是
> **RAM 裡上一次留下的舊資料** —— 一份格式完全正常、內容完全錯誤的 dump。
> **對照組把那件事變成一個例外,而不是一個結論。**(儀器坑,`RUNBOOK` §8.7.8)

> ⚠️ **`691 B/s` 是正常速度。** 38400 baud 的理論上限約 3.8 KB/s,而 `DB` 是
> 十六進位文字輸出(每個 byte 印成 3–4 個字元)加上往返,所以實際約 700 B/s。
> **64 KiB ≈ 95 秒。看到 2 分鐘不要以為卡住了。**

> ❌ **有 `.partial` 檔案但沒有 `.bin` → 有一塊重讀三次都沒過。**
> 工具的規則是「拼不完整就不吐檔案」。**那要查,不要繞過** ——
> 通常是線路品質或 `usbipd` 掉了。

### A5.3 跟上一份比 —— 這一步回答「有沒有人動過這台」

```bash
cmp <(head -c 65536 "$HOME/fwre-work/dumps/flash-n150rt-console-1.bin") "$SNAP" \
  && echo "IDENTICAL"
```

**預期**(如果從 8/16 的完整 dump 到現在沒有任何寫入):

```text
IDENTICAL
```

**不相同的話,先看差在哪裡再判斷:**

```bash
bash tools/config-attrib.sh \
  <(head -c 65536 "$HOME/fwre-work/dumps/flash-n150rt-console-1.bin") "$SNAP"
```

> ⚠️ **不相同不一定是壞事。** 這台從 2026-08-17 下午起,`COMPDS` 已經被
> POST 輪覆寫過(`A9`),所以跟 8/16 那份**一定不同**。
> **判準是「跟上一場收工時記下的數字相同」,不是「跟最早那份相同」。**

> ★ **而 `IDENTICAL` 這件事本身在 2026-08-17 變成了一個免費的對照組:**
> 那天 11:02 的快照與 8/16 的完整 dump 逐 byte 相同 —— **而那期間這台開過機
> 至少兩次、跑過完整的 GET 輪、還成功登入過一次。**
> 所以「開機和讀取不會改設定區」不是假設,是量出來的 ——
> 而那正是下午 POST 輪的差異可以**全部歸因**給 POST 的理由。

### A5.4 IoC 預檢

```bash
bash tools/ioc-precheck.sh "$SNAP"
```

**預期**:

```text
COMPCS: checksum_ok=True verdict=consistent ring_fill_agrees=True entries=344
COMPDS: checksum_ok=True verdict=consistent ring_fill_agrees=True entries=344

common entries: 343
differing     : 0
```

**三個欄位,而它們不是同一件事:**

| 欄位 | 誰在說話 |
|---|---|
| `checksum_ok` | **廠商自己的程式碼。** `libapmib` 的 8-bit payload checksum |
| `ring_fill_agrees` | **解碼器自己的對照組。** 用兩種不同的 LZSS 視窗初值解一次,結果要相同 —— 否則結果依賴了「沒有任何 literal 寫過」的視窗 byte |
| `verdict` | 解碼器對自己這次工作的判斷 |

> 🔴 **`differing` 這個數字不是常數。**
> 它到 2026-08-17 上午是 **4 / 343**(`CHECK_SSID_OK` · `DHCP_LEASE_TIME` ·
> `MIB_VER` · `WLAN_SSIDS`),下午的 POST 輪之後是 **0 / 343** ——
> 因為那一輪把 `COMPDS` 覆寫成 `COMPCS` 了。
>
> **判準是「跟上一場記下的數字相同」。看到不是 4 就當資安事件是錯的** ——
> 先讀 `BENCH-LOG.md` 最後一場的「燒掉了什麼」。

> ❌ **出現一筆你的紀錄裡沒有的差異 → 停,走事件處理程序。**
> 這個型號在公開的殭屍網路工具裡被點名過,而 `A7.3` 的 IoC 埠掃描是這一項的另一半。

> ❌ **`checksum_ok=False` → 停。** 那代表裝置自己也會拒絕這份 blob。
> 不要在一份廠商程式碼都不接受的資料上做任何推論。

---

## A6 🔌 隔離確認 —— 而且要帶對照組

| | |
|---|---|
| **層** | T3 |
| **會不會改變裝置** | 純讀 |
| **前置** | `A4` 完成,而且 `ip route get` 沒有 `via` |
| **關掉的項目** | `P0-4` |
| **最後驗證** | 2026-08-17 |

**這一節要證明的是:那條線上只有你和這台裝置,沒有第三個東西,而且它沒有在對外連線。**

### A6.1 為什麼這一節看起來多此一舉,而它不是

**直覺的做法是:抓 45 秒封包,零個封包 = 網段乾淨。**

**2026-08-17 就是這樣做的,而它差點被寫成結論。** 那一刻 kernel 的計數器是
`RX: 0 packets / TX: 12` —— **送得出去,收不回來。** 也就是零封包不是因為網段乾淨,
是因為**那條線根本沒在送東西給你**。

> 🔴 **「抓到零個封包」不是證據,它是兩件事的其中一件,而你分不出是哪一件:**
> (a) 網段乾淨,或 (b) 你的擷取根本沒在工作。
>
> **所以這一節主動製造已知流量。** 「封包數 > 0」就是那次擷取的**對照組** ——
> 它證明擷取是活的,零才有意義。

### A6.2 抓,而且自己製造流量

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

**逐行解釋:**

| 行 | 做什麼 |
|---|---|
| `tcpdump -n` | **不要做反解 DNS。** 不加 `-n` 的話 tcpdump 自己會發 DNS 查詢,而那正是你要找的東西之一 —— **工具會污染自己的量測** |
| `-i "$IF"` | 只聽那一張網卡 |
| `-w "$PCAP"` | 寫成檔案,不要印在螢幕上(要能重看) |
| `& TD=$!` | 丟到背景,記下 PID 等一下殺 |
| `sleep 1` | 讓 tcpdump 真的開始聽再送東西。**不等的話你自己製造的流量會漏掉** |
| `ping -c 3 -i 0.3` | 三個 ICMP,間隔 0.3 秒 —— **這就是對照組流量** |
| `curl … http://…/` | 再加一次 TCP,證明不只 ICMP 在動 |
| `sleep 12` | 留 12 秒安靜期,看有沒有**別的東西**自己冒出來 |

**預期**:

```text
rx before: 0
rx after : 16
```

### A6.3 讀那份 pcap

```bash
tshark -r "$PCAP" 2>/dev/null | wc -l
tshark -r "$PCAP" -T fields -e eth.src 2>/dev/null | sort | uniq -c
tshark -r "$PCAP" -Y dns 2>/dev/null | head
tshark -r "$PCAP" -Y 'ip.dst != 10.1.1.0/24 && ip.src != 10.1.1.0/24' 2>/dev/null | head
```

| 行 | 問什麼 |
|---|---|
| `wc -l` | **總封包數。這是對照組,必須 > 0** |
| `-T fields -e eth.src \| uniq -c` | **來源 MAC 各出現幾次。必須剛好兩個** |
| `-Y dns` | **有沒有 DNS 查詢。必須是空的** |
| `-Y 'ip.dst != …'` | **有沒有對 10.1.1.0/24 以外的流量。必須是空的** |

**預期**:

```text
16
      8 fc:19:28:61:84:c9
      8 14:4d:xx:xx:xx:xx
```
`dns` 和最後那一行**都必須沒有輸出**。

> ✅ **剛好兩個 MAC** = 你的網卡 + 裝置。第一個數字是你在 `A4` 看到的 `enx` 後面那串。

> ❌ **第三個 MAC → 停。** 網段上有別的東西。可能是:
> (a) 你插在 switch 上而不是直連 —— 拔掉,一條線直接對接;
> (b) Windows 側還有一個位址在那個網段 —— 檢查 `Get-NetIPAddress` 有沒有 `10.1.1.x`;
> (c) 真的有第三台機器 —— 那就不是隔離網段。

> ❌ **總封包數是 0 → 擷取沒在工作,不是網段乾淨。** 先看 `rx after`:
> 如果它也是 0,那條線沒在送東西給你(`A4` 的 `LOWER_UP` 再確認一次)。
> **不要把這個寫成「網段乾淨」。**

> ❌ **有 DNS 或對外流量 → WAN 埠可能插了東西,或裝置在嘗試對外連線。**
> 先確認 WAN 埠是空的。這台在 `wan_disconnect` 時會叫一個 DNS spoof helper,
> 那是登記簿 `P6-10` 的事,還沒有人看過它。

> ⚠️ **per-unit 識別碼(MAC、SSID)不要寫進 repo 裡的檔案。** 跟 W02 把 PCB 條碼
> 塗掉是同一條規則,而 `BENCH-LOG.md` 的標頭跟它自己 2026-08-17 上午那一段
> 正好互相矛盾 —— 那件事還沒決定要往哪邊收。

---

## A7 🔌 埠與服務偵察

| | |
|---|---|
| **層** | T3 |
| **會不會改變裝置** | 純讀 |
| **前置** | `A6` 通過;裝置已正常開機並服務(等 45 秒,見 `A10`) |
| **關掉的項目** | `P1-2` · `P6-11` · `P1-10` |
| **最後驗證** | 2026-08-17(上午場) |

### A7.1 掃描前先確認 web 活著 —— 這是對照組,不是禮貌

```bash
curl -s -o /dev/null -m 4 -w 'before: %{http_code}\n' http://10.1.1.1/
```

**預期**:`before: 200`

> 🔴 **為什麼一定要先做這件事。** 這是 400 MHz MIPS、32 MiB RAM 的機器。
> **一次把 `boa` 打掛的掃描,結果看起來會跟「埠都關著」一模一樣** ——
> 65,532 個 `closed`,而你會把它寫成發現。
> **掃描前後各一次,兩次都 200,`closed` 才是裝置的答案而不是你的。**

### A7.2 全 TCP

```bash
D="$HOME/fwre-work/dumps"
sudo nmap -sS -p- --reason -T3 --max-retries 2 -oA "$D/tcp" 10.1.1.1
curl -s -o /dev/null -m 4 -w 'after tcp: %{http_code}\n' http://10.1.1.1/
```

**逐個旗標:**

| 旗標 | 意思 | 為什麼是這個 |
|---|---|---|
| `-sS` | SYN 掃描(送 SYN,看 SYN/ACK,不完成三方握手) | 比 `-sT` 輕,對這台的負擔小 |
| `-p-` | **全部 65,535 個埠** | 因為預測裡有具體的埠號,而「沒掃到」和「關著」不一樣 |
| `--reason` | 印出**為什麼**判定成 open / closed | `closed (reset)` 和 `filtered (no-response)` 是不同的事實 |
| `-T3` | 時序等級 3(預設) | **不要用 `-T4`。** 見下 |
| `--max-retries 2` | 每個埠最多重試兩次 | 預設 10,在慢裝置上會拖到幾十分鐘 |
| `-oA "$D/tcp"` | 同時輸出三種格式(`.nmap` / `.gnmap` / `.xml`) | **證據要留檔,不能只留在螢幕上** |

**預期**(這台 2026-08-17 的答案):

```text
PORT      STATE SERVICE REASON
80/tcp    open  http    syn-ack ttl 64
52869/tcp open  unknown syn-ack ttl 64
52881/tcp open  unknown syn-ack ttl 64
Not shown: 65532 closed tcp ports (reset)
```

> 🔴 **不要用 `-T4`。** 在這台上 `-T4` 的併發量足以讓 `boa` 停止回應,
> 而你會得到一份「幾乎全部 closed」的結果 —— 那是你自己造成的。

> ⚠️ **`52869` 與 `52881` 不在任何一條預測裡。** 這是 2026-08-17 的實測發現:
> 預測**點名的每一項都對**(80 開、22/23/5555 關),而**它點名得太少**。
> `52869` 是 `miniigd`(UPnP SOAP),`52881` 是 `wscd`(WPS)。

> 🔴 **`52869` 是 CVE-2014-8361 的埠,而那個 CVE 在 CISA KEV 裡、有公開的武器化程式碼。**
> **這一節只做偵察。不要呼叫任何 SOAP action。**

### A7.3 重點 UDP,以及 IoC 埠

```bash
sudo nmap -sU -p 53,67,69,123,161,162,1900,5353,5555 --reason -T3 -oA "$D/udp" 10.1.1.1
curl -s -o /dev/null -m 4 -w 'after udp: %{http_code}\n' http://10.1.1.1/
sudo nmap -sT -Pn -p 19412,31412,48101,2323,60001,5555,9034,7547 --reason -oA "$D/ioc" 10.1.1.1
curl -s -o /dev/null -m 4 -w 'after ioc: %{http_code}\n' http://10.1.1.1/
```

| 旗標 | 意思 |
|---|---|
| `-sU` | UDP 掃描。**慢,所以只掃指定的九個**,不掃全部 |
| `-sT` | 完整 TCP 連線掃描(三方握手)。IoC 那一組用它,因為要確定「真的沒有東西在聽」 |
| `-Pn` | **跳過主機存活探測。** 不加的話 nmap 可能先 ping,而 ping 不通就整組跳過 |

**預期**:

```text
53/udp   open|filtered domain
67/udp   open|filtered dhcps
1900/udp open|filtered upnp
161/udp  closed        snmp
```
IoC 那八個埠 **全部 `closed`**。

> ⚠️ **`open|filtered` 不是「開著」。** UDP 沒回應時 nmap 分不出「開著但不回」
> 和「被防火牆丟掉」—— 所以它老實說兩種都可能。`53` / `67` 是 DNS 與 DHCP,
> 這台是路由器,合理。

> ❌ **IoC 那八個埠任何一個有回應 → 停,走事件處理程序。**
> 那些埠是公開殭屍網路工具用的(`2323` telnet 變體、`48101` Mirai、
> `7547` TR-069 CVE-2016-10372…)。這個型號在那些工具裡被點名過。
> **有回應不代表被入侵,但它代表你不能再把後面的量測當成乾淨裝置的量測。**

### A7.4 UPnP:banner 說的和 binary 說的不一樣

```bash
printf 'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: "ssdp:discover"\r\nMX: 2\r\nST: upnp:rootdevice\r\n\r\n' \
  | nc -u -w3 10.1.1.1 1900
```

或用工具(它會先確認你是直連,不是的話直接拒絕):

```bash
python3 tools/bench-probe.py ssdp --host 10.1.1.1 -o "$D/ssdp.json"
```

**預期**:

```text
Server: miniupnpd/1.4 UPnP/1.4
Location: http://10.1.1.1:52869/picsdesc.xml
```

**然後去 rootfs 裡找那個 binary:**

```bash
ls -l "$HOME/fwre-work/extracted/unit-2018/squashfs-root/bin/" | grep -iE 'upnp|igd'
strings -a "$HOME/fwre-work/extracted/unit-2018/squashfs-root/bin/miniigd" \
  | grep -iE 'miniupnpd|MiniIGD'
```

**預期 —— 而這是這一節最重要的一件事:**

```text
-rwxr-xr-x 1 ... 97100 ... miniigd
Server: miniupnpd/1.4 UPnP/1.4
MiniIGD %s (%s).
/etc/miniigd.conf
```

> 🔴 **rootfs 裡只有 `/bin/miniigd`,`mini_upnpd` / `miniupnpd` 這兩個 binary 不存在**
> —— 而那個 banner 字串就在 `miniigd` 自己的字串表裡。
>
> **只讀 banner 會查錯一整組 CVE。** `miniigd` 是 Realtek 的
> (CVE-2014-8361,CISA KEV);`miniupnpd` 是完全不同的專案、不同的 CVE 歷史。
> **登記簿 `P1-10` 事先就要求分辨這一點,而那才是它存在的理由。**

> ⚠️ **`nc` 在這台裝置上不存在,但你的主機上要有。** 沒有的話用上面那個工具版本。

---

## A8 🔌 HTTP 那幾輪 —— 用工具,不要手打

| | |
|---|---|
| **層** | T3 |
| **會不會改變裝置** | **純讀**(全部是 GET;POST 在 `A9`) |
| **前置** | `A4` 直連;裝置已服務 |
| **關掉的項目** | `P1-3` · `P1-5` · `P1-8` · `P2-1` · `P2-2` · `P2-3` · `P2-4` · `P2-5` · `P3-13` |
| **最後驗證** | 2026-08-17 |

### A8.1 為什麼是工具,不是 curl

**一次打錯的 POST 會讓 `boa` 死掉,然後後面 57 個端點全部回「連不上」——
而那看起來跟「端點不存在」一模一樣。** 一次手滑,57 個端點的普查變成 57 個偽陰性。

`tools/bench-probe.py` 擋掉這件事,而且它做四件手打做不到的事:

| 它做什麼 | 為什麼 |
|---|---|
| **拒絕**沒帶 `submit-url` 的 `/boafrm/` POST | 那會讓 handler `strcpy("/status.htm")` 寫進唯讀段 |
| **拒絕**參數裡有 shell 元字元 | 注入是 W06 的事,而且要在回復演練之後 |
| **每 5–20 個請求重跑對照組**,而且會重試 | 單一 process 的 `boa` 忙起來跟死掉長得一樣 |
| 端點清單從**committed 的 Ghidra 報告**讀 | 不是寫死的副本,所以不會跟報告漂移 |

### A8.2 五個 group,一次一個

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
| `control` | 裝置回不回應、是不是直連 | —(每一組自己也會跑) |
| `fingerprint` | `Server:` 標頭、404 的形狀、`/boafrm/` vs `/goform/` | `P1-3` `P1-8` |
| `gate` | 授權閘門的實際涵蓋範圍,約 50 種 URI 形狀 | `P2-1` `P2-2` `P2-3` `P2-4` `P2-5` |
| `writes` | 寫入類 handler 有沒有被門特別對待(**GET only**) | `P3-13` |
| `endpoints` | 57 + 3 + 4 個名字(GET 模式) | `P1-5` |
| `ssdp` | UPnP,單播與多播 | `P1-10` |

> ❌ **`-o` 沒給就等於沒做。** 工具會提醒你:
> `(no --output: nothing was recorded. A probe whose response is not kept is not evidence)`

**`control` 的預期輸出:**

```text
   200  control                                  408B  Boa/0.94.14rc21
  route: 10.1.1.1 is directly attached on enxfc19286184c9
```

> ❌ **第二行出現 `⚠ … is reached via …` → 回 `A4`。** 那一整組結果會是那條路徑的
> 量測,不是裝置的。

### A8.3 ★ 閘門的四行指紋 —— 記住它們,後面每一個判讀都靠它

```text
不存在的 .htm,不含豁免子字串   302 → login.htm    門跑了,擋掉
不存在的 .htm,含豁免子字串     404                門沒跑,落到檔案層
/boafrm/formX                   302 → home.htm     門沒跑(GET 走不到 handleForm)
/boafrm/formX.htm               302 → login.htm    門跑了
```

**怎麼從 JSON 把它撈出來:**

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

**這台的機制(2026-08-17 量到的):閘門只在 URI 含 `.htm` 或 `.asp` 時才跑,
然後對照一份 11 個字串的豁免清單,而比對是「路徑裡**含有**」——不錨定。**

出貨的 76 個 `.htm` 裡,**7 個未認證可取**:

```text
index · login · status · countDownPage · countDownPageWizard   ← 清單上直接列的
wan_status · Connect_status                                    ← 只因為含有 "status.htm"
```

> ★ **最後兩個不在任何一份清單上,而它們免認證。** 那就是「不錨定」的真正效果 ——
> 不是一個繞過工具,是**一個比程式碼寫出來的名單更大的豁免集合**。

> 🔴 **而它不是繞過,理由比「試了沒用」精確得多:豁免比對和開檔用的是同一個
> 正規化路徑。** 任何裝飾到足以取得豁免的路徑,伺服器都開不到:
>
> ```text
> /password.htm?x=status.htm   302 → login.htm   query 被切掉了
> /password.htm;status.htm     404               豁免生效了,但沒有這個檔
> /login.htm/../password.htm   302 → login.htm   正規化在閘門之前
> ```
>
> **第二行同時證明兩件事:豁免真的生效了,而且繞不過去。**

> 🔴 **測繞過的時候目標必須是真的被擋的頁面。**
> 2026-08-17 第一輪把十三種變形全打在 `/status.htm` 上 —— 而它在豁免清單上、
> **本來就回 200**。那等於拿一扇沒鎖的門測開鎖技巧。
> 這台真的被擋的:`/password.htm`、`/tcpiplan.htm`、`/upload.htm`。

### A8.4 `writes` group:回答一個問題而不執行任何 handler

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

**預期**:

```text
('quiet', 'bare')      {'302 -> home.htm': 22}
('quiet', 'with .htm') {'302 -> login.htm': 22}
('spawns', 'bare')     {'302 -> home.htm': 35}
('spawns', 'with .htm'){'302 -> login.htm': 34, '404 -> ': 1}
```

> ✅ **寫入類與讀取類完全相同 → `P3-13` 的反證條件不成立,預測成立。**

> ★ **那個唯一的 `404` 是 `formLogin.htm`,而它是這一節最漂亮的一格。**
> `formLogin` 也在閘門的豁免清單上,所以路徑含有它就豁免 → 門不跑 →
> 落到檔案層 → 沒有這個檔 → 404。
> **那是閘門模型預測的第 57 個資料點,而它沒有被擬合過。**

> ⚠️ **`quiet` / `spawns` 這個分類是代理指標,工具自己也這樣講。**
> 它分的是「有沒有呼叫 `system()`/`execl()`」,**不是「有沒有寫設定」** ——
> 所以它把 `formPasswordSetup` 判成 `quiet`(它只呼叫 `strcpy`),而那顯然會寫。
> **所以這一組也單獨探測測試自己點名的三個端點**,而且**表裡沒有那三個就拒絕執行**。

### A8.5-預告 `endpoints` 這一組在 GET 模式下分不出東西

**57 個 `root_form[]` 名字的 GET 全部回 `302 / 131B → home.htm`,
和一個不存在的名字無法區分** —— 因為 `translate_uri` 在 `handleForm` 之前就轉走了。

**但有兩個例外,而它們是真的端點:**

```text
formOpdRedirect   302 / 535B → /opmode1.htm
formWanRedirect   302 / 536B
formWlanRedirect2 302 / 131B     ← 與不存在的名字無異
```

> ★ **那兩個回應與其他所有路徑都不同,所以它們被處理了 —— 而 Ghidra 讀出來的
> 57 筆不含它們。** 追下去發現它們由 `init_get`(`0x00407b7c`)處理,不是
> `handleForm`。**所以 `root_form[]` 的 57 不是少,它對 `handleForm` 是完整的;
> 另外有一條更早的路徑。** 而 `formWlanRedirect2` 沒有任何函式引用它 ——
> 字串在 `.rodata` 裡,但是死的。
>
> **三個來源一致:字串在、無人引用、裝置當它不存在。**

**要真正分辨端點存在與否必須 POST,那是 `A9`。**

---

## A8.5 🔌 ★ `GET /config.dat` —— 一條四層都指得出來的證據鏈

| | |
|---|---|
| **層** | T3(取檔)+ T2(比對 flash) |
| **會不會改變裝置** | **純讀** |
| **前置** | `A4` 網段;`A5` 或 `A3` 讀出來的 dump |
| **關掉的項目** | `P10-1` |
| **最後驗證** | 2026-08-17 |

**這一節是這個專案最值得單獨講的一個結果,而它只有三行命令。**

一個**未認證**的 `GET /config.dat` 拿回 7,490 bytes,而那 7,490 bytes 的 SHA-256
**跟你用 bootloader 從 SPI flash `0xC000` 讀出來的那 7,490 bytes 完全相同**。

### A8.5.1 取檔(未認證)

```bash
D="$HOME/fwre-work/dumps"
curl -s -D "$D/config-dat.headers" -o "$D/config-dat.bin" http://10.1.1.1/config.dat
head -3 "$D/config-dat.headers"
printf 'bytes: %s\n' "$(stat -c %s "$D/config-dat.bin")"
head -c 6 "$D/config-dat.bin"; echo
```

**預期**:

```text
HTTP/1.1 200 OK
Date: ...
Server: Boa/0.94.14rc21
bytes: 7490
COMPCS
```

> 🔴 **注意這裡沒有任何憑證。** `/config.dat` 的路徑裡沒有 `.htm` 也沒有 `.asp`,
> 所以授權閘門**根本不跑**(`A8` 的指紋那四行)。而 `boa` 在**啟動時就建立**這個檔案 ——
> 不需要任何人 POST 任何東西:
>
> ```text
> 401 lseek(3,49152,SEEK_SET) = 49152        <- 0xC000, COMPCS
> 401 read(3,0x490018,7490) = 7490
> 401 open("/web/config.dat",O_RDWR|O_CREAT|O_TRUNC) = 3
> ```
>
> (那三行是 `A1.7` 的模擬環境用 `-strace` 抓到的。)**所以這條鏈比這個 repo
> 原本假設的短一步。**

### A8.5.2 跟 flash 比,而這一步是整節的重點

```bash
D="$HOME/fwre-work/dumps"
echo "served :  $(sha256sum "$D/config-dat.bin" | cut -c1-32)"
echo "flash  :  $(dd if="$D/flash-n150rt-console-1.bin" bs=1 skip=49152 count=7490 \
                  status=none | sha256sum | cut -c1-32)"
cmp <(dd if="$D/flash-n150rt-console-1.bin" bs=1 skip=49152 count=7490 status=none) \
    "$D/config-dat.bin" && echo "IDENTICAL"
```

**預期**(前 32 個字元一致,而 `cmp` 是真正的判據):

```text
served :  e09cbf8428aa15944ed75939e79820c5
flash  :  e09cbf8428aa15944ed75939e79820c5
IDENTICAL
```

> 🔴 **`49152` 就是 `0xC000`,而它是十進位** —— `dd` 的 `skip` 不吃 `0x`。
> 這台已經用兩種進位制咬過人一次(`FLR` 的長度十六進位、`DB` 的長度十進位),
> 所以這裡寫成十進位並且把換算寫出來。

> ❌ **`cmp` 說不同 → 停,而且這是好消息不是壞消息。** 兩種可能,都要查清楚:
> (a) 你的 dump 是在改過設定之後讀的,而 `config.dat` 是現況 —— 重讀一次 `A5` 的快照;
> (b) 範圍不對 —— `COMPCS` 的長度在 header 裡,不一定是 7,490。
> **不要調整範圍去湊到相同。** 先確認長度從哪裡來。

### A8.5.3 解出裡面的密碼,然後拿它去認證

```bash
"$HOME/fwre-work/venv/bin/python" -m fwrecon compcs "$D/config-dat.bin" \
    --mib "$HOME/fwre-work/extracted/unit-2018/squashfs-root/lib/libapmib.so" \
    --disclosure reveal -f md | grep -iE 'USER_NAME|USER_PASSWORD'
```

然後拿那組值去跑 `A11.5` —— **它會通**。

### 為什麼這一節值得單獨存在

**這條鏈的每一環都能單獨指出來,而且用的是不同的儀器:**

| 環 | 誰量的 | 走哪條路 |
|---|---|---|
| HTTP 回應 7,490 bytes | `curl` | 乙太網路 |
| flash `0xC000` 起 7,490 bytes | bootloader 的 `FLR` + `DB` | 序列埠 |
| 那份 blob 裡的 `USER_PASSWORD` | `fwrecon compcs` | LZSS 解碼 + `libapmib` 的 checksum |
| 那組明文通過認證 | `curl -u` | 乙太網路 |

> ★ **而第二環順手關掉一個從 W02 就開著的缺口。** W02 說「沒有第二個獨立儀器讀過
> 這顆 flash」——每一個 byte 都是經 bootloader 的 `FLR` 來的,所以一個系統性錯誤的
> `FLR` 會是隱形的。
>
> 這一節裡,`boa` 經 **kernel 的 MTD 驅動**、走**乙太網路**讀了同一塊區域;
> W02 經 **bootloader 的 SPI 常式**、走 **UART**。
> **兩條不共用任何程式碼的路徑,同一組 bytes。**
> 那是**佐證(corroboration)**,不是**重複(repeatability)** —— 而那一欄從
> 2026-08-16 起一直是空的。**範圍是 `0xC000`–`0xD142`,不是整顆晶片。**

> ⚠️ **這是 CVE-2019-19822(未認證設定外洩)加 CVE-2019-19823(明文儲存),
> 兩個都是 2019 年公開的。** 這一節重現的是已公開的東西,不是新發現 ——
> 這個專案自己的部分是**那條佐證鏈**,不是那個漏洞。

---

## A9 🔌 POST 輪 —— **這一節會改變裝置的設定**

| | |
|---|---|
| **層** | T3 |
| **會不會改變裝置** | **改設定。而且它已經兩次把 web server 弄掉。** |
| **前置** | **`A5` 的快照必須已經抓好**;`A8` 已經跑過(GET 那半邊先做) |
| **關掉的項目** | `P1-4` · `P1-5` · `P1-6` |
| **最後驗證** | 2026-08-17(跑兩次,兩次都在第 45 個附近把 `boa` 弄掉) |

> ## 🔴 跑之前把這一整節讀完
>
> **POST 到 form handler 就是執行它。** 而參數全部缺席的 handler **不會什麼都不做** ——
> accessor 會回它的預設值,而 handler 把那個預設值寫進去。
>
> 這一節做完你會有:57 個端點的存在性答案、W05 DoD 最後一格、
> **以及一個未認證的可用性缺陷的量測**。代價是這台的設定會變,而那是計畫內的。

### A9.1 為什麼有 13 個端點不會被打

```bash
python3 - <<'PY'
import importlib.util, pathlib
spec = importlib.util.spec_from_file_location("bp", pathlib.Path("tools/bench-probe.py"))
bp = importlib.util.module_from_spec(spec); spec.loader.exec_module(bp)
for name, why in sorted(bp.HAZARDOUS.items()):
    print(f"  {name:<22} {why}")
PY
```

**四種最壞情況,而第一種最陰險:**

| handler | 打下去會怎樣 |
|---|---|
| `formTcpipSetup` / `formWanTcpipSetup` / `formVlan` | **LAN 位址或 VLAN 被改 → 掃到一半失去這台**,而後面每個端點都回「連不上」,看起來跟「端點不存在」一模一樣 —— **正是這支工具當初為了 `submit-url` 而生的那個失效模式,換一件衣服** |
| `formPasswordSetup` | 管理密碼被改 → **`A8.5` 和 `A11.5` 的 CVE-2019-19823 端到端鏈當場毀掉**,而那是這個專案最硬的一條證據 |
| `formUpload` / `formUploadConfig` | 韌體 / 設定上傳路徑。`boa` 裡有 `DownloadRFW` —— **這是會磚的那一類** |
| `formOpMode*` / `formWizard` / `formReboot*` | 運作模式變更,多半接重開機 |

> ⚠️ **設定被改是可以歸因也可以還原的;失去 LAN 位址、失去密碼、進入韌體上傳路徑不是。**
> 那是這份清單的分界線,不是「危險程度」。

> 💡 **真的要打其中一個,要第二個旗標 `--allow-destructive`,而它會被記進 transcript。**
> 「我接受設定會變」和「請把 LAN 位址從我手上拿走」是兩個不同的同意。

### A9.2 打

```bash
python3 tools/bench-probe.py endpoints --host 10.1.1.1 --allow-post \
        -o "$HOME/fwre-work/dumps/endpoints-post.json"
```

**第一行輸出就是拒絕清單 —— 它出現在任何結果之前,是刻意的:**

```text
  note  13 of 64 endpoints will not be POSTed: formTcpipSetup, formPasswordSetup,
        formUpload, formVlan, formWanTcpipSetup, formOpMode, formOpMode1,
        formOpMode2, formWizard, formRebootCheck, formSaveConfig,
        formUploadConfig, formRebootSchedule
```

> 🔴 **一份覆蓋 44 / 57 而不說的掃描,讀起來就像一份完整的普查。**
> 所以名字和數量寫在第一筆紀錄裡,讀者先遇到缺口,才遇到結論。

**每一個 POST 之後,工具會等到伺服器再度回應,並把等待時間記成那個端點的停滯時長。**
那不是繞過障礙,**那就是量測**。

**已知會發生的事(2026-08-17 兩次一致):**

```text
送出 POST 34–36 個   有回應 31–32   零個 404
狀態碼: 200 ×4 · 302 ×27–28
302 去向: msg.htm ×13 · status.htm ×11–12 · countDownPage.htm ×2 · login.htm ×1
最慢: formPortFw 9650ms · formPocketWizard 6359ms
      formWlanSetup / formRoute / formSysLog 各 ~6008ms
約第 45 個之後 -> control failed ... ConnectionRefusedError
```

### A9.3 ★ 那個 `ConnectionRefusedError` 不是掃描失敗,是結果

> 🔴 **不帶任何參數的未認證 POST,佔住這台唯一的 web server 4.7–9.7 秒。**
> `boa` 在這台是**單一 process**(`boa: starting server pid=350, port 80`),
> handler 呼叫 `system()` / `execl()` 期間它不回到 accept 迴圈,
> backlog 滿了之後新連線被**拒絕**。
>
> 約 45 個連續請求讓它徹底停止服務,**兩次都是**。而且:
>
> - `ping` **全程正常** —— kernel 活著,只有 `boa` 不見了
> - console **一行訊息都沒有** —— 沒有 oops,什麼都沒有
> - **20 分鐘後 `boa` 仍然沒有回來** —— `rcS` 是一次性啟動它的,不是 respawn
>
> **斷電重開即復原。**

> ⚠️ **這與 `P4-1` 不是同一條。** `P4-1` 是**不帶** `submit-url`、往唯讀段 `strcpy`;
> 這一條**帶**了 `submit-url`,是一個完全合法的請求。
> **分類與影響評估留給 W06/W07**,`docs/disclosure.md` 的 `D-9` 記了一筆。

**中止之後 transcript 仍然會寫出來**(2026-08-17 之前不會 —— 儀器 bug 20),
而它會印出最慢的五個請求:

```text
wrote .../endpoints-post.json  (46 requests, run STOPPED)

  slowest requests before the stop:
       9650 ms  POST /boafrm/formPortFw
       6359 ms  POST /boafrm/formPocketWizard
```

### A9.4 ★ `formSysCmd` 答了,而且可證明它沒有執行任何東西

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

**預期**:

```text
302  10ms  -> http://10.1.1.1/status.htm
```

**這一格關掉 W05 DoD 的最後一項(W06 目標的「可達性已知」),而且它什麼都沒執行 ——
那不是我的保證,是 handler 自己的程式碼:**

```c
cmd = req_get_cstream_var(req, "sysCmd", "");
if (*cmd != '\0') {              /* <- sysCmd 缺席,所以這裡是 false */
    snprintf(buf, 100, "%s 2>&1 > %s", cmd, "/tmp/syscmd.log");
    system(buf);                 /* <- 根本沒被呼叫 */
}
send_redirect_perm(req, submit_url);
```

> 🔴 **「可達性」和「概念驗證」是兩件事,而把它們混為一談會讓 DoD 因為一個
> 不存在的理由開著。** 一個不帶 `sysCmd` 的 POST 證明端點可達且未認證;
> 一個**帶命令**的 POST 才是 PoC —— 那是 `P3-3`,W06 的,而且要在
> `docs/disclosure.md` 說明狀態之後。

### A9.5 收尾:再抓一份快照,然後歸因

```bash
# 1) 回 A3 搶 bootloader（要斷電重開），然後：
SNAP2="$HOME/fwre-work/dumps/config-region-$(date +%Y%m%d-%H%M)-post.bin"
python3 -u tools/console-dump.py dump --at-prompt \
        --flash 0x0 --length 0x10000 --ram 0x81000000 --chunk 16384 -o "$SNAP2"
# 2) 逐欄位歸因
bash tools/config-attrib.sh "$HOME/fwre-work/dumps/"*-pre.bin "$SNAP2"
```

**預期 —— 而 2026-08-17 的答案有一半不在任何人的預測裡:**

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

> 🔴 **`COMPDS` 動了,而它是出廠預設區。** 那 23 欄 = 同樣的 19 欄
> **加上原本區分兩區的 4 欄,而且每一欄都移到 `COMPCS` 的值**。
> 兩區現在 343 個共同欄位完全相同。
>
> **所以:一次未認證的設定寫入,同時把出廠預設區覆蓋掉。**
> 在這個 build 上,**「恢復原廠設定」還原的是最後被寫進去的那一份** ——
> reset 按鈕不是復原路徑。唯一的復原是從裝置外的副本重寫(`A12`)。

> ✅ **`H601` UNCHANGED 是這裡最重要的一行。** 那是這一台的 MAC 與射頻校準,
> 全世界只有這一份,而且 reset 不還原它。**每一次歸因都先看那一行。**

> ⚠️ **沒有一個危險旗標被打開**(2026-08-17):`SSH_ENABLED`、`UPNP_ENABLED`、
> `PING_WAN_ACCESS_ENABLED` 和三個 `VPN_PASSTHRU_*` 全部 1 → 0。
> **但 `NOTICE_ENABLED` 變成 208** —— 一個布林欄位裝了 208,
> 代表某個 handler 把它 accessor 對「參數缺席」回的值寫了進去,而那既不是 0 也不是 1。
> **那是一條線索,不是結論。**

---

## A10 🔌 冷開機計時(一次上電餵三項)

| | |
|---|---|
| **層** | T3 |
| **會不會改變裝置** | 純讀 |
| **前置** | 板子**斷電**;`A4` 的網段已設好;console 沒有被別的程式佔用 |
| **關掉的項目** | `P1-12` |
| **最後驗證** | 2026-08-17 |

**一次完整的上電同時交付三樣東西**,所以不要為它們分三次開機:

1. `P1-12` —— 上電到 web 可服務的秒數
2. `P9-1` 的動態半 —— kernel 印(或不印)什麼 cmdline
3. 一份帶時間戳的完整開機 log,之後任何問題都可以回頭查

### A10.1 跑

```bash
bash tools/coldboot-timing.sh /dev/ttyUSB0 10.1.1.1 "$HOME/fwre-work/dumps"
```

**看到這一行才 🔌 插電**(這次**不要**送 ESC,讓它正常開機):

```text
  ==>   armed.  console -> .../coldboot-…-log
  ==>           http    -> .../coldboot-…-http

        >>> POWER THE ROUTER ON NOW <<<   (no ESC; let it boot)
```

**為什麼要一支腳本而不是兩個終端機:**

| 它做什麼 | 為什麼手做不到 |
|---|---|
| console 每一行蓋一個 `date +%s.%N` | picocom **沒有行內時間戳**,而 `ts` 不是每台機器都有 |
| HTTP 用 `until curl` 硬輪詢,`-m 1` | 沒有 `-m 1` 的話一個卡住的 connect 會吞掉「伺服器起來」那一刻 |
| **兩半用同一個時鐘** | 兩個終端機各自的「我按下 Enter 的時間」不能相減 |
| t=0 取 **console 第一行的時間戳** | 從腳本啟動算,量到的是**你的反應時間** |

### A10.2 讀結果

**預期**:

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

**這台的分段(2026-08-17)**:

```text
+0.00  第一個 console 字元
+0.61  ---RealTek(RTL8196E) v1.3 (400MHz)
+5.84  Jump to image start=0x80500000
+6.91  Uncompressing Linux... done, booting the kernel.
+14.02 init started: BusyBox v1.13.4
+32.50 boa: starting server pid=350, port 80
+38.76 ★ 第一個 HTTP 200
```

> 🔴 **`boa` 印出自己啟動之後,還有 6.26 秒不能服務。**
> 那段時間它在做 `flash extr /web` —— 把 143 個檔案從 flash 解到 ramfs。
> **所以「console 上看到 boa 啟動」不等於「可以開始掃描」。**

> 🔴 **預測是「< 40 秒」,量到 38.76,餘裕只有 1.24 秒 —— 而 t=0 是第一個
> console 字元,不是通電瞬間。** 通電到第一個字元那段沒有量,所以 **38.76 是下界**。
>
> 反證條件寫的是「**明顯**超過 40 秒」,38.76 不是,所以判成立 ——
> **不可以因為餘裕太薄就事後改標準,那正是登記簿要防的事。**
> 但這一項的用途是當「服務沒回應」判定的基準線,**所以可用的形式是「等 45 秒」**,
> 不是「小於 40 秒成立」。

> ⚠️ **那個 `FAIL  the kernel printed no 'Kernel command line:'` 在這台上是預期的,
> 不是你的擷取漏了。** `A1.6.2` 解出的 kernel 裡**根本沒有這個字串** ——
> 所以它永遠印不出來。腳本報 `FAIL` 是對的(它不該假設這台特殊),
> 而**「image 裡沒有那個字串」正是解釋 console 為什麼沒印的那個獨立來源**。

> ⚠️ **也沒有 `Linux version`。** 那個字串**在** image 裡(`A1.6.2` 的對照組會證明),
> 但沒印出來 —— 早期 printk 在這個 build 上是關的。
> **兩件事不同:一個是字串不存在,一個是存在但沒印。** 分清楚。

### A10.3 手做的版本(腳本壞了的時候)

```bash
# 終端機 1:帶時間戳的 console
stty -F /dev/ttyUSB0 38400 cs8 -cstopb -parenb -crtscts -ixon -ixoff raw -echo
while IFS= read -r line; do printf '%s %s\n' "$(date +%s.%N)" "$line"; done \
  < /dev/ttyUSB0 | tee "$HOME/fwre-work/dumps/coldboot-manual.log"

# 終端機 2:輪詢(先跑這個,再插電)
until curl -s -o /dev/null -m 1 http://10.1.1.1/; do sleep 0.2; done
date +%s.%N
```

**然後把終端機 2 印的那個數字,減掉終端機 1 log 第一行的數字。**

> ⚠️ **`stty` 的那一長串不是裝飾。** `-echo` 沒關的話你送的字元會被回傳,
> log 裡會出現重複;`-ixon -ixoff` 沒關的話 `0x11`/`0x13` 這兩個 byte 會被
> 當成流量控制吃掉 —— 而 flash 裡到處都是那兩個 byte。

---

## A11 🔌 救援路徑 —— 非破壞性上限

| | |
|---|---|
| **層** | T3 |
| **會不會改變裝置** | 純讀 **只要你不上傳任何東西**。`AUTOBURN` 是 RAM 變數,斷電就沒 |
| **前置** | 板子停在 `<RealTek>`;`A4` 的網段已設好 |
| **關掉的項目** | `P9-3` |
| **最後驗證** | 2026-08-17 |

```bash
python3 -u tools/console-dump.py rescue --at-prompt --ip 10.1.1.1 \
        -o "$HOME/fwre-work/dumps/rescue.json"
```

**預期**:

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

**驗證**(主機端):

```bash
IF="$(ip -br link | awk '/^enx/{print $1; exit}')"
ping -c 3 -W 2 10.1.1.1
ip neigh show 10.1.1.1
cat "/sys/class/net/$IF/statistics/rx_packets"
```

**預期 —— 而它跟直覺相反:**

```text
3 packets transmitted, 0 received, 100% packet loss
10.1.1.1 dev enx… lladdr 56:0a:01:01:01:e8 REACHABLE
1
```

> 🔴 **`ping` 收 0 是正常的,不是失敗。** loader 的堆疊只做 ARP + UDP/TFTP,
> **沒有義務實作 ICMP**。成功的判據是 **`ip neigh` 是 `REACHABLE`**
> 加上 **`rx_packets` 從 0 變 1** —— 那是兩個不共用程式碼的來源。
>
> 而那個 MAC(`56:0a:01:01:01:e8`)**不是網卡燒錄的位址**:
> `0a 01 01 01` 就是 `10.1.1.1`,loader 從你給的 IP 合成一個出來。
> **2026-08-17 我把「ping 有回應且 MAC 是這台」寫成成功條件,兩半都錯。**

> 🔴 **`AUTOBURN 0` 一定要在 `IPCONFIG` 之前。** 順序反過來,網路一起來就有一個
> autoburn 狀態未知的 TFTP 伺服器在聽。工具強制這個順序,而且**它只送得出 `0`**。

> ⚠️ **`AUTOBURN: 0`(有冒號)會回 `Unknown command !`** —— `?` 印的說明文字**不是語法**。
> loader 的字串表把指令 token 和說明行分開存。工具會依序試候選形式並印出哪一個成立。

> ❌ **這一節結束後拔電重開。** 不要從 `IPCONFIG` 過的狀態直接 `J` 或繼續開機。

---

## A11.5 🔌 憑證與 session —— 兩個來源位址

| | |
|---|---|
| **層** | T3 |
| **會不會改變裝置** | **純讀。**登入一次不寫任何東西(這個 build 沒有 session 可寫) |
| **前置** | `A4` 的網段已設好;密碼已從 flash 解出來 |
| **關掉的項目** | `P2-7` · `P2-8` |
| **最後驗證** | 2026-08-17 |

**密碼不是猜的,是從你自己的 flash 解出來的** ——
`USER_NAME` / `USER_PASSWORD`,明文,兩個獨立來源(`fwrecon compcs`,以及廠商自己的
`flash get`)。所以登入成功是**在自己的機器上把 CVE-2019-19823 端到端走完**。

```bash
# 從你的快照解出憑證。--disclosure protect 會遮掉,要看明文才加 reveal
"$HOME/fwre-work/venv/bin/python" -m fwrecon compcs \
    "$HOME/fwre-work/dumps/flash-n150rt-console-1.bin" --offset 0xC000 \
    --mib "$HOME/fwre-work/extracted/unit-2018/squashfs-root/lib/libapmib.so" \
    --disclosure reveal -f md | grep -iE 'USER_NAME|USER_PASSWORD'
```

**不帶憑證 / 帶憑證 / 帶錯的,三個一起打,才有對照組:**

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

**預期**:

```text
none  HTTP/1.1 302 Found | Location: http://10.1.1.1/login.htm |
good  HTTP/1.1 200 OK |
bad   HTTP/1.1 302 Found | Location: http://10.1.1.1/login.htm |
```

> 🔴 **`Set-Cookie` 一行都不會出現,而那是這一測最重要的輸出。**
> 這個 build **沒有 session**:授權是每一個請求各自的 HTTP Basic。
> 不是 2015 的 `AUTHG_IP_ADDR`、不是 2020 的五格表、**也不是反組譯指到的那個全域**。

**session 模型 —— 用第二個來源位址,而這一測不必再讀一行組語:**

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

**預期 —— 成功之後同一個位址不帶憑證仍然被擋,那就是「沒有 session」的證據:**

```text
10.1.1.100 with    200
10.1.1.100 without 302
10.1.1.101 with    200
10.1.1.101 without 302
```

**沒有帳號鎖定 —— 這一項要真的跑完,不要跑三次就下結論:**

```bash
for i in $(seq 1 50); do
  curl -s -o /dev/null -m 6 -u "$U:wrong$i" http://10.1.1.1/password.htm
done
printf 'after 50 wrong, the 51st correct one: '
curl -s -o /dev/null -w '%{http_code}\n' -m 6 -u "$U:$P" http://10.1.1.1/password.htm
```

**預期**:`200`。**五十次錯誤之後第五十一次正確的仍然通** = 沒有計數器、沒有鎖定。

> ⚠️ **「沒有 session」不等於「沒有 CSRF」。** 瀏覽器會自動重送快取的 Basic 憑證,
> 所以跨站面是靠另一個機制活著的。這是推論,不是這一測量到的東西。

> ❌ **`good` 那一行不是 200 → 停,不要重試。** 要嘛解碼器錯了,要嘛這台被改過密碼。
> 回去查 `fwrecon compcs` 的輸出,不要在裝置上試別的密碼。

---

## A12 🔌🔴 寫 flash(`FLW`)—— **唯一不可逆的一節**

| | |
|---|---|
| **層** | T2 |
| **會不會改變裝置** | **不可逆** |
| **前置** | **兩份 dump 的雜湊都對過**;`A5` 的快照已抓 |
| **關掉的項目** | `P0-3` |
| **最後驗證** | 2026-08-17(演練於 `0x3F0000`;磁區語意的判別讀在同日下午) |

> ## 🔴 動手前的四條規矩
>
> 1. **每一行先看完,再貼。不准現打。** 這台已經教過一課:兩個相鄰指令用兩種
>    進位制(`FLR` 的長度是**十六進位**,`DB` 的長度是**十進位**)。
>    **`FLW` 的參數順序打錯 = 把測試樣式寫進 kernel。**
> 2. **只碰你事先確認過是空的那個位址。** 不要「順便試試看 `0x350000`」。
> 3. **`tools/console-dump.py` 送不出 `FLW`**(它的 `FORBIDDEN` 擋掉
>    `FLW`/`EB`/`EW`/`J `)。**這是刻意的:寫入指令由讀過它的人親手打,不由腳本發。**
>    所以這一節用 `picocom`。
>    (`AUTOBURN` 是唯一的例外,見 `A11` —— 因為擋掉它反而更危險。)
> 4. **每一步看到預期輸出才准下一步。** 對不上就停,填紀錄卡,回報。

**開始之前,先讓機器確認安全網在:**

```bash
make doctor TIER=2
```

必須看到 `two independent reads agree — there is a safety net`。

> ❌ **只有一份 dump,或雜湊不符 → 不要寫。** 那是這台的唯一備份。

### 為什麼 `0x3F0000` 是安全的演練標的

W02 的完整 dump 證明 **`0x350000` 到 partition 結尾整段是 `FF`(已抹除)**,
沒有任何東西讀它。映像本體結束在 `0x34A041`(3.29 MiB)。

### 開 picocom

```bash
picocom -b 38400 --logfile "$HOME/fwre-work/dumps/flw-$(date +%Y%m%d-%H%M).log" /dev/ttyUSB0
```

**離開 picocom 是 `Ctrl-A` 然後 `Ctrl-X`。先記住,等一下會用到。**

> 🔴 **不要加 `--omap crlf`。** picocom 的 `crlf` 是「把 CR 換成 LF」,不是
> 「CR 後面補 LF」,送出去的行尾會變成裸 `LF`,而這台的 bootloader 收 `CR`。
> 更糟的是**任何多送的一個換行都會被 `FLR` 的 `(Y)es , (N)o ?` 吃掉當答案** ——
> 代價是拿到一份格式完全正常、內容是 RAM 舊值的 dump。**維持預設,一個 map 都不要加。**

> 💡 **讀取那半邊可以不用手打。** `tools/console-dump.py dump --at-prompt …`
> 會自己處理 `Y` 提示、驗證回應、而且**先跑一個正對照組**(見 `A12` 末)。
> 它只是送不出 `EB` 和 `FLW`。所以兩種做法:
> **(a) 全程 picocom 手打** —— 人會等提示,陷阱咬不到人;
> **(b) 讀取用工具、寫入用 picocom** —— 要換手,但讀取那半邊有機器把關。
> **兩種都可以。不要混著半途改。**

按一次 **Enter**,應該看到乾淨的 `<RealTek>`。

---

### Step 1 — 確認目標區真的是空的(唯讀)

```text
FLR 80520000 3F0000 100
Y
DB 80520000 256
```

**預期**:`Flash Read Successed!`,然後**整片 `ff`**,16 行,每行 16 個 byte。

> ❌ **不是整片 `ff` → 停。** 那裡有東西,而換位址之前要先知道那是什麼。

### Step 2 — 在 RAM 裡放樣式,並且確認它真的進去了

```text
EB 80530000 DE AD BE EF DE AD BE EF
DB 80530000 8
```

**預期**:`de ad be ef de ad be ef`

> ✅ **`EB` 一次吃多個 byte:2026-08-17 實測可以。**(`?` 的說明寫了 `...`,
> 但在那之前沒有人這樣送過,`RUNBOOK §8.9` 把它列為「未實測」。)
> **如果 `DB` 讀回來只有第一個 byte 對**,就是一次只吃一個,改成八行
> `EB 80530000 DE` / `EB 80530001 AD` / … —— 而那是一條要記下來的裝置事實,不是失敗。

### Step 3 — 寫入(★ 第一個不可逆的動作)

```text
FLW 3F0000 80530000 8
Y
```

**預期 —— 而它不是你以為的那句話:**

```text
Write 0x00000008 Bytes to SPI flash#1, offset 0x003f0000<0xbd3f0000>, from RAM 0x80530000 to 0x80530008
(Y)es, (N)o->Y
.
```

> 🔴 **參數順序是 `<flash 位移> <RAM 位址> <長度>` —— 跟 `FLR` 的
> `<RAM 位址> <flash 位移> <長度>` 剛好相反。看兩遍再送。**

> ⚠️ **成功只印一個句點 `.`,不印 `Flash Write Successed!`。**
> 那句話確實存在於 loader 裡(stage2 `0x0a861`),但它屬於 **TFTP 自動燒錄路徑**;
> 互動式 `FLW` 的訊息是上面那個 `Write 0x… Bytes to SPI flash#1 …`。
> 兩條路徑相距 2.7 KiB,而 `Flash Read Successed!`(`0x0b4a4`)在互動叢裡 ——
> **那就是這個分群的對照組。**

> ⚠️ **`FLW` 的 Y 提示是 `(Y)es, (N)o->`,`FLR` 的是 `(Y)es , (N)o ? -->`。**
> 相鄰兩個指令,兩種標點。

> 💡 **回應順手洩漏 flash 的記憶體映射位址**:`offset 0x003f0000<0xbd3f0000>`
> —— SPI flash 映射在 `0xbd000000`(KSEG1 非快取區)。

### Step 4 — 讀回,而且讀到「另一個」RAM 位址

```text
FLR 80540000 3F0000 8
Y
DB 80540000 8
```

**預期**:`de ad be ef de ad be ef`

> 🔴 **一定要讀到 `80540000`,不要讀 `80530000`。** 讀回原位址只是把你剛剛放進去的
> 東西再看一次,**證明不了任何事**。
>
> **而「換一個沒用過的位址」還是不夠好** —— 你不知道那個位址裡本來是什麼。
> 更強的做法是先讀一塊**已知內容**的 flash 進去當對照組(`A12` 末的工具就是這樣做的)。
> 2026-08-17 上午這一格的證據就是因此不可採信,而下午重做時才補上對照組。

**這一步過了 = 回復路徑的「寫」半邊成立。還沒完。**

### Step 5 — ★ 量 `FLW` 的磁區語意

> **SPI NOR 的抹除單位是磁區(這顆 EN25QH32B 是 4 KiB),不是 byte。**
> 如果 `FLW` 為了寫 8 個 byte 而抹掉整個磁區,**那麼任何一次 `FLW` 都會毀掉同磁區
> 裡的其他內容** —— 那是救援時會殺死你的事實。

在**同一個 4 KiB 磁區**的另一個位址寫第二個樣式,然後回頭讀第一個:

```text
EB 80530100 CA FE BA BE CA FE BA BE
DB 80530100 8
FLW 3F0100 80530100 8
Y
FLR 80560000 3F0000 8
Y
DB 80560000 8
```

**兩種結果,都要記下來,都不是失敗:**

| 讀到 | 意思 | 對 W06 的影響 |
|---|---|---|
| `de ad be ef …` | `FLW` **保留磁區內其餘內容**(讀-改-抹-寫回) | 可以精準覆寫;但斷電失去的是整個 4 KiB |
| `ff ff ff ff …` | `FLW` **抹掉整個磁區而不保留** | 救援必須整個磁區一起寫回;`H601` 與 `COMPCS` 各自的磁區都是不可分割的單位 |

> ✅ **2026-08-17 的答案是第一種。** `FLW` 是**讀出整個磁區 → 改指定 byte →
> 抹除磁區 → 整段寫回**。三條證據:抹除後回到 `FF`(所以有抹除)、同磁區鄰居沒被清掉
> (所以抹除前先讀出來了)、而 loader 的**指令集裡一個抹除指令都沒有**
> (所以抹除只能由 `FLW` 自己做)。
>
> **仍然要自己跑一次。** 你的單位可能是不同的 flash 型號,而 loader 的型號表裡
> **沒有任何 Eon `QH` 系** —— console 上的 `chipName: UNKNOWN` 就是它認不出來,
> 所以走的是通用路徑,而通用路徑的行為沒有理由用別顆晶片去推。

### Step 6 — ★ 還原測試,而且它有兩種都正確的答案

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
| `ff ff ff ff …` | `FLW` 有抹除語意(與 Step 5 一致)。**還原 = 直接覆寫** | ✅ 通過 |
| `de ad be ef …` | **`FLW` 是純程式化,`1` 只能變 `0`。** 寫 `FF` 什麼都沒改 | ⚠️ 見下 |

> ⚠️ **第二種結果不是操作失誤,是這台的物理性質。** 不要重試,不要換樣式。

### 如果 Step 6 讀回 `de ad be ef` —— 不要慌,但也不要繼續

**`P0-3` 的反證條件是事先寫下的**:「讀回與寫入不一致,**或抹除後不是全 FF**
→ 救援路徑不成立」。**照字面就是被反證了,而且不准事後改判。** 該做的是:

1. **先在 bootloader 裡找抹除指令**,把 `?` 的完整輸出留下來。
   `FLW` 的第四個參數 `<SPI cnt#>` 沒有人解釋過,抹除可能藏在那裡。
2. **記下來,今天到此為止。**

**同時要知道:這台不是沒有救。** `/bin/startup.sh` 有一條裝置自己的還原路徑 ——
`flash test-csconf` 失敗時它會用 `0x8000` 的出廠 `COMPDS` 蓋回 `0xC000`,
而 `H601`(`0x6000`)不在那條路徑上、不會被動到。
**但那是裝置自己做的,不是你執行的,而且它會把設定改回出廠值。**
它是安全網,不是救援路徑,兩者不能互相取代。

> 🔴 **而那條路徑有一個副作用,值得單獨記一筆:** 在「DS 與 CS 都無效」的分支裡,
> `flash default-sw` 之後緊接著是 **`flash set TELNET_ENABLED 1`**。
> 也就是**設定區同時損壞的裝置,重開之後 telnet 是開的** —— 而 `root:123456`
> 在這個 build 的 `passwd.org` 裡還在。**這是靜態讀出來的,還沒驗證。**

### Step 7 — 收尾

離開 picocom:`Ctrl-A` 然後 `Ctrl-X`。
**板子留在 `<RealTek>`,不要重開機**,如果後面還有節要跑。

---

### 讀取一律用工具,因為它帶對照組

```bash
python3 -u tools/console-dump.py dump --at-prompt \
        --flash 0x3F0100 --length 8 --ram 0x80560000 --chunk 8 \
        -o "$HOME/fwre-work/dumps/probe.bin"
xxd "$HOME/fwre-work/dumps/probe.bin"
```

它比手打多三件事,而**第三件是關鍵**:確認 `(Y)es` 真的被接受(不接受就丟例外);
每一塊解析驗證加二次取樣重讀;**對照組先把 flash `0x000000` 讀進同一個 `--ram`**,
比對已知的 `0b f0 00 04` —— 所以真正的讀取之前,那塊 RAM 裝的是**第三種東西**,
既不是 `ca fe ba be` 也不是 `ff ff ff ff`。
**「換一個沒用過的位址」比不上這個:沒用過的位址裡是什麼,你並不知道。**

> ❌ **這一格不准用 `--no-control`。** 對照組正是它的全部價值。

---

### W06 要用它做什麼:還原 16 KiB,不是 8 個 byte

2026-08-17 的 POST 輪把 `COMPDS`(`0x8000`–`0xC000`)覆寫成 `COMPCS` 了。
還原的來源是 `config-region-20260817-1102-pre.bin`
(與 8/16 完整 dump 的前 64 KiB 逐 byte 相同)。

**這比演練難的地方有三個,先想清楚再開始:**

1. **16 KiB = 4 個磁區**,而 `EB` 一次只灌幾個 byte。**手打灌不動 16 KiB。**
   需要一支寫入端的工具,而目前**沒有** —— `console-dump.py` 刻意送不出 `FLW`。
   **那支工具要先寫、要有守衛套件、而且要在演練區 `0x3F0000` 驗過,才准指向 `0x8000`。**
2. **每一個磁區都是讀-改-抹-寫回**,所以寫到一半斷電失去的是那 4 KiB。
   `COMPDS` 壞掉不致命(裝置自己會用它修 `COMPCS`,反過來就不行了) ——
   **但要在動手前確認方向,不要在寫壞之後才想。**
3. **還原之後要重新建立 IoC 基準**(`A5` 的 `tools/ioc-precheck.sh`),
   而預期值是**還原後應該回到 4 / 343**。**那一步就是這次還原的驗證。**

---

## A13 收尾與紀錄

| | |
|---|---|
| **層** | T1(記錄本身不碰裝置) |
| **會不會改變裝置** | 沒有 |
| **關掉的項目** | —(這一節不關掉登記簿項目,它是把別節的結果登記進去) |
| **最後驗證** | 2026-08-17 |

**這一節是把「我跑過」變成「repo 裡有一筆可被質疑的紀錄」。跳過它,前面全部白做。**

### A13.1 每一項跑完就登記,不要累積到最後

```bash
python3 tools/rtcase.py record --id P1-2 --date 2026-08-17 \
    --verdict confirmed --evidence dynamic \
    --artefact BENCH-LOG.md \
    --note "80 開;52869 / 52881 也開,而它們不在任何一條預測裡。22 / 23 / 5555 關,IoC 八埠全關。四次對照組全 200,所以 closed 是裝置的答案。"
```

| 參數 | 值域 | 意思 |
|---|---|---|
| `--id` | 登記簿裡的編號 | 打錯 → 工具直接拒絕 |
| `--date` | `YYYY-MM-DD` | 測試**執行**的日期,不是登記的日期 |
| `--verdict` | `confirmed` / `refuted` / `partial` / `na` | 對照**事先凍結**的那句話判,不是對照你的感覺 |
| `--evidence` | `dynamic` / `static` / `emulated` | 見下,這一欄不能含糊 |
| `--artefact` | **repo 裡存在的路徑**,可重複 | 見下 |
| `--note` | 自由文字 | substance 寫在這裡 |

**`--evidence` 三個等級,而它們渲染成不同的符號:**

| 值 | 意思 | 渲染 |
|---|---|---|
| `dynamic` | 在**這台矽**上跑出來的 | ✅ |
| `static` | 讀出來的(反組譯、字串、dump) | 🟥,**永遠不會變成 ✅** |
| `emulated` | 在模擬環境裡**執行**過,但不是矽 | 🟪,**也永遠不會變成 ✅** |

> 🔴 **`emulated` 是 2026-08-17 才加的第三個等級,而它解決一個真實的困境:**
> `A1.7` 的環境讓這台自己的 binary 對這台自己的 flash 真的**跑起來**了。
> 記成 `static` 低估了(有東西執行了);記成 `dynamic` 就是**這個登記簿存在的目的
> 要防的那種漂白**。所以它有自己的符號,而且不會變成勾。

> ❌ **`--artefact` 必須是 repo 裡存在的檔。** `~/fwre-work/dumps/` **不在 repo 裡**,
> 所以不能當 artefact —— `rtcase check` 會擋掉指向不存在檔案的證據連結。
> **慣例是指向 `BENCH-LOG.md`**,而 substance 寫在 `--note` 裡。

> ❌ **`rtcase` 會拒絕一個沒有事先寫好反證條件的項目,而那不是 bug。**
> 訊息長這樣:`P?-? has no refutation condition. Write it into the register and re-freeze`。
> **一個沒有事先寫下「失敗長什麼樣」的測試,事後一定會被讀成成功** ——
> 因為回應到手的時候,讀的人已經知道自己想看到什麼了。

> ⚠️ **每一筆結果會戳上它當時所依據那段反證文字的逐項雜湊。**
> 所以事後去改反證條件會被抓到:`rtcase check` 會說
> `result was recorded against a different wording`。**這不是防篡改** ——
> 你手上有鑰匙 —— 它是「改動出現在 diff 裡」和「不會」的差別。

### A13.2 重生成、驗證、看還欠什麼

```bash
make ledger
make todo WEEK=W05
make rtcase
```

**預期**:

```text
wrote test-ledger.md - 130 cases, 34 executed
W05: 27/27 done, 0 outstanding
register OK - 130 cases, 102 frozen, 34 executed, freeze 69c342dc...
  schedule d68ace7d..., 4 rescheduled: P3-1, P3-2, P3-3, P9-9
```

> ⚠️ **`test-ledger.md` 是生成的,不要手改。** CI 會跑
> `make ledger && git diff --exit-code`,改了登記簿沒重生成就紅。

> ⚠️ **`4 rescheduled` 那一行是刻意顯眼的。** `week` 欄位進了第二個雜湊
> `[schedule].sha256`,所以**搬動一項到別的週必須同時寫下 `rescheduled_from`、
> 理由、日期,並重新宣告雜湊** —— 少一個 CI 就紅。
> 那條機制存在的原因:W05 有四項排在 W05 但**週計畫自己禁止本週做**,
> 所以收斂指令永遠到不了 0。**決定早就寫在 `PROGRESS.md`,不一致的是資料。**

### A13.3 往 BENCH-LOG 追加這一場

**格式**:計畫(動手之前寫的)→ 紀錄卡 → 實測結果 → 燒掉了什麼 → 下一場從哪裡開始。

> 🔴 **計畫要在動手之前 commit。** append-only 加上 git,讓「寫在前面」這件事
> **可以被 diff 證明** —— 而那是這整套東西唯一不肯妥協的一件事。
> 一份事後才寫的成功條件證明不了任何東西。

> ⚠️ **只追加,不修改既有段落。** 一場做完就定版,連你發現自己當時錯了也一樣 ——
> **把更正寫在新的一場裡**。2026-08-17 的兩處更正(`FLW` 的預期字樣、
> 閘門的錯誤推論)就是這樣處理的。

> ⚠️ **per-unit 識別碼(MAC、SSID、`config.dat` 內容、射頻校準值)不寫進來。**
> 跟 W02 把 PCB 條碼塗掉是同一條規則,而揭露策略的擁有者是
> [`docs/disclosure.md`](docs/disclosure.md) —— **這裡不複述它,只指向它。**
> (標頭曾經複述過,然後跟自己檔案裡的一段矛盾了。)

### A13.4 一週結束時還有三件事

| 檔案 | 寫什麼 |
|---|---|
| [`PROGRESS.md`](PROGRESS.md) | gate、DoD、carried-forward。**不要把單項測試結果寫成散文** |
| [`README.md`](README.md) | gate 勾選板 + 一行數字。**跟 PROGRESS 同一個 commit** |
| [`study/weekly-results.md`](study/weekly-results.md) | 一句話版本、三個可辯護的點、**以及「這週沒證明什麼」** |

> 🔴 **「這週沒證明什麼」那一欄是空的,代表這一週的自我檢查不夠。**
> 那一欄是三個裡面最重要的一個。

---

## A14 出事的時候

| 症狀 | 原因 | 做什麼 |
|---|---|---|
| `Cannot find device "eth1"` 而 `ping` 卻通 | 網卡在 Windows 側,你繞過去了 | `A4` 的 `ip route get`。看 `via` |
| 抓不到任何封包 | 先看 `rx_packets`。`0` = 鏈路沒在送東西給你 | `A6` |
| `Speed: Unknown!` / `Duplex: Half` | 協商沒完成,或對端沒起來(例如板子停在 bootloader) | 正常,繼續 |
| 所有端點都「不存在」 | 你可能把 `boa` 打掛了 | `python3 tools/bench-probe.py control --host 10.1.1.1` |
| `boa` 完全不回應但 `ping` 通 | `A9` 的已知結果。`rcS` 不 respawn | **拔電重開** |
| `catch` 說 `booted past the interrupt window` | 板子沒有真的斷電過 | 確實拔電,停 2 秒,重跑 `A3` |
| `DB` 印出來跟上一次一樣 | `FLR` 沒生效(多半是 `Y` 被下一個指令吃掉) | 那是 RAM 舊值,不是 flash |
| 打錯 `FLW` 參數 | —— | **不要再送任何指令。拍照。** |
| `rtcase check` 說 artefact 不存在 | 證據連結要指到 repo 裡存在的檔 | `A13` |
| `test-ledger.md is out of date` | 改了登記簿沒跑 `make ledger` | `make ledger` |
| `binwalk: command not found` 而它明明裝了 | `~/.cargo/bin` 不在這個 shell 的 PATH | `bash tools/setup/setup-wsl.sh path`,然後用 `bash -lc` |
| IoC 預檢不是你記的那個數字 | 可能是上一場的 POST 輪 | 讀 `BENCH-LOG.md` 最後一場的「燒掉了什麼」 |

---

# Part B — 每一週跑哪幾節

> **只追加。** 一週做完就定版。**Part A 是可編輯的;這裡不是。**

## B-W05 偵察(2026-08-17,已完成:登記簿 27/27、DoD 5/5)

| 場次 | 順序 | 本週特有 |
|---|---|---|
| 上午 | `A0` → `A2` → `A3` → `A5` → `A4` → `A6` → `A7` → `A8` → `A13` | `A12` 的 `FLW` 演練(一次性,G3.5 #5) |
| 下午 | `A0` → `A2` → `A3` → **`A12` 讀磁區** → `A5` → `A4` → `A11` → `A10` → `A8` → `A9` → `A3` → `A5` → `A13` | 磁區語意判別;`P9-1` 靜態三來源 |

**下午那個順序有一個理由**:`A12` 的磁區讀取排在最前面,因為它答的是 W06 卡住的
那一格,而**一場只要提早結束,最不能掉的就是它**。

**這一週實際發生了什麼、以及四個儀器缺陷** → [`BENCH-LOG.md`](BENCH-LOG.md)。
**判定** → [`test-ledger.md`](test-ledger.md)。**推理** → [`PROGRESS.md`](PROGRESS.md)。

## B-W06 PoC(未開始)

**開場三件事,照這個順序:**

1. **還原 `COMPDS`** —— 2026-08-17 的 POST 輪把它覆蓋成 `COMPCS` 了。
   來源:`config-region-20260817-1102-pre.bin`(與 8/16 完整 dump 的前 64 KiB 相同)。
   範圍:`0x8000`–`0xC000`,16 KiB = 4 個磁區。走 `A12`。
   **然後重新建立 IoC 基準**,之後才有對照組。
2. `A0` → `A2` → `A3` → `A5` → `A4` → `A13`,加上開火與還原。
3. **決定 `BENCH-LOG.md` 標頭那個 MAC 矛盾往哪邊收** ——
   標頭說 per-unit 識別碼不寫進來,而上午那一段寫了兩個 MAC。
