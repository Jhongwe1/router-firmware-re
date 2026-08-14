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

---

## 2026-08-10 — W03:Ghidra 靜態逆向上半

**背景**:W02 的硬體還沒到。計畫書寫「G2 過不了不准進 W3」,但 G2 的通過標準
本來就允許「官方韌體主路徑 + 誠實記錄」,所以硬體不是知識上的前置條件,只是
時間上的。先做 W03。

**結果**:本週 DoD 五項全過,而且 W04 的 G3 八格裡有七格順便解掉了。

---

### 做了什麼

- 把 `root_form[]` 分派表從兩個 build 裡挖出來(2015 版 59 個 handler、
  2020 版 49 個),並且**用「誰讀這張表」當證據**分辨它跟 ASP 變數表
- 把 handler 全部命名寫回 Ghidra 專案(185 個),不是手動改 5 個
- 讀完 `process_header_end`、`translate_uri`、`handleForm`、`formLogin`、`formWsc`
- 逆完 `/bin/skt`(10 KB,36 個函式,可以整支看懂)
- 新增 4 支 Ghidra 腳本:`BoaFormTable`、`BoaSinks`、`BoaDecompile`、`BoaListing`

---

### 今天最重要的一件事:**授權檢查是拿 URI 做子字串比對**

`process_header_end` @ `0x0040be0c`,整個授權區塊的進入條件是
`strstr(uri, "htm") != NULL`:

```
0040c23c  jalr t9                  -> strstr
0040c248  beq v0,zero,0x0040c3a0                 ; 回 NULL 就跳過整段檢查
```

所以路徑裡沒有 `htm` 三個字的東西,**完全不檢查**:`/config.dat`、`/ca.cer`、
還有全部 59 個 `/boafrm/form*`。

CVE-2019-19822 的公告寫的是現象——「`.dat` 檔沒有被限制」。這裡是原因,而且
範圍比公告大得多:`.dat` 根本不是特例,它只是「不是 .htm」。

⚠️ **這是靜態結論**。機器還沒開過。要證實只需要三個 `curl`,寫在
`notes/auth-flow.md` 最後。在那之前,只能說「程式碼是這樣寫的」,不能說
「機器是這樣跑的」。

---

### 卡住的地方(這段最值錢)

#### 1. W01 的 `import.ps1` 把自己的輸出蓋掉了

想重用 W01 建好的 Ghidra 專案,結果裡面**只有一個 program**,叫 `boa`。

原因:`analyzeHeadless -import <path>` 是用**檔名**命名 program 的。兩個版本的
`boa` 都叫 `boa`,加上 `-overwrite`,第二次匯入就把第一次的無聲蓋掉。
`import.ps1` 裡明明算了 `$programName = "boa-$Label"`,但那個變數**從頭到尾沒被用到**。

W01 產出的 JSON 其實是對的(各自在自己那次匯入時寫出),但兩個檔案的 `program`
欄位都是 `"boa"`,**除了檔名以外沒有任何東西能證明哪個是哪個**。

改法:每個版本一個 project folder;而且每份 Ghidra 報告都帶上被分析檔案的
SHA-256,`check-reports.py` 現在強制要求。

**教訓**:一份無法指認自己輸入的報告,不是證據。而且「變數算了沒用到」這種 bug,
編譯器不會抓,腳本語言更不會。

#### 2. sink 統計第一版是假陰性 ← 跟 W01 的 `readelf` 是同一種錯

第一次跑出來:V2.1.2 有 **589** 個 `strcpy` 呼叫點,V3.4.0 有 **1** 個。

我差點就寫「2020 版把不安全字串複製都拿掉了」。但 `nm -D` 明明說 V3.4.0 還在
import `strcpy`,而且兩個 build 是同一份程式碼、大小只差 11%,`sprintf` 兩邊都是
694 個。**一邊在說謊。**

真相在 ELF 裡:

