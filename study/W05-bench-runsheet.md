# W05 實機作業單 — 2026-08-17

> **這份檔案不是規程的第二份拷貝。**
> 規程的擁有者是 [`RUNBOOK.md` §8.9](../RUNBOOK.md)（`FLW` 演練）與
> [§8.7.8](../RUNBOOK.md)（`FLR`+`DB`）；單項測試的預測與反證條件的擁有者是
> [`study/test-cases.toml`](test-cases.toml)。
> **本檔擁有的是「2026-08-17 這一場照什麼順序做、每一步看到什麼」** —— 作業單與紀錄卡。
> 做完之後，逐字 transcript 貼回 `RUNBOOK.md` §8.9，判定用 `rtcase record` 記進登記簿。

> ## ⚠️ 先讀這三行，再插電
>
> 1. **`RUNBOOK.md` §8.9 的演練從來沒有被執行過。** 所以它裡面每一行「預期輸出」
>    都是**預測**，不是實測紀錄。本檔把預測標成「預期」，實際看到的填進紀錄卡。
> 2. **§8.9 的「抹回去」那一步在物理上可能做不到，而且它沒有說。**
>    NOR flash 的程式化只能把 `1` 變 `0`。**把 `FF` 寫在 `DE` 上面，得到的還是 `DE`。**
>    要回到 `FF` 必須「抹除」，那是另一個動作。除非 RealTek 的 `FLW` 會先自動抹掉整個磁區
>    —— 而**那正是這次演練要量出來的東西**，不是可以假設的東西。
>    所以本檔的 Phase 2 比 §8.9 多兩步，它們的用途是**分辨這兩種語意**。
> 3. **WAN 埠必須是空的。** 網路線只接 LAN 埠。**不要按 reset 鍵。**

---

## 這一場要關掉的登記簿項目

| ID | 項目 | 這一場做到哪 |
|---|---|---|
| `P0-2` | UART console 常駐 + 全程 log | Phase 0 |
| `P0-10` | 每次動手前抓 64 KiB 設定區快照 | Phase 1 |
| `P0-5` | IoC 預檢：這台是不是已經是別人的肉雞 | Phase 1 的同一份讀取 |
| **`P0-3`** | **bootloader 救援路徑演練（G3.5 #5）** | **Phase 2 ← 今天的關鍵** |
| `P9-3` | bootloader TFTP / HTTP 救援 | Phase 2 附帶 |

**`P0-3` 沒過，Phase 3（網路）就不准開始。** 這不是儀式：W06 的 PoC 執行的是
`flash set`，寫的就是設定區，而這台的回復路徑從來沒有被執行過。
`0x006000` 的 `H601` 是這台的 MAC 和射頻校準值，**全世界只有這一份**，
原廠映像沒有，回復原廠設定也不會還原它。

---

# Phase 0 — 接線與抓 bootloader

## 0.1 開工前的三個確認（不碰裝置）

**確認唯一的還原鏡像還在，而且沒變。** 貼進 WSL：

```bash
cd ~/fwre-work/dumps && sha256sum -c <<'EOF'
a800059a9b8c414df026a22b8423a5939d0f9bb793109d0f7ce086f6810f37ea  flash-n150rt-console-1.bin
a800059a9b8c414df026a22b8423a5939d0f9bb793109d0f7ce086f6810f37ea  flash-n150rt-console-2.bin
EOF
```

**預期輸出**（兩行都要 `OK`）：

```
flash-n150rt-console-1.bin: OK
flash-n150rt-console-2.bin: OK
```

> ❌ **任何一行不是 `OK` → 停。** 那是這台的唯一備份，備份壞了就沒有安全網。

**實體檢查，用眼睛：**

- [ ] 網路線插在 **LAN** 埠（有數字標號的那幾個），**不是** WAN 埠
- [ ] WAN 埠**什麼都沒插**
- [ ] CP2102 的三條線接在 UART 排針上：`VCC · TX · RX · GND`，pin 1 是絲印三角形那端
      → **VCC 那條不要接**（板子自己有電，接了會對打）
      → CP2102 的 `RX` 接板子的 `TX`(pin 2)，CP2102 的 `TX` 接板子的 `RX`(pin 3)，`GND` 對 `GND`(pin 4)
- [ ] **電源還沒插**

## 0.2 把 USB 轉序列器交給 WSL

**Windows PowerShell**（不需要管理員，之前 bind 過了）：

```powershell
usbipd list
```

找到 `10c4:ea60` 那一行，記下 BUSID（上次是 `1-4`）。然後：

```powershell
usbipd attach --wsl --busid 1-4
```

**預期**：`usbipd: info: Using WSL distribution ...` 之後那一行的 STATE 變成 `Attached`。

> ⚠️ **attachment 綁在 WSL 這個 VM 上。VM 一停，裝置就退回 Windows。**
> 所以另外開一個 PowerShell 視窗，貼這一行然後**不要關**：
> ```powershell
> wsl -d Ubuntu-24.04 -- sleep 14400
> ```

**回到 WSL 確認裝置在**：

```bash
ls -l /dev/ttyUSB*
```

