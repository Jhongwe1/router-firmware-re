# 工作日誌

> 這份是給我自己看的。**卡住的地方寫得比做成的地方詳細**——三個月後回頭看,
> 有價值的是「我以為會怎樣、結果怎樣、為什麼」,不是「我裝了什麼」。

---

## 2026-08-07 — W01：偵察與解包

**目標**：過 G0(工具鏈全綠)+ G1(能口述韌體七要素)

**結果**:G0、G1 都過了,而且做出了計畫外的東西。

---

### 做了什麼

- WSL2 Ubuntu 24.04 工具鏈:binwalk v3.1.0(cargo)、unblob 26.6.4(pipx)、
  sasquatch v4.5.1-6(ONEKEY 預編 deb)、qemu-user-static、flashrom、picocom
- Windows 端:portable Temurin JDK 21 + Ghidra 12.1.2,全部 SHA-256 釘死
- 抓到**兩個**韌體版本並驗證雜湊
- 解出兩個 rootfs,答完 G1 七要素
- 寫了 `fwrecon`(Python,零執行期相依),58 個測試
- 自己逆出 Realtek `IMG_HEADER_T` 容器格式並寫成 parser
- Docker + GitHub Actions CI

---

### 卡住的地方(這段最值錢)

#### 1. `curl | sh` 把錯誤吞掉了

rustup 安裝失敗,退出碼 7。以為是網路掛了,結果 5 分鐘後手動測 `sh.rustup.rs`
回 200——是瞬斷。

真正的問題是我看不出來:`curl ... | sh` 在 `pipefail` 下,退出碼到底是 curl 的
還是 sh 的,分不清,而且沒留下任何可以檢查的檔案。

**改法**:先下載到 cache、再執行。網路錯誤和安裝錯誤從此分得開。
**教訓**:安裝腳本裡的 `curl | sh` 是反模式,不是因為不安全,是因為不可除錯。

#### 2. binwalk v3 編不過 —— fontconfig

`yeslogic-fontconfig-sys` build.rs panic。binwalk v3 用 plotters 畫熵圖,
plotters 要 fontconfig/freetype。裝 `libfontconfig1-dev libfreetype-dev` 就好。

**教訓**:Rust 工具的系統相依不會出現在 `cargo install` 的文件裡,只會在 build.rs
炸掉的時候出現。

#### 3. 我的 G0 驗證誤報工具壞掉

驗證腳本說 `sasquatch` 和 `unsquashfs` MISSING。實際上兩個都好好的。

原因:`unsquashfs -version` **印出正確版本然後 exit 1**。squashfs-tools 的老毛病。
我用「執行成功」當存在判準,就把好工具判死了。

改用 `-help`(rc=0)。

**教訓**:驗證一個工具「能動」,要先知道它「怎樣算能動」。不能假設 `--version` 回 0。

#### 4. 我的探測腳本自己有 bug(這個最丟臉)

為了查上面那件事,我寫了:

```bash
out=$("$t" "$flag" 2>&1 | head -3)
echo "rc=$?"
```

回報全部 `rc=0`,跟我看到的現象矛盾。因為 `$?` 抓的是 **pipeline 最後一個指令**
(`head`)的退出碼,`head` 永遠回 0。

**教訓**:除錯工具本身也會說謊。當「觀測結果」跟「現象」矛盾時,先懷疑觀測方法。

#### 5. launcher 把退出碼吃掉

我的包裝腳本最後一行是 `echo "exit code: $?"`,所以腳本自己的退出碼是 `echo` 的
= 0。背景任務回報「成功」,實際上裡面炸了。連錯兩次才發現。

**教訓**:任何包裝腳本都要 `exit "$rc"`。

#### 6. **`readelf` 在無聲說謊** ← 今天最重要的一件事

我用 `readelf --dyn-syms` 掃兩個版本的 boa,找危險函式 import。

- V2.1.2:181 個 UND 符號,含 `system`、`popen`、`strcpy`……合理
- V3.4.0:**0 個**

我差點就寫下「2020 版移除了所有危險 import」。那會是完全錯誤的結論。