| | V2.1.2 | V3.4.0 |
|---|---|---|
| section header | 29 個 | **沒有**(`sstrip` 過) |
| `DT_MIPS_PLTGOT` | 沒有 | `0x472ac4`,有真的 PLT |
| 呼叫方怎麼到 `strcpy` | Ghidra 建了叫 `strcpy` 的 thunk | `jal` 到一個**沒有名字**的 PLT stub |

沒有 section header,Ghidra 找不到 `.plt` 去標它的每一項,結果只有部分 PLT 項目
被建成函式——`system`、`sprintf` 有,`strcpy`、`strcat` 沒有。

修法不用猜。MIPS 的 PLT entry 是四道指令,每個欄位都由 GOT slot 位址 `S` 決定:

```
lui   $15, %hi(S)        3C 0F hi
lw    $25, %lo(S)($15)   8D F9 lo
addiu $24, $15, %lo(S)   25 F8 lo
jr    $25                03 20 00 08
```

所以我是**把 signature 算出來**再去記憶體找,而且規定「只能命中一次,命中兩次或
零次就不採用」。修完:587 vs 577,兩個 build 對得上了。

修之前先量過:`jal = 9979`、`jalr = 16`。幾乎全部都是直接跳 PLT,所以根本不需要
去解 `gp`——**先量再修,不要先猜**。

順手還修了兩件事:
- 從**函式外面**來的 data reference 是 GOT 欄位,不是呼叫點。就是它讓 `strcpy`
  回報「1」而不是誠實的「0,而且 0 是錯的」。
- 報告加了 `self_check`:如果某個 symbol 明明被 import 卻找不到呼叫方,整份檔案
  標成 `SUSPECT`。

**教訓**:工具回報「0」也是一種主張,要跟其他主張一樣被質疑。這已經是這個專案
第二次栽在同一件事上了(W01 是 `readelf` 對 sstrip 過的 ELF 印空白)。

#### 3. 公開的 SDK 原始碼跟手上的 binary 不一樣

網路上流傳的 rtl819x SDK 把分派表元素宣告成:

```c
typedef struct { char name[80]; void (*function)(request*, int, char**); } form_name_t;
```

名字是**內嵌**的,一項 84 bytes。我本來打算照這個寫 recovery 腳本。

實際上這兩支 binary 是 `char *name`,一項 8 bytes。證據有兩個:`handleForm` 自己
的 `ppuVar5 + 2`(在 `char**` 上就是 8 bytes),還有復原出來的表格項數
(59 / 49)剛好等於 W01 用數字串數出來的數量。

**教訓**:外流的 SDK 是「對眼前 binary 的假設」,不是「規格」。所以腳本寫成
「測試 `[字串指標][可執行位址]` 這個形狀是否以固定間距重複」,而且**要能失敗**——
一支不可能失敗的復原腳本,證明不了任何事。

#### 4. 反編譯器在最關鍵的函式上出警告,而我差點沒看

`process_header_end` 的反編譯輸出頂上掛了三行
`WARNING: Heritage AFTER dead removal` / `Restarted to delay deadcode elimination`。
而它反編譯出來的內容是:拿使用者送的帳密去跟**兩個從來沒被寫入過**的堆疊
buffer(`sp+0x40`、`sp+0x60`)比較,比中了就給 `authorized = 2`(比一般帳號還高一級)。

「binary 真的拿未初始化的堆疊當密碼比」和「反編譯器把填值的呼叫吃掉了」是完全
不同的兩件事。所以我寫了 `BoaListing.java` 去讀組語,結果:整支函式裡對 `sp+0x40`
和 `sp+0x60` 只有三次存取,兩次是拿位址當 `strcmp` 參數、一次是讀第一個 byte。
**沒有任何寫入,位址也從來沒被傳出去過。**

所以它真的在跟未初始化的堆疊比。但**能不能利用是動態問題**,靜態決定不了——
記錄成 W05/W06 的候選,不是結論,而且在證實或否證之前不會報給任何人。

**教訓**:反編譯器自己宣告它有困難的時候,任何從它輸出得到的結論都是猜的。

#### 5. 我的 `string:` selector 無聲地找不到東西