**預期**：`crw-rw---- 1 root dialout 188, 0 ... /dev/ttyUSB0`

## 0.3 抓 bootloader（`P0-2`）

貼這一行，**然後才去插電源**：

```bash
cd /mnt/c/Users/Key20/Desktop/router
python3 -u tools/console-dump.py catch --port /dev/ttyUSB0 --window 300 -v \
        2>&1 | tee ~/fwre-work/dumps/w05-console-$(date +%Y%m%d-%H%M).log
```

看到這一行才插電：

```
>>> POWER THE ROUTER ON NOW <<<
```

**預期**：ESC 串流打斷開機，最後停在

```
<RealTek>
```

> ⚠️ **已知坑（RUNBOOK 第 7 號儀器 bug）**：搶 bootloader 是「連續送」ESC，
> 它只吃掉一個，**其餘全部排在輸入緩衝區裡**，所以**搶到之後第一條指令必定失敗**，
> 回你 `Unknown command !`。工具的 `settle()` 會先送一個裸 `\r` 清掉。
> 手打的時候：**先按一次 Enter，看到乾淨的 `<RealTek>` 再打真的指令。**

> ❌ **抓不到 → 不要重試超過三次。** 每次都是一次完整的開機。
> 抓不到的原因通常是 window 太短或線接反了，不是裝置的問題。

---

# Phase 1 — 64 KiB 設定區快照（`P0-10` + `P0-5`）

**一次 90 秒的讀取，同時是三件事**：今天的還原點、IoC 預檢的輸入、
以及「昨天到現在設定沒被動過」的證明。整段是唯讀，不寫任何東西。

板子停在 `<RealTek>`，貼這一段：

```bash
cd /mnt/c/Users/Key20/Desktop/router
SNAP=~/fwre-work/dumps/config-region-$(date +%Y%m%d-%H%M).bin
python3 -u tools/console-dump.py dump --at-prompt \
        --flash 0x0 --length 0x10000 --ram 0x81000000 --chunk 16384 \
        -o "$SNAP"
echo "SNAP=$SNAP"
```

**預期**：約 90 秒（65,536 bytes ÷ 723 B/s），結尾

```
wrote ... 65536 bytes
```

> ⚠️ **工具的規則是「拼不完整就不吐檔案」**，只留 `.partial`。
> 有 `.partial` 沒有 `.bin` = 有一塊重讀三次都沒過。**那要查，不要繞過。**

## 1.1 對照：這 64 KiB 跟昨天的完整 dump 一樣嗎

```bash
cmp <(head -c 65536 ~/fwre-work/dumps/flash-n150rt-console-1.bin) "$SNAP" \
  && echo "IDENTICAL — 設定區與 8/16 的完整 dump 逐 byte 相同"
```

**預期**：`IDENTICAL`

> 🔴 **如果有差異，先不要判斷是好是壞。** 這台從 8/16 之後就沒被動過，
> 所以差異只有兩種可能：**(a) 有東西改了設定** —— 那是 `P0-5` 的反證條件，
> 是資安事件不是弱點研究；**(b) `FLR` 這條讀取路徑不穩定** —— 那更嚴重，
> 因為 W02 的整份 dump 都走它。**兩種都要先查清楚才准往下走。**
> `cmp` 印出來的第一個差異位移是關鍵，記進紀錄卡。

## 1.2 IoC 預檢（`P0-5`）

```bash
cd /mnt/c/Users/Key20/Desktop/router
~/fwre-work/venv/bin/python -m fwrecon compcs "$SNAP" --offset 0xC000 \
     --mib ~/fwre-work/extracted/unit-2018/squashfs-root/lib/libapmib.so \
     --disclosure protect -f json -o /tmp/cs-today.json
~/fwre-work/venv/bin/python -m fwrecon compcs "$SNAP" --offset 0x8000 \
     --mib ~/fwre-work/extracted/unit-2018/squashfs-root/lib/libapmib.so \
     --disclosure protect -f json -o /tmp/ds-today.json
```

**測前寫下的成功條件（不准事後調整）**：
**live 設定與出廠預設的差異維持在 4 / 344 筆。**

> ❌ **出現第 5 筆差異 → 停手，走事件處理程序。**
> 這型號在公開的殭屍網路工具裡被點名過。**一台已經是別人的裝置是一起事件，不是一個測試標的。**

---

# Phase 2 — `FLW` 回復路徑演練（`P0-3` / G3.5 #5）★ 今天的關鍵

> ## 🔴 動手前的四條規矩
>
> 1. **每一行先看完，再貼。不准現打。** `FLR` 已經教過這台一課：
>    兩個相鄰指令用兩種進位制（`FLR` 長度是十六進位，`DB` 長度是十進位）。
>    **`FLW` 參數順序打錯 = 把測試樣式寫進 kernel。**
> 2. **只碰 `0x3F0000`。** 不要「順便試試看 `0x350000`」。
> 3. **`console-dump.py` 送不出 `FLW`**（它的 `FORBIDDEN` 常數擋掉 `FLW`/`EB`/`EW`/`AUTOBURN`/`J`）。
>    這是刻意的：**寫入指令由讀過它的人親手打，不由腳本發。** 所以這一段用 `picocom`。
> 4. **每一步看到預期輸出才准下一步。** 對不上就停，填紀錄卡，回報。