真相:V3.4.0 的 boa 被 **`sstrip`** 過,`e_shnum == 0`,section header 整個沒了。
`readelf` 靠 section header 回答問題,找不到就**印空白、回傳 0**。而 `nm -D` 走
`PT_DYNAMIC`,照樣列得出 `U system`。

```
$ readelf --dyn-syms bin/boa    # 什麼都沒有,exit 0
$ nm -D bin/boa | grep system   # U system
```

**教訓**:「工具沒回報問題」不等於「沒有問題」。無聲失敗比大聲失敗危險得多。
**行動**:這件事直接催生了 `fwrecon/elf.py`——自己解析 ELF,只走 program header
和 `PT_DYNAMIC`(即 loader 走的路),這兩個東西 strip 不掉。

#### 7. 然後我自己的 parser 也錯了

`fwrecon elf` 跑 V2.1.2 的 boa:16 imports / **257 exports**。但 `readelf` 說有
181 個 UND。

我把 import 判準寫成 `st_shndx == 0 && st_value == 0`。**MIPS 上這是錯的**:
未定義函式的 `st_value` 存的是 `.MIPS.stubs` 裡 lazy-binding 樁的位址,通常非零。
所以 181 個裡有 165 個被誤判成 export——包含 `system` 和 `strcpy`,正好是這支工具
存在的理由。

ABI 的定義只有一條:`st_shndx == SHN_UNDEF` 就是 import。`st_value` 不該參與判斷。

修完:V2.1.2 的 command-exec binary 從 0 個變成正確的 33 個。

**教訓**:
- 寫了新工具,一定要跟既有工具對答案。我是因為 `nm -D` 說 181、我說 16,才發現的。
- 測試 fixture 要重現「陷阱」,不是重現「教科書案例」。我把 fixture 改成 import 帶
  非零 stub 位址(跟真實 MIPS 一樣),既有測試就自動變成這個 bug 的回歸測試。

#### 8. 工具的假陽性 / 假陰性

跑真實韌體後才看得出來的兩個問題:

- **gzip 假陽性**:`\x1f\x8b` 只有 16 bit,在壓縮資料裡到處都是。在 LZMA kernel
  裡報了一個不存在的 gzip。加上 deflate method byte(`\x08`)就乾淨了。
- **`/init` 被當成 shell script 解析**:它其實是 busybox ELF,結果報告裡出現一整行
  反編譯亂碼。改成看內容(有 NUL byte 就跳過)而不是看檔名。

**教訓**:單元測試過了不代表工具對。要拿真實資料跑,而且要**讀輸出**,不能只看有沒有
crash。

#### 9. winget 裝 JDK 卡在 UAC

`winget install EclipseAdoptium.Temurin.21.JDK` 走 MSI,要管理員權限,跳 UAC 就卡死。
改成下載 Temurin **portable ZIP** 解到 `%LOCALAPPDATA%`,不用權限,而且能釘 SHA-256。

**教訓**:要能無人值守執行的東西,別走需要提權的安裝路徑。

#### 10. PowerShell 5.1 的 `2>&1` 陷阱

`& $javaExe -version 2>&1` 讓驗證腳本掛掉——JDK 和 Ghidra 明明都裝好了。
Windows PowerShell 5.1 對原生程式做 stderr 重導向,會把每一行包成 ErrorRecord,
配上 `$ErrorActionPreference='Stop'` 就變成終止錯誤。

`java -version` 寫 stderr(歷史包袱),JDK 9+ 的 `java --version` 寫 stdout。改用後者。

---

### 學到什麼(技術面)

- Realtek `.web` 是 `cvimg` 容器:每段 16-byte big-endian header
  `{signature[4], startAddr, burnAddr, len}`。`burnAddr` 直接給出 flash 佈局——
  這是之後拿實體 dump 對照的依據。
- **SquashFS 4.0 的 on-disk 格式規定就是 little-endian**,不管 CPU 端序。所以
  big-endian MIPS 韌體裡看到 `hsqs` 是正常的,不是矛盾。v3 才是端序相依的。
- 兩份韌體的 SquashFS `mkfs_time` 都是 2038 年——把 raw 值 byte-reverse 之後,
  數值幾乎等於檔案系統大小。八成是廠商 build script 把 size 寫進 timestamp 欄位。
  結論:**這些映像不能用自己的 metadata 定年**。