想在 2020 版裡找授權函式,用 `string:AUTHG_IP_ADDR`、`string:getSanvas` 去撈,
回傳 0 個函式。差點就寫「2020 版沒有這些東西」。

其中一半是真的(2020 版確實把 `AUTHG_IP_ADDR`、`countDownPageWizard.htm`、
`notice_frame.htm`、`formLogin.htm` 全刪了,授權那段是重寫的),
但 `getSanvas` 是我的 bug:實際字串是 `setting/getSanvas`,**reference 指向字串
開頭**,我搜子字串命中的是中間那個位址,那裡當然沒有 xref。

**教訓**:自己寫的查詢工具回傳空集合時,先問「是真的沒有,還是我問錯了」。
這跟第 2 點是同一個病。

#### 6. W01 的「最高價值函式」是假陽性

W01 把 `FUN_00440eec`(裡面有 `cp /var/web/config.dat %s`)寫成「W01 找到的
單一最高價值函式」。W03 追下去:它是 `/boafrm/formSaveConfig`,而那個 `%s` 是

```c
sprintf(buf, "/var/web/Config_%s_%04d%02d%02d%02d%02d%02d.bin", "N150RT",
        年, 月, 日, 時, 分, 秒);
```

一個寫死的型號字串加六個 `localtime()` 欄位。**沒有任何請求資料進得去,不是
命令注入。**

有寫進 `sink-inventory.md`。死掉的候選跟活下來的候選一樣要留下來,不然這個專案
就會變成「只記錄成功」的專案。

---

### 學到什麼(技術面)

- **`formSysCmd` 在這台機器上不存在**。不在 2015 的 59 項裡,也不在 2020 的 49 項裡。
  而 `handleForm` 是 `strlen` 相等 + `memcmp` 全等比對,沒有 fallback、沒有第二張表。
  W01 提名的 `FUN_0044c610` 是 **ASP 變數表**裡的 `sysCmdLog`,由 `handleScript` 讀——
  是「顯示 log 的那半」,會執行命令的那半根本沒編進來。
- **真正的命令執行面是 `formWsc`**。`localPin`、`peerPin` 沒過濾也沒長度檢查就進
  `system()`;`targetAPSsid` 有長度檢查(< 33)但被塞進 shell 的雙引號裡沒跳脫。
  同一支函式裡十行前的 `targetAPMac` 卻是逐字元過濾成 hex 又要求剛好 12 長。
  **會寫過濾,但每個參數各自為政**——這就是 ad-hoc 輸入處理的長相。
  而且 2015 和 2020 兩版**一模一樣**,五年沒動。
- **`/bin/skt` 全解了**:聽 TCP **5555**,`hel,xasf` 執行
  `iptables -I INPUT -p tcp --dport 80 -i eth1 -j ACCEPT`,`oki,xasf` 刪掉。
  它不給 shell、也不繞密碼,它是**可達性後門**——把本來防火牆擋住的管理介面打開。
  配上上面那個 `htm` 授權洞,2015 那份映像裡就是一條完整的未認證遠端 root 鏈,
  由兩個各自出貨的缺陷組成。

### 學到什麼(方法面)

W01 的結論是「任何結論都要有兩個獨立來源」。W03 把它變得更具體:

**當兩個來源不一致的時候,不一致本身就是資料。**
- `nm -D`(有 strcpy)vs 我的統計(1 個)→ 指向 sstrip + PLT
- SDK 原始碼(`char[80]`)vs 反編譯(`+2` 步進)→ 指向這台是不同的 SDK 設定
- W01 的字串計數(59)vs 復原出來的表(59)→ 一致,這才是真的可以拿去用的數字

還有一個新的:**復原資料結構 > 累積交叉引用**。`formSysCmd` 那三條線索
(字串不見了、有 log 路徑、有 `sysCmdselect` 頁面片段)全都指向同一個錯誤答案。
把 `root_form[]` 這個結構挖出來,一次就結案了。

### 明天 / 下一步(W04)