### 為什麼 `0x3F0000` 是安全的

W02 Day 4 的完整 dump 證明 **`0x350000` 到 part 結尾整段都是 `FF`（已抹除）**，
沒有任何東西讀它。演練寫入的完美標的。

### 開 picocom

```bash
picocom -b 38400 --logfile ~/fwre-work/dumps/w05-flw-$(date +%Y%m%d-%H%M).log /dev/ttyUSB0
```

**離開 picocom 是 `Ctrl-A` 然後 `Ctrl-X`。** 先記住這個，等一下會用到。

> ⚠️ **不要加 `--omap crlf`。** picocom 的 `crlf` 是「把 CR 換成 LF」，不是「CR 後面補 LF」，
> 送出去的行尾會變成裸 `LF`，而這台的 bootloader 收 `CR`。
> 更糟的是任何多送的一個換行**都會被 `FLR` 的 `(Y)es , (N)o ?` 吃掉當答案** ——
> 那正是 `RUNBOOK.md` §8.7.8 記過的第一號陷阱，代價是拿到一份格式完全正常、
> 內容是 RAM 舊值的 dump。**維持預設，一個 map 都不要加。**

> 💡 **讀取步驟也可以不用 picocom。** `tools/console-dump.py cmd --at-prompt FLR ...`
> 會自己處理那個 `Y` 提示並驗證回應，比手打安全。它只是**送不出 `EB` 和 `FLW`**。
> 所以：全程 picocom 手打（本檔的寫法，人會等提示，陷阱咬不到人），
> 或讀取用工具、寫入用 picocom（要換手，但讀取那半邊有機器把關）。**兩種都可以，不要混著半途改。**

按一次 **Enter**，應該看到乾淨的 `<RealTek>`。

---

## Step 1 — 確認目標區真的是空的（唯讀）

```
FLR 80520000 3F0000 100
```

它會問，回答 `Y`：

```
Y
```

**預期**：`Flash Read Successed!`

```
DB 80520000 256
```

**預期**：**整片 `ff`**，16 行，每行 16 個 byte。

> ❌ **不是整片 `ff` → 停。** 那裡有東西，換一個位址之前要先知道那是什麼。

---

## Step 2 — 在 RAM 裡放樣式，並且確認它真的進去了

```
EB 80530000 DE AD BE EF DE AD BE EF
```

```
DB 80530000 8
```

**預期**：`de ad be ef de ad be ef`

> ⚠️ **`EB <Address> <Value>...` 一次吃多個 byte 這件事沒有被實測過**
> （`?` 的說明寫了 `...`，但這台沒人這樣送過）。
> **如果 `DB` 讀回來只有第一個 byte 對**，就是一次只吃一個，改成八行：
> ```
> EB 80530000 DE
> EB 80530001 AD
> EB 80530002 BE
> EB 80530003 EF
> EB 80530004 DE
> EB 80530005 AD
> EB 80530006 BE
> EB 80530007 EF
> ```
> **這一步失敗不是壞消息，是一條要記下來的裝置事實。**

---

## Step 3 — 寫入（★ 第一個不可逆的動作）

```
FLW 3F0000 80530000 8
```

```
Y
```

**預期**：`Flash Write Successed!`（或等價字樣）

> 參數順序是 **`<flash 位移> <RAM 位址> <長度>`** —— 跟 `FLR` 的
> `<RAM 位址> <flash 位移> <長度>` **是相反的**。看兩遍再送。

---

## Step 4 — 讀回，而且讀到「另一個」RAM 位址

```
FLR 80540000 3F0000 8
```

```
Y
```

```
DB 80540000 8
```

**預期**：`de ad be ef de ad be ef`

> 🔴 **一定要讀到 `80540000`，不要讀 `80530000`。**
> 讀回原位址只是把你剛剛放進去的東西再看一次，**證明不了任何事**。

**這一步過了 = 回復路徑的「寫」半邊成立。** 還沒完。

---

## Step 5 — ★ 量 `FLW` 的語意：它會不會先抹掉整個磁區

> **這一步 `RUNBOOK.md` §8.9 沒有，而它是這次演練最重要的產出。**
> SPI NOR 的抹除單位是磁區（通常 4 KiB），不是 byte。
> 如果 `FLW` 為了寫 8 個 byte 而抹掉整個 4 KiB 磁區，
> **那麼任何一次 `FLW` 都會毀掉同磁區裡的其他內容** —— 那是救援時會殺死你的事實。

在**同一個 4 KiB 磁區**的另一個位址寫第二個樣式：

```
EB 80530100 CA FE BA BE CA FE BA BE
```

```
DB 80530100 8
```

**預期**：`ca fe ba be ca fe ba be`

```
FLW 3F0100 80530100 8
```

```
Y
```

**現在回頭讀第一個樣式**：

```
FLR 80540000 3F0000 8
```

```
Y
```

```
DB 80540000 8
```

**兩種結果，都要記下來，都不是失敗：**

