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
| [8](#8-part-4--ghidra-靜態分析) | **Part 4** — Ghidra 靜態分析 | 5 分鐘 |
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

### 跑自動分析

```powershell
cd $env:USERPROFILE\Desktop\router

.\ghidra\import.ps1 -Label 2.1.2 `
  -Binary \\wsl$\Ubuntu-24.04\home\key\fwre-work\extracted\v2.1.2\squashfs-root\bin\boa
```

> 📌 `\\wsl$\Ubuntu-24.04\home\key\...` 是**從 Windows 看 WSL 檔案**的路徑。
> `key` 換成你的 Linux 使用者名稱(在 WSL 裡打 `whoami` 可以查)。
>
> 這樣做的用意:資料**只有一份**,躺在 WSL 的 Linux 檔案系統上,Windows 這邊只是讀它。不會有兩份不同步的問題。

**應該看到:**

```
 ==>  importing \\wsl$\...\bin\boa as boa-2.1.2

  ok   language        MIPS:BE:32:default
  ok   image base      00400000
  ok   functions       809
  ok   strings matched 360 of 3337
  ok   wrote           ...\reports\ghidra-strings-2.1.2.json
```

⏱ 約 1 分鐘(自動分析本身 39 秒)。

再跑 2020 版:

```powershell
.\ghidra\import.ps1 -Label 3.4.0 `
  -Binary \\wsl$\Ubuntu-24.04\home\key\fwre-work\extracted\v3.4.0\squashfs-root\bin\boa
```

**`MIPS:BE:32:default` 這行很重要** —— `BE` = Big Endian。Ghidra 自己從檔案標頭判斷出來的,跟我們前面用別的方法算出來的答案一致。**兩個獨立來源得到同一個答案,才敢當結論用。**

### 這份 JSON 有什麼用

它列出每個關鍵字串「被程式的哪個函式用到」。這把「這個 522 KB 的檔案裡有這些字」變成「**該打開哪幾個函式來看**」。

```powershell
wsl -d Ubuntu-24.04 bash -c "cd /mnt/c/Users/Key20/Desktop/router/reports && jq -r '.matches[] | select(.value|test(\"syscmd\";\"i\")) | \"\(.address) \(.value)\"' ghidra-strings-2.1.2.json"
```

完整的「該看哪些函式、為什麼」整理在 [`notes/ghidra-triage.md`](notes/ghidra-triage.md)。

### 打開圖形介面自己看

```powershell
& "$env:LOCALAPPDATA\fwre-tools\ghidra_12.1.2_PUBLIC\ghidraRun.bat"
```

第一次開會問你要不要建專案 —— 選 **File → Open Project**,路徑在:

```
%LOCALAPPDATA%\fwre-tools\ghidra-projects\totolink-n150rt.gpr
```

裡面已經有 `boa-2.1.2` 和 `boa-3.4.0` 分析好了。雙擊打開,按 `G` 可以跳到指定位址。

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
make verify test lint check-reports
```

```
  ok   G0 GREEN — all tools functional
58 passed in 0.43s
All checks passed!
reports OK — 2 fwrecon (schema 1.0), 2 Ghidra
```

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
make test          # 58 個測試
make lint          # 程式碼風格
make check-reports # 報告有沒有跟工具脫節
make help          # 列出所有指令

# ── Ghidra(回到 PowerShell)────────────────────────────
.\ghidra\import.ps1 -Label 2.1.2 -Binary \\wsl$\Ubuntu-24.04\home\key\fwre-work\extracted\v2.1.2\squashfs-root\bin\boa
.\ghidra\import.ps1 -Label 3.4.0 -Binary \\wsl$\Ubuntu-24.04\home\key\fwre-work\extracted\v3.4.0\squashfs-root\bin\boa

# ── 單獨用工具 ────────────────────────────────────────
~/fwre-work/venv/bin/python -m fwrecon image  <韌體.web>
~/fwre-work/venv/bin/python -m fwrecon elf    <執行檔>
~/fwre-work/venv/bin/python -m fwrecon rootfs <解開的目錄>
```

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
