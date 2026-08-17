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
| **最後驗證** | 這一節的命令**最後一次真的被執行**是哪一天。舊的日期代表要小心 |

> **實體動作用 🔌 標記。** 那幾步腳本做不到,只有你的手做得到。

---

# Part A — 程序

## A0 開工前:讓機器自己說它準備好了沒

| | |
|---|---|
| **層** | T1 / T2 / T3(各自檢查) |
| **會不會改變裝置** | 純讀,而且**完全不碰裝置** |
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

## A2 🔌 把 USB 裝置交給 WSL

| | |
|---|---|
| **層** | T2(序列)/ T3(再加網卡) |
| **會不會改變裝置** | 純讀 |
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

## A9 🔌 POST 輪 —— **這一節會改變裝置的設定**

| | |
|---|---|
| **層** | T3 |
| **會不會改變裝置** | **改設定。而且它已經證明會把 web server 弄掉。** |
| **前置** | **`A5` 的快照必須已經抓好** |
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

## A12 🔌🔴 寫 flash(`FLW`)—— **唯一不可逆的一節**

| | |
|---|---|
| **層** | T2 |
| **會不會改變裝置** | **不可逆** |
| **前置** | **兩份 dump 的雜湊都對過**(`make doctor TIER=2`);`A5` 的快照已抓 |
| **最後驗證** | 2026-08-17 |

**開始之前,三件事缺一不可:**

```bash
make doctor TIER=2
```

必須看到 `two independent reads agree — there is a safety net`。

> ❌ **只有一份 dump,或雜湊不符 → 不要寫。** 那是這台的唯一備份。

**已知的機制(2026-08-17 量到的,帶對照組):**

`FLW` 是**讀出整個磁區 → 改指定 byte → 抹除磁區 → 整段寫回**。
所以:**磁區內其餘內容會被保留**,但**寫入中途斷電失去的是整個 4 KiB,不是幾個 byte**。

而 loader 的指令集裡**一個抹除指令都沒有**,所以抹除只能由 `FLW` 自己做 ——
這是那個推論的第三條證據。

> 🔴 **`H601`(`0x006000`,這台的 MAC 與射頻校準)整個住在一個磁區裡,
> 而 `HW_WLAN0_WSC_PIN` 在 `0x648a` —— 也在那個磁區裡。**
> 寫它就是重寫那 4 KiB。全世界只有這一份。

**手打的時候,每一步的規矩:**

```text
DB <新的 RAM 位址> 8          ← 對照組:先看那塊 RAM 現在是什麼
FLR <同一個位址> <flash 位移> 8
Y                              ← 一定要,而且 FLR 會把下一行整個吃掉當答案
DB <同一個位址> 8              ← 內容有變 = FLR 生效了
```

> 🔴 **兩個會安靜害死你的坑:**
> 1. **`FLR` 的長度是十六進位,`DB` 的長度是十進位。** `DB <addr> 100` 回你
>    100 bytes 不是 0x100。**沒有任何警告,你會拿到格式完全正常、長度錯誤的 dump。**
> 2. **`FLR` 問 `(Y)es , (N)o ?` 並且把下一行整個吃掉。** 腳本裡直接送下一個指令
>    會得到 `Abort!`,然後那個 `DB` 印出來的是 **RAM 裡上一次留下的舊資料**,
>    而你會以為那是 flash 的內容。

> 🔴 **`FLW` 和 `FLR` 的確認提示標點不同** ——
> `FLW` 是 `(Y)es, (N)o->`,`FLR` 是 `(Y)es , (N)o ? -->`。相鄰兩個指令,兩種標點。

> ⚠️ **`FLW` 成功不印 `Flash Write Successed!`,只印一個句點 `.`。**
> 那句話確實存在於 loader 裡(stage2 `0x0a861`),但它屬於 **TFTP 自動燒錄路徑**,
> 不是互動式 `FLW`。互動式的訊息長這樣:
> ```text
> Write 0x00000008 Bytes to SPI flash#1, offset 0x003f0000<0xbd3f0000>, from RAM 0x80530000 to 0x80530008
> (Y)es, (N)o->Y
> .
> ```

> ❌ **打錯 `FLW` 的參數:不要再送任何指令。拍下整個畫面再說。**

**能用工具就用工具** —— 讀取一律走這個,它有正對照組:

```bash
python3 -u tools/console-dump.py dump --at-prompt \
        --flash 0x3F0100 --length 8 --ram 0x80560000 --chunk 8 \
        -o "$HOME/fwre-work/dumps/probe.bin"
xxd "$HOME/fwre-work/dumps/probe.bin"
```

**它比手打多三件事,而第三件是關鍵:** 確認 `(Y)es` 真的被接受;每一塊解析驗證加二次取樣;
**對照組先把 flash `0x000000` 讀進同一個 `--ram`**,比對已知的 `0b f0 00 04` ——
所以真正的讀取之前,那塊 RAM 裝的是**第三種東西**。
**「換一個沒用過的位址」比不上這個:沒用過的位址裡是什麼,你並不知道。**

---

## A13 收尾與紀錄

| | |
|---|---|
| **層** | T1(記錄本身不碰裝置) |
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