| 讀到 | 意思 | 對 W06 的影響 |
|---|---|---|
| `de ad be ef de ad be ef` | **`FLW` 只寫它被指定的那幾個 byte**，不抹磁區 | 救援可以精準覆寫，風險低 |
| `ff ff ff ff ff ff ff ff` | ★ **`FLW` 會先抹掉整個 4 KiB 磁區** | **救援時必須整個磁區一起寫回**，`H601` 和 `COMPCS` 各自所在的磁區都要當成不可分割的單位 |

---

## Step 6 — ★ 還原測試，而且它有兩種都正確的答案

```
EB 80530200 FF FF FF FF FF FF FF FF
```

```
DB 80530200 8
```

**預期**：`ff ff ff ff ff ff ff ff`

```
FLW 3F0000 80530200 8
```

```
Y
```

```
FLR 80550000 3F0000 8
```

```
Y
```

```
DB 80550000 8
```

**兩種結果：**

| 讀到 | 意思 | 判定 |
|---|---|---|
| `ff ff ff ff ff ff ff ff` | `FLW` 有抹除語意（與 Step 5 一致）。**還原 = 直接覆寫。** | ✅ `P0-3` 成立，W05 可以往下 |
| `de ad be ef de ad be ef` | **`FLW` 是純程式化，`1` 只能變 `0`。** 寫 `FF` 什麼都沒改。 | ⚠️ **見下面「如果 Step 6 回到 DEADBEEF」** |

> ⚠️ **第二種結果不是操作失誤，是這台的物理性質。** 不要重試，不要換樣式。
> 記下來，然後往下讀。

---

## 如果 Step 6 讀回 `de ad be ef` —— 不要慌，但也不要繼續

**登記簿 `P0-3` 的反證條件是事先寫下的**：

> 「讀回與寫入不一致，**或抹除後該區塊不是全 FF** → 救援路徑不成立。
> G3.5 #5 不通過，W05 不得往下走。」

**照字面，這條就是被反證了，而且不准事後改判。** 該做的是：

1. **先在 bootloader 裡找抹除指令**，把 `?` 的完整輸出貼回來：
   ```
   ?
   ```
   `FLW` 的第四個參數 `<SPI cnt#>` 沒有人解釋過，抹除可能藏在那裡。
2. **記下來，然後今天就到這裡為止。** 我拿到 `?` 的完整輸出和你的紀錄卡之後，
   會給你下一步。

**同時要知道的事：這台不是沒有救。** `/bin/startup.sh` 裡有一條裝置自己的還原路徑：

```
$TOOL test-csconf
if [ $? != 0 ]; then
        echo 'Current configuration invalid, reset to default configuration!'
        $LOADDS          # flash reset1 —— 用 0x8000 的出廠 COMPDS 蓋回 0xC000
fi
```

也就是說**設定區壞掉的時候，這台開機時會自己用出廠預設修好它**，
而 `H601`（`0x6000`，MAC 與射頻校準）不在那條路徑上、不會被動到。
但那是**裝置自己做的**，不是我們執行的，而且**它會把設定改回出廠值**。
所以它是安全網，不是救援路徑，兩者不能互相取代。

> 🔴 **而且那條路徑有一個副作用，值得單獨記一筆：**
> `startup.sh` 在「DS 與 CS 都無效」的分支裡執行 `flash default-sw` 之後，
> 緊接著就是 **`flash set TELNET_ENABLED 1`**。
> 也就是：**設定區同時損壞的裝置，重開之後 telnet 是開的** —— 而 `root:123456`
> 在這個 build 的 `passwd.org` 裡還在。這是靜態讀出來的，還沒驗證。

---

## Step 7 — 收尾

離開 picocom：`Ctrl-A` 然後 `Ctrl-X`。

**板子留在 `<RealTek>`，不要重開機**，Phase 3 還要用。

---

# 紀錄卡 — 2026-08-17，從逐字 transcript 填寫

**每一格都對得上一份 log 檔。** 逐字紀錄在
`$FWRE_WORK/dumps/w05-console-20260817-0731.log` 與
`w05-flw-20260817-0738.log`；規程要求的完整 transcript 貼在
[`RUNBOOK.md` §8.9](../RUNBOOK.md)。