1. 2020 版的授權是重寫過的,**還沒讀**。第一步:找出誰呼叫 `FUN_0040b850`
   (吐 `WWW-Authenticate` 的那支)。我的 `callers:` selector 回傳空的,那是工具
   結果不是答案。
2. `libapmib.so` 完全沒讀,而它在本週每一個發現的路徑上。
3. 六個 handler 的 `execl` argv 還沒追。
4. `DAT_0048e9f8` 的大小(401 路徑上那個 `strcpy(全域, URI)`)。
5. 硬體到貨後:用三個 `curl` 驗證這週所有結論。

---

## W04 — 2026-08-11:G3 過了,但過的方式跟預期的不一樣

### 先講結論

G3 五條全過。可是 W03 留下來的兩個開放問題,**答案都跟 W03 猜的相反**:

1. 2020 版**有修**(所有 POST 都進閘門了),但**沿用同一種寫法**,所以又開了一個新洞。
2. 2025 那批 CVE **就是掛在這台機器上的**,不是 W03 寫的「掛在兄弟型號」。

還有一個更難堪的:W01 寫的「兩份映像檔裡都沒有 `/etc/passwd`」是錯的。
兩份都有。而且 2015 那份裡面,**Pierre Kim 2015 公告的後門帳號 `onlime_r` 還在**,
uid 0,雜湊值跟他公告上印的一模一樣。

### 這週最有價值的一件事:三次工具錯誤

新寫的 `BoaArgTrace` 連續錯三次,**三次它自己的 `self_check` 都寫 `consistent`**。

| 第幾次 | 症狀 | 真正的原因 |
|---|---|---|
| 1 | 304 個呼叫點只有 **1** 個被標成「有請求參數流進來」 | 同一套「把 varnode 解成字串」的邏輯寫了兩份,兩份走鐘了 |
| 2 | 2015 版 86 個、2020 版 **0** 個 | `accessor:` 選項拿去跟小寫化的名字比,所以永遠不會相等 |
| 3 | `strcpy` 在 2015 版 151 個、2020 版 **0** 個 | W03 已經在 `BoaSinks` 修過的 sstrip PLT 問題,我重寫了一份沒帶上修正 |

第 1 次抓到,是因為 W03 早就**用手讀出** `formWsc` 有三個參數進 `system()`,
工具卻一個都沒找到 —— 兩個來源不一致。
第 2、3 次抓到,靠的是 CLAUDE.md 那條:**兩版要橫著讀,不要直著讀**。
同一份程式碼相隔五年,不可能 86 → 0。

得到的教訓,寫在這裡因為它比任何一個漏洞都值錢:

> **一個永遠不會觸發的檢查,也永遠不會失敗。**
> `self_check: consistent` 只代表「我檢查的那幾件事沒出問題」,
> 不代表「答案是對的」。

所以做了兩件事:
- 把 PLT 解析抽成 `BoaPlt.java`,**只留一份**。同一個 bug 在這個專案出現兩次,
  就不是 bug 了,是設計問題。
- `BoaArgTrace` 新增 `accessor_declared_but_never_matched`:
  **給了選項卻沒配對到任何東西,現在算錯誤,不算沉默。**

### 一行程式碼 = 兩個 CVE

```c
sprintf(acStack_220, "flash set HW_WLAN0_WSC_PIN %s", localPin);  /* 100 bytes */
system(acStack_220);
```

- 沒過濾 → CVE-2025-3987(命令注入)
- 沒長度檢查 → CVE-2025-4462(緩衝區溢位)

同一行。而且**2015 那份映像檔裡一字不差**,比 CVE 早十年。

`submit-url` 那組更誇張:四個 CVE(3990/3991/3992/3993),其實是**同一段三行的尾巴
複製到 34 個 handler 裡**。有編號的那四個只是抽樣,不是全部。

### `strcpy(p, "/status.htm")` —— 沒人寫進 CVE 的那個

```c
pcVar1 = req_get_cstream_var(param_1, "submit-url", "");
if (*pcVar1 == '\0') {
    strcpy(pcVar1, "/status.htm");   /* 寫進 accessor 回傳的 buffer */
}
strcpy(&lastUrl, pcVar1);            /* lastUrl 只有 100 bytes */
```