### 學到什麼(方法面)

今天六個 bug 裡,有四個是**觀測工具本身出錯**,不是被觀測的東西出錯。
在逆向工程裡這個比例大概是常態,因為每件事都是間接觀測。

實務原則:**任何結論都要有兩個獨立來源**。今天救我的分別是
`nm -D` vs `readelf`、`nm -D` vs `fwrecon`。

---

### 意外收穫

原本只打算「解包 + 記錄」,結果拿到了 2015 和 2020 兩個版本,跨越 2019-12 揭露事件,
可以做真正的前後對照:

- **2015 版(揭露後 5 週)**:`/bin/skt` 後門還在,只是 `rcS` 裡那行被註解掉(`#skt&`)。
  「拿掉後門」和「不再啟動後門」是兩件事,他們只做了第二件。
- **2020 版(全面揭露後 9 個月)**:`/web/config.dat` 是指向 `/var/config.dat` 的
  symlink,而 `rcS` 會 `cp -rf /web/* /var/web/`。也就是 CVE-2019-19822 的暴露路徑
  在結構上還在。

  ⚠️ **這還不能說「沒修」**。修法也可能在 Boa 的請求授權邏輯裡,而不是檔案佈局。
  要在 W03 進 Ghidra 確認。先記錄證據,不要超譯。

---

### 收工前多做的十分鐘(結果比預期好)

寫 RUNBOOK 的時候我寫了一道 `qemu-mips-static` + chroot 的指令,按照自己定的規則
「只寫跑過的東西」,就去實測了一下。結果:

```
$ sudo chroot $ROOTFS /qemu-mips-static /bin/busybox
BusyBox v1.13.4 (2015-08-11 17:26:34 CST) multi-call binary

$ sudo chroot $ROOTFS /qemu-mips-static /bin/boa --help
Usage: /bin/boa [-c serverroot] [-d] [-f configfile] [-r chroot] [-l debug_level]
```

**2015 年的大端序 MIPS 執行檔,在我的 x86 筆電上跑起來了。** 而且 `boa` 吐的是它
自己真正的用法說明,不是崩潰訊息。

這把計畫書裡列為 W05 風險的「模擬環境」先解掉一半 —— 大概率**不需要 FirmAE**
(全系統模擬,要裝 30–60 分鐘)。

⚠️ 但別高興太早,講清楚這證明了什麼:**只證明「載得起來、跑得動」**。真的要服務
HTTP 請求時,`boa` 會呼叫 `libapmib.so`,而 apmib 會直接讀 `/dev/mtd*` 快閃記憶體
分割區 —— chroot 裡沒有那些東西。那是 W05 要處理的。

**方法上的收穫**:我原本只是要驗證文件裡的一行指令,結果順手把下下週的一個風險
提前解掉了。**「只寫你跑過的東西」這條規則的價值,不只是文件正確,而是它逼你真的
去跑。** 這次是撿到,但邏輯上不是偶然。

### 明天 / 下一步

1. Ghidra:找 Boa 的 handler dispatch table,把 `formSysCmd` 的真實註冊名挖出來
   (字串表裡沒有 `formSysCmd`,但 `sysCmdselect`、`/tmp/syscmd.log` 都在)
2. 確認 Boa 對 `.dat` 路徑到底有沒有做認證檢查
3. 逆 `libapmib.so` 的 `COMPCS` 格式
4. 硬體到貨後:量 UART、讀 flash 型號(驗證 2MB vs 3.57MB 的矛盾)、dump 出來跟
   `burnAddr` 佈局對照

### 待辦(不緊急但別忘)

- [ ] archive.org 那份 V2.1.2,`r6cr` 宣告長度比檔案多 9 bytes。是上傳者截斷,還是
      長度欄位含某種 trailer?找第二份來源比對
- [ ] Softpedia 的 2.1.1 / 2.1.3 / 2.1.6 有 interstitial 擋腳本下載,手動抓
- [ ] `w6cg` 那個 web bundle 的封裝格式只看了個大概,還沒寫 parser
- [ ] kernel(LZMA @ `cr6c+0x2808`)還沒解