```
T-01  P0-2   UART console 常駐                        2026-08-17 07:31
      抓到 bootloader: 一次上電命中，300 秒 window
      banner: ---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)
      log: dumps/w05-console-20260817-0731.log
      判定: ✅ 成立
      反證檢查: 測前寫的是「console 出現亂碼、斷線或不吐訊息 → 供電/接地問題」
                實際看到: 乾淨的 <RealTek>，`?` 完整印出 16 條指令，全程無亂碼

T-02  P0-10  64 KiB 設定區快照                        2026-08-17 07:33
      檔名: dumps/config-region-20260817-0733.bin        大小: 65,536
      與 8/16 完整 dump 的 cmp: **IDENTICAL** —— 逐 byte 相同
      判定: ✅ 成立
      反證檢查: 測前寫的是「送出已知會寫設定的請求後兩份快照差異是 0 → 還原點範圍選錯」
                實際看到: 本次尚未送出任何寫入請求，此為基準快照。範圍正確性
                          待 W06 第一次 flash 寫入後才可判定 → 本項記為 🔶 部分

T-03  P0-5   IoC 預檢                                 2026-08-17 07:35
      COMPCS vs COMPDS 差異筆數: **4 / 343**（測前寫的成功條件: 4）
        CHECK_SSID_OK · DHCP_LEASE_TIME · MIB_VER · WLAN_SSIDS
      兩區的 checksum_ok 皆為 True，verdict 皆為 consistent
      判定: ✅ 成立
      反證檢查: 測前寫的是「出現第 5 筆設定差異，或 19412/31412/48101/2323/60001
                任一埠有回應 → 資安事件，測試中止」
                實際看到: 第 5 筆沒有出現。**埠的部分本次未測**（網段尚未建立），
                          所以本項只完成一半 → 記為 🔶 部分，埠掃描留在 Phase 3

T-04  P0-3   FLW 回復路徑演練                          2026-08-17 07:38–07:47
      Step 1  0x3F0000 起 256 bytes: **整片 ff**（16 行全 ff）
      Step 2  EB 一次吃 8 個 byte: **可以** —— `DB` 讀回 de ad be ef de ad be ef
              （RUNBOOK §8.9 把這件事列為「沒有被實測過」，現在測過了）
      Step 3  FLW 回應字樣（逐字）:
              Write 0x00000008 Bytes to SPI flash#1, offset 0x003f0000<0xbd3f0000>,
              from RAM 0x80530000 to 0x80530008
              (Y)es, (N)o->Y
              .
              → **不是「Flash Write Successed!」，是一個句點。** §8.9 的預期字樣是錯的
      Step 4  讀回（新 RAM 位址 80540000）: de ad be ef de ad be ef —— 與寫入一致
      Step 5  ★ 在同磁區 0x3F0100 寫入後回頭讀 0x3F0000: de ad be ef de ad be ef
              → 讀起來是「FLW 不抹磁區」，**但這一格的讀回用了 80540000，
                而那是 Step 4 已經用過的位址** —— RUNBOOK §8.7.8 警告過的形狀。
                **作業單這一格設計錯誤，結果不可採信** → 見下面「未結」
      Step 6  ★ 寫 FF FF FF FF FF FF FF FF 到 0x3F0000，讀回（新位址 80550000）:
              ff ff ff ff ff ff ff ff → **回到全 FF**
      判定: ✅ 成立（對照它事先凍結的那一句）
      反證檢查: 測前寫的是「讀回與寫入不一致，或抹除後該區塊不是全 FF
                → 救援路徑不成立，W05 不得往下走」
                實際看到: 讀回與寫入一致（Step 4），抹除後全 FF（Step 6）。
                          兩個條件都滿足，**所以 P0-3 通過**
      這一步燒掉了什麼: 0x3F0000 與 0x3F0100 各 8 bytes 被寫過又被抹回。
                        該區在 W02 完整 dump 中確認為已抹除區，無任何東西讀它
      下一步: 見「未結：FLW 的磁區語意」

T-05  P1-1   找到真實 LAN IP                            2026-08-17 08:15
      USB 網路卡在 Windows 側起來，從這台的 DHCP 伺服器拿到位址:
        Get-NetIPAddress → Ethernet 5   10.1.1.10/24   PrefixOrigin: Dhcp
      ping 10.1.1.1 → 3/3，rtt 1.97 / 3.08 / 3.23 ms
      判定: ✅ 成立
      反證檢查: 測前寫的是「DHCP 沒派到 10.1.1.0/24 的位址，或 10.1.1.1 不回應
                → 解出來的設定區與這台實際跑的設定不是同一份，compcs 解碼要重驗」
                實際看到: 派到 10.1.1.10 —— **正是預測的 10.1.1.10–254 這個池子的
                第一個位址**，而 10.1.1.1 回應 ICMP。COMPCS 的解碼經得起這一測。
      ⚠️ 這一測同時暴露一件事: **回應的 TTL 是 63，不是 64。**
         直連的 Linux 主機回 64，少一跳代表中間有路由器 —— 網路卡起在 Windows 側，
         WSL 是繞過去的。所以在 `usbipd attach` 之前:
           · P0-4 隔離確認做不了（不在那個網段上）
           · P1-10 SSDP 一定失敗，而且會失敗得像「UPnP 沒開」（多播不過 NAT）
           · P2-7 兩個來源 IP 會被 NAT 成同一個
           · nmap -sS / -sU 的結果不可信
         **而且 Windows 同時在 10.1.1.10（實驗網段）、192.168.0.101（Wi-Fi，通外網）
         和 192.168.56.1 上** —— 它帶著完整網路堆疊坐在實驗網段裡，
         這本身就違反 P0-4 事先寫的「網段上只有兩個 MAC」。
      下一步: usbipd attach --wsl --busid 2-4，然後 **ping 回來要是 ttl=64 才准往下**
```

---

## 未結：`FLW` 的磁區語意，以及為什麼這比 `P0-3` 通過更重要

**Step 5 與 Step 6 的結果在 NOR flash 的物理上互相矛盾。**