`req_get_cstream_var` 找不到參數時,回傳的是**呼叫端給的預設值**,也就是 `""`
那個字面常數 —— 它在 `.rodata`,而 `.rodata` 在 `R E` 的 segment 裡。

所以「POST 過去但完全不帶 `submit-url`」→ 往唯讀記憶體寫 12 bytes → boa 死掉。
2015 版連認證都不用過。

這也順便解釋了一件本來看起來像雜訊的事:**這個型號所有公開 PoC 都帶
`submit-url=/xxx.htm`**。不是為了好看,是不帶就沒有回應。

**但這是靜態讀出來的。** 一個 `curl` 就能證實或推翻,而機器還沒到。

### 2020 版:修了,可是

閘門條件從「URI 含 `htm`」變成「URI 含 `.htm` 或 `.asp`,**或者是 POST**」。
所有 handler 都進去了 —— **這是真的修好了,要講清楚。**

問題是判斷方式沒變,還是拿 `strstr` 掃整條 URI,而豁免名單完全沒有錨定:

```
POST /login/boafrm/formWsc
      ^^^^^ 含 "login"     -> 0x0040a2d8 跳過轉址
            ^^^^^^ 含 "boafrm" -> translate_uri 放行 POST
            ^^^^^^^^^^^^^^^^ handleForm 用 strstr 找 "/boafrm/",再精準比對
```

三個 `strstr`,同一條字串,沒有一個綁開頭。**照程式碼讀,這樣就進 handler 了。**

`GET /config.dat` 更直接:不含 `.htm`、不含 `.asp`、不是 POST → 閘門整段跳過。
CVE-2019-19822 在一份 2020-10-30、也就是全面揭露九個月後的版本裡,還在。

> 這條**沒有回報給任何人**,也不會在 W05/W06 實機或模擬跑出來之前回報。
> 靜態讀三個 `strstr` 不等於漏洞。

### 順手撿到的

- `/etc/privateKey.key`(2020 版):2048-bit RSA 私鑰,自簽憑證 CN=192.168.1.254,
  **2014 年就過期了**,而這份韌體是 2020 年出的。每一台都同一把。
- `/etc/dropbear_rsa_host_key`(2015 版):同樣的問題,SSH host key 全型號共用。
- `root` 的密碼兩版都是 `123456`。Pierre Kim 公告上是 `12345`。
  廠商對「密碼被公開」的回應是加一位數。
- `nobody` 的 uid 和 gid **都是 0**。

### 明天 / 下一步(W05)

1. **W02 還是卡在硬體。** 但 W05 的模擬路線 W01 已經驗過能跑 —— 先把 boa 在
   qemu chroot 底下服起來,`/dev/mtd*` 用假檔案墊。
2. 四個 `curl` 就能結案的東西,列在 `notes/auth-flow-2020.md` 最後。
   其中 `POST /login/boafrm/formWsc` 是整週最重要的一個。
3. 去抓 **V2.1.1-B20150708**(Pierre Kim 說最後一個有洞的版本),
   把它的 `root_form[]` 挖出來 —— 一個指令就能確定 `formSysCmd` 到底是
   「廠商修掉的」還是「本來就沒編進去」。
4. `TELNET_ENABLED` / `SSH_ENABLED` 預設是不是開的?這決定 `root:123456` 值多少。
5. `needReboot`、`run_init_script_flag` 是誰在讀?它們就貼在 `lastUrl` 後面。

---

## W02 Day 1 — 2026-08-14:硬體到貨,而我第一個動作就做錯了

### 先講結論

**W01 贏了一次。** 硬體到貨前三週,W01 從 `.web` 容器自己的 `burnAddr` 表算出
flash map 最高到 3.57 MiB,斷定公開規格寫的 2MB **不可能對**,預測至少 4MB。

今天 `U19` 的絲印是 `cFeon QH32B-104HIP` = EN25QH32B = **32 Mbit = 4 MiB**。

