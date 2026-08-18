# RUNBOOK — 從零開始跑完一次

> **這份文件的讀者是兩種人：**
> 1. 三個月後把一切都忘光的我自己
> 2. 完全沒碰過逆向工程的人（高中生程度）
>
> 所以每一步都有：**要打什麼指令 → 應該看到什麼 → 沒看到怎麼辦**。
> 看不懂的名詞先跳過，[§11 名詞表](#11-名詞表)有解釋。
>
> **維護規則：每次做完新的一段工作，都要回來更新這份文件。**
> 規則寫在 [§13](#13-怎麼維護這份文件)。

---

## 目錄

| § | 內容 | 需要時間 |
|---|---|---|
| [1](#1-你會得到什麼) | 你會得到什麼 | 讀 2 分鐘 |
| [2](#2-開始前的準備) | 開始前的準備 | 5 分鐘 |
| [3](#3-五分鐘概念補課) | 五分鐘概念補課 | 讀 5 分鐘 |
| [4](#4-part-0--環境建置) | **Part 0** — 環境建置 | 30–45 分鐘 |
| [5](#5-part-1--取得韌體) | **Part 1** — 取得韌體 | 1 分鐘 |
| [6](#6-part-2--解包韌體) | **Part 2** — 解包韌體 | 1 分鐘 |
| [7](#7-part-3--產生分析報告) | **Part 3** — 產生分析報告 | 10 秒 |
| [8](#8-part-4--ghidra-靜態分析) | **Part 4** — Ghidra 靜態分析 | 10 分鐘 |
| [8.5](#85-part-5--讀出授權流程w03) | **Part 5** — 讀出授權流程（W03） | 讀 20 分鐘 |
| [8.6](#86-part-6--硬體開工料件辨識w02-day-1) | **Part 6** — 硬體開工：料件辨識（W02 Day 1） | 2–3 小時 |
| [8.7](#87-part-7--序列-console-與-flash-讀取w02-day-23) | **Part 7** — 序列 console 與 flash 讀取（W02 Day 2–3） | 3–4 小時 |
| [9](#9-驗收) | 驗收：G0 與 G1 | 10 分鐘 |
| [10](#10-疑難排解) | 疑難排解 | 出事再看 |
| [11](#11-名詞表) | 名詞表 | 查閱 |
| [12](#12-一頁速查表) | 一頁速查表 | 熟了之後只看這頁 |
| [12.5](#125-下一階段開工前要先裝的東西) | **W02 / W05 開工前要補裝的東西** | 開新階段前必看 |
| [13](#13-怎麼維護這份文件) | 怎麼維護這份文件 | 讀 2 分鐘 |
| [14](#14-變更紀錄) | 變更紀錄 | — |

---

## 1. 你會得到什麼

跑完之後，你手上會有：

1. **一台路由器的韌體被完整拆開** —— 從一個 3.4 MB 的 `.web` 檔，變成 165 個檔案的完整 Linux 檔案系統
2. **兩個版本的對照**（2015 年 vs 2020 年），可以看出廠商在漏洞被公開後到底改了什麼
3. **一份自動產生的分析報告**，列出所有網頁端點、所有會執行系統指令的程式、所有可疑的檔案連結
4. **Ghidra 裡的反組譯專案**，以及一份「該從哪個函式開始看」的清單

全部都是**指令跑出來的**，不需要你手動點來點去。

---

## 2. 開始前的準備

### 你需要

| 項目 | 需求 | 怎麼確認 |
|---|---|---|
| 作業系統 | Windows 10/11（64 位元） | 開始鍵 → 設定 → 系統 → 關於 |
| 硬碟空間 | **至少 5 GB** | 檔案總管看 C 槽 |
| 記憶體 | 8 GB 以上 | 工作管理員 → 效能 |
| 網路 | 要下載約 1 GB | — |
| 權限 | **不需要管理員** | 這是刻意設計的，見 §10.1 |

實際佔用（我這台實測）：

```
WSL 端    ~136 MB(韌體 6.6 MB + 解包後 21 MB + Python 環境 108 MB)
          + apt 套件約 500 MB
Windows 端 JDK 328 MB + Ghidra 872 MB + 下載快取 742 MB(事後可刪)
```

### 為什麼要用 WSL

WSL = Windows Subsystem for Linux，讓你在 Windows 裡跑一個真的 Linux。

**逆向 Linux 韌體必須在 Linux 上做。** 韌體裡有符號連結（symlink）、有 Unix 權限位元，Windows 的檔案系統存不下這些東西 —— 存不下就等於**資料會悄悄消失，而且不會報錯**。這個專案最重要的一個發現（`/web/config.dat` 是個符號連結）在 Windows 上解包會直接看不到。

詳見 [`docs/workspace-layout.md`](docs/workspace-layout.md)。

---

## 3. 五分鐘概念補課

> 已經懂的人直接跳到 [§4](#4-part-0--環境建置)。

### 韌體（firmware）是什麼

路由器裡面其實是一台小電腦，它也要跑作業系統。那個作業系統 + 所有程式打包成一個檔案，就叫**韌體**。你在官網下載的 `.web` 檔就是它。

### 這個 `.web` 檔裡面有什麼

不是壓縮檔，是**好幾塊東西黏在一起**，每塊前面有 16 個位元組的標頭說明「我是什麼、我要被燒到快閃記憶體的哪個位置」。

```
┌──────────┬────────────────────────────────────────┐
│ 標頭 16B │ 網頁介面資料 (bzip2 壓縮)              │  ← 只有 2015 版有
├──────────┼────────────────────────────────────────┤
│ 標頭 16B │ Linux 核心 (LZMA 壓縮)                 │
├──────────┼────────────────────────────────────────┤
│ 標頭 16B │ 根檔案系統 (SquashFS)   ← 我們主要要的 │
└──────────┴────────────────────────────────────────┘
```

這個格式是我們**自己逆出來的**，沒有官方文件。`fwrecon` 就是照這個格式寫的解析器。

### 根檔案系統（rootfs）

就是 Linux 的 `/` 目錄 —— `/bin`、`/etc`、`/lib` 那一整套。用 **SquashFS** 格式壓起來，唯讀。

解開後你會看到：

```
bin/  dev/  etc/  home/  lib/  mnt/  proc/  sys/  tmp/  usr/  var/  web/
```

跟一般 Linux 一模一樣，只是小很多。

### MIPS 和「端序」

你的電腦是 **x86** 架構，這台路由器是 **MIPS** 架構 —— 指令集完全不同，所以路由器裡的程式**不能**在你電腦上直接執行。

**端序（endianness）**是指多位元組數字的排列方向。數字 `0x12345678` 存進記憶體：

```
大端序 Big Endian    : 12 34 56 78   ← 這台路由器是這個
小端序 Little Endian : 78 56 34 12   ← 你的 x86 電腦是這個
```

搞錯端序的話，反組譯出來會是一堆垃圾。所以這是一開始就要先確定的事。

### Boa 是什麼

`/bin/boa` 是這台路由器的**網頁伺服器** —— 你在瀏覽器打 `192.168.1.1` 進去看到的設定頁面，就是它吐出來的。

它是 2005 年就停止維護的老軟體（版本 `0.94.14rc21`），而且**用 root 身分執行**。這代表它只要有一個漏洞，攻擊者就直接拿到最高權限，沒有第二道關卡。

### CVE 是什麼

**CVE = 公開漏洞編號**。全世界共用的漏洞編號系統，格式 `CVE-年份-流水號`。

這個專案研究的是**已經公開、已經修好**的舊漏洞 —— 目的是學習「漏洞長什麼樣、為什麼會發生」，不是攻擊別人的設備。

> ⚠️ **法律與道德底線**
> - 只拆**自己買的**硬體
> - 只在**隔離網路**測試，不連上線設備
> - 不碰 ISP 的機器（中華電信的數據機不是你的）
> - 真的找到新漏洞 → 走 TWCERT/CC 責任揭露，不公開

---

## 4. Part 0 — 環境建置

> ⏱ 30–45 分鐘，大部分時間在等下載。
> 這一段**只要做一次**，之後都不用重跑。

### 4.1 安裝 WSL（如果還沒有）

按 **開始鍵 → 打 `PowerShell` → 右鍵 → 以系統管理員身分執行**，然後：

```powershell
wsl --install -d Ubuntu-24.04
```

> 這是整個流程**唯一**需要管理員權限的一步，而且只有第一次要。

裝完會要你**重開機**。重開後 Ubuntu 會自己跳出來，叫你設一組 Linux 的使用者名稱和密碼。

> 💡 這個密碼跟你的 Windows 密碼無關，是 Linux 內部用的。**記起來**，後面 `sudo` 會用到。

**確認裝好了：**

```powershell
wsl --list --verbose
```

應該看到：

```
  NAME            STATE           VERSION
* Ubuntu-24.04    Running         2
```

`VERSION` 一定要是 **2**。是 1 的話跑 `wsl --set-version Ubuntu-24.04 2`。

### 4.2 取得這個專案

在 **一般的**（不用管理員）PowerShell 裡：

```powershell
cd $env:USERPROFILE\Desktop
git clone https://github.com/Jhongwe1/router-firmware-re.git router
cd router
```

沒有 git 的話：`winget install Git.Git`，然後**關掉 PowerShell 重開**。

> 📌 **之後所有指令都假設你在這個目錄裡。**
> 我的路徑是 `C:\Users\Key20\Desktop\router`，你的可能不同，下面看到這個路徑就換成你自己的。

### 4.3 Windows 端：Java + Ghidra

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup\setup-windows.ps1 all
```

**這會做什麼：**

1. 下載 **Temurin JDK 21**（205 MB）—— Ghidra 是 Java 寫的，需要它
2. 下載 **Ghidra 12.1.2**（547 MB）—— 美國 NSA 開發並開源的反組譯工具
3. **兩個都比對官方公布的 SHA-256**，不符就刪檔中止
4. 解壓到 `%LOCALAPPDATA%\fwre-tools\`（你的使用者目錄，**不需要管理員**）

⏱ 看網速，大概 5–20 分鐘。中間沒有進度條是正常的，PowerShell 關掉進度條才不會慢十倍。

**應該看到：**

```
 ==>   jdk: downloading OpenJDK21U-jdk_x64_windows_hotspot_21.0.12_8.zip
  ok   jdk: SHA-256 verified
  ok   JDK 21.0.12+8 installed; JAVA_HOME=C:\Users\...\fwre-tools\jdk-21.0.12+8
 ==>   ghidra: downloading ghidra_12.1.2_PUBLIC_20260605.zip
  ok   ghidra: SHA-256 verified
  ok   GHIDRA_INSTALL_DIR set to C:\Users\...\fwre-tools\ghidra_12.1.2_PUBLIC

=== G0 gate: Windows-side toolchain ===
  ok   java  openjdk 21.0.12 2026-07-21 LTS
  ok   ghidra ghidraRun.bat
  ok   ghidra support\analyzeHeadless.bat

  ok   G0 (Windows) GREEN
```

看到 **`G0 (Windows) GREEN`** 就成功了。

> 🔔 **中途可能跳出「Windows 防火牆」問你私人/公共網路** —— 那是 Java。
> **按取消就好**，我們的分析完全在本機跑，不需要網路。

### 4.4 WSL 端：逆向工具鏈

```powershell
wsl -d Ubuntu-24.04 bash /mnt/c/Users/Key20/Desktop/router/tools/setup/setup-wsl.sh all
```

> 路徑換成你自己的。Windows 的 `C:\` 在 WSL 裡叫 `/mnt/c/`，反斜線要換成斜線。

**這會做什麼：**

| 階段 | 裝什麼 | 為什麼要 |
|---|---|---|
| `apt` | 39 個系統套件 | 壓縮格式、SquashFS 工具、MIPS 模擬器、燒錄工具 |
| `rust` | Rust 編譯器 | binwalk v3 是 Rust 寫的，要自己編 |
| `binwalk` | binwalk 3.1.0 | 掃描檔案裡藏了什麼格式 |
| `sasquatch` | 修改版 unsquashfs | 廠商的 SquashFS 有非標準變體，原版解不開 |
| `unblob` | unblob 26.6.4 | 另一套解包工具，拿來對答案 |
| `path` | 改 `~/.bashrc` | 讓新開的終端機找得到上面這些 |
| `verify` | 逐一執行每個工具 | **不是檢查檔案在不在，是真的跑跑看** |

⏱ 5–15 分鐘，大部分在編譯 binwalk。

**中途會問你 Linux 密碼**（裝系統套件要 `sudo`），就是 §4.1 設的那組。

**應該看到：**

```
=== G0 gate: toolchain verification ===
  ok   binwalk                /home/key/.cargo/bin/binwalk
  ok   unblob                 /home/key/.local/bin/unblob
  ok   sasquatch              /usr/bin/sasquatch
  ok   sasquatch-v4be         /usr/bin/sasquatch-v4be
  ok   unsquashfs             /usr/bin/unsquashfs
  ok   qemu-mips-static       /usr/bin/qemu-mips-static
  ok   qemu-mipsel-static     /usr/bin/qemu-mipsel-static
  ok   flashrom               /usr/sbin/flashrom
  ok   picocom                /usr/bin/picocom
  ok   7z                     /usr/bin/7z
  ok   cpio                   /usr/bin/cpio
  ok   readelf                /usr/bin/readelf
  ok   strings                /usr/bin/strings
  ok   jq                     /usr/bin/jq

  ok   G0 GREEN — all tools functional
```

看到 **`G0 GREEN`** 就成功了。有紅字 `FAIL` 的話翻 [§10 疑難排解](#10-疑難排解)。

> 💡 這個腳本**可以重複執行**。裝到一半失敗，直接再跑一次就好，已經裝好的會跳過。

### 4.5 之後每次開工

從這裡開始，**進 WSL 工作比較方便**。開一個 PowerShell：

```powershell
wsl -d Ubuntu-24.04
```

提示字元會變成 Linux 的樣子（像 `key@K:~$`）。然後：

```bash
cd /mnt/c/Users/Key20/Desktop/router
```

> 📌 **下面 §5–§7 的指令都在這個 WSL 環境裡打。**
> §8 的 Ghidra 要回到 PowerShell（因為 Ghidra 裝在 Windows 端）。
> 打 `exit` 可以離開 WSL 回到 PowerShell。

---

## 5. Part 1 — 取得韌體

```bash
make fetch
```

**這會做什麼：**

1. 讀 [`firmware/SOURCES.json`](firmware/SOURCES.json) —— 裡面寫著要抓哪兩個檔、從哪抓、雜湊值應該是多少
2. 下載到 `~/fwre-work/firmware/`（**不是**在專案資料夾裡，見下方說明）
3. 逐一比對 **檔案大小 / MD5 / SHA-1 / SHA-256**
4. 把實際結果寫進 [`firmware/MANIFEST.json`](firmware/MANIFEST.json)

**應該看到：**

```
  ok   downloaded 3469005 bytes
  ok   size    matches declared value
  ok   md5     matches declared value
  ok   sha1    matches declared value
  ok   sha256  matches declared value
  ok   recorded in firmware/MANIFEST.json
...
  ok   all images fetched and verified
```

⏱ 約 11 秒。

### 為什麼要這麼囉嗦地驗雜湊

因為**分析結果只有在「知道分析的是哪些位元組」的前提下才有意義**。

網路上叫「N150RT 韌體」的檔案有好幾個不同版本，鏡像站也會偷偷換檔。所以：

- `SOURCES.json` = **我打算抓什麼**（手寫的，含預期雜湊）
- `MANIFEST.json` = **我實際抓到什麼**（程式產生的）

兩個對不起來就會報錯，而不是默默讓後面所有結論失效。

2015 那版的 MD5/SHA-1 是從 **archive.org 的 metadata API** 抄來的，不是我自己算的 —— 所以可以拿一個我們控制不了的來源驗證：

```bash
curl -s https://archive.org/metadata/TOTOLINKN150RTV2.1.2B20150825.1601 \
  | jq '.files[] | select(.name|endswith(".web")) | {name, size, md5, sha1}'
```

### 為什麼韌體不放進 git

那是廠商的檔案，**不是我們的東西，不能散布**。這個 repo 只放「怎麼拿到 + 雜湊多少」，讓任何人都能自己抓到一模一樣的位元組。

---

## 6. Part 2 — 解包韌體

```bash
make unpack
```

**這會做什麼：**

1. 用 `fwrecon` 解析 `.web` 的容器格式，算出根檔案系統在**第幾個位元組**
2. 用 `dd` 把那一段切出來
3. 用 `unsquashfs` 解開；失敗才退回用 `sasquatch`
4. **檢查解出來的樹裡有沒有符號連結** —— 沒有就直接失敗

**應該看到：**

```
--- v2.1.2 (TOTOLINK-N150RT-V2.1.2-B20150825.1601.web) ----------
  ok   rootfs at file offset 1294004 (2174978 bytes, lzma-compressed)
  ok   carved 2174978 bytes -> /home/key/fwre-work/extracted/v2.1.2/rootfs.squashfs
 warn  unsquashfs returned non-zero but produced a tree (device nodes and
 warn  ownership need root; file contents and modes are intact)
  ok   extracted: 165 files, 20 dirs, 99 symlinks

--- v3.4.0 (TOTOLINK-N150RT-V3.4.0-B20201030.1142.web) ----------
  ok   rootfs at file offset 1234978 (2158594 bytes, xz-compressed)
  ok   carved 2158594 bytes -> /home/key/fwre-work/extracted/v3.4.0/rootfs.squashfs
 warn  unsquashfs returned non-zero but produced a tree ...
  ok   extracted: 364 files, 33 dirs, 103 symlinks

  ok   all images unpacked into /home/key/fwre-work/extracted
```

⏱ 約 10 秒。

> ✅ **那兩行 `warn` 是正常的，不是錯誤。**
> `unsquashfs` 用一般使用者身分跑，沒辦法建立裝置節點（`/dev/*`）也沒辦法改檔案擁有者，所以它回傳非零。但**檔案內容和權限位元都是完整的**，那才是我們要的。
> 腳本因此不看回傳值，改看「有沒有解出東西、裡面有沒有符號連結」。

### 自己看看解出了什麼

```bash
ls ~/fwre-work/extracted/v2.1.2/squashfs-root/
```

```
bin  dev  etc  home  init  lib  mnt  proc  sys  tmp  usr  var  web
```

**這就是一台路由器的完整作業系統**，躺在你的硬碟上。逛逛看：

```bash
# 網頁伺服器本體
ls -la ~/fwre-work/extracted/v2.1.2/squashfs-root/bin/boa

# 開機時執行的腳本 —— 看第 108-110 行
cat -n ~/fwre-work/extracted/v2.1.2/squashfs-root/etc/init.d/rcS | sed -n '105,111p'
```

你會看到：

```
   105	#echo 1 > /proc/sys/net/ipv4/ip_forward #don't enable ip_forward before set MASQUERADE
   106	#echo 2048 > /proc/sys/net/core/hot_list_length
   107	
   108	# start web server
   109	boa
   110	#skt&
   111	
```

**第 110 行前面那個 `#` 就是本專案最有意思的發現之一。** `skt` 是 2015 年被公開的後門程式，廠商的「修補」方式是**把啟動那行註解掉**，但 `/bin/skt` 這個檔案還好好地留在韌體裡。詳見 [`notes/prior-art.md`](notes/prior-art.md)。

---

## 7. Part 3 — 產生分析報告　→ `runsheet.md` `A1.2`

```bash
make recon
```

**這會做什麼：** 對兩個版本各產生 JSON + Markdown 報告，再做一份版本差異對照，全部寫進 [`reports/`](reports/)。

⏱ 約 10 秒。

**應該看到 5 個檔案被寫出來：**

```
wrote reports/n150rt-2.1.2.json
wrote reports/n150rt-2.1.2.md
wrote reports/n150rt-3.4.0.json
wrote reports/n150rt-3.4.0.md
wrote reports/diff-2.1.2-to-3.4.0.md
```

### 看報告

```bash
# 用預設程式開(Windows 記事本 / VS Code)
explorer.exe reports

# 或直接在終端機看重點
jq -r '.findings[] | "[\(.severity)] \(.kind): \(.detail)"' reports/n150rt-3.4.0.json
```

```
[high] web-exposed-runtime-file: /web/ca.cer -> /var/ca.cer
[high] web-exposed-runtime-file: /web/config.dat -> /var/config.dat
[high] web-exposed-runtime-file: /web/user.cer -> /var/user.cer
[medium] service-disabled-not-removed: miniigd, snmpd, telnetd, tr069
[info] command-exec-surface: 17 binaries import system()/popen()/exec*()
[info] no-nx-marker: 4 binaries have no PT_GNU_STACK segment
[info] web-handler-surface: 49 form handlers in /bin/boa
...
```

**那三個 `high` 是什麼意思：**

路由器的檔案系統是唯讀的，所以會變動的東西都放在 `/var`（開機時建立的暫存空間）。而 `/web/config.dat` 是一個**指向 `/var/config.dat` 的符號連結**，`/web` 又是網頁伺服器對外公開的目錄。

翻成白話：**路由器把自己的設定檔（裡面有帳號密碼）放進了對外公開的網頁目錄。** 這就是 CVE-2019-19822 的成因。

> ⚠️ 但要小心：這只證明「檔案在公開目錄裡」，**不等於「不用登入就能下載」**。
> 也可能 Boa 在處理請求時有做認證檢查。要確認就得進 Ghidra 讀程式碼 —— 那是下一個階段的工作。
>
> **能區分「我觀察到什麼」和「我推論出什麼」，是這行最重要的紀律。**

### 看版本差異

```bash
cat reports/diff-2.1.2-to-3.4.0.md
```

這份會告訴你 2015 → 2020 之間：哪些網頁端點被加了、哪些被拿掉、哪些執行檔消失了（例如 `/bin/skt`）、哪些符號連結是新增的。

---

## 8. Part 4 — Ghidra 靜態分析

> 這一段要**回到 PowerShell**（Ghidra 裝在 Windows 端）。WSL 裡打 `exit` 離開。

### Ghidra 是什麼

把機器碼**還原成接近 C 語言的程式碼**的工具，NSA 開發並開源。

路由器裡的 `/bin/boa` 是編譯好的執行檔，人類讀不懂。Ghidra 可以把它變回大致看得懂的樣子。

### 兩個步驟，不是一個

- **`import.ps1`** = 匯入 + 跑自動分析。**貴**（每支好幾分鐘），但結果會存進專案，只要跑一次。
- **`analyze.ps1`** = 對已經分析好的程式跑一支腳本。**便宜**（幾秒），可以一直重跑。

W01 的版本把兩件事綁在一起，結果每改一行腳本就要重新分析一次。分開之後才有辦法做 W03 那種「改腳本 → 重跑 → 看結果」的迴圈。

### 步驟一：匯入 + 自動分析

```powershell
cd $env:USERPROFILE\Desktop\router

$boa2015 = '\\wsl$\Ubuntu-24.04\home\key\fwre-work\extracted\v2.1.2\squashfs-root\bin\boa'
$boa2020 = '\\wsl$\Ubuntu-24.04\home\key\fwre-work\extracted\v3.4.0\squashfs-root\bin\boa'
$skt     = '\\wsl$\Ubuntu-24.04\home\key\fwre-work\extracted\v2.1.2\squashfs-root\bin\skt'

.\ghidra\import.ps1 -Label 2.1.2     -Binary $boa2015
.\ghidra\import.ps1 -Label 3.4.0     -Binary $boa2020
.\ghidra\import.ps1 -Label 2.1.2-skt -Binary $skt
```

> 📌 `\\wsl$\Ubuntu-24.04\home\key\...` 是**從 Windows 看 WSL 檔案**的路徑。
> `key` 換成你的 Linux 使用者名稱（在 WSL 裡打 `whoami` 可以查）。
>
> 這樣做的用意：資料**只有一份**，躺在 WSL 的 Linux 檔案系統上，Windows 這邊只是讀它。不會有兩份不同步的問題。

**應該看到：**

```
 ==>  importing \\wsl$\...\bin\boa
      project : ...\ghidra-projects\totolink-n150rt/2.1.2
      sha256  : ddda5a4f3c65b54b96d8cc485f617daf049ad70eab42ac57e87b4b005f17d97a
  ok   analysed and stored under totolink-n150rt/2.1.2
```

⏱ 三支加起來約 5 分鐘。

> ⚠️ **`-Label` 為什麼是資料夾，不只是個標籤**
>
> `analyzeHeadless -import <path>` 是用**檔名**幫 program 命名的。兩個版本的檔案
> 都叫 `boa`，所以 W01 的寫法讓它們變成同一個名字，再加上 `-overwrite`，
> **第二次匯入會把第一次的無聲蓋掉**。
>
> 現在每個版本進自己的 project folder（`totolink-n150rt/2.1.2` 等），而且每份
> 報告都會帶上被分析檔案的 SHA-256。一份說不出自己分析了哪個檔案的報告，不算證據。

**`MIPS:BE:32:default` 這行很重要** —— `BE` = Big Endian。Ghidra 自己從檔案標頭判斷出來的，跟我們前面用別的方法算出來的答案一致。**兩個獨立來源得到同一個答案，才敢當結論用。**

### 步驟二：跑分析腳本

```powershell
# W01 的字串交叉引用
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaStringXrefs -Binary $boa2015

# W03:把 /boafrm/ 分派表挖出來,並把所有 handler 命名寫回專案
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaFormTable -Binary $boa2015
.\ghidra\analyze.ps1 -Label 3.4.0 -Script BoaFormTable -Binary $boa2020

# W03:危險函式呼叫點普查(要在 BoaFormTable 之後跑,才認得出 handler)
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaSinks -Binary $boa2015
.\ghidra\analyze.ps1 -Label 3.4.0 -Script BoaSinks -Binary $boa2020
```

**應該看到：**

```
INFO  BoaFormTable.java> BoaFormTable: 2 table(s), 100 entries, 98 functions named
INFO  BoaSinks.java> BoaSinks: 1686 call sites across 21 sinks, 432 named functions
```

⏱ 每支 20–60 秒。

### 產出在哪裡

| 檔案 | 內容 |
|---|---|
| `reports/ghidra-strings-<版本>.json` | 關鍵字串 → 用到它的函式（W01） |
| `reports/ghidra-formtable-<版本>.json` | `root_form[]` 全表：每個 `/boafrm/` 路由的名字、handler 位址、它讀了哪些請求參數 |
| `reports/ghidra-sinks-<版本>.json` | `system` / `strcpy` / `sprintf` … 的每一個呼叫點，以及呼叫它的函式 |

看分派表：

```powershell
wsl -d Ubuntu-24.04 bash -c "cd /mnt/c/Users/Key20/Desktop/router && jq -r '.tables[] | select(.role==\"root_form\") | .entries[] | \"\(.handler) \(.name)\"' reports/ghidra-formtable-2.1.2.json | head -20"
```

完整的「該看哪些函式、為什麼」整理在 [`notes/ghidra-triage.md`](notes/ghidra-triage.md);
結論在 [`notes/dispatch-table.md`](notes/dispatch-table.md) 和
[`notes/auth-flow.md`](notes/auth-flow.md)。

### 打開圖形介面自己看

```powershell
& "$env:LOCALAPPDATA\fwre-tools\ghidra_12.1.2_PUBLIC\ghidraRun.bat"
```

第一次開會問你要不要建專案 —— 選 **File → Open Project**，路徑在：

```
%LOCALAPPDATA%\fwre-tools\ghidra-projects\totolink-n150rt.gpr
```

裡面有 `2.1.2`、`3.4.0`、`2.1.2-skt` 三個資料夾。雙擊裡面的 `boa` 打開，按 `G` 可以跳到指定位址。

**跑過 `BoaFormTable` 之後**，函式列表裡會有 185 個 `form_*` 和 `aspvar_*` 開頭的名字，每個上面都有一段註解寫著它是從分派表哪一項來的。直接按 `G` 跳到 `0x0044a190`（2015 版的 `form_formWsc`）就能看到本週最重要的那幾行。

---

## 8.5 Part 5 — 讀出授權流程（W03）

這一段是**閱讀**，不是跑指令。腳本只負責把證據搬出來，結論是人讀出來的。

### 把要讀的函式匯出成 C

```powershell
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaDecompile -Binary $boa2015 `
  -Out "$PWD\ghidra\decomp\decomp-2.1.2.json" `
  -ExtraArgs @('name:handleForm','name:translate_uri','name:process_requests','prefix:form_','callers:system')
```

產出在 `ghidra/decomp/`（**這個資料夾不進 git**）。

> ⚠️ **為什麼反編譯結果不能 commit**
>
> 反編譯出來的 C 是廠商 binary 的衍生物。整包 commit 等於換個方式散布韌體，
> 跟 README「不轉散布廠商韌體」的立場衝突。筆記裡引用片段 + 加上分析說明是另一回事，
> 那些有 commit。

### 讀不懂的時候，看組語

反編譯器**會出錯，而且會先警告你**。`process_header_end` 的輸出頂上有三行
`WARNING: Heritage AFTER dead removal`，那代表它自己知道這段處理得不好。

```powershell
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaListing -Binary $boa2015 -ReadOnly `
  -Out "$PWD\ghidra\decomp\listing-phe.txt" -ExtraArgs @('0040be0c','0040c600')
```

出來的是純文字組語，而且呼叫目標和字串常數都已經解出來了。找這幾行：

```
0040c234  lw t9,-0x7cbc(gp)        -> PTR_strstr_0048b2f4
0040c238  addiu a1,a1,-0x2be0        "htm"
0040c23c  jalr t9                  -> strstr
0040c248  beq v0,zero,0x0040c3a0                 ; 回 NULL 就跳過整段授權檢查
```

**這四行就是本週的結論**：URI 裡沒有 `htm` 三個字，授權檢查整段被跳過。
完整說明在 [`notes/auth-flow.md`](notes/auth-flow.md)。

> 用純文字而不是截圖，是因為截圖沒辦法 diff、沒辦法 grep、Ghidra 升版之後也沒辦法重新產生。

---

## 8.6 Part 6 — 硬體開工：料件辨識（W02 Day 1）

> 硬體 2026-08-14 到貨。**這一節只寫 Day 1 真的做完的事。**
> 到這一節結束為止，**路由器一次都沒有通電**。UART 和 SPI 是 Day 2 之後的事，
> 等真的跑過再回來補這一節 —— 見 [§13 鐵則 1](#13-怎麼維護這份文件)。

### 8.6.1 順序：跟著「可逆程度」走，不要跟著計畫書的日期走

```
拍照 → 抄絲印 → (通電) 電表定腳位 → 邏輯分析儀量 baud → 抓 bootlog → 最後才夾 SPI
```

**在拿到第一份 bootlog 之前，不做任何不可逆的動作。**

理由有兩個，第二個比較重要：

1. SOIC-8 夾是整週最可能弄壞東西的一步（夾歪、滑掉、短到隔壁腳）。
2. bootlog 會**先告訴你 flash 型號和 partition 表** —— 你等於在量之前先拿到一個
   預測，量完才知道自己對不對。反過來做就沒有對照組了。

> ⚠️ **這台機器是 G2 和 G4 的單點故障。** 沒有第二台。W05 要把 web server 服起來、
> W06 要在實機上重現 CVE，都靠它。任何「順手拆一下」的動作，都要先答得出
> 「這一刀換到哪一個 gate 的哪一格」。答不出來就不要動。

### 8.6.2 先拍照，再碰任何東西

G2 的第四格交付物就是**標註過的 PCB 照片**，而**原廠狀態只有一次機會拍**。
正反面高解析、對焦在絲印、光線側打；底部標籤整張拍下來。

### 8.6.3 抄絲印

用手機微距或放大鏡逐顆拍。這台上面有五顆：

| 位置 | 絲印 | 判讀 | 用途 |
|---|---|---|---|
| — | `RTL8196E` | Realtek RTL8196E | SoC(MIPS 大端序) |
| `U19` | `cFeon QH32B-104HIP` | Eon EN25QH32B,32 Mbit = **4 MiB** | 韌體儲存 |
| — | `Winbond W9825G6KH-6` | 256 Mbit SDRAM = **32 MiB** | 系統記憶體 |
| — | `RTL8188ER` | 1T1R 802.11n | 無線 |
| — | `LSC LSP5526` | **沒查到** | 電源（從位置推測） |

> 💡 **cFeon 的 `Q` 在這個放大倍率下跟 `O` 幾乎一樣。** 照片上讀起來像 `OH32B`，
> 但世界上沒有 `EN25OH32B`。**這種事不要靠瞇眼睛決定** —— Day 4 讓 `flashrom` 讀
> 晶片自己回報的 JEDEC ID，那才是證據。

完整判讀和每一條的第二來源：[`notes/hardware-inspection.md`](notes/hardware-inspection.md)。

### 8.6.4 確認 flashrom 認得這顆 flash

這是 Day 1 的交付物之一，現在就能查，不用碰硬體：

```bash
flashrom -L | grep -i en25qh
```

**實際輸出：**

```
Eon                          EN25QH128                            PREW          16384  SPI
Eon                          EN25QH16                             PREW           2048  SPI
Eon                          EN25QH32                             PREW           4096  SPI
Eon                          EN25QH64                             PREW           8192  SPI
```

`PREW` = probe / read / erase / write 四種都支援；`4096` KiB = **4 MiB**。

> ⚠️ **這個輸出不能當成「flash 是 4MB」的第二來源。**
> `flashrom` 的資料庫是**用料號當索引**的，而料號是從同一塊晶片上的同一行字讀來的。
> 它證明的是「**如果**這顆是 EN25QH32，那它就是 4096 KiB 而且我讀得動」，
> 不是「這顆是 4 MiB」。
>
> **真正獨立的來源是晶片自己回報的 JEDEC ID**（Eon 的廠商碼是 `0x1C`），
> 那要等 Day 4 夾上去才有。

**夾之前還要量一件事：SOP-8 有 150 mil 和 208 mil 兩種寬度**，而 CH341A 套件附的
夾子常常是窄的那種。先量 `U19` 的本體寬度，不要硬夾。

### 8.6.5 確認 usbipd 裝好了

```powershell
winget install --interactive --exact dorssel.usbipd-win
```

裝完之後 **PowerShell 要重開**（見 [§10.15](#1015-usbipd-裝好了但-powershell-說找不到)）。

```powershell
usbipd list
```

**實際輸出（工具都還沒插上的樣子）：**

```
Connected:
BUSID  VID:PID    DEVICE                                                        STATE
1-3    046d:c52b  Logitech USB Input Device, USB Input Device                   Not shared
1-6    13d3:56a8  USB2.0 HD UVC WebCam                                          Not shared
1-10   8087:0026  Intel(R) Wireless Bluetooth(R)                                Not shared

Persisted:
GUID                                  DEVICE
```

USB-TTL / CH341A / 邏輯分析儀插上去之後，這張表會多出對應的列 —— **那就是確認
「東西有被 Windows 認到」最快的方法**，比開裝置管理員快。

### 8.6.6 Day 1 刻意沒做的事

| 沒做 | 為什麼 |
|---|---|
| **拆天線** | 試過，失敗，而且**本來就不該做** —— 它不對應 G2 任何一格。見 [§10.14](#1014-天線焊點-450c-化不開) |
| **剪 on/off 開關線短接成常開** | 提出後否決。那兩根線的用途沒量過就短接是在賭；而且接下來要反覆斷電重開幾十次，**一個能撥的開關是資產不是障礙** |
| **通電** | Day 1 只做辨識。通電是 Day 2 量腳位時才開始 |
| **焊任何東西** | 這台的 UART **已經有排針**，整個 W02 一刀都不用焊 |

### 8.6.7 找到 UART 排針

板子下緣、LED 那一排旁邊，有一組**已經焊好的 4-pin 2.54mm 排針**，
旁邊絲印直接印著 `UART`。

意思是：**整個 W02 完全不用焊接。** 廠商把 debug 介面留在出貨的消費性產品上，
而且還標了名字。

> ⚠️ **絲印寫 `UART` 只告訴你「這組是 UART」，沒告訴你「哪一支是哪一支」。**
> GND / VCC / TX / RX 的順序要用電表量出來（Day 2），**不可以照慣例猜**。

### 8.6.8 照片進 repo 之前：先遮

**這塊板子上有兩張會指認出「你這一台」的標籤：**

| 位置 | 是什麼 | 動作 |
|---|---|---|
| PCB 背面條碼 | 12 個十六進位字元 —— **幾乎確定是這台的 MAC 位址** | **遮掉再 commit** |
| PCB 正面 QR + 數字標籤 | 機身序號 | **遮掉再 commit** |

而 G2 要交的就是**背面那張照片**。

同一條規則接下來還會用到兩次：

- **bootlog** 會印出 MAC，而且照 W04 找到的 `flash set HW_WLAN0_WSC_PIN %s` 來看，
  很可能連 **WPS PIN** 一起印；
- **flash dump 的 config 分割區**裡全部都有 —— 這也是 [`.gitignore`](.gitignore)
  一開始就把 `dumps/*` 擋在 repo 外面的原因之一。

**一條規則，三個地方：從「我這一台」讀出來的東西一律遮掉，只發表對「這個型號」
成立的事實。** 遮蔽要在 `git add` 之前決定 —— **推上去之後才遮的，不叫遮。**

> 💡 **QR 比印出來的數字危險。** 印出來的號碼要有人去「讀」，QR 是**自動被解碼的**，
> 而且縮圖之後照樣解得出來。所以連廣角照裡只有幾十像素寬的那個 QR 也要蓋掉。

### 8.6.9 遮蔽和標註都用腳本，不用影像編輯器

理由跟 W03 拒絕用 Ghidra 截圖一樣：**編輯器產出的檔案沒有人能檢查、沒辦法 diff、
原圖重拍之後也沒辦法重新產生。**

兩支工具都需要 Pillow，裝進**這個專案自己的 venv**：

```bash
~/fwre-work/venv/bin/python -m pip install Pillow
```

```bash
PY=~/fwre-work/venv/bin/python

# 遮蔽:實心塗黑(不是模糊 —— 模糊在已知字體上是可逆的),順便丟掉 EXIF
$PY tools/redact-photo.py <原圖>.jpeg notes/img/04-pcb-bottom-redacted.jpg \
    --expect-size 2048x1536 --box 640,710,520,200

# 標註:框和文字寫在 JSON 裡,圖是算出來的
$PY tools/annotate-photo.py notes/img/pcb-top-annotations.json \
                            notes/img/05-pcb-top-annotated.jpg
```

**應該看到：**

```
  ok    04-pcb-bottom-redacted.jpg: 1 region(s), 104,000 px (3.31% of frame) painted out, EXIF dropped, verified on read-back
  ok    05-pcb-top-annotated.jpg: 12 callouts, 2048x1936
```

> ⚠️ **工具能證明框裡是純黑，證明不了框在對的位置。**
> **那一關是人工的，三張都要親眼看過。**

完整座標紀錄、檔名規則、產生方式：[`notes/img/README.md`](notes/img/README.md)。

---

## 8.7 Part 7 — 序列 console 與 flash 讀取（W02 Day 2–3）

> 2026-08-15 實際跑過的流程。**這一節從頭到尾板子是通電的。**

### 8.7.1 量腳位：先驗表，再量板

**順序不能顛倒。**

```
1. 電池 → V⎓ 20V 檔 → 讀到 1.5 / 9        ← 驗證表本身,不碰板子
2. 通電 → 板子的 LED 有沒有亮              ← 驗證板子有電,不用表
3. 斷電 → Ω 檔,黑筆夾 DC 座外環,紅筆掃四支腳
4. 通電 → V⎓ 20V 檔,同樣掃四支腳
```

第 1 步不能省。這一天最久的一次卡關，就是**用 200mV 檔去量 3.3V** ——
差 16 倍，而它回給我的不是「超量程」，是一個會漂的 `0.x`，看起來跟真讀數一樣。
見 [§10.17](#1017-電壓量到-0x-在跳-而且怎麼量都不對)。

實測結果（pin 1 = 板上三角形那端）：

| 腳 | 斷電 Ω 對地 | 通電 V 對地 | 判定 |
|---|---|---|---|
| 1 | 181 Ω | 3.3 V | **VCC** —— 不接 |
| 2 | 18 kΩ | 0–3.3V 在跳 | **TX** |
| 3 | 15 kΩ | 0 V | RX(推論) |
| 4 | **0.2 Ω** | **0 V** | **GND** |

> 💡 **3.3V 軌對地是幾百歐姆，不是開路。** 這是最容易被當成地的一個讀數。
> 三個量級清楚分開（`0.2` / `181` / `15–18k`）才是可以下判斷的資料。

### 8.7.2 量 baud，不要試 baud

邏輯分析儀接 TX + **GND（一定要接）**，8 MS/s，抓 3–5 秒，先按 Run 再開電源。

量**最窄**的脈衝：**26 µs** → `1/26µs` = 38.46 kHz → **38400**。

> **自洽檢查才是重點：** 同一段裡有一個脈衝正好是 **52 µs = 2 × 26**。
> 如果 26 µs 是兩個位元，就必須存在 13 µs 的脈衝 —— 而不可能有半個位元。
>
> **最接近的錯誤答案是 19200，它的位元時間正好 52.08 µs。**
> 挑錯脈衝就會設成 19200，然後整晚看亂碼。

### 8.7.3 把 CP2102 交給 WSL

接線：`GND→pin4`、轉接板 `RXD→pin2`、轉接板 `TXD→pin3`、**`VCC` 不接**。
**先接 GND 再接訊號線。**

```powershell
usbipd list
```
```
1-1    10c4:ea60  Silicon Labs CP210x USB to UART Bridge (COM3)   Not shared
```
```powershell
usbipd bind --busid 1-1          # 需要系統管理員,只做一次
```

> ⚠️ **`attach` 之前 WSL 必須正在跑**，否則會說
> `There is no WSL 2 distribution running`。見 [§10.19](#1019-usbipd-attach-說沒有-wsl-2-發行版在跑)。

```powershell
Start-Process -WindowStyle Hidden wsl -ArgumentList "-d","Ubuntu-24.04","--","sleep","7200"
usbipd attach --wsl --busid 1-1
```

**應該看到：**

```
crw-rw---- 1 root dialout 188, 0 /dev/ttyUSB0
[   31.521095] cp210x 1-1:1.0: cp210x converter detected
[   31.523173] usb 1-1: cp210x converter now attached to ttyUSB0
```

WSL 的使用者預設**不在 `dialout` 群組**，所以要：

```bash
sudo usermod -aG dialout $USER    # 之後永久有效
sudo chmod 666 /dev/ttyUSB0       # 這次立即生效
```

### 8.7.4 抓 bootlog

```bash
stty -F /dev/ttyUSB0 38400 cs8 -cstopb -parenb raw -echo
timeout 90 cat /dev/ttyUSB0 > ~/fwre-work/dumps/uart-boot.log
```

**先讓它跑起來，然後才開板子電源。** 開機訊息只跑一次。

實測 1903 bytes / 69 行，`Booting` 出現 **1 次**（所以不是 boot loop）。
內容分析在 [`notes/uart-findings.md`](notes/uart-findings.md)。

### 8.7.5 這台的 console 沒有 shell

開完機送 `\r`，回來的是**完整的回顯，但指令不執行、也沒有提示符**：

```
送  : \r \r \r\n  echo MARKER_1234\r
回  : CR LF ×4,然後 "echo MARKER_1234" CR LF
```

**那是 Linux tty 行規程在回顯，不管有沒有行程在讀。**
沒有 getty、沒有 shell,bootlog 裡也沒有 BusyBox 那句
`Please press Enter to activate this console`。

> **「console 有回應」感覺很像成功，但它不是。** 要分清楚回顯來自 tty 層，
> 還是真的有東西在讀。

### 8.7.6 搶 bootloader：ESC 要在上電之前就開始送

中斷視窗只有一秒多，而且開機瞬間就開始 —— **看到輸出才按已經來不及了。**

```bash
timeout 45 cat /dev/ttyUSB0 > ~/fwre-work/dumps/uart-bootloader.log &
END=$((SECONDS+20)); while [ $SECONDS -lt $END ]; do printf '\033' > /dev/ttyUSB0; sleep 0.03; done
# ↑ 開始送之後才打開板子電源
```

**成功的樣子（注意它沒有去載核心，改去初始化網路）：**

```
---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)
P0phymode=01, embedded phy
---Ethernet init Okay!
<RealTek>
```

### 8.7.7 bootloader 指令：`?` 不是 `HELP`

```
<RealTek>?
----------------- COMMAND MODE HELP ------------------
HELP (?)   : Print this help message
DB <Address> <Len>        DW <Address> <Len>
EB <Address> <Value>...   EW <Address> <Value>...
CMP <dst><src><length>    IPCONFIG:<TargetAddress>
AUTOBURN: 0/1             LOADADDR: <Load Address>
J: Jump to <TargetAddress>
FLR: FLR <dst><src><length>
FLW <dst_ROM_offset><src_RAM_addr><length_Byte> <SPI cnt#>
MDIOR / MDIOW / PHYR / PHYW / PORT1
```

說明自己寫 `HELP (?)`，但 `HELP` 回 `Unknown command !`。**只有 `?` 能用。**

> ⚠️ **`FLW`、`EB`、`EW`、`AUTOBURN` 會寫入。打錯參數就是磚。**
> 讀 flash 只需要 **`FLR`** 和 **`DB`**，一個寫入指令都不要送。

### 8.7.8 讀 flash:`FLR` + `DB`

**這是一條完整的 flash 讀取路徑，不用夾 SOIC-8 夾子。**

```
FLR <RAM位址> <flash位移> <長度>     ← 三個都是十六進位
Y                                     ← 一定要,見下
DB <RAM位址> <長度>                   ← 位址十六進位,長度十進位
```

**實測：**

```
<RealTek>FLR 80520000 180000 40
Flash read from 00180000 to 80520000 with 00000040 bytes ?
(Y)es , (N)o ? --> Y
Flash Read Successed!
<RealTek>DB 80520000 64
80520000: 68 73 71 73 37 02 00 00 00 1c ad 80 00 00 02 00     hsqs............
```

> ### ⚠️ 兩個會安靜害死你的坑
>
> **1. `FLR` 會問 `(Y)es , (N)o ?`，而且把下一行整個吃掉當答案。**
> 腳本裡如果直接送下一個指令，會得到 `Abort!` —— 然後那個 `DB` 印出來的是
> **RAM 裡上一次留下的舊資料**，而你會以為那是 flash 的內容。
>
> **2. `FLR` 的長度是十六進位，`DB` 的長度是十進位。**
> `DB <addr> 100` 回你 100 bytes，不是 0x100。**沒有任何警告，你會拿到一份
> 格式完全正常、長度錯誤的 dump。**
>
> **對策：每次 `FLR` 之前先 `DB` 同一塊 RAM 當對照組。** 內容沒變就是 FLR 沒生效。

實際讀出來的 flash 版面在 [`notes/flash-layout.md`](notes/flash-layout.md)。

---

### 8.7.9 完整 4 MiB dump:`tools/console-dump.py`(W02 Day 4)

上面那套是手動讀 64 byte 窗口。**要把整顆 4 MiB 讀下來，手是不行的** —— 那是
26 萬行十六進位、大約 95 分鐘，而 38400 沒有流量控制，**掉字元不是可能性，是排程**。

掉一個字元不會有人通知你。你會得到一份短一點、但看起來完全正常的 hex dump,
貼進轉換器之後得到一個**中間有洞、洞之後每個位移全部位移掉**的映像檔，
然後所有下游結論都會很有自信地錯。

```bash
# 1. 釘住 WSL(usbipd 的 attachment 綁在這個 VM 上,VM 一停裝置就退回 Windows)
#    另開一個視窗放著不要關:
wsl -d Ubuntu-24.04 -- sleep 7200

# 2. Windows(不需要管理員,如果之前 bind 過)
usbipd list                          # 找 10c4:ea60 的 BUSID
usbipd attach --wsl --busid <id>

# 3. WSL:抓 bootloader。ESC 會連續送滿整個 window,所以時間點很寬鬆
python3 -u tools/console-dump.py catch --port /dev/ttyUSB0 --window 300
#    ↑ 看到這行之後才去上電:>>> POWER THE ROUTER ON NOW <<<

# 4. 先試跑 64 KiB,不要直接衝 4 MiB
python3 -u tools/console-dump.py dump --at-prompt \
        --flash 0x060000 --length 0x10000 --ram 0x81000000 \
        -o ~/fwre-work/dumps/pilot.bin

# 5. 完整 dump。~95 分鐘,期間不需要碰板子,不需要重開機
setsid nohup python3 -u tools/console-dump.py dump --at-prompt \
        --flash 0x0 --length 0x400000 --ram 0x81000000 --chunk 16384 \
        --flr-timeout 300 --verify-sample 0.05 \
        -o ~/fwre-work/dumps/flash-n150rt-console-1.bin \
        > ~/fwre-work/dumps/console-dump.log 2>&1 < /dev/null &

tail -f ~/fwre-work/dumps/console-dump.log     # 看進度
```

**這支工具做了四件手做不到的事：**

| | |
|---|---|
| **陽性對照** | 先 `FLR` flash `0x000000`，前四個 byte 必須是 `0b f0 00 04` —— 那是 8/15 另一場 session 記下的已知答案。對不上就不往下走 |
| **逐塊驗證** | 每一塊檢查位址連續、每行剛好 16 byte、總長相符。**掉一行就整塊重讀** |
| **抽驗重讀** | 全部讀完後隨機抽 5% 的塊**再讀一次**比對。解析器看不到「格式正確但內容錯」的位元翻轉，重讀看得到 |
| **拼不完整就不吐檔案** | 只留 `.partial`。**一份看起來完整的殘缺映像，比沒有映像更糟** |

> ### ⚠️ 兩個 8/16 踩到的坑
>
> **1. ESC 會塞住 bootloader 的輸入緩衝區。** 搶 bootloader 是「連續送」ESC,
> 它只吃掉一個用來中斷開機，**其餘全部排在輸入緩衝區裡** —— 所以搶到之後
> **第一條指令必定失敗**，回你 `Unknown command !`。
> 對策：先送一個裸 `\r` 讀到 prompt 再送真正的指令（工具的 `settle()`）。
> 這一坑害我以為 `?` 不是 help —— 而 §8.7.7 明明記過 `?` 就是 help。
>
> **2. 不要照 `notes/` 裡引用的 transcript 寫解析器。** `notes/` 是分析文件，
> 引用會為了排版修剪；**§8.7.8 這裡的 transcript 才是逐字的**。
> 第一版解析器沒有 ASCII 欄，把裝置吐的**每一行**都判成不合法。

**速率是物理上限，不要調程式：** 每 16 個 data byte 要送 81 個字元
（位址 8 + `: ` 2 + hex 48 + 空白 5 + ASCII 16 + CRLF 2），**5.06 倍膨脹**。
38400 8N1 = 3840 B/s ÷ 5.06 = **759 B/s 理論上限**，實測 723 B/s。
線已經吃滿了。

**dump 落地之後，它還不是證據：**

```bash
python -m fwrecon flashdump ~/fwre-work/dumps/flash-n150rt-console-1.bin
```

這會拿映像去對 **8/15 console 讀到的每一個 offset** 和 **W01 從廠商容器推導的
燒錄位址** —— 兩份都寫在它存在之前。硬檢查沒過就 exit 1。
per-unit 秘密區（`0x006000`–`0x010000`）只報 SHA-256，**永遠不印內容**。

---

## 8.8 W04-2 新增的操作（2026-08-16）

### 8.8.1 把這台自己的 `boa` 讀進 Ghidra，並跑五種量測

匯入一次幾分鐘，之後每次跑腳本只要幾秒。

```powershell
$boa = "\\wsl$\Ubuntu-24.04\home\key\fwre-work\extracted\unit-2018\squashfs-root\bin\boa"
.\ghidra\import.ps1  -Label unit-2018 -Binary $boa
.\ghidra\analyze.ps1 -Label unit-2018 -Script BoaFormTable -Binary $boa
.\ghidra\analyze.ps1 -Label unit-2018 -Script BoaSinks     -Binary $boa
.\ghidra\analyze.ps1 -Label unit-2018 -Script BoaMnemonics -Binary $boa -ReadOnly
.\ghidra\analyze.ps1 -Label unit-2018 -Script BoaArgTrace  -Binary $boa `
    -ExtraArgs @('sink:system','sink:strcpy','sink:sprintf','sink:snprintf','depth:6')
```

> ### ⚠️ 三個會安靜給你錯答案的坑
>
> **1. Ghidra 專案是整個上鎖的。** 前一個 `analyze.ps1` 還在跑的時候再開一個，
> 會拿到 `LockException: Unable to lock project!`。**要排隊，不能平行。**
>
> **2. `BoaArgTrace` 對 `sstrip` 過的 build 一定要給 `accessor:`。**
> V3.4.0 沒有符號，不給 `accessor:FUN_0040e9e0` 的話，它**一個 request 參數都
> 認不出來**，污染點數字直接從 49 掉到 0 —— 而 `self_check` 會寫 `consistent`，
> 因為那個檢查只在「你給了 override 但沒對上」時才會叫。
> 現在多了一個 `no_accessor_identified`，零匹配就報 SUSPECT。
>
> **3. 三個 build 要用同一組 spec 才能比。** 報告現在會把 `spec` 欄寫進去，
> 沒有那一欄的舊報告不能拿來跟新的並排 —— W04 的 304 和 W04-2 的 1508
> 看起來像個發現，其實是在回答不同的問題。

### 8.8.2 解碼設定區（`COMPCS` / `COMPDS`）

```bash
fwrecon compcs $FWRE_WORK/dumps/flash-n150rt-console-1.bin --offset 0x00C000 \
  --mib $FWRE_WORK/extracted/unit-2018/squashfs-root/lib/libapmib.so \
  -f json -o reports/compcs-unit-2018.json
```

`--offset 0x008000` 是出廠預設。**`0x006000` 會失敗，而且應該失敗** —— 那塊是
`H601`，沒有壓縮，不是 `COMPHS`：

```
fwrecon compcs: no APMIB config magic at 0x6000: found b'H601\x04\x8e',
expected one of ['COMPCS', 'COMPDS', 'COMPHS']
```

**退出碼有意義：** `0` 乾淨，`1` 解出來了但自己標了 anomaly,`2` 根本不接受這塊
資料。`1` 和 `2` 都不可以拿來當證據。

`--disclosure protect` 會把 per-unit 識別碼換成 sha256。今天的決定是 `open`，
但**機制留著，而且有一個會失敗的測試守著它** —— 改的是政策，不是能力，下一台
機器不一定是你的。

### 8.8.3 CI 閘門：`BoaGate`，以及**為什麼一定要給 `control:`**

```powershell
# 對照組一定要帶 control:,否則這個閘門不能證明自己是活的
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaGate -Binary $boa212 `
    -ExtraArgs @('control:30','depth:8')
```

> **這一格是整個工具的賣點，不是一個選項。**
>
> 第一次跑，它在 V2.1.2 上回報 **0 findings** —— 而那個 build 是 W03/W04
> 一行一行讀出 34 個有問題的 handler 的那一個。原因有兩個，而且是分開的兩次：
> 先是用「名字」比對 sink，但這些 binary 呼叫 libc 是走 `sstrip` 過的 PLT,
> Ghidra 把它叫成 `FUN_xxxxxxxx`；修掉之後又發現字面值解析只檢查 `isConstant()`，
> 而 MIPS 的字串位址是 lui/addiu 湊出來的，所以**一個參數名字都沒讀到**。
>
> 兩次都會以「這個 build 很乾淨」的形式出貨。**`control:30` 兩次都當場擋下來。**
> 一個沒有在已知壞掉的 build 上驗證過的 SAST 規則，不是檢查，是裝飾。

### 8.8.4 抓一份廠商映像回來，以及它只下載了 40% 的時候怎麼辦

**這一節服務 `PROGRESS.md` 開放問題 #0：把公開的 V2.1.6 重抓一次，而且先驗
zip 自己的 CRC-32。** 第一次抓只下來 40.3%，而那份殘檔仍然回答了問題，所以
下面兩件事都要寫：怎麼抓，以及**殘檔可以撐到哪裡、不可以撐到哪裡**。

#### 抓檔：腳本抓不到，瀏覽器抓得到

Softpedia 對 PowerShell `HEAD`、三種 User-Agent 的 `curl`、`WebFetch` 全部回
**403**。`firmware/SOURCES.json` 從 W01 就記著這件事，所以這是**確認，不是發現**
—— 不要再花時間繞它。用瀏覽器點，然後**不要憑記憶把網址打進文件**：

```bash
# Windows 在下載時自己寫了來源,這是證據,不是回憶
cat "N150RT-V2.1.6-20160516.zip:Zone.Identifier"
```

```
[ZoneTransfer]
ZoneId=3
ReferrerUrl=https://drivers.softpedia.com/dyn-postdownload.php/335a36e267124a3717d2cddfb77226ef/6a811c68/8974a/4/1
HostUrl=https://us.softpedia-secure-download.com/dl/54f52698326aaa49c40bddd5fdf34dd8/6a810e64/300563018/drivers/router/N150RT-V2.1.6-20160516.zip
```

> 從 WSL 讀 NTFS 的 alternate data stream 就是把 `:Zone.Identifier` 接在檔名
> 後面當成一個檔案開。**檔案搬進 `$FWRE_WORK` 的時候這條 stream 會跟著搬，
> 但用 `cp` 到別的檔案系統就沒了** —— 要保存 provenance 就先讀出來。

#### 驗檔：`unzip` 說壞掉，不代表它壞掉

```bash
unzip -t N150RT-V2.1.6-20160516.zip
```

```
  End-of-central-directory signature not found.  Either this file is not
  a zipfile, or it constitutes one disk of a multi-part archive.
```

**這個訊息會讓你以為檔案是壞的。它不是，它是被截斷的，而那是兩件事。**
ZIP 的目錄在檔尾，少了目錄 `unzip` 就完全不動手；但 deflate 是**串流**，
前綴照樣解得開。用 `tools/zipprefix.py`，它直接讀 local file header：

```bash
python3 tools/zipprefix.py $FWRE_WORK/firmware/N150RT-V2.1.6-20160516.zip
```

```
archive              N150RT-V2.1.6-20160516.zip
bytes on disk        1,390,332
inner filename       TOTOLINK-N150RT-V2.1.6-B20160516.1233.web
method               8 (deflate)
DOS mtime            2016-05-16 12:34:30
stored CRC-32        0xd20c0622
compressed size      3,447,222
uncompressed size    3,453,871
filename build date  B20160516 — agrees with the DOS timestamp field
compressed present   1,390,253 of 3,447,222 (40.3%)
central directory    ABSENT — truncated
recovered            1,394,888 of 3,453,871 (40.4%)
CRC-32 recovered     0xb051aa45  vs stored 0xd20c0622  -> MISMATCH
```

**`DOS mtime` 那一行是這支工具存在的第二個理由。** 檔名裡的 `B20160516` 是
文字，鏡像站可以隨便打；DOS 時間戳是打包程式寫進去的**另一個欄位**。兩個對上，
偽造成本就從「改檔名」變成「還要改時間戳」。**這仍然只是佐證** —— TOTOLINK
不簽章，所以沒有任何東西能證明這些 byte 出自原廠（`firmware/SOURCES.json`）。

#### 取出殘檔：預設不准，而且 `--allow-partial` 不會把結論洗白

```bash
python3 tools/zipprefix.py <zip> -o /tmp/out.bin        # 沒過 CRC → 拒絕寫,exit 1
python3 tools/zipprefix.py <zip> -o /tmp/out.bin --allow-partial
```

```
refusing to write a payload that failed CRC verification; pass --allow-partial if an incomplete recovery is the intent
```

```
wrote                /tmp/recovered.bin  (1,394,888 bytes, INCOMPLETE — not the whole image)
```

> **`--allow-partial` 只解除「不准寫」，它不會把 exit code 變成 0。**
> 這是故意的：殘檔可以拿來分析，但**「我知道它是殘的」和「它是完整的」不能
> 用同一個回傳值表示**。CI 或任何腳本照樣攔得住。
>
> 重抓成功的判準只有一個：**`CRC-32 recovered` 要等於 `0xd20c0622`。**
> 這個數字現在寫在這裡，是為了讓下一次的驗證有一個**事先寫好的目標**，
> 而不是抓完再看它是多少。

#### 殘檔撐得到哪裡 —— 比第一次寫的多

`fwrecon image` 讀那份 40% 的前綴：

```bash
$FWRE_WORK/venv/bin/python -m fwrecon image $FWRE_WORK/firmware/v2.1.6-partial.web
```

```
 #  tag      file off  flash off   ram addr       length  payload
 0  w6cg   0x00000000 0x00010000 0x00010000      296,804  bzip2
 1  cr6c   0x00048774 0x00060000 0x80500000      986,114  raw/unrecognised
      inner: lzma (alone format, lc=3 lp=0 pb=2) at +0x2808
! 111938 unparsed bytes at 0x139386
```

**兩個 section 都是完整的，不是只有 header。** `fwrecon` 的 `payload_actual`
等於 `length`，而且 `cr6c` 裡那條 LZMA 解到底（`eof=True`，3,374,608 bytes）。
截斷的是第三段 `r6cr`，也就是 rootfs —— 所以缺的是 `/etc/version` 和 `boa`，
**不是「只有 section 長度」**。第一次寫成後者，低估了手上的東西一整段。

### 8.8.5 打開 `w6cg`：廠商實際出貨的網頁，以及一個會騙人的 grep

W01 把 `w6cg` 的封裝格式列為「解開了但沒 parse」，一直沒動。`fwrecon web`
把它做完了 —— 格式是 **64 bytes 的 header + 內容**，長度欄在 `+0x3c` 而且是
**big-endian**（header 裡其他欄位是 little-endian，只有這一個不是）。

```bash
# .web 容器
$FWRE_WORK/venv/bin/python -m fwrecon web <韌體.web> --grep formSysCmd
# 直接讀 flash dump,要自己給 w6cg 的位置
$FWRE_WORK/venv/bin/python -m fwrecon web ~/fwre-work/dumps/flash-n150rt-console-1.bin \
        --at 0x010000 --grep formSysCmd
```

```
firmware/TOTOLINK-N150RT-V2.1.2-B20150825.1601.web  144 entries, self_check: exact
searching entry contents for 'formSysCmd'
  syscmd.htm                                   3,835 bytes  11 hit(s)

firmware/v2.1.6-partial.web  144 entries, self_check: exact
  syscmd.htm                                   3,835 bytes  11 hit(s)

dumps/flash-n150rt-console-1.bin  143 entries, self_check: exact
searching entry contents for 'formSysCmd'
  no entry contains it
```

> ⚠️ **`self_check: exact` 是這個工具唯一的保證，不是裝飾。**
> 這個格式**沒有校驗碼、沒有檔案數、沒有結束標記** —— 所以「我 parse 對了」
> 這件事只能從結構本身證明：每一步都是 `64 + length`，所以走完整條鏈要嘛
> **剛好停在最後一個 byte**，要嘛歪掉。長度欄位猜錯一個 offset，一兩筆之內就
> 會歪，而且回不來。**看到 `derailed` 就不要用它吐出來的任何數字。**
>
> ⚠️ **`--grep` 是逐筆搜「內容」，不是搜整塊解壓後的資料 —— 這個差別會害人。**
> 2018 那份 bundle 裡直接用 `grep` 找 `syscmd.htm` **找得到**，而正確答案是
> 那個檔案不存在：命中的是 `language_vn/sc/sp.js` 裡的一行註解
> `/**** syscmd.htm ****/`。**檔名出現在某個檔案裡，不等於那個檔案存在** ——
> 我第一次就是這樣差點推翻 `notes/auth-flow-2018.md` 一句正確的結論。

其他用法：

```bash
python -m fwrecon web <image>                     # 列出全部 entry(名稱/長度/sha256)
python -m fwrecon web <image> --extract syscmd.htm -o /tmp/syscmd.htm
python -m fwrecon web <image> --json -o reports/...
```

---

## 8.9 G3.5 最後一格：`FLW` 回復路徑演練（**2026-08-17 已執行**）　→ `runsheet.md` `A2.5`

> ✅ **做過了。逐字 transcript 在 §8.9.1，實測推翻本節三處寫法。**
> 下面的步驟保留原樣，因為 §8.9.1 的更正只有對照著原文才讀得懂。
>
> ⚠️ **要照著做請走 [`runsheet.md`](runsheet.md) 的 `A2.5`**，它是改正後的版本
> 加上磁區語意那兩步。本節是**歷史紀錄與推理**，它的步驟刻意沒有更新。

**W05 不准在這一格完成之前開始。** 理由不是儀式：W06 的 PoC 必然寫 flash
（`flash set` 寫的就是 `COMPCS`），而這台機器的回復路徑**從來沒有被執行過**。
`0x006000` 的 `H601` 是這台的 MAC 和射頻校準值，**全世界只有這一份**，
原廠映像沒有，回復原廠設定也不會還原。

### 開始之前，三件事缺一不可

```bash
# 1. 兩份 dump 都在,而且雜湊沒變 —— 這是唯一的還原鏡像
cd $FWRE_WORK/dumps && sha256sum -c <<'EOF'
a800059a9b8c414df026a22b8423a5939d0f9bb793109d0f7ce086f6810f37ea  flash-n150rt-console-1.bin
a800059a9b8c414df026a22b8423a5939d0f9bb793109d0f7ce086f6810f37ea  flash-n150rt-console-2.bin
EOF
```

2. **每一行 `FLW` 先寫在檔案裡，念一遍，再貼進終端機。不准現打。**
   `FLR` 已經教過這台的教訓：兩個相鄰指令用兩種進位制。**`FLW` 參數順序打錯
   = 把測試樣式寫進 kernel。**
3. **只碰 `0x3F0000`。** 不要「順便試試看 `0x350000`」。

### 為什麼 `0x3F0000` 是安全的

W02 Day 4 的完整 dump 證明 **`0x350000` 到 part 結尾整段都是 `FF`（已抹除）**。
沒有任何東西讀它。這是演練寫入的完美標的。

### 步驟 —— 每一步看到預期輸出才准下一步

```
# 前置條件,不是儀式:先確認那裡真的是空的
FLR 80520000 3F0000 100
Y
DB 80520000 256
    → 必須整片 FF。不是的話,停,那裡有東西。

# 在 RAM 裡放一段認得出來的樣式,並且確認它真的進去了
EB 80530000 DE AD BE EF DE AD BE EF
DB 80530000 16
    → 必須看到 de ad be ef de ad be ef

# 寫進去
FLW 3F0000 80530000 8
Y
    → Flash Write Successed!(或等價字樣)

# 讀回來 —— 注意讀到「另一個」RAM 位址,不要讀原來那塊
FLR 80540000 3F0000 8
Y
DB 80540000 8
    → 必須逐 byte 等於 de ad be ef de ad be ef
    → 讀回原位址就只是把你剛剛放的東西再看一次,證明不了任何事

# 抹回去
FLW 3F0000 <一塊全 FF 的 RAM> 8      ← 或用 bootloader 的抹除指令(先 ? 查)
Y
FLR 80550000 3F0000 8
Y
DB 80550000 8
    → 必須回到 ff ff ff ff ff ff ff ff
```

### 這一次演練同時證明三件事

| | |
|---|---|
| **回復路徑存在，而且我執行過** | 不再是「文件上列著 `FLW`」。W06 可以排寫 flash 的實驗了 |
| **`FLW` 的參數順序和單位我確認過** | 順序打錯的代價是把樣式寫進 kernel |
| **這是一次寫入 → 讀回的往返** | 系統性錯的 `FLR` 仍然躲得掉（位址偏移會互相抵銷），但**資料層的錯誤躲不掉** |

**做完之後，把逐字 transcript 貼回這一節，並在 `notes/uart-pinout.md` 的
bootloader 指令表補上「`FLW` 已實測，日期」。** 這份文件是操作紀錄，它的
transcript 是逐字的 —— W02 Day 4 的第 8 號 bug 就是因為有人去讀了 `notes/`
裡被排版修剪過的引用，而不是讀這裡。

---

### 8.9.1 逐字 transcript(2026-08-17 07:38–07:47)

原始檔：`$FWRE_WORK/dumps/w05-flw-20260817-0738.log`。這一場的紀錄卡在
[`BENCH-LOG.md`](BENCH-LOG.md)。

```
<RealTek>FLR 80520000 3F0000 100
Flash read from 003F0000 to 80520000 with 00000100 bytes	?
(Y)es , (N)o ? --> Y
Flash Read Successed!
<RealTek>DB 80520000 256
 [Addr]   .0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .A .B .C .D .E .F
80520000: ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff     ................
   (16 行全部 ff,此處省略 15 行 —— 完整內容見 log 檔)
<RealTek>EB 80530000 DE AD BE EF DE AD BE EF
<RealTek>DB 80530000 8
 [Addr]   .0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .A .B .C .D .E .F
80530000: de ad be ef de ad be ef                             ........
<RealTek>FLW 3F0000 80530000 8
Write 0x00000008 Bytes to SPI flash#1, offset 0x003f0000<0xbd3f0000>, from RAM 0x80530000 to 0x80530008
(Y)es, (N)o->Y
.<RealTek>FLR 80540000 3F0000 8
Flash read from 003F0000 to 80540000 with 00000008 bytes	?
(Y)es , (N)o ? --> Y
Flash Read Successed!
<RealTek>DB 80540000 8
 [Addr]   .0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .A .B .C .D .E .F
80540000: de ad be ef de ad be ef                             ........
<RealTek>EB 80530100 CA FE BA BE CA FE BA BE
<RealTek>DB 80530100 8
 [Addr]   .0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .A .B .C .D .E .F
80530100: ca fe ba be ca fe ba be                             ........
<RealTek>FLW 3F0100 80530100 8
Write 0x00000008 Bytes to SPI flash#1, offset 0x003f0100<0xbd3f0100>, from RAM 0x80530100 to 0x80530108
(Y)es, (N)o->Y
.<RealTek>FLR 80540000 3F0000 8
Flash read from 003F0000 to 80540000 with 00000008 bytes	?
(Y)es , (N)o ? --> T Y
Flash Read Successed!
<RealTek>DB 80540000 8
 [Addr]   .0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .A .B .C .D .E .F
80540000: de ad be ef de ad be ef                             ........
<RealTek>EB 80530200 FF FF FF FF FF FF FF FF
<RealTek>DB 80530200 8
 [Addr]   .0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .A .B .C .D .E .F
80530200: ff ff ff ff ff ff ff ff                             ........
<RealTek>FLW 3F0000 80530200 8
Write 0x00000008 Bytes to SPI flash#1, offset 0x003f0000<0xbd3f0000>, from RAM 0x80530200 to 0x80530208
(Y)es, (N)o->Y
.<RealTek>FLR 80550000 3F0000 8
Flash read from 003F0000 to 80550000 with 00000008 bytes	?
(Y)es , (N)o ? --> Y
Flash Read Successed!
<RealTek>DB 80550000 8
 [Addr]   .0 .1 .2 .3 .4 .5 .6 .7 .8 .9 .A .B .C .D .E .F
80550000: ff ff ff ff ff ff ff ff                             ........
<RealTek>
```

**判定：寫入 → 讀回逐 byte 一致，抹除後回到全 FF。§8.9 事先凍結的兩個條件都滿足，
`P0-3` 通過，G3.5 補齊。**

### 8.9.2 這一次實測推翻的四處

| 上面寫的 | 實際 |
|---|---|
| 「`Flash Write Successed!`（或等價字樣）」 | **一個句點 `.`**。真正的回應是 `Write 0x… Bytes to SPI flash#1, offset 0x003f0000<0xbd3f0000>, from RAM 0x… to 0x…`。**這一列 2026-08-17 下午再修一次 —— 見下面的方框：那句話存在，只是屬於另一條路徑** |
| `FLR` 的提示是 `(Y)es , (N)o ? -->` | **`FLW` 的是 `(Y)es, (N)o->`**。兩個相鄰指令，兩種標點 —— 跟「兩種進位制」是同一種毛病 |
| 「`EB` 一次吃多個 byte 沒有被實測過」 | **測過了，可以。** `?` 的說明本身也寫 `EB <Address> <Value1> <Value2>...` |
| 「抹回去：`FLW 3F0000 <一塊全 FF 的 RAM> 8`」 | **會回到 FF，但理由不是這份文件想的那個。** NOR flash 的程式化只能把 `1` 變 `0`，`FF` 寫在 `DE` 上面應該還是 `DE`。它回到 `FF` 代表**`FLW` 自己做了抹除** —— 見 §8.9.3 |

**額外情報：`FLW` 的回應洩漏 flash 的記憶體映射位址** —— `offset 0x003f0000<0xbd3f0000>`，
所以 SPI flash 映射在 **`0xbd000000`**（KSEG1 非快取區）。`notes/flash-layout.md` 沒有這個。

> ### 📌 2026-08-17 下午：第一列的更正本身也不夠準
>
> 上表第一列說「`Flash Write Successed!` 是錯的」。**那句話存在於這台的
> bootloader 裡**，位址 stage2 `0x0a861` —— 它只是**不屬於互動式 `FLW`**。
>
> 上午沒找到它的原因是：**整顆 4 MiB 裡沒有任何一個 bootloader 字串是明文的。**
> `grep FLR`、`grep IPCONFIG`、`grep "COMMAND MODE HELP"` 全部落空，而那三個字
> 每天都在 console 上看得到。真相是 `0x000000`–`0x0012F0` 只是第一階段
> (DRAM 訓練：`Booting...` / `DTR Done.` / `DCR Done.` / `DDCR Done.`),
> **`0x0012F0` 起是一段 LZMA：17,334 → 56,592 bytes**，指令直譯器整個在裡面。
>
> 解開之後，兩句話分屬兩叢，相距 2.7 KiB：
>
> | 位址（stage2） | 字串 | 屬於 |
> |---|---|---|
> | `0x0a7f8` | `burn Addr =0x%x! srcAddr=0x%x len =0x%x ` | TFTP 自動燒錄 |
> | `0x0a824` | `it's special wrt image need add 4 byte to burnlen =%8x!` | 同上 |
> | **`0x0a861`** | **`Flash Write Successed!`** | **同上** |
> | `0x0a87d` | `Flash Write Failed!` | 同上 |
> | `0x0a8b1` | `**TFTP Client Upload File Size = %X Bytes at %X` | 同上 |
> | **`0x0b4a4`** | **`Flash Read Successed!`** | **互動式指令** |
> | `0x0b4d0` | `----------------- COMMAND MODE HELP ---…` | 同上 |
> | **`0x0b50c`** | **`Write 0x%x Bytes to SPI flash#%d, offset 0x%x<0x%x>, from RAM 0x%x to 0x%x`** | **同上** |
>
> **這個分群自帶對照組**：`Flash Read Successed!` 是互動式 `FLR` 真的會印的那一句，
> 而它落在互動叢裡；看不到的那一句落在 TFTP 叢裡。所以正確的說法不是
> 「作業單抄錯了字串」，是 **「作業單抄的是同一顆 binary 裡另一條路徑的訊息」**，
> 而現在兩條路徑各自指得出位址。
>
> 產生方式（可重跑，而且拒絕在對照組沒過時出報告）：
> ```bash
> make loader-report        # -> reports/bootloader-unit-2018.json
> python3 tools/loader-unpack.py <dump> --strings | less
> ```

### 8.9.3 未結：`FLW` 的磁區語意，以及作業單這一格設計錯了

**Step 5 與 Step 6 的結果在 NOR flash 的物理上互相矛盾。**
抹除的最小單位是磁區（這顆 EN25QH32B 是 4 KiB），所以 Step 5 在 `0x3F0100` 的寫入
本應把 `0x3F0000` 一起抹掉，但它讀起來還在。三條證據指向同一個機制：

| | |
|---|---|
| Step 6 回到 `FF` | 一定有抹除 |
| Step 5 同磁區另一段沒被清掉 | 抹除前先把磁區內容讀出來了 |
| **`?` 的完整指令集裡沒有任何抹除指令** | 所以抹除只能由 `FLW` 自己做 |

**推定：`FLW` 是「讀出整個磁區 → 改指定 byte → 抹除磁區 → 整段寫回」。**
如果成立，**每一次 `FLW` 都會重寫整個 4 KiB 磁區**，而 `H601`（這台的 MAC 與
射頻校準）整個住在一個磁區裡 —— 寫入中途斷電失去的不是 8 個 byte，是那個磁區。

> ⚠️ **而且這一格的證據本來就不夠，原因在作業單：**
> Step 5 的讀回用了 `80540000`，**那是 Step 4 已經用過、而且裡面就是 `de ad be ef` 的位址**。
> §8.7.8 早就警告過「內容沒變就是 `FLR` 沒生效」，而作業單自己踩了進去。

分辨它只要一組指令（`80560000` 是全新的 RAM 位址，第一個 `DB` 是對照組）：

```
DB 80560000 8
FLR 80560000 3F0100 8
Y
DB 80560000 8
```

讀到 `ca fe ba be …` → 讀-改-抹-寫回成立；讀到 `ff ff …` → `FLW` 抹掉整個磁區，
**寫 flash 的風險等級要全部上調**。

> **2026-08-17 下午補充：靜態這一側查過了，而它答不出來。**
> bootloader 第二階段解開之後（`make loader-report`），整個 56,592 bytes 裡
> **一個 `erase` / `sector` / `block` 字串都沒有**。有的是 `chipName: %s` 和
> 一張 SPI 型號表（`MX25L…` / `EN25…` / `W25Q…` / `GD25Q…`）。
> 也就是說 loader 認得晶片，但從不宣告它抹了什麼 ——
> **這一格只能用上面那四行指令在機器上分辨，靜態繞不過去。**
>
> **而它順手關掉 `notes/uart-findings.md` 裡一個標著「Not confirmed」的問題，
> 但只關掉一半。** 那份筆記記過 console 上印 `chipName: UNKNOWN`，並推測
> 「boot ROM 的 flash ID 表裡沒有 EN25QH32B」——同時明寫**未追到來源、不主張是哪顆晶片**。
> 現在來源在手上：
>
> ```
> 0x0acb0  MX25L1605D  MX25L3205D  MX25L6405D  MX25L12805D  MX25L256
>          MX25L1635D  MX25L3235D  S25FL016A   S25FL032A    S25FL064P
>          S25FL128P   EN25F16     EN25F32     EN25Q16      EN25Q32
>          GD25Q8      GD25Q16     GD25Q32     GD25Q64      GD25Q128
>          W25Q16      W25Q32      W25Q64      W25Q128      W25X16
>          W25X32      W25X64      AT25DF161
> 0x0adcc  UNKNOWN          ← 表的最後一格,就是 console 印出來的那個字
> 0x0ade4  chipName: %s     ← 印它的那一行
> ```
>
> | 那份筆記的假設 | 現在的狀態 |
> |---|---|
> | 表裡沒有這顆晶片 | ✅ **成立** —— Eon 只有 `F` 和 `Q` 兩系，**沒有任何 `QH`**，而 `UNKNOWN` 是表的成員 |
> | 「所以它退回通用 SPI 指令」 | ❌ **仍未確認** —— 這是行為主張，我手上是字串不是程式碼 |
> | 它認不出來的是哪一顆 | ❌ **仍未確認，而且刻意不主張** —— **JEDEC ID 到今天還沒讀過**
>   （`notes/hardware-inspection.md` 第 26/341 行），晶片身分目前只有絲印一個來源 |
>
> **對開放 #17 的影響是壞消息**：loader 認不得這顆晶片，所以 `FLW` 走的是它的
> 通用路徑，而通用路徑的抹除語意**更沒有理由用別顆晶片的行為去推**。
> 那四行指令因此更該跑，不是更不該。

### 8.9.4 改良後的步驟（下次寫 flash 用這一版）

上面 §8.9 的六步是 2026-08-17 實際跑的那一版。**它有一個設計缺陷，而缺陷
不在指令，在讀回的位址**：

> 🔴 **每一次讀回都要用一個從來沒用過的 RAM 位址。**
> 原版的 Step 5 讀回用了 `80540000`，而 Step 4 已經把同一個樣式放進那裡 ——
> 所以「值沒變」和「`FLR` 沒生效」分不開。§8.7.8 早就用名字警告過這個坑，
> 而作業單自己踩了進去。

**下次的順序，每一步換一個 RAM 位址，而且每次 `FLR` 之前先 `DB` 一次當對照組：**

```
# 對照:讀之前那塊 RAM 是什麼
DB 80560000 8
FLR 80560000 <flash 位移> 8
Y
DB 80560000 8          ← 內容有變 = FLR 生效了
```

**判別 `FLW` 是否抹整個磁區**（這一項在 2026-08-17 之後仍然未決，見 §8.9.3）：

```
DB 80560000 8 ; FLR 80560000 3F0100 8 ; Y ; DB 80560000 8
```

> ### 📌 手打之前先看這個：工具已經比手做好了
>
> ```bash
> python3 -u tools/console-dump.py dump --at-prompt \
>     --flash 0x3F0100 --length 8 --ram 0x80560000 --chunk 8 \
>     -o ~/fwre-work/dumps/w05-sector-probe-$(date +%Y%m%d-%H%M).bin
> ```
>
> 它比上面那四行多三件事，而且第三件正是上一場踩的坑：
>
> 1. `flr()` 會**確認 `(Y)es` 提示真的被接受**，不接受就丟例外。
>    上一場的逐字紀錄裡有一行 `(Y)es , (N)o ? --> T Y` —— 手打會發生這種事。
> 2. `DB` 的每一塊都被解析驗證，而且會二次取樣重讀。
> 3. **對照組先把 flash `0x000000` 讀進同一個 `--ram`**，比對已知的
>    `0b f0 00 04`。所以在真正的讀取之前，`0x80560000` 裡裝的是
>    **既不是 `ca fe ba be` 也不是 `ff ff ff ff` 的第三種東西** ——
>    §8.7.8「內容沒變就是 FLR 沒生效」那個坑，被對照組自動排除了。
>    **這比「換一個沒用過的 RAM 位址」更強**：沒用過的位址裡是什麼，你並不知道。
>
> `--no-control` 存在，但這一格**不准用** —— 對照組正是這一格的全部價值。

`ca fe ba be …` → 讀-改-抹-寫回，**每次 `FLW` 重寫整個 4 KiB 磁區**；
`ff ff …` → `FLW` 抹掉整個磁區而不保留，**寫 flash 的風險等級全部上調**。

**W06 為什麼非知道不可**：`HW_WLAN0_WSC_PIN` 在 `0x648a`，住在 `H601`
（`0x006000`）那個磁區裡 —— 那是這台的 MAC 和射頻校準值，全世界只有這一份。
如果 `FLW` 是整磁區重寫，寫入中途斷電失去的不是幾個 byte，是那個磁區。

---

## 8.10 W05 Day 0：測試登記簿怎麼用（G3.75）

W05–W07 要對同一台機器跑一百多個測試。**這一節是那一百多次的操作規程。**

### 8.10.1 為什麼不直接開一張表在 PROGRESS 裡

兩個理由，都不是潔癖：

1. **同一份狀態被兩個檔案擁有，一定會漂移。** 2026-08-16 就發生過一次
   （`PROGRESS.md` 說開放題已答、`LOG.md` 三個檔案外還把同一題當成未答）。
   130 列的表放兩份，一個禮拜就散。
2. **沒有事先寫下「失敗長什麼樣」的測試，事後一定會被讀成成功。** 回應到手的時候，
   讀的人已經知道自己想看到什麼了。

所以：`test-cases.toml` 是唯一擁有單項狀態的檔案，`test-ledger.md`
是它生成出來的，`tools/rtcase.py check` 在 CI 裡擋。

### 8.10.2 三個指令

```bash
# 這一週還欠什麼(每天開工第一條)
make todo WEEK=W05
#   W05: 0/31 done, 31 outstanding
#      [ ] P0-3   §3.2/12.3  bootloader 救援路徑演練 FLW→FLR→抹除(G3.5 #5)
#      [ ] P1-5   §4.5       E-0:57 還是 60 —— 測的是工具,不是裝置
#      ...

# 開工前:確認登記簿是綠的(CI 也跑同一條)
python3 tools/rtcase.py check
#   register OK - 130 cases, 102 frozen, 5 executed, freeze 69c342dce863dcc7...
#     outstanding: W05 0/31  W06 0/25  W07 0/60

# 跑完一項之後:記錄
python3 tools/rtcase.py record --id P3-3 --date 2026-08-20 \
    --verdict confirmed --evidence dynamic \
    --artefact poc/formSysCmd/README.md \
    --note "回應 200,GET /k 取回 uid=0(root)"
#   recorded P3-3 = confirmed (dynamic) in test-results.json

# 重生成可讀的那一份,然後再 check 一次
make ledger
```

| 欄位 | 只能填 | 意思 |
|---|---|---|
| `--verdict` | `confirmed` / `refuted` / `partial` / `na` | 成立 / 不成立 / 部分 / 不適用 |
| `--evidence` | `static` / `dynamic` | **真的送過封包才算 `dynamic`。** 填 `static` 的話，登記簿印 🟥 不印 ✅ |
| `--artefact` | 可重複，repo 相對路徑 | 判 `confirmed` / `partial` 一定要有，而且路徑必須存在 |

### 8.10.3 反證條件怎麼寫

**這是整份登記簿唯一真正重要的欄位。** 判準是：*看到什麼，我就承認這條不成立?*

| ❌ 這樣寫沒有用 | ✅ 這樣寫才擋得住自己 |
|---|---|
| 「沒有反應就是不成立」 | 「未帶憑證收到 301 到登入頁 → `未認證` 的讀法錯了，NVD 的 `PR:H` 是對的，X-7 那條爭議要撤回」 |
| 「掃不到就是關的」 | 「9034 有回應 → rootfs 的 ELF 清單漏了東西。那比命中一個 KEV 更重要，因為它讓所有『這台沒有 X』的說法一起失效」 |

差別是：好的反證條件會**指名哪一份既有結論要跟著改**。寫不出那一句，通常代表
這個測試本身還沒想清楚要問什麼。

### 8.10.4 要改預測的時候

改了就得同時改 `[freeze].sha256`，**而且要在同一個 commit 裡**：

```bash
python3 tools/rtcase.py freeze        # 印出新的雜湊,自己貼進 test-cases.toml
python3 tools/rtcase.py check
```

> ⚠️ **如果那一項已經有結果了，`check` 會直接擋下來**，因為每一筆結果都戳了它
> 當時被判定所依據的那段文字的雜湊。要改就得連戳記一起改，`git diff` 會把
> 「事後改了預測」這件事攤在那裡。這不是防你，是讓那個動作留下痕跡。

### 8.10.5 紀錄卡（每一次執行都要留）

登記簿只留判定與證據連結。**逐字的 request / response 留在這裡的格式**：

```
T-xx  <項目 ID>                                    日期時間:
可行性: ★    出場證據:            依據:
送出(逐字,含完整 URL 與 body):

原始回應(狀態碼 + header + 前 200 bytes):

觀測通道 1(例:GET /k 的內容):
觀測通道 2(例:tcpdump 的 ICMP/DNS):
UART console 當下輸出:

判定:  ✅成立 / ❌不成立 / 🔶部分 / ⚠️不確定(說明為什麼)
反證檢查: 測前寫的是「看到 ___ 就不成立」,實際看到 ___
這一步燒掉了什麼(不可逆的部分):
下一步:
```

**「反證檢查」那一行不能空白。** 它跟登記簿裡凍結的那一句必須對得起來 ——
對不起來就是你測的不是你當初要測的東西。

### 8.10.6 會踩到的

| 症狀 | 原因 |
|---|---|
| `check` 說 `freeze mismatch` | 改了 `predict` 或 `refute` 沒重算雜湊。跑 `rtcase freeze` 貼回去 |
| `record` 拒絕，說 `no refutation condition` | 那一項還沒寫反證。**先寫，不要先記結果** —— 這是刻意的 |
| `check` 說 `artefact ... does not exist` | 證據連結指到不存在的檔。證據不能是裝飾 |
| `check` 說 `has been edited since the result` | 有結果的項目被改了預測。要嘛把字改回去，要嘛連戳記一起改讓 diff 看得見 |
| CI 說 `test-ledger.md is out of date` | 改了登記簿沒跑 `make ledger` |
| 本機 `python3` 說沒有 `tomllib` | Windows 側那顆是 3.10。走 WSL，或 `FWRE_PY=$HOME/fwre-work/venv/bin/python` |

### 8.10.7 這個 gate 自己會不會騙人

會，所以有 `bash tools/test-rtcase.sh`：1 個必須通過的對照組 + 21 個
**必須被擋下來、而且必須是因為正確的理由被擋下來**的案例。`make ci` 兩個都跑。

> 沒有對照組的守衛套件會在整個系統壞掉的情況下全綠 —— 2026-08-14
> `tools/test-photo-tools.sh` 就是 5/5 通過而每一次呼叫都死在 `import PIL`。
> 這 22 個案例第一次跑就抓到 `rtcase record` 的一個真 bug。
> **2026-08-17 增至 27 個**，新的五個裡有三個在測「執行過 ≠ 在矽上執行過」的
> 渲染規則（§8.11.5）。

---

## 8.11 W05：把這台的韌體跑起來（qemu-user + 真 flash）　→ `runsheet.md` `A1.4`

**W01 就證明過 2015 的 MIPS 執行檔能在 x86 上跑，唯一被點名的阻礙是
`libapmib` 要讀 `/dev/mtd*`。W02 之後那個檔案在手上了。**

### 8.11.1 三個指令

```bash
sudo make qemu-env                      # 建環境(約 30 秒)
sudo bash tools/qemu-env.sh check       # 陽性對照
bash tools/test-qemu-env.sh             # 守衛套件(不需要 root 的那半也會跑)
```

`build` 做的每一步都抄自這台自己的開機：`/etc/init.d/rcS` 的 `mkdir /var/*`、
`/bin/sysconf` 字串表裡的 `cp -a /etc/boa/boa.conf.bak /var/boa.conf`、
以及 `flash extr /web`（**用廠商自己的解壓工具灌 docroot，不是我們的**）。
**唯一不是這台自己的，是把 flash dump 放成 `/dev/mtdblock0`。**

### 8.11.2 陽性對照為什麼是三個值而不是一個

```bash
sudo bash tools/qemu-env.sh check
#   control ok: TELNET_ENABLED=0
#   control ok: IP_ADDR=10.1.1.1
#   control ok: USER_NAME="admin"
#   MIB lines from the vendor binary: 2317
#   positive control passed
```

三個值都是 W04-2 用**不共用程式碼的解碼器**讀出來的。錯的映像、空的裝置檔、
留在共享記憶體裡的舊值，每一種都會打掉其中至少一個。守衛套件證明它們真的會掉。

### 8.11.3 ⚠️ 復原檔案不等於復原狀態

`flash` / `boa` / `sysconf` 把 MIB 表快取在 **System V 共享記憶體**裡。
那段記憶體屬於**主機**核心，活得比 guest 行程久，而且 `cp` 回 `/dev/mtdblock0`
碰不到它。

```bash
sudo bash tools/qemu-env.sh run /bin/flash set HW_WLAN0_WSC_PIN 11111111
sudo cp <pristine> ~/fwre-work/qemu-env-2018/dev/mtdblock0     # 只復原檔案
sudo bash tools/qemu-env.sh run /bin/flash get HW_WLAN0_WSC_PIN
#   HW_WLAN0_WSC_PIN="11111111"      ← 值是從 shm 來的,不是從檔案
```

**每次量測之前跑 `reset`，不要自己 `cp`。**

```bash
sudo bash tools/qemu-env.sh reset       # 檔案 + shm/sem 一起
```

這一坑不是從 strace 推出來的，是**一次量錯的結果**：只改了 `HW_WLAN0_REG_DOMAIN`
的那一輪，diff 裡冒出七個 WPS PIN 欄位的 byte —— 上一個測試留下的。

### 8.11.4 一個指令，兩個 oracle

```bash
sudo bash tools/qemu-env.sh reset
sudo bash tools/qemu-env.sh run /bin/sh -c \
     'flash set HW_WLAN0_WSC_PIN 1;ls -l / > /var/web/x.txt 2>&1;#'
sudo bash tools/qemu-env.sh diff
#   3 bytes changed
#     0x00648a  0x39 -> 0x31
#     0x00648b  0x39 -> 0x00
#     0x006493  0x0d -> 0x4e   <- H601 checksum
#   checksum: delta 65, expected 65 -> balances
```

上面那一行 `sh -c` 的字串，就是 `boa` 的 `sprintf` 會組出來的東西。
輸出落在 docroot（oracle 0），flash 上被改掉的三個 byte 是 oracle 4。
完整設計在 [`notes/oracle-design.md`](notes/oracle-design.md)。

> **`boa` 本身在這裡起不來** —— 它在 `libapmib.so+0x27dc` 的一個**未對齊半字存取**
> 上吃 SIGBUS，而真機的 kernel 會靜靜幫它修好。這不是韌體的缺陷也不是指令集問題
> （那條指令是 opcode `0x29`，標準 MIPS I，手算編碼對過原始 bytes）。
> 經過在 [`notes/emulation-2018.md` §4](notes/emulation-2018.md)。

### 8.11.5 登記簿多了第三種證據等級

模擬環境裡跑出來的結果**既不是靜態、也不是動態**。記成 `static` 低估了它
（東西真的執行了），記成 `dynamic` 就是登記簿存在要防的那種灌水。

```bash
python3 tools/rtcase.py record --id P3-6 --date 2026-08-17 \
    --verdict confirmed --evidence emulated \
    --artefact notes/oracle-design.md --note "..."
```

`emulated` 渲染成 **🟪，永遠不會變成 ✅**，而 `tools/test-rtcase.sh` 有三個案例
在測這條規則。順帶修掉一個潛伏的 bug：圖例原本用左欄的長度去索引右欄，
**第七個結果標記會被靜靜丟掉** —— 而那正好是新加的這一個。

### 8.11.6 網路那一輪：`tools/bench-probe.py`

```bash
python3 tools/bench-probe.py control     --host 10.1.1.1
python3 tools/bench-probe.py fingerprint --host 10.1.1.1 -o $D/w05-fingerprint.json
python3 tools/bench-probe.py gate        --host 10.1.1.1 -o $D/w05-gate.json
python3 tools/bench-probe.py endpoints   --host 10.1.1.1 -o $D/w05-endpoints.json
python3 tools/bench-probe.py ssdp        --host 10.1.1.1 -o $D/w05-ssdp.json
bash tools/test-bench-probe.sh           # 8 個案例,不需要裝置
```

**它擋掉的那件事**：POST 到 `/boafrm/*` 少帶 `submit-url` 會讓 handler
`strcpy("/status.htm")` 寫進唯讀段，照程式碼讀那會打掛 web server ——
然後**後面每一個端點都會回「連不上」，看起來就跟「端點不存在」一模一樣**。
一次打錯，57 個端點的普查變成 57 個偽陰性。

它還做兩件事：**每 10–20 個請求重跑一次對照組**（否則「後半段全失敗」無從得知
從哪裡開始壞的），以及**參數裡有 shell 元字元就拒絕送**（注入是 W06 的，而且
在回復演練之後）。端點清單從 `reports/ghidra-formtable-unit-2018.json` 讀，
不是寫死的。

> ⚠️ `endpoints` **預設走 GET**。`--allow-post` 會真的執行 handler ——
> `formWlanSetup` 收到只有 `submit-url` 的 POST，其他參數全取預設值，
> 那可能就是把無線設定清掉。要跑就前後各抓一次 64 KiB 快照。

---

### 8.11.7 `--alignfix`：把 `qemu-user` 跟裝置核心的那一個差異補掉（W07，2026-08-18）

**為什麼需要它。** `handler-sweep.py` 報 **57 個 handler 裡有 39 個**被一個
合法 POST 打死。那支工具自己把欄位命名成 `died_under_emulation` 並附上
「這不是關於裝置的主張」，因為它答不出原因。W07 把 `gdb-multiarch` 接上
`qemu-mips-static` 的 gdbstub，讓故障當場發生：

```bash
# 讓 boa 不要 daemonise（-d），並在第一道指令之前等除錯器（-g）
sudo chroot /home/key/fwre-work/qemu-env-2018 ./qemu-mips-static -g 1234 \
     /bin/boa -d -f /var/boa-emu.conf
gdb-multiarch -batch -ex 'set architecture mips' -ex 'set endian big' \
     -ex 'target remote 127.0.0.1:1234' -ex continue -ex 'x/8i $pc-24'
```

```text
Program received signal SIGBUS, Bus error.
=> 0x2b2c87dc:  sh  s7,0(s8)
```

那個位址在 `libapmib.so + 0x27d0`,函式是 **`mib_write_to_raw`**——把 MIB 打包
成 TLV 寫進 flash 緩衝區的那一支。**變長記錄，欄位偏移天生是奇數。**
MIPS Linux 核心會在 trap handler 裡替使用者空間補完未對齊存取，裝置上什麼事
都不會發生；`qemu-user` 直接送 SIGBUS,而 `boa` 自己有一個 SIGBUS handler
會 dump core 然後 abort。

> 🏆 **所以那 39 個的共同點不是脆弱，是「它們會存設定」。**
> 19 個「活著」的是參數不足提早返回、根本沒走到序列化器的。
> 這也一併解釋了 `P8-24` 那個「寫入不可觀測」——`flash default-sw` 死在同一行。
> **兩個分開記錄的觀察是同一個 bug。**

**怎麼用：**

```bash
sudo FWRE_WORK=/home/key/fwre-work tools/qemu-env.sh --profile unit-2018 serve 8080 --alignfix
sudo FWRE_WORK=/home/key/fwre-work python3 tools/handler-sweep.py --profile unit-2018 \
     --alignfix --out reports/handler-sweep-unit-2018-alignfix.json
bash tools/test-alignfix.sh          # 8 個守衛案例,不需要裝置也不需要 root
```

> ### ⚠️ 三件事，每一件都是踩過才寫下來的
>
> **1. 它預設關閉，而那是決定不是疏漏。** 打開它會改變這個環境**是什麼**。
> 2026-08-18 以前所有模擬量測都是在沒有它的情況下取得的，profile 的陽性對照
> 也是。一個安靜改掉這件事的旗標，會讓兩個不能並列的東西看起來像同一個。
> `serve` 每次都印它是哪個模式。
>
> **2. 它會拒絕，而不是猜。** o32 的 `ucontext` 偏移是寫死的，而寫錯的偏移
> 會產生看起來很合理的垃圾。所以 handler 會把復原出來的 `pc` 讀回去、要求
> 那道指令解得出 `lh`/`lhu`/`sh`/`lw`/`sw`,**而且**要求用復原出來的暫存器
> 算出的位址真的沒對齊。任一項不過就把 `SIG_DFL` 裝回去，讓程序照原本的方式
> 死掉。`tools/test-alignfix.sh` 會編一支故意寫錯偏移的版本來證明那條路走得到。
>
> **3. 修好它當場弄壞了另一件事，而且是對照組抓到的。** 崩潰消失之後
> handler 真的會存檔——而每次探測前的還原本來是**崩潰的副作用**。於是探測 N
> 讀到的是探測 1..N-1 寫下去的東西。環境自己的陽性對照下一次 `check` 就回
> `USER_NAME=""` 而不是 `"admin"`。現在 `--alignfix` 會把 `--reset-each`
> 一起打開，而且掃描跑完會再跑一次 `check`,環境漂掉就讓整輪失敗。

### 8.11.8 `tools/mipsref.py`：問「誰參照這個位址」，而且不靠 Ghidra

`BoaXref` 的 `refs:` 用 Ghidra 的參照模型回答同一個問題。對 `check_auth_flag`
它的答案是「一次寫、零次讀」——而**一個被寫但沒人讀的全域**是一個很強的主張，
它決定那個上游缺陷在這個 build 上是活的還是死的。CLAUDE.md 的規矩是
**沒有單一工具的主張**。

```bash
python3 tools/mipsref.py <binary> --addr 004899d8 --control 004899e0
python3 tools/mipsref.py <binary> --segments      # RELRO / NX / GOT 在哪個段
```

它跟 Ghidra 獨立：沒有符號表、沒有分析資料庫、沒有參照模型，只解指令編碼。
三種定址都掃——`lui`+`%lo` 配對、`gp` 相對、`$zero` 絕對——**漏掉任何一種，
看起來會跟「乾淨」一模一樣**。`gp` 不是從 Ghidra 拿的，是從 ELF 自己的
`PT_DYNAMIC` 算 `DT_PLTGOT + 0x7ff0`；`sstrip` 吃掉的是 section header，
segment 還在，所以這條路在這個語料上走得通而 `readelf -S` 走不通。

> **`--control` 是重點不是選項。** 它指定一個**必須**回報至少一次讀和一次寫的
> 位址。解碼錯、`gp` 算錯、file offset 對 vaddr 的換算錯——控制組都會回零，
> 這支工具就 exit 2,而不是印出一個很有自信的空答案。那是 `BoaGate` 學了兩次
> 的同一課。

#### 2026-08-19：v1 的答案是錯的，而裝置抓到它，控制組沒有

`P2-11` 在實機上量到 session 視窗在**每一次登入後 601 秒**關掉、而不是開機後
601 秒，兩個相隔 706 秒的錨點都落在 `login+601`。v1 對 `beforeuptime`
（`0x004899dc`）的回答是「一讀、零寫」，而那個寫**從頭到尾都在 `0x0044f140`**。

三種盲點，任何一種單獨都足以把一個被寫的全域報成 `writes: 0`：

1. **儲存指令裡根本沒有那個位址。** o32 PIC 從 GOT 取全域的位址——
   `lw $v1,%got(beforeuptime)($gp)`——然後 `sw $v0,0($v1)` 寫進去。`sw` 的
   立即數是 `0`。那條指令沒有提到 `0x004899dc` 的任何一個 bit。
2. **位址進了暫存器，既不是存取、也不是「沒有存取」。**
   `addiu $a0,$v0,%lo(authipaddr)` 把位址做出來給 callee 寫。v1 給它
   `reads: False, writes: False`——在總數上跟「沒有被參照」分不出來。
3. **一個 GOT 槽被當成變數報出去。** 已提交的報告把 `0x00486270` 標成
   `authipaddr`、「6 次讀、0 次寫」。`0x00486270` 是 `authipaddr` 的 **GOT 槽**；
   變數在 `0x0048fbd8`。那六次全是 `lw ...($gp)`——**六次取址，一次讀都沒有。**

所以 v2 報四類不報兩類，而且把「位址被取用」和「位址被寫入」分開：直接讀、
直接寫、取址（`addiu` 或 `lw %got`）、以及**經由暫存器**的間接讀寫與
「活著進入呼叫」。`beforeuptime` 現在是「1 次直接讀 + 1 次間接寫（`0x0044f140`）」，
`authipaddr` 是「0 讀 0 寫、6 次取址、6 次活著進入呼叫」——那正是 `strcpy` 的形狀。

**同一個變數在同一支 binary 裡用兩種定址模式，而那才是這一課。**
gate（`0x0040bff8`–`0x0040c000`）用 `lui`+`%lo` 直接定址，v1 看得見；
`form_formLogin`（`0x0044f134`）用 GOT，v1 看不見。**「一讀零寫」不是韌體的
性質，是掃描器只看得見兩種模式中的一種。**

> 🔴 **`sstrip` 沒有吃掉符號表，而這個專案以為它吃掉了。**
> section header 沒了，所以 `readelf -s` 什麼都不印——但 `.dynsym` 是
> `DT_SYMTAB` / `DT_STRTAB` 指到的，那兩個在 `PT_DYNAMIC` 裡，因為 loader 需要
> 它們。這支 boa 有 **423 個具名符號**，`beforeuptime` 與 `authipaddr` 都在裡面，
> 帶真實位址。那是 `--sym` 的來源，也是工具現在能自己說出「`0x00486270` 不是
> `authipaddr`」的原因——那句話以前要靠讀者發現。

> 🔴 **第一個控制組一路都是綠的，而它證明的路徑不是出事的那條。**
> `0x004899e0`（`nowuptime`）有一次直接讀和一次直接寫，所以 `--control` 在那次
> 錯誤的執行裡就是通過的。**一個控制組只證明它自己走過的那條路。**
> 所以 v2 多一個 `--control-indirect`：它要求**至少一個經由暫存器找到的寫**，
> 少了 deref pass 就會大聲失敗，而不是安靜地印出 v1 的數字。`nowuptime`
> 兩種都有——`0x0040be54` 直接寫、`0x0044f14c` 經 GOT 寫——所以它一個位址同時
> 當得了兩個控制組。`check-reports.py` 對 `schema >= 2` 的報告強制這一格。
>
> 寫這個 deref pass 的時候，第一版立刻被自己的新控制組打掉：`jalr` 會破壞
> caller-saved 暫存器，所以我在呼叫處就停止追蹤——**但延遲槽在控制權轉移之前
> 執行**，而 `nowuptime` 的寫正好在延遲槽裡。一條指令，答案就反過來。

第二來源照 CLAUDE.md 的規矩走**指令層**：`ghidra/scripts/BoaListing.java` 對
`0x0044f0e0`–`0x0044f190` 印出的清單裡，`0044f140 sw v0,0x0(v1)` 旁邊
Ghidra 自己標了 `-> beforeuptime`。**資訊一直在工具自己的輸出裡，差一層間接。**

`make mipsref-reports` 重新產生那兩份報告，命令寫在 Makefile 而不是留在 shell
history —— 手打是第一份報告會把 GOT 槽當成變數的原因之一。

---

### 8.11.9 `tools/device-liveness.py`：問裝置它還能不能做它的本業

**這支工具存在是因為一次持續兩天的失敗，而那兩天裡每一場進站都是綠的。**

W05 的未認證 POST 輪把 `DHCP_MTU_SIZE` 從 1500 寫成 0。`eth1` 從那天起以 `MTU:0`
開機：送不出一個封包、拿不到 WAN 位址、每一次重開都一樣。**四場進站跑在中間，
沒有一場注意到** —— 因為這個專案的每一個儀器問的都是「**主機**準備好了沒」：
工具鏈、雜湊、序列埠、USB 網卡、隔離網段。沒有一個問「**裝置**還能用嗎」。

```bash
make liveness                                     # 問裝置
python3 tools/device-liveness.py --from-file cfg.bin --no-baseline   # 問一份存檔
```

**它怎麼問，以及為什麼是這條路。** 一發未認證的 `GET /config.dat`。那個路徑沒有
`.htm` 也沒有 `.asp`，所以授權閘門根本不跑（`CVE-2019-19822`，`P10-1`），而 `boa`
在啟動時就從 flash 的 `COMPCS` 區把那個檔建好。**所以一個請求就拿到整份現行設定，
而這個 repo 本來就有解碼器。**

**拿一個資訊揭露缺陷當健康檢查，是刻意的。** 其他路都更貴而且證明得更少：序列埠
console 沒有 shell；網頁介面要憑證，而且沒有任何一頁同時顯示這些欄位；telnet shell
要先用命令注入**開**出來——那會在量測之前改變裝置。這條什麼都不改、也不需要憑證。

**兩半，而第二半才是通用的修法。**

1. **有名字的斷言**，每一條帶著「壞了會怎樣」那句話。沒有那句話的欄位不該放進來：
   一個失敗訊息不說壞了會怎樣的檢查，會把讀者送去猜，而猜就是那四場做的事。
2. **對凍結基準線的漂移**，逐欄位列出並計數。**第一半只抓得到有人想過的破壞**，
   而 `DHCP_MTU_SIZE` 在它壞掉兩天之後才有人想到它。第二半是為了下一個。

> 🔴 **三種結果，而第三種是刻意存在的。** exit 0 是 `OK`；exit 1 是
> `BROKEN`（裝置回應了，而它不在做它的本業）或 `UNUSABLE`（解碼器指到錯的位移，
> 那是儀器問題）；**exit 3 是「裝置沒回應，什麼都沒有量到」** —— 那不是通過也不是
> 失敗，而 `make doctor` 把它顯示成 `--`。一個把「裝置關著」算成通過的健康檢查，
> 就是那四場進站。

> ⚠️ **它讀的是持久設定，不是執行時狀態。** `config.dat` 是 `boa` 啟動時寫的，
> 所以它看得見**跨重開機**的破壞——那正是沒人抓到的那一類——但看不見這一場手動
> `ifconfig` 改過的東西、死掉的行程、插錯埠的線。那些要靠線。

> ⚠️ **`--disclosure protect` 會把 per-unit 識別碼換成雜湊，而基準線是明文。**
> 拿雜湊去比明文會替每一個被遮蔽的欄位製造出一次假漂移——第一次真的跑就製造了五個。
> 所以只有兩邊都沒被遮蔽的欄位才進漂移清單，被遮蔽的那些單獨計數並列名。
> **一份訓練讀者不去讀的清單，跟沒有清單一樣。**

`tools/test-device-liveness.sh` 19 個案例，全部不需要裝置：判斷邏輯是一個純函數。

---

### 8.11.10 `tools/cve-endpoints.py`：公告的名字，對這個 build 的名字

見 [§8.12.39](#81239-公告的名字與這個-build-的名字為什麼要機械地比--runsheetmd-a110)
—— 那一節寫的是為什麼，這裡只放怎麼跑。

```bash
python3 tools/cve-endpoints.py --json reports/cve-endpoints-unit-2018.json
```

三個控制組任何一個倒了就 exit 2，而 `check-reports.py` 對這份報告強制 `control_ok`。
公告清單從 `notes/cve-status.md` 解析，**工具不帶第二份**。

---

### 8.11.11 `tools/rogue-dhcp.py`：WAN 側的假 ISP，以及它為什麼會拒絕跑

**這支工具會回答任何問它的東西，所以它最重要的部分是拒絕條件而不是功能。**

```bash
sudo python3 tools/rogue-dhcp.py --iface enx… --server 192.168.77.1      --offer 192.168.77.100 --route 10.99.0.0/16=192.168.77.66 --seconds 140
```

**四個拒絕，而第一個不是為了測試品質。** 一台 DHCP server 起在錯的介面上，會把
位址、預設路由和 DNS 發給那條線上的其他東西 —— 室友的筆電、手機、你自己這台。
**那不是一次失敗的實驗，那是別人要 debug 的斷線。** 所以：

- 只綁**一個**介面（`SO_BINDTODEVICE`），沒給就不跑；
- 拒絕帶著本機預設路由的介面；
- 拒絕「介面自己的位址不在它要發出去的網段裡」—— 那個組合代表操作者腦子裡的線
  跟 socket 上的線不是同一條；
- `--only-mac` 之下拒絕回答其他 client，因為這張桌子只有一台受測裝置。

**`--route` 一次送三個選項（121、249、33），而那是設計不是偷懶。** 這台自己的
DISCOVER 同時索取這三個，而哪一個它真的照做是問題本身；一次送三個保證送得到，
代價是失去歸因（`PROGRESS.md` 開放題 #77）。要歸因就分三次各送一個。

**為什麼不是 `dnsmasq`。** 這一節要送的是一台正常 server 不會送的東西，而且**封包
要進紀錄** —— 「裝置拿了租約」和「裝置問了、我答了」是兩件不同的主張，只有 capture
分得開。2026-08-18 那一版是臨時腳本，而臨時腳本送不出有趣的那一半。

`tools/test-rogue-dhcp.sh` 12 個案例：選項編碼逐 byte 對手算值（`option 121` 的
`/16` 必須是 `10 0a63 c0a84d42`，`option 33` 必須是固定 8-byte 對且不帶遮罩），
加上兩個 CLI 拒絕。**CI 不是 root，而那正是 `geteuid` 那條拒絕跑得起來的原因** ——
它必須在開 socket 之前拒絕，不是之後。

---

## 8.12 實機場次：每一步為什麼存在

> ## 🔴 這一節一個命令都不放，而那是 CI 執行的
>
> **要複製貼上的命令、逐字的預期輸出、每一步的停止條件，全部在
> [`runsheet.md`](runsheet.md)。** 這一節保留的是**為什麼每一步存在、坑的來歷、
> 以及跨週的推理** —— 而那些東西 runsheet **不重複**。
>
> **理由是「一份狀態一個擁有者」，而這一次切法不同：按內容種類切，不按檔案切。**
> 命令有一個擁有者（`runsheet.md`），推理有一個擁有者（這裡）。兩邊互相指名，
> 沒有任何一段話出現兩次。
>
> **為什麼要這樣切：** §8.12 是**參考書**形狀 —— 它假設讀者知道自己為什麼在這裡。
> 一個第一次 clone 這個 repo 的人需要的是**程序**形狀：線性、有預期輸出、
> 而且**能叫他停下來**。把兩者塞進同一節的結果是兩邊都做不好。
>
> | 你想知道 | 去讀 |
> |---|---|
> | 確切要打什麼、會看到什麼、什麼時候該停 | **[`runsheet.md`](runsheet.md)** |
> | 這一步為什麼存在、上次是怎麼壞的 | **本節** |
> | 我能重現到哪裡（三層） | [`REPRODUCE.md`](REPRODUCE.md) |
> | 那一天實際發生了什麼 | [`BENCH-LOG.md`](BENCH-LOG.md) |
>
> **`tools/check-runsheet.py` 對本節驗兩件事：§8.12 底下一個 `bash` /
> `powershell` fence 都不准有**，而**每一小節必須指名它對應的 `runsheet.md`
> 的 `A` 節，一對一 —— 少一邊就紅**。
>
> 🔴 **這兩條規則是 2026-08-17 補的，而它補的是一個真實的失效。**
> 本節上一版開頭就寫著「命令搬走了」—— 然後裡面留著 **12 個命令塊**，
> 其中**四個當天就被實測否證了**：冒號式的 `AUTOBURN: 0`
> （回 `Unknown command !`，`?` 印的說明文字不是語法）、把「`ping` 有回應」
> 當成救援成功條件（loader 的堆疊沒有義務實作 ICMP）、
> 「Linux 一定會印 `Kernel command line:`」（那個字串根本不在 image 裡）、
> 以及用兩個終端機量冷開機時間（兩個終端機的時鐘不能相減）。
>
> **檢查器看不到那四個，因為它只讀 `runsheet.md`** —— 而這裡放的偏偏是同一批
> 命令的舊版本。所以修法不是「去檢查這裡的命令」，是**讓這裡不准有命令**：
> 一個不准放命令的段落裡，不可能有過期的命令。
> `tools/test-check-runsheet.sh` 證明那支檢查器自己會失敗。

**W05 之後每一週都有實機場次，而三週的流程不一樣**：W05 是偵察，W06 會**寫
flash**,W07 是大量迭代。共用的只有前綴。所以這一節不是一份流程，是**幾個
可以單獨讀的小節**；一週跑哪幾節寫在 [`runsheet.md` Part B](runsheet.md)。

> **不要為某一週開一份 `W0N-bench-runsheet.md`。** W05 開過一份，1,091 行裡
> 580 行是跨週可重用的規程 —— 第二份就是同一份狀態兩個擁有者，而這個 repo
> 已經因為那件事失敗過兩次。
>
> **實際跑了什麼寫進 [`BENCH-LOG.md`](BENCH-LOG.md)**（根目錄，只追加）：
> 這一場的計畫寫在動手之前，下面接逐字節錄。
> **因為那份紀錄是逐字的，本節可以自由精煉** —— 證據站在紀錄上，不站在這裡。

### 8.12.0 一週跑哪幾節：擁有者是 runsheet Part B

> 🔴 **這一小節原本自己放一張組合表，而 `runsheet.md` Part B 也有一張。**
> 同一份狀態兩個擁有者，用兩套編號描述同一個上午 ——
> 這裡寫 `1 → 2 → 3 → 4`，那裡寫 `A0 → A2 → A3 → A5`。
> **2026-08-17 收掉了：組合表只在 [`runsheet.md` Part B](runsheet.md) 有一份**，
> 本節只留「為什麼那樣排」。

**W05 下半的順序有兩個理由，而第一個比看起來重要：**

1. **§8.9.3 那四行排第一。** 它是純讀（`DB`/`FLR`，四行，約 20 秒），而它答的是
   **W06 非知道不可**的那一格 —— `HW_WLAN0_WSC_PIN` 在 `0x648a`，住在 `H601` 的磁區裡。
   排第一不是因為它有時效，是因為**一場只要提早結束，最不能掉的就是它**。
   （§8.12.3 的快照也是純讀，兩者誰先都不會互相污染。）
2. **console 那半場整段排在網段之前**，因為 §8.12.10 / 8.12.11 / 8.12.9 一個都不需要
   網路卡交給 WSL，而 `usbipd attach` 不會活過 WSL 重啟 —— 少一個會在中途壞掉的相依。

**§8.12.3（快照）在每一節之前都要跑一次，而且它便宜到沒有藉口不做**：64 KiB,
約 90 秒，而完整的 4 MiB 是 105 分鐘。

---

### 8.12.1 開工前，還沒碰裝置　→ `runsheet.md` `A1.1`

**為什麼開工第一條是一支腳本而不是一份清單：一份 markdown 可以叫讀者去檢查
某件事，只有腳本能告訴他壞掉的是哪一項。** `make doctor` 的每一個 `FAIL`
自帶修它的那一行命令 —— 那條規則把「照做了但沒用」變成「這一項壞了，
而這是修它的命令」，而前者是新手放棄的地方。

**它第一件事驗還原鏡像的雜湊，而那不是禮貌。** 那兩份 dump 是這台的唯一備份；
`H601`（`0x006000`）裡的 MAC 與射頻校準**全世界只有這一份**，原廠映像沒有，
「恢復原廠設定」也不還原它。**備份壞了就沒有安全網，而沒有安全網的時候
§8.9 那一節不准開始。**

> 🔴 **「不要按 reset 鍵」是這一段唯一的實體禁令**，理由是它會用 `COMPDS`
> 蓋掉 `COMPCS` —— 毀掉的是這台的現況證據。**而 2026-08-17 之後這件事變得更嚴重**：
> 那天的 POST 輪已經把 `COMPDS` 覆寫成 `COMPCS`，所以在這個 build 上
> 「恢復原廠設定」還原的是**最後被寫進去的那一份**。
> reset 鍵不是復原路徑，唯一的復原是從裝置外的副本重寫。

---

### 8.12.2 抓 bootloader　→ `runsheet.md` `A2.2`

**搶 bootloader 是「連續送 ESC」，而那個做法留下一個坑：**
loader 只吃一個 ESC，**其餘全部排在輸入緩衝區裡**，所以**搶到之後第一條手打的
指令必定回 `Unknown command !`**。工具的 `settle()` 會先送一個裸 `\r` 清掉；
手打就先按一次 Enter。（§8.7.9 的第 7 號儀器 bug。）

**抓不到不要重試超過三次**，理由是成本不對稱：每一次都是一次完整開機循環，
而 2026-08-17 抓失敗那一次的真正原因不是視窗太短，是**板子沒有真的斷電過** ——
`catch` 抓到的是執行中的 Linux console 對 ESC 的回應。那個失效模式看起來
跟「時序沒抓準」一模一樣，所以工具現在會分辨並印
`the board booted past the interrupt window`。

**要讓它正常開機進 Linux：拔電、插電、不送 ESC。** 那是進 runsheet 第 3 站的方法。

---

### 8.12.3 64 KiB 設定區快照，每次動手前　→ `runsheet.md` `A2.3`

**這一份同時是三件事**：還原點、IoC 預檢的輸入、以及「上一場到現在沒被動過」的證明。
`0x6000` 的 `H601`、`0x8000` 的 `COMPDS`、`0xC000` 的 `COMPCS` 全在那 64 KiB 裡。

**它便宜到沒有藉口不做，而那個成本差是這一節存在的全部理由**：64 KiB 約 95 秒，
完整的 4 MiB 是 105 分鐘 —— 而**會被改的只有那 64 KiB**。

> 🔴 **`FLR` 之前先跑一個正對照組，而那是這一步真正的價值。**
> `FLR` 會問 `(Y)es , (N)o ?` 並且**把下一行整個吃掉當答案**。如果那個 `Y`
> 沒被接受，`FLR` 根本沒生效，接下來 `DB` 印出來的是 **RAM 裡上一次留下的舊資料**
> —— 一份格式完全正常、內容完全錯誤的 dump。
> 對照組（讀 flash `0x000000`，比對已知的 `0b f0 00 04`）把那件事變成一個例外，
> 而不是一個結論。（§8.7.8 記過的第一號陷阱。）

> ❌ **IoC 預檢出現一筆你的紀錄裡沒有的差異 → 停手，走事件處理程序。**
> 這型號在公開的殭屍網路工具裡被點名過。
>
> ⚠️ **但判準是「跟上一場收工時記下的數字相同」，不是一個常數。**
> 那個數字到 2026-08-17 上午是 4 / 343，下午的 POST 輪之後是 0 / 343 ——
> 因為那一輪把 `COMPDS` 覆寫成 `COMPCS` 了。**看到不是 4 就當資安事件是錯的。**

> ★ **`IDENTICAL` 在 2026-08-17 變成了一個免費的對照組**：那天 11:02 的快照與
> 8/16 的完整 dump 逐 byte 相同 —— **而那期間這台開過機至少兩次、跑過完整的
> GET 輪、還成功登入過一次**。所以「開機和讀取不會改設定區」不是假設，是量出來的，
> 而那正是下午 POST 輪的差異可以**全部歸因**給 POST 的理由。

---

### 8.12.4 網段，並且**證明**是直連　→ `runsheet.md` `A3.1`

> 🔴 **這一步唯一的對照組是路由表，不是 `ping`。**
> 關鍵字是 `via`：`ip route get 10.1.1.1` 有 `via` 就是繞道，沒有才是直連。
>
> **2026-08-17 實測踩過**：`ping` 三個全通、而作業單寫死的 `eth1` 這個介面
> **不存在**，兩件事同時為真 —— 因為封包繞經 Windows 出去了。
> 在那個狀態下隔離確認做不了、SSDP 一定失敗得像「服務沒開」、
> 兩個來源 IP 會被 NAT 成同一個、`nmap -sS/-sU` 量的是那條路徑不是裝置。
>
> ⚠️ **而 `ping` 會通，唯一的破綻是 `ttl=63` 不是 64。** 少的那一跳就是路由器。
> 這是儀器 bug 21，而它是靠**讀路由表**發現的，不是靠看 `ping` 成功 ——
> 所以判準寫成路由表，`ttl` 只是它的第二來源。
>
> `tools/bench-probe.py` 現在每次執行都自己從 `/proc/net/route` 判定這件事，
> 記進 transcript，並對 `ssdp` 那一組**直接拒絕執行**。

**介面名字不要寫死**：它叫 `enx<mac>`（Linux 的可預測命名），不叫 `eth1`。
上面那個失效模式的起因就是一份寫死了 `eth1` 的作業單。

---

### 8.12.5 隔離確認，而且要帶對照組　→ `runsheet.md` `A3.3`

**成功條件：剛好兩個 MAC，沒有 DNS，沒有對外連線。**

> 🔴 **「抓到零個封包」不是證據。** 2026-08-17 第一次抓 45 秒得到零，
> 差點寫成「網段乾淨」—— 而那一刻 kernel 的計數器是 `RX: 0 packets / TX: 12`，
> **送得出去、收不回來**。所以這一節**主動製造已知流量**，
> 而「封包數 > 0」就是那次擷取的對照組。
>
> 懷疑鏈路的時候，用一個不共用程式碼的第二來源：
> `cat /sys/class/net/$IF/statistics/rx_packets`。

---

### 8.12.6 埠與服務偵察　→ `runsheet.md` `A3.4`

> ⚠️ **不要 `-T4`。** 這是 400 MHz MIPS、32 MiB RAM，而 `-T4` 的併發量足以讓
> `boa` 停止回應。
>
> 🔴 **掃描前後各確認一次 web 還活著，而那是對照組不是禮貌。**
> 一次把 `boa` 打掛的掃描，結果看起來會跟「埠都關著」一模一樣 ——
> 65,532 個 `closed`，而你會把它寫成發現。**兩次都 200，`closed` 才是裝置的答案
> 而不是你的。**

**這台已知的答案（2026-08-17）**：`80` / `52869`（`miniigd` UPnP SOAP）/
`52881`（`wscd` WPS）開，其餘 65,532 個 TCP 埠 closed。
`53` / `67` / `1900` UDP 有回應。**IoC 埠全部 closed。**

> 🔴 **服務的 banner 不等於它的 codebase。** 這台的 UPnP 送
> `Server: miniupnpd/1.4`，而 rootfs 裡**只有 `/bin/miniigd`、沒有 `mini_upnpd`** ——
> 那個 banner 字串就在 `miniigd` 自己的字串表裡。**只讀 banner 會查錯一整組 CVE。**
> 判定方法：`strings` 那支 binary，以及 `find` 整個 rootfs。

---

### 8.12.7 HTTP 那幾輪，用工具不要手打　→ `runsheet.md` `A3.5`

**為什麼是工具**：少帶 `submit-url` 的 POST 會讓 handler `strcpy("/status.htm")`
寫進唯讀段，照程式碼讀那會打掛 web server —— 然後**後面每一個端點都會回
「連不上」，看起來就跟「端點不存在」一模一樣**。一次打錯，57 個端點的普查
變成 57 個偽陰性。工具擋掉這件事，每 10–20 個請求重跑對照組，
端點清單從 `reports/ghidra-formtable-unit-2018.json` 讀。

> ⚠️ `endpoints` **預設 GET**。`--allow-post` 會真的執行 handler ——
> 前後各跑一次 §8.12.3。

> 🔴 **測繞過的時候，目標必須是真的被擋的頁面。**
> 2026-08-17 第一輪把十三種變形全打在 `/status.htm` 上，
> 而**它在豁免清單上、本來就回 200** —— 等於拿沒鎖的門測開鎖技巧。
> 這台真的被擋的：`/password.htm`、`/tcpiplan.htm`、`/upload.htm`（→ 302 `login.htm`）。
> 未認證可取的只有 7 個：`status` / `Connect_status` / `login` / `index` /
> `wan_status` / `countDownPage` / `countDownPageWizard`。

---

### 8.12.8 收尾與紀錄　→ `runsheet.md` `A4.1`

**這一節把「我跑過」變成「repo 裡有一筆可被質疑的紀錄」。跳過它，前面全部白做。**

**`--evidence` 有三個等級而不是兩個，而第三個是 2026-08-17 才加的**：
`dynamic`（在這台矽上跑出來的）、`static`（讀出來的）、
`emulated`（在模擬環境裡**執行**過，但不是矽）。
中間那個等級解決一個真實的困境：§8.11 的環境讓這台自己的 binary 對這台自己的
flash 真的跑起來了 —— 記成 `static` 低估了（有東西執行了），
記成 `dynamic` 就是**這個登記簿存在的目的要防的那種漂白**。
所以它有自己的符號，而且**永遠不會變成勾**。

**每一筆結果會戳上它當時所依據那段反證文字的逐項雜湊**，所以事後改反證條件會被抓到。
**這不是防篡改** —— 鑰匙在作者手上 —— 它是「改動出現在 diff 裡」和「不會」的差別。

然後往 [`BENCH-LOG.md`](BENCH-LOG.md) **追加**這一場：計畫（動手前寫的）、
紀錄卡、逐字節錄、燒掉了什麼、下一步。**只追加，不修改既有段落。**
**計畫要在動手之前 commit**，這樣「寫在前面」這件事可以被 `git diff` 證明 ——
一份事後才寫的成功條件證明不了任何東西。

**per-unit 識別碼（MAC、SSID、`config.dat` 內容、射頻校準）不進 repo** ——
跟 W02 把 PCB 條碼塗掉是同一條規則，而擁有者是
[`docs/disclosure.md`](docs/disclosure.md)。原始 transcript 留在 `$FWRE_WORK/dumps/`。

---

### 8.12.9 冷開機那一輪，一次上電餵三項　→ `runsheet.md` `A3.2`

**一次完整的上電同時交付 `P1-12`、`P9-1` 的動態半、以及一份帶時間戳的 bootlog。**
分三次開機做完全一樣的事，只是多燒兩次開機循環。

> 🔴 **2026-08-17 更正：這一節原本寫「兩個終端機，一邊擷取一邊輪詢」，而那量不到東西。**
> 兩個終端機各自的「我按下 Enter 的時間」不能相減，所以現在有一支
> `tools/coldboot-timing.sh`，它做四件手做不到的事：
>
> | 它做什麼 | 為什麼手做不到 |
> |---|---|
> | console 每一行蓋一個 `date +%s.%N` | picocom **沒有行內時間戳**，而 `ts` 不是每台機器都有 |
> | HTTP 輪詢帶 `-m 1` | 沒有它，一個卡住的 connect 會吞掉「伺服器起來」那一刻 |
> | **兩半用同一個時鐘** | 這是整節的關鍵，也是兩個終端機做不到的那一件 |
> | t=0 取 **console 第一行的時間戳** | 從腳本啟動算，量到的是**你的反應時間** |

**這一輪要從 log 裡撈三樣東西**，而第三樣在這台上的答案跟直覺相反：

| 撈什麼 | 為什麼 |
|---|---|
| 第一行 bootloader banner 的時間戳 | `P1-12` 的 t=0 |
| `boa: starting server pid=…, port 80` | **不是** t=1 —— 見下 |
| `Kernel command line: …` | `P9-1` 的動態半，而**這台印不出來**，見 §8.12.10 |

> 🔴 **`boa` 印出自己啟動之後，還有 6.26 秒不能服務。** 那段時間它在做
> `flash extr /web`，把 143 個檔案從 flash 解到 ramfs。
> **所以「console 上看到 boa 啟動」不等於「可以開始掃描」**，而這就是
> 「等 45 秒」那條規則的來歷。

> 🔴 **量到 38.76 s，預測寫的是「< 40 秒」，餘裕 1.24 秒 —— 而 38.76 是下界。**
> t=0 取的是 console 第一個字元，不是通電那一刻；通電到第一個字元那段沒有量。
> 反證條件寫的是「**明顯**超過 40 秒」，38.76 不是，所以判成立 ——
> **不可以因為餘裕太薄就事後改標準，那正是登記簿要防的事。**
> 但這一項的用途是當「服務沒回應」判定的基準線，**所以可用的形式是「等 45 秒」**，
> 不是「小於 40 秒成立」。這兩句話不衝突：一句是判定，一句是用法。

---

#### 為什麼 `A3.2` 多了第四小節，以及那一節的時鐘為什麼不是 console 第一行

這一節的標題從 W07 增補起就寫著「一次上電餵四項」並且聲稱關掉 `P2-11`，而它的
內文只交付三樣、從頭到尾沒有提過 `P2-11`。`coldboot-timing.sh` 自己的檔頭也只列
三件。**一節聲稱關掉的編號，可以在它自己的內文裡完全沒有程序**，而
`tools/check-runsheet.py` 的兩個方向都看不到那一種：它驗「標題聲稱的編號在登記簿
裡」與「已執行的列有節聲稱它」，兩個都在編號的層級，沒有一個在程序的層級。
2026-08-18 進站當天補寫成 `A3.2.4`，記在 `PROGRESS.md` 開放題 #71。

**時鐘的來源是一個 1 秒精度的問題。** 那條臂的到期條件是
`nowuptime - beforeuptime >= 601`，而 `nowuptime` 來自 `sysinfo()`，也就是**系統
uptime**——它從 kernel 起跑，不是從通電。console 第一行到 kernel 開始之間量到
6.50 秒（預測 6.9），所以拿 console 第一行當 t=0，視窗邊界會整整早 7 秒，而這一節
要驗的預測精度是 1 秒。**用 log 裡 `booting the kernel` 那一行的時間戳。**

**為什麼是掃過邊界而不是量兩個點。** 登記簿要的是三段：視窗內 200、第二個來源
302、視窗後 302。兩個點就滿足了那三段，而它答不出「它在第幾秒翻的」——**而
「它在 601 翻」正是整條主張。** 一個固定間隔的掃描會讓預測有機會差一秒，兩個點
不會。

**第二個來源位址是把「視窗關了」跟「伺服器掛了」分開的唯一東西。** 兩者在只看
第一個位址的紀錄上長得一模一樣：都是不再回 200。如果某一格兩個位址同時變成
連不上，那是 `boa` 掛了，而這一節就沒有結果。

🔴 **第一版把「登入」寫成一發帶憑證的 GET，而它量到的是一個自己造的假陰性。**
寫 `authipaddr` 的是**登入表單的 handler**，不是任何一個通過認證的請求：
HTTP Basic 走 `process_header_end` 的憑證比對，那條路徑從頭到尾不會經過
`form_formLogin`。於是「成功登入」的下一秒量到 302，而那看起來跟
「這條臂在這台從來不成立」完全一樣——那正是登記簿反證條件 (a) 的形狀，
差一個措辭就會被寫成本週最重的反駁。**改成 POST 登入端點之後，臂立刻成立。**

★ **這一節的結果反過來推翻了它所依據的那份 note。** `notes/auth-session-ip.md`
說視窗是系統 uptime、601 秒之後永久關閉；實測是 login+601，而且重新登入會重開。
兩個相差 706 秒的錨點都落在 login+601。**那不是量到一個數字，是把兩個互斥的
機制假設分開**，而分開它們的是第二個錨點的存在，不是第一次量測的精度。

### 8.12.10 `P9-1`：bootloader 能不能傳 kernel command line　→ `runsheet.md` `A1.3`

**先讀這一段再決定要不要花開機循環。靜態那一側已經答完了。**

`make loader-report` 解開 bootloader 第二階段之後，對 13 個 cmdline 形狀的字串
掃描（`cmdline` / `bootargs` / `bootcmd` / `console=` / `root=` / `init=` /
`mem=` / `rootfstype` / `setenv` / `printenv` / `env ` / `ethaddr` / `bootdelay`）
得到 **0 個命中**，而**同一次掃描找到 `?` 印的全部 17 個指令**
—— 找不到全部 17 個，工具就拒絕出報告，所以那個 0 是有對照組的 0。

**結論：這台的 bootloader 沒有環境變數機制，沒有地方放 kernel command line,
也沒有任何指令可以設定它。**`?` 列的 16 條指令（`DB DW EB EW CMP IPCONFIG
AUTOBURN LOADADDR J FLR FLW MDIOR MDIOW PHYR PHYW PORT1`）現在**對得上 binary
自己的字串表**，所以「`?` 有沒有漏印指令」這個疑慮也一起解掉。

> 🔴 **cmdline 也不在 flash 裡可改的地方。** 整顆 4 MiB 找不到
> `console=ttyS0` 明文；它在 `cr6c`（`0x060000`）的 **LZMA 壓縮酬載**裡，
> 而酬載前面那段是自解壓 stub（`0x060030` 起：`3c 10 80 5f` = `lui s0,0x805f`）。
> 所以 `FLR` 到 RAM 用 `EB` 戳一戳就改掉 —— **這條路不存在。**

> 🔴 **2026-08-17 更正：這一節原本寫「Linux 一定會印 `Kernel command line: …`」。
> 它不會 —— 那個字串根本不在這台的 kernel image 裡。**
> `A1.3` 把 `cr6c` 的 LZMA 解出來之後直接量：`Linux version` **在**、
> `swapper` **在**、`Kernel command line` **不在**。所以它永遠印不出來，
> 而 `coldboot-timing.sh` 為此報的那一行 `FAIL` 在這台上是預期的。
>
> **這件事比原本的寫法有價值**：「image 裡沒有那個字串」正是解釋
> 「console 為什麼沒印」的那個**獨立來源**，而原本的寫法會把一次正確的量測
> 讀成一次擷取失敗。腳本繼續報 `FAIL` 是對的 —— 它不該假設這台特殊。
>
> ⚠️ **也沒印 `Linux version`，但那是另一回事**：那個字串**在** image 裡，
> 只是沒印出來（早期 printk 在這個 build 上是關的）。
> **「字串不存在」和「存在但沒印」是兩件事**，混起來就少了一個來源。

**所以 `P9-1` 的三個獨立來源全部是靜態的，而登記簿為它宣告的
`exit_evidence` 就是 `static`** —— loader 的字串空間、kernel 的 `.rodata`、
以及裝置 console 的 `?`。三者不共用程式碼。

> 💡 **仍然存在的路徑，而它零 flash 寫入**：`AUTOBURN 0` → `LOADADDR` →
> TFTP 一份改過 cmdline 的 kernel 進 RAM → `J`。
> loader 的字串證實這條路存在（`Set TFTP Load Addr 0x%x`、`Jump to 0x%x`）。
> 成本是要能重壓一份 kernel，而那 38 個字元的 cmdline 字串沒有多餘空間放
> ` init=/bin/sh`，得先確認後面有沒有留白。**排 W07 之後。**

---

### 8.12.11 `P9-3`：救援路徑，而且不上傳任何東西　→ `runsheet.md` `A2.4`

**`P9-3` 凍結的反證條件只問「救援模式進不進得去」，沒有要求上傳。**
所以這一節到「loader 的網路堆疊活著」為止，**零 flash 寫入、零上傳**。

從 `make loader-report` 讀出來的流程（每一步都有對應的字串）：

| 步驟 | loader 會印 | 作用 |
|---|---|---|
| 關掉 autoburn | `AutoBurning=0` | **先做這一步。**收到檔案要不要燒進 flash 的開關 |
| 設 IP | ` Target Address=%d.%d.%d.%d` → `Now your Target IP is …` | 設板子的 IP 並起網路 |
| 設載入位址 | `Set TFTP Load Addr 0x%x` | 上傳的檔案落在 RAM 哪裡 |
| （客戶端上傳） | `**TFTP Client Upload, File Name: %s` → `**TFTP Client Upload File Size = %X Bytes at %X` | **不做** |
| （autoburn=1 才會） | `burn Addr =0x%x!…` → `Flash Write Successed!` | **不做** |

> 🔴 **必須先關 autoburn 再設 IP。** 順序反過來的話，網路一起來就有一個
> autoburn 狀態未知的 TFTP 伺服器在聽。這一步同時把「autoburn 預設是什麼」
> 印出來 —— 那本身是情報。工具強制這個順序，而且**它只送得出 `0`**。

> 🔴 **2026-08-17 兩處更正，而兩處都是「我寫的成功條件錯了」，不是裝置的問題。**
>
> **（一）指令的形式。** 這一節原本寫 `AUTOBURN: 0` 和 `IPCONFIG:10.1.1.1`
> —— **帶冒號的兩個都回 `Unknown command !`**。loader 的字串表把指令 token 和
> 說明行分開存，而 `?` 印出來的是說明行。**`?` 印的說明文字不是語法。**
> 這正是 `tools/check-runsheet.py` 的存在理由：在那之前，沒有任何東西
> 把作業單裡的命令當命令來讀。
>
> **（二）成功條件。** 原本寫「`ping` 有回應」加「回應的 MAC 是這台的」，
> **兩半都不成立**：
>
> | 我寫的 | 實際 | 為什麼 |
> |---|---|---|
> | `ping` 有回應 | **0 received, 100% loss** | loader 的堆疊只做 ARP + UDP/TFTP，**沒有義務實作 ICMP** |
> | 回應的 MAC 是這台的 | `56:0a:01:01:01:e8` | `0a 01 01 01` 就是 `10.1.1.1` —— **loader 從你給的 IP 合成一個 MAC** |
>
> **可用的判準是兩個不共用程式碼的來源**：`ip neigh` 是 `REACHABLE`，
> 加上 kernel 自己的 `rx_packets` 從 0 變 1。判定與逐項證據在
> [`test-ledger.md`](test-ledger.md) 的 `P9-3`。

> ⚠️ **計畫外的發現，列為開放題**：TFTP GET **不看檔名** ——
> 對一個不存在的檔名也吐 516 bytes 的 DATA（opcode 3），
> 而那 516 bytes 與 flash `0x060010` 起的 `cr6c` 酬載逐 byte 相同。

> ⚠️ 這一節結束後**拔電重開**，不要從設過 IP 的狀態直接 `J` 或繼續開機。

---

### 8.12.12 POST 掃描：哪些 handler 不准打　→ `runsheet.md` `A3.8`

**`P1-4` / `P3-13` 要求 POST，而 POST 會真的執行 handler。**
`reports/ghidra-sinks-unit-2018.json` 說這台的 57 個 handler 裡有
**23 個呼叫 `system()`、13 個 `execl()`、45 個 `strcpy()`**。

**盲掃 57 個 = 在全世界唯一一台上跑 36 個會 spawn process 的 handler。**
而參數全部缺席的 handler 仍然會把 accessor 的預設值寫進去。最壞的四種：

| handler | 打下去可能發生 |
|---|---|
| `formTcpipSetup` / `formWanTcpipSetup` / `formVlan` | **LAN 位址或 VLAN 被改 → 掃到一半失去這台**，而後面每個端點都會回「連不上」，看起來跟「端點不存在」一模一樣 —— 正是 `bench-probe` 當初為了 `submit-url` 而生的那個失效模式，換一件衣服 |
| `formPasswordSetup` | 管理密碼被改成空的或垃圾 → **CVE-2019-19823 的端到端鏈當場毀掉**，而那是這個專案最硬的一條證據 |
| `formUpload` / `formUploadConfig` | 韌體 / 設定上傳路徑。`boa` 裡有 `DownloadRFW` |
| `formOpMode` / `formOpMode1` / `formOpMode2` / `formWizard` | 運作模式變更，多半接重開機 |

**所以 `bench-probe endpoints --allow-post` 現在硬性拒絕這一類**，而且
`formSysCmd` **從迴圈裡拿出來單獨打**（它是 W05 DoD 第 5 項那一格，見 §8.12.13）。

> 🔴 **而且要先寫下來：這一輪一定會改設定。**
> IoC 預檢凍結的成功條件是「COMPCS vs COMPDS 差異 = 4 / 343」。
> POST 掃完之後那個數字**會變**，而且應該變。所以：
>
> 1. 掃描**前後各抓一份 64 KiB 快照**（§8.12.3），
> 2. 掃完之後把新的差異**逐欄位列出來並歸因到哪一輪**，
> 3. **新的數字成為新基準**，舊的 4/343 連同「是這一場的哪一步造成的」一起留在紀錄裡。
>
> 這比守住 4/343 強：守住只證明沒動到，**歸因證明了動了什麼、被誰動的**。
> 反過來，沒有前後快照就掃，等於把基準洗掉而且說不出被誰洗的。

**2026-08-17 這一輪的兩個結果，而它們決定了 W06 的形狀：**

> 🔴 **一、掃描跑不完，而那個中止是結果不是失敗。** 不帶任何參數的未認證 POST
> 佔住這台唯一的 web server 4.7–9.7 秒（`boa` 在這台是**單一 process**），
> 約 45 個連續請求之後它徹底停止服務，**兩次都是**。
> `ping` 全程正常、console 一行訊息都沒有、20 分鐘後 `boa` 仍然沒回來 ——
> `rcS` 是一次性啟動它的，不是 respawn。斷電重開即復原。
>
> **這與 `P4-1` 不是同一條**：`P4-1` 是**不帶** `submit-url`、往唯讀段 `strcpy`；
> 這一條**帶**了 `submit-url`，是一個完全合法的請求。
> **分類與影響評估留給 W06/W07**，`docs/disclosure.md` 的 `D-9` 記了一筆。

> 🔴 **二、`COMPDS` 動了，而它是出廠預設區。** 那一輪把出廠預設區的 23 個欄位
> 全部覆寫成 `COMPCS` 的值，兩區現在 343 個共同欄位完全相同。
> **所以：一次未認證的設定寫入，同時把出廠預設區覆蓋掉。**
> 在這個 build 上，「恢復原廠設定」還原的是**最後被寫進去的那一份** ——
> **reset 按鈕不是復原路徑**，唯一的復原是從裝置外的副本重寫（§8.9）。
> 而 `H601` UNCHANGED 是那次歸因裡最重要的一行：每一次歸因都先看它。

### 8.12.13 這一段會踩到的　→ `runsheet.md` `A4.2`

| 症狀 | 原因 |
|---|---|
| `Cannot find device "eth1"` 而 `ping` 卻通 | 網路卡起在 Windows 側，你繞過去了。**看路由表有沒有 `via`** |
| 抓不到任何封包 | 先看 `/sys/class/net/$IF/statistics/rx_packets`。`RX: 0` = 鏈路沒在送東西給你 |
| `Speed: Unknown!` `Duplex: Half` | 協商沒完成，或對端沒起來（例如板子還停在 bootloader） |
| 所有端點都「不存在」 | 你可能把 `boa` 打掛了。跑對照組 `curl http://10.1.1.1/` |
| 打錯 `FLW` 參數 | **不要再送任何指令。** 拍下整個畫面再說 |
| `DB` 印出來跟上一次一樣 | `FLR` 沒生效（多半是 `Y` 被下一個指令吃掉）。那是 RAM 舊值 |
| `rtcase check` 說 artefact 不存在 | 證據連結要指到 **repo 裡**存在的檔；`~/fwre-work/dumps/` 不在 repo 裡 |

---

### 8.12.14 把 USB 裝置交給 WSL　→ `runsheet.md` `A2.1`

**這一步為什麼是獨立的一節，而不是網段那一節的開頭：兩張卡的失效模式不一樣，
而其中一個會安靜地毀掉整場量測。**

**序列轉接器（`10c4:ea60`）沒交過去，症狀是誠實的**：沒有 `/dev/ttyUSB0`，
每一條命令都立刻失敗。

**網路卡（`0bda:8153`）沒交過去，症狀是說謊的**：它留在 Windows 側，
**Windows 會從這台路由器拿到 DHCP 位址**，於是 WSL 的封包被**路由**過去 ——
`ping` 會通、`curl` 會回 200，而你量的是那條路徑不是裝置。
2026-08-17 真的發生過（儀器 bug 21），詳細後果在 §8.12.4。

> ⚠️ **`usbipd attach` 綁在 WSL 這個 VM 上，VM 一停裝置就退回 Windows。**
> 這是一個「會在中途壞掉的相依」，而它決定了場次的排法：
> §8.12.10 / 8.12.11 / 8.12.9 一個都不需要網路卡，所以 console 那半場
> 整段排在網段之前 —— 少一個中途會掉的東西。

---

### 8.12.15 `GET /config.dat`：一條四層都指得出來的證據鏈　→ `runsheet.md` `A3.6`

**這是這個專案最值得單獨講的一個結果，而它只有三行命令。**
一個**未認證**的 `GET /config.dat` 拿回 7,490 bytes，而那 7,490 bytes 的 SHA-256
**跟用 bootloader 從 SPI flash `0xC000` 讀出來的那 7,490 bytes 完全相同**。

**為什麼它拿得到：`/config.dat` 的路徑裡沒有 `.htm` 也沒有 `.asp`，
所以授權閘門根本不跑。** 而 `boa` 在**啟動時就建立**這個檔案 ——
`lseek(3, 49152)` → `read(…, 7490)` → `open("/web/config.dat", O_RDWR|O_CREAT|O_TRUNC)`，
三行 `strace` 來自 §8.11 的模擬環境。**所以這條鏈比原本假設的短一步**：
不需要任何人先 POST 任何東西。

> ★ **而第二環順手關掉一個從 W02 就開著的缺口。**
> W02 說「沒有第二個獨立儀器讀過這顆 flash」—— 每一個 byte 都是經 bootloader 的
> `FLR` 來的，所以一個系統性錯誤的 `FLR` 會是隱形的。
>
> 這一節裡，`boa` 經 **kernel 的 MTD 驅動**、走**乙太網路**讀了同一塊區域；
> W02 經 **bootloader 的 SPI 常式**、走 **UART**。
> **兩條不共用任何程式碼的路徑，同一組 bytes。**
>
> 那是**佐證（corroboration）**，不是**重複（repeatability）** ——
> 而那一欄從 2026-08-16 起一直是空的。**範圍是 `0xC000`–`0xD142`，不是整顆晶片。**

> ⚠️ **這是 CVE-2019-19822（未認證設定外洩）加 CVE-2019-19823（明文儲存），
> 兩個都是 2019 年公開的。** 這一節重現的是已公開的東西，不是新發現 ——
> **這個專案自己的部分是那條佐證鏈，不是那個漏洞。**

---

### 8.12.16 憑證與 session：為什麼要兩個來源位址　→ `runsheet.md` `A3.7`

**密碼不是猜的，是從你自己的 flash 解出來的**，所以登入成功是
**在自己的機器上把 CVE-2019-19823 端到端走完**，而不是對別人的裝置做事。

**`Set-Cookie` 一行都不會出現，而那是這一測最重要的輸出。**
這個 build **沒有 session**：授權是每一個請求各自的 HTTP Basic。
不是 2015 版的 `AUTHG_IP_ADDR`、不是 2020 版的五格表、
**也不是反組譯指到的那個全域** —— 三個靜態猜測全部落空，而一次量測就定案。

**為什麼要第二個來源位址（`10.1.1.101`）：因為「沒有 session」不能用
「沒看到 cookie」證明。** 一個以來源 IP 記狀態的實作也不會發 cookie。
所以判準是：`.100` 帶憑證成功之後，**`.100` 不帶憑證仍然被擋**，
而 `.101` 帶憑證也成功 —— 兩個位址、四種組合，才排除掉 IP 綁定那個模型。
**這一測不必再讀一行組語。**

> ⚠️ **「沒有 session」不等於「沒有 CSRF」。** 瀏覽器會自動重送快取的 Basic 憑證，
> 所以跨站面是靠另一個機制活著的。**這是推論，不是這一測量到的東西。**

> ⚠️ **帳號鎖定那一項要真的跑完五十次，不要跑三次就下結論。**
> 「前三次沒鎖」和「沒有鎖定機制」是兩個不同的主張，而一個門檻在第 5 次或第 10 次
> 的實作會讓前者為真、後者為假。

---

### 8.12.17 把設定區寫回去：為什麼它需要一支工具　→ `runsheet.md` `A2.6`

**2026-08-17 那一輪未認證 POST 把 `COMPDS`（出廠預設區）覆寫成 `COMPCS` 了**，
而那不是計畫中的副作用 —— 它是 `D-10` 那個發現本身。資料沒有丟：
`config-region-20260817-1102-pre.bin` 與 8/16 的完整 dump 前 64 KiB 逐 byte 相同，
**兩份獨立的副本**。要做的只是把它寫回去。

**「只是」兩個字撐不住三件事。**

**第一，這是 16 KiB，不是 8 個 byte。** `A2.5` 的演練用 `EB` 手打八個 byte 進 RAM
再 `FLW`。同樣的做法乘以兩千倍就不是同一件事了：`EB` 一行吃幾個 byte
**從來沒有人量過**（`runsheet` 到那天為止只知道「多 byte 形式可以」），
而猜錯的代價不是慢，是**一行只進第一個 byte、其餘被丟掉**，
然後你把一份殘缺的 16 KiB 燒進設定區。

**第二，`console-dump.py` 刻意送不出 `FLW`。** 那不是疏漏，那是它的保證：
它的 docstring 說它只讀，而它的守衛套件 `grep` 那份保證。
把寫入路徑加進去，等於毀掉「這支檔案不可能寫壞你的機器」這個
**一個 `grep` 就能驗證**的性質。所以寫入是另一支工具，
而它的白名單只有兩段：演練用的 `0x3F0000`，和它存在的理由 `0x008000`–`0x010000`。
**bootloader 與 `H601` 由建構上就搆不到，沒有任何旗標放得寬。**

**第三，順序有方向性。** `/bin/startup.sh` 在 `flash test-csconf` 失敗時
會用 `0x8000` 的 `COMPDS` 蓋回 `0xC000` —— **裝置自己修得回 `COMPCS`，
反過來不成立**。所以先寫 `COMPDS` 這一邊是對的：寫壞了還有裝置自己的安全網，
寫壞另一邊就沒有了。

> 🔴 **`A2.5` 與 `A2.6` 不能互相取代，而混淆它們是最容易犯的錯。**
> `A2.5` 演練的是**這台裝置的 `FLW` 語意**（讀-改-抹-寫回，且保留磁區其餘內容）；
> `A2.6.2` 演練的是**這支程式送出去的 `FLW`**。
> 兩者都在 `0x3F0000` 上做，但問的是不同的問題 ——
> 一個是「裝置會怎麼做」，一個是「我的程式有沒有把參數擺反」。
> `FLW` 的參數順序**跟 `FLR` 相反**，而那是這台上最容易一次做錯的一件事。

> ⚠️ **驗證的判據是分段的，不是一個 `cmp`。** 這一節只寫 `0x8000`–`0xC000`，
> 所以 `0xC000` 之後**本來就會**跟 8/16 的快照不同（那是 8/17 POST 輪的現況）。
> 一個整段 `cmp` 會報出差異，而讀的人很容易把「預期中的不同」讀成「還原失敗」。
> **前兩段必須相同、第三段必須不同**，三個都要對才叫還原成功。

> ★ **還原之後，`P9-9`（reset 按鈕到底還原什麼）在 W07 才重新有意義。**
> 8/17 把兩區弄成一模一樣，於是「reset 用 `COMPDS` 蓋 `COMPCS`」這個預測
> 無法判別 —— 蓋不蓋結果都一樣。**這一節把判別力還回去。**

---

### 8.12.18 未認證命令注入：為什麼順序是 ICMP → docroot → flash　→ `runsheet.md` `A3.9`

**這個漏洞是盲注，而那一件事決定了整節的排法。**
`formSysCmd` 的格式字串在 `/bin/boa` 裡是 `%s 2>&1 > %s`：你送的命令在前，
後面接著把 stdout 導去 `/tmp/syscmd.log`。**所以 `system()` 的輸出不會進 HTTP 回應**，
而「看到 `uid=0(root)` 就是成功」這種驗證方式在這台上永遠不會發生。
原版計畫要的東西是對的，只是它找錯地方。

**三個 oracle，按副作用由小到大排，而那個順序本身就是方法：**

| oracle | 寫什麼 | 它單獨能證明什麼 |
|---|---|---|
| ICMP | **什麼都不寫** | 命令執行了 |
| docroot 回寫 | `/var/web`，而 `/var` 是 ramfs | 命令的**輸出**取得回來 |
| flash 差異（§8.12.19） | 非揮發性儲存 | 命令改了矽晶片上的 byte |

**反過來做的代價很具體**：先用會寫東西的 oracle，第一發要是失敗了，
你分不出「注入不成立」和「注入成立但 oracle 看不到」——
而那兩者的後續動作完全相反。**先用零副作用的把注入釘死，
之後每一個看不到結果的情況就都是 oracle 的問題。**

**`;#` 那個習慣用法不是裝飾。** 因為 handler 自己的重導向接在後面，
而 `sh` 裡最後一個 stdout 重導向贏，`cat x > /var/web/f.txt` 會**建立那個檔案然後留空**。
**空檔和「參數被過濾掉」看起來一模一樣**，而 W05 的 oracle 那份筆記
就是在這一格上第一版寫錯的。

> 🔴 **判據是「來源 `10.1.1.1` 的 ICMP type 8」，不是「有 ICMP」。**
> 對照組裡路由器送的是 type 0（reply）。方向與型別一起看，
> 才分得出「它回了我的 ping」和「它替我跑了一個 ping」。

> ★ **不帶憑證那一發成立 = `docs/disclosure.md` 的 `D-6` 可以動了。**
> CVE-2024-51228 在 NVD 上是 `PR:H`（需要高權限），而這個 build 的閘門
> 根本不跑 `/boafrm/formSysCmd` 這個 URI。**漏洞本身 2024-11-27 就公開了，
> 沒有任何禁運**；有爭議的只是那個分數，而一個請求就能定案。
> **接著要補上「帶憑證那一發」** —— 兩發行為相同才排除得掉
> 「其實我不小心帶了什麼」。

> ⚠️ **三個標的的揭露狀態不同，所以 `runsheet` 對它們的寫法不同。**
> `formWsc`（CVE-2025-3987 / 4462 / 6299）已公開，完整命令寫出來；
> **`formRoute` / `subnet` 是 `D-1`，這個專案自己找到、沒有 CVE、還沒通報任何人**，
> 所以 `runsheet` 只給形狀不給可貼上的請求。
> **指出 handler 與參數名是發現，給一個能複製的請求是重現** ——
> 而重現要跟著揭露狀態走。這是那條規則第一次真的咬到自己。

> ★ **`P5-5`（`cat /proc/cpuinfo`）看起來像順手，實際上它是 W02 開放 #6 的終點。**
> SoC 是 RTL8196E，核心是 RLX4181 還是 RLX5281 直接影響 W01 讀出來的「MIPS-I」，
> 而**這台沒有 shell**，所以那一格從 2026-08-16 一直開著。
> 命令注入成立的第一個副產品，就是一個從來問不出口的問題突然只要一行。

---

### 8.12.19 第 ⑤ 環：為什麼要指著 flash 上的 byte　→ `runsheet.md` `A3.10`

**別人證明命令執行了，靠的是 HTTP 回應或一個 ICMP 封包。
這一節是注入前後各讀一次 SPI flash 的設定區，然後指著被改掉的那幾個 byte
說「這是那個 HTTP 請求做的」——而且能把它翻譯成一個有名字的 MIB 欄位。**

**能這樣做的唯一原因，是 W02 把 flash 讀出來了、W04-2 學會了解碼它。**
硬體那一週不是一個 checkbox，它是這條證據鏈的最後一環。

**這一發刻意不帶任何分隔符。** `localPin=13572468` 走的是
`sprintf(buf[100], "flash set HW_WLAN0_WSC_PIN %s", localPin); system(buf)`
的**正常**路徑。注入那一半 §8.12.18 已經證明了；
**這一節要證明的是那條路真的通到 flash**，而混進一個分隔符就等於同時動兩個變數。

**它一次證明五件事，而每一件都指得回一份可重新產生的產物**：命令真的執行了
（靠持久儲存被改了，不是靠回應）、`system()` 收到的就是我送的字串（寫進去的值
就是我送的值）、W04 的根因讀對了（那一行確實是那個格式字串）、W04-2 的解碼器
是對的（它把 flash 的變化翻譯成一個有名字的欄位）、W02 的 dump 路徑仍然有效
（同一條 `FLR`+`DB`，第三次用途）。

> 🔴 **每一次歸因都先看 `H601`（`0x6000`–`0x8000`）那一行。**
> 它必須是 `UNCHANGED`。那是這一台的 MAC 與射頻校準，全世界只有這一份，
> 而出廠重置不還原它。

> ⚠️ **`COMPDS` 大概也會跟著動**，因為 `D-10`：這個 build 上一次未認證的設定寫入
> 會**同時**覆蓋出廠預設區。那不是這一節的失誤，是那個發現本身 ——
> 但它代表 `A2.6` 要再跑一次，而這次可以順便回答一個還沒人問的問題：
> **是每一次 POST 都覆蓋 `COMPDS`，還是只有某些 handler？**

> ★ **把值改回去是這個實驗完整的一部分**，而且它順便證明這個注入是
> **可重複、可控、可逆**的 —— 不是一次僥倖。原值要從 `-pre.bin` 解出來，
> 不要用記憶裡的：記憶裡的那個值，和你希望它是的那個值，是同一個東西。

---

### 8.12.20 未認證改密碼：為什麼它排在倒數第二　→ `runsheet.md` `A3.11`

**排這一節的位置靠的不是危險程度，是依賴關係。**
`A3.6` + `A3.7` 那條鏈的內容是「從自己 flash 解出來的密碼可以登入」——
CVE-2019-19822 → 19823 端到端，這個專案最硬的一條證據。
**這一節會把那個密碼換掉。** 順序反了就不是「順序不好」，是把證據毀掉。

**兩項合起來才是一個發現，分開各自都不是。**
`P10-4`（把密碼設成空字串之後整台不再要求認證）的分支 `0x0040bd18`
W04-2 已經靜態讀出來了 —— **分支存不存在是靜態的事**。
真正的問題是**有沒有一條未認證的路可以把它設成空**，而那是 `P10-3`。
`docs/disclosure.md` 的 `D-4` 寫得很直接：**可達性比那個分支重要；
如果沒有未認證的路徑能把它設成空，這就是一個奇觀而不是一個漏洞。**

> ⚠️ **參數名要從這台自己的 `/web` bundle 讀出來，不要從別的機型抄。**
> 拿錯欄位名的結果是「沒反應」，而那跟「被閘門擋下來」的輸出完全一樣 ——
> 於是你會把一個打錯字記成 `P10-3` 被反證。

> 🔴 **還原之後要看兩行，不是一行。** 只驗「舊憑證可以登入」的話，
> 「密碼還原了」和「這台已經不檢查密碼了」會給出一模一樣的輸出。
> 必須同時確認**不帶憑證仍然被擋**。

---

### 8.12.21 會把 `boa` 弄掉的那一梯次　→ `runsheet.md` `A3.12`

**`rcS` 起 `boa` 一次，沒有任何東西會重起它。** 2026-08-17 量過兩次：
四十五個左右的畸形 POST 之後 `boa` 就不再回應，二十分鐘後仍然不在，
`ping` 照樣通，console 一行都不印。**復原手段只有斷電重開，加 45 秒。**
所以這一梯次排在第 3 站最後，而且每一項之後都要探活 ——
**弄掛之後，後面每一項的結果都會變成「連不上」，那跟「端點不存在」長得一模一樣。**

**`P4-1` 跟 `D-9` 是兩件事，不要混講。** `D-9` 是**帶** `submit-url` 的
合法 POST 佔住單行程 server 四到十秒；`P4-1` 是**不帶**，
handler 拿到 `""` 字面量的位址然後 `strcpy` 進去，而那在唯讀段。
**同一個 handler，兩種完全不同的失效，其中一個是合法請求。**

**`P4-3` / `P4-4` 留在 W06 而 `P4-5` 之後全部移到 W07，理由是 oracle 存不存在。**
`P4-3` 有一個事先寫下的、具體的、可觀察的預測：`lastUrl[100]` 之後緊接著
`needReboot` 與 `run_init_script_flag`，所以溢位先改到的是**旗標**而不是返回位址
—— **觀察點是這台會不會自己重開機**，一個請求一次，不需要任何除錯器。
`P4-5` 以後那些要的是崩潰**加上 `epc` 可控**，而這台沒有 shell、沒有 gdbserver，
**`epc` 的 oracle 目前並不存在**。先做的應該是把那個 oracle 建起來，
而那是一件獨立的事。

> 🔴 **`P2-6`（協定層畸形）排在整節最後**，因為它最可能弄掛 server。

---

### 8.12.22 三個請求，而它們排在第 3 站最前面　→ `runsheet.md` `A3.13`

**為什麼是這一節開場，而不是埠掃描。**

第 3 站原本的順序是偵察在前、寫入在後，而 `A3.13` 比偵察更前面，理由不是它更
重要，是**它的成本是零而它的結論可能推翻一整條線**。三個 GET，不寫任何東西，
不用斷電，在一台完全沒有被這一場動過的機器上跑。

而它要驗的東西有一個性質，是這個專案到目前為止沒有遇過的：**它依賴一塊沒有人
寫過的堆疊記憶體裡剛好是什麼。** 模擬環境上那塊是零，理由很可能是結構性的
——`process_header_end` 是請求路徑上最深的框架，而 Linux 給的是清零的堆疊頁——
但那是一個論證，不是一次量測。**在裝置上執行過之前，`D-15` 不會寄給任何人。**

**為什麼四個請求而不是一個。**

一個「不帶密碼也進得去」的成功，在這台上有**兩個**互相獨立的解釋，而它們是
不同的缺陷：

| | 機制 | 分支 |
|---|---|---|
| `D-4` | 儲存的密碼是空的，所以比對被整個跳過 | `0x0040bd18` |
| `D-15` | 儲存的密碼是好的，比對有跑，但它比對的是一塊沒人寫過的緩衝區 | `0x0040bd48` |

分辨它們的是 `wrongpw` 那一列：**`D-4` 之下錯密碼也會過，`D-15` 之下錯密碼會被
擋。** 所以那一列不是湊數的對照組，它是唯一能把兩個缺陷分開的觀測。

如果 `A3.7` 的 `wrongpw` 回 `200`，代表這台的密碼在某個時間點被設成空的（
`A3.11.2` 就會做這件事），那 `A3.13` 量到的東西沒有意義，要先把密碼設回非空
再重跑。**這是本檔唯一一個「前一節的副作用會讓後一節的結果失效」的地方**，
而它之所以不會被順序解決，是因為兩節之間隔著整個第 3 站。

**為什麼請求本體不在 runsheet 裡。**

`D-15` 尚未通報，而且它在**公開映像上也成立** —— 那跟這個專案其他的發現不一樣，
其他的都綁在一台沒有人下載得到的 build 上。`docs/disclosure.md` 的規則說
reproduction 跟著揭露狀態走，所以請求在 repo 外面，runsheet 指過去。

**而這條規則在 `A3.11.2` 上沒有被遵守**，那是一個治理缺陷而不是筆誤：沒有任何
工具同時讀 `docs/disclosure.md` 和 `runsheet.md`，所以一個宣稱和一個指令可以
無限期地互相矛盾。記在 `docs/disclosure.md § A governance defect`，`A3.13` 是
第一節照新做法寫的。

**`Host` 那一半為什麼要打一發預期會失敗的。**

`A3.13.2` 的最後一發送一個帶 HTML 標記的 `Host`，而**預期是它被編碼**。
模擬環境上兩個 sink 都編碼了 —— `Location` 走 URL-encode、HTML body 走實體 ——
所以那一發預期不會產生 XSS。

打它的理由是：`D-14` 目前被評為「low，而且明確不是 XSS」，而那個評級**完全建立
在編碼有做這件事上**。一個只驗證自己預期成立的那半邊的測試，量到的是自己的
預期。如果實機上沒有編碼，`D-14` 就從 open redirect 變成未認證的反射型 XSS，
而那是完全不同的一列。


### 8.12.23 分派表為什麼需要第二個來源　→ `runsheet.md` `A1.5`

**因為到 2026-08-18 為止它只有一個,而這個 repo 的規矩不允許。**

「攻擊面」這個詞在這份專案裡的意思,最後都會化約成 `root_form[]` 有哪些條目。
每一份端點清單、每一次「57 個裡有幾個」、`bughunt.md` 的孤島那一節,全部站在
`reports/ghidra-formtable-*.json` 上,而那份檔案的產生者只有一個。**這不是可以用
`readelf` 補的**:這些 binary 是 `sstrip` 過的,一個 section header 都沒有,
`readelf -S` 回的是空的。所以「不從單一工具下結論」這條規則,在最關鍵的那一張表上
從來沒有被滿足過。

`formtable-scan.py` 不讀指令,只讀資料:program header 之後,在可寫段裡找連續的
`(指向字串的指標, 指向程式碼的指標)` 對。它找到的是**形狀**,不是意義 ——
`asp_page_variables` 是同一種形狀,它也會找到,而那件事本身是關於這支 binary 的
一個事實,不是雜訊。

**它可能錯在哪裡,而這句話寫在跑它之前。** 一張中間插了第三個 word 的表,在
stride 8 之下不會被認出來;一串剛好相鄰的無關字串,理論上可以湊出一個 run。
所以 `--expect` 存在:每一個 build 都必須找到 `formLogin`,找不到就 exit 2。
**一個因為 stride 猜錯、或 image base 算錯而回報「乾淨的空答案」的掃描器,
跟一支真的沒有分派表的 binary 長得一模一樣。** 這個 repo 出過兩次這種東西:
`BoaGate` 在一個手讀出 34 個缺陷的 build 上回報 0,以及一個追蹤器跨版本從 86 掉到 0。

**六個 build 的差集,以及它為什麼比數字重要。** 這一台的 57 個是 N300RT V2.1.6
那 61 個的嚴格子集 —— `P8-21` 問「六個產品是不是同一顆」,而「子集」是比「不同」
強得多的答案:它說那是同一份程式碼加一個功能差集。而 `formSysCmd` 在 N150RT
V3.4.0 裡不在了、在 19 個月更早的 N300RT V3.4.0 裡還在,那說明廠商的移除是**逐產品**
的。**一句「2020 修掉了」在這裡是錯的,而只有六個 build 排在一起才看得出來。**

**方法只在一個 build 上被驗證過,而那是這一節最該被追問的地方。** `--compare` 在
`unit-2018` 上與 Ghidra 逐項相同,另外五個沒有對照可比。唯一的間接證據是子集關係
本身:一個會截斷表的掃描器會產生散落的缺項,不是一個乾淨的子集。**這不是證明。**

---

### 8.12.24 為什麼輸入清單要用閘門自己的輸出　→ `runsheet.md` `A1.6`

**因為「想得到的輸入」跟「這支 binary 真的會讀的參數」是兩件事,而前者永遠比較短。**

W07 計畫對這一格的要求只有一句:*一個兩百行的迴圈就夠了,不准寫框架*。那句話是對的,
而它容易被誤讀成「隨便打打就好」。真正讓這一輪值錢的不是變異的巧妙,是**輸入集合是
算出來的**:端點是還原出來的 57 個,參數名是 `BoaGate` 在 `reports/ghidra-gate-*.json`
裡逐一指認的,長度階梯裡的 100 與 260 不是圓整數字,而是兩份既有量測 ——
W04 在 V2.1.2 上量到的 `lastUrl[100]`,以及閘門對 `form_formFilter` 的 `ip6addr`
報的 `sp-258`。

**四個維度裡最重要的是 `absent`,而它是這一週才長出來的。**
長度階梯永遠找不到「參數缺席」這一類,因為它送的東西**太長而不是不存在**。
2026-08-18 量到的五個 handler 全部是缺席才死;其中 `formSchedule` 帶著一個
格式完全正確的 `submit-url` 也照死,因為它讀的參數不叫那個名字。

**`ladder` 只跑堆疊那 22 個 finding,而那是刻意的取樣。**
返回位址跟緩衝區在同一個框架裡,所以長度階梯問的是堆疊問題;把它跑滿 134 個
finding 要多花一小時的重啟,去對其中 112 個問錯的問題。取樣的界線寫在報告的
`ladder_population` 欄位裡,不是寫在這裡就算數。

**正對照與負對照,以及為什麼負的那個承重。**
`P4-9` 凍結的反證條件是「跑滿一輪零崩潰,而同一輪的正對照也沒被標記為死亡 →
harness 的存活偵測壞了」。它原本點名「`P4-3` 的已知崩潰」,而 `P4-3` 在這台是
`refuted` —— `formNtp` 把 `submit-url` 回顯進 `Location`,800 bytes 回 799,
任何長度都不崩潰。**那個對照不存在**,於是反證條件的第二個子句恆為真,整條退化成
「零崩潰就等於 harness 壞了」,而那會把一個正確的否定結果讀成儀器故障。
2026-08-18 開火之前換成 `formSchedule`,凍結雜湊在同一個 commit 裡改。

---

### 8.12.25 死掉之後才開始的那一段　→ `runsheet.md` `A1.7`

**`died_under_emulation` 不是發現。** 它是一份長度為一的候選清單,而 W06 在實機上
量到的 `D-11`（一個未認證的請求讓 web server 不再回來）恰好也說不出是哪一個。
兩個「說不出」放在一起不會變成一個答案。

**為什麼要 gdbstub,而不是讀 log。** `boa` 自己裝了 SIGSEGV handler ——
log 上那行 `caught SIGSEGV, dumping core in /tmp` 就是它 —— 然後 abort。
所以訊號永遠到不了 qemu 的預設處理,**位址一次都不會被印出來**。gdb 先看到訊號,
`nopass` 讓它到不了 `boa` 的 handler,而暫存器還是故障那一刻的。

**兩個坑,兩次都各花掉一場,而它們不是同一類的坑。**
第一個是**知識**:`boa` 會 daemonize,gdb 跟的是馬上結束的父行程,整場以
「exited normally」加一份空暫存器收尾 —— 而 `-d` 這個旗標就寫在 binary 自報的
usage 裡,只是沒有人讀過。第二個是**設計**:帶 `--alignfix` 的時候 firmware 每寫
一次設定就吃掉幾十個 SIGBUS,那是設計如此,一個看到 SIGBUS 就停的 gdb 走不到要
定性的那個 fault。**第一個是查得到的,第二個只有跑過才知道。**

**位址要被分類,不然它只是一個十六進位數字。**
`SIGSEGV` 與「`SIGSEGV`,而且寫入的目標在一個 `R-X` 的 PT_LOAD 裡」是兩個不同的
發現,只有第二個解釋得了任何事。而**這個差別在實機上也成立**:核心會替使用者空間
補未對齊存取,但**不會**替它補權限錯誤,所以這一類的死亡是少數幾個可以從模擬直接
外推到矽上的 —— 而那句話仍然要在矽上驗一次,那是 `A3.23`。

**這一節的第三個產出是超時本身。** 一個不會 fault 的案例會讓 gdb 停在 `continue`
裡不回來,所以「超時 = 沒有 fault」是判準而不是例外。第一版把它寫成例外,結果第一個
對照組（一個**因為它會活著才被選中**的 handler）燒掉三分鐘之後把整輪拖掉,
已經跑完的五個案例一起丟掉。**一個對照組貴到會被跳過,就等於沒有對照組。**

**第四個產出是 2026-08-18 才學到的,而它比前三個都貴:對照組本身是逐 build 的。**
把這一節搬到 `v2.1.2` 上跑的時候,`unit-2018` 用了一整週的兩個對照組同時失效,
而且失效的方式不一樣。`formNtp:` 直接 SIGSEGV —— 它在那個 build 上就是「參數缺席
就死」的七個之一,而不是五個。`formWsc:localPin=1234` 更糟:它**沒有崩潰,而是
讓整個 guest 重開機**。一個會重開機的案例在報表上長得像「no signal」,也就是長得
像一個合格的對照組。
**在一個 build 上量出來的對照組,不是另一個 build 上的對照組**,而這句話跟這一節
本來就在講的那件事（一個測試繼承產生它的那份涵蓋率）是同一句話,只是往上一層。

**第五個產出是這個 repo 的環境安全前提被推翻了。** 那個「重開機」不是比喻:
guest 走到 `system("reboot -f")`,`busybox` 的 `reboot -f` 是一個裸的 `reboot(2)`,
`qemu-user` 把它交給宿主核心,而這整套工具是用 root 跑的 —— **`chroot` 不是隔離,
中間沒有任何 namespace。**宿主被關掉三次,而每一次看起來都像工具卡住:輸出斷在一半、
報表沒寫出來、事後 `/tmp` 是空的。**會說明發生什麼事的那個東西,剛好就是被關掉的
那一個。** 現在所有 guest 都經過同一個函式起動,而那個函式帶 `unshare --pid --fork`;
在 PID namespace 裡,`reboot(2)` 的語意就是這個 namespace 的 init 收到訊號,
也就是它在裝置上本來的語意。

> **一個模擬環境的失敗模式,不會只停在模擬環境裡。**

---

### 8.12.26 別的家族的路徑,以及三個對照為什麼是這一節唯一有價值的部分　→ `runsheet.md` `A1.8`

**五列不同編號的測試在問同一句話**:`root_form[]` 是不是唯一的 dispatch 來源。
`cstecgi.cgi`、`download.cgi`、`/cgi-bin/*`、`/goform/*` 都是別的 TOTOLINK 家族
才有的東西,而它們的反證條件逐字相同 —— 任何一個有回應,附錄 A 的完整性宣稱就不成立。

**而「有回應」這四個字是這一節唯一困難的地方。**
第一次跑的時候,`/cgi-bin/` 與 `/goform/` 底下每一個路徑都回 `400`,那看起來像
「有東西在那裡」。直到一個**保證沒有人實作得出來**的名字也回 `400` ——
`400` 是「POST 到一個不是 CGI 的路徑」的通用答案,不是端點存在的證據。

**更難看的是 GET 那半邊,而它是這支工具自己的缺陷。**
第一版的 GET 對每一個路徑都回 `200` 與 2,895 bytes,包含
`/zzqq-not-real.htm` —— 一個因為不可能存在才被選中的名字。原因是
urllib 預設會跟隨轉址,而這台對任何沒有豁免的路徑回 `302 → home.htm`,
**所以每一發量到的都是閘門的轉址,回報的是首頁的長度**。
一個會跟隨轉址的存在性探測,分不出「這個路徑存在」與「這個路徑被轉去一個存在的
地方」。

> **是對照組抓到的,不是結果抓到的。** 十六個字典項目互相一致什麼都不代表;
> 一個不可能存在的名字跟它們一致,代表全部。

---

### 8.12.27 設定區差分:為什麼它到這一週才是一個桌面動作　→ `runsheet.md` `A1.9`

`P8-23` 登記的做法是「用 GUI 改一個已知值再差分」,而那句話預設了一台開著的機器。
**它到 2026-08-18 之前在桌面上做不了,而理由不是難,是模擬環境寫不了設定。**
`libapmib` 的 TLV 序列化器對奇數位址存半字,`qemu-user` 給 SIGBUS,所以**任何**
會存設定的路徑都在同一道指令上停住 —— 那也是 39 個 handler「死掉」的真正原因。
`tools/alignfix/` 補掉那一個差異之後,「改一個已知值再差分」第一次不需要裝置。

**而這件事的價值不在省一次上電。** 差分要成立,前後兩份快照之間**只能有一個變數**;
在實機上那很難保證(背景服務會寫設定、DHCP 租約會到期、時間會走),在一個
`reset` 就回到同一份 flash 的環境裡,它是免費的。

`P8-12` 在同一節,因為它的答案是同一種形狀:**這條鏈卡在自家工具,不是裝置。**
`fwrecon compcs` 只有 decode,沒有 encoder,所以「上傳一份改過的設定」這件事
在這個 repo 裡目前做不到 —— 而那是一個關於工具的結論,不是關於裝置的結論,
兩者不可以寫成同一句話。

**而這一節第一次被執行是 2026-08-18,寫好它的隔天,它錯了兩次。**

第一次錯在**沒有帶那個讓它得以存在的東西**。上面整段在講 `tools/alignfix/` 補掉了
對齊差異,然後步驟裡的 `flash set` 沒有掛上 preload。失敗的樣子不是報錯:guest 印出
`Bus error` 之後**不會結束**,就一直待著。一個沒有上限的步驟在這種失敗下讀起來像
「慢」,不像「壞」——所以現在那個上限是工具的一部分,而超時訊息直接說出是哪一個
preload 不見了。

第二次錯得更值得記:**它叫人比較兩個不在同一個座標系的數字。**
`qemu-env.sh diff` 報的是 flash 映像裡的位移,而設定區是壓縮的（這一台是 7,478
壓成 45,226）;`fwrecon compcs` 報的是解壓之後的欄位位移。把前者拿去對後者,比的是
兩件不同的東西 —— 而第一次跑出來的結果**差 2 bytes**,看起來「差不多對」。
**那比明顯錯更難發現,也更容易被寫成結論。**

所以現在這一節不比較它們:工具把每一個變動的 byte 標成「在壓縮酬載裡」或「在它
之後第幾個 byte」,然後**只在解壓空間裡**做差分。`P8-23` 的反證條件也因此變成兩個
方向都能觸發 —— 解出來一個欄位都沒動,或者動的不只一個 —— 而不是一個要靠人眼判斷
「像不像同一個位置」的問題。

> **場次之前把步驟寫出來是必要的,不是充分的。** 2026-08-17 加的規則抓得到「有結果
> 卻沒有步驟」的列;抓不到「有步驟但一次都沒跑過」的節。而一個沒跑過的步驟,是一個
> 關於指令的預測,不是指令。

---

### 8.12.28 UDP 那一輪為什麼是第一次跑,而不是重跑　→ `runsheet.md` `A3.14`

`runsheet` 舊版用 `nmap -sT` 掃過 9034,而 `P6-4` 講的是 CVE-2021-35394 的 **UDP**
daemon。**一個 TCP RST 對一個 UDP listener 什麼都沒說。** W05 的 UDP 清單十個埠
裡沒有 9034,所以這不是重跑,是第一次跑。

**沒有正對照的「全部關閉」量到的是鏈路,不是裝置。**
UDP 沒有交握,所以「沒有回應」與「封包沒送到」在觀測上完全相同。因此同一輪裡必須
有一個**已知會回應**的 UDP 埠 —— 1900（SSDP,`P1-10` 已經證實 miniigd 在跑）
或 53。那一發不是湊數的,它是唯一能把「裝置沒開這個埠」跟「你的網卡設錯了」
分開的東西。

`P6-6`（skt 5555 後門）、`P6-7`（TR-069 7547）、`P6-8`（SNMP 161）、
`P6-12`（20005 / 9999）排在同一節,因為它們共用同一份對照與同一次連線設定,
分開跑等於重複三次同樣的準備工作而不會多知道任何事。

---

🔴 **登記簿指定的兩個正對照在這台上都不會回應，而理由不同——這一節的價值一半
在那裡。** 反證條件寫「沒有正對照的『全關』不算數」，因為 `nmap` 的
`open|filtered` 與真正的靜默分不出來。實際上：`53/udp` 沒有 relay 在聽（`dnrd`
由 `sysconf` 在 WAN phy 路徑上啟動，沒有 WAN 就不起來，見 §8.12.30）；而
`1900/udp` **有東西在聽**，只是 `nmap` 的預設 SSDP 探測用 `ST: ssdp:all`，
而這台不回答 `ssdp:all`——那本身違反規範，也讓它被報成 `open|filtered`。

**所以「1900 沒有回應」在 2026-08-18 差一點被寫成「這台沒有 UPnP」。**
換成三個具體的 ST 之後它全部回 200。**這台有兩個 UPnP 堆疊**：`miniigd` 的 IGD
（`52869/tcp`，被 `UPNP_ENABLED=0` 關掉）與 `wscd` 的 WSC（`1900/udp` +
`52881/tcp`，那個旗標**管不到它**）。一個旗標關掉一個堆疊，而報告會說 UPnP 關了。

**可用的正對照是 DHCP**，而它比登記簿要求的強：`broadcast-dhcp-discover` 收到
一份完整的 `DHCPOFFER`，那是一次應用層往返，不是「有回應」。**替換要寫下來，
不能默默通過**——一個被換掉的對照組如果沒有記錄，下一個人會以為原本那個成立過。

### 8.12.29 UPnP:為什麼 SOAP 的路徑不是手冊寫的那一個　→ `runsheet.md` `A3.15`

`P6-1` 登記的端點是 `/upnp/control/WANIPConn1`,那是抄自公告的寫法。
**這一台的 `miniigd` 用的是 `/upnp/control/WANIPConnection`**,而那個差別會讓
一整輪 SOAP 請求全部回 404,看起來像「這台沒有 UPnP」——
而 `P1-10` 已經在實機上量到 52869 是開的。**一個錯的路徑產生的是一個假的否定。**

**`P8-7` 排在同一節,因為它是同一個 SOAP 端點的另一個用途,不是另一個測試。**
`AddPortMapping` 的 `NewInternalClient` 填成路由器自己的 LAN 位址,就把一個
LAN-only 的管理介面推上 WAN。**這一發做完之後必須把映射刪掉**,而刪除要在同一節
裡完成 —— 一個留在裝置上的映射會讓後面每一節的網路行為都改變,而那不會報錯。

**這一節不碰的東西也寫在這裡**:不對真的網際網路開任何映射,WAN 側接的是假 ISP。

---

### 8.12.30 DNS 身分,以及為什麼要拔掉 WAN　→ `runsheet.md` `A3.16`

`P6-9` 問的是「在聽的是哪一支」,而不是「有沒有 DNS」。rootfs 裡有三個候選
（`dnrd` / `dnsmasq` / `dns_protocl`）,而版本查詢的回應形狀分得出來。
**指名一支才有辦法去查它的已知缺陷;「有一個 DNS 在聽」查不了任何東西。**

`P6-10` 是這個專案獨有的一格:`wan_disconnect` 這個腳本會叫起 `StartDnsSpoof`,
所以**WAN 斷線是一個攻擊者在某些情境下製造得出來的觸發條件**。
拔掉 WAN 線之後 DNS 的行為改不改變,是這一格的全部內容。

> ⚠️ **`dnsspoof` 這個名字跟 dsniff 的工具撞名,而那個撞名已經讓一次 prior-art
> 搜尋走錯方向。** 搜尋要按**行為**搜,不是按名字。

---

🔴 **這一節的 `P6-10` 在 2026-08-18 不是「拔 WAN 線」測出來的，是「WAN 真的
連上過然後線被拔掉」測出來的，而那個差別是全部。** 一台從來沒有連上過 WAN 的
機器，拔線什麼都不會發生——`dnsspoof` 的觸發條件是狀態轉換，不是狀態。
本場之所以測得到，是因為 `A3.18` 那一節先讓它拿到一份真的 DHCP 租約。
**兩節的依賴關係在作業單上看不出來，記在這裡。**

`dnsspoof` 起來之後對**每一個**名字回 `10.1.1.1`，包含一個不存在的 TLD——
所以它是全域萬用字元，不是解析失敗的後備。而 `53/udp` 在本場稍早每一次量都是
關的，所以「有沒有 DNS」這個問題的答案會隨 WAN 狀態翻面：**在同一台機器上，
同一個埠，同一天，量到兩個相反的答案而兩個都對。**

### 8.12.31 CSRF 與 DNS rebinding:一條公告改變了這兩列的寫法　→ `runsheet.md` `A3.17`

`P8-3` 與 `P8-4` 凍結的預測寫的是「這台沒有 CSRF token」。**預測不改** ——
凍結的東西不因為事後找到前案就改,那正是凍結的意義。**但卡片必須引用
CVE-2023-47677（Talos）**:同一顆 SDK 的 `boa` 被報告有 CSRF 缺陷,而且**有**一個
「載入 HTML 表單頁之前不讓 API 被呼叫」的防護,可用 iframe 繞過。
不引用,結果會被讀成這個專案的發現。

**而 Talos 描述的機制不是這個 binary 裡的那一個。** 這裡的是以來源 IP 為鍵、
用 uptime 過期的比對（見 8.12.9 與 `notes/auth-session-ip.md`）。兩者是不是
同一個功能從外面看的兩種描述,**沒有解決**,卡片照這樣寫。

`P8-6`（DNS rebinding）排在同一節,因為它與 CSRF 共用同一個前提:**這台不檢查
`Host`**。`check_host` 是一個正確的驗證器,而 `0x0040bbec` 在 `vhost_root` 為 NULL
時跳過整段,`VHostRoot` 在設定檔裡是註解掉的。所以 rebinding 少掉了它通常最難的
那一步,而這一節要驗的是那個「少掉」在矽上也成立。

---

### 8.12.32 假上游:為什麼 NTP / DDNS / DHCP / PPPoE 排在同一節　→ `runsheet.md` `A3.18`

**這一節問的是同一個問題的五個實例**:這台**主動連出去**拿回來的資料,有沒有被
當成資料處理。`bughunt.md` 的方法那一節寫過,這是第四個來源,而且它是唯一一個
不看「可以送什麼進去」的來源。

`P8-11`（假 NTP / 假 DDNS / 假 DNS 回應）與 `P8-19`（WAN 側 DHCP / PPPoE）
共用同一套器材:一台假 ISP。分成兩次架等於把最貴的準備工作做兩遍。
`P6-5`（SIP ALG,CVE-2022-27255）也在這一節,理由相同 —— 它必須從 WAN 側送,
而 WAN 側只有在假 ISP 接上的時候才存在。

**已經知道的一件事要先講,免得被當成新發現**:`/usr/share/udhcpc/eth1.bound`
是一行 `sysconf conn dhcp $interface $ip $subnet $router $dns`,值變成 argv
而不是命令,而且 `hostname` 與 `domain` **根本沒有被傳進去**。所以注入的問題往
`sysconf` 裡面移了一跳,而那一跳還沒有被回答。**這一節不是去證實一個已經被否定的
形狀,是去問那一跳。**

---

🔴 **這一節在 2026-08-18 撞到一件跟 NTP / DDNS 無關、但比它們都重的事，而它值得
寫在程序的「為什麼」裡：先確認裝置還做得到它的本業。**

WAN 側的每一項都預設「裝置會在 WAN 上講話」。實際上它一個 frame 都沒送——
不是 DHCP、不是 ARP、什麼都沒有——而 `udhcpc` 在 `ps` 裡、`WAN_DHCP` 是 1。
原因是 `eth1` 以 `MTU:0` 開機，而那是因為 W05 那一輪未認證的、參數缺席的 POST
把 `DHCP_MTU_SIZE` 從 1500 寫成 0，**寫進 flash**。

**那不是一個服務被關掉，那是這台路由器從 2026-08-17 起就上不了網**，而中間跑過
四場進站、沒有一場問過它還能不能路由。記在 `PROGRESS.md` 開放題 #73。

**所以這一節（以及任何 WAN 側的節）的第一步是把 `eth1` 的 MTU 看一眼**，
而更好的做法是讓 `make doctor` 或第 1 站去問「這台還做得到它的本業嗎」。
一個把裝置變安全的測試，會無聲地作廢後面的測試——本週有五個標的是這樣沒的：
`UPNP_ENABLED`、`ALG_SIP_ENABLED`、`SSH_ENABLED`、`TELNET_ENABLED`、
`DHCP_MTU_SIZE`。**前四個只是關掉服務，第五個把裝置弄壞了。**

⚠️ **DHCP 那一半有一個順序陷阱**：租約一拿到就是 3600 秒，而逼它重新 DISCOVER
要送 `SIGUSR1` 給 `udhcpc`——那需要 LAN 側的存取，而 LAN 側存取與網卡插在 WAN 埠
互斥。**要送第二份不同的租約（例如帶路由選項的），必須在插到 WAN 埠之前就安排
好觸發方式**，否則就是這一場的結果：選項 33 / 121 / 249 在它自己的請求清單裡，
而那份租約沒有送成。

### 8.12.33 儲存型注入:八個欄位裡只有三個這一週測得到　→ `runsheet.md` `A3.19`

`P8-2` 登記了八個候選,而**其中五個這一週打不到**,理由各不相同:惡意 Beacon 的
SSID 要監聽模式網卡（跟著 `P7-3` 移到 W08）、無線 client 名稱要有裝置連上這台的
Wi-Fi、NetBIOS / mDNS 這台根本沒有對應的 daemon（55 個 ELF 裡沒有 `nmbd` 也沒有
`avahi`）。**把打不到的三個寫成「未觀察到」會是一句假話。**

測得到的三個是 UPnP 的 `NewPortMappingDescription`（52869 開著）、`formSysLog`
那一組（失敗登入的帳號名與 `User-Agent`）、以及 PPPoE server name（跟 `A3.18` 同一趟）。

**每一個都先讀模板再送封包。** docroot 的 143 個檔在 dump 裡,有沒有輸出編碼是
**讀得出來**的,而讀出來之後送封包才知道要看哪一頁。反過來做等於在瀏覽器裡大海撈針。

> ⚠️ 反過來的那一半也要寫下來:**模板沒有編碼、但送進去的值被截斷或消失**,
> 代表過濾發生在寫入端而不是輸出端 —— 那要指出是哪一個 handler 做的,
> 否則「有 XSS」與「送不進去」會被寫成同一件事。

---

### 8.12.34 借合法功能做偵察,以及一個便宜的可用性測試　→ `runsheet.md` `A3.20`

`P8-14` 的價值不在「能不能」,在**它不需要任何新的缺陷**:`formSysCmd` 是這台
**出廠就有**的功能,而 `P3-3` 已經在實機上證明它未認證可達。所以「用它掃內網」
量到的是**一個合法功能的影響範圍**,而那正是寫給網通產業讀者看的時候最有說服力的
一格 —— 不是「我找到一個洞」,是「這個功能本身就是一台內網掃描器」。

`P8-16`（Slowloris）排在同一節,理由是成本:它跟 `P8-14` 共用同一條連線,
而它問的問題只有一個 —— `boa` 是單一 process（`boa: starting server pid=350`）,
所以**同時連線數的上限就是可用性的上限**。W05 已經量到未認證的空 POST 可以把它
佔住六到九秒,一次約 45 個就把它徹底弄掉。Slowloris 是那個數字的下界版本。

> 🔴 **這一節做完之後 web server 很可能不在了。** 所以它排在需要 web server 的
> 每一節之後,而排在 `A3.24` 之前。

---

🔴 **`P8-16` 的計數在 2026-08-18 錯過一次，而錯的方向會給出相反的結論。**
用 `/proc/net/tcp` 數 `boa` 的連線，在握著 200 條的時候回報 **0**——因為
`boa` 綁的是 dual-stack IPv6 socket，IPv4 client 以 `::ffff:` 映射位址出現在
`/proc/net/tcp6`。同一份檔案在本場稍早也沒有把 port 80 列成 LISTEN，**而當時
伺服器正在回應**。

**那個「不可能」才是去查第二次的理由，不是別的。** 一份說「你正在講話的那個
服務不存在」的檔案，它的 0 是它自己的 0。用 `tcp6` 數，`boa` 握著 251 條而且
全程服務——所以反證條件的第二支觸發，`boa` 的連線處理要回頭讀。

⚠️ **這一節與 `A3.23` 都會產生「短 timeout 的 `000`」**，而它跟崩潰長得一模一樣。
本場踩到兩次：`formWlanSetup` 在 `-m 6` 下回 `000`，實際上它回 200 只是花了
10.3 秒。**會重新初始化無線介面的 handler 給 30 秒以上。**

### 8.12.35 線上的明文憑證,與驅動的私有 ioctl　→ `runsheet.md` `A3.21`

`P8-17` 的預測是「管理介面純 HTTP,沒有 TLS 堆疊,所以憑證在線上是明文」,而
**它的反證條件才是這一節的重點**:抓到的封包裡密碼**不是**明文 → 有某種前端雜湊,
那要回去讀 `w6cg` 裡的 JS。這個 repo 已經在別的地方犯過「假設前端沒做事」的錯,
而這一發的成本是一個 `tcpdump`。

`P8-20`（`iwpriv` 私有 ioctl）在同一節,但它的前提不同:**它需要一個 shell**,
而這台沒有。所以這一格這一週能做的是**靜態的那一半** —— `iwpriv` 在 `/bin` 裡,
驅動接不接私有命令可以從驅動的 ioctl 表讀出來。**「拿到 shell 之後可以做什麼」
不是一個未經證實的假設可以支撐的句子**,所以卡片上要寫成條件句。

---

### 8.12.36 無線指紋與登入計時:兩個便宜、而且其中一個大概會失敗的量測　→ `runsheet.md` `A3.22`

`P1-11` 是這一場最便宜的一格,而它的用途是**否證一個排除理由**:`E-8` 之所以被
排除,是因為這台被判定成 2.4 GHz 802.11n only、沒有 5 GHz、沒有 WPA3。
掃到 5 GHz 或 SAE,那個排除就不成立。**一個把自己的排除理由拿去驗的測試,
比一個去證實預期的測試值錢。**

`P2-10`（登入計時預言）**預期會失敗**,而它仍然要做,理由寫在它自己的反證條件裡:
「1000 次取樣的分佈重疊 → 方法在這條鏈路上沒有解析度,**記為方法限制而不是
「沒有時間差」**」。這兩句話在資料上長得一模一樣,而它們是完全不同的結論。
**一個沒有事先寫下這個區別的計時測試,事後一定會被寫成第二種。**

---

### 8.12.37 把桌面算出來的兩份清單拿到矽上　→ `runsheet.md` `A3.23`

**這一節是這一場唯一一個會反過來否證自家儀器的測試,所以它不准被跳過。**

桌面上算出兩份清單:五個「參數缺席就死」的 handler,以及一份在模擬下全部
404 的路徑字典。兩份都是模擬或靜態的產物,而 `P5-6` 凍結的反證條件正是
「模擬下的崩潰在實體機上重現不了 → 模擬環境的結論不能外推,只能當篩選器不能當證據」。

**分成兩發,而且不准混在同一張卡上:**

1. **五個裡挑一個開火** —— `formSchedule`,缺 `webpage`。預期:web server 消失,
   而且不會自己回來。**這一發如果成立,`D-11` 從「一個未認證的請求殺掉 server,
   說不出是哪一個」變成一個有名字、有機制、有位址的東西。**
2. **另外抽 2–3 個原本在那 39 個裡、現在活著的 handler**（例如 `formNtp`、
   `formDMZ`）,送同樣的一發。**預期:它們在矽上會活著**,因為核心會補對齊 ——
   這是一個有機制撐著的預測,不是硬幣。

> ⚠️ **第二發的反證條件比第一發的預測重要**:如果那 2–3 個在實機上也死掉,
> **對齊那套解釋就是錯的**,而錯的代價不只是這一格 —— 它會讓 `tools/alignfix`
> 打開之後量到的每一件事,以及 `bughunt.md` 第 16 列的改寫,全部退回原點。

`P1-7` 在同一節,因為它是同一種形狀的第二份清單:桌面上那些路徑全部與不存在的
名字無法區分,而**這一台的閘門會把沒豁免的路徑轉去 `home.htm`**,所以實機上要看的是
`302` 的目的地而不是狀態碼。**跟隨轉址的探測量到的是轉址** —— 那個錯誤桌面上犯過
一次,見 §8.12.26。

---

🔴 **兩發的編號是 1、2，而可以跑的順序是 2、1。** 第一發是**終局的**——`boa`
消失而且不會自己回來——而第二發需要 `boa` 活著。照編號跑，第二發根本打不成。
編號沒有改，是為了讓這條修正在文件上看得見。

🔴 **而第二發才是重的那一發。** 第一發驗證的是「模擬下的崩潰在矽上也成立」，
那是好消息但不改變任何既有結論；第二發問的是「那些**只在模擬下**死掉的，
在矽上會不會活著」——**如果它們也死掉，`tools/alignfix` 打開之後量到的每一件事
都退回原點。** 實測三個全部活著（`formNtp` 4.42 秒、`formDMZ` 4.50 秒、
`formWlanSetup` 10.3 秒），對齊那套解釋成立。

🔴 **開火之前要先開第二條路，而理由是一份拿不回來的 core dump。**
第一發之後 console 印了 `caught SIGSEGV, dumping core in /tmp`。那份 core 取不
回來：`boa` 是唯一的入口、`/tmp` 是 `/var/tmp` 的 symlink 而它是 tmpfs（重開就
沒）、序列埠會回顯輸入但不回應（這台的 console 沒有 shell）。**修法是在開火之前
用命令注入把 `telnetd` 起來。**

本場後半立刻套用了，而它在 `A3.15` 的 `wscd` 那一節**直接救了場**：`wscd` 停止
回應之後，是 telnet 進去才發現**行程還活著、只是把 listener 關了**，而
「卡住」與「崩潰」的區別是那整條發現的核心。⚠️ 那是一個沒有認證的 root shell，
收工前必須斷電。

🔴 **2026-08-19 追加：那條為了取回 core dump 而開的門，順手把 `P5-2` 從「要再打一
發崩潰」變成「讀兩個檔」。** `P5-2` 問的是 uClibc 有沒有固定的載入位址，而它唯一
的觀測通道原本是 kernel 的 fault 訊息 —— 也就是說，**每量一次就要打掉一次
`boa`，再斷電重開。** 桌面上那份 `notes/mips-ret2libc.md` 已經從兩行既有的 fault
訊息把基底算到 `0x2aae3000`，但那兩行來自**同一次開機**，而登記簿的反證條件寫的
是「兩次重開機後基底不同」。

**`/proc/<pid>/maps` 直接把那個數字印出來，不需要任何東西崩潰**，而且今晚這一次
是 reset 之後的**另一次開機**，所以它答得了那條字面反證。**一個非破壞性的量測
排在一個終局的量測前面，這個順序不是禮貌，是它唯一可能的順序** —— 第一發打完
`boa` 就沒有 `<pid>` 了。同一個 shell 還能讀 `/proc/sys/kernel/randomize_va_space`，
那是「有沒有隨機化」的第二個、而且獨立於位址算術的來源。

⚠️ **這一格會讓那份桌面計算變成可反駁的，而那正是它排進來的理由。** 如果
`maps` 印出來的不是 `2aae3000`，那份筆記裡的 `system @ 0x2ab08460` 就只對
2026-08-18 那一次開機成立，`P5-2` 要從 `partial` 改成 `refuted`，而整條 ret2libc
的前提要重寫。**一個只能證實自己的步驟不值得排進一場 bench。**

### 8.12.38 Reset 按鈕排在全場最後,而理由跟危險程度無關　→ `runsheet.md` `A3.24`

**它抹掉的是前面每一項站著的地面。**

`P9-9` 的預測是「reset 之後 `COMPCS` 變回 `COMPDS`」。如果那成立,這一場前面
每一項改過的設定都不存在了,`P0-5` 的 IoC 基準（`COMPCS` 與 `COMPDS` 差 4/343）
也歸零,而第 ⑤ 環那種「指著 flash 上被改掉的 byte」的證據鏈,指的那些 byte 會
變回原值。**所以它的位置不是因為它危險,是因為它是一個時間方向上的單向門。**

**`H601` 必須 UNCHANGED,而那一格才是這一列真正在問的。**
`H601` 放的是這一台獨有的 MAC 與射頻校準。如果 reset 也把它蓋掉,那這台就
**永久地**不再是它自己了,而且那件事不會有任何錯誤訊息。

#### 2026-08-19,按鈕還沒按之前:這一節有兩個錯,而第二個讓它不可能失敗

**第一個是位址。** 這一節原本要求前後各一份 `H601` 快照,而它給的位址是
`0x3F0000`。`H601` 在 `0x006000` —— `runsheet.md` `A2.3.1` 的分區圖自己就是
這樣畫的,`notes/flash-layout.md` 第 134 行也是,而公開的 Realtek SDK
`apmib.h` 的 `HW_SETTING_OFFSET` 同樣是 `0x6000`。實際讀那顆 flash:`0x006000`
起 4,096 個 byte 裡有 4,093 個不是 `FF`,開頭就是 `H601` 四個字元接一串 MAC;
`0x3F0000` 起 4,096 個 byte **全部是 `FF`**,那是抹除區。

所以那一版的「前後各一份、而且不可以省的一步」,比的是 `0xFF` 對 `0xFF`。
**一個不可能失敗的對照組,而且正好架在這一列唯一真正在問的那一格上。**
它會永遠回報 UNCHANGED,包括在 reset 真的把 `H601` 蓋掉的那個世界裡。
這跟 `make recovery scripts able to fail` 是同一條規矩,只是這次犯在文件上。

**第二個是狀態。** 同一份命令帶 `--at-prompt`,那是「板子已經停在 `<RealTek>`」,
第 2 站;而這一節掛在第 3 站。**一個第 3 站的步驟執行不了第 2 站的命令**,
而「`A1.1` → `A4.2` 從頭讀下來就是一個可以照著跑的順序」正是 Part A 的承諾。
`check-runsheet.py` 現在檢查這件事:一個步驟的**命令**如果需要別站的裝置狀態,
就要在前面把讀者明確送去那一站,否則 CI 擋下來（`A3.8` 的救援路徑就是這樣寫的,
所以它合法）。

**修法是引用而不是重寫。** `A2.3` 的 64 KiB 快照是從 `0x0` 開始的,`H601`
本來就在裡面,所以「前」那一份**已經有七份**,而且 `0x6000` 那 4 KiB 在
2026-08-16 到 2026-08-18 之間 **byte 完全相同**。這比原本設計的一對前後快照更強:
一個橫跨三天、五次上電、兩次 flash 寫入的穩定基準線,任何改變都無從解釋成雜訊。

#### 為什麼 2026-08-19 要改預測,而且是在按下去之前改

原預測是「reset 會把 `COMPCS` 覆寫回 `COMPDS`」。桌面上把昨晚第 2 站那份
`config-region-20260818-1927-pre.bin` 兩個區都解出來之後,那句話**今天沒有
鑑別力**:343 個具名欄位,`COMPDS` 與 `COMPCS` 差 **0 個**。按下去之後量到
「兩個區一樣」,分不出「reset 有作用」和「reset 什麼都沒做」。

而它們為什麼一樣,才是真正的發現:**`COMPDS` 自己也被寫壞了。** 對
2026-08-16 的原始讀值,出廠預設區有 25 / 343 個欄位不同,其中包含
`DHCP_MTU_SIZE 1500 → 0`、`UPNP_ENABLED 1 → 0`、`ALG_SIP_ENABLED 1 → 0`。
W05 那一輪未認證、參數缺席的 POST 不只改了現行設定,**它改了出廠預設**。

於是「reset 會不會把 WAN 救回來」變成一個真的有兩個答案的問題,而靜態這一半
指向其中一個:`/bin/reload`（昨晚 `ps` 裡 PID 291,活著）輪詢 `/proc/load_default`,
命中之後印 `Going to Reload Default` 並執行 `flash default-sw`;而 `/bin/flash`
自己的 usage 把兩件事分得很清楚 —— `default` 是「write all flash parameters
**from hard code**」,`reset` 才是「reset current setting to default」。
**按鈕走的是前者**,所以它應該寫編譯進去的硬編碼表,而不是那塊被弄壞的區。

兩個答案都是結果,而且都不是小事:

- **回到 1500 / 1 / 1** → `P8-19` 那條鏈拿到第三個獨立驗證,而且是唯一一個
  不需要動手改任何東西的;`P6-1`、`P8-7`、`P6-5` 三列也同時解鎖,不必動
  `A2.5`/`A2.6` 那個唯一不可逆的寫 flash 路徑。
- **仍然是 0** → 一發未認證的 POST 把這台推進一個**連廠商自己的復原按鈕都
  出不來**的狀態。那時 `P8-19` 從「跨越所有重開機」升級成「跨越原廠重置」,
  而唯一的回頭路是拿 programmer 寫 flash。

**在按下去之前,這一場所有的紀錄卡都要先寫完。** 不是習慣問題:reset 之後,
任何一張「等一下再補」的卡都失去了它可以回頭驗證的環境。


### 8.12.39 公告的名字與這個 build 的名字，為什麼要機械地比　→ `runsheet.md` `A1.10`

**這一節存在是因為一個 404 有兩種讀法，而其中一種是錯的。**

十六份公告點名了一個表單端點與一個參數。重現的人逐字照抄兩者。**如果任一個拼法
對眼前這個 build 是錯的，請求會 404、或者參數被忽略，而那個結果最誠實的讀法
——「沒有這個漏洞」——是錯的。**

這個專案已經被咬過兩次。`CVE-2025-3992` 寫 `/boafrm/formWlwds`、`CVE-2025-3995`
寫 `/boafrm/fromStaticDHCP`，兩個拼法在**六個** build 的分派表裡都不存在，而它們
各自描述的缺陷確實在，只是名字不同：`formWlWds`（中間大寫 W）與 `formStaticDHCP`
（`form`，不是 `from`）。而 `CVE-2025-3988` 寫 `service_type`，這台的 handler
讀的是 `comment`。

**為什麼是機械地比，而不是讀過去。** 十六列乘兩個名字是三十二次比對，手做會漏，
而且漏掉的那一次長得跟做過一樣。工具比對的兩份東西都是已提交的報告——這一台自己
還原出來的 `root_form[]`（57 筆），以及同一張表跨六個 binary——所以它不需要裝置、
不需要 dump，一份 clone 就跑得完。

**公告清單為什麼不在工具裡。** `notes/cve-status.md` 是那張矩陣的擁有者。工具帶
第二份就是同一份狀態的第二個擁有者，而這個 repo 的經驗是兩份會在一週內對不起來。
代價是要對散文寫解析器，而那個代價由**拒絕跑**來付：讀不到 15 列就 exit 2，
因為一份殘片會產出一張又短又乾淨又錯的表。

**三個控制組，而它們防的是兩種不同的假通過。** 正對照（`formSysCmd`/`sysCmd`
必須找到）防的是比對器壞掉；負對照（一個編出來的端點與一個編出來的參數必須都回報
不存在）防的是比對器對什麼都說「不存在」——**那會產出一張全是有趣負面結果的表**；
解析下限防的是讀到殘片。`check-reports.py` 對這份報告強制 `control_ok`。

**`P4-6` 以前掛在 `A1.6` 的標題上，而 `A1.6` 從頭到尾沒有它的程序。** `A1.6` 做的是
參數缺席／長度階梯／協定炸彈，那是 `paramfuzz.py` 的三個維度；`P4-6` 問的是名字對
不對得上。那是 `PROGRESS.md` 開放題 #71 的形狀——標題宣稱關掉一列而內容沒有它，
而 `check-runsheet.py` 兩個方向都看不見。2026-08-19 拆開。

**這一節的結論是靜態的，而那個限制要寫在結論旁邊而不是註腳裡。** 參數名出現在
handler 參照的字串裡，只代表那個 handler 提到它。**不代表它從請求裡讀那個名字**，
更不代表溢位重現得出來。這一節回答的是比較窄、但也是唯一機械答得出來的那個問題：
照公告逐字重現，打的東西在這一台上存不存在。

## 9. 驗收

### G0 — 工具鏈全綠

```bash
make verify                                              # WSL 端
```
```powershell
powershell -ExecutionPolicy Bypass -File tools\setup\setup-windows.ps1 verify   # Windows 端
```

兩邊都要看到 `GREEN`。

### G1 — 能不能口述韌體的七個要素

**闔上電腦，大聲回答。** 答不出來就再讀一次 [`notes/anatomy-n150rt.md`](notes/anatomy-n150rt.md)。

| # | 問題 | 答案 |
|---|---|---|
| 1 | 這是什麼晶片? | Realtek RTL8196 系列 —— **還沒實體確認**，要等拆機 |
| 2 | 什麼 CPU 架構? | MIPS32,MIPS-I 指令集，o32 ABI |
| 3 | 端序? | **大端序 Big Endian** |
| 4 | 載入基底位址 / 進入點? | `0x00400000` / `0x00404020`（2.1.2） |
| 5 | 什麼檔案系統? | SquashFS 4.0 —— 2015 版用 LZMA,2020 版用 XZ |
| 6 | 網頁伺服器是誰? | `/bin/boa`,`Boa/0.94.14rc21`，**以 root 執行** |
| 7 | 設定檔怎麼存? | `libapmib.so` → `COMPCS` 明文格式 → `/web/config.dat` |

**進階題（答得出來代表你真的懂了）：**

- 為什麼大端序的 MIPS 裡面裝的是「小端序」的 SquashFS?
  → SquashFS 4.0 規格就規定**磁碟格式一律小端序**，不管 CPU 是什麼。核心驅動會自己轉。這不是矛盾。
- 規格書說 2MB 快閃記憶體，你為什麼說至少 4MB?
  → 韌體自己的燒錄位址表最高到 3.57 MiB，塞不進 2MB。
- 為什麼 `readelf` 對 2020 版的 boa 什麼都印不出來?
  → 那個檔案被 `sstrip` 過，section header 整個被移除。`readelf` 靠它工作，找不到就**印空白還回傳成功**。

### 全部重跑一次（確認沒壞）

```bash
make verify      # G0:工具鏈
make ci          # CI 會檢查的全部(容器建置除外)
```

```
  ok   G0 GREEN — all tools functional
All checks passed!
110 passed in 2.17s
reports OK — 12 fwrecon (schema 1.0), 27 Ghidra, 1 rtcase
register OK - 128 cases, 98 frozen, 5 executed, freeze ba6810e848c69f56...
  22 passed, 0 failed
  ok   local CI equivalents passed (container build not included)
```

> ⚠️ **push 之前跑 `make ci`，不要自己挑幾個目標跑。** 見 [§10.21](#1021-本機全綠但-ci-還是紅的)。

### G3.75 — 開打前的前置（W05 Day 0）

```bash
python3 tools/rtcase.py check        # 登記簿凍結了、每一筆結果都有證據
bash tools/test-rtcase.sh            # 而且這個 gate 真的擋得住東西(22 個案例)
```

| # | 要有什麼 | 現況 |
|---|---|---|
| 1 | `FLW` 回復路徑演練過（＝ G3.5 #5，見 §8.9） | ❌ **還沒做，它擋住下面全部** |
| 2 | 隔離驗證過：網段上只有兩個 MAC,WAN 接假上游 | ❌ 要在機台前做 |
| 3 | IoC 預檢：設定 vs 出廠基準線 + 殭屍網路常用埠 | ❌ 要有機器。**判準先寫好了：差異維持在 4/344** |
| 4 | 預測登記簿凍結 | ✅ `test-ledger.md`，128 項 / 98 項有反證 |
| 5 | 揭露登記簿寫好 | ✅ `docs/disclosure.md` |

**5 條沒到齊之前，不准對這台送第一個封包。** 操作規程在 §8.10。

---

## 10. 疑難排解

> 下面每一條都是**這個專案真的踩過**的坑，不是想像出來的。

### 10.1 UAC / 「這個 App 要變更你的裝置」跳出來

**除了 §4.1 裝 WSL 之外，任何步驟都不該跳這個。**

如果跳了，代表你可能用到了舊版腳本（走 `winget` 裝 JDK 的那版）。現在的 `setup-windows.ps1` 用免安裝 ZIP 解到使用者目錄，不需要權限。**按取消，然後 `git pull` 更新專案再跑一次。**

### 10.2 Windows 防火牆問「私人網路 / 公共網路」

是 Java（Ghidra）觸發的。**按取消**。Ghidra 的分析純本機運算，不需要網路。

### 10.3 `make: command not found`

你在 PowerShell 裡打了應該在 WSL 裡打的指令。先 `wsl -d Ubuntu-24.04`，再 `cd /mnt/c/...`。

### 10.4 `binwalk: command not found`（明明裝過了）

新開的終端機還沒載入 PATH。兩個解法：

```bash
source ~/.bashrc          # 立即生效
```
或直接關掉終端機重開。

### 10.5 安裝腳本卡在 `rust: fetching rustup-init`

網路瞬斷。**直接重跑一次**：

```bash
bash tools/setup/setup-wsl.sh all
```

腳本是**冪等的** —— 已經裝好的會跳過，只補沒裝的。

### 10.6 binwalk 編譯失敗，提到 `fontconfig`

缺系統套件。理論上 `apt` 階段已經裝了，沒有的話手動補：

```bash
sudo apt install -y libfontconfig1-dev libfreetype-dev
bash tools/setup/setup-wsl.sh binwalk
```

> binwalk v3 有畫熵值圖的功能，那功能需要字型函式庫。這個相依關係不會寫在文件裡，只會在編譯炸掉時出現。

### 10.7 `make unpack` 說 `no symlinks in the extracted tree`

**這是保護機制，不是壞掉。**

代表你把 `FWRE_WORK` 指到了 Windows 的磁碟（`/mnt/c/...`），那裡存不了符號連結。

```bash
echo $FWRE_WORK        # 應該是空的,或是 /home/你的名字/fwre-work
unset FWRE_WORK        # 清掉,用預設值
make unpack
```

### 10.8 `unsquashfs` 回傳非零 / 一堆 `created 0 devices`

**正常。** 見 [§6](#6-part-2--解包韌體) 的說明。只要看到 `extracted: N files ... M symlinks` 而且 M > 0 就是成功。

### 10.9 Ghidra 說 `GHIDRA_INSTALL_DIR is not set`

環境變數還沒生效。**關掉 PowerShell 重開**，或當場設：

```powershell
$env:GHIDRA_INSTALL_DIR = "$env:LOCALAPPDATA\fwre-tools\ghidra_12.1.2_PUBLIC"
```

### 10.10 Ghidra 說 `binary not found` 而路徑看起來是對的

`\\wsl$\...` 路徑要求 WSL **正在執行**。先隨便跑一下讓它起來：

```powershell
wsl -d Ubuntu-24.04 -- true
```

還有，路徑裡的使用者名稱要對：

```powershell
wsl -d Ubuntu-24.04 -- whoami
```

### 10.11 `make test` 有測試被跳過（skipped）

在 Windows 上跑測試才會這樣 —— 建立符號連結在 Windows 需要特殊權限。**在 WSL 裡跑就不會**。

### 10.12 空間不夠

下載快取跑完就可以刪：

```powershell
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\fwre-setup"     # 省 742 MB
```

WSL 端要清解包結果：

```bash
make clean-work        # 刪掉解開的檔案系統,韌體和報告都保留
```

### 10.13 想從頭來一次

```bash
rm -rf ~/fwre-work
make fetch unpack recon
```

工具鏈不用重裝。

### 10.14 天線焊點 450°C 化不開

**症狀：** 板上其他焊點一碰就化，天線那條線的焊點加熱到 450°C 只有一點點形變。

**原因：不是溫度，是熱容量。**

那個焊點的另一端接的是 **RF 接地銅箔** —— 整片地平面加上底下的過孔陣列，對烙鐵頭
來說就是一片散熱片。熱流進去的速度比流走的速度慢，焊點永遠停在 150–200°C。
面板顯示的 450 是**烙鐺尖端**的溫度，不是焊點的溫度。

一起在害你的還有：

- **細錐頭接觸面積太小**（約 1 mm²），傳熱功率正比於接觸面積
- **家用烙鐵沒有閉迴路溫控**，感溫在加熱棒不在尖端，一碰大銅面尖端就掉到 250°C 以下
- **450°C 反而更難焊** —— 助焊劑在你需要它工作之前就碳化燒光了
- 同軸線的網狀屏蔽層本身也是散熱片

熔點順帶釐清：有鉛 Sn63Pb37 是 **183°C**，無鉛 SAC305 是 **217–220°C**。
**兩個都遠低於 450，所以熔點從來不是問題。**

**解法：別拆。**

這個專案裡拆天線**不對應 G2 任何一格**，而且天線的同軸線終點是 RTL8188ER 的
輸出級 —— 拆掉之後通電等於讓功率放大器對著開路發射。這台機器是 G2 和 G4 的
單點故障，沒有第二台。

真的需要拆大焊點時，正確做法是**反直覺的：先「加錫」，不是先「吸錫」**——
換刀頭（2.5–3 mm）→ 塗助焊劑 → 灌一坨新的**有鉛**錫進去（合金熔點被拉低，
而且形成液態熱橋）→ 溫度回到 **350–370°C** → 大銅面從背面用熱風槍 180–200°C
預熱。**450°C 已經在燒板子了** —— 焊盤底下的膠 250°C 就開始軟化，撐夠久焊盤會
整片跟著烙鐵起來。

**要練拆焊，去找一塊報廢板，不要拿唯一的目標練。**

### 10.15 usbipd 裝好了，但 PowerShell 說找不到

**症狀：**

```
usbipd : The term 'usbipd' is not recognized as the name of a cmdlet ...
```

**原因：** 安裝程式改了系統 PATH，但**已經開著的終端機不會重新讀 PATH**。

**解法：** 關掉 PowerShell 重開。急著用的話直接給完整路徑：

```powershell
& "C:\Program Files\usbipd-win\usbipd.exe" list
```

先確認到底裝了沒，再決定是 PATH 問題還是安裝問題：

```powershell
winget list --exact --id dorssel.usbipd-win
```

```
Name       Id                 Version Source
---------------------------------------------
usbipd-win dorssel.usbipd-win 5.3.0   winget
```

### 10.16 `flashrom --version` 說 `unknown`

**症狀：**

```
$ flashrom --version
flashrom unknown on Linux 6.6.87.2-microsoft-standard-WSL2 (x86_64)
```

**原因：** Debian/Ubuntu 打包時沒把版本字串編進去。**不是壞掉**，功能完全正常。
套件管理員知道真正的版本：

```bash
dpkg -s flashrom | grep -i '^Version'
```

```
Version: 1.3.0-2.1ubuntu2
```

**這一條值得記下來的地方不是解法，是它戳破了一個規則。**
G0 的宣稱是「**每個工具都用『跑跑看』來驗證，不是檢查檔案在不在**」——
而 `flashrom` 是這張表裡**唯一一個版本號不是跑出來的**。功能上無所謂，
但 `PROGRESS.md` 的 G0 表應該說清楚那個 `1.3.0` 是哪裡來的，
而不是讓人以為做了一個其實沒做的檢查。

### 10.17 電壓量到 `0.x` 在跳，而且怎麼量都不對

**症狀：** 量 UART 腳位對地電壓，四支腳全部讀到 `0.多` 而且一直跳。

**原因：檔位。** 手動檔電表上，轉盤的數字是那一檔**能顯示的最大值**：

| 檔位 | 最大 | 量 3.3V |
|---|---|---|
| `200m` | **0.2 V** | ❌ 差 16 倍 |
| `2000m` / `2` | 2 V | ❌ |
| **`20`** | **20 V** | ✅ |

**這一條最危險的地方不是差 16 倍，是它不會報錯。** 停在 200mV 檔量 3.3V,
回給你的是一個會漂的 `0.x` —— 那個形狀跟一個真實的、有雜訊的低電壓讀數
一模一樣，你會去懷疑板子、懷疑探針、懷疑自己。

**解法：先量一顆已知的電池。**

```
V⎓ 20V 檔 → AA 電池 → 應該讀 1.5 左右
```

讀到了 → 表和檔位都好 → 問題一定在板子那側。
讀不到 → 先修表，板子的事全部往後排。

> **用已知量驗證儀器，再拿它去量未知量。**
> 這跟 §12 那條「先看 `self_check`，但 `self_check` 本身也會騙人」是同一件事。

### 10.18 電阻讀到孤零零一個 `1`

**那是「超出量程」，不是 1 歐姆。** 畫面左邊一個 `1`、後面沒有小數點和其他位數。

換高一檔（200 → 2k → 20k → 200k → 2M），看它在哪一檔進入量程。
**在哪一檔進入量程本身就是資訊** —— 訊號腳通常在 20k 檔顯示出 4.7k / 10k / 15k
之類的上拉電阻值。

順便一個免費的檢查：**這個讀數在物理上合不合理?**
訊號腳對地 1Ω 等於短路，那塊板不會動 —— 光憑這點就知道 `1` 不是 1Ω。

### 10.19 `usbipd attach` 說「沒有 WSL 2 發行版在跑」

**症狀：**

```
usbipd: error: There is no WSL 2 distribution running;
keep a command prompt to a WSL 2 distribution open to leave it running.
```

**原因：** `wsl -d Ubuntu-24.04 -- <指令>` 這種呼叫是跑完就結束的，
而 `attach` 需要發行版**持續開著**。

**解法：** 先把它釘住，再 attach。

```powershell
Start-Process -WindowStyle Hidden wsl -ArgumentList "-d","Ubuntu-24.04","--","sleep","7200"
usbipd attach --wsl --busid 1-1
```

或者直接開一個 WSL 視窗放著不要關。

另外：`bind` 需要**系統管理員**，`attach` 不用。

### 10.20 PulseView 打不開 fx2lafw 分析儀

**症狀：** 掃描找得到裝置，按 OK 之後 `Failed to open device / generic/unspecified error`。

**先排除三個最常見的**（這次三個都不是）：

```powershell
# 1. 驅動綁了沒?應該是 WinUSB
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like "USB\VID_0925*" }
# 2. 韌體檔在不在?
Get-ChildItem "C:\Program Files\sigrok" -Recurse -Filter "*.fw" | Select Name
# 3. 有沒有程式佔用?
Get-Process | Where-Object { $_.ProcessName -match "pulseview|Logic" }
```

**剩下最可能的原因：FX2 上傳韌體之後會用新的 VID/PID 重新列舉，而那個新 ID
沒有驅動。** Zadig 要做**兩次** —— 一次給上傳前的 ID，一次給上傳後的。

> ⚠️ **這一條在本專案裡沒有被證實。** 我改用 Saleae Logic 2 就通了
> （clone 的 VID/PID 就是 `0925:3881`，原廠軟體認得），所以上面那個原因是推論。
> **要證實的方法：讓 PulseView 跳錯之後不要拔線、不要關程式，那時去列舉 USB,
> 看有沒有冒出一個沒有驅動的新裝置。**

**而且分析儀不在關鍵路徑上** —— baud 在 console 上試四個值兩分鐘就有答案，
判準一樣硬（可讀 vs 亂碼）。不要為了工具卡住主線。

### 10.21 本機全綠，但 CI 還是紅的

**症狀：** push 之前跑過 `make lint test check-reports` 全過，GitHub Actions 還是失敗。

**原因：CI 有四個 job，你手動挑的那幾個目標蓋不到全部。**

| CI job | 本機等價 |
|---|---|
| `fwrecon (lint + tests)` | `make lint test` |
| **`shell scripts`** | **`shellcheck --severity=warning tools/*.sh tools/setup/*.sh`** |
| `toolchain image builds` | `docker build -f docker/Dockerfile .`（要幾分鐘） |
| `committed reports match the tooling` | `make check-reports` |

**解法：**

```bash
make ci        # 上面除了容器建置之外的全部
```

改到 `docker/` 底下的東西時再另外跑一次容器建置。

> **這一條真正的教訓不是「記得跑 shellcheck」。**
>
> 是**「知道該跑哪幾個」本身就不是一種檢查，那是一個遲早會忘的習慣**。
> 我 2026-08-15 那次就是靠記憶挑了兩個目標跑、以為綠了才 push。
>
> 修法不是下次更小心，是**讓「全部」變成一個指令** —— 所以有了 `make ci`。
> 這跟 W04 那條「一個永遠不會觸發的檢查也永遠不會失敗」是同一個形狀：
> **一個要靠人記得去跑的檢查，遲早不會被跑。**

實際踩到的那個警告是 `SC2164`（`cd` 沒有 `|| exit`），而它剛好是
`tools/test-photo-tools.sh` 存在的理由那一類 bug：**如果 `cd` 無聲失敗，
每個「這個一定要失敗」的測試都會因為「找不到檔案」而通過。**

---

## 11. 名詞表

| 名詞 | 白話解釋 |
|---|---|
| **韌體 firmware** | 硬體裡面那套作業系統 + 程式，打包成一個檔案 |
| **rootfs** | 根檔案系統，就是 Linux 的 `/` 那一整棵目錄樹 |
| **SquashFS** | 一種唯讀的壓縮檔案系統，嵌入式裝置最常用 |
| **ELF** | Linux 執行檔的格式（等同 Windows 的 `.exe`） |
| **MIPS** | 一種 CPU 架構，常見於路由器。跟你電腦的 x86 不相容 |
| **端序 endianness** | 多位元組數字在記憶體裡的排列方向。搞錯就全部讀成垃圾 |
| **Boa** | 一個超輕量網頁伺服器，2005 年就停止維護了 |
| **CVE** | 全球通用的漏洞編號，格式 `CVE-年-流水號` |
| **binwalk** | 掃描一個檔案裡藏了哪些已知格式的工具 |
| **Ghidra** | NSA 開源的反組譯工具，把機器碼還原成類 C 程式碼 |
| **符號連結 symlink** | 一個「指向別的檔案」的捷徑 |
| **sstrip** | 一種極限瘦身手法，把 ELF 的 section header 整個砍掉 |
| **JEDEC ID** | 快閃記憶體晶片被問到時**自己回報**的廠商碼+裝置碼。跟印在外殼上的字是**兩個獨立來源** |
| **日期碼 date code** | 印在晶片上的 `YYWW`（年+第幾週）。全板取最新的那顆，就是「組裝時間不早於」的下限 |
| **SOP-8 / mil** | 8 腳表面黏著封裝，有 150 mil 和 208 mil 兩種寬度。**夾具買錯寬度就夾不上去** |
| **磁性元件 magnetics** | RJ45 後面那幾顆黑方塊，乙太網路的隔離變壓器。數量可以反推有幾個網路埠 |
| **section header** | ELF 檔裡描述各區段的目錄。**砍掉程式照跑**，但分析工具會瞎掉 |
| **`system()`** | C 語言裡「執行一個 shell 指令」的函式。**命令注入漏洞的終點** |
| **NX / canary / RELRO / PIE** | 四種防止記憶體漏洞被利用的保護機制。**這台路由器一個都沒有** |
| **G0 / G1** | 本專案自訂的驗收關卡：G0 = 環境好了，G1 = 韌體看懂了 |
| **WSL** | Windows Subsystem for Linux,Windows 裡的真 Linux |
| **冪等 idempotent** | 同一個指令跑幾次結果都一樣，不會重複做或做壞 |

---

## 12. 一頁速查表

> 熟了之後只看這頁。

```bash
# ── 只做一次 ──────────────────────────────────────────
wsl --install -d Ubuntu-24.04                    # PowerShell (系統管理員)
powershell -ExecutionPolicy Bypass -File tools\setup\setup-windows.ps1 all
wsl -d Ubuntu-24.04 bash /mnt/c/.../tools/setup/setup-wsl.sh all

# ── 每次開工 ──────────────────────────────────────────
wsl -d Ubuntu-24.04
cd /mnt/c/Users/Key20/Desktop/router

# ── 主流程 ────────────────────────────────────────────
make verify        # G0:每個工具都真的跑跑看
make fetch         # 下載 + 驗雜湊         (~11 秒)
make unpack        # 解出根檔案系統        (~10 秒)
make recon         # 產生所有報告          (~10 秒)

# ── 檢查 ──────────────────────────────────────────────
make ci            # ★ push 之前跑這個 —— CI 的四個 job(容器建置除外)
make test          # 70 個測試
make lint          # 程式碼風格
make shellcheck    # shell 腳本
make check-reports # 報告有沒有跟工具脫節
make help          # 列出所有指令

# ── Ghidra(回到 PowerShell)────────────────────────────
$b='\\wsl$\Ubuntu-24.04\home\key\fwre-work\extracted\v2.1.2\squashfs-root\bin\boa'
.\ghidra\import.ps1 -Label 2.1.2 -Binary $b          # 匯入+自動分析,每支幾分鐘,只跑一次

.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaStringXrefs -Binary $b   # 字串 xref (W01)
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaFormTable   -Binary $b   # root_form[] + 命名 handler
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaSinks       -Binary $b   # 危險函式呼叫點普查
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaDecompile   -Binary $b `
    -Out "$PWD\ghidra\decomp\d.json" -ExtraArgs @('prefix:form_','name:handleForm')
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaListing     -Binary $b -ReadOnly `
    -Out "$PWD\ghidra\decomp\l.txt"  -ExtraArgs @('0040be0c','0040c600')   # 組語

# ── W04 新增的兩支 ────────────────────────────────────
# 誰呼叫我、我呼叫誰、我碰到哪些字串;refs: 用來問「這個全域是誰寫、誰讀」
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaXref -Binary $b `
    -ExtraArgs @('name:process_header_end','refs:0049087c','depth:3')

# 每個 sink 呼叫點的「每個參數到底是什麼」:字面字串 / 堆疊位置+框架大小 /
# 全域 / **請求參數的名字**。accessor: 只有在 binary 被 strip 掉時才需要給。
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaArgTrace -Binary $b `
    -ExtraArgs @('sink:system','sink:strcpy','sink:sprintf','in:form_',
                 'accessor:req_get_cstream_var','depth:6')
# 2020 版的 accessor 名字不一樣(符號被 strip 了):accessor:FUN_0040e9e0

# ── W02 硬體 ──────────────────────────────────────────
flashrom -L | grep -i en25qh          # 這顆 flash 認不認得(4096 KiB = 4 MiB)
usbipd list                            # 工具插上去有沒有被 Windows 看到

PY=~/fwre-work/venv/bin/python         # 這兩支要 Pillow,裝在專案 venv 裡
$PY tools/redact-photo.py   <原圖> <輸出> --expect-size 2048x1536 --box X,Y,W,H
$PY tools/annotate-photo.py notes/img/pcb-top-annotations.json <輸出>
bash tools/test-photo-tools.sh         # 這兩支的自我測試(13 項,含對照組)

# ── W02 序列 console ──────────────────────────────────
# PowerShell:bind 要管理員,attach 之前 WSL 必須在跑
Start-Process -WindowStyle Hidden wsl -ArgumentList "-d","Ubuntu-24.04","--","sleep","7200"
usbipd bind --busid 1-1 ; usbipd attach --wsl --busid 1-1

sudo usermod -aG dialout $USER; sudo chmod 666 /dev/ttyUSB0
stty -F /dev/ttyUSB0 38400 cs8 -cstopb -parenb raw -echo
timeout 90 cat /dev/ttyUSB0 > ~/fwre-work/dumps/uart-boot.log   # 先跑,再開電源

# 搶 bootloader:ESC 要在上電之前就開始送
END=$((SECONDS+20)); while [ $SECONDS -lt $END ]; do printf '\033' > /dev/ttyUSB0; sleep 0.03; done

# bootloader 讀 flash(? 才是 help,HELP 不是)
#   FLR <RAM> <flash> <len>   三個都十六進位,然後一定要送 Y
#   DB  <RAM> <len>           位址十六進位,長度十進位 ← 兩種進位,會害人

# ── W02 Day 4:自動化 dump(§8.7.9)──────────────────
python3 -u tools/console-dump.py catch --port /dev/ttyUSB0 --window 300
#   ↑ 看到 POWER THE ROUTER ON NOW 之後才上電;ESC 整段時間都在送,不用趕
python3 -u tools/console-dump.py dump --at-prompt --flash 0x060000 \
        --length 0x10000 -o ~/fwre-work/dumps/pilot.bin        # 先試跑
setsid nohup python3 -u tools/console-dump.py dump --at-prompt \
        --flash 0x0 --length 0x400000 --chunk 16384 --verify-sample 0.05 \
        -o ~/fwre-work/dumps/flash-n150rt-console-1.bin \
        > ~/fwre-work/dumps/console-dump.log 2>&1 < /dev/null & # ~95 分鐘
python -m fwrecon flashdump ~/fwre-work/dumps/flash-n150rt-console-1.bin
bash tools/test-console-dump.sh        # 解析器的守衛套件(不需要硬體)
bash tools/test-flash-tools.sh         # flash-read.sh 的篩檢守衛(不需要硬體)
#   搶到 bootloader 之後第一條指令一定失敗:ESC 塞在它的輸入緩衝區裡
#   速率 723 B/s 是線的物理上限(5.06 倍膨脹),調程式沒有用

# ── 單獨用工具 ────────────────────────────────────────
~/fwre-work/venv/bin/python -m fwrecon image  <韌體.web>
~/fwre-work/venv/bin/python -m fwrecon elf    <執行檔>
~/fwre-work/venv/bin/python -m fwrecon rootfs <解開的目錄>
~/fwre-work/venv/bin/python -m fwrecon mib    <libapmib.so>
~/fwre-work/venv/bin/python -m fwrecon web    <韌體.web> [--at 0x010000] [--grep 字串]
#   ↑ 出貨的網頁本體。self_check 不是 exact 就不要用它的數字
#     --grep 是逐筆搜「內容」;用整塊 grep 會找到不存在的檔名(§8.8.5)

# ── 廠商 zip:驗 CRC,必要時取殘檔(§8.8.4)────────────
cat "<檔名>.zip:Zone.Identifier"                 # 下載來源,OS 寫的,不是回憶
python3 tools/zipprefix.py <檔名>.zip            # 讀 header + 驗 CRC-32
python3 tools/zipprefix.py <檔名>.zip -o out.bin --allow-partial
#   CRC 沒過就拒絕寫;--allow-partial 只解除「不准寫」,exit code 照樣非 0
#   重抓 V2.1.6 的成功判準:CRC-32 要等於 0xd20c0622

# ── W05 測試登記簿(§8.10)─────────────────────────
make todo WEEK=W05                               # 這週還欠哪幾項(每天第一條)
make rtcase                                      # gate:凍結 + 每筆結果都有證據
make rtcase-test                                 # 對照:證明這個 gate 擋得住東西
make ledger                                      # 重生成 test-ledger.md
python3 tools/rtcase.py record --id P3-3 --date 2026-08-20 \
    --verdict confirmed --evidence dynamic --artefact poc/formSysCmd/README.md
python3 tools/rtcase.py freeze                   # 改過預測之後,把新雜湊貼回登記簿
#   --evidence dynamic 才會印 ✅;static 印 🟥;emulated 印 🟪
#   真的對這台送過封包才叫 dynamic。在 qemu 裡跑起來的叫 emulated
#   沒寫反證條件的項目,record 會直接拒絕 —— 這是刻意的

# ── W05 模擬環境:這台自己的韌體 + 這顆 flash 的副本(§8.11)──
sudo make qemu-env                               # 建環境(~30 秒),結尾自動跑陽性對照
sudo bash tools/qemu-env.sh check                # 三個已知值 + MIB 行數
sudo bash tools/qemu-env.sh reset                # ★ 每次量測前:檔案 **和** shm 一起
sudo bash tools/qemu-env.sh run /bin/flash get TELNET_ENABLED
sudo bash tools/qemu-env.sh run /bin/sh -c \
     'flash set HW_WLAN0_WSC_PIN 1;ls -l / > /var/web/x.txt 2>&1;#'
sudo bash tools/qemu-env.sh diff                 # 改了哪幾個 byte,校驗和平不平
make qemu-test                                   # 守衛套件(不需 root 的那半也會跑)
#   ⚠️ 只 cp 回 /dev/mtdblock0 不算復原 —— MIB 表快取在主機的 SysV 共享記憶體裡

# ── W05 網路那一輪(§8.11.6)──────────────────────
python3 tools/bench-probe.py control     --host 10.1.1.1
python3 tools/bench-probe.py fingerprint --host 10.1.1.1 -o ~/fwre-work/dumps/w05-fp.json
python3 tools/bench-probe.py gate        --host 10.1.1.1 -o ~/fwre-work/dumps/w05-gate.json
python3 tools/bench-probe.py endpoints   --host 10.1.1.1 -o ~/fwre-work/dumps/w05-ep.json
python3 tools/bench-probe.py ssdp        --host 10.1.1.1 -o ~/fwre-work/dumps/w05-ssdp.json
make probe-test                                  # 8 個案例,不需要裝置
#   endpoints 預設 GET。--allow-post 會真的執行 handler,前後各抓一次 64 KiB 快照
```

> ⚠️ **看報告先看 `self_check`，但不要只看 `self_check`。**
> W04 的 `BoaArgTrace` 連續錯了三次，三次 `self_check` 都寫 `consistent`。
> 抓到它的不是自我檢查，是**把兩版並排比**：同一份程式碼相隔五年，不可能
> 2015 版有 86 個受污染的呼叫點、2020 版有 0 個。
> **一個永遠不會觸發的檢查，也永遠不會失敗。**

**重要路徑**

| 東西 | 在哪 |
|---|---|
| 專案（文字檔） | `C:\Users\Key20\Desktop\router` |
| 工作資料（二進位） | `~/fwre-work`（WSL 內） |
| 從 Windows 看工作資料 | `\\wsl$\Ubuntu-24.04\home\key\fwre-work` |
| Ghidra | `%LOCALAPPDATA%\fwre-tools\ghidra_12.1.2_PUBLIC` |
| Ghidra 專案 | `%LOCALAPPDATA%\fwre-tools\ghidra-projects` |

---

## 12.5 下一階段開工前要先裝的東西

> W01 **沒有**裝這些，是刻意的 —— 理由寫在 [`PROGRESS.md`](PROGRESS.md) 的
> 「Deliberately not done in W01」。
> **開始 W02 / W05 之前先回來看這節。**

### W02（硬體）開工前

> ✅ **2026-08-14 已完成**（`usbipd-win 5.3.0`）。實際做完的第一天寫在
> [§8.6](#86-part-6--硬體開工料件辨識w02-day-1)。裝完找不到指令是正常的，
> 見 [§10.15](#1015-usbipd-裝好了但-powershell-說找不到)。

零件到貨那天，一次做完：

```powershell
# PowerShell(系統管理員)—— 把 USB 裝置接進 WSL 用
winget install --interactive --exact dorssel.usbipd-win
```

裝完**重開 PowerShell**，確認：

```powershell
usbipd list
```

會列出你插著的 USB 裝置。之後把 USB-TTL 轉接板接給 WSL 的流程是：

```powershell
usbipd list                      # 找到轉接板的 BUSID,例如 2-4
usbipd bind   --busid 2-4        # 只要做一次(需要管理員)
usbipd attach --wsl --busid 2-4  # 每次插拔都要做
```

然後在 WSL 裡：

```bash
ls /dev/ttyUSB*                  # 應該出現 /dev/ttyUSB0
picocom -b 115200 /dev/ttyUSB0   # 常見鮑率:115200 或 57600
```

> 離開 picocom 是 **Ctrl-A 然後 Ctrl-X**。

> ⚠️ **接線前務必先確認電壓是 3.3V，不是 5V。** 接錯會燒掉路由器的 SoC。
> 轉接板上通常有跳線或切換開關。**用三用電表量過再接。**

### W05（動態分析）開工前

**先試輕量的路** —— 工具已經裝好了，不用額外安裝。**W01 收工時實測過，可以動：**

```bash
R=~/fwre-work/extracted/v2.1.2/squashfs-root
sudo cp /usr/bin/qemu-mips-static "$R/"
sudo chroot "$R" /qemu-mips-static /bin/busybox
sudo chroot "$R" /qemu-mips-static /bin/boa --help
```

實際輸出：

```
BusyBox v1.13.4 (2015-08-11 17:26:34 CST) multi-call binary
Copyright (C) 1998-2008 Erik Andersen, Rob Landley, Denys Vlasenko
and others. Licensed under GPLv2.

Usage: busybox [function] [arguments]...
```

```
/bin/boa: invalid option -- -
Usage: /bin/boa [-c serverroot] [-d] [-f configfile] [-r chroot] [-l debug_level]
  To calculate the debug level, logically 'or'
  some of the following values together to get a debug level:
	1:	Alias
	2:	CGI Output
	4:	CGI Input
	8:	CGI Environment
...
```

**這代表 2015 年的 MIPS 執行檔可以在你的 x86 電腦上直接跑。** `boa` 吐出了自己
真正的用法說明，包含 `-c serverroot` 和 `-f configfile` —— 這正是之後要餵它設定檔
把 web 伺服器整個拉起來的入口。

> `qemu-mips-static` 是**大端序** MIPS 用的（`qemu-mipsel-static` 是小端序）。
> 這台機器是大端序，所以用前者 —— 見 [§9 G1 第 3 題](#9-驗收)。
> 用錯的那個會直接說 `Invalid ELF image`。

> ⚠️ 「能啟動」不等於「能完整跑」。`boa` 真的服務請求時會去呼叫 `libapmib.so`，
> 而 apmib 會直接讀快閃記憶體分割區（`/dev/mtd*`），那在 chroot 裡不存在。
> 到時候可能要偽造那些節點，或用 `LD_PRELOAD` 攔掉。**這是 W05 要解的問題，
> 不是現在。**

跑不動再考慮 FirmAE（**全系統模擬**，連 Linux 核心一起跑）：

```bash
cd ~ && git clone https://github.com/pr0v3rbs/FirmAE
cd FirmAE && ./install.sh      # 30–60 分鐘
```

---

## 13. 怎麼維護這份文件

**規則：每完成一段新工作，回來更新這份文件，而且要在同一個 commit 裡。**

### 什麼時候一定要更新

| 情況 | 要改哪裡 |
|---|---|
| 加了新的 `make` 目標 | §12 速查表 + 對應的 Part 章節 |
| 加了新工具 / 改版本 | §4 環境建置 + §2 空間需求 |
| 踩到新的坑並解決了 | **§10 疑難排解**（這節最有價值） |
| 進入新的週次（W02、W03…） | 新增一個 Part 章節 |
| 有指令的輸出變了 | 把「應該看到」的區塊更新成真實輸出 |
| 出現新名詞 | §11 名詞表 |

### 三條鐵則

1. **只寫你真的跑過的東西。** 「應該看到」區塊必須是**貼上來的真實輸出**，不是憑印象打的。這份文件的價值全繫於此 —— 一旦有一段是編的，讀者就再也不能信任其他段落。

2. **每個步驟都要有「怎麼知道成功了」。** 只寫指令不寫預期輸出，等於沒寫。

3. **失敗案例跟成功案例一樣重要。** §10 的每一條都省下讀者一小時。踩到新坑就補一條，格式是：**症狀 → 原因 → 解法**。

### 自我檢查

改完之後問自己：

- [ ] 三個月後的我照著打，會不會卡住?
- [ ] 一個沒碰過逆向的人讀到這裡，會不會有名詞看不懂又查不到?
- [ ] 每個指令都有「應該看到什麼」嗎?
- [ ] §14 變更紀錄補了嗎?

---

## 14. 變更紀錄

| 日期 | 週次 | 改了什麼 |
|---|---|---|
| 2026-08-07 | W01 | 初版。涵蓋環境建置、韌體取得、解包、`fwrecon` 報告、Ghidra headless 分析，以及 W01 實際踩到的 13 個坑。 |
| 2026-08-07 | W01 收工 | 新增 §12.5：W02 / W05 開工前要補裝的東西（usbipd、UART 3.3V 警告、qemu chroot 先於 FirmAE）。這三項 W01 刻意沒做，理由記在 `PROGRESS.md`。 |
| 2026-08-07 | W01 收工 | 新增 [`study/QA.md`](study/QA.md) 自我檢核題庫（39 題）。之後每週的問題都往那裡累積。 |
| 2026-08-10 | W03 | §8 改寫：`import.ps1`（匯入+分析）與 `analyze.ps1`（跑腳本）拆開，並加上 `-Label` 為什麼要當資料夾用的說明 —— W01 的寫法會讓第二次匯入無聲蓋掉第一次。 |
| 2026-08-10 | W03 | 新增 §8.5 Part 5：用 `BoaDecompile` 匯出 C、用 `BoaListing` 讀組語，以及「反編譯器出警告時不能信它」的操作方式。 |
| 2026-08-10 | W03 | §12 速查表補上 W03 的四支腳本。`study/QA.md` 增至 60 題。 |
| 2026-08-11 | W04 | §12 速查表補上 `BoaXref`、`BoaArgTrace`、`fwrecon mib`，以及「先看 `self_check`，但 `self_check` 本身也會騙人」這條。 |
| 2026-08-11 | W04 | `study/QA.md` 新增 §8（W04）：2020 版授權、`submit-url`、後門帳號、MIB 表，以及三個工具 bug 的自白。 |
| 2026-08-14 | W02 Day 1 | 新增 §8.6 Part 6：硬體到貨後的第一天 —— 順序為什麼要跟著「可逆程度」走、五顆 IC 的絲印、`flashrom` 相容性（附實際輸出）、`usbipd` 確認（附實際輸出）、找到已焊好的 UART 排針，以及**照片進 repo 前的遮蔽規則**。 |
| 2026-08-14 | W02 Day 1 | §10 新增三條真的踩到的坑：**10.14 天線焊點 450°C 化不開**（熱容量 ≠ 溫度，而且本來就不該拆）、**10.15 usbipd 裝好卻找不到**、**10.16 `flashrom --version` 說 `unknown`**（它戳破了 G0「每個工具都是跑出來的」這句話）。 |
| 2026-08-14 | W02 Day 1 | §11 名詞表新增 JEDEC ID、日期碼、SOP-8/mil、磁性元件；§12.5 的 W02 前置作業標記完成。 |
| 2026-08-14 | W02 Day 1 | 新增 §8.6.9：照片的遮蔽與標註全部走腳本（`tools/redact-photo.py`、`tools/annotate-photo.py`），理由跟 W03 不用 Ghidra 截圖一樣。§12 速查表補上這兩支和 `flashrom -L` / `usbipd list`。**兩支工具第一次跑都是錯的，而且都不是自己抓到的** —— 經過寫在 `LOG.md`。 |
| 2026-08-15 | W02 Day 2–3 | 新增 §8.7 Part 7：量腳位（**先驗表再量板**）、量 baud（26µs，以及 52µs=2×26 的自洽檢查）、`usbipd` + `/dev/ttyUSB0`、抓 bootlog、確認 console **沒有 shell**、用 ESC 搶 bootloader、以及 **`FLR`+`DB` 這條不用夾具的 flash 讀取路徑**。全部附實際輸出。 |
| 2026-08-15 | W02 Day 2–3 | §10 新增四條：**10.17 200mV 檔量 3.3V 不會報錯，只會給你一個看起來像真的數字**（解法是先量電池）、10.18 孤零零一個 `1` 是超量程、10.19 `usbipd attach` 需要 WSL 正在跑、10.20 PulseView 打不開 fx2lafw（**這條沒有被證實，如實標註**）。 |
| 2026-08-15 | W02 Day 2–3 | §12 速查表新增序列 console 全流程，含 **`FLR` 十六進位 / `DB` 十進位**這個會安靜產生錯誤資料的坑。`study/QA.md` 新增 §10。 |
| 2026-08-15 | 收工後 | 新增 **`make ci`**（§9、§12）和 §10.21。起因是本機跑了 `make lint test check-reports` 全綠就 push,CI 還是紅的 —— **CI 有四個 job，靠記憶挑目標跑不是檢查，是遲早會忘的習慣。** |
| 2026-08-16 | W02 Day 4 | 新增 §8.7.9：完整 4 MiB dump 走 `tools/console-dump.py`（陽性對照、逐塊驗證、抽驗重讀、拼不完整就不吐檔案）。附兩個當天踩到的坑：**ESC 會塞住 bootloader 的輸入緩衝區，搶到之後第一條指令必定失敗**；以及**不要照 `notes/` 的引用寫解析器 —— §8.7.8 這裡的 transcript 才是逐字的**。 |
| 2026-08-16 | W02 Day 4 | §12 速查表新增 W02 Day 4 全流程與兩支不需要硬體的守衛套件。CH341A 量出來是未改的 5V 板（CS/CLK/DI 全 5V，只有座上 VCC 是 3.3V），3.3V 魔改後仍是 5V、**原因未隔離**，決定改走零風險的 console 路 —— 經過寫在 `LOG.md`。 |
| 2026-08-17 | W05 Day 0 | 新增 **§8.10 測試登記簿**（G3.75）：`rtcase check / record / render` 三個指令、反證條件怎麼寫（好例 vs 壞例）、改預測要同一個 commit 重算雜湊、紀錄卡格式、六個會踩到的坑。**這一列是跟§8.10 同一個 commit 寫的** —— W04-2 就是在新增 §8.8/§8.9 的那個 commit 裡漏了這張表。 |
| 2026-08-17 | W05 Day 0 | §9 驗收新增 G3.75；§12 速查表新增 `make rtcase` / `make ledger` / `make rtcase-test`。`study/QA.md` 新增 §13。 |
| 2026-08-16 | W04-2 | 新增 §8.8：把這台自己的 `boa` 讀進 Ghidra 跑五種量測、解碼 `COMPCS`/`COMPDS`、以及 `BoaGate` 為什麼一定要帶 `control:`。 |
| 2026-08-16 | W04-2 | 新增 §8.9：G3.5 最後一格 `FLW` 回復路徑演練的逐字步驟，含三條保護措施。**這一格還沒做。** |
| 2026-08-16 | W04-2 補課 | 新增 §8.8.4：廠商映像重抓、從 `Zone.Identifier` 讀 provenance、`tools/zipprefix.py`，以及一份 40% 殘檔**撐得到哪裡**（兩個 section 完整，截斷的是 rootfs）。§12 速查表補上 `zipprefix`。 |
| 2026-08-16 | W04-2 補課 | 新增 §8.8.5：`fwrecon web` —— 把 W01 留下的 `w6cg` 格式做完（64B header，長度欄在 `+0x3c` 且是 big-endian）。§12 速查表補上。兩個坑寫在該節：**`self_check` 不是 `exact` 就不要用它的數字**；以及 **`--grep` 逐筆搜內容，不是搜整塊** —— 用整塊 grep 會在 2018 那份裡「找到」一個不存在的 `syscmd.htm`。 |
| 2026-08-16 | W04-2 補課 | `make lint` 與 CI 補掃 `tools/*.py`。**那幾支獨立腳本一直不在任何 lint 範圍內** —— 它們不在 `fwrecon` 套件裡，ruff 往上找設定檔永遠找不到 `tools/fwrecon/pyproject.toml`，所以是用預設規則掃的，等於幾乎沒掃。改成用 `--config` 指同一份設定（不另開一份會漂移的），掃出 `console-dump.py` 一個 `B007`，已修。 |
| 2026-08-17 | W05 | **§8.9 從「還沒做」改成已執行**，補上 §8.9.1 逐字 transcript、§8.9.2 **本節被實測推翻的四處**（回應字樣不是 `Flash Write Successed!` 是一個句點；`FLW` 的 Y 提示與 `FLR` 標點不同；`EB` 一次吃多個 byte 已證；「寫 FF 抹回去」會成功但理由跟文件想的不一樣），以及 §8.9.3 **未結的 `FLW` 磁區語意**。 |
| 2026-08-17 | W05 | 新增 **§8.11**：qemu-user + 真 flash 當 `/dev/mtdblock0`。含 §8.11.3 **「復原檔案不等於復原狀態」** —— MIB 表快取在主機的 System V 共享記憶體裡，`cp` 回裝置檔碰不到它。這一坑是一次量錯的結果，不是推理出來的。 |
| 2026-08-17 | W05 | §8.11.5：登記簿新增第三種證據等級 **`emulated`（🟪，永遠不會變成 ✅）**。`tools/test-rtcase.sh` 22 → 27 個案例。順帶修掉圖例用左欄長度索引右欄的潛伏 bug —— 第七個結果標記會被靜靜丟掉，而那正好是新加的這一個。 |
| 2026-08-17 | W05 | §8.11.6：`tools/bench-probe.py` + 8 個案例的守衛套件。**它存在的理由是一個無聲的失敗模式**：POST 少帶 `submit-url` 會打掛 boa，而之後每個端點都長得像「不存在」。 |
| 2026-08-17 | W05 | §12 速查表新增 `make qemu-env` / `qemu-test` / `probe-test`;`make ci` 從 6 個目標變 8 個。作業單與紀錄卡在 [`BENCH-LOG.md`](BENCH-LOG.md)（**新檔，它擁有的是「這一場照什麼順序做」，規程仍然歸 §8.9**）。`study/QA.md` 新增 §14。 |
| 2026-08-17 | W05 Phase 3 | §8.11.6 補上實測：`bench-probe` 的對照組現在也判「**是不是真的直連在這個網段上**」（從 `/proc/net/route`），因為 `ping` 成功而 `ttl=63` 這件事在 HTTP 回應裡完全看不見。守衛套件 8 → 9 個案例，**新的那個第一次跑就抓到實作是錯的**（`/proc/net/route` 只有 main 表，loopback 掉進預設路由）。 |
| 2026-08-17 | W05 Phase 3 | 作業單 [`BENCH-LOG.md`](BENCH-LOG.md) 補 §3.-1（重開機**之前**要先做完的三件事）與 §3.R1–R7（Phase 3 的逐項實測結果）。介面名寫死 `eth1` 全部改掉 —— WSL 用 MAC 衍生的可預測命名。 |
| 2026-08-17 | W05 收工重構 | 新增 **§8.12 實機場次：可組合的程序庫**（0–9），以及 **§8.9.4 改良後的 `FLW` 步驟**。起因是當天建的 `study/W05-bench-runsheet.md` 長成 1,091 行、裝了五種東西，其中約 580 行是跨週可重用的規程 —— **再為 W06 開一份就是同一份狀態兩個擁有者**。規程進 §8.12，實際跑了什麼進根目錄的 [`BENCH-LOG.md`](BENCH-LOG.md)（只追加），舊檔刪除。規則寫進 `CLAUDE.md`。 |

> **上面三列裡的前兩列是補登的，而漏登的方式值得記一筆。** §8.8 和 §8.9 是
> 2026-08-16 的「document sync」commit 加進這份文件的，那個 commit **改了
> RUNBOOK 卻沒有回頭補這張表**；接著又落了兩個 commit 的真工作，兩個都沒有
> 再同步 RUNBOOK 和 `LOG.md`。
>
> 病因不是忘記，是**把「document sync」當成一週過一次的關卡，而不是隨時要
> 成立的狀態**。§13 那條規則（「每完成一段新工作，回來更新這份文件，而且要在
> 同一個 commit 裡」）存在的理由就是防這個，而它在規則本身被重寫進 `CLAUDE.md`
> 的同一週失效了。§13 的自我檢查清單最後一項是「§14 變更紀錄補了嗎?」——
> 那一項當天沒有被執行。

---

## 接下來

| 文件 | 內容 |
|---|---|
| [`README.md`](README.md) | 專案總覽與主要發現 |
| [`PROGRESS.md`](PROGRESS.md) | 每週關卡進度 |
| [`LOG.md`](LOG.md) | 逐日工作紀錄，**包含所有走錯的路** |
| [`notes/anatomy-n150rt.md`](notes/anatomy-n150rt.md) | 韌體結構完整解剖 |
| [`notes/prior-art.md`](notes/prior-art.md) | 前人研究：誰在什麼時候發現了什麼 |
| [`notes/attack-surface.md`](notes/attack-surface.md) | 攻擊面地圖 |
| [`notes/ghidra-triage.md`](notes/ghidra-triage.md) | Ghidra 裡該先看哪些函式 |
| [`notes/dispatch-table.md`](notes/dispatch-table.md) | **`root_form[]` 全表** —— 兩個版本的每一個 `/boafrm/` 路由 |
| [`notes/auth-flow.md`](notes/auth-flow.md) | **Boa 怎麼決定你可不可以進來** —— W03 最重要的一份 |
| [`notes/sink-inventory.md`](notes/sink-inventory.md) | 危險函式呼叫點清單，依可利用性排序 |
| [`notes/formSysCmd-analysis.md`](notes/formSysCmd-analysis.md) | 那個不存在的 CVE 端點，以及三條線索為什麼都指錯方向 |
| [`notes/skt-analysis.md`](notes/skt-analysis.md) | 2015 後門完整拆解：port、暗號、和它存在的那一行 `iptables` |
| [`study/QA.md`](study/QA.md) | **自我檢核題庫** —— 每一條主張配一個「想推翻它的人會怎麼問」，答案是折疊的 |