程式化只能把 `1` 變 `0`。`FF` 寫在 `DE` 上面應該還是 `DE`；Step 6 讀回全 `FF`，
**代表確實有抹除發生**。而抹除的最小單位是磁區（這顆 EN25QH32B 是 4 KiB），
所以 Step 5 在 `0x3F0100` 的寫入本應把整個 `0x3F0000`–`0x3F0FFF` 抹掉——
但 `0x3F0000` 讀起來還是原樣。

三條證據指向同一個機制：

| | |
|---|---|
| Step 6 回到 `FF` | 一定有抹除 |
| Step 5 同磁區另一段沒被清掉 | 抹除前先把磁區內容讀出來了 |
| **`?` 的完整指令集裡沒有任何抹除指令** | 所以抹除只能由 `FLW` 自己做 |

**推定：bootloader 的 `FLW` 是「讀出整個磁區 → 改指定 byte → 抹除磁區 → 整段寫回」。**

**如果成立，這是一條必須寫進 W06 風險評估的事實**：每一次 `FLW`
都會重寫整個 4 KiB 磁區，而 `H601`（這台的 MAC 與射頻校準值）**整個住在一個磁區裡**。
寫入中途斷電失去的不是 8 個 byte，是那個磁區。

### 一組指令就能分辨（`80560000` 是全新的 RAM 位址）

```
DB 80560000 8
FLR 80560000 3F0100 8
Y
DB 80560000 8
```

第一個 `DB` 是對照組 —— 讀 flash 之前先看那塊 RAM 是什麼，
**否則「值沒變」和「FLR 沒生效」分不開**，那正是 Step 5 踩到的坑。

| 第二個 `DB` 讀到 | 結論 |
|---|---|
| `ca fe ba be ca fe ba be` | 讀-改-抹-寫回成立。Step 5 的讀法是對的，只是證據不夠 |
| `ff ff ff ff ff ff ff ff` | Step 6 抹掉了整個磁區，Step 5 是 RAM 舊值。**風險等級上調** |

**這一項不影響 `P0-3` 的判定** —— 它問的是別的問題，而 `P0-3` 凍結的那一句
已經被滿足了。事後把它變難，跟事後把它變鬆一樣不誠實。它是一條新的
carried-forward 開放題。

---

## 對 `RUNBOOK.md` §8.9 的三處更正（本次實測）

| §8.9 寫的 | 實際 |
|---|---|
| 「`Flash Write Successed!`（或等價字樣）」 | **一個句點 `.`**。真正的回應是 `Write 0x… Bytes to SPI flash#1, offset 0x003f0000<0xbd3f0000>, from RAM 0x… to 0x…` 然後 `(Y)es, (N)o->` |
| `FLR` 的提示是 `(Y)es , (N)o ? -->` | **`FLW` 的是 `(Y)es, (N)o->`** —— 兩個相鄰指令，兩種標點。與「兩種進位制」同一種毛病 |
| 「`EB` 一次吃多個 byte 沒有被實測過」 | **測過了，可以。** `?` 的說明本身也寫 `EB <Address> <Value1> <Value2>...` |
| 「抹回去：`FLW 3F0000 <一塊全 FF 的 RAM> 8`」 | **這樣做確實會回到 FF** —— 但理由不是文件想的那個，見上面「未結」 |

順帶：`FLW` 的回應洩漏了 flash 的記憶體映射位址 —— `offset 0x003f0000<0xbd3f0000>`，
所以 SPI flash 映射在 **`0xbd000000`**（KSEG1，非快取）。這個資訊在 W02 的
`flash-layout.md` 裡沒有。

---

# Phase 3 — 網路（`P0-3` 通過之後才開始）

## 3.-1 順序：重開機**之前**要先做完的三件事

Phase 2 結束時板子停在 `<RealTek>`，**Linux 從來沒有起來過** —— 沒有 `boa`，
沒有網路堆疊。所以 Phase 3 必須重開機。但有三件事要在重開之前做完，
每一件都是「重開之後就做不了 / 要重來一次」：

| 先做 | 為什麼不能等 |
|---|---|
| **§8.9.3 的 `FLW` 磁區語意判定**（四行指令） | 重開之後要再搶一次 bootloader 窗口才回得來 |
| **網路卡 bind + attach + `ip link set up`** | `P0-4` 要抓的是**開機瞬間**的封包，那是裝置最可能對外講話的時候 |
| **啟動 `tcpdump` 與 `P1-12` 的計時器** | `P1-12` 量的是「上電到 web 可服務」，計時器必須先跑 |

```
1. （還在 bootloader）跑 §8.9.3 的四行
2. 網路卡：usbipd bind --busid 2-4  →  usbipd attach --wsl --busid 2-4
3. sudo ip link set eth1 up          （先不要給位址，DHCP 是 P1-1 要測的）
4. sudo tcpdump -ni eth1 -w ~/fwre-work/dumps/w05-boot-$(date +%H%M).pcap &
5. 貼上 §3.4 的計時器
6. picocom 留著不要關 —— 這台沒有 shell，console 是唯一的崩潰觀測管道
7. 拔電、插電，★ 這次不要送 ESC
```