這是這個專案第一次**對物理世界做出可證偽的預測,然後物理世界同意了**。

同一天,計畫書的硬體規格表被打掉三格:SoC 是 **8196E 不是 8196C**、
RAM 晶片是 **32MB 不是 16MB**、flash 是 4MB。三格全部都是從別人的規格抄來的,
沒有一格是量出來的。

**但今天真正值得寫下來的不是這個,是我一開始做錯的事。**

### 今天走錯的路(這段最值錢)

#### 1. 拆機第一個動作是拿 450°C 去燒天線焊點

烙鐵調到 450°C,板上其他焊點一碰就化,天線那個焊點只有一點點形變。
我當時問的問題是:**「是不是材質不同?是不是我不夠有耐心?是不是溫度不夠高?」**

**三個都不是,而且我問錯問題了。**

技術上的答案是**熱容量,不是溫度**:那個焊點另一端是 RF 接地銅箔加過孔陣列,
對烙鐵來說是一片散熱片;顯示的 450 是尖端溫度,焊點大概只有 150–200°C;
而且 450°C 會讓助焊劑在你需要它工作之前就碳化燒光,**溫度越高反而越焊不動**。
有鉛 183°C、無鉛 217–220°C,兩個都遠低於 450 —— **熔點從頭到尾就不是問題**。

但這只是次要的答案。真正該先問的是:

> **我為什麼要拆這條天線?**

我答不出來。G2 要的四樣東西 —— bootlog、SPI dump、dump 對官方韌體、標註過的
PCB 照片 —— **天線在不在板上,一樣都沒有幫助**。

而那條線的終點是 **RTL8188ER 的輸出級**,拆掉通電等於對開路發射;
**而且這台是 G2 和 G4 的單點故障**,W05 要把 web server 服起來、W06 要在實機上
重現 CVE,都靠它,沒有備品。

**寫成規則:任何不可逆的動作,先答出「這一刀換到哪一個 gate 的哪一格」。答不出來就不要動。**

#### 2. 差點把 on/off 開關的線剪掉扭在一起

想法是「剪掉接一起變成常開,插回板子」。**兩個問題:**

第一,**我不知道那兩根線是什麼。** 可能串在 DC 電源路徑上(短接 = 常開,能動),
也可能接到 GPIO(短接的意義取決於極性)。從照片看 `J2` 緊貼著 DC 座,layout
像前者 —— **但那是從照片推的,不是量的**,而量它只要三分鐘。

第二,**就算量出來能短接,還是不該剪。** 接下來抓 bootlog 要反覆斷電重開幾十次,
**一個能用手撥的開關是資產,不是障礙**。我是在把一個乾淨的動作,換成一個會抖、
會斷續、會短到旁邊的動作。

結果:插頭插回去,開關撥 ON。零刀。

#### 3. 還沒拍照就先動烙鐵

**G2 的第四格交付物就是標註過的 PCB 照片,而原廠狀態只有一次機會拍。**
我在拍照之前就先去燒焊點了。這次沒造成損失,是因為焊點沒化開。

### 五顆 IC

| 位置 | 絲印 | 是什麼 |
|---|---|---|
| — | `RTL8196E` `I510VG1` `GF23 TAIWAN` | SoC |
| `U19` | `cFeon QH32B-104HIP` `1750HKB` | EN25QH32B,**4 MiB** SPI NOR |
| — | `Winbond W9825G6KH-6` `1837H` | 256 Mbit SDRAM,**32 MiB** |
| — | `RTL8188ER` `I210QP1 GF08` | 1T1R 802.11n |
| — | `LSC LSP5526` `181525` | **沒查到**。從位置推測是降壓穩壓 |

外加板子層級:4 LAN + 1 WAN、三顆 U&T 磁性元件(2+2+1 = 五個埠,對得上 8196E
內建的交換器)、`ANT1` / `ANT2` 兩個天線腳位但只裝一支、`U6` 附近有沒裝的焊盤。

