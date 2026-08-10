# 自我檢核題庫

> 這份是**給我自己考自己**用的。每次做完一段工作,就把「面試官會怎麼問」的問題丟進來。
>
> **答案是折疊的。先自己講一遍,再展開對答案。**
> 用讀的沒有用 —— 一定要**出聲講完整句**,或是打字寫下來。
> 你以為你懂了但講不出來,在面試現場就等於不懂。

---

## 怎麼用

| 標記 | 意思 |
|---|---|
| 🔵 **基本** | 答不出來代表這段沒讀懂,回去補 |
| 🟠 **理解** | 考「為什麼」,不是「是什麼」 |
| 🔴 **追殺** | 面試官在你答完之後追問的那一句。**這種題才是分水嶺** |
| ⚪ **開放** | 沒有標準答案,考思考方式 |

### 進度追蹤

每次複習完更新這張表。**「講得出來」的標準是:不看筆記,連續講 30 秒不卡。**

| 章節 | 題數 | 上次複習 | 講得出來 |
|---|---|---|---|
| [1. 韌體結構與容器格式](#1-韌體結構與容器格式) | 7 | — | ／7 |
| [2. ELF 與 CPU 架構](#2-elf-與-cpu-架構) | 8 | — | ／8 |
| [3. 工具與方法論](#3-工具與方法論) | 7 | — | ／7 |
| [4. 漏洞與攻擊面](#4-漏洞與攻擊面) | 8 | — | ／8 |
| [5. 工程實踐](#5-工程實踐) | 5 | — | ／5 |
| [6. 開放題](#6-開放題) | 4 | — | — |
| [7. 分派表與授權流程(W03)](#7-分派表與授權流程w03) | 21 | — | ／21 |

---

## 1. 韌體結構與容器格式

### 1.1 🔵 這個 `.web` 檔裡面有什麼?

<details><summary>答案</summary>

三段(2015 版)或兩段(2020 版)結構,每段前面 16 個位元組的標頭:

```c
typedef struct {
    unsigned char signature[4];   /* "cr6c" / "r6cr" / "w6cg" */
    unsigned int  startAddr;      /* 載入到 RAM 的位址 */
    unsigned int  burnAddr;       /* 燒到快閃記憶體的偏移 */
    unsigned int  len;            /* 內容長度,不含標頭 */
} IMG_HEADER_T;
```

**全部是大端序。**

2015 版:`w6cg`(網頁資源,bzip2)→ `cr6c`(核心,LZMA)→ `r6cr`(根檔案系統,SquashFS)
2020 版:`cr6c` → `r6cr`(少了 `w6cg`)

</details>

### 1.2 🔴 你怎麼知道那 16 個位元組的欄位順序是對的?搞不好是 `[tag][len][addr][addr]`?

<details><summary>答案</summary>

**用結構自洽性驗證,不是用猜的。**

如果欄位順序猜對了,那麼:

> 第 N 段的 `payload_offset + len` 應該**剛好**落在第 N+1 段的 signature 上。

實測:2020 版 `cr6c` 的 payload 從 `0x10` 開始,`len = 0x12d802`,
`0x10 + 0x12d802 = 0x12d812` —— 而 `r6cr` 的 signature 就在 `0x12d812`。**分毫不差。**

欄位順序錯的話這個鏈子接不起來。三段全部接得上,而且兩個版本都接得上,基本上排除巧合。

另一個佐證:`burnAddr` 解出來是 `0x10000` / `0x60000` / `0x180000` —— 全部是漂亮的
64 KB 對齊邊界,正好符合快閃記憶體分割區的樣子。如果欄位對調,會得到
`0x80c00000` 當「燒錄位址」,那是 RAM 位址,不可能。

`fwrecon` 的 `test_sections_are_contiguous` 就是把這個檢查寫成測試。

</details>

### 1.3 🟠 `burnAddr` 有什麼用?為什麼不只用 binwalk 掃一掃就好?

<details><summary>答案</summary>

binwalk 告訴你「**檔案裡有什麼**」,`burnAddr` 告訴你「**這東西會被放到晶片的哪個位置**」。

這個差別在 W02 拆機時就是全部:當你用 CH341A 把 flash 讀出來,得到一個 4MB 的原始
映像,你要怎麼知道哪一段是根檔案系統?**就是靠 `burnAddr`。**

它也是「官方韌體 vs 我機器上實際跑的韌體」能對照的唯一依據。

</details>

### 1.4 🔵 為什麼說這台機器的快閃記憶體至少 4MB?

<details><summary>答案</summary>

取所有段落的 `burnAddr + len` 最大值:

```
0x180000 (1,572,864) + 2,174,978 = 3,747,842 bytes = 3.57 MiB
```

塞不進 2MB,所以至少 4MB。

TechInfoDepot 寫 2MB,**要嘛描述的是別的板子版本,要嘛就是錯的**。
W02 拆機看晶片絲印確認。

</details>

### 1.5 🟠 SquashFS 是什麼?為什麼嵌入式裝置都用它?

<details><summary>答案</summary>

**唯讀 + 壓縮**的檔案系統。

- 唯讀 → 沒有寫入路徑,不會因為斷電寫壞;也不用 journal
- 壓縮 → 2.1 MB 的映像解開後是 8 MB,快閃記憶體很貴,這個比例很關鍵
- 支援多種壓縮器 → 這台 2015 版用 LZMA、2020 版用 XZ

代價:要改東西只能重刷整個分割區。所以會變動的資料(設定檔、憑證)都丟到
`/var` 這種開機時建的 tmpfs —— **這正是 `/web/config.dat` 是符號連結的原因。**

</details>

### 1.6 🔴 大端序的 MIPS,為什麼根檔案系統的 SquashFS 標頭是小端序?你是不是讀錯了?

<details><summary>答案</summary>

**沒讀錯,而且這不矛盾。**

SquashFS **4.0 的規格就規定磁碟格式一律小端序**,不管 CPU 是什麼端序,核心驅動負責
轉換。會端序相依的是 SquashFS 3.x,4.0 把 byte-swapping 那套拿掉了。

**「你怎麼確定不是讀錯」—— 三個獨立佐證:**

1. `unsquashfs`(懂這個格式的工具)**乾淨地解開了**。如果端序判斷錯,它會直接罵。
2. 用小端序去解其他欄位,**每一個都合理**:`block_size = 0x00020000 = 131072`,
   而 `block_log = 17`,`2^17 = 131072` —— **兩個獨立欄位互相對得上**。
   端序讀錯的話這兩個不可能同時成立。
3. `inode count = 582`,跟 binwalk 獨立算出來的一樣。

**這題的價值不在答案,在示範「怎麼證明自己沒讀錯」。** 逆向工程幾乎每個結論都是
間接觀測,你必須有能力自我驗證。

</details>

### 1.7 🟠 兩個映像的 SquashFS 建立時間都是 2038 年。這代表什麼?

<details><summary>答案</summary>

代表**這個欄位不能信,這些映像沒辦法用自己的 metadata 定年**。

原始值 `0x802d2100` 和 `0x80ed2000`。把 byte 順序反過來讀是 `0x00212d80`(2,174,848)
和 `0x0020ed80`(2,158,464)—— 分別跟兩個檔案系統自己的大小只差一兩百位元組。

**推測**是廠商的 build script 把「大小」寫進了「時間戳記」欄位,而且端序還寫反。

⚠️ 注意用詞:這是**推測**,我沒有證據。`fwrecon` 的報告裡也是寫 "possibly"。
**能夠說「我不確定」,比硬給一個好聽的答案更專業。**

實務影響:唯一可信的日期來源是檔名(`B20150825` / `B20201030`)。

</details>

---

## 2. ELF 與 CPU 架構

### 2.1 🔵 這台機器是什麼架構?你怎麼知道的?

<details><summary>答案</summary>

**大端序 MIPS32,MIPS-I 指令集,o32 ABI。**

從 ELF 標頭直接讀:
- `e_machine = 8` → EM_MIPS
- `e_ident[EI_DATA] = 2` → ELFDATA2MSB → **大端序**
- `e_flags & 0xF0000000 = 0` → mips1
- `e_flags & 0x1000` → o32 ABI

第二個來源:Ghidra 自己判定的 `MIPS:BE:32:default`,跟我算的一致。

</details>

### 2.2 🟠 端序搞錯會怎樣?

<details><summary>答案</summary>

反組譯出來全是垃圾,而且**不會報錯**——這才是危險的地方。

實例:韌體 `0x50` 位置的位元組是 `3c 10 80 d3`。

- 當**大端序**讀:`0x3c1080d3` → `lui $s0, 0x80d3` —— 合理的 MIPS 指令,而且
  後面跟著 `addiu`,是標準的「載入 32 位元常數」慣用法
- 當**小端序**讀:`0xd380103c` → opcode `0b110100`,是 MIPS64 的 `LD`,
  在 32 位元開機碼裡毫無道理

**所以「指令看起來合不合理」本身就是端序的驗證方法。**

qemu 也一樣:用錯 `qemu-mipsel-static` 會直接說 `Invalid ELF image`。

</details>

### 2.3 🔴 你這個 `elf.py` 為什麼不直接呼叫 `readelf`?重造輪子不是壞味道嗎?

<details><summary>答案</summary>

**因為 `readelf` 在這個專案上會無聲說謊。**

2020 版的 `/bin/boa` 被 `sstrip` 過,`e_shnum == 0` —— section header 整張表被移除。

```
$ readelf --dyn-syms bin/boa     # 什麼都不印,退出碼 0
$ nm -D bin/boa | grep system    # U system
```

`readelf` 靠 section header 回答問題。找不到就印空白、**回傳成功**。
呼叫端會忠實記錄「這個 binary 沒有危險 import」然後往下走。

**這在本專案第一次分析時真的發生了**,我差點寫下「2020 版移除了所有危險函式」
這個完全錯誤的結論。

所以 `elf.py` 只走 **program header + `PT_DYNAMIC`** —— 也就是**動態連結器走的路**。
那兩個東西 strip 不掉,strip 掉程式就跑不起來。

> **這不是重造輪子,是換一個不會在關鍵時刻閉嘴的資訊來源。**

面試時這題答得好的話,展示的是:你知道工具的**失效模式**,而不只是會用工具。

</details>

### 2.4 🔴 你說 MIPS 上判斷 import 只能看 `st_shndx`。那 `st_value` 裡到底放什麼?

<details><summary>答案</summary>

放**該符號的 lazy-binding 樁(stub)位址**,在 `.MIPS.stubs` 區段裡。

MIPS o32 沒有 x86 那種 PLT。呼叫一個還沒解析的外部函式時,會先跳到 `.MIPS.stubs`
的一小段程式,那段再去找動態連結器解析。所以 `.dynsym` 裡的未定義函式,
`st_value` 通常**不是 0**,而是這個樁的位址。

**我踩過這個坑。** 一開始判準寫成:

```python
if st_shndx == 0 and st_value == 0:   # 錯
```

結果 `/bin/boa` 的 181 個 import 有 **165 個被歸類成 export**——包含 `system` 和
`strcpy`,正好是這支工具存在的理由。

ABI 的定義只有一條:**`st_shndx == SHN_UNDEF (0)` 就是未定義符號**,`st_value`
不該參與判斷。

**怎麼發現的:** `nm -D` 說 181 個,我的工具說 16 個。**兩個來源不一致就是警報。**

</details>

### 2.5 🟠 `sstrip` 是什麼?為什麼廠商要做?

<details><summary>答案</summary>

比 `strip` 更激進的瘦身:`strip` 拿掉符號表,`sstrip` 連 **section header table 整張**
都砍掉。

**程式照樣能跑**,因為執行只需要 program header(告訴核心哪段載到哪),
section header 是給連結器和分析工具看的。

廠商的動機通常是省空間(這台 2MB/4MB 的快閃記憶體,每 KB 都在算)。
**副作用**是讓靜態分析變難——但那是副作用,不是主要目的,別過度解讀成「反分析」。

怎麼辨識:`readelf -h` 看 `Number of section headers: 0`,
或 `file` 直接說 `no section header`。

</details>

### 2.6 🔵 這台機器有哪些記憶體保護機制?

<details><summary>答案</summary>

**一個都沒有。**

| 機制 | 狀態 |
|---|---|
| Stack canary | ❌ 沒有 `__stack_chk_fail` |
| NX(不可執行堆疊) | ❌ 大多數 binary **連 `PT_GNU_STACK` 都沒有** |
| PIE / ASLR | ❌ `ET_EXEC`,固定載入在 `0x00400000` |
| RELRO | ❌ 沒有 `PT_GNU_RELRO` |
| FORTIFY | ❌ 沒有任何 `*_chk` 符號 |

而且 **Boa 以 root 執行**。

</details>

### 2.7 🔴 「沒有 `PT_GNU_STACK`」跟「`PT_GNU_STACK` 存在但可執行」有什麼差別?為什麼要分?

<details><summary>答案</summary>

- **沒有這個段** = 工具鏈太舊,根本不會產生這個標記。核心看不到標記,
  就**退回預設值:堆疊可執行**。
- **有這個段但帶 `PF_X`** = 工具鏈知道這個機制,但**明確地**標成可執行。

執行時的結果一樣(堆疊都能執行),但**成因不同**,而成因決定你怎麼描述這件事:
前者是「2008 年的 uClibc 工具鏈」,後者是「有人做了選擇」。

`fwrecon` 因此把 `nx` 設計成三態:`None`(標記不存在)/ `True` / `False`,
**不把「不知道」壓成「否」**。

> 這題考的是:你會不會為了讓資料結構好看,把兩種不同的事實混成一種。
> 在安全分析裡這是重罪。

</details>

### 2.8 🟠 這些防護都沒有,對攻擊難度的實際影響是什麼?

<details><summary>答案</summary>

**一個堆疊溢位就直接拿 root,不需要任何進階技巧。**

現代 x86 打一個堆疊溢位要:洩漏位址繞過 ASLR → 找 ROP gadget 繞過 NX →
處理 canary。這裡**全部不用**:

- 位址固定(沒 PIE)→ 不用洩漏
- 堆疊可執行 → shellcode 直接放堆疊上跳過去,不用 ROP
- 沒 canary → 直接蓋返回位址
- Boa 是 root → 沒有第二階段提權

**所以看 2025 年那幾個 buffer overflow CVE 時,要用這個前提去理解它們的嚴重性。**

</details>

---

## 3. 工具與方法論

### 3.1 🔴 你今天六個 bug 裡有四個是「工具本身出錯」。這對你的工作方式有什麼影響?

<details><summary>答案</summary>

**任何結論都要有兩個獨立來源。**

逆向工程幾乎全是間接觀測——你看不到程式在跑,只能透過工具去推斷。
所以「工具說什麼」和「事實是什麼」之間永遠有一層。

今天救我的兩次都是交叉比對:
- `nm -D` vs `readelf` → 發現 `readelf` 對 sstrip 過的檔案無聲失敗
- `nm -D` vs 我自己的 parser → 發現 MIPS stub 位址的判準錯誤

**實務原則:結果讓你意外的時候,先懷疑量測方法,再懷疑被量測的東西。**

</details>

### 3.2 🔴 「工具沒有回報問題」和「沒有問題」的差別?

<details><summary>答案</summary>

**天差地遠,而且無聲失敗比大聲失敗危險得多。**

大聲失敗(crash、非零退出碼)你會處理。無聲失敗會直接變成你的結論。

今天的例子:`readelf --dyn-syms` 對 sstrip 過的檔案印空白、退出碼 0。
一個包在外面的腳本會完全合理地記錄「危險 import: 0 個」。

**設計原則:寫工具時,「我答不出來」和「答案是空的」必須是兩種不同的回傳。**
`fwrecon` 的 `analyse()` 因此對非 ELF 回傳帶 `error` 欄位的物件,而不是空結果。

</details>

### 3.3 🟠 這段 bash 錯在哪?

```bash
out=$(mytool --version 2>&1 | head -3)
echo "rc=$?"
```

<details><summary>答案</summary>

**`$?` 抓的是 pipeline 最後一個指令(`head`)的退出碼,不是 `mytool` 的。**
`head` 幾乎永遠回 0,所以這段會永遠印 `rc=0`。

我今天就是這樣寫的,結果探測腳本回報「所有工具都正常」,跟我眼睛看到的現象矛盾。

正確寫法:

```bash
mytool --version >/dev/null 2>&1
echo "rc=$?"
```

或用 `set -o pipefail` 讓 pipeline 回傳第一個非零的退出碼。

**教訓:除錯工具自己也會有 bug。觀測結果跟現象矛盾時,先查觀測方法。**

</details>

### 3.4 🟠 為什麼 `unsquashfs` 回傳非零,我們卻當它成功?

<details><summary>答案</summary>

因為它是**用一般使用者身分**跑的:建立不了裝置節點(`/dev/*`)、改不了檔案擁有者,
所以回傳 2。但**檔案內容和權限位元都是完整的**,那才是我們要的。

`unpack-firmware.sh` 因此不看退出碼,改看**實質成功條件**:

```
樹存在 && 裡面有檔案 && 有符號連結
```

而且「沒有符號連結」會**直接讓腳本失敗**——因為那代表目標檔案系統存不了符號連結,
`/web/config.dat` 那個關鍵發現會憑空消失。

> 這題考的是:你會不會盲目相信退出碼。**退出碼是工具作者的意見,不是事實。**

</details>

### 3.5 🔴 為什麼一定要解包到 ext4?在 `/mnt/c` 上解會怎樣?

<details><summary>答案</summary>

**符號連結和權限位元會消失,而且不會報錯。**

WSL 透過 DrvFs 掛載 Windows 磁碟,預設不帶 Linux metadata。解包時符號連結會變成
普通檔案或直接消失,setuid 位元存不下來。

**對這個專案是致命的:**

1. `/web/config.dat` **是個符號連結**——本專案嚴重性最高的發現。在 `/mnt/c` 上解包
   會直接看不到。
2. 「兩個映像都沒有 setuid 檔案」這句話,只有在 setuid 位元存得下來的前提下才是
   **關於韌體的陳述**;否則它只是**關於檔案系統的陳述**。

所以腳本會在 `FWRE_WORK` 指向 `/mnt/*` 時直接拒絕執行。

</details>

### 3.6 🟠 為什麼測試的 fixture 要「重現陷阱」而不是「重現教科書案例」?

<details><summary>答案</summary>

因為教科書案例過了,不代表真實資料會過。

我原本的 ELF fixture 把 import 的 `st_value` 設成 0(教科書寫法)。
測試全過,但真實的 MIPS binary 上工具是壞的——因為真實的 `st_value` 不是 0。

改成 fixture 也帶非零 stub 位址之後,**既有的測試自動變成這個 bug 的回歸測試**。

**原則:fixture 要長得像最難搞的真實資料,不是最乾淨的假想資料。**

</details>

### 3.7 ⚪ 如果 `fwrecon` 和 binwalk 對同一個檔案給出不同答案,你會怎麼做?

<details><summary>答案(思路,不是標準答案)</summary>

**不會挑一個相信,而是把不一致本身當成發現。**

順序大概是:
1. 先確認兩邊在回答**同一個問題**(很多「不一致」其實是定義不同)
2. 找第三個來源(unblob、手動 hexdump、規格文件)
3. 手動驗證爭議的那幾個位元組——最終仲裁永遠是原始資料
4. 不管誰對,**把這件事寫進 LOG**

Dockerfile 裡刻意同時裝 binwalk 和 fwrecon 就是為了這個:
**兩個獨立實作互相對照,不一致是資訊,不是麻煩。**

</details>

---

## 4. 漏洞與攻擊面

### 4.1 🔵 CVE-2019-19822 和 19823 有什麼不同?

<details><summary>答案</summary>

- **19822 = 存取控制問題**:`GET /config.dat` 不需要認證就能拿到設定檔
- **19823 = 資料儲存問題**:那個設定檔裡的密碼是**明文**(`COMPCS` 格式)

**兩個獨立的缺陷,合起來才致命。**

- 只有 19822(檔案外洩但密碼有雜湊)→ 嚴重性大降
- 只有 19823(明文存但拿不到檔案)→ 需要先有其他漏洞

> 這題考的是你會不會把「一條攻擊鏈」和「一個漏洞」混為一談。
> 廠商修其中一個,另一個還在——這正是為什麼要分開編號。

</details>

### 4.2 🔴 你說 2020 版還有 config.dat 暴露路徑。所以廠商沒修?

<details><summary>答案</summary>

**不能這樣說,而且這題就是在測你會不會超譯。**

我**觀察到**的是:
- `/web/config.dat` 是指向 `/var/config.dat` 的符號連結
- `rcS` 有 `cp -rf /web/* /var/web/`
- `boa.conf` 的 `DocumentRoot` 是 `/var/web`

所以那個檔案**結構上在 web 根目錄裡**。

我**沒有**觀察到的是:Boa 收到 `GET /config.dat` 時到底有沒有做認證檢查。
修補完全可能做在請求授權那一層,而不是檔案佈局。

要下結論必須:**逆 `translate_uri` / `process_requests`,或在模擬環境實測。**
那是 W03/W05 的事。

> **這題答錯的人會說「所以有漏洞」。答對的人會說「所以要看這個函式」。**
> 面試官問這題就是在篩這個。

</details>

### 4.3 🟠 `#skt&` 這一行為什麼重要?

<details><summary>答案</summary>

2015 年 Pierre Kim 公開了 `/bin/skt` 這個後門(開 socket、收指令、`system()` 執行)。

V2.1.2 建置於 **2015-08-25**,揭露後五週——是廠商的回應版本。而回應是:

```
109  boa
110  #skt&
```

**把啟動那行註解掉,但 `/bin/skt` 還是照樣打包進韌體。**

「不啟動後門」和「沒有後門」是兩種不同的安全性質,他們只做到第一種。
任何能取得命令執行的人,都會發現一個現成的工具躺在那裡。

**這件事催生了 `fwrecon` 把「被註解掉的 init 行」當成一級發現來報告** ——
只看「有什麼在跑」的工具會判定這個映像是乾淨的。

</details>

### 4.4 🔴 `formSysCmd` 這個字串在兩個 binary 裡都找不到。所以這台機器沒這個漏洞?

<details><summary>答案</summary>

**不能這樣推。字串表不是完整的功能清單。**

反證就在同一個 binary 裡:
- `sysCmdselect` ← 這正是公開 PoC 裡的參數名
- `sysCmdLog`
- `/tmp/syscmd.log`

**功能明顯編進去了**,只是 handler 的註冊名字沒有以這個形式出現在字串表。

可能的原因:名字在執行期組出來、handler 用 dispatch table 註冊而名字存法不同、
或字串被拆開了。

而且原始 advisory 自己就寫了這個漏洞「即使 GUI(`syscmd.htm`)不存在也能觸發」——
**端點活得比它的介面久,正好符合我們看到的證據形狀。**

解法:進 Ghidra 讀 `handleForm`(那 9 個指向 `/boafrm/` 的 XREF 都在它身上)。

</details>

### 4.5 🟠 `submit-url` 這個字串有 50 個 XREF。你能從這推出什麼?

<details><summary>答案</summary>

**這 50 個函式幾乎就是 handler 的完整清單——而且不需要知道任何一個的名字。**

Realtek 的 `form*` handler 都會讀這個參數來決定處理完之後要導向哪一頁。
所以「誰引用了 `submit-url`」≈「誰是 handler」。

佐證:兩個罐頭 HTML 回應模板各有 41 個 XREF,而且跟上面那組高度重疊。

**跟另一個方法對答案**:`fwrecon` 從字串表撈到 59 個 `form*` 名字(2015 版)。
50 vs 59,同方向、差 20% 以內——**兩個獨立方法互相印證**。

而且差距本身有意義:名字存在不代表 handler 存在,handler 存在也不代表名字在字串表
——**後者正是 `formSysCmd` 的情況**。

</details>

### 4.6 🔴 `cp /var/web/config.dat %s` 這個字串為什麼是本週最有價值的發現?

<details><summary>答案</summary>

它同時具備命令注入的**三個要素**:

1. **是一段 shell 指令**(`cp`)
2. **有 `%s`** → 代表會被 `sprintf` 之類填值
3. **同一個函式(`FUN_00440eec`)裡還有 `rm -rf /var/config.dat`** → 這個函式明顯
   在跟 shell 打交道

如果那個 `%s` 的內容來自 HTTP 請求參數,而組出來的字串進了 `system()` ——
那就是命令注入。而 Boa 是 root。

⚠️ **但目前這只是「值得看」,不是「有漏洞」。** 還沒讀反編譯結果,不知道
`%s` 從哪來、有沒有過濾。**W03 要做的就是把這條路徑追完。**

</details>

### 4.7 🟠 為什麼 `getSanvas` 只出現在 2020 版?這說明什麼?

<details><summary>答案</summary>

CAPTCHA 是 2015 到 2020 之間**新增**的功能——是廠商為了擋暴力破解加的防護。

然後 CVE-2019-19825 說這個 CAPTCHA 可以繞過(明文回傳、且用 HTTP Basic auth 就
直接跳過)。

**新增的安全機制本身變成漏洞**,這是很典型的模式:防護措施加得比核心邏輯晚,
沒有納入原本的威脅模型。

佐證:2020 版的 boa 多連了 `libcjson.so`,正好對應 advisory 裡那個
`{"topicurl":"setting/getSanvas"}` 的 JSON 登入路徑。**兩條獨立證據指向同一件事。**

</details>

### 4.8 🔵 為什麼「Boa 以 root 執行」值得單獨拿出來講?

<details><summary>答案</summary>

因為它讓**每一個 handler 的 bug 都直接是 root 等級的 bug**。

正常的伺服器會降權(跑在 `www-data` 之類),這樣一個 web 漏洞只拿到低權限帳號,
攻擊者還得再找一個提權漏洞。**這台機器沒有這一層。**

`boa.conf` 裡就寫著:

```
User root
Group root
```

所以評估任何 `form*` handler 的漏洞時,嚴重性上限都是「完全控制裝置」,
沒有中間值。

</details>

---

## 5. 工程實踐

### 5.1 🟠 為什麼 `SOURCES.json` 和 `MANIFEST.json` 要分兩個檔?

<details><summary>答案</summary>

- `SOURCES.json` = **意圖**(手寫):我打算分析哪些映像、從哪拿、雜湊應該是多少
- `MANIFEST.json` = **觀測**(程式產生):我實際拿到了什麼、什麼時候拿的

**分開的意義:當鏡像站偷偷換檔,會變成「意圖與觀測不一致」而報錯,
而不是默默讓所有下游結論失效。**

合成一個檔的話,重跑一次就自動「修正」成新的雜湊,你永遠不會發現東西被換過。

</details>

### 5.2 🟠 韌體為什麼不放進 git?

<details><summary>答案</summary>

那是廠商的檔案,**不是我們的東西,沒有散布權**。即使裝置已經 EOL 也一樣。

替代方案:committed 的是**取得方式 + 雜湊**,任何人都能自己抓到位元組完全相同的
檔案並驗證。**可重現性不需要靠散布來達成。**

加分細節:2015 版的 MD5/SHA-1 是從 archive.org 的 metadata API 抄的,不是我自己
算的——所以可以拿一個**我們控制不了的來源**驗證。

</details>

### 5.3 🔴 CI 跑不了分析(沒有韌體),那 CI 到底在測什麼?

<details><summary>答案</summary>

**測「產生分析的那套工具」是對的、裝得起來的。**

58 個測試全部用**程式在記憶體裡建出來的合成資料**:一個 section header 被砍掉的
大端序 MIPS ELF、一個 Realtek 容器、一個 SquashFS superblock、一個被截斷的映像。

這不是妥協,是**優點**:每個 fixture 精準編碼一個要測的性質,包括真實樣本要靠
運氣才碰得到的邊角情況(截斷、sstrip、假的 gzip magic)。

另外三個 job:
- **shellcheck** — 腳本的靜態檢查
- **Docker build** — Dockerfile 結尾會實際執行每個工具,所以「build 成功」本身
  就是「版本 pin 還有效」的斷言
- **report schema check** — 抓「改了報告格式卻忘記重新產生」

</details>

### 5.4 🟠 為什麼所有第三方工具都要 pin 版本?

<details><summary>答案</summary>

**因為分析結果的可重現性取決於工具版本。**

三個月後 `apt install binwalk` 給你的不會是今天這個 binary。工具改了,
輸出可能就不一樣——而你的筆記說「binwalk 顯示 X」。

所以:binwalk pin 到 `v3.1.0`、sasquatch pin 到 `sasquatch-v4.5.1-6`、
Ghidra 和 JDK 都對 SHA-256。

`fwrecon` 更進一步:**零執行期相依**。ELF 和容器格式都自己解析,
不 shell out。這樣報告用一個乾淨的 Python 就能重現。

</details>

### 5.5 ⚪ 單人專案為什麼還要走 PR?

<details><summary>答案(觀點,可以有不同意見)</summary>

不是為了 code review(沒有 reviewer,那部分是演戲),而是:

1. **CI 在碰到 main 之前先跑。** W01 第一次 CI 是紅的(report schema 檢查有 bug)。
   直接推 main 的話,portfolio repo 首頁會掛紅叉——那是面試官第一眼看到的東西。
2. **PR 本身是作品。** 描述裡寫了發現什麼、證據是什麼、哪些是觀察哪些是推論。
   那比 commit message 更能展示工程判斷。
3. **這是目標公司的流程。** OpenBMC 走 Gerrit,系統廠韌體團隊沒有直接 push master 的。

粒度建議:**一週一個 PR**,不是一個 commit 一個 PR。

</details>

---

## 6. 開放題

沒有標準答案。這些是**思考練習**,建議寫下來而不是想一想就過。

### 6.1 ⚪ 如果你是當年寫這套韌體的 RD,`config.dat` 這件事該怎麼做才對?

<details><summary>思考方向</summary>

至少四個層次,越上面越根本:

1. **不要把設定檔放進 web 根目錄。** 需要下載功能就走 CGI handler,由程式讀檔後
   輸出,而不是讓 web server 直接 serve 檔案系統上的路徑。
2. **密碼不該可還原。** 存 salted hash。設定備份需要密碼的話,用使用者提供的
   密語加密整份備份。
3. **web server 降權。** 不要跑 root。
4. **預設拒絕。** Boa 的授權應該是白名單(明確允許的路徑才給),而不是黑名單。
   `.dat` 被漏掉正是黑名單思維的產物。

**面試加分點**:能講出「這是 default-allow vs default-deny 的設計問題」,
比列出四個修法更有價值——那顯示你看到的是模式,不是個案。

**跟你 OpenBMC 那半的連結**:phosphor 那邊的 D-Bus 權限模型也是同一個問題的
不同形式。想想看你在 `entity-manager` 裡看過的設定檔是怎麼處理的。

</details>

### 6.2 ⚪ 假設你在 W03 證實了 `.dat` 真的不用認證就能下載。這是新漏洞嗎?你會怎麼做?

<details><summary>思考方向</summary>

先問幾個問題:

- 這台裝置 EOL 了嗎?(是)→ 廠商還會修嗎?
- 這跟 CVE-2019-19822 是同一個漏洞,還是不同的?(2020 版是同一個問題的延續,
  還是新引入的路徑?)
- 有人已經報過 2020 版了嗎?

**如果是既有 CVE 在新版本上的延續** → 不是新漏洞,是「修補不完整」。價值在於
**記錄事實**,而且這是很好的 writeup 素材。

**如果是全新的東西** → 走 TWCERT/CC 協調揭露,即使裝置 EOL。
不要因為「反正沒人修」就直接公開。

**任何情況下都不要做的事**:掃描網際網路上的其他裝置來「驗證影響範圍」。

</details>

### 6.3 ⚪ 這個專案的 `fwrecon`,拿去分析一台 D-Link 或 TP-Link 的韌體會怎樣?哪些部分能重用?

<details><summary>思考方向</summary>

分三層想:

- **`elf.py`** — 幾乎完全通用。ELF 是標準,只是換架構(ARM 的話 `EM_ARM`,
  端序可能不同)。要補的可能是 ARM 的 hardening 判斷。
- **`rootfs.py`** — 大部分通用(找 web server、掃 sink、看符號連結、init 腳本),
  但 `HANDLER_RE` 是 Boa/Realtek 特有的。換成 GoAhead 或 uhttpd 要改。
- **`rtlimage.py`** — 完全不通用。這是 Realtek 專屬格式。

**這個分層本身就是答案**:當初就是照「通用 → 半通用 → 廠商特定」切模組的。
面試時能講出這個切法,比講「我寫了一個工具」強得多。

延伸思考:如果要支援第二個廠商,`rtlimage.py` 應該變成什麼樣的介面?

</details>

### 6.4 ⚪ 你要怎麼在履歷上用一句話描述這個專案?

<details><summary>思考方向</summary>

**不要寫「逆向了一台路由器韌體」。** 那是活動,不是成果。

要素:
- **能力**(不是任務):在未知架構上從零建立理解
- **可驗證的具體成果**:某個數字或某個明確發現
- **工程素養**:可重現、有測試、有紀律

反面例子:「使用 binwalk 和 Ghidra 分析 TOTOLINK 路由器韌體」——
這句話任何跟過一次教學文的人都能寫。

自己寫三個版本,然後問:**哪一句會讓面試官想追問?** 那句就對了。

⚠️ 而且你必須守得住你寫的每一個字。寫「發現廠商修補不完整」,
就要能當場講清楚證據到哪、推論到哪。

</details>

---

## 待補(下次上課要加的題)

- [ ] W02:UART 為什麼是 3.3V 不是 5V?接錯會怎樣?
- [ ] W02:SPI NOR 的 SOIC-8 腳位?為什麼要在通電狀態下夾?
- [ ] W02:實體 dump 出來要怎麼跟 `burnAddr` 對照?
- [ ] W03:`handleForm` 的 dispatch 機制是什麼?
- [ ] W03:Boa 的認證檢查在哪個環節?
- [ ] W03:`libapmib.so` 的 `COMPCS` 格式長什麼樣?

---

## 7. 分派表與授權流程(W03)

> 這一章是本專案目前**最會被追殺**的部分。因為結論很重(「所有 handler 都不用認證」),
> 而證據全部是靜態的。面試官會從兩個方向打:**「你怎麼確定?」**和**「那為什麼公告不是這樣寫?」**

### 7.1 🔵 一個 `POST /boafrm/formWsc` 進來之後,怎麼走到 handler 的?

<details><summary>答案</summary>

```
process_requests()          Boa 原生的狀態機
 └─ read_header()
      └─ process_header_end()      ← 唯一的授權關卡
           └─ translate_uri()      ← Boa 原生 alias.c,只做路徑轉換
                └─ write_body() ─> handleForm()
                                     └─ handler(req, 0, 0)
```

`handleForm` 做的事:`strstr(uri, "/boafrm/")` 找到前綴,跳過 8 個字元,然後
拿剩下的字串去走 `root_form[]` 這個以 NULL 結尾的陣列,比對方式是
**`strlen` 相等 + `memcmp` 全等**。命中就 `send_r_request_ok2()` 然後呼叫函式指標。

表格元素是 `{char *name; void (*fn)(request*, int, char**)}`,一項 8 bytes。

</details>

### 7.2 🔴 你說有 59 個 handler。你怎麼知道不會有第 60 個在別的地方註冊?

<details><summary>答案</summary>

因為 `handleForm` 的迴圈條件是 `*ppuVar5 != NULL`,**它只看這一張表**,沒有
fallback、沒有第二張表、沒有前綴比對、沒有 hash 表。所以「能被 `/boafrm/<name>`
叫到的東西」= 這張表的內容,這是封閉的。

**但要誠實說出這句話的邊界**:我證明的是「`handleForm` 只能到這 59 個」。
沒有排除的是:

- 別的 binary 自己開 port 提供服務(`/bin/skt` 就是一個例子)
- `formAjaxSet`(2020 才有)在它的 JSON body 裡自己再做一層分派
- CGI 路徑 —— `translate_uri` 還認得 `application/x-httpd-cgi`

**加分講法**:「我證明的是這個 dispatcher 的封閉性,不是這台機器攻擊面的封閉性。
這兩件事常被混為一談。」

</details>

### 7.3 🔴 網路上的 rtl819x SDK 原始碼寫 `char name[80]`,你說是 `char *name`。誰錯了?

<details><summary>答案</summary>

兩個都沒錯 —— **是不同的 SDK 版本/設定**。重點是我怎麼知道手上這支是哪一種:

1. **反編譯器**:`ppuVar1 = ppuVar5 + 2`,在 `char**` 上就是 8 bytes 一項。
   如果名字是 `char name[80]` 內嵌,步進會是 84。
2. **交叉檢查**:復原出來的表項數(59 / 49)剛好等於 W01 用完全不同方法
   (數字串表裡的 `form*` 字串)得到的數量。

而且我的復原腳本**沒有假設任何一種佈局**:它測試「`[字串指標][可執行位址]` 是否
以固定間距重複」。如果哪天遇到真的用 `char[80]` 的映像,它會找不到東西並且說找不到,
而不是吐出垃圾。

**加分講法**:「外流的 SDK 是對眼前 binary 的**假設**,不是規格。我拿它當假設來源,
不當事實來源。」

</details>

### 7.4 🔵 `formSysCmd` 在這台機器上在哪裡?

<details><summary>答案</summary>

**不在。** 不在 2015 版的 59 項裡,也不在 2020 版的 49 項裡。
`POST /boafrm/formSysCmd` 會走到 `send_r_not_found`。

</details>

### 7.5 🔴 那 `/tmp/syscmd.log`、`sysCmdselect`、`sysCmdLog` 這些字串是怎麼回事?

<details><summary>答案</summary>

它們是這個功能的**另外半邊**——顯示的那半,不是執行的那半。

W01 提名 `FUN_0044c610`(唯一引用 `/tmp/syscmd.log` 的函式)當 CVE-2019-19824 的
handler。W03 復原表格之後看到:它在 **ASP 頁面變數表**(`0x004885d0`)裡註冊為
`sysCmdLog`,而那張表是 `handleScript` 讀的,不是 `handleForm`。
也就是「頁面裡寫 `<% sysCmdLog %>` 時把 log 印出來」的那個函式。

Realtek SDK 的 `root_form[]` 是照 build-time 的功能開關組出來的。這個產品編進了
log viewer 和 `sysCmdselect` 頁面片段,但沒編進會執行命令的 handler。
**剩下的字串是設定的痕跡,不是功能的證據。**

**這題真正在考的**:三條線索(字串消失、有 log 路徑、有頁面片段)全部指向同一個
**錯誤**答案。把資料結構挖出來一次就結案。**復原結構 > 累積交叉引用。**

</details>

### 7.6 🔵 Boa 的授權檢查在哪一行?

<details><summary>答案</summary>

`process_header_end` @ `0x0040be0c`(V2.1.2)。整段授權區塊的進入條件裡有這一項:

```c
&& strstr(uri, "htm") != NULL
```

也就是說:**URI 裡沒有 `htm` 這三個字,整段檢查被跳過。**

`translate_uri` 是 Boa 原生的 `alias.c`(debug 訊息還印著 `"alias.c"` 和行號),
只做路徑轉換,沒有認證;`handleForm` 也沒有;59 個 handler 沒有任何一個自己再檢查
一次(全部反編譯之後 grep 過 MIB `0x1ec`/`0x1ed`/`0x1ee`,只有 `formLogin` 碰)。
所以那一行就是全部。

</details>

### 7.7 🔴 反編譯器會騙人。你憑什麼確定分支方向是「沒有 htm 就跳過」而不是相反?

<details><summary>答案</summary>

**因為我沒有只看反編譯器。** 這支函式的反編譯輸出頂上掛了三行
`WARNING: Heritage AFTER dead removal` / `Restarted to delay deadcode elimination`,
等於它自己承認處理得不好,所以我去讀組語:

```
0040c234  lw t9,-0x7cbc(gp)        -> PTR_strstr_0048b2f4
0040c238  addiu a1,a1,-0x2be0        "htm"
0040c23c  jalr t9                  -> strstr
0040c240  _move a0,s1                             ; a0 = request URI
0040c248  beq v0,zero,0x0040c3a0                  ; 回 NULL → 跳到 LAB_0040c3a0
```

關鍵是**跟旁邊那幾條比**:白名單頁面(`status.htm`、`login.htm`…)用的都是
`bne v0,zero` —— 「有命中就跳過檢查」。只有這一條是 `beq v0,zero` ——
「**沒**命中就跳過檢查」。而它們全部跳到同一個 `LAB_0040c3a0`,也就是繞過授權區塊、
直接進 `translate_uri`。

**加分講法**:「反編譯器宣告它有困難的時候,從它輸出得到的任何結論都是猜的。
我為此寫了一支輸出組語的腳本,而不是截圖。」

</details>

### 7.8 🟠 公告說的是「`.dat` 檔沒被限制」。你的說法有比較嚴重嗎?

<details><summary>答案</summary>

嚴重很多,而且是**範圍**的差別,不是程度的差別。

公告描述的是**現象**:`.dat` 沒被保護。聽起來像是「漏了一種副檔名」,修法就是
「把 `.dat` 加進檢查清單」。

實際的**原因**是:授權是拿 URI 做子字串比對,所以它保護的只有 HTML 介面。
「沒被保護的東西」不是一份清單,是一整個補集:

| 路徑 | 含 `htm`? | 檢查? |
|---|---|---|
| `/home.htm` | 是 | 有 |
| `/config.dat` | 否 | **沒有** |
| `/ca.cer` | 否 | **沒有** |
| `POST /boafrm/formPasswordSetup` | 否 | **沒有** |
| 全部 59 個 handler | 否 | **沒有** |

**這是 default-allow 的設計**(黑名單思維),不是一個漏掉的副檔名。
`.dat` 從來不是特例,它只是「不是 `.htm`」。

</details>

### 7.9 🔴 可是 CVE-2019-19824 的公告明明寫「authenticated attacker」。你是不是搞錯了?

<details><summary>答案</summary>

三件事要分開講,不要含糊過去:

1. **19824 的端點在這台機器上根本不存在**,所以那條公告的認證前提在這台機器上
   無從驗證。
2. 公告作者用了 `--user "admin:password"` 去測。**「他帶了憑證去測」不等於
   「不帶憑證就進不去」**——這是研究方法造成的描述,不是被測出來的邊界。
3. 那份公告涵蓋的是一整個 Realtek SDK 裝置家族。`root_form[]` 是每個產品各自
   build 出來的,授權那段程式碼各家也可能改過。**跨型號的結論不能直接套。**

**而最重要的一句**:我的結論目前也**只是靜態的**。我讀出了程式碼怎麼寫,
沒有證明機器怎麼跑。要證實只要三個 `curl`,寫在 `notes/auth-flow.md` 最後。
在跑出來之前,正確的講法是「程式碼是這樣寫的」,不是「這台機器可以被這樣打」。

**這題其實在考誠實度,不是技術。** 敢說「我還沒證實」比硬凹有價值得多。

</details>

### 7.10 🟠 登入成功之後,這台機器怎麼記得你是誰?

<details><summary>答案</summary>

**記你的 IP 位址。** 沒有 cookie、沒有 token、沒有 nonce。

`formLogin` 比對成功之後:

```c
apmib_set(0x1ec, req + 0x4bd);   /* 用戶端 IP */
apmib_set(0x1ed, username);
apmib_set(0x1ee, userpass);
```

之後每個 `.htm` 請求就拿 `apmib_get(0x1ec)` 跟來源 IP 做 `strcmp`。
閒置超過 600 秒就把它設回 `0.0.0.0`。

順帶一提:帳密是**明文**存進 APMIB 的(`0x1ed`/`0x1ee`),而 `config.dat` 就是
APMIB 的序列化檔案。這條線把 CVE-2019-19822(設定檔外洩)和 19823(明文密碼)
接了起來——拿到 `config.dat` 就等於拿到這裡比對用的那兩個值。

</details>

### 7.11 🔴 用 IP 當 session,實際上要多少成本才能繞過?

<details><summary>答案</summary>

看攻擊者在哪:

- **同一台機器上的另一個程式**(惡意 App、另一個使用者):零成本,IP 一樣。
- **同一個 NAT 後面**(公司、宿舍、咖啡廳):零成本,對外 IP 一樣。這是最現實的場景。
- **同一個 L2 網段**:ARP 欺騙即可,幾秒。
- **純遠端、不同 IP**:需要 IP spoofing,而 TCP 三向交握要求收得到回包,
  所以實務上很難——**但這台機器的 handler 根本不需要通過這關**,因為
  `/boafrm/*` 從頭到尾就沒進授權檢查。

**最後這句才是重點**:IP session 有多弱其實不太重要,因為要改設定的路徑根本繞過它。
IP session 只保護 HTML 頁面。

</details>

### 7.12 🟠 `formLogin` 的錯誤訊息有什麼問題?

<details><summary>答案</summary>

```c
if (strcmp(username, cfg_user) == 0) {
    if (strcmp(userpass, cfg_pass) == 0) { /* 成功 */ }
    msg = "ERROR: Password error.";      /* 帳號對、密碼錯 */
} else {
    msg = "ERROR: Username error.";      /* 帳號就錯了 */
}
```

**帳號列舉(username enumeration)**:兩種失敗回不同的字串,攻擊者可以先確定帳號
存不存在,再去猜密碼。沒有看到任何速率限制。

另外 `strcmp` 不是常數時間,理論上有 timing side channel;不過在這種裝置上
網路抖動遠大於那點差異,**不值得當成賣點講**——會顯得你在背名詞。

</details>

### 7.13 🔴 你說有個「拿未初始化的堆疊當密碼比」。這是漏洞嗎?

<details><summary>答案</summary>

**目前只能說是候選,不能說是漏洞。** 這題的正確答案是把兩件事分乾淨:

**已經確定的**(組語層級):V2.1.2 的 HTTP Basic 路徑會把使用者送的帳密拿去跟
`sp+0x40` 和 `sp+0x60` 比,比中了給 `authorized = 2`(比一般帳號高一級,
像是 supervisor)。整支函式對這兩個位址**只有三次存取**:兩次是拿位址當 `strcmp`
參數,一次是讀第一個 byte。**沒有任何寫入,位址也沒被傳出去過。**

**還沒確定的**:那塊堆疊在真實執行時裝什麼。這是動態問題:

- 如果 `sp+0x40` 剛好是 NUL 開頭,空帳號就會比中;密碼那邊在 `auth_pass` 為空時
  改讀 `lb v0,0x60(sp)`,那個 byte 是 0 的話也算過。
- Boa 是單一 process、迴圈處理請求,所以固定 frame offset 上的殘留值
  比多執行緒伺服器可重現得多。

**所以現在的處置**:記在 `notes/auth-flow.md` 當 W05/W06 的候選,
**在證實或否證之前不會報給任何人**。

**加分講法**:「靜態分析能證明程式碼寫錯了,不能證明錯得可以被利用。
把這兩件事混在一起講,是漏洞報告被退件最常見的原因。」

</details>

### 7.14 🔵 `formWsc` 有哪些請求參數會進 `system()`?

<details><summary>答案</summary>

- **`localPin`** → `sprintf(buf[100], "flash set HW_WLAN0_WSC_PIN %s", localPin)` → `system()`。
  **沒長度檢查、沒字元過濾。** 同時是命令注入和堆疊溢位。
- **`peerPin`** → 兩條路徑:
  - 一條只抽數字進 `local_254[52]`,**但抽的時候索引沒有上限** → 純溢位。
  - 一條 `sprintf(buf, "echo %s > /var/wps_peer_pin", peerPin)` → **原始值直接進 `system()`**。
- **`targetAPSsid`** → `iwpriv wlan%d set_mib wsc_specssid="%s"` → `system()`。
  有長度檢查(< 33),但**沒有跳脫**。

2015 和 2020 兩版**一模一樣**,五年沒動。

</details>

### 7.15 🔴 `targetAPSsid` 有長度檢查了,為什麼還是漏洞?

<details><summary>答案</summary>

因為長度檢查擋的是**溢位**,擋不了**注入**。它被塞進 shell 命令的雙引號裡:

```c
sprintf(buf, "iwpriv wlan%d set_mib wsc_specssid=\"%s\" ", wlan_idx, targetAPSsid);
system(buf);
```

送 `a";reboot;"` 就把引號關掉、接上自己的命令,而且長度遠小於 33。

**根因要講精確**:「缺的不是長度檢查(那個有),是**在把資料放進另一種語言的
語法之前沒有做對應的跳脫**。」加引號不是跳脫,引號本身也是資料的一部分。

</details>

### 7.16 🔴 同一支函式裡,`targetAPMac` 有嚴格過濾,`targetAPSsid` 沒有。這說明什麼?

<details><summary>答案</summary>

`targetAPMac` 是逐字元檢查是不是 `[0-9a-fA-F]`,而且要求長度剛好 12。
十行之後的 `targetAPSsid` 只檢查長度。

說明:**開發者會寫過濾,而且知道怎麼寫**。問題不是能力,是**每個參數各自為政**——
沒有統一的輸入處理層,每個欄位靠寫的人當下記不記得。

這是 ad-hoc 輸入處理的典型長相,而且它的失敗模式是**隨機的**:同一支函式裡有的
參數安全、有的不安全,審查的時候很容易看到前面那個安全的就放心了。

**面試加分點**:能把它講成「這是架構問題不是個案」,並且提出修法方向
(集中式的參數取得層,在 `req_get_cstream_var` 那一層就依用途做白名單),
比列出三個 bug 有價值得多。

</details>

### 7.17 🔵 `/bin/skt` 做什麼?

<details><summary>答案</summary>

10 KB、36 個函式,可以整支看懂。

- 不帶參數執行 → `TcpServer(0x15b3, 0xe10)`,**聽 TCP 5555**。
- 收到 `hel,xasf` → `system("iptables -I INPUT -p tcp --dport 80 -i eth1 -j ACCEPT")`
- 收到 `oki,xasf` → 同一條規則的 `-D`(刪除)
- 另外還有 `gvr,xasf`、`bye,xasf` 兩個暗號(沒有副作用,推測是握手/關閉)

**它不給 shell,也不繞密碼。它是「可達性後門」**:把本來被防火牆擋在外面的
管理介面打開。`eth1` 在這塊板子上應該是 WAN 側 —— 但那是從 iptables 規則讀出來的,
還沒在實機驗證(W02)。

</details>

### 7.18 🟠 `rcS` 裡 `skt` 那行被註解掉了(`#skt&`),它沒在跑。那還算漏洞嗎?

<details><summary>答案</summary>

**「不啟動後門」和「沒有後門」是兩件不同的事。**

V2.1.2 的日期是 2015-08-25,大約在 Pierre Kim 2015 年 7 月揭露之後五週。
廠商對一個已公開後門的回應,是**把啟動它的那一行註解掉,然後照樣把 binary
出貨**——放在 `/bin`,而且是可執行的。

任何能執行一條命令的東西,都能執行 `/bin/skt &`。而這台機器的 web 介面上就有
好幾條能執行命令的路徑(`formWsc`)。所以它把「一個 RCE」升級成「一個 RCE 加上
一條持久化的對外通道」。

**而這件事可以量化,不是嘴砲**:V3.4.0(五年後)把檔案整個刪掉了。
廠商後來做對了;2015 年做的是便宜的那個。

</details>

### 7.19 🔴 你的 sink 統計第一版說 2020 版只有 1 個 `strcpy`。你怎麼發現那是錯的?

<details><summary>答案</summary>

**因為它跟旁邊的數字對不起來。** 2015 版 589 個、2020 版 1 個,可是:

- 兩者是同一份程式碼,大小只差 11%
- `sprintf` 兩邊都是 694 個,`memcpy` 是 110 vs 112
- `nm -D` 明明說 2020 版還在 import `strcpy`

一份 C 程式不可能只有一次 `strcpy` 而有 694 次 `sprintf`。**兩個來源不一致的時候,
不一致本身就是資料。**

原因:2020 版被 `sstrip` 過(沒有 section header)而且有真正的 PLT
(`DT_MIPS_PLTGOT`)。Ghidra 找不到 `.plt` 去標它,只有部分項目被建成函式——
`system`、`sprintf` 有,`strcpy` 沒有。所以呼叫方指到一個**沒有名字的 stub**,
而我只數了指到 symbol 本身的參考。

**這是 W01 `readelf` 那個坑的第二次。** 所以現在報告裡有 `self_check`:
只要有 symbol 被 import 卻找不到呼叫方,整份檔案標成 `SUSPECT`。

</details>

### 7.20 🔴 那你怎麼修的?別跟我說你用猜的。

<details><summary>答案</summary>

**先量再修。** 修之前先數:`jal = 9979`、`jalr = 16`。
所以幾乎所有呼叫都是直接跳 PLT,不是 `lw t9,%call16(gp)` 那種 GOT 間接呼叫——
代表**不需要**去解 `gp`,問題單純是 PLT 項目沒被辨識出來。

而 MIPS 的 PLT entry 是 binutils 產生的四道固定指令,每個欄位都由 `.got.plt`
的 slot 位址 `S` 決定:

```
lui   $15, %hi(S)        3C 0F hi
lw    $25, %lo(S)($15)   8D F9 lo
addiu $24, $15, %lo(S)   25 F8 lo
jr    $25                03 20 00 08
```

所以我是**把這 16 個 byte 算出來**再去記憶體找,而且規定「只能命中一次;
命中兩次或零次就不採用」——寧可回報找不到,也不要挑一個。

順手還修了一件事:從**函式外面**來的 data reference 是 GOT 欄位,不是呼叫點。
就是它讓 `strcpy` 回報「1」而不是誠實的「0」。**把 1 變回 0,才會觸發 self_check。**

修完:587 vs 577,兩個 build 對得上了。

</details>

### 7.21 ⚪ 你這週所有結論都是靜態的,機器還沒到。要怎麼證明它們是對的?

<details><summary>思考方向</summary>

先承認靜態分析能給什麼、不能給什麼:

- **能給**:程式碼寫成什麼樣、資料結構長什麼樣、哪條路徑存在。
- **不能給**:實際執行時的狀態(堆疊殘留)、設定相依的分支(那個 MIB `0x10e`
  兩條路徑走哪條)、以及最重要的——**這台機器上實際跑的是哪個 build**。

驗證分三層,成本由低到高:

1. **模擬**(W05):W01 已經證明 `qemu-mips-static` + chroot 可以讓 2015 版的
   `boa` 跑起來並印出 usage。缺的是 `libapmib.so` 會去讀 `/dev/mtd*`。
   把那層擋掉或做假,就能發真的 HTTP 請求。
2. **實機**(W02 到貨後):三個 `curl` 就結案 ——
   `GET /config.dat` 應該回 200、`GET /home.htm` 應該回 401、
   `POST /boafrm/formPasswordSetup` 應該真的改掉密碼。
3. **交叉比對**:找同家族其他型號的韌體,看 `strstr(uri,"htm")` 這個模式是不是
   Realtek SDK 的共通寫法。如果是,這就不是一台機器的 bug。

**面試加分點**:主動說出「我的結論還沒被執行驗證過」比被問出來好一百倍。
而且要能講清楚**驗證計畫**——有計畫的未完成,和沒想過的未完成,是完全不同的東西。

</details>

---

## 8. W04:CVE 根因定位、2020 版授權、工具會騙人

> 🔴 = 一定會被問到 · 🟠 = 有機會 · 🔵 = 送分題 · ⚪ = 你要主動講的

### 8.1 🔴 你說 2020 版「修好了」又說「還是有洞」。到底是修了還是沒修?

<details><summary>答案</summary>

**兩件事都是真的,而且要分開講,因為它們是不同的宣稱。**

W03 找到的洞是:2015 版的閘門條件是 `strstr(uri, "htm")`,而 59 個
`/boafrm/form*` 端點的 URI 裡沒有 `htm`,所以**一個都沒被檢查**。

2020 版把條件換成 `(URI 含 ".htm") || (URI 含 ".asp") || (method == POST)`。
所有 handler 都是 POST,所以**全部進閘門了。這個洞是真的修好了。**

沒變的是**判斷方式**:兩版都是拿 `strstr` 掃整條 URI。2015 是「納入條件」太窄,
2020 把納入條件放寬了,結果換成「豁免清單」變成窄的那一端:

```
0040a2cc  move a0,s1              ; a0 = request URI
0040a2d0  jal strstr
0040a2d4  _addiu a1,a1,0x8a0      ; "login"
0040a2d8  bne v0,zero,0x0040a354  ; 含 "login" -> 跳過轉址
```

`strstr` 沒有綁開頭,所以 URI 裡**任何位置**出現 `login` 都算。

我的講法是:**根因沒有變,只是換了個地方冒出來。** 這比「修好了」或「沒修」
都更接近事實,而且是可以驗證的說法。
</details>

### 8.2 🔴 `POST /login/boafrm/formWsc` —— 你實際打過嗎?

<details><summary>答案</summary>

**沒有。這是靜態讀出來的,機器還沒到手,W02 卡在硬體。**

我能講到多細:三個 `strstr` 都不綁位置,而且**讀的是同一個欄位**(`req + 0xf8`):

1. 閘門 `0x0040a2d8`:`strstr(uri, "login")` → 有就跳過轉址
2. `translate_uri` `0x00403860`:POST 打到非 CGI 路徑,`strstr(uri, "boafrm")` 有就放行
3. `handleForm` `0x0040ee60`:`strstr(uri, "/boafrm/")` 找到後,對後面 8 bytes 做精準比對

中間 `clean_pathname` 會把 `.` 和 `..` 收掉,但這條路徑兩個都沒有。

要證實只要兩個請求:`POST /boafrm/formWsc`(對照組,應該被轉址)和
`POST /login/boafrm/formWsc`(應該進 handler)。兩個都被轉址,就是我讀錯,
那它會以否定結果留在 `notes/auth-flow-2020.md` 裡。

**而且在 W05/W06 跑出來之前,我不會回報給任何人。** 靜態讀三個 `strstr`
不等於漏洞,拿去通報只會浪費別人的時間。
</details>

### 8.3 🔴 十四個 CVE 你說只有三個缺陷。這不是在幫廠商講話嗎?

<details><summary>答案</summary>

正好相反,這對廠商更難看。

- CVE-2025-3987 和 CVE-2025-4462 是**同一行**:
  `sprintf(buf[100], "flash set HW_WLAN0_WSC_PIN %s", localPin); system(buf)`。
  一個講沒過濾,一個講沒長度檢查。同一行,兩個編號。
- CVE-2025-3990/3991/3992/3993 是**同一段三行的尾巴**,複製在 **34 個 handler** 裡。
  有編號的只有四個。

所以真正的意思是:**編號的數量反映的是有人送了幾份 PoC,不是缺陷有幾個。**
而且那一行在 **2015 版裡一字不差** —— 這些不是 2025 年的 bug,是 2015 年的 bug
花了十年才被登記。

我用來說明的方式:「如果我照 CVE 清單修,我會修四個 handler,剩下 29 個一樣有洞。」
</details>

### 8.4 🔴 `lastUrl` 是 100 bytes,你怎麼知道?別跟我說是反編譯器講的。

<details><summary>答案</summary>

不是反編譯器,是 **V2.1.2 的符號表**:

```
$ readelf -sW bin/boa | grep -E 'lastUrl|needReboot'
   421: 0049087c   100 OBJECT  GLOBAL DEFAULT   23 lastUrl
   241: 004908e0     4 OBJECT  GLOBAL DEFAULT   23 needReboot
```

`0x49087c + 100 = 0x4908e0`,剛好就是 `needReboot`。所以不但知道大小,
還知道**溢出去第一個踩到的是誰**:兩個控制旗標,而且 `needReboot = 1` 就寫在
那個 `strcpy` 的上一行。

補充一句可以主動講的:這是 **`.bss` 的資料溢位,不是堆疊溢位**。
沒有 canary 的問題,也沒有 return address 在旁邊。踩到的是相鄰的全域變數。
把它講成「可以蓋 return address 拿 shell」就是吹牛。
</details>

### 8.5 🔴 你說少帶一個參數就能讓 web server 掛掉。憑什麼?

<details><summary>答案</summary>

`req_get_cstream_var` 找不到參數時,回傳的是**呼叫端傳進來的預設值**:

```c
if (-1 < (int)__n) {
    param_3 = malloc(__n + 1);      /* 找到了:配剛好的大小 */
    ...
}
return param_3;                      /* 沒找到:原封不動回傳預設值 */
```

而所有 handler 都是這樣呼叫的:`req_get_cstream_var(req, "submit-url", "")`。
那個 `""` 是 `.rodata` 裡的字面常數(V2.1.2 在 `0x476418`)。

```
LOAD  0x000000 0x00400000 0x00400000 0x77744 0x77744 R E   <- .rodata 在這裡
LOAD  0x078000 0x00488000 0x00488000 0x0368c 0x1ea18 RW
```

`R E`,沒有 W。然後 handler 做 `strcpy(pcVar1, "/status.htm")` —— 往唯讀分頁
寫 12 bytes。boa 是**單一 process** 在迴圈裡處理請求,掛了就沒了。

**這是靜態推論,不是觀測。** 我沒跑過。要推翻它只需要一個請求。
但它同時解釋了一件事:這個型號所有公開 PoC 都帶 `submit-url=`。
如果少帶會 500 或 400,大家不會這麼一致。
</details>

### 8.6 🔴 W01 寫「兩份映像檔都沒有 `/etc/passwd`」。現在你說有。哪一次是錯的?

<details><summary>答案</summary>

**W01 錯了,而且錯得很典型。**

`/etc/passwd` 是一個指向 `/var/passwd` 的 symlink。`/var` 是開機才掛上去的
tmpfs,在**解包出來的映像檔裡當然不存在**,所以 `stat` 回答「不存在」。

W01 把「symlink 指到的東西不存在」讀成「檔案不存在」,然後從這裡推出
「認證檢查一定在某支 binary 裡」,並且用這個理由把後門帳號的問題往後推了
W01、W03、大半個 W04。

真正的內容一直躺在旁邊:

```
$ cat etc/passwd.org            # V2.1.2
root:zhxPr1e7Npazg:0:0:root:/:/bin/sh
onlime_r:$1$01OyWDBw$Hrxb2t.LtmiiJD49OBsCU/:0:0:root:/:/bin/sh

$ strings -a bin/sysconf | grep passwd
cp /etc/passwd.org /var/passwd 2> /dev/null
```

教訓:**在韌體映像檔裡,懸空的 symlink 是常態不是異常。**
`/var` 底下所有東西都是開機才寫的。正確的問題不是「這個路徑存在嗎」,
而是「這個路徑存在嗎;如果不存在,映像檔裡有沒有東西會寫它」。

順帶一提,W01 的**結論**(web 的認證檢查在 binary 裡)其實是對的 ——
它在 MIB `USER_NAME` / `USER_PASSWORD`。對的結論,錯的證據。
這種情況比純粹講錯更危險,因為它不會被自己發現。
</details>

### 8.7 🔴 `onlime_r` 的密碼你是怎麼知道的?你破解了廠商的東西?

<details><summary>答案</summary>

雜湊值在**我自己買的機器的韌體檔案裡**,用 `crypt()` 對二十個常見字串比對:

| 帳號 | 雜湊 | 演算法 | 密碼 |
|---|---|---|---|
| `root` | `zhxPr1e7Npazg` | DES crypt | `123456` |
| `onlime_r` | `$1$01OyWDBw$Hrxb2t.LtmiiJD49OBsCU/` | MD5-crypt | `12345` |

`onlime_r` 那個根本不用破 —— **Pierre Kim 2015 年的公告上就印著同一串雜湊**。
我做的只是確認它一字不差地出現在**廠商在他公告之後才發布的版本**裡。

而 `root` 是 DES crypt:8 個有效字元、56-bit,現在的硬體幾秒鐘。
兩版都是 `123456`,而公告上寫的是 `12345`。廠商的修法是加一位數。
</details>

### 8.8 🟠 `config.dat` 裡的密碼在第幾個 byte?

<details><summary>答案</summary>

**我不知道,而且我不會猜。**

我知道的是格式:`libapmib.so` 寫的檔案是 `COMPCS` 魔術字 + **壓縮過的 TLV 串流**,
內容是 MIB 表的序列化。同族還有 `COMPHS`(硬體設定)、`COMPDS`(預設設定),
對應 `/dev/mtdblock0` 上的三塊區域。

所以 CVE-2019-19823「明文儲存密碼」的意思是:`USER_PASSWORD` 就是一個普通的
MIB 項目,一個普通的 TLV 紀錄,**中間沒有任何雜湊步驟**。這也是為什麼
`formLogin` 可以直接 `strcmp(userpass, cfg_pass)`。

但「第幾個 byte」需要一份真的 `config.dat`,而那需要 W02 的 flash dump
或者一台跑著的機器。壓縮演算法我也還沒認出來。
**證據支持的是「這是 MIB 表的壓縮序列化」,不是「密碼在 offset N」。**
</details>

### 8.9 🔵 `apmib_get(0xb6)` 的 `0xb6` 是什麼?

<details><summary>答案</summary>

`USER_NAME`。`0xb7` 是 `USER_PASSWORD`。

不是猜的 —— `libapmib.so` 裡有一張 413 筆的表,每筆 60 bytes:
big-endian `uint32` 編號,接一個 **32 bytes 內嵌的名字**。

版面是量出來的,不是照網路上的 SDK header 抄的(這個專案在
`dispatch-table.md` 已經被那樣坑過一次):

```
00c818  00 00 01 ec                                    id
00c81c  41 55 54 48 47 5f 49 50 5f 41 44 44 52 00 ...  "AUTHG_IP_ADDR"
00c854  00 00 01 ed                                    <- 正好 0x3c 之後
00c858  41 55 54 48 47 5f 55 53 45 52 5f 4e 41 4d 45   "AUTHG_USER_NAME"
```

而且這三個編號正好就是 `process_header_end` 在用的 `0x1ec/0x1ed/0x1ee` ——
**兩個獨立來源(binary 的行為 + 另一個檔案的表)對上了**,這才是可以拿去用的。
</details>

### 8.10 ⚪ 你的工具錯了三次,自我檢查三次都說沒問題。那你的結論還能信嗎?

<details><summary>答案(這題要自己主動講)</summary>

**這題我主動講,因為它是這週最有價值的東西。**

`BoaArgTrace` 連續錯三次,三次 `self_check` 都寫 `consistent`:

| 次數 | 症狀 | 原因 |
|---|---|---|
| 1 | 304 個呼叫點只有 1 個被標成有請求參數 | 同一套解析邏輯寫了兩份,走鐘了 |
| 2 | 2015 版 86 個、2020 版 **0** 個 | `accessor:` 拿去跟小寫化的名字比,永遠不相等 |
| 3 | `strcpy` 2015 版 151 個、2020 版 **0** 個 | W03 已經修過的 sstrip PLT 問題,我重寫了一份沒帶上修正 |

抓到它們的**不是自我檢查**:

- 第 1 次:W03 已經**用手讀**出 `formWsc` 有三個參數進 `system()`,工具一個都沒找到。兩個來源不一致。
- 第 2、3 次:把兩版並排比。同一份程式碼相隔五年,不可能 86 → 0。

結論兩句:

> **一個永遠不會觸發的檢查,也永遠不會失敗。**
> `self_check: consistent` 只代表「我想到要檢查的那幾件事沒問題」。

所以我做了兩件事而不是只修 bug:把 PLT 解析抽成 `BoaPlt.java` **只留一份**
(同一個 bug 在同一個專案出現兩次,就不是 bug 是設計問題),
以及讓「給了選項卻沒配對到任何東西」變成錯誤而不是沉默。

至於結論能不能信:**能信的部分是有第二個來源的那些。**
`lastUrl` 是 100 bytes —— 符號表講的。閘門的分支方向 —— 組語講的。
`onlime_r` 的雜湊 —— 檔案裡就有,而且對得上公開公告。
沒有第二來源的,我都標成「照程式碼讀是這樣」並且寫出要怎麼推翻它。
</details>

### 8.11 🟠 `execl` 那六個 handler,你 W03 說參數是使用者控制的。現在呢?

<details><summary>答案</summary>

**W03 猜錯了,而且是我自己推翻的。**

兩版所有 `execl` 呼叫點,argv 都是:

```c
execl(path, "firewall.sh", NULL);      /* 或 ip_qos.sh / radvd.sh / ntp.sh */
```

一個固定的腳本名字加一個 NULL。**沒有任何請求參數進到 argv。**

那使用者輸入去哪了?**進 MIB**,shell 腳本之後自己讀回來。
所以問題還在,只是搬家了 —— 真正該讀的是 `/etc/scripts/*.sh`,
一個 MIB 值被 `firewall.sh` 內插進命令,跟直接注入是同一個 bug,只是晚一個 process。

界線也要講清楚:我的工具解析的是**呼叫當下的參數**,`argv[0]` 是一個裝著路徑的
堆疊 buffer,工具**不會回頭追誰寫進那個 buffer**。所以「沒有請求參數進 argv」
成立的範圍是參數欄位,不包含路徑本身。
</details>

### 8.12 🔴 `formSysCmd` 不在表裡。你 W03 說是「編譯時沒開這個功能」,現在改口?

<details><summary>答案</summary>

**改口,而且新的說法比舊的強,因為它可以被推翻。**

W03 的說法是「SDK 的 `root_form[]` 是按產品組出來的,這台編譯時沒帶這個 handler」。
那是猜的,而且沒有任何東西支持。

日期支持另一個說法。Pierre Kim 的 `2015-totolink-0x02.txt` **點名 N150RT-V2**,
說它有 CVE-2015-9551(`/boafrm/formSysCmd` 未認證 RCE),
而且寫明「until last firmware **`TOTOLINK-N150RT-V2.1.1-B20150708.1548.web`**」。

我手上這份 V2.1.2 是 **2015-08-25** —— 他說最後一個有洞的版本之後。
而在這份裡,handler 從分派表消失了。

所以比較可能的解釋是:**這就是修補本身,被我看到了。**
同一個版本還做了另外兩件事:把 `#skt&` 註解掉(但留著 binary),
以及**把 `onlime_r` 留在 `passwd.org` 裡**。三件事修好一件。

**而且這是可以驗的:** 去抓 V2.1.1-B20150708,挖它的 `root_form[]`。
有 `formSysCmd` → 我說對了;沒有 → 我又錯了,W03 的說法反而比較接近。
這個實驗寫在 `PROGRESS.md` 的 carried-forward 清單裡。
</details>

### 8.13 🟠 你說 2020 版的 401 函式沒有人呼叫。萬一是 Ghidra 沒找到呢?

<details><summary>答案</summary>

這正是我不敢只用一個工具的地方,所以查了兩次。

Ghidra 說 `FUN_0040b850` 的 caller 數是 0。第二個來源是**直接掃原始 bytes**:
MIPS 的 `jal` 是絕對定址,目標編碼進指令裡,跟指令自己的位址無關。

```
jal 0x0040b850  ->  0x0C000000 | (0x0040b850 >> 2)  =  0C 10 2E 14
```

在整個 ELF 裡掃這四個 byte:**0 次**。

而同一支掃描程式,在同一個檔案裡找 `jal 0x0040a4f8` 找到 **1 次**、
`jal 0x00408720` 找到 **1 次** —— 跟 Ghidra 報的數字一樣,而且位置
(file offset `0x8910`)跟 Ghidra 報的呼叫點位址(`0x00408910`)對得上。
**掃描器是校準過的,所以那個 0 是真的。**

意義:這台機器**永遠不會回 401**。沒過認證是被 302 轉去登入頁。
寫 PoC 的時候如果去 assert 401,會對著一台行為完全正常的機器 debug 半天。
</details>

### 8.14 🔵 這週你最不確定的是什麼?

<details><summary>答案</summary>

按不確定程度排:

1. **`POST /login/boafrm/formWsc` 到底會不會進 handler。** 三個 `strstr`
   都讀過、組語層級確認過分支方向,但沒跑過。
2. **少帶 `submit-url` 會不會真的讓 boa 掛掉。** `.rodata` 在 `R E` segment
   是量出來的,回傳預設值的路徑也是讀出來的,但「寫唯讀分頁會 SIGSEGV」
   是作業系統行為,不是我從這份 binary 讀到的。
3. **`0x182` 那個重複的 MIB 編號**(`CUSTOM_PASSTHRU_ENABLED` 和
   `MLD_PROXY_DISABLED`)。我相信它是廠商表裡真的重複 —— `libapmib` 自己就帶
   `"MIB Error: %s detect duplicate id in %s"` 這個字串、還 export 了
   `mibtbl_check` —— 但我沒去讀查表函式確認它到底會回哪一個。
4. **四個 handler 在 2020 版沒顯示 `submit-url` 汙染但還存在**
   (`formDdns`、`formNewSchedule`、`formSysLog`、`formWanTcpipSetup`)。
   是被改寫了,還是我的六跳回溯不夠深?沒查。

前兩個 W05 一個 `curl` 就有答案,後兩個是純靜態、隨時可以做,只是這週沒排進去。
</details>