> ⚠️ **不要按 reset 鍵。** 那會把 `COMPCS` 蓋回出廠值，
> 而 `P0-5` 剛量到的 4/343 差異就是這台的現況證據。

**開機之後第一件事是 `P1-1`，而且要先測 DHCP 再固定 IP** ——
直接設靜態位址就跳過了它事先寫下的反證條件（「DHCP 沒派到 10.1.1.0/24 的位址」）：

```bash
sudo nmap --script broadcast-dhcp-discover -e eth1    # 它派的是什麼位址？
sudo ip addr add 10.1.1.100/24 dev eth1               # 量完才固定
ping -c 3 10.1.1.1
```

## 3.0 測前已經凍結的預測，不准事後改

雜湊在 [`study/test-cases.toml`](test-cases.toml) 的 `[freeze].sha256`。

| | 預測 | 錯了代表什麼 |
|---|---|---|
| `P1-1` | LAN 是 **10.1.1.1/24**（`fwrecon` 與廠商 `flash get` 兩個來源一致） | 解出來的設定與實際跑的不是同一份 |
| `P1-2` / `P6-11` | **22 和 23 都關**，80 開 | `COMPCS` 的旗標不是實際生效的那份 |
| `P1-2` | **5555 關**（`/bin/skt` 在這個 build 已被刪） | 有第二個沒找到的東西在監聽 |
| `P1-3` | `Server:` 可辨識為 Boa 0.94.14rc21；未認證可取的頁面是那 143 檔的子集 | docroot 不只是 `w6cg` 展開的內容 |
| `P1-5` | **57 還是 60** —— Ghidra 讀 `root_form[]` 得 57，`fwrecon` 抽字串得 60 | **測的是工具，不是裝置** |
| `P1-8` | `/boafrm/` 有回應，`/goform/` 沒有 | 這台不是純 Boa |
| `P1-10` | **1900 有回應**（`UPNP_ENABLED=1`） | 旗標不是啟動條件，`sysconf` 還有別的閘 |
| `P1-12` | 上電到 web 可服務 **< 40 秒** | bootlog 時間戳不是牆鐘時間 |
| `P2-1` | `/boafrm/*` 的 POST 整批在門外（門只看 `.htm` / `.asp`） | `auth-flow-2018.md` 的指令級讀法有漏 |

## 3.1 把網路卡交給 WSL

網路卡是 `2-4  0bda:8153  Realtek USB GbE`，狀態 `Not shared`，所以要先 bind。
**bind 需要系統管理員；attach 不用。**

```powershell
# 系統管理員 PowerShell，一次就好
usbipd bind --busid 2-4
```

```powershell
# 一般 PowerShell
usbipd attach --wsl --busid 2-4
usbipd list          # 2-4 應該變成 Attached
```

WSL 裡確認，並手動指定位址（**不要靠 DHCP**——`P1-1` 要測的正是它派不派得出來）：

```bash
ip -br link                     # 找新出現的介面，通常是 eth1
sudo ip link set eth1 up
sudo ip addr flush dev eth1
sudo ip addr add 10.1.1.100/24 dev eth1
ip -br addr show eth1
```

## 3.2 `P0-4` — 隔離確認，在送任何東西之前

```bash
sudo tcpdump -ni eth1 -w ~/fwre-work/dumps/w05-lab-$(date +%H%M).pcap &
sleep 20
sudo kill %1
tshark -r ~/fwre-work/dumps/w05-lab-*.pcap -T fields -e eth.src 2>/dev/null | sort -u
```

**測前寫下的成功條件：`eth.src` 只出現兩個 MAC。**

> ❌ **出現第三個 MAC，或看到對外的 DNS / HTTP → 隔離不成立，停手。**
> 也再確認一次 **WAN 埠是空的**。

## 3.3 `P1-1` / `P1-2` / `P6-11` — 位址與埠

```bash
ping -c 3 10.1.1.1
```

```bash
# 全 TCP。約 2–5 分鐘
sudo nmap -sS -p- --reason -oA ~/fwre-work/dumps/w05-tcp 10.1.1.1

# 重點 UDP（1900 UPnP / 53 / 67 / 161 SNMP）
sudo nmap -sU -p 53,67,69,123,161,1900,5353 --reason -oA ~/fwre-work/dumps/w05-udp 10.1.1.1
```

**逐條對照 3.0 的表。** 特別是：

> 🔴 **如果 5555 是開的 —— 停下所有事。** `/bin/skt` 在這個 build 已被刪除
> （W02 Day 4，三版橫讀），所以 5555 上有東西監聽意味著**還有第二個我沒找到的東西**。
> 那比命中任何一個預測都重要。

> 🔴 **如果 23 或 22 是開的** —— `COMPCS` 解出來的旗標不是實際生效的那份，
> `compcs-decode.md` 和 `credentials.md` 的結論都要重寫。而且要注意：
> `/bin/startup.sh` 在「DS 與 CS 都無效」的分支裡會執行 `flash set TELNET_ENABLED 1`，
> 所以 telnet 開著也可能代表**這台的設定區曾經壞過**。

## 3.4 `P1-12` — 上電到 web 可服務的時間