**最好的消息:板子下緣有一組已經焊好的 4-pin 排針,旁邊絲印直接印著 `UART`。**
整個 W02 一刀都不用焊 —— 本週最大的不可逆風險在還沒開始之前就消失了。

> 但絲印寫 `UART` 只命名了這一組,**沒告訴我四支的順序**。GND/VCC/TX/RX 明天用
> 電表量,不照慣例猜 —— 接錯的代價不對稱,TX/RX 反了只是沒訊號,VCC 接錯可能燒 SoC。

### 今天最容易騙到自己的一件事

`flashrom -L | grep -i en25qh` 回報 `EN25QH32 ... 4096 SPI`。

**這不是「flash 是 4MB」的第二來源,而我差一點就把它當成第二來源。**

`flashrom` 的資料庫是**用料號當索引**的,而料號是我從同一塊晶片上的同一行油墨
讀出來、再打進 `grep` 的。它證明的是「**如果**這顆是 EN25QH32,那它是 4096 KiB」,
不是「這顆是 4 MiB」。**兩個來源共用同一個上游,就只是一個來源。**

**跟 W01 那個坑是同一種:** `readelf` 和 `nm -D` 在 sstrip 過的 ELF 上不是獨立
來源,因為它們讀同一張 section header。

真正獨立的是**晶片自己在 SPI 上回報的 JEDEC ID**。Day 4 才有。
所以今天筆記裡那張表的「第二來源」欄位**五格全是空的**,那是它應該有的樣子。

### 一個工具的小裂縫

`flashrom --version` 印 `flashrom unknown`,而 `dpkg` 說 `1.3.0-2.1ubuntu2`。

功能完全正常(Debian 打包沒把版本字串編進去),但值得記:**G0 的宣稱是
「每個工具都用跑跑看來驗證,不是檢查檔案在不在」—— 而 `flashrom` 是那張表裡
唯一一個版本號不是跑出來的。** 無害,但表格應該說清楚那個數字哪來的,
而不是讓人以為做了一個其實沒做的檢查。

### 照片的處理

PCB 背面條碼是 12 個十六進位字元,**幾乎確定是這台的 MAC**;正面 QR 標籤是序號。
**兩張都要遮掉才能 commit**,而 G2 要交的就是背面那張。

同一條規則接下來還會用兩次:bootlog 會印 MAC(照 W04 的 `HW_WLAN0_WSC_PIN`
來看,很可能連 WPS PIN 一起印),flash dump 的 config 分割區裡全部都有。

**一條規則:從「我這一台」讀出來的東西一律遮,只發表對「這個型號」成立的事實。**
而且要在 `git add` 之前決定 —— 推上去之後才遮的不叫遮。

### 明天 / 下一步(W02 Day 2)

1. **拍照補齊 + 遮蔽 + 標註**,把 G2 第四格結掉。
2. **電表定腳位**:GND(通斷對屏蔽罩)→ VCC(通電後恆 3.3V,**同時確認是 3.3V
   不是 1.8V**)→ TX(開機瞬間會抖的那根)。
3. **邏輯分析儀量 baud**,不要用試的:`baud = 1 / 最窄脈衝寬度`。
   26.04 µs = 38400、8.68 µs = 115200。UART decoder 解出可讀英文字才算確認。
4. **順手把五顆 IC 的第二來源補掉**:`/proc/cpuinfo`、核心記憶體行、
   `LSP5526` 的輸出腳電壓。都在 bootlog 起來的那十分鐘之內。
5. **量 `J2`**,把「串在電源上還是 GPIO」這題結掉。
6. 有空的話寫 `BoaIsa.java`:數 `/bin/boa` 裡的 `LWL`/`LWR`/`SWL`/`SWR`。
   0 次的話,就證明 Realtek SDK 的 toolchain 到 2020 年都還鎖在 Lexra 的子集上 ——
   那才是 W01 的 ELF header 寫 MIPS-I 的真正原因。
   **注意 qemu 跑得起來不能當證據**,子集程式在完整模擬器上兩種情況都會成功。
