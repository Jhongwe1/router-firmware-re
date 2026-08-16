# RUNBOOK — 從零開始跑完一次

> **這份文件的讀者是兩種人:**
> 1. 三個月後把一切都忘光的我自己
> 2. 完全沒碰過逆向工程的人(高中生程度)
>
> 所以每一步都有:**要打什麼指令 → 應該看到什麼 → 沒看到怎麼辦**。
> 看不懂的名詞先跳過,[§11 名詞表](#11-名詞表)有解釋。
>
> **維護規則:每次做完新的一段工作,都要回來更新這份文件。**
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
| [8.5](#85-part-5--讀出授權流程w03) | **Part 5** — 讀出授權流程(W03) | 讀 20 分鐘 |
| [8.6](#86-part-6--硬體開工料件辨識w02-day-1) | **Part 6** — 硬體開工:料件辨識(W02 Day 1) | 2–3 小時 |
| [8.7](#87-part-7--序列-console-與-flash-讀取w02-day-23) | **Part 7** — 序列 console 與 flash 讀取(W02 Day 2–3) | 3–4 小時 |
| [9](#9-驗收) | 驗收:G0 與 G1 | 10 分鐘 |
| [10](#10-疑難排解) | 疑難排解 | 出事再看 |
| [11](#11-名詞表) | 名詞表 | 查閱 |
| [12](#12-一頁速查表) | 一頁速查表 | 熟了之後只看這頁 |
| [12.5](#125-下一階段開工前要先裝的東西) | **W02 / W05 開工前要補裝的東西** | 開新階段前必看 |
| [13](#13-怎麼維護這份文件) | 怎麼維護這份文件 | 讀 2 分鐘 |
| [14](#14-變更紀錄) | 變更紀錄 | — |

---

## 1. 你會得到什麼

跑完之後,你手上會有:

1. **一台路由器的韌體被完整拆開** —— 從一個 3.4 MB 的 `.web` 檔,變成 165 個檔案的完整 Linux 檔案系統
2. **兩個版本的對照**(2015 年 vs 2020 年),可以看出廠商在漏洞被公開後到底改了什麼
3. **一份自動產生的分析報告**,列出所有網頁端點、所有會執行系統指令的程式、所有可疑的檔案連結
4. **Ghidra 裡的反組譯專案**,以及一份「該從哪個函式開始看」的清單

全部都是**指令跑出來的**,不需要你手動點來點去。

---

## 2. 開始前的準備

### 你需要

| 項目 | 需求 | 怎麼確認 |
|---|---|---|
| 作業系統 | Windows 10/11(64 位元) | 開始鍵 → 設定 → 系統 → 關於 |
| 硬碟空間 | **至少 5 GB** | 檔案總管看 C 槽 |
| 記憶體 | 8 GB 以上 | 工作管理員 → 效能 |
| 網路 | 要下載約 1 GB | — |
| 權限 | **不需要管理員** | 這是刻意設計的,見 §10.1 |

實際佔用(我這台實測):

```
WSL 端    ~136 MB(韌體 6.6 MB + 解包後 21 MB + Python 環境 108 MB)
          + apt 套件約 500 MB
Windows 端 JDK 328 MB + Ghidra 872 MB + 下載快取 742 MB(事後可刪)
```

### 為什麼要用 WSL

WSL = Windows Subsystem for Linux,讓你在 Windows 裡跑一個真的 Linux。

**逆向 Linux 韌體必須在 Linux 上做。** 韌體裡有符號連結(symlink)、有 Unix 權限位元,Windows 的檔案系統存不下這些東西 —— 存不下就等於**資料會悄悄消失,而且不會報錯**。這個專案最重要的一個發現(`/web/config.dat` 是個符號連結)在 Windows 上解包會直接看不到。

詳見 [`docs/workspace-layout.md`](docs/workspace-layout.md)。

---

## 3. 五分鐘概念補課

> 已經懂的人直接跳到 [§4](#4-part-0--環境建置)。

### 韌體(firmware)是什麼

路由器裡面其實是一台小電腦,它也要跑作業系統。那個作業系統 + 所有程式打包成一個檔案,就叫**韌體**。你在官網下載的 `.web` 檔就是它。

### 這個 `.web` 檔裡面有什麼

不是壓縮檔,是**好幾塊東西黏在一起**,每塊前面有 16 個位元組的標頭說明「我是什麼、我要被燒到快閃記憶體的哪個位置」。

```
┌──────────┬────────────────────────────────────────┐
│ 標頭 16B │ 網頁介面資料 (bzip2 壓縮)              │  ← 只有 2015 版有
├──────────┼────────────────────────────────────────┤
│ 標頭 16B │ Linux 核心 (LZMA 壓縮)                 │
├──────────┼────────────────────────────────────────┤
│ 標頭 16B │ 根檔案系統 (SquashFS)   ← 我們主要要的 │
└──────────┴────────────────────────────────────────┘
```

這個格式是我們**自己逆出來的**,沒有官方文件。`fwrecon` 就是照這個格式寫的解析器。

### 根檔案系統(rootfs)

就是 Linux 的 `/` 目錄 —— `/bin`、`/etc`、`/lib` 那一整套。用 **SquashFS** 格式壓起來,唯讀。

解開後你會看到:

```
bin/  dev/  etc/  home/  lib/  mnt/  proc/  sys/  tmp/  usr/  var/  web/
```

跟一般 Linux 一模一樣,只是小很多。

### MIPS 和「端序」

你的電腦是 **x86** 架構,這台路由器是 **MIPS** 架構 —— 指令集完全不同,所以路由器裡的程式**不能**在你電腦上直接執行。

**端序(endianness)**是指多位元組數字的排列方向。數字 `0x12345678` 存進記憶體:

```
大端序 Big Endian    : 12 34 56 78   ← 這台路由器是這個
小端序 Little Endian : 78 56 34 12   ← 你的 x86 電腦是這個
```

搞錯端序的話,反組譯出來會是一堆垃圾。所以這是一開始就要先確定的事。

### Boa 是什麼

`/bin/boa` 是這台路由器的**網頁伺服器** —— 你在瀏覽器打 `192.168.1.1` 進去看到的設定頁面,就是它吐出來的。

它是 2005 年就停止維護的老軟體(版本 `0.94.14rc21`),而且**用 root 身分執行**。這代表它只要有一個漏洞,攻擊者就直接拿到最高權限,沒有第二道關卡。

### CVE 是什麼

**CVE = 公開漏洞編號**。全世界共用的漏洞編號系統,格式 `CVE-年份-流水號`。

這個專案研究的是**已經公開、已經修好**的舊漏洞 —— 目的是學習「漏洞長什麼樣、為什麼會發生」,不是攻擊別人的設備。

> ⚠️ **法律與道德底線**
> - 只拆**自己買的**硬體
> - 只在**隔離網路**測試,不連上線設備
> - 不碰 ISP 的機器(中華電信的數據機不是你的)
> - 真的找到新漏洞 → 走 TWCERT/CC 責任揭露,不公開

---

## 4. Part 0 — 環境建置

> ⏱ 30–45 分鐘,大部分時間在等下載。
> 這一段**只要做一次**,之後都不用重跑。

### 4.1 安裝 WSL(如果還沒有)

按 **開始鍵 → 打 `PowerShell` → 右鍵 → 以系統管理員身分執行**,然後:

```powershell
wsl --install -d Ubuntu-24.04
```

> 這是整個流程**唯一**需要管理員權限的一步,而且只有第一次要。

裝完會要你**重開機**。重開後 Ubuntu 會自己跳出來,叫你設一組 Linux 的使用者名稱和密碼。

> 💡 這個密碼跟你的 Windows 密碼無關,是 Linux 內部用的。**記起來**,後面 `sudo` 會用到。

**確認裝好了:**

```powershell
wsl --list --verbose
```

應該看到:

```
  NAME            STATE           VERSION
* Ubuntu-24.04    Running         2
```

`VERSION` 一定要是 **2**。是 1 的話跑 `wsl --set-version Ubuntu-24.04 2`。

### 4.2 取得這個專案

在 **一般的**(不用管理員)PowerShell 裡:

```powershell
cd $env:USERPROFILE\Desktop
git clone https://github.com/Jhongwe1/router-firmware-re.git router
cd router
```

沒有 git 的話:`winget install Git.Git`,然後**關掉 PowerShell 重開**。

> 📌 **之後所有指令都假設你在這個目錄裡。**
> 我的路徑是 `C:\Users\Key20\Desktop\router`,你的可能不同,下面看到這個路徑就換成你自己的。

### 4.3 Windows 端:Java + Ghidra

```powershell
powershell -ExecutionPolicy Bypass -File tools\setup\setup-windows.ps1 all
```

**這會做什麼:**

1. 下載 **Temurin JDK 21**(205 MB)—— Ghidra 是 Java 寫的,需要它
2. 下載 **Ghidra 12.1.2**(547 MB)—— 美國 NSA 開發並開源的反組譯工具
3. **兩個都比對官方公布的 SHA-256**,不符就刪檔中止
4. 解壓到 `%LOCALAPPDATA%\fwre-tools\`(你的使用者目錄,**不需要管理員**)

⏱ 看網速,大概 5–20 分鐘。中間沒有進度條是正常的,PowerShell 關掉進度條才不會慢十倍。

**應該看到:**

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
> **按取消就好**,我們的分析完全在本機跑,不需要網路。

### 4.4 WSL 端:逆向工具鏈

```powershell
wsl -d Ubuntu-24.04 bash /mnt/c/Users/Key20/Desktop/router/tools/setup/setup-wsl.sh all
```

> 路徑換成你自己的。Windows 的 `C:\` 在 WSL 裡叫 `/mnt/c/`,反斜線要換成斜線。

**這會做什麼:**

| 階段 | 裝什麼 | 為什麼要 |
|---|---|---|
| `apt` | 39 個系統套件 | 壓縮格式、SquashFS 工具、MIPS 模擬器、燒錄工具 |
| `rust` | Rust 編譯器 | binwalk v3 是 Rust 寫的,要自己編 |
| `binwalk` | binwalk 3.1.0 | 掃描檔案裡藏了什麼格式 |
| `sasquatch` | 修改版 unsquashfs | 廠商的 SquashFS 有非標準變體,原版解不開 |
| `unblob` | unblob 26.6.4 | 另一套解包工具,拿來對答案 |
| `path` | 改 `~/.bashrc` | 讓新開的終端機找得到上面這些 |
| `verify` | 逐一執行每個工具 | **不是檢查檔案在不在,是真的跑跑看** |

⏱ 5–15 分鐘,大部分在編譯 binwalk。

**中途會問你 Linux 密碼**(裝系統套件要 `sudo`),就是 §4.1 設的那組。

**應該看到:**

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

> 💡 這個腳本**可以重複執行**。裝到一半失敗,直接再跑一次就好,已經裝好的會跳過。

### 4.5 之後每次開工

從這裡開始,**進 WSL 工作比較方便**。開一個 PowerShell:

```powershell
wsl -d Ubuntu-24.04
```

提示字元會變成 Linux 的樣子(像 `key@K:~$`)。然後:

```bash
cd /mnt/c/Users/Key20/Desktop/router
```

> 📌 **下面 §5–§7 的指令都在這個 WSL 環境裡打。**
> §8 的 Ghidra 要回到 PowerShell(因為 Ghidra 裝在 Windows 端)。
> 打 `exit` 可以離開 WSL 回到 PowerShell。

---

## 5. Part 1 — 取得韌體

```bash
make fetch
```

**這會做什麼:**

1. 讀 [`firmware/SOURCES.json`](firmware/SOURCES.json) —— 裡面寫著要抓哪兩個檔、從哪抓、雜湊值應該是多少
2. 下載到 `~/fwre-work/firmware/`(**不是**在專案資料夾裡,見下方說明)
3. 逐一比對 **檔案大小 / MD5 / SHA-1 / SHA-256**
4. 把實際結果寫進 [`firmware/MANIFEST.json`](firmware/MANIFEST.json)

**應該看到:**

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

網路上叫「N150RT 韌體」的檔案有好幾個不同版本,鏡像站也會偷偷換檔。所以:

- `SOURCES.json` = **我打算抓什麼**(手寫的,含預期雜湊)
- `MANIFEST.json` = **我實際抓到什麼**(程式產生的)

兩個對不起來就會報錯,而不是默默讓後面所有結論失效。

2015 那版的 MD5/SHA-1 是從 **archive.org 的 metadata API** 抄來的,不是我自己算的 —— 所以可以拿一個我們控制不了的來源驗證:

```bash
curl -s https://archive.org/metadata/TOTOLINKN150RTV2.1.2B20150825.1601 \
  | jq '.files[] | select(.name|endswith(".web")) | {name, size, md5, sha1}'
```

### 為什麼韌體不放進 git

那是廠商的檔案,**不是我們的東西,不能散布**。這個 repo 只放「怎麼拿到 + 雜湊多少」,讓任何人都能自己抓到一模一樣的位元組。

---

## 6. Part 2 — 解包韌體

```bash
make unpack
```

**這會做什麼:**

1. 用 `fwrecon` 解析 `.web` 的容器格式,算出根檔案系統在**第幾個位元組**
2. 用 `dd` 把那一段切出來
3. 用 `unsquashfs` 解開;失敗才退回用 `sasquatch`
4. **檢查解出來的樹裡有沒有符號連結** —— 沒有就直接失敗

**應該看到:**

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

> ✅ **那兩行 `warn` 是正常的,不是錯誤。**
> `unsquashfs` 用一般使用者身分跑,沒辦法建立裝置節點(`/dev/*`)也沒辦法改檔案擁有者,所以它回傳非零。但**檔案內容和權限位元都是完整的**,那才是我們要的。
> 腳本因此不看回傳值,改看「有沒有解出東西、裡面有沒有符號連結」。

### 自己看看解出了什麼

```bash
ls ~/fwre-work/extracted/v2.1.2/squashfs-root/
```

```
bin  dev  etc  home  init  lib  mnt  proc  sys  tmp  usr  var  web
```

**這就是一台路由器的完整作業系統**,躺在你的硬碟上。逛逛看:

```bash
# 網頁伺服器本體
ls -la ~/fwre-work/extracted/v2.1.2/squashfs-root/bin/boa

# 開機時執行的腳本 —— 看第 108-110 行
cat -n ~/fwre-work/extracted/v2.1.2/squashfs-root/etc/init.d/rcS | sed -n '105,111p'
```

你會看到:

```
   105	#echo 1 > /proc/sys/net/ipv4/ip_forward #don't enable ip_forward before set MASQUERADE
   106	#echo 2048 > /proc/sys/net/core/hot_list_length
   107	
   108	# start web server
   109	boa
   110	#skt&
   111	
```

**第 110 行前面那個 `#` 就是本專案最有意思的發現之一。** `skt` 是 2015 年被公開的後門程式,廠商的「修補」方式是**把啟動那行註解掉**,但 `/bin/skt` 這個檔案還好好地留在韌體裡。詳見 [`notes/prior-art.md`](notes/prior-art.md)。

---

## 7. Part 3 — 產生分析報告

```bash
make recon
```

**這會做什麼:** 對兩個版本各產生 JSON + Markdown 報告,再做一份版本差異對照,全部寫進 [`reports/`](reports/)。

⏱ 約 10 秒。

**應該看到 5 個檔案被寫出來:**

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

**那三個 `high` 是什麼意思:**

路由器的檔案系統是唯讀的,所以會變動的東西都放在 `/var`(開機時建立的暫存空間)。而 `/web/config.dat` 是一個**指向 `/var/config.dat` 的符號連結**,`/web` 又是網頁伺服器對外公開的目錄。

翻成白話:**路由器把自己的設定檔(裡面有帳號密碼)放進了對外公開的網頁目錄。** 這就是 CVE-2019-19822 的成因。

> ⚠️ 但要小心:這只證明「檔案在公開目錄裡」,**不等於「不用登入就能下載」**。
> 也可能 Boa 在處理請求時有做認證檢查。要確認就得進 Ghidra 讀程式碼 —— 那是下一個階段的工作。
>
> **能區分「我觀察到什麼」和「我推論出什麼」,是這行最重要的紀律。**

### 看版本差異

```bash
cat reports/diff-2.1.2-to-3.4.0.md
```

這份會告訴你 2015 → 2020 之間:哪些網頁端點被加了、哪些被拿掉、哪些執行檔消失了(例如 `/bin/skt`)、哪些符號連結是新增的。

---

## 8. Part 4 — Ghidra 靜態分析

> 這一段要**回到 PowerShell**(Ghidra 裝在 Windows 端)。WSL 裡打 `exit` 離開。

### Ghidra 是什麼

把機器碼**還原成接近 C 語言的程式碼**的工具,NSA 開發並開源。

路由器裡的 `/bin/boa` 是編譯好的執行檔,人類讀不懂。Ghidra 可以把它變回大致看得懂的樣子。

### 兩個步驟,不是一個

- **`import.ps1`** = 匯入 + 跑自動分析。**貴**(每支好幾分鐘),但結果會存進專案,只要跑一次。
- **`analyze.ps1`** = 對已經分析好的程式跑一支腳本。**便宜**(幾秒),可以一直重跑。

W01 的版本把兩件事綁在一起,結果每改一行腳本就要重新分析一次。分開之後才有辦法做 W03 那種「改腳本 → 重跑 → 看結果」的迴圈。

### 步驟一:匯入 + 自動分析

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
> `key` 換成你的 Linux 使用者名稱(在 WSL 裡打 `whoami` 可以查)。
>
> 這樣做的用意:資料**只有一份**,躺在 WSL 的 Linux 檔案系統上,Windows 這邊只是讀它。不會有兩份不同步的問題。

**應該看到:**

```
 ==>  importing \\wsl$\...\bin\boa
      project : ...\ghidra-projects\totolink-n150rt/2.1.2
      sha256  : ddda5a4f3c65b54b96d8cc485f617daf049ad70eab42ac57e87b4b005f17d97a
  ok   analysed and stored under totolink-n150rt/2.1.2
```

⏱ 三支加起來約 5 分鐘。

> ⚠️ **`-Label` 為什麼是資料夾,不只是個標籤**
>
> `analyzeHeadless -import <path>` 是用**檔名**幫 program 命名的。兩個版本的檔案
> 都叫 `boa`,所以 W01 的寫法讓它們變成同一個名字,再加上 `-overwrite`,
> **第二次匯入會把第一次的無聲蓋掉**。
>
> 現在每個版本進自己的 project folder(`totolink-n150rt/2.1.2` 等),而且每份
> 報告都會帶上被分析檔案的 SHA-256。一份說不出自己分析了哪個檔案的報告,不算證據。

**`MIPS:BE:32:default` 這行很重要** —— `BE` = Big Endian。Ghidra 自己從檔案標頭判斷出來的,跟我們前面用別的方法算出來的答案一致。**兩個獨立來源得到同一個答案,才敢當結論用。**

### 步驟二:跑分析腳本

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

**應該看到:**

```
INFO  BoaFormTable.java> BoaFormTable: 2 table(s), 100 entries, 98 functions named
INFO  BoaSinks.java> BoaSinks: 1686 call sites across 21 sinks, 432 named functions
```

⏱ 每支 20–60 秒。

### 產出在哪裡

| 檔案 | 內容 |
|---|---|
| `reports/ghidra-strings-<版本>.json` | 關鍵字串 → 用到它的函式(W01) |
| `reports/ghidra-formtable-<版本>.json` | `root_form[]` 全表:每個 `/boafrm/` 路由的名字、handler 位址、它讀了哪些請求參數 |
| `reports/ghidra-sinks-<版本>.json` | `system` / `strcpy` / `sprintf` … 的每一個呼叫點,以及呼叫它的函式 |

看分派表:

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

第一次開會問你要不要建專案 —— 選 **File → Open Project**,路徑在:

```
%LOCALAPPDATA%\fwre-tools\ghidra-projects\totolink-n150rt.gpr
```

裡面有 `2.1.2`、`3.4.0`、`2.1.2-skt` 三個資料夾。雙擊裡面的 `boa` 打開,按 `G` 可以跳到指定位址。

**跑過 `BoaFormTable` 之後**,函式列表裡會有 185 個 `form_*` 和 `aspvar_*` 開頭的名字,每個上面都有一段註解寫著它是從分派表哪一項來的。直接按 `G` 跳到 `0x0044a190`(2015 版的 `form_formWsc`)就能看到本週最重要的那幾行。

---

## 8.5 Part 5 — 讀出授權流程(W03)

這一段是**閱讀**,不是跑指令。腳本只負責把證據搬出來,結論是人讀出來的。

### 把要讀的函式匯出成 C

```powershell
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaDecompile -Binary $boa2015 `
  -Out "$PWD\ghidra\decomp\decomp-2.1.2.json" `
  -ExtraArgs @('name:handleForm','name:translate_uri','name:process_requests','prefix:form_','callers:system')
```

產出在 `ghidra/decomp/`(**這個資料夾不進 git**)。

> ⚠️ **為什麼反編譯結果不能 commit**
>
> 反編譯出來的 C 是廠商 binary 的衍生物。整包 commit 等於換個方式散布韌體,
> 跟 README「不轉散布廠商韌體」的立場衝突。筆記裡引用片段 + 加上分析說明是另一回事,
> 那些有 commit。

### 讀不懂的時候,看組語

反編譯器**會出錯,而且會先警告你**。`process_header_end` 的輸出頂上有三行
`WARNING: Heritage AFTER dead removal`,那代表它自己知道這段處理得不好。

```powershell
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaListing -Binary $boa2015 -ReadOnly `
  -Out "$PWD\ghidra\decomp\listing-phe.txt" -ExtraArgs @('0040be0c','0040c600')
```

出來的是純文字組語,而且呼叫目標和字串常數都已經解出來了。找這幾行:

```
0040c234  lw t9,-0x7cbc(gp)        -> PTR_strstr_0048b2f4
0040c238  addiu a1,a1,-0x2be0        "htm"
0040c23c  jalr t9                  -> strstr
0040c248  beq v0,zero,0x0040c3a0                 ; 回 NULL 就跳過整段授權檢查
```

**這四行就是本週的結論**:URI 裡沒有 `htm` 三個字,授權檢查整段被跳過。
完整說明在 [`notes/auth-flow.md`](notes/auth-flow.md)。

> 用純文字而不是截圖,是因為截圖沒辦法 diff、沒辦法 grep、Ghidra 升版之後也沒辦法重新產生。

---

## 8.6 Part 6 — 硬體開工:料件辨識(W02 Day 1)

> 硬體 2026-08-14 到貨。**這一節只寫 Day 1 真的做完的事。**
> 到這一節結束為止,**路由器一次都沒有通電**。UART 和 SPI 是 Day 2 之後的事,
> 等真的跑過再回來補這一節 —— 見 [§13 鐵則 1](#13-怎麼維護這份文件)。

### 8.6.1 順序:跟著「可逆程度」走,不要跟著計畫書的日期走

```
拍照 → 抄絲印 → (通電) 電表定腳位 → 邏輯分析儀量 baud → 抓 bootlog → 最後才夾 SPI
```

**在拿到第一份 bootlog 之前,不做任何不可逆的動作。**

理由有兩個,第二個比較重要:

1. SOIC-8 夾是整週最可能弄壞東西的一步(夾歪、滑掉、短到隔壁腳)。
2. bootlog 會**先告訴你 flash 型號和 partition 表** —— 你等於在量之前先拿到一個
   預測,量完才知道自己對不對。反過來做就沒有對照組了。

> ⚠️ **這台機器是 G2 和 G4 的單點故障。** 沒有第二台。W05 要把 web server 服起來、
> W06 要在實機上重現 CVE,都靠它。任何「順手拆一下」的動作,都要先答得出
> 「這一刀換到哪一個 gate 的哪一格」。答不出來就不要動。

### 8.6.2 先拍照,再碰任何東西

G2 的第四格交付物就是**標註過的 PCB 照片**,而**原廠狀態只有一次機會拍**。
正反面高解析、對焦在絲印、光線側打;底部標籤整張拍下來。

### 8.6.3 抄絲印

用手機微距或放大鏡逐顆拍。這台上面有五顆:

| 位置 | 絲印 | 判讀 | 用途 |
|---|---|---|---|
| — | `RTL8196E` | Realtek RTL8196E | SoC(MIPS 大端序) |
| `U19` | `cFeon QH32B-104HIP` | Eon EN25QH32B,32 Mbit = **4 MiB** | 韌體儲存 |
| — | `Winbond W9825G6KH-6` | 256 Mbit SDRAM = **32 MiB** | 系統記憶體 |
| — | `RTL8188ER` | 1T1R 802.11n | 無線 |
| — | `LSC LSP5526` | **沒查到** | 電源(從位置推測) |

> 💡 **cFeon 的 `Q` 在這個放大倍率下跟 `O` 幾乎一樣。** 照片上讀起來像 `OH32B`,
> 但世界上沒有 `EN25OH32B`。**這種事不要靠瞇眼睛決定** —— Day 4 讓 `flashrom` 讀
> 晶片自己回報的 JEDEC ID,那才是證據。

完整判讀和每一條的第二來源:[`notes/hardware-inspection.md`](notes/hardware-inspection.md)。

### 8.6.4 確認 flashrom 認得這顆 flash

這是 Day 1 的交付物之一,現在就能查,不用碰硬體:

```bash
flashrom -L | grep -i en25qh
```

**實際輸出:**

```
Eon                          EN25QH128                            PREW          16384  SPI
Eon                          EN25QH16                             PREW           2048  SPI
Eon                          EN25QH32                             PREW           4096  SPI
Eon                          EN25QH64                             PREW           8192  SPI
```

`PREW` = probe / read / erase / write 四種都支援;`4096` KiB = **4 MiB**。

> ⚠️ **這個輸出不能當成「flash 是 4MB」的第二來源。**
> `flashrom` 的資料庫是**用料號當索引**的,而料號是從同一塊晶片上的同一行字讀來的。
> 它證明的是「**如果**這顆是 EN25QH32,那它就是 4096 KiB 而且我讀得動」,
> 不是「這顆是 4 MiB」。
>
> **真正獨立的來源是晶片自己回報的 JEDEC ID**(Eon 的廠商碼是 `0x1C`),
> 那要等 Day 4 夾上去才有。

**夾之前還要量一件事:SOP-8 有 150 mil 和 208 mil 兩種寬度**,而 CH341A 套件附的
夾子常常是窄的那種。先量 `U19` 的本體寬度,不要硬夾。

### 8.6.5 確認 usbipd 裝好了

```powershell
winget install --interactive --exact dorssel.usbipd-win
```

裝完之後 **PowerShell 要重開**(見 [§10.15](#1015-usbipd-裝好了但-powershell-說找不到))。

```powershell
usbipd list
```

**實際輸出(工具都還沒插上的樣子):**

```
Connected:
BUSID  VID:PID    DEVICE                                                        STATE
1-3    046d:c52b  Logitech USB Input Device, USB Input Device                   Not shared
1-6    13d3:56a8  USB2.0 HD UVC WebCam                                          Not shared
1-10   8087:0026  Intel(R) Wireless Bluetooth(R)                                Not shared

Persisted:
GUID                                  DEVICE
```

USB-TTL / CH341A / 邏輯分析儀插上去之後,這張表會多出對應的列 —— **那就是確認
「東西有被 Windows 認到」最快的方法**,比開裝置管理員快。

### 8.6.6 Day 1 刻意沒做的事

| 沒做 | 為什麼 |
|---|---|
| **拆天線** | 試過,失敗,而且**本來就不該做** —— 它不對應 G2 任何一格。見 [§10.14](#1014-天線焊點-450c-化不開) |
| **剪 on/off 開關線短接成常開** | 提出後否決。那兩根線的用途沒量過就短接是在賭;而且接下來要反覆斷電重開幾十次,**一個能撥的開關是資產不是障礙** |
| **通電** | Day 1 只做辨識。通電是 Day 2 量腳位時才開始 |
| **焊任何東西** | 這台的 UART **已經有排針**,整個 W02 一刀都不用焊 |

### 8.6.7 找到 UART 排針

板子下緣、LED 那一排旁邊,有一組**已經焊好的 4-pin 2.54mm 排針**,
旁邊絲印直接印著 `UART`。

意思是:**整個 W02 完全不用焊接。** 廠商把 debug 介面留在出貨的消費性產品上,
而且還標了名字。

> ⚠️ **絲印寫 `UART` 只告訴你「這組是 UART」,沒告訴你「哪一支是哪一支」。**
> GND / VCC / TX / RX 的順序要用電表量出來(Day 2),**不可以照慣例猜**。

### 8.6.8 照片進 repo 之前:先遮

**這塊板子上有兩張會指認出「你這一台」的標籤:**

| 位置 | 是什麼 | 動作 |
|---|---|---|
| PCB 背面條碼 | 12 個十六進位字元 —— **幾乎確定是這台的 MAC 位址** | **遮掉再 commit** |
| PCB 正面 QR + 數字標籤 | 機身序號 | **遮掉再 commit** |

而 G2 要交的就是**背面那張照片**。

同一條規則接下來還會用到兩次:

- **bootlog** 會印出 MAC,而且照 W04 找到的 `flash set HW_WLAN0_WSC_PIN %s` 來看,
  很可能連 **WPS PIN** 一起印;
- **flash dump 的 config 分割區**裡全部都有 —— 這也是 [`.gitignore`](.gitignore)
  一開始就把 `dumps/*` 擋在 repo 外面的原因之一。

**一條規則,三個地方:從「我這一台」讀出來的東西一律遮掉,只發表對「這個型號」
成立的事實。** 遮蔽要在 `git add` 之前決定 —— **推上去之後才遮的,不叫遮。**

> 💡 **QR 比印出來的數字危險。** 印出來的號碼要有人去「讀」,QR 是**自動被解碼的**,
> 而且縮圖之後照樣解得出來。所以連廣角照裡只有幾十像素寬的那個 QR 也要蓋掉。

### 8.6.9 遮蔽和標註都用腳本,不用影像編輯器

理由跟 W03 拒絕用 Ghidra 截圖一樣:**編輯器產出的檔案沒有人能檢查、沒辦法 diff、
原圖重拍之後也沒辦法重新產生。**

兩支工具都需要 Pillow,裝進**這個專案自己的 venv**:

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

**應該看到:**

```
  ok    04-pcb-bottom-redacted.jpg: 1 region(s), 104,000 px (3.31% of frame) painted out, EXIF dropped, verified on read-back
  ok    05-pcb-top-annotated.jpg: 12 callouts, 2048x1936
```

> ⚠️ **工具能證明框裡是純黑,證明不了框在對的位置。**
> **那一關是人工的,三張都要親眼看過。**

完整座標紀錄、檔名規則、產生方式:[`notes/img/README.md`](notes/img/README.md)。

---

## 8.7 Part 7 — 序列 console 與 flash 讀取(W02 Day 2–3)

> 2026-08-15 實際跑過的流程。**這一節從頭到尾板子是通電的。**

### 8.7.1 量腳位:先驗表,再量板

**順序不能顛倒。**

```
1. 電池 → V⎓ 20V 檔 → 讀到 1.5 / 9        ← 驗證表本身,不碰板子
2. 通電 → 板子的 LED 有沒有亮              ← 驗證板子有電,不用表
3. 斷電 → Ω 檔,黑筆夾 DC 座外環,紅筆掃四支腳
4. 通電 → V⎓ 20V 檔,同樣掃四支腳
```

第 1 步不能省。這一天最久的一次卡關,就是**用 200mV 檔去量 3.3V** ——
差 16 倍,而它回給我的不是「超量程」,是一個會漂的 `0.x`,看起來跟真讀數一樣。
見 [§10.17](#1017-電壓量到-0x-在跳-而且怎麼量都不對)。

實測結果(pin 1 = 板上三角形那端):

| 腳 | 斷電 Ω 對地 | 通電 V 對地 | 判定 |
|---|---|---|---|
| 1 | 181 Ω | 3.3 V | **VCC** —— 不接 |
| 2 | 18 kΩ | 0–3.3V 在跳 | **TX** |
| 3 | 15 kΩ | 0 V | RX(推論) |
| 4 | **0.2 Ω** | **0 V** | **GND** |

> 💡 **3.3V 軌對地是幾百歐姆,不是開路。** 這是最容易被當成地的一個讀數。
> 三個量級清楚分開(`0.2` / `181` / `15–18k`)才是可以下判斷的資料。

### 8.7.2 量 baud,不要試 baud

邏輯分析儀接 TX + **GND(一定要接)**,8 MS/s,抓 3–5 秒,先按 Run 再開電源。

量**最窄**的脈衝:**26 µs** → `1/26µs` = 38.46 kHz → **38400**。

> **自洽檢查才是重點:** 同一段裡有一個脈衝正好是 **52 µs = 2 × 26**。
> 如果 26 µs 是兩個位元,就必須存在 13 µs 的脈衝 —— 而不可能有半個位元。
>
> **最接近的錯誤答案是 19200,它的位元時間正好 52.08 µs。**
> 挑錯脈衝就會設成 19200,然後整晚看亂碼。

### 8.7.3 把 CP2102 交給 WSL

接線:`GND→pin4`、轉接板 `RXD→pin2`、轉接板 `TXD→pin3`、**`VCC` 不接**。
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

> ⚠️ **`attach` 之前 WSL 必須正在跑**,否則會說
> `There is no WSL 2 distribution running`。見 [§10.19](#1019-usbipd-attach-說沒有-wsl-2-發行版在跑)。

```powershell
Start-Process -WindowStyle Hidden wsl -ArgumentList "-d","Ubuntu-24.04","--","sleep","7200"
usbipd attach --wsl --busid 1-1
```

**應該看到:**

```
crw-rw---- 1 root dialout 188, 0 /dev/ttyUSB0
[   31.521095] cp210x 1-1:1.0: cp210x converter detected
[   31.523173] usb 1-1: cp210x converter now attached to ttyUSB0
```

WSL 的使用者預設**不在 `dialout` 群組**,所以要:

```bash
sudo usermod -aG dialout $USER    # 之後永久有效
sudo chmod 666 /dev/ttyUSB0       # 這次立即生效
```

### 8.7.4 抓 bootlog

```bash
stty -F /dev/ttyUSB0 38400 cs8 -cstopb -parenb raw -echo
timeout 90 cat /dev/ttyUSB0 > ~/fwre-work/dumps/uart-boot.log
```

**先讓它跑起來,然後才開板子電源。** 開機訊息只跑一次。

實測 1903 bytes / 69 行,`Booting` 出現 **1 次**(所以不是 boot loop)。
內容分析在 [`notes/uart-findings.md`](notes/uart-findings.md)。

### 8.7.5 這台的 console 沒有 shell

開完機送 `\r`,回來的是**完整的回顯,但指令不執行、也沒有提示符**:

```
送  : \r \r \r\n  echo MARKER_1234\r
回  : CR LF ×4,然後 "echo MARKER_1234" CR LF
```

**那是 Linux tty 行規程在回顯,不管有沒有行程在讀。**
沒有 getty、沒有 shell,bootlog 裡也沒有 BusyBox 那句
`Please press Enter to activate this console`。

> **「console 有回應」感覺很像成功,但它不是。** 要分清楚回顯來自 tty 層,
> 還是真的有東西在讀。

### 8.7.6 搶 bootloader:ESC 要在上電之前就開始送

中斷視窗只有一秒多,而且開機瞬間就開始 —— **看到輸出才按已經來不及了。**

```bash
timeout 45 cat /dev/ttyUSB0 > ~/fwre-work/dumps/uart-bootloader.log &
END=$((SECONDS+20)); while [ $SECONDS -lt $END ]; do printf '\033' > /dev/ttyUSB0; sleep 0.03; done
# ↑ 開始送之後才打開板子電源
```

**成功的樣子(注意它沒有去載核心,改去初始化網路):**

```
---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)
P0phymode=01, embedded phy
---Ethernet init Okay!
<RealTek>
```

### 8.7.7 bootloader 指令:`?` 不是 `HELP`

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

說明自己寫 `HELP (?)`,但 `HELP` 回 `Unknown command !`。**只有 `?` 能用。**

> ⚠️ **`FLW`、`EB`、`EW`、`AUTOBURN` 會寫入。打錯參數就是磚。**
> 讀 flash 只需要 **`FLR`** 和 **`DB`**,一個寫入指令都不要送。

### 8.7.8 讀 flash:`FLR` + `DB`

**這是一條完整的 flash 讀取路徑,不用夾 SOIC-8 夾子。**

```
FLR <RAM位址> <flash位移> <長度>     ← 三個都是十六進位
Y                                     ← 一定要,見下
DB <RAM位址> <長度>                   ← 位址十六進位,長度十進位
```

**實測:**

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
> **1. `FLR` 會問 `(Y)es , (N)o ?`,而且把下一行整個吃掉當答案。**
> 腳本裡如果直接送下一個指令,會得到 `Abort!` —— 然後那個 `DB` 印出來的是
> **RAM 裡上一次留下的舊資料**,而你會以為那是 flash 的內容。
>
> **2. `FLR` 的長度是十六進位,`DB` 的長度是十進位。**
> `DB <addr> 100` 回你 100 bytes,不是 0x100。**沒有任何警告,你會拿到一份
> 格式完全正常、長度錯誤的 dump。**
>
> **對策:每次 `FLR` 之前先 `DB` 同一塊 RAM 當對照組。** 內容沒變就是 FLR 沒生效。

實際讀出來的 flash 版面在 [`notes/flash-layout.md`](notes/flash-layout.md)。

---

### 8.7.9 完整 4 MiB dump:`tools/console-dump.py`(W02 Day 4)

上面那套是手動讀 64 byte 窗口。**要把整顆 4 MiB 讀下來,手是不行的** —— 那是
26 萬行十六進位、大約 95 分鐘,而 38400 沒有流量控制,**掉字元不是可能性,是排程**。

掉一個字元不會有人通知你。你會得到一份短一點、但看起來完全正常的 hex dump,
貼進轉換器之後得到一個**中間有洞、洞之後每個位移全部位移掉**的映像檔,
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

**這支工具做了四件手做不到的事:**

| | |
|---|---|
| **陽性對照** | 先 `FLR` flash `0x000000`,前四個 byte 必須是 `0b f0 00 04` —— 那是 8/15 另一場 session 記下的已知答案。對不上就不往下走 |
| **逐塊驗證** | 每一塊檢查位址連續、每行剛好 16 byte、總長相符。**掉一行就整塊重讀** |
| **抽驗重讀** | 全部讀完後隨機抽 5% 的塊**再讀一次**比對。解析器看不到「格式正確但內容錯」的位元翻轉,重讀看得到 |
| **拼不完整就不吐檔案** | 只留 `.partial`。**一份看起來完整的殘缺映像,比沒有映像更糟** |

> ### ⚠️ 兩個 8/16 踩到的坑
>
> **1. ESC 會塞住 bootloader 的輸入緩衝區。** 搶 bootloader 是「連續送」ESC,
> 它只吃掉一個用來中斷開機,**其餘全部排在輸入緩衝區裡** —— 所以搶到之後
> **第一條指令必定失敗**,回你 `Unknown command !`。
> 對策:先送一個裸 `\r` 讀到 prompt 再送真正的指令(工具的 `settle()`)。
> 這一坑害我以為 `?` 不是 help —— 而 §8.7.7 明明記過 `?` 就是 help。
>
> **2. 不要照 `notes/` 裡引用的 transcript 寫解析器。** `notes/` 是分析文件,
> 引用會為了排版修剪;**§8.7.8 這裡的 transcript 才是逐字的**。
> 第一版解析器沒有 ASCII 欄,把裝置吐的**每一行**都判成不合法。

**速率是物理上限,不要調程式:** 每 16 個 data byte 要送 81 個字元
(位址 8 + `: ` 2 + hex 48 + 空白 5 + ASCII 16 + CRLF 2),**5.06 倍膨脹**。
38400 8N1 = 3840 B/s ÷ 5.06 = **759 B/s 理論上限**,實測 723 B/s。
線已經吃滿了。

**dump 落地之後,它還不是證據:**

```bash
python -m fwrecon flashdump ~/fwre-work/dumps/flash-n150rt-console-1.bin
```

這會拿映像去對 **8/15 console 讀到的每一個 offset** 和 **W01 從廠商容器推導的
燒錄位址** —— 兩份都寫在它存在之前。硬檢查沒過就 exit 1。
per-unit 秘密區(`0x006000`–`0x010000`)只報 SHA-256,**永遠不印內容**。

---

## 8.8 W04-2 新增的操作(2026-08-16)

### 8.8.1 把這台自己的 `boa` 讀進 Ghidra,並跑五種量測

匯入一次幾分鐘,之後每次跑腳本只要幾秒。

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
> **1. Ghidra 專案是整個上鎖的。** 前一個 `analyze.ps1` 還在跑的時候再開一個,
> 會拿到 `LockException: Unable to lock project!`。**要排隊,不能平行。**
>
> **2. `BoaArgTrace` 對 `sstrip` 過的 build 一定要給 `accessor:`。**
> V3.4.0 沒有符號,不給 `accessor:FUN_0040e9e0` 的話,它**一個 request 參數都
> 認不出來**,污染點數字直接從 49 掉到 0 —— 而 `self_check` 會寫 `consistent`,
> 因為那個檢查只在「你給了 override 但沒對上」時才會叫。
> 現在多了一個 `no_accessor_identified`,零匹配就報 SUSPECT。
>
> **3. 三個 build 要用同一組 spec 才能比。** 報告現在會把 `spec` 欄寫進去,
> 沒有那一欄的舊報告不能拿來跟新的並排 —— W04 的 304 和 W04-2 的 1508
> 看起來像個發現,其實是在回答不同的問題。

### 8.8.2 解碼設定區(`COMPCS` / `COMPDS`)

```bash
fwrecon compcs $FWRE_WORK/dumps/flash-n150rt-console-1.bin --offset 0x00C000 \
  --mib $FWRE_WORK/extracted/unit-2018/squashfs-root/lib/libapmib.so \
  -f json -o reports/compcs-unit-2018.json
```

`--offset 0x008000` 是出廠預設。**`0x006000` 會失敗,而且應該失敗** —— 那塊是
`H601`,沒有壓縮,不是 `COMPHS`:

```
fwrecon compcs: no APMIB config magic at 0x6000: found b'H601\x04\x8e',
expected one of ['COMPCS', 'COMPDS', 'COMPHS']
```

**退出碼有意義:** `0` 乾淨,`1` 解出來了但自己標了 anomaly,`2` 根本不接受這塊
資料。`1` 和 `2` 都不可以拿來當證據。

`--disclosure protect` 會把 per-unit 識別碼換成 sha256。今天的決定是 `open`,
但**機制留著,而且有一個會失敗的測試守著它** —— 改的是政策,不是能力,下一台
機器不一定是你的。

### 8.8.3 CI 閘門:`BoaGate`,以及**為什麼一定要給 `control:`**

```powershell
# 對照組一定要帶 control:,否則這個閘門不能證明自己是活的
.\ghidra\analyze.ps1 -Label 2.1.2 -Script BoaGate -Binary $boa212 `
    -ExtraArgs @('control:30','depth:8')
```

> **這一格是整個工具的賣點,不是一個選項。**
>
> 第一次跑,它在 V2.1.2 上回報 **0 findings** —— 而那個 build 是 W03/W04
> 一行一行讀出 34 個有問題的 handler 的那一個。原因有兩個,而且是分開的兩次:
> 先是用「名字」比對 sink,但這些 binary 呼叫 libc 是走 `sstrip` 過的 PLT,
> Ghidra 把它叫成 `FUN_xxxxxxxx`;修掉之後又發現字面值解析只檢查 `isConstant()`,
> 而 MIPS 的字串位址是 lui/addiu 湊出來的,所以**一個參數名字都沒讀到**。
>
> 兩次都會以「這個 build 很乾淨」的形式出貨。**`control:30` 兩次都當場擋下來。**
> 一個沒有在已知壞掉的 build 上驗證過的 SAST 規則,不是檢查,是裝飾。

### 8.8.4 抓一份廠商映像回來,以及它只下載了 40% 的時候怎麼辦

**這一節服務 `PROGRESS.md` 開放問題 #0:把公開的 V2.1.6 重抓一次,而且先驗
zip 自己的 CRC-32。** 第一次抓只下來 40.3%,而那份殘檔仍然回答了問題,所以
下面兩件事都要寫:怎麼抓,以及**殘檔可以撐到哪裡、不可以撐到哪裡**。

#### 抓檔:腳本抓不到,瀏覽器抓得到

Softpedia 對 PowerShell `HEAD`、三種 User-Agent 的 `curl`、`WebFetch` 全部回
**403**。`firmware/SOURCES.json` 從 W01 就記著這件事,所以這是**確認,不是發現**
—— 不要再花時間繞它。用瀏覽器點,然後**不要憑記憶把網址打進文件**:

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
> 後面當成一個檔案開。**檔案搬進 `$FWRE_WORK` 的時候這條 stream 會跟著搬,
> 但用 `cp` 到別的檔案系統就沒了** —— 要保存 provenance 就先讀出來。

#### 驗檔:`unzip` 說壞掉,不代表它壞掉

```bash
unzip -t N150RT-V2.1.6-20160516.zip
```

```
  End-of-central-directory signature not found.  Either this file is not
  a zipfile, or it constitutes one disk of a multi-part archive.
```

**這個訊息會讓你以為檔案是壞的。它不是,它是被截斷的,而那是兩件事。**
ZIP 的目錄在檔尾,少了目錄 `unzip` 就完全不動手;但 deflate 是**串流**,
前綴照樣解得開。用 `tools/zipprefix.py`,它直接讀 local file header:

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
文字,鏡像站可以隨便打;DOS 時間戳是打包程式寫進去的**另一個欄位**。兩個對上,
偽造成本就從「改檔名」變成「還要改時間戳」。**這仍然只是佐證** —— TOTOLINK
不簽章,所以沒有任何東西能證明這些 byte 出自原廠(`firmware/SOURCES.json`)。

#### 取出殘檔:預設不准,而且 `--allow-partial` 不會把結論洗白

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

> **`--allow-partial` 只解除「不准寫」,它不會把 exit code 變成 0。**
> 這是故意的:殘檔可以拿來分析,但**「我知道它是殘的」和「它是完整的」不能
> 用同一個回傳值表示**。CI 或任何腳本照樣攔得住。
>
> 重抓成功的判準只有一個:**`CRC-32 recovered` 要等於 `0xd20c0622`。**
> 這個數字現在寫在這裡,是為了讓下一次的驗證有一個**事先寫好的目標**,
> 而不是抓完再看它是多少。

#### 殘檔撐得到哪裡 —— 比第一次寫的多

`fwrecon image` 讀那份 40% 的前綴:

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

**兩個 section 都是完整的,不是只有 header。** `fwrecon` 的 `payload_actual`
等於 `length`,而且 `cr6c` 裡那條 LZMA 解到底(`eof=True`,3,374,608 bytes)。
截斷的是第三段 `r6cr`,也就是 rootfs —— 所以缺的是 `/etc/version` 和 `boa`,
**不是「只有 section 長度」**。第一次寫成後者,低估了手上的東西一整段。

### 8.8.5 打開 `w6cg`:廠商實際出貨的網頁,以及一個會騙人的 grep

W01 把 `w6cg` 的封裝格式列為「解開了但沒 parse」,一直沒動。`fwrecon web`
把它做完了 —— 格式是 **64 bytes 的 header + 內容**,長度欄在 `+0x3c` 而且是
**big-endian**(header 裡其他欄位是 little-endian,只有這一個不是)。

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

> ⚠️ **`self_check: exact` 是這個工具唯一的保證,不是裝飾。**
> 這個格式**沒有校驗碼、沒有檔案數、沒有結束標記** —— 所以「我 parse 對了」
> 這件事只能從結構本身證明:每一步都是 `64 + length`,所以走完整條鏈要嘛
> **剛好停在最後一個 byte**,要嘛歪掉。長度欄位猜錯一個 offset,一兩筆之內就
> 會歪,而且回不來。**看到 `derailed` 就不要用它吐出來的任何數字。**
>
> ⚠️ **`--grep` 是逐筆搜「內容」,不是搜整塊解壓後的資料 —— 這個差別會害人。**
> 2018 那份 bundle 裡直接用 `grep` 找 `syscmd.htm` **找得到**,而正確答案是
> 那個檔案不存在:命中的是 `language_vn/sc/sp.js` 裡的一行註解
> `/**** syscmd.htm ****/`。**檔名出現在某個檔案裡,不等於那個檔案存在** ——
> 我第一次就是這樣差點推翻 `notes/auth-flow-2018.md` 一句正確的結論。

其他用法:

```bash
python -m fwrecon web <image>                     # 列出全部 entry(名稱/長度/sha256)
python -m fwrecon web <image> --extract syscmd.htm -o /tmp/syscmd.htm
python -m fwrecon web <image> --json -o reports/...
```

---

## 8.9 ⚠️ G3.5 最後一格:`FLW` 回復路徑演練(**還沒做,而且要你親手做**)

**W05 不准在這一格完成之前開始。** 理由不是儀式:W06 的 PoC 必然寫 flash
(`flash set` 寫的就是 `COMPCS`),而這台機器的回復路徑**從來沒有被執行過**。
`0x006000` 的 `H601` 是這台的 MAC 和射頻校準值,**全世界只有這一份**,
原廠映像沒有,回復原廠設定也不會還原。

### 開始之前,三件事缺一不可

```bash
# 1. 兩份 dump 都在,而且雜湊沒變 —— 這是唯一的還原鏡像
cd $FWRE_WORK/dumps && sha256sum -c <<'EOF'
a800059a9b8c414df026a22b8423a5939d0f9bb793109d0f7ce086f6810f37ea  flash-n150rt-console-1.bin
a800059a9b8c414df026a22b8423a5939d0f9bb793109d0f7ce086f6810f37ea  flash-n150rt-console-2.bin
EOF
```

2. **每一行 `FLW` 先寫在檔案裡,念一遍,再貼進終端機。不准現打。**
   `FLR` 已經教過這台的教訓:兩個相鄰指令用兩種進位制。**`FLW` 參數順序打錯
   = 把測試樣式寫進 kernel。**
3. **只碰 `0x3F0000`。** 不要「順便試試看 `0x350000`」。

### 為什麼 `0x3F0000` 是安全的

W02 Day 4 的完整 dump 證明 **`0x350000` 到 part 結尾整段都是 `FF`(已抹除)**。
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
| **回復路徑存在,而且我執行過** | 不再是「文件上列著 `FLW`」。W06 可以排寫 flash 的實驗了 |
| **`FLW` 的參數順序和單位我確認過** | 順序打錯的代價是把樣式寫進 kernel |
| **這是一次寫入 → 讀回的往返** | 系統性錯的 `FLR` 仍然躲得掉(位址偏移會互相抵銷),但**資料層的錯誤躲不掉** |

**做完之後,把逐字 transcript 貼回這一節,並在 `notes/uart-pinout.md` 的
bootloader 指令表補上「`FLW` 已實測,日期」。** 這份文件是操作紀錄,它的
transcript 是逐字的 —— W02 Day 4 的第 8 號 bug 就是因為有人去讀了 `notes/`
裡被排版修剪過的引用,而不是讀這裡。

---

## 8.10 W05 Day 0:測試登記簿怎麼用(G3.75)

W05–W07 要對同一台機器跑一百多個測試。**這一節是那一百多次的操作規程。**

### 8.10.1 為什麼不直接開一張表在 PROGRESS 裡

兩個理由,都不是潔癖:

1. **同一份狀態被兩個檔案擁有,一定會漂移。** 2026-08-16 就發生過一次
   (`PROGRESS.md` 說開放題已答、`LOG.md` 三個檔案外還把同一題當成未答)。
   130 列的表放兩份,一個禮拜就散。
2. **沒有事先寫下「失敗長什麼樣」的測試,事後一定會被讀成成功。** 回應到手的時候,
   讀的人已經知道自己想看到什麼了。

所以:`study/test-cases.toml` 是唯一擁有單項狀態的檔案,`study/test-ledger.md`
是它生成出來的,`tools/rtcase.py check` 在 CI 裡擋。

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
| `--evidence` | `static` / `dynamic` | **真的送過封包才算 `dynamic`。** 填 `static` 的話,登記簿印 🟥 不印 ✅ |
| `--artefact` | 可重複,repo 相對路徑 | 判 `confirmed` / `partial` 一定要有,而且路徑必須存在 |

### 8.10.3 反證條件怎麼寫

**這是整份登記簿唯一真正重要的欄位。** 判準是:*看到什麼,我就承認這條不成立?*

| ❌ 這樣寫沒有用 | ✅ 這樣寫才擋得住自己 |
|---|---|
| 「沒有反應就是不成立」 | 「未帶憑證收到 301 到登入頁 → `未認證` 的讀法錯了,NVD 的 `PR:H` 是對的,X-7 那條爭議要撤回」 |
| 「掃不到就是關的」 | 「9034 有回應 → rootfs 的 ELF 清單漏了東西。那比命中一個 KEV 更重要,因為它讓所有『這台沒有 X』的說法一起失效」 |

差別是:好的反證條件會**指名哪一份既有結論要跟著改**。寫不出那一句,通常代表
這個測試本身還沒想清楚要問什麼。

### 8.10.4 要改預測的時候

改了就得同時改 `[freeze].sha256`,**而且要在同一個 commit 裡**:

```bash
python3 tools/rtcase.py freeze        # 印出新的雜湊,自己貼進 study/test-cases.toml
python3 tools/rtcase.py check
```

> ⚠️ **如果那一項已經有結果了,`check` 會直接擋下來**,因為每一筆結果都戳了它
> 當時被判定所依據的那段文字的雜湊。要改就得連戳記一起改,`git diff` 會把
> 「事後改了預測」這件事攤在那裡。這不是防你,是讓那個動作留下痕跡。

### 8.10.5 紀錄卡(每一次執行都要留)

登記簿只留判定與證據連結。**逐字的 request / response 留在這裡的格式**:

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
| `record` 拒絕,說 `no refutation condition` | 那一項還沒寫反證。**先寫,不要先記結果** —— 這是刻意的 |
| `check` 說 `artefact ... does not exist` | 證據連結指到不存在的檔。證據不能是裝飾 |
| `check` 說 `has been edited since the result` | 有結果的項目被改了預測。要嘛把字改回去,要嘛連戳記一起改讓 diff 看得見 |
| CI 說 `study/test-ledger.md is out of date` | 改了登記簿沒跑 `make ledger` |
| 本機 `python3` 說沒有 `tomllib` | Windows 側那顆是 3.10。走 WSL,或 `FWRE_PY=$HOME/fwre-work/venv/bin/python` |

### 8.10.7 這個 gate 自己會不會騙人

會,所以有 `bash tools/test-rtcase.sh`:1 個必須通過的對照組 + 21 個
**必須被擋下來、而且必須是因為正確的理由被擋下來**的案例。`make ci` 兩個都跑。

> 沒有對照組的守衛套件會在整個系統壞掉的情況下全綠 —— 2026-08-14
> `tools/test-photo-tools.sh` 就是 5/5 通過而每一次呼叫都死在 `import PIL`。
> 這 22 個案例第一次跑就抓到 `rtcase record` 的一個真 bug。

---

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

**闔上電腦,大聲回答。** 答不出來就再讀一次 [`notes/anatomy-n150rt.md`](notes/anatomy-n150rt.md)。

| # | 問題 | 答案 |
|---|---|---|
| 1 | 這是什麼晶片? | Realtek RTL8196 系列 —— **還沒實體確認**,要等拆機 |
| 2 | 什麼 CPU 架構? | MIPS32,MIPS-I 指令集,o32 ABI |
| 3 | 端序? | **大端序 Big Endian** |
| 4 | 載入基底位址 / 進入點? | `0x00400000` / `0x00404020`(2.1.2) |
| 5 | 什麼檔案系統? | SquashFS 4.0 —— 2015 版用 LZMA,2020 版用 XZ |
| 6 | 網頁伺服器是誰? | `/bin/boa`,`Boa/0.94.14rc21`,**以 root 執行** |
| 7 | 設定檔怎麼存? | `libapmib.so` → `COMPCS` 明文格式 → `/web/config.dat` |

**進階題(答得出來代表你真的懂了):**

- 為什麼大端序的 MIPS 裡面裝的是「小端序」的 SquashFS?
  → SquashFS 4.0 規格就規定**磁碟格式一律小端序**,不管 CPU 是什麼。核心驅動會自己轉。這不是矛盾。
- 規格書說 2MB 快閃記憶體,你為什麼說至少 4MB?
  → 韌體自己的燒錄位址表最高到 3.57 MiB,塞不進 2MB。
- 為什麼 `readelf` 對 2020 版的 boa 什麼都印不出來?
  → 那個檔案被 `sstrip` 過,section header 整個被移除。`readelf` 靠它工作,找不到就**印空白還回傳成功**。

### 全部重跑一次(確認沒壞)

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

> ⚠️ **push 之前跑 `make ci`,不要自己挑幾個目標跑。** 見 [§10.21](#1021-本機全綠但-ci-還是紅的)。

### G3.75 — 開打前的前置(W05 Day 0)

```bash
python3 tools/rtcase.py check        # 登記簿凍結了、每一筆結果都有證據
bash tools/test-rtcase.sh            # 而且這個 gate 真的擋得住東西(22 個案例)
```

| # | 要有什麼 | 現況 |
|---|---|---|
| 1 | `FLW` 回復路徑演練過(＝ G3.5 #5,見 §8.9) | ❌ **還沒做,它擋住下面全部** |
| 2 | 隔離驗證過:網段上只有兩個 MAC,WAN 接假上游 | ❌ 要在機台前做 |
| 3 | IoC 預檢:設定 vs 出廠基準線 + 殭屍網路常用埠 | ❌ 要有機器。**判準先寫好了:差異維持在 4/344** |
| 4 | 預測登記簿凍結 | ✅ `study/test-ledger.md`,128 項 / 98 項有反證 |
| 5 | 揭露登記簿寫好 | ✅ `docs/disclosure.md` |

**5 條沒到齊之前,不准對這台送第一個封包。** 操作規程在 §8.10。

---

## 10. 疑難排解

> 下面每一條都是**這個專案真的踩過**的坑,不是想像出來的。

### 10.1 UAC / 「這個 App 要變更你的裝置」跳出來

**除了 §4.1 裝 WSL 之外,任何步驟都不該跳這個。**

如果跳了,代表你可能用到了舊版腳本(走 `winget` 裝 JDK 的那版)。現在的 `setup-windows.ps1` 用免安裝 ZIP 解到使用者目錄,不需要權限。**按取消,然後 `git pull` 更新專案再跑一次。**

### 10.2 Windows 防火牆問「私人網路 / 公共網路」

是 Java(Ghidra)觸發的。**按取消**。Ghidra 的分析純本機運算,不需要網路。

### 10.3 `make: command not found`

你在 PowerShell 裡打了應該在 WSL 裡打的指令。先 `wsl -d Ubuntu-24.04`,再 `cd /mnt/c/...`。

### 10.4 `binwalk: command not found`(明明裝過了)

新開的終端機還沒載入 PATH。兩個解法:

```bash
source ~/.bashrc          # 立即生效
```
或直接關掉終端機重開。

### 10.5 安裝腳本卡在 `rust: fetching rustup-init`

網路瞬斷。**直接重跑一次**:

```bash
bash tools/setup/setup-wsl.sh all
```

腳本是**冪等的** —— 已經裝好的會跳過,只補沒裝的。

### 10.6 binwalk 編譯失敗,提到 `fontconfig`

缺系統套件。理論上 `apt` 階段已經裝了,沒有的話手動補:

```bash
sudo apt install -y libfontconfig1-dev libfreetype-dev
bash tools/setup/setup-wsl.sh binwalk
```

> binwalk v3 有畫熵值圖的功能,那功能需要字型函式庫。這個相依關係不會寫在文件裡,只會在編譯炸掉時出現。

### 10.7 `make unpack` 說 `no symlinks in the extracted tree`

**這是保護機制,不是壞掉。**

代表你把 `FWRE_WORK` 指到了 Windows 的磁碟(`/mnt/c/...`),那裡存不了符號連結。

```bash
echo $FWRE_WORK        # 應該是空的,或是 /home/你的名字/fwre-work
unset FWRE_WORK        # 清掉,用預設值
make unpack
```

### 10.8 `unsquashfs` 回傳非零 / 一堆 `created 0 devices`

**正常。** 見 [§6](#6-part-2--解包韌體) 的說明。只要看到 `extracted: N files ... M symlinks` 而且 M > 0 就是成功。

### 10.9 Ghidra 說 `GHIDRA_INSTALL_DIR is not set`

環境變數還沒生效。**關掉 PowerShell 重開**,或當場設:

```powershell
$env:GHIDRA_INSTALL_DIR = "$env:LOCALAPPDATA\fwre-tools\ghidra_12.1.2_PUBLIC"
```

### 10.10 Ghidra 說 `binary not found` 而路徑看起來是對的

`\\wsl$\...` 路徑要求 WSL **正在執行**。先隨便跑一下讓它起來:

```powershell
wsl -d Ubuntu-24.04 -- true
```

還有,路徑裡的使用者名稱要對:

```powershell
wsl -d Ubuntu-24.04 -- whoami
```

### 10.11 `make test` 有測試被跳過(skipped)

在 Windows 上跑測試才會這樣 —— 建立符號連結在 Windows 需要特殊權限。**在 WSL 裡跑就不會**。

### 10.12 空間不夠

下載快取跑完就可以刪:

```powershell
Remove-Item -Recurse -Force "$env:LOCALAPPDATA\fwre-setup"     # 省 742 MB
```

WSL 端要清解包結果:

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

**症狀:** 板上其他焊點一碰就化,天線那條線的焊點加熱到 450°C 只有一點點形變。

**原因:不是溫度,是熱容量。**

那個焊點的另一端接的是 **RF 接地銅箔** —— 整片地平面加上底下的過孔陣列,對烙鐵頭
來說就是一片散熱片。熱流進去的速度比流走的速度慢,焊點永遠停在 150–200°C。
面板顯示的 450 是**烙鐺尖端**的溫度,不是焊點的溫度。

一起在害你的還有:

- **細錐頭接觸面積太小**(約 1 mm²),傳熱功率正比於接觸面積
- **家用烙鐵沒有閉迴路溫控**,感溫在加熱棒不在尖端,一碰大銅面尖端就掉到 250°C 以下
- **450°C 反而更難焊** —— 助焊劑在你需要它工作之前就碳化燒光了
- 同軸線的網狀屏蔽層本身也是散熱片

熔點順帶釐清:有鉛 Sn63Pb37 是 **183°C**,無鉛 SAC305 是 **217–220°C**。
**兩個都遠低於 450,所以熔點從來不是問題。**

**解法:別拆。**

這個專案裡拆天線**不對應 G2 任何一格**,而且天線的同軸線終點是 RTL8188ER 的
輸出級 —— 拆掉之後通電等於讓功率放大器對著開路發射。這台機器是 G2 和 G4 的
單點故障,沒有第二台。

真的需要拆大焊點時,正確做法是**反直覺的:先「加錫」,不是先「吸錫」**——
換刀頭(2.5–3 mm)→ 塗助焊劑 → 灌一坨新的**有鉛**錫進去(合金熔點被拉低,
而且形成液態熱橋)→ 溫度回到 **350–370°C** → 大銅面從背面用熱風槍 180–200°C
預熱。**450°C 已經在燒板子了** —— 焊盤底下的膠 250°C 就開始軟化,撐夠久焊盤會
整片跟著烙鐵起來。

**要練拆焊,去找一塊報廢板,不要拿唯一的目標練。**

### 10.15 usbipd 裝好了,但 PowerShell 說找不到

**症狀:**

```
usbipd : The term 'usbipd' is not recognized as the name of a cmdlet ...
```

**原因:** 安裝程式改了系統 PATH,但**已經開著的終端機不會重新讀 PATH**。

**解法:** 關掉 PowerShell 重開。急著用的話直接給完整路徑:

```powershell
& "C:\Program Files\usbipd-win\usbipd.exe" list
```

先確認到底裝了沒,再決定是 PATH 問題還是安裝問題:

```powershell
winget list --exact --id dorssel.usbipd-win
```

```
Name       Id                 Version Source
---------------------------------------------
usbipd-win dorssel.usbipd-win 5.3.0   winget
```

### 10.16 `flashrom --version` 說 `unknown`

**症狀:**

```
$ flashrom --version
flashrom unknown on Linux 6.6.87.2-microsoft-standard-WSL2 (x86_64)
```

**原因:** Debian/Ubuntu 打包時沒把版本字串編進去。**不是壞掉**,功能完全正常。
套件管理員知道真正的版本:

```bash
dpkg -s flashrom | grep -i '^Version'
```

```
Version: 1.3.0-2.1ubuntu2
```

**這一條值得記下來的地方不是解法,是它戳破了一個規則。**
G0 的宣稱是「**每個工具都用『跑跑看』來驗證,不是檢查檔案在不在**」——
而 `flashrom` 是這張表裡**唯一一個版本號不是跑出來的**。功能上無所謂,
但 `PROGRESS.md` 的 G0 表應該說清楚那個 `1.3.0` 是哪裡來的,
而不是讓人以為做了一個其實沒做的檢查。

### 10.17 電壓量到 `0.x` 在跳,而且怎麼量都不對

**症狀:** 量 UART 腳位對地電壓,四支腳全部讀到 `0.多` 而且一直跳。

**原因:檔位。** 手動檔電表上,轉盤的數字是那一檔**能顯示的最大值**:

| 檔位 | 最大 | 量 3.3V |
|---|---|---|
| `200m` | **0.2 V** | ❌ 差 16 倍 |
| `2000m` / `2` | 2 V | ❌ |
| **`20`** | **20 V** | ✅ |

**這一條最危險的地方不是差 16 倍,是它不會報錯。** 停在 200mV 檔量 3.3V,
回給你的是一個會漂的 `0.x` —— 那個形狀跟一個真實的、有雜訊的低電壓讀數
一模一樣,你會去懷疑板子、懷疑探針、懷疑自己。

**解法:先量一顆已知的電池。**

```
V⎓ 20V 檔 → AA 電池 → 應該讀 1.5 左右
```

讀到了 → 表和檔位都好 → 問題一定在板子那側。
讀不到 → 先修表,板子的事全部往後排。

> **用已知量驗證儀器,再拿它去量未知量。**
> 這跟 §12 那條「先看 `self_check`,但 `self_check` 本身也會騙人」是同一件事。

### 10.18 電阻讀到孤零零一個 `1`

**那是「超出量程」,不是 1 歐姆。** 畫面左邊一個 `1`、後面沒有小數點和其他位數。

換高一檔(200 → 2k → 20k → 200k → 2M),看它在哪一檔進入量程。
**在哪一檔進入量程本身就是資訊** —— 訊號腳通常在 20k 檔顯示出 4.7k / 10k / 15k
之類的上拉電阻值。

順便一個免費的檢查:**這個讀數在物理上合不合理?**
訊號腳對地 1Ω 等於短路,那塊板不會動 —— 光憑這點就知道 `1` 不是 1Ω。

### 10.19 `usbipd attach` 說「沒有 WSL 2 發行版在跑」

**症狀:**

```
usbipd: error: There is no WSL 2 distribution running;
keep a command prompt to a WSL 2 distribution open to leave it running.
```

**原因:** `wsl -d Ubuntu-24.04 -- <指令>` 這種呼叫是跑完就結束的,
而 `attach` 需要發行版**持續開著**。

**解法:** 先把它釘住,再 attach。

```powershell
Start-Process -WindowStyle Hidden wsl -ArgumentList "-d","Ubuntu-24.04","--","sleep","7200"
usbipd attach --wsl --busid 1-1
```

或者直接開一個 WSL 視窗放著不要關。

另外:`bind` 需要**系統管理員**,`attach` 不用。

### 10.20 PulseView 打不開 fx2lafw 分析儀

**症狀:** 掃描找得到裝置,按 OK 之後 `Failed to open device / generic/unspecified error`。

**先排除三個最常見的**(這次三個都不是):

```powershell
# 1. 驅動綁了沒?應該是 WinUSB
Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like "USB\VID_0925*" }
# 2. 韌體檔在不在?
Get-ChildItem "C:\Program Files\sigrok" -Recurse -Filter "*.fw" | Select Name
# 3. 有沒有程式佔用?
Get-Process | Where-Object { $_.ProcessName -match "pulseview|Logic" }
```

**剩下最可能的原因:FX2 上傳韌體之後會用新的 VID/PID 重新列舉,而那個新 ID
沒有驅動。** Zadig 要做**兩次** —— 一次給上傳前的 ID,一次給上傳後的。

> ⚠️ **這一條在本專案裡沒有被證實。** 我改用 Saleae Logic 2 就通了
> (clone 的 VID/PID 就是 `0925:3881`,原廠軟體認得),所以上面那個原因是推論。
> **要證實的方法:讓 PulseView 跳錯之後不要拔線、不要關程式,那時去列舉 USB,
> 看有沒有冒出一個沒有驅動的新裝置。**

**而且分析儀不在關鍵路徑上** —— baud 在 console 上試四個值兩分鐘就有答案,
判準一樣硬(可讀 vs 亂碼)。不要為了工具卡住主線。

### 10.21 本機全綠,但 CI 還是紅的

**症狀:** push 之前跑過 `make lint test check-reports` 全過,GitHub Actions 還是失敗。

**原因:CI 有四個 job,你手動挑的那幾個目標蓋不到全部。**

| CI job | 本機等價 |
|---|---|
| `fwrecon (lint + tests)` | `make lint test` |
| **`shell scripts`** | **`shellcheck --severity=warning tools/*.sh tools/setup/*.sh`** |
| `toolchain image builds` | `docker build -f docker/Dockerfile .`(要幾分鐘) |
| `committed reports match the tooling` | `make check-reports` |

**解法:**

```bash
make ci        # 上面除了容器建置之外的全部
```

改到 `docker/` 底下的東西時再另外跑一次容器建置。

> **這一條真正的教訓不是「記得跑 shellcheck」。**
>
> 是**「知道該跑哪幾個」本身就不是一種檢查,那是一個遲早會忘的習慣**。
> 我 2026-08-15 那次就是靠記憶挑了兩個目標跑、以為綠了才 push。
>
> 修法不是下次更小心,是**讓「全部」變成一個指令** —— 所以有了 `make ci`。
> 這跟 W04 那條「一個永遠不會觸發的檢查也永遠不會失敗」是同一個形狀:
> **一個要靠人記得去跑的檢查,遲早不會被跑。**

實際踩到的那個警告是 `SC2164`(`cd` 沒有 `|| exit`),而它剛好是
`tools/test-photo-tools.sh` 存在的理由那一類 bug:**如果 `cd` 無聲失敗,
每個「這個一定要失敗」的測試都會因為「找不到檔案」而通過。**

---

## 11. 名詞表

| 名詞 | 白話解釋 |
|---|---|
| **韌體 firmware** | 硬體裡面那套作業系統 + 程式,打包成一個檔案 |
| **rootfs** | 根檔案系統,就是 Linux 的 `/` 那一整棵目錄樹 |
| **SquashFS** | 一種唯讀的壓縮檔案系統,嵌入式裝置最常用 |
| **ELF** | Linux 執行檔的格式(等同 Windows 的 `.exe`) |
| **MIPS** | 一種 CPU 架構,常見於路由器。跟你電腦的 x86 不相容 |
| **端序 endianness** | 多位元組數字在記憶體裡的排列方向。搞錯就全部讀成垃圾 |
| **Boa** | 一個超輕量網頁伺服器,2005 年就停止維護了 |
| **CVE** | 全球通用的漏洞編號,格式 `CVE-年-流水號` |
| **binwalk** | 掃描一個檔案裡藏了哪些已知格式的工具 |
| **Ghidra** | NSA 開源的反組譯工具,把機器碼還原成類 C 程式碼 |
| **符號連結 symlink** | 一個「指向別的檔案」的捷徑 |
| **sstrip** | 一種極限瘦身手法,把 ELF 的 section header 整個砍掉 |
| **JEDEC ID** | 快閃記憶體晶片被問到時**自己回報**的廠商碼+裝置碼。跟印在外殼上的字是**兩個獨立來源** |
| **日期碼 date code** | 印在晶片上的 `YYWW`(年+第幾週)。全板取最新的那顆,就是「組裝時間不早於」的下限 |
| **SOP-8 / mil** | 8 腳表面黏著封裝,有 150 mil 和 208 mil 兩種寬度。**夾具買錯寬度就夾不上去** |
| **磁性元件 magnetics** | RJ45 後面那幾顆黑方塊,乙太網路的隔離變壓器。數量可以反推有幾個網路埠 |
| **section header** | ELF 檔裡描述各區段的目錄。**砍掉程式照跑**,但分析工具會瞎掉 |
| **`system()`** | C 語言裡「執行一個 shell 指令」的函式。**命令注入漏洞的終點** |
| **NX / canary / RELRO / PIE** | 四種防止記憶體漏洞被利用的保護機制。**這台路由器一個都沒有** |
| **G0 / G1** | 本專案自訂的驗收關卡:G0 = 環境好了,G1 = 韌體看懂了 |
| **WSL** | Windows Subsystem for Linux,Windows 裡的真 Linux |
| **冪等 idempotent** | 同一個指令跑幾次結果都一樣,不會重複做或做壞 |

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
make ledger                                      # 重生成 study/test-ledger.md
python3 tools/rtcase.py record --id P3-3 --date 2026-08-20 \
    --verdict confirmed --evidence dynamic --artefact poc/formSysCmd/README.md
python3 tools/rtcase.py freeze                   # 改過預測之後,把新雜湊貼回登記簿
#   --evidence dynamic 才會印 ✅;static 印 🟥。真的送過封包才叫 dynamic
#   沒寫反證條件的項目,record 會直接拒絕 —— 這是刻意的
```

> ⚠️ **看報告先看 `self_check`,但不要只看 `self_check`。**
> W04 的 `BoaArgTrace` 連續錯了三次,三次 `self_check` 都寫 `consistent`。
> 抓到它的不是自我檢查,是**把兩版並排比**:同一份程式碼相隔五年,不可能
> 2015 版有 86 個受污染的呼叫點、2020 版有 0 個。
> **一個永遠不會觸發的檢查,也永遠不會失敗。**

**重要路徑**

| 東西 | 在哪 |
|---|---|
| 專案(文字檔) | `C:\Users\Key20\Desktop\router` |
| 工作資料(二進位) | `~/fwre-work`(WSL 內) |
| 從 Windows 看工作資料 | `\\wsl$\Ubuntu-24.04\home\key\fwre-work` |
| Ghidra | `%LOCALAPPDATA%\fwre-tools\ghidra_12.1.2_PUBLIC` |
| Ghidra 專案 | `%LOCALAPPDATA%\fwre-tools\ghidra-projects` |

---

## 12.5 下一階段開工前要先裝的東西

> W01 **沒有**裝這些,是刻意的 —— 理由寫在 [`PROGRESS.md`](PROGRESS.md) 的
> 「Deliberately not done in W01」。
> **開始 W02 / W05 之前先回來看這節。**

### W02(硬體)開工前

> ✅ **2026-08-14 已完成**(`usbipd-win 5.3.0`)。實際做完的第一天寫在
> [§8.6](#86-part-6--硬體開工料件辨識w02-day-1)。裝完找不到指令是正常的,
> 見 [§10.15](#1015-usbipd-裝好了但-powershell-說找不到)。

零件到貨那天,一次做完:

```powershell
# PowerShell(系統管理員)—— 把 USB 裝置接進 WSL 用
winget install --interactive --exact dorssel.usbipd-win
```

裝完**重開 PowerShell**,確認:

```powershell
usbipd list
```

會列出你插著的 USB 裝置。之後把 USB-TTL 轉接板接給 WSL 的流程是:

```powershell
usbipd list                      # 找到轉接板的 BUSID,例如 2-4
usbipd bind   --busid 2-4        # 只要做一次(需要管理員)
usbipd attach --wsl --busid 2-4  # 每次插拔都要做
```

然後在 WSL 裡:

```bash
ls /dev/ttyUSB*                  # 應該出現 /dev/ttyUSB0
picocom -b 115200 /dev/ttyUSB0   # 常見鮑率:115200 或 57600
```

> 離開 picocom 是 **Ctrl-A 然後 Ctrl-X**。

> ⚠️ **接線前務必先確認電壓是 3.3V,不是 5V。** 接錯會燒掉路由器的 SoC。
> 轉接板上通常有跳線或切換開關。**用三用電表量過再接。**

### W05(動態分析)開工前

**先試輕量的路** —— 工具已經裝好了,不用額外安裝。**W01 收工時實測過,可以動:**

```bash
R=~/fwre-work/extracted/v2.1.2/squashfs-root
sudo cp /usr/bin/qemu-mips-static "$R/"
sudo chroot "$R" /qemu-mips-static /bin/busybox
sudo chroot "$R" /qemu-mips-static /bin/boa --help
```

實際輸出:

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
真正的用法說明,包含 `-c serverroot` 和 `-f configfile` —— 這正是之後要餵它設定檔
把 web 伺服器整個拉起來的入口。

> `qemu-mips-static` 是**大端序** MIPS 用的(`qemu-mipsel-static` 是小端序)。
> 這台機器是大端序,所以用前者 —— 見 [§9 G1 第 3 題](#9-驗收)。
> 用錯的那個會直接說 `Invalid ELF image`。

> ⚠️ 「能啟動」不等於「能完整跑」。`boa` 真的服務請求時會去呼叫 `libapmib.so`,
> 而 apmib 會直接讀快閃記憶體分割區(`/dev/mtd*`),那在 chroot 裡不存在。
> 到時候可能要偽造那些節點,或用 `LD_PRELOAD` 攔掉。**這是 W05 要解的問題,
> 不是現在。**

跑不動再考慮 FirmAE(**全系統模擬**,連 Linux 核心一起跑):

```bash
cd ~ && git clone https://github.com/pr0v3rbs/FirmAE
cd FirmAE && ./install.sh      # 30–60 分鐘
```

---

## 13. 怎麼維護這份文件

**規則:每完成一段新工作,回來更新這份文件,而且要在同一個 commit 裡。**

### 什麼時候一定要更新

| 情況 | 要改哪裡 |
|---|---|
| 加了新的 `make` 目標 | §12 速查表 + 對應的 Part 章節 |
| 加了新工具 / 改版本 | §4 環境建置 + §2 空間需求 |
| 踩到新的坑並解決了 | **§10 疑難排解**(這節最有價值) |
| 進入新的週次(W02、W03…) | 新增一個 Part 章節 |
| 有指令的輸出變了 | 把「應該看到」的區塊更新成真實輸出 |
| 出現新名詞 | §11 名詞表 |

### 三條鐵則

1. **只寫你真的跑過的東西。** 「應該看到」區塊必須是**貼上來的真實輸出**,不是憑印象打的。這份文件的價值全繫於此 —— 一旦有一段是編的,讀者就再也不能信任其他段落。

2. **每個步驟都要有「怎麼知道成功了」。** 只寫指令不寫預期輸出,等於沒寫。

3. **失敗案例跟成功案例一樣重要。** §10 的每一條都省下讀者一小時。踩到新坑就補一條,格式是:**症狀 → 原因 → 解法**。

### 自我檢查

改完之後問自己:

- [ ] 三個月後的我照著打,會不會卡住?
- [ ] 一個沒碰過逆向的人讀到這裡,會不會有名詞看不懂又查不到?
- [ ] 每個指令都有「應該看到什麼」嗎?
- [ ] §14 變更紀錄補了嗎?

---

## 14. 變更紀錄

| 日期 | 週次 | 改了什麼 |
|---|---|---|
| 2026-08-07 | W01 | 初版。涵蓋環境建置、韌體取得、解包、`fwrecon` 報告、Ghidra headless 分析,以及 W01 實際踩到的 13 個坑。 |
| 2026-08-07 | W01 收工 | 新增 §12.5:W02 / W05 開工前要補裝的東西(usbipd、UART 3.3V 警告、qemu chroot 先於 FirmAE)。這三項 W01 刻意沒做,理由記在 `PROGRESS.md`。 |
| 2026-08-07 | W01 收工 | 新增 [`study/QA.md`](study/QA.md) 自我檢核題庫(39 題)。之後每週的問題都往那裡累積。 |
| 2026-08-10 | W03 | §8 改寫:`import.ps1`(匯入+分析)與 `analyze.ps1`(跑腳本)拆開,並加上 `-Label` 為什麼要當資料夾用的說明 —— W01 的寫法會讓第二次匯入無聲蓋掉第一次。 |
| 2026-08-10 | W03 | 新增 §8.5 Part 5:用 `BoaDecompile` 匯出 C、用 `BoaListing` 讀組語,以及「反編譯器出警告時不能信它」的操作方式。 |
| 2026-08-10 | W03 | §12 速查表補上 W03 的四支腳本。`study/QA.md` 增至 60 題。 |
| 2026-08-11 | W04 | §12 速查表補上 `BoaXref`、`BoaArgTrace`、`fwrecon mib`,以及「先看 `self_check`,但 `self_check` 本身也會騙人」這條。 |
| 2026-08-11 | W04 | `study/QA.md` 新增 §8(W04):2020 版授權、`submit-url`、後門帳號、MIB 表,以及三個工具 bug 的自白。 |
| 2026-08-14 | W02 Day 1 | 新增 §8.6 Part 6:硬體到貨後的第一天 —— 順序為什麼要跟著「可逆程度」走、五顆 IC 的絲印、`flashrom` 相容性(附實際輸出)、`usbipd` 確認(附實際輸出)、找到已焊好的 UART 排針,以及**照片進 repo 前的遮蔽規則**。 |
| 2026-08-14 | W02 Day 1 | §10 新增三條真的踩到的坑:**10.14 天線焊點 450°C 化不開**(熱容量 ≠ 溫度,而且本來就不該拆)、**10.15 usbipd 裝好卻找不到**、**10.16 `flashrom --version` 說 `unknown`**(它戳破了 G0「每個工具都是跑出來的」這句話)。 |
| 2026-08-14 | W02 Day 1 | §11 名詞表新增 JEDEC ID、日期碼、SOP-8/mil、磁性元件;§12.5 的 W02 前置作業標記完成。 |
| 2026-08-14 | W02 Day 1 | 新增 §8.6.9:照片的遮蔽與標註全部走腳本(`tools/redact-photo.py`、`tools/annotate-photo.py`),理由跟 W03 不用 Ghidra 截圖一樣。§12 速查表補上這兩支和 `flashrom -L` / `usbipd list`。**兩支工具第一次跑都是錯的,而且都不是自己抓到的** —— 經過寫在 `LOG.md`。 |
| 2026-08-15 | W02 Day 2–3 | 新增 §8.7 Part 7:量腳位(**先驗表再量板**)、量 baud(26µs,以及 52µs=2×26 的自洽檢查)、`usbipd` + `/dev/ttyUSB0`、抓 bootlog、確認 console **沒有 shell**、用 ESC 搶 bootloader、以及 **`FLR`+`DB` 這條不用夾具的 flash 讀取路徑**。全部附實際輸出。 |
| 2026-08-15 | W02 Day 2–3 | §10 新增四條:**10.17 200mV 檔量 3.3V 不會報錯,只會給你一個看起來像真的數字**(解法是先量電池)、10.18 孤零零一個 `1` 是超量程、10.19 `usbipd attach` 需要 WSL 正在跑、10.20 PulseView 打不開 fx2lafw(**這條沒有被證實,如實標註**)。 |
| 2026-08-15 | W02 Day 2–3 | §12 速查表新增序列 console 全流程,含 **`FLR` 十六進位 / `DB` 十進位**這個會安靜產生錯誤資料的坑。`study/QA.md` 新增 §10。 |
| 2026-08-15 | 收工後 | 新增 **`make ci`**(§9、§12)和 §10.21。起因是本機跑了 `make lint test check-reports` 全綠就 push,CI 還是紅的 —— **CI 有四個 job,靠記憶挑目標跑不是檢查,是遲早會忘的習慣。** |
| 2026-08-16 | W02 Day 4 | 新增 §8.7.9:完整 4 MiB dump 走 `tools/console-dump.py`(陽性對照、逐塊驗證、抽驗重讀、拼不完整就不吐檔案)。附兩個當天踩到的坑:**ESC 會塞住 bootloader 的輸入緩衝區,搶到之後第一條指令必定失敗**;以及**不要照 `notes/` 的引用寫解析器 —— §8.7.8 這裡的 transcript 才是逐字的**。 |
| 2026-08-16 | W02 Day 4 | §12 速查表新增 W02 Day 4 全流程與兩支不需要硬體的守衛套件。CH341A 量出來是未改的 5V 板(CS/CLK/DI 全 5V,只有座上 VCC 是 3.3V),3.3V 魔改後仍是 5V、**原因未隔離**,決定改走零風險的 console 路 —— 經過寫在 `LOG.md`。 |
| 2026-08-17 | W05 Day 0 | 新增 **§8.10 測試登記簿**（G3.75）：`rtcase check / record / render` 三個指令、反證條件怎麼寫（好例 vs 壞例）、改預測要同一個 commit 重算雜湊、紀錄卡格式、六個會踩到的坑。**這一列是跟§8.10 同一個 commit 寫的** —— W04-2 就是在新增 §8.8/§8.9 的那個 commit 裡漏了這張表。 |
| 2026-08-17 | W05 Day 0 | §9 驗收新增 G3.75；§12 速查表新增 `make rtcase` / `make ledger` / `make rtcase-test`。`study/QA.md` 新增 §13。 |
| 2026-08-16 | W04-2 | 新增 §8.8:把這台自己的 `boa` 讀進 Ghidra 跑五種量測、解碼 `COMPCS`/`COMPDS`、以及 `BoaGate` 為什麼一定要帶 `control:`。 |
| 2026-08-16 | W04-2 | 新增 §8.9:G3.5 最後一格 `FLW` 回復路徑演練的逐字步驟,含三條保護措施。**這一格還沒做。** |
| 2026-08-16 | W04-2 補課 | 新增 §8.8.4:廠商映像重抓、從 `Zone.Identifier` 讀 provenance、`tools/zipprefix.py`,以及一份 40% 殘檔**撐得到哪裡**(兩個 section 完整,截斷的是 rootfs)。§12 速查表補上 `zipprefix`。 |
| 2026-08-16 | W04-2 補課 | 新增 §8.8.5:`fwrecon web` —— 把 W01 留下的 `w6cg` 格式做完(64B header,長度欄在 `+0x3c` 且是 big-endian)。§12 速查表補上。兩個坑寫在該節:**`self_check` 不是 `exact` 就不要用它的數字**;以及 **`--grep` 逐筆搜內容,不是搜整塊** —— 用整塊 grep 會在 2018 那份裡「找到」一個不存在的 `syscmd.htm`。 |
| 2026-08-16 | W04-2 補課 | `make lint` 與 CI 補掃 `tools/*.py`。**那幾支獨立腳本一直不在任何 lint 範圍內** —— 它們不在 `fwrecon` 套件裡,ruff 往上找設定檔永遠找不到 `tools/fwrecon/pyproject.toml`,所以是用預設規則掃的,等於幾乎沒掃。改成用 `--config` 指同一份設定(不另開一份會漂移的),掃出 `console-dump.py` 一個 `B007`,已修。 |

> **上面三列裡的前兩列是補登的,而漏登的方式值得記一筆。** §8.8 和 §8.9 是
> 2026-08-16 的「document sync」commit 加進這份文件的,那個 commit **改了
> RUNBOOK 卻沒有回頭補這張表**;接著又落了兩個 commit 的真工作,兩個都沒有
> 再同步 RUNBOOK 和 `LOG.md`。
>
> 病因不是忘記,是**把「document sync」當成一週過一次的關卡,而不是隨時要
> 成立的狀態**。§13 那條規則(「每完成一段新工作,回來更新這份文件,而且要在
> 同一個 commit 裡」)存在的理由就是防這個,而它在規則本身被重寫進 `CLAUDE.md`
> 的同一週失效了。§13 的自我檢查清單最後一項是「§14 變更紀錄補了嗎?」——
> 那一項當天沒有被執行。

---

## 接下來

| 文件 | 內容 |
|---|---|
| [`README.md`](README.md) | 專案總覽與主要發現 |
| [`PROGRESS.md`](PROGRESS.md) | 每週關卡進度 |
| [`LOG.md`](LOG.md) | 逐日工作紀錄,**包含所有走錯的路** |
| [`notes/anatomy-n150rt.md`](notes/anatomy-n150rt.md) | 韌體結構完整解剖 |
| [`notes/prior-art.md`](notes/prior-art.md) | 前人研究:誰在什麼時候發現了什麼 |
| [`notes/attack-surface.md`](notes/attack-surface.md) | 攻擊面地圖 |
| [`notes/ghidra-triage.md`](notes/ghidra-triage.md) | Ghidra 裡該先看哪些函式 |
| [`notes/dispatch-table.md`](notes/dispatch-table.md) | **`root_form[]` 全表** —— 兩個版本的每一個 `/boafrm/` 路由 |
| [`notes/auth-flow.md`](notes/auth-flow.md) | **Boa 怎麼決定你可不可以進來** —— W03 最重要的一份 |
| [`notes/sink-inventory.md`](notes/sink-inventory.md) | 危險函式呼叫點清單,依可利用性排序 |
| [`notes/formSysCmd-analysis.md`](notes/formSysCmd-analysis.md) | 那個不存在的 CVE 端點,以及三條線索為什麼都指錯方向 |
| [`notes/skt-analysis.md`](notes/skt-analysis.md) | 2015 後門完整拆解:port、暗號、和它存在的那一行 `iptables` |
| [`study/QA.md`](study/QA.md) | **自我檢核題庫** —— 每一條主張配一個「想推翻它的人會怎麼問」,答案是折疊的 |