```bash
# 先斷電。這一行會一直重試，看到第一個回應就印出秒數。
# 開始跑之後再插電。
python3 - <<'EOF'
import socket, time
t0 = time.time()
while time.time() - t0 < 120:
    try:
        s = socket.create_connection(("10.1.1.1", 80), 1.0); s.close()
        print(f"web answered after {time.time()-t0:.1f} s"); break
    except OSError:
        time.sleep(0.25)
else:
    print("no answer within 120 s")
EOF
```

## 3.5 `P1-3` / `P1-5` / `P1-6` / `P1-8` / `P2-*` — HTTP，用工具不要手打

**為什麼不是一頁 `curl`**：這裡有三輪 57 個端點的掃描，而其中一個失敗模式是無聲的
—— **POST 少帶 `submit-url` 會讓 handler `strcpy("/status.htm")` 寫進唯讀段**
（[`submit-url-overflow.md`](../notes/submit-url-overflow.md)），照程式碼讀那會打掛
web server，然後**後面每一個端點都會回「連不上」，看起來就跟「端點不存在」一模一樣**。
一次打錯，整輪普查變成整輪偽陰性。

[`tools/bench-probe.py`](../tools/bench-probe.py) 擋掉這件事，而且：
每一次請求都留逐字紀錄、**每 10–20 個請求重跑一次對照組**（否則「後半段全失敗」
無從得知是從哪裡開始的）、參數裡有 shell 元字元就拒絕送（注入是 W06 的事）。
守衛套件 `bash tools/test-bench-probe.sh` 證明這些拒絕會觸發，8 個案例。

```bash
cd /mnt/c/Users/Key20/Desktop/router
D=~/fwre-work/dumps

python3 tools/bench-probe.py control     --host 10.1.1.1
python3 tools/bench-probe.py fingerprint --host 10.1.1.1 -o $D/w05-fingerprint.json
python3 tools/bench-probe.py gate        --host 10.1.1.1 -o $D/w05-gate.json
python3 tools/bench-probe.py endpoints   --host 10.1.1.1 -o $D/w05-endpoints.json
python3 tools/bench-probe.py ssdp        --host 10.1.1.1 -o $D/w05-ssdp.json
```

> ⚠️ **`endpoints` 預設走 GET。** 加 `--allow-post` 會讓它 POST，而
> **POST 會真的執行那個 handler** —— `formWlanSetup` 收到一個只有 `submit-url`
> 的 POST，其他參數全部取到預設值，那可能就是把無線設定清掉。
> 要跑 POST 版本的話，**前後各抓一次 64 KiB 設定區快照**，
> 然後 `cmp` —— 那既是安全網，也是一次 Oracle 4 的預演。

## 3.6 `P2-8` / `P2-7` — 憑證與 session

密碼**已經從 flash 解出來**（`USER_NAME` / `USER_PASSWORD` = `admin` / `admin`，
明文，兩個獨立來源：`fwrecon compcs` 與廠商自己的 `flash get`）。
所以登入成功是**在自己的機器上端到端證實 CVE-2019-19823**，不是猜密碼。

session 模型（`P2-7`）用兩個 IP 測：登入之後，**從第二個位址**帶同一組 cookie 打管理頁。

```bash
sudo ip addr add 10.1.1.101/24 dev eth1        # 第二個來源位址
curl -sD- --interface 10.1.1.101 -b cookies.txt http://10.1.1.1/status.htm -o /dev/null
```

通了 → 不是 IP 綁定。擋了 → 是。**這一測直接分辨 `auth-flow-2018.md` 留下的分支，
不必再讀一行組語。**

## 3.7 記錄

跑完每一項：

```bash
python3 tools/rtcase.py record --id P1-2 --date 2026-08-17 \
    --verdict confirmed --evidence dynamic \
    --artefact dumps/w05-tcp.nmap --note "80 開；22/23/5555 皆關"
make ledger
```

> ⚠️ `--artefact` 的路徑必須存在**在 repo 裡**。`~/fwre-work/dumps/` 不在 repo 裡，
> 所以要嘛把摘要複製進 `reports/`，要嘛把 artefact 指向 `study/W05-bench-runsheet.md`
> 這一份紀錄。**`rtcase check` 會擋掉指向不存在檔案的證據連結。**

---

## 出事的時候

| 症狀 | 怎麼辦 |
|---|---|
| 打錯 `FLW` 的參數 | **不要再送任何指令。** 拍下整個 console 畫面，回報。多送一個指令可能把可回復的變成不可回復的 |
| console 全是亂碼 | 鮑率錯（是 **38400**，不是 115200），或 GND 沒接好 |
| `<RealTek>` 之後第一個指令回 `Unknown command !` | 正常，是 ESC 塞在緩衝區。按 Enter 清掉再送 |
| `DB` 印出來的內容跟上一次一模一樣 | `FLR` 沒生效（多半是 `Y` 被下一個指令吃掉了）。**那份資料是 RAM 裡的舊值，不是 flash** |
| 板子不會開機了 | `Phase 2` 只碰 `0x3F0000`，那裡沒有東西會被讀。如果真的不開機，原因不在這裡，回報 |
