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
