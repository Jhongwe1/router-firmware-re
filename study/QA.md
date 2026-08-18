# 自我檢核題庫

> 這份是**給我自己考自己**用的。每次做完一段工作，就把
> 「**一個想推翻這個結論的人會怎麼問**」丟進來。
>
> 它不是題庫，是**對自己的設計審查**。一條結論如果沒有人試過要推翻它，
> 它只是還沒有被推翻而已。
>
> **答案是折疊的。先自己講一遍，再展開對答案。**
> 用讀的沒有用 —— 一定要**出聲講完整句**，或是打字寫下來。
> 你以為你懂了但講不出來，被追問的時候就等於不懂。

---

## 怎麼用

| 標記 | 意思 |
|---|---|
| 🔵 **基本** | 答不出來代表這段沒讀懂，回去補 |
| 🟠 **理解** | 考「為什麼」，不是「是什麼」 |
| 🔴 **追殺** | 你答完之後，一個不相信你的人會追的那一句。**這種題才是分水嶺** |
| ⚪ **開放** | 沒有標準答案，考思考方式 |

### 進度追蹤

每次複習完更新這張表。**「講得出來」的標準是：不看筆記，連續講 30 秒不卡。**

| 章節 | 題數 | 上次複習 | 講得出來 |
|---|---|---|---|
| [1. 韌體結構與容器格式](#1-韌體結構與容器格式) | 7 | — | ／7 |
| [2. ELF 與 CPU 架構](#2-elf-與-cpu-架構) | 8 | — | ／8 |
| [3. 工具與方法論](#3-工具與方法論) | 7 | — | ／7 |
| [4. 漏洞與攻擊面](#4-漏洞與攻擊面) | 8 | — | ／8 |
| [5. 工程實踐](#5-工程實踐) | 5 | — | ／5 |
| [6. 開放題](#6-開放題) | 4 | — | — |
| [7. 分派表與授權流程（W03）](#7-分派表與授權流程w03) | 21 | — | ／21 |
| [8. CVE 根因定位（W04）](#8-w04cve-根因定位2020-版授權工具會騙人) | 14 | — | ／14 |
| [9. 硬體（W02 Day 1）](#9-w02硬體day-1) | 13 | — | ／13 |
| [10. Console 與 flash(W02 Day 2–3)](#10-w02console-與-flashday-23) | 11 | — | ／11 |
| [11. 自動化 flash dump 與工具信任（W02 Day 4）](#11-w02自動化-flash-dump-與工具信任day-4) | 9 | — | ／9 |
| [12. 搬到這台真的在跑的 binary 上（W04-2）](#12-w04-2把結論搬到這台真的在跑的-binary-上) | 15 | — | ／15 |
| [13. 登記簿、凍結與事後改答案（W05 Day 0）](#13-w05-day-0登記簿凍結以及你憑什麼說你沒有事後改答案) | 8 | — | ／8 |

---

## 1. 韌體結構與容器格式

### 1.1 🔵 這個 `.web` 檔裡面有什麼?

<details><summary>答案</summary>

三段（2015 版）或兩段（2020 版）結構，每段前面 16 個位元組的標頭：

```c
typedef struct {
    unsigned char signature[4];   /* "cr6c" / "r6cr" / "w6cg" */
    unsigned int  startAddr;      /* 載入到 RAM 的位址 */
    unsigned int  burnAddr;       /* 燒到快閃記憶體的偏移 */
    unsigned int  len;            /* 內容長度,不含標頭 */
} IMG_HEADER_T;
```

**全部是大端序。**

2015 版：`w6cg`（網頁資源，bzip2）→ `cr6c`（核心，LZMA）→ `r6cr`（根檔案系統，SquashFS）
2020 版：`cr6c` → `r6cr`（少了 `w6cg`）

</details>

### 1.2 🔴 你怎麼知道那 16 個位元組的欄位順序是對的?搞不好是 `[tag][len][addr][addr]`?

<details><summary>答案</summary>

**用結構自洽性驗證，不是用猜的。**

如果欄位順序猜對了，那麼：

> 第 N 段的 `payload_offset + len` 應該**剛好**落在第 N+1 段的 signature 上。

實測：2020 版 `cr6c` 的 payload 從 `0x10` 開始，`len = 0x12d802`，
`0x10 + 0x12d802 = 0x12d812` —— 而 `r6cr` 的 signature 就在 `0x12d812`。**分毫不差。**

欄位順序錯的話這個鏈子接不起來。三段全部接得上，而且兩個版本都接得上，基本上排除巧合。

另一個佐證：`burnAddr` 解出來是 `0x10000` / `0x60000` / `0x180000` —— 全部是漂亮的
64 KB 對齊邊界，正好符合快閃記憶體分割區的樣子。如果欄位對調，會得到
`0x80c00000` 當「燒錄位址」，那是 RAM 位址，不可能。

`fwrecon` 的 `test_sections_are_contiguous` 就是把這個檢查寫成測試。

</details>

### 1.3 🟠 `burnAddr` 有什麼用?為什麼不只用 binwalk 掃一掃就好?

<details><summary>答案</summary>

binwalk 告訴你「**檔案裡有什麼**」，`burnAddr` 告訴你「**這東西會被放到晶片的哪個位置**」。

這個差別在 W02 拆機時就是全部：當你用 CH341A 把 flash 讀出來，得到一個 4MB 的原始
映像，你要怎麼知道哪一段是根檔案系統?**就是靠 `burnAddr`。**

它也是「官方韌體 vs 我機器上實際跑的韌體」能對照的唯一依據。

</details>

### 1.4 🔵 為什麼說這台機器的快閃記憶體至少 4MB?

<details><summary>答案</summary>

取所有段落的 `burnAddr + len` 最大值：

```
0x180000 (1,572,864) + 2,174,978 = 3,747,842 bytes = 3.57 MiB
```

塞不進 2MB，所以至少 4MB。

TechInfoDepot 寫 2MB，**要嘛描述的是別的板子版本，要嘛就是錯的**。
W02 拆機看晶片絲印確認。

</details>

### 1.5 🟠 SquashFS 是什麼?為什麼嵌入式裝置都用它?

<details><summary>答案</summary>

**唯讀 + 壓縮**的檔案系統。

- 唯讀 → 沒有寫入路徑，不會因為斷電寫壞；也不用 journal
- 壓縮 → 2.1 MB 的映像解開後是 8 MB，快閃記憶體很貴，這個比例很關鍵
- 支援多種壓縮器 → 這台 2015 版用 LZMA、2020 版用 XZ

代價：要改東西只能重刷整個分割區。所以會變動的資料（設定檔、憑證）都丟到
`/var` 這種開機時建的 tmpfs —— **這正是 `/web/config.dat` 是符號連結的原因。**

</details>

### 1.6 🔴 大端序的 MIPS，為什麼根檔案系統的 SquashFS 標頭是小端序?你是不是讀錯了?

<details><summary>答案</summary>

**沒讀錯，而且這不矛盾。**

SquashFS **4.0 的規格就規定磁碟格式一律小端序**，不管 CPU 是什麼端序，核心驅動負責
轉換。會端序相依的是 SquashFS 3.x,4.0 把 byte-swapping 那套拿掉了。

**「你怎麼確定不是讀錯」—— 三個獨立佐證：**

1. `unsquashfs`（懂這個格式的工具）**乾淨地解開了**。如果端序判斷錯，它會直接罵。
2. 用小端序去解其他欄位，**每一個都合理**：`block_size = 0x00020000 = 131072`，
   而 `block_log = 17`，`2^17 = 131072` —— **兩個獨立欄位互相對得上**。
   端序讀錯的話這兩個不可能同時成立。
3. `inode count = 582`，跟 binwalk 獨立算出來的一樣。

**這題的價值不在答案，在示範「怎麼證明自己沒讀錯」。** 逆向工程幾乎每個結論都是
間接觀測，你必須有能力自我驗證。

</details>

### 1.7 🟠 兩個映像的 SquashFS 建立時間都是 2038 年。這代表什麼?

<details><summary>答案</summary>

代表**這個欄位不能信，這些映像沒辦法用自己的 metadata 定年**。

原始值 `0x802d2100` 和 `0x80ed2000`。把 byte 順序反過來讀是 `0x00212d80`（2,174,848）
和 `0x0020ed80`（2,158,464）—— 分別跟兩個檔案系統自己的大小只差一兩百位元組。

**推測**是廠商的 build script 把「大小」寫進了「時間戳記」欄位，而且端序還寫反。

⚠️ 注意用詞：這是**推測**，我沒有證據。`fwrecon` 的報告裡也是寫 "possibly"。
**能夠說「我不確定」，比硬給一個好聽的答案更專業。**

實務影響：唯一可信的日期來源是檔名（`B20150825` / `B20201030`）。

</details>

---

## 2. ELF 與 CPU 架構

### 2.1 🔵 這台機器是什麼架構?你怎麼知道的?

<details><summary>答案</summary>

**大端序 MIPS32,MIPS-I 指令集，o32 ABI。**

從 ELF 標頭直接讀：
- `e_machine = 8` → EM_MIPS
- `e_ident[EI_DATA] = 2` → ELFDATA2MSB → **大端序**
- `e_flags & 0xF0000000 = 0` → mips1
- `e_flags & 0x1000` → o32 ABI

第二個來源：Ghidra 自己判定的 `MIPS:BE:32:default`，跟我算的一致。

</details>

### 2.2 🟠 端序搞錯會怎樣?

<details><summary>答案</summary>

反組譯出來全是垃圾，而且**不會報錯**——這才是危險的地方。

實例：韌體 `0x50` 位置的位元組是 `3c 10 80 d3`。

- 當**大端序**讀：`0x3c1080d3` → `lui $s0, 0x80d3` —— 合理的 MIPS 指令，而且
  後面跟著 `addiu`，是標準的「載入 32 位元常數」慣用法
- 當**小端序**讀：`0xd380103c` → opcode `0b110100`，是 MIPS64 的 `LD`，
  在 32 位元開機碼裡毫無道理

**所以「指令看起來合不合理」本身就是端序的驗證方法。**

qemu 也一樣：用錯 `qemu-mipsel-static` 會直接說 `Invalid ELF image`。

</details>

### 2.3 🔴 你這個 `elf.py` 為什麼不直接呼叫 `readelf`?重造輪子不是壞味道嗎?

<details><summary>答案</summary>

**因為 `readelf` 在這個專案上會無聲說謊。**

2020 版的 `/bin/boa` 被 `sstrip` 過，`e_shnum == 0` —— section header 整張表被移除。

```
$ readelf --dyn-syms bin/boa     # 什麼都不印,退出碼 0
$ nm -D bin/boa | grep system    # U system
```

`readelf` 靠 section header 回答問題。找不到就印空白、**回傳成功**。
呼叫端會忠實記錄「這個 binary 沒有危險 import」然後往下走。

**這在本專案第一次分析時真的發生了**，我差點寫下「2020 版移除了所有危險函式」
這個完全錯誤的結論。

所以 `elf.py` 只走 **program header + `PT_DYNAMIC`** —— 也就是**動態連結器走的路**。
那兩個東西 strip 不掉，strip 掉程式就跑不起來。

> **這不是重造輪子，是換一個不會在關鍵時刻閉嘴的資訊來源。**

這題答得好的話，展示的是：你知道工具的**失效模式**，而不只是會用工具。

</details>

### 2.4 🔴 你說 MIPS 上判斷 import 只能看 `st_shndx`。那 `st_value` 裡到底放什麼?

<details><summary>答案</summary>

放**該符號的 lazy-binding 樁（stub）位址**，在 `.MIPS.stubs` 區段裡。

MIPS o32 沒有 x86 那種 PLT。呼叫一個還沒解析的外部函式時，會先跳到 `.MIPS.stubs`
的一小段程式，那段再去找動態連結器解析。所以 `.dynsym` 裡的未定義函式，
`st_value` 通常**不是 0**，而是這個樁的位址。

**我踩過這個坑。** 一開始判準寫成：

```python
if st_shndx == 0 and st_value == 0:   # 錯
```

結果 `/bin/boa` 的 181 個 import 有 **165 個被歸類成 export**——包含 `system` 和
`strcpy`，正好是這支工具存在的理由。

ABI 的定義只有一條：**`st_shndx == SHN_UNDEF (0)` 就是未定義符號**，`st_value`
不該參與判斷。

**怎麼發現的：** `nm -D` 說 181 個，我的工具說 16 個。**兩個來源不一致就是警報。**

</details>

### 2.5 🟠 `sstrip` 是什麼?為什麼廠商要做?

<details><summary>答案</summary>

比 `strip` 更激進的瘦身：`strip` 拿掉符號表，`sstrip` 連 **section header table 整張**
都砍掉。

**程式照樣能跑**，因為執行只需要 program header（告訴核心哪段載到哪），
section header 是給連結器和分析工具看的。

廠商的動機通常是省空間（這台 2MB/4MB 的快閃記憶體，每 KB 都在算）。
**副作用**是讓靜態分析變難——但那是副作用，不是主要目的，別過度解讀成「反分析」。

怎麼辨識：`readelf -h` 看 `Number of section headers: 0`，
或 `file` 直接說 `no section header`。

</details>

### 2.6 🔵 這台機器有哪些記憶體保護機制?

<details><summary>答案</summary>

**一個都沒有。**

| 機制 | 狀態 |
|---|---|
| Stack canary | ❌ 沒有 `__stack_chk_fail` |
| NX（不可執行堆疊） | ❌ 大多數 binary **連 `PT_GNU_STACK` 都沒有** |
| PIE / ASLR | ❌ `ET_EXEC`，固定載入在 `0x00400000` |
| RELRO | ❌ 沒有 `PT_GNU_RELRO` |
| FORTIFY | ❌ 沒有任何 `*_chk` 符號 |

而且 **Boa 以 root 執行**。

</details>

### 2.7 🔴 「沒有 `PT_GNU_STACK`」跟「`PT_GNU_STACK` 存在但可執行」有什麼差別?為什麼要分?

<details><summary>答案</summary>

- **沒有這個段** = 工具鏈太舊，根本不會產生這個標記。核心看不到標記，
  就**退回預設值：堆疊可執行**。
- **有這個段但帶 `PF_X`** = 工具鏈知道這個機制，但**明確地**標成可執行。

執行時的結果一樣（堆疊都能執行），但**成因不同**，而成因決定你怎麼描述這件事：
前者是「2008 年的 uClibc 工具鏈」，後者是「有人做了選擇」。

`fwrecon` 因此把 `nx` 設計成三態：`None`（標記不存在）/ `True` / `False`,
**不把「不知道」壓成「否」**。

> 這題考的是：你會不會為了讓資料結構好看，把兩種不同的事實混成一種。
> 在安全分析裡這是重罪。

</details>

### 2.8 🟠 這些防護都沒有，對攻擊難度的實際影響是什麼?

<details><summary>答案</summary>

**一個堆疊溢位就直接拿 root，不需要任何進階技巧。**

現代 x86 打一個堆疊溢位要：洩漏位址繞過 ASLR → 找 ROP gadget 繞過 NX →
處理 canary。這裡**全部不用**：

- 位址固定（沒 PIE）→ 不用洩漏
- 堆疊可執行 → shellcode 直接放堆疊上跳過去，不用 ROP
- 沒 canary → 直接蓋返回位址
- Boa 是 root → 沒有第二階段提權

**所以看 2025 年那幾個 buffer overflow CVE 時，要用這個前提去理解它們的嚴重性。**

</details>

---

## 3. 工具與方法論

### 3.1 🔴 你今天六個 bug 裡有四個是「工具本身出錯」。這對你的工作方式有什麼影響?

<details><summary>答案</summary>

**任何結論都要有兩個獨立來源。**

逆向工程幾乎全是間接觀測——你看不到程式在跑，只能透過工具去推斷。
所以「工具說什麼」和「事實是什麼」之間永遠有一層。

今天救我的兩次都是交叉比對：
- `nm -D` vs `readelf` → 發現 `readelf` 對 sstrip 過的檔案無聲失敗
- `nm -D` vs 我自己的 parser → 發現 MIPS stub 位址的判準錯誤

**實務原則：結果讓你意外的時候，先懷疑量測方法，再懷疑被量測的東西。**

</details>

### 3.2 🔴 「工具沒有回報問題」和「沒有問題」的差別?

<details><summary>答案</summary>

**天差地遠，而且無聲失敗比大聲失敗危險得多。**

大聲失敗（crash、非零退出碼）你會處理。無聲失敗會直接變成你的結論。

今天的例子：`readelf --dyn-syms` 對 sstrip 過的檔案印空白、退出碼 0。
一個包在外面的腳本會完全合理地記錄「危險 import： 0 個」。

**設計原則：寫工具時，「我答不出來」和「答案是空的」必須是兩種不同的回傳。**
`fwrecon` 的 `analyse()` 因此對非 ELF 回傳帶 `error` 欄位的物件，而不是空結果。

</details>

### 3.3 🟠 這段 bash 錯在哪?

```bash
out=$(mytool --version 2>&1 | head -3)
echo "rc=$?"
```

<details><summary>答案</summary>

**`$?` 抓的是 pipeline 最後一個指令（`head`）的退出碼，不是 `mytool` 的。**
`head` 幾乎永遠回 0，所以這段會永遠印 `rc=0`。

我今天就是這樣寫的，結果探測腳本回報「所有工具都正常」，跟我眼睛看到的現象矛盾。

正確寫法：

```bash
mytool --version >/dev/null 2>&1
echo "rc=$?"
```

或用 `set -o pipefail` 讓 pipeline 回傳第一個非零的退出碼。

**教訓：除錯工具自己也會有 bug。觀測結果跟現象矛盾時，先查觀測方法。**

</details>

### 3.4 🟠 為什麼 `unsquashfs` 回傳非零，我們卻當它成功?

<details><summary>答案</summary>

因為它是**用一般使用者身分**跑的：建立不了裝置節點（`/dev/*`）、改不了檔案擁有者，
所以回傳 2。但**檔案內容和權限位元都是完整的**，那才是我們要的。

`unpack-firmware.sh` 因此不看退出碼，改看**實質成功條件**：

```
樹存在 && 裡面有檔案 && 有符號連結
```

而且「沒有符號連結」會**直接讓腳本失敗**——因為那代表目標檔案系統存不了符號連結，
`/web/config.dat` 那個關鍵發現會憑空消失。

> 這題考的是：你會不會盲目相信退出碼。**退出碼是工具作者的意見，不是事實。**

</details>

### 3.5 🔴 為什麼一定要解包到 ext4?在 `/mnt/c` 上解會怎樣?

<details><summary>答案</summary>

**符號連結和權限位元會消失，而且不會報錯。**

WSL 透過 DrvFs 掛載 Windows 磁碟，預設不帶 Linux metadata。解包時符號連結會變成
普通檔案或直接消失，setuid 位元存不下來。

**對這個專案是致命的：**

1. `/web/config.dat` **是個符號連結**——本專案嚴重性最高的發現。在 `/mnt/c` 上解包
   會直接看不到。
2. 「兩個映像都沒有 setuid 檔案」這句話，只有在 setuid 位元存得下來的前提下才是
   **關於韌體的陳述**；否則它只是**關於檔案系統的陳述**。

所以腳本會在 `FWRE_WORK` 指向 `/mnt/*` 時直接拒絕執行。

</details>

### 3.6 🟠 為什麼測試的 fixture 要「重現陷阱」而不是「重現教科書案例」?

<details><summary>答案</summary>

因為教科書案例過了，不代表真實資料會過。

我原本的 ELF fixture 把 import 的 `st_value` 設成 0（教科書寫法）。
測試全過，但真實的 MIPS binary 上工具是壞的——因為真實的 `st_value` 不是 0。

改成 fixture 也帶非零 stub 位址之後，**既有的測試自動變成這個 bug 的回歸測試**。

**原則：fixture 要長得像最難搞的真實資料，不是最乾淨的假想資料。**

</details>

### 3.7 ⚪ 如果 `fwrecon` 和 binwalk 對同一個檔案給出不同答案，你會怎麼做?

<details><summary>答案（思路，不是標準答案）</summary>

**不會挑一個相信，而是把不一致本身當成發現。**

順序大概是：
1. 先確認兩邊在回答**同一個問題**（很多「不一致」其實是定義不同）
2. 找第三個來源（unblob、手動 hexdump、規格文件）
3. 手動驗證爭議的那幾個位元組——最終仲裁永遠是原始資料
4. 不管誰對，**把這件事寫進 LOG**

Dockerfile 裡刻意同時裝 binwalk 和 fwrecon 就是為了這個：
**兩個獨立實作互相對照，不一致是資訊，不是麻煩。**

</details>

---

## 4. 漏洞與攻擊面

### 4.1 🔵 CVE-2019-19822 和 19823 有什麼不同?

<details><summary>答案</summary>

- **19822 = 存取控制問題**：`GET /config.dat` 不需要認證就能拿到設定檔
- **19823 = 資料儲存問題**：那個設定檔裡的密碼是**明文**（`COMPCS` 格式）

**兩個獨立的缺陷，合起來才致命。**

- 只有 19822（檔案外洩但密碼有雜湊）→ 嚴重性大降
- 只有 19823（明文存但拿不到檔案）→ 需要先有其他漏洞

> 這題考的是你會不會把「一條攻擊鏈」和「一個漏洞」混為一談。
> 廠商修其中一個，另一個還在——這正是為什麼要分開編號。

</details>

### 4.2 🔴 你說 2020 版還有 config.dat 暴露路徑。所以廠商沒修?

<details><summary>答案</summary>

**不能這樣說，而且這題就是在測你會不會超譯。**

我**觀察到**的是：
- `/web/config.dat` 是指向 `/var/config.dat` 的符號連結
- `rcS` 有 `cp -rf /web/* /var/web/`
- `boa.conf` 的 `DocumentRoot` 是 `/var/web`

所以那個檔案**結構上在 web 根目錄裡**。

我**沒有**觀察到的是：Boa 收到 `GET /config.dat` 時到底有沒有做認證檢查。
修補完全可能做在請求授權那一層，而不是檔案佈局。

要下結論必須：**逆 `translate_uri` / `process_requests`，或在模擬環境實測。**
那是 W03/W05 的事。

> **這題答錯的人會說「所以有漏洞」。答對的人會說「所以要看這個函式」。**
> 問這題就是在篩這個。

</details>

### 4.3 🟠 `#skt&` 這一行為什麼重要?

<details><summary>答案</summary>

2015 年 Pierre Kim 公開了 `/bin/skt` 這個後門（開 socket、收指令、`system()` 執行）。

V2.1.2 建置於 **2015-08-25**，揭露後五週——是廠商的回應版本。而回應是：

```
109  boa
110  #skt&
```

**把啟動那行註解掉，但 `/bin/skt` 還是照樣打包進韌體。**

「不啟動後門」和「沒有後門」是兩種不同的安全性質，他們只做到第一種。
任何能取得命令執行的人，都會發現一個現成的工具躺在那裡。

**這件事催生了 `fwrecon` 把「被註解掉的 init 行」當成一級發現來報告** ——
只看「有什麼在跑」的工具會判定這個映像是乾淨的。

</details>

### 4.4 🔴 `formSysCmd` 這個字串在兩個 binary 裡都找不到。所以這台機器沒這個漏洞?

<details><summary>答案</summary>

**不能這樣推。字串表不是完整的功能清單。**

反證就在同一個 binary 裡：
- `sysCmdselect` ← 這正是公開 PoC 裡的參數名
- `sysCmdLog`
- `/tmp/syscmd.log`

**功能明顯編進去了**，只是 handler 的註冊名字沒有以這個形式出現在字串表。

可能的原因：名字在執行期組出來、handler 用 dispatch table 註冊而名字存法不同、
或字串被拆開了。

而且原始 advisory 自己就寫了這個漏洞「即使 GUI（`syscmd.htm`）不存在也能觸發」——
**端點活得比它的介面久，正好符合我們看到的證據形狀。**

解法：進 Ghidra 讀 `handleForm`（那 9 個指向 `/boafrm/` 的 XREF 都在它身上）。

</details>

### 4.5 🟠 `submit-url` 這個字串有 50 個 XREF。你能從這推出什麼?

<details><summary>答案</summary>

**這 50 個函式幾乎就是 handler 的完整清單——而且不需要知道任何一個的名字。**

Realtek 的 `form*` handler 都會讀這個參數來決定處理完之後要導向哪一頁。
所以「誰引用了 `submit-url`」≈「誰是 handler」。

佐證：兩個罐頭 HTML 回應模板各有 41 個 XREF，而且跟上面那組高度重疊。

**跟另一個方法對答案**：`fwrecon` 從字串表撈到 59 個 `form*` 名字（2015 版）。
50 vs 59，同方向、差 20% 以內——**兩個獨立方法互相印證**。

而且差距本身有意義：名字存在不代表 handler 存在，handler 存在也不代表名字在字串表
——**後者正是 `formSysCmd` 的情況**。

</details>

### 4.6 🔴 `cp /var/web/config.dat %s` 這個字串為什麼是本週最有價值的發現?

<details><summary>答案</summary>

它同時具備命令注入的**三個要素**：

1. **是一段 shell 指令**（`cp`）
2. **有 `%s`** → 代表會被 `sprintf` 之類填值
3. **同一個函式（`FUN_00440eec`）裡還有 `rm -rf /var/config.dat`** → 這個函式明顯
   在跟 shell 打交道

如果那個 `%s` 的內容來自 HTTP 請求參數，而組出來的字串進了 `system()` ——
那就是命令注入。而 Boa 是 root。

⚠️ **但目前這只是「值得看」，不是「有漏洞」。** 還沒讀反編譯結果，不知道
`%s` 從哪來、有沒有過濾。**W03 要做的就是把這條路徑追完。**

</details>

### 4.7 🟠 為什麼 `getSanvas` 只出現在 2020 版?這說明什麼?

<details><summary>答案</summary>

CAPTCHA 是 2015 到 2020 之間**新增**的功能——是廠商為了擋暴力破解加的防護。

然後 CVE-2019-19825 說這個 CAPTCHA 可以繞過（明文回傳、且用 HTTP Basic auth 就
直接跳過）。

**新增的安全機制本身變成漏洞**，這是很典型的模式：防護措施加得比核心邏輯晚，
沒有納入原本的威脅模型。

佐證：2020 版的 boa 多連了 `libcjson.so`，正好對應 advisory 裡那個
`{"topicurl":"setting/getSanvas"}` 的 JSON 登入路徑。**兩條獨立證據指向同一件事。**

</details>

### 4.8 🔵 為什麼「Boa 以 root 執行」值得單獨拿出來講?

<details><summary>答案</summary>

因為它讓**每一個 handler 的 bug 都直接是 root 等級的 bug**。

正常的伺服器會降權（跑在 `www-data` 之類），這樣一個 web 漏洞只拿到低權限帳號，
攻擊者還得再找一個提權漏洞。**這台機器沒有這一層。**

`boa.conf` 裡就寫著：

```
User root
Group root
```

所以評估任何 `form*` handler 的漏洞時，嚴重性上限都是「完全控制裝置」，
沒有中間值。

</details>

---

## 5. 工程實踐

### 5.1 🟠 為什麼 `SOURCES.json` 和 `MANIFEST.json` 要分兩個檔?

<details><summary>答案</summary>

- `SOURCES.json` = **意圖**（手寫）：我打算分析哪些映像、從哪拿、雜湊應該是多少
- `MANIFEST.json` = **觀測**（程式產生）：我實際拿到了什麼、什麼時候拿的

**分開的意義：當鏡像站偷偷換檔，會變成「意圖與觀測不一致」而報錯，
而不是默默讓所有下游結論失效。**

合成一個檔的話，重跑一次就自動「修正」成新的雜湊，你永遠不會發現東西被換過。

</details>

### 5.2 🟠 韌體為什麼不放進 git?

<details><summary>答案</summary>

那是廠商的檔案，**不是我們的東西，沒有散布權**。即使裝置已經 EOL 也一樣。

替代方案：committed 的是**取得方式 + 雜湊**，任何人都能自己抓到位元組完全相同的
檔案並驗證。**可重現性不需要靠散布來達成。**

加分細節：2015 版的 MD5/SHA-1 是從 archive.org 的 metadata API 抄的，不是我自己
算的——所以可以拿一個**我們控制不了的來源**驗證。

</details>

### 5.3 🔴 CI 跑不了分析（沒有韌體），那 CI 到底在測什麼?

<details><summary>答案</summary>

**測「產生分析的那套工具」是對的、裝得起來的。**

58 個測試全部用**程式在記憶體裡建出來的合成資料**：一個 section header 被砍掉的
大端序 MIPS ELF、一個 Realtek 容器、一個 SquashFS superblock、一個被截斷的映像。

這不是妥協，是**優點**：每個 fixture 精準編碼一個要測的性質，包括真實樣本要靠
運氣才碰得到的邊角情況（截斷、sstrip、假的 gzip magic）。

另外三個 job：
- **shellcheck** — 腳本的靜態檢查
- **Docker build** — Dockerfile 結尾會實際執行每個工具，所以「build 成功」本身
  就是「版本 pin 還有效」的斷言
- **report schema check** — 抓「改了報告格式卻忘記重新產生」

</details>

### 5.4 🟠 為什麼所有第三方工具都要 pin 版本?

<details><summary>答案</summary>

**因為分析結果的可重現性取決於工具版本。**

三個月後 `apt install binwalk` 給你的不會是今天這個 binary。工具改了，
輸出可能就不一樣——而你的筆記說「binwalk 顯示 X」。

所以：binwalk pin 到 `v3.1.0`、sasquatch pin 到 `sasquatch-v4.5.1-6`、
Ghidra 和 JDK 都對 SHA-256。

`fwrecon` 更進一步：**零執行期相依**。ELF 和容器格式都自己解析，
不 shell out。這樣報告用一個乾淨的 Python 就能重現。

</details>

### 5.5 ⚪ 單人專案為什麼還要走 PR?

<details><summary>答案（觀點，可以有不同意見）</summary>

不是為了 code review（沒有 reviewer，那部分是演戲），而是：

1. **CI 在碰到 main 之前先跑。** W01 第一次 CI 是紅的（report schema 檢查有 bug）。
   直接推 main 的話，repo 首頁會掛紅叉——那是任何人第一眼看到的東西。
2. **PR 本身是作品。** 描述裡寫了發現什麼、證據是什麼、哪些是觀察哪些是推論。
   那比 commit message 更能展示工程判斷。
3. **這是目標公司的流程。** OpenBMC 走 Gerrit，系統廠韌體團隊沒有直接 push master 的。

粒度建議：**一週一個 PR**，不是一個 commit 一個 PR。

</details>

---

## 6. 開放題

沒有標準答案。這些是**思考練習**，建議寫下來而不是想一想就過。

### 6.1 ⚪ 如果你是當年寫這套韌體的 RD,`config.dat` 這件事該怎麼做才對?

<details><summary>思考方向</summary>

至少四個層次，越上面越根本：

1. **不要把設定檔放進 web 根目錄。** 需要下載功能就走 CGI handler，由程式讀檔後
   輸出，而不是讓 web server 直接 serve 檔案系統上的路徑。
2. **密碼不該可還原。** 存 salted hash。設定備份需要密碼的話，用使用者提供的
   密語加密整份備份。
3. **web server 降權。** 不要跑 root。
4. **預設拒絕。** Boa 的授權應該是白名單（明確允許的路徑才給），而不是黑名單。
   `.dat` 被漏掉正是黑名單思維的產物。

**這題的關鍵**：能講出「這是 default-allow vs default-deny 的設計問題」，
比列出四個修法更有價值——那顯示你看到的是模式，不是個案。

**跟你 OpenBMC 那半的連結**：phosphor 那邊的 D-Bus 權限模型也是同一個問題的
不同形式。想想看你在 `entity-manager` 裡看過的設定檔是怎麼處理的。

</details>

### 6.2 ⚪ 假設你在 W03 證實了 `.dat` 真的不用認證就能下載。這是新漏洞嗎?你會怎麼做?

<details><summary>思考方向</summary>

先問幾個問題：

- 這台裝置 EOL 了嗎?（是）→ 廠商還會修嗎?
- 這跟 CVE-2019-19822 是同一個漏洞，還是不同的?（2020 版是同一個問題的延續，
  還是新引入的路徑?）
- 有人已經報過 2020 版了嗎?

**如果是既有 CVE 在新版本上的延續** → 不是新漏洞，是「修補不完整」。價值在於
**記錄事實**，而且這是很好的 writeup 素材。

**如果是全新的東西** → 走 TWCERT/CC 協調揭露，即使裝置 EOL。
不要因為「反正沒人修」就直接公開。

**任何情況下都不要做的事**：掃描網際網路上的其他裝置來「驗證影響範圍」。

</details>

### 6.3 ⚪ 這個專案的 `fwrecon`，拿去分析一台 D-Link 或 TP-Link 的韌體會怎樣?哪些部分能重用?

<details><summary>思考方向</summary>

分三層想：

- **`elf.py`** — 幾乎完全通用。ELF 是標準，只是換架構（ARM 的話 `EM_ARM`，
  端序可能不同）。要補的可能是 ARM 的 hardening 判斷。
- **`rootfs.py`** — 大部分通用（找 web server、掃 sink、看符號連結、init 腳本），
  但 `HANDLER_RE` 是 Boa/Realtek 特有的。換成 GoAhead 或 uhttpd 要改。
- **`rtlimage.py`** — 完全不通用。這是 Realtek 專屬格式。

**這個分層本身就是答案**：當初就是照「通用 → 半通用 → 廠商特定」切模組的。
能講出這個切法，比講「我寫了一個工具」強得多。

延伸思考：如果要支援第二個廠商，`rtlimage.py` 應該變成什麼樣的介面?

</details>

### 6.4 ⚪ 用一句話描述這個專案，你會怎麼講?

<details><summary>思考方向</summary>

**不要寫「逆向了一台路由器韌體」。** 那是活動，不是成果。

要素：
- **能力**（不是任務）：在未知架構上從零建立理解
- **可驗證的具體成果**：某個數字或某個明確發現
- **工程素養**：可重現、有測試、有紀律

反面例子：「使用 binwalk 和 Ghidra 分析 TOTOLINK 路由器韌體」——
這句話任何跟過一次教學文的人都能寫。

自己寫三個版本，然後問：**哪一句會讓一個工程師想追問?** 那句就對了。

⚠️ 而且你必須守得住你寫的每一個字。寫「發現廠商修補不完整」，
就要能當場講清楚證據到哪、推論到哪。

</details>

---

## 待補（下次上課要加的題）

- [ ] W02：UART 為什麼是 3.3V 不是 5V?接錯會怎樣?
- [ ] W02：SPI NOR 的 SOIC-8 腳位?為什麼要在通電狀態下夾?
- [ ] W02：實體 dump 出來要怎麼跟 `burnAddr` 對照?
- [ ] W03：`handleForm` 的 dispatch 機制是什麼?
- [ ] W03：Boa 的認證檢查在哪個環節?
- [ ] W03：`libapmib.so` 的 `COMPCS` 格式長什麼樣?

---

## 7. 分派表與授權流程（W03）

> 這一章是本專案目前**最會被追殺**的部分。因為結論很重（「所有 handler 都不用認證」），
> 而證據全部是靜態的。追問會從兩個方向來：**「你怎麼確定?」**和**「那為什麼公告不是這樣寫?」**

### 7.1 🔵 一個 `POST /boafrm/formWsc` 進來之後，怎麼走到 handler 的?

<details><summary>答案</summary>

```
process_requests()          Boa 原生的狀態機
 └─ read_header()
      └─ process_header_end()      ← 唯一的授權關卡
           └─ translate_uri()      ← Boa 原生 alias.c,只做路徑轉換
                └─ write_body() ─> handleForm()
                                     └─ handler(req, 0, 0)
```

`handleForm` 做的事：`strstr(uri, "/boafrm/")` 找到前綴，跳過 8 個字元，然後
拿剩下的字串去走 `root_form[]` 這個以 NULL 結尾的陣列，比對方式是
**`strlen` 相等 + `memcmp` 全等**。命中就 `send_r_request_ok2()` 然後呼叫函式指標。

表格元素是 `{char *name; void (*fn)(request*, int, char**)}`，一項 8 bytes。

</details>

### 7.2 🔴 你說有 59 個 handler。你怎麼知道不會有第 60 個在別的地方註冊?

<details><summary>答案</summary>

因為 `handleForm` 的迴圈條件是 `*ppuVar5 != NULL`，**它只看這一張表**，沒有
fallback、沒有第二張表、沒有前綴比對、沒有 hash 表。所以「能被 `/boafrm/<name>`
叫到的東西」= 這張表的內容，這是封閉的。

**但要誠實說出這句話的邊界**：我證明的是「`handleForm` 只能到這 59 個」。
沒有排除的是：

- 別的 binary 自己開 port 提供服務（`/bin/skt` 就是一個例子）
- `formAjaxSet`（2020 才有）在它的 JSON body 裡自己再做一層分派
- CGI 路徑 —— `translate_uri` 還認得 `application/x-httpd-cgi`

**加分講法**：「我證明的是這個 dispatcher 的封閉性，不是這台機器攻擊面的封閉性。
這兩件事常被混為一談。」

</details>

### 7.3 🔴 網路上的 rtl819x SDK 原始碼寫 `char name[80]`，你說是 `char *name`。誰錯了?

<details><summary>答案</summary>

兩個都沒錯 —— **是不同的 SDK 版本/設定**。重點是我怎麼知道手上這支是哪一種：

1. **反編譯器**：`ppuVar1 = ppuVar5 + 2`，在 `char**` 上就是 8 bytes 一項。
   如果名字是 `char name[80]` 內嵌，步進會是 84。
2. **交叉檢查**：復原出來的表項數（59 / 49）剛好等於 W01 用完全不同方法
   （數字串表裡的 `form*` 字串）得到的數量。

而且我的復原腳本**沒有假設任何一種佈局**：它測試「`[字串指標][可執行位址]` 是否
以固定間距重複」。如果哪天遇到真的用 `char[80]` 的映像，它會找不到東西並且說找不到，
而不是吐出垃圾。

**加分講法**：「外流的 SDK 是對眼前 binary 的**假設**，不是規格。我拿它當假設來源，
不當事實來源。」

</details>

### 7.4 🔵 `formSysCmd` 在這台機器上在哪裡?

<details><summary>答案</summary>

**不在。** 不在 2015 版的 59 項裡，也不在 2020 版的 49 項裡。
`POST /boafrm/formSysCmd` 會走到 `send_r_not_found`。

</details>

### 7.5 🔴 那 `/tmp/syscmd.log`、`sysCmdselect`、`sysCmdLog` 這些字串是怎麼回事?

<details><summary>答案</summary>

它們是這個功能的**另外半邊**——顯示的那半，不是執行的那半。

W01 提名 `FUN_0044c610`（唯一引用 `/tmp/syscmd.log` 的函式）當 CVE-2019-19824 的
handler。W03 復原表格之後看到：它在 **ASP 頁面變數表**（`0x004885d0`）裡註冊為
`sysCmdLog`，而那張表是 `handleScript` 讀的，不是 `handleForm`。
也就是「頁面裡寫 `<% sysCmdLog %>` 時把 log 印出來」的那個函式。

Realtek SDK 的 `root_form[]` 是照 build-time 的功能開關組出來的。這個產品編進了
log viewer 和 `sysCmdselect` 頁面片段，但沒編進會執行命令的 handler。
**剩下的字串是設定的痕跡，不是功能的證據。**

**這題真正在考的**：三條線索（字串消失、有 log 路徑、有頁面片段）全部指向同一個
**錯誤**答案。把資料結構挖出來一次就結案。**復原結構 > 累積交叉引用。**

</details>

### 7.6 🔵 Boa 的授權檢查在哪一行?

<details><summary>答案</summary>

`process_header_end` @ `0x0040be0c`（V2.1.2）。整段授權區塊的進入條件裡有這一項：

```c
&& strstr(uri, "htm") != NULL
```

也就是說：**URI 裡沒有 `htm` 這三個字，整段檢查被跳過。**

`translate_uri` 是 Boa 原生的 `alias.c`（debug 訊息還印著 `"alias.c"` 和行號），
只做路徑轉換，沒有認證；`handleForm` 也沒有；59 個 handler 沒有任何一個自己再檢查
一次（全部反編譯之後 grep 過 MIB `0x1ec`/`0x1ed`/`0x1ee`，只有 `formLogin` 碰）。
所以那一行就是全部。

</details>

### 7.7 🔴 反編譯器會騙人。你憑什麼確定分支方向是「沒有 htm 就跳過」而不是相反?

<details><summary>答案</summary>

**因為我沒有只看反編譯器。** 這支函式的反編譯輸出頂上掛了三行
`WARNING: Heritage AFTER dead removal` / `Restarted to delay deadcode elimination`,
等於它自己承認處理得不好，所以我去讀組語：

```
0040c234  lw t9,-0x7cbc(gp)        -> PTR_strstr_0048b2f4
0040c238  addiu a1,a1,-0x2be0        "htm"
0040c23c  jalr t9                  -> strstr
0040c240  _move a0,s1                             ; a0 = request URI
0040c248  beq v0,zero,0x0040c3a0                  ; 回 NULL → 跳到 LAB_0040c3a0
```

關鍵是**跟旁邊那幾條比**：白名單頁面（`status.htm`、`login.htm`…）用的都是
`bne v0,zero` —— 「有命中就跳過檢查」。只有這一條是 `beq v0,zero` ——
「**沒**命中就跳過檢查」。而它們全部跳到同一個 `LAB_0040c3a0`，也就是繞過授權區塊、
直接進 `translate_uri`。

**加分講法**：「反編譯器宣告它有困難的時候，從它輸出得到的任何結論都是猜的。
我為此寫了一支輸出組語的腳本，而不是截圖。」

</details>

### 7.8 🟠 公告說的是「`.dat` 檔沒被限制」。你的說法有比較嚴重嗎?

<details><summary>答案</summary>

嚴重很多，而且是**範圍**的差別，不是程度的差別。

公告描述的是**現象**：`.dat` 沒被保護。聽起來像是「漏了一種副檔名」，修法就是
「把 `.dat` 加進檢查清單」。

實際的**原因**是：授權是拿 URI 做子字串比對，所以它保護的只有 HTML 介面。
「沒被保護的東西」不是一份清單，是一整個補集：

| 路徑 | 含 `htm`? | 檢查? |
|---|---|---|
| `/home.htm` | 是 | 有 |
| `/config.dat` | 否 | **沒有** |
| `/ca.cer` | 否 | **沒有** |
| `POST /boafrm/formPasswordSetup` | 否 | **沒有** |
| 全部 59 個 handler | 否 | **沒有** |

**這是 default-allow 的設計**（黑名單思維），不是一個漏掉的副檔名。
`.dat` 從來不是特例，它只是「不是 `.htm`」。

</details>

### 7.9 🔴 可是 CVE-2019-19824 的公告明明寫「authenticated attacker」。你是不是搞錯了?

<details><summary>答案</summary>

三件事要分開講，不要含糊過去：

1. **19824 的端點在這台機器上根本不存在**，所以那條公告的認證前提在這台機器上
   無從驗證。
2. 公告作者用了 `--user "admin:password"` 去測。**「他帶了憑證去測」不等於
   「不帶憑證就進不去」**——這是研究方法造成的描述，不是被測出來的邊界。
3. 那份公告涵蓋的是一整個 Realtek SDK 裝置家族。`root_form[]` 是每個產品各自
   build 出來的，授權那段程式碼各家也可能改過。**跨型號的結論不能直接套。**

**而最重要的一句**：我的結論目前也**只是靜態的**。我讀出了程式碼怎麼寫，
沒有證明機器怎麼跑。要證實只要三個 `curl`，寫在 `notes/auth-flow.md` 最後。
在跑出來之前，正確的講法是「程式碼是這樣寫的」，不是「這台機器可以被這樣打」。

**這題其實在考誠實度，不是技術。** 敢說「我還沒證實」比硬凹有價值得多。

</details>

### 7.10 🟠 登入成功之後，這台機器怎麼記得你是誰?

<details><summary>答案</summary>

**記你的 IP 位址。** 沒有 cookie、沒有 token、沒有 nonce。

`formLogin` 比對成功之後：

```c
apmib_set(0x1ec, req + 0x4bd);   /* 用戶端 IP */
apmib_set(0x1ed, username);
apmib_set(0x1ee, userpass);
```

之後每個 `.htm` 請求就拿 `apmib_get(0x1ec)` 跟來源 IP 做 `strcmp`。
閒置超過 600 秒就把它設回 `0.0.0.0`。

順帶一提：帳密是**明文**存進 APMIB 的（`0x1ed`/`0x1ee`），而 `config.dat` 就是
APMIB 的序列化檔案。這條線把 CVE-2019-19822（設定檔外洩）和 19823（明文密碼）
接了起來——拿到 `config.dat` 就等於拿到這裡比對用的那兩個值。

</details>

### 7.11 🔴 用 IP 當 session，實際上要多少成本才能繞過?

<details><summary>答案</summary>

看攻擊者在哪：

- **同一台機器上的另一個程式**（惡意 App、另一個使用者）：零成本，IP 一樣。
- **同一個 NAT 後面**（公司、宿舍、咖啡廳）：零成本，對外 IP 一樣。這是最現實的場景。
- **同一個 L2 網段**：ARP 欺騙即可，幾秒。
- **純遠端、不同 IP**：需要 IP spoofing，而 TCP 三向交握要求收得到回包，
  所以實務上很難——**但這台機器的 handler 根本不需要通過這關**，因為
  `/boafrm/*` 從頭到尾就沒進授權檢查。

**最後這句才是重點**：IP session 有多弱其實不太重要，因為要改設定的路徑根本繞過它。
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

**帳號列舉（username enumeration）**：兩種失敗回不同的字串，攻擊者可以先確定帳號
存不存在，再去猜密碼。沒有看到任何速率限制。

另外 `strcmp` 不是常數時間，理論上有 timing side channel;不過在這種裝置上
網路抖動遠大於那點差異，**不值得當成賣點講**——會顯得你在背名詞。

</details>

### 7.13 🔴 你說有個「拿未初始化的堆疊當密碼比」。這是漏洞嗎?

<details><summary>答案</summary>

**目前只能說是候選，不能說是漏洞。** 這題的正確答案是把兩件事分乾淨：

**已經確定的**（組語層級）：V2.1.2 的 HTTP Basic 路徑會把使用者送的帳密拿去跟
`sp+0x40` 和 `sp+0x60` 比，比中了給 `authorized = 2`（比一般帳號高一級，
像是 supervisor）。整支函式對這兩個位址**只有三次存取**：兩次是拿位址當 `strcmp`
參數，一次是讀第一個 byte。**沒有任何寫入，位址也沒被傳出去過。**

**還沒確定的**：那塊堆疊在真實執行時裝什麼。這是動態問題：

- 如果 `sp+0x40` 剛好是 NUL 開頭，空帳號就會比中；密碼那邊在 `auth_pass` 為空時
  改讀 `lb v0,0x60(sp)`，那個 byte 是 0 的話也算過。
- Boa 是單一 process、迴圈處理請求，所以固定 frame offset 上的殘留值
  比多執行緒伺服器可重現得多。

**所以現在的處置**：記在 `notes/auth-flow.md` 當 W05/W06 的候選，
**在證實或否證之前不會報給任何人**。

**加分講法**：「靜態分析能證明程式碼寫錯了，不能證明錯得可以被利用。
把這兩件事混在一起講，是漏洞報告被退件最常見的原因。」

</details>

### 7.14 🔵 `formWsc` 有哪些請求參數會進 `system()`?

<details><summary>答案</summary>

- **`localPin`** → `sprintf(buf[100], "flash set HW_WLAN0_WSC_PIN %s", localPin)` → `system()`。
  **沒長度檢查、沒字元過濾。** 同時是命令注入和堆疊溢位。
- **`peerPin`** → 兩條路徑：
  - 一條只抽數字進 `local_254[52]`，**但抽的時候索引沒有上限** → 純溢位。
  - 一條 `sprintf(buf, "echo %s > /var/wps_peer_pin", peerPin)` → **原始值直接進 `system()`**。
- **`targetAPSsid`** → `iwpriv wlan%d set_mib wsc_specssid="%s"` → `system()`。
  有長度檢查（< 33），但**沒有跳脫**。

2015 和 2020 兩版**一模一樣**，五年沒動。

</details>

### 7.15 🔴 `targetAPSsid` 有長度檢查了，為什麼還是漏洞?

<details><summary>答案</summary>

因為長度檢查擋的是**溢位**，擋不了**注入**。它被塞進 shell 命令的雙引號裡：

```c
sprintf(buf, "iwpriv wlan%d set_mib wsc_specssid=\"%s\" ", wlan_idx, targetAPSsid);
system(buf);
```

送 `a";reboot;"` 就把引號關掉、接上自己的命令，而且長度遠小於 33。

**根因要講精確**：「缺的不是長度檢查（那個有），是**在把資料放進另一種語言的
語法之前沒有做對應的跳脫**。」加引號不是跳脫，引號本身也是資料的一部分。

</details>

### 7.16 🔴 同一支函式裡，`targetAPMac` 有嚴格過濾，`targetAPSsid` 沒有。這說明什麼?

<details><summary>答案</summary>

`targetAPMac` 是逐字元檢查是不是 `[0-9a-fA-F]`，而且要求長度剛好 12。
十行之後的 `targetAPSsid` 只檢查長度。

說明：**開發者會寫過濾，而且知道怎麼寫**。問題不是能力，是**每個參數各自為政**——
沒有統一的輸入處理層，每個欄位靠寫的人當下記不記得。

這是 ad-hoc 輸入處理的典型長相，而且它的失敗模式是**隨機的**：同一支函式裡有的
參數安全、有的不安全，審查的時候很容易看到前面那個安全的就放心了。

**這題的關鍵**：能把它講成「這是架構問題不是個案」，並且提出修法方向
（集中式的參數取得層，在 `req_get_cstream_var` 那一層就依用途做白名單），
比列出三個 bug 有價值得多。

</details>

### 7.17 🔵 `/bin/skt` 做什麼?

<details><summary>答案</summary>

10 KB、36 個函式，可以整支看懂。

- 不帶參數執行 → `TcpServer(0x15b3, 0xe10)`，**聽 TCP 5555**。
- 收到 `hel,xasf` → `system("iptables -I INPUT -p tcp --dport 80 -i eth1 -j ACCEPT")`
- 收到 `oki,xasf` → 同一條規則的 `-D`（刪除）
- 另外還有 `gvr,xasf`、`bye,xasf` 兩個暗號（沒有副作用，推測是握手/關閉）

**它不給 shell，也不繞密碼。它是「可達性後門」**：把本來被防火牆擋在外面的
管理介面打開。`eth1` 在這塊板子上應該是 WAN 側 —— 但那是從 iptables 規則讀出來的，
還沒在實機驗證（W02）。

</details>

### 7.18 🟠 `rcS` 裡 `skt` 那行被註解掉了（`#skt&`），它沒在跑。那還算漏洞嗎?

<details><summary>答案</summary>

**「不啟動後門」和「沒有後門」是兩件不同的事。**

V2.1.2 的日期是 2015-08-25，大約在 Pierre Kim 2015 年 7 月揭露之後五週。
廠商對一個已公開後門的回應，是**把啟動它的那一行註解掉，然後照樣把 binary
出貨**——放在 `/bin`，而且是可執行的。

任何能執行一條命令的東西，都能執行 `/bin/skt &`。而這台機器的 web 介面上就有
好幾條能執行命令的路徑（`formWsc`）。所以它把「一個 RCE」升級成「一個 RCE 加上
一條持久化的對外通道」。

**而這件事可以量化，不是嘴砲**：V3.4.0（五年後）把檔案整個刪掉了。
廠商後來做對了；2015 年做的是便宜的那個。

</details>

### 7.19 🔴 你的 sink 統計第一版說 2020 版只有 1 個 `strcpy`。你怎麼發現那是錯的?

<details><summary>答案</summary>

**因為它跟旁邊的數字對不起來。** 2015 版 589 個、2020 版 1 個，可是：

- 兩者是同一份程式碼，大小只差 11%
- `sprintf` 兩邊都是 694 個，`memcpy` 是 110 vs 112
- `nm -D` 明明說 2020 版還在 import `strcpy`

一份 C 程式不可能只有一次 `strcpy` 而有 694 次 `sprintf`。**兩個來源不一致的時候，
不一致本身就是資料。**

原因：2020 版被 `sstrip` 過（沒有 section header）而且有真正的 PLT
（`DT_MIPS_PLTGOT`）。Ghidra 找不到 `.plt` 去標它，只有部分項目被建成函式——
`system`、`sprintf` 有，`strcpy` 沒有。所以呼叫方指到一個**沒有名字的 stub**,
而我只數了指到 symbol 本身的參考。

**這是 W01 `readelf` 那個坑的第二次。** 所以現在報告裡有 `self_check`：
只要有 symbol 被 import 卻找不到呼叫方，整份檔案標成 `SUSPECT`。

</details>

### 7.20 🔴 那你怎麼修的?別跟我說你用猜的。

<details><summary>答案</summary>

**先量再修。** 修之前先數：`jal = 9979`、`jalr = 16`。
所以幾乎所有呼叫都是直接跳 PLT，不是 `lw t9,%call16(gp)` 那種 GOT 間接呼叫——
代表**不需要**去解 `gp`，問題單純是 PLT 項目沒被辨識出來。

而 MIPS 的 PLT entry 是 binutils 產生的四道固定指令，每個欄位都由 `.got.plt`
的 slot 位址 `S` 決定：

```
lui   $15, %hi(S)        3C 0F hi
lw    $25, %lo(S)($15)   8D F9 lo
addiu $24, $15, %lo(S)   25 F8 lo
jr    $25                03 20 00 08
```

所以我是**把這 16 個 byte 算出來**再去記憶體找，而且規定「只能命中一次；
命中兩次或零次就不採用」——寧可回報找不到，也不要挑一個。

順手還修了一件事：從**函式外面**來的 data reference 是 GOT 欄位，不是呼叫點。
就是它讓 `strcpy` 回報「1」而不是誠實的「0」。**把 1 變回 0，才會觸發 self_check。**

修完：587 vs 577，兩個 build 對得上了。

</details>

### 7.21 ⚪ 你這週所有結論都是靜態的，機器還沒到。要怎麼證明它們是對的?

<details><summary>思考方向</summary>

先承認靜態分析能給什麼、不能給什麼：

- **能給**：程式碼寫成什麼樣、資料結構長什麼樣、哪條路徑存在。
- **不能給**：實際執行時的狀態（堆疊殘留）、設定相依的分支（那個 MIB `0x10e`
  兩條路徑走哪條）、以及最重要的——**這台機器上實際跑的是哪個 build**。

驗證分三層，成本由低到高：

1. **模擬**（W05）：W01 已經證明 `qemu-mips-static` + chroot 可以讓 2015 版的
   `boa` 跑起來並印出 usage。缺的是 `libapmib.so` 會去讀 `/dev/mtd*`。
   把那層擋掉或做假，就能發真的 HTTP 請求。
2. **實機**（W02 到貨後）：三個 `curl` 就結案 ——
   `GET /config.dat` 應該回 200、`GET /home.htm` 應該回 401、
   `POST /boafrm/formPasswordSetup` 應該真的改掉密碼。
3. **交叉比對**：找同家族其他型號的韌體，看 `strstr(uri,"htm")` 這個模式是不是
   Realtek SDK 的共通寫法。如果是，這就不是一台機器的 bug。

**這題的關鍵**：主動說出「我的結論還沒被執行驗證過」比被問出來好一百倍。
而且要能講清楚**驗證計畫**——有計畫的未完成，和沒想過的未完成，是完全不同的東西。

</details>

---

## 8. W04：CVE 根因定位、2020 版授權、工具會騙人

> 🔴 = 一定會被問到 · 🟠 = 有機會 · 🔵 = 送分題 · ⚪ = 你要主動講的

### 8.1 🔴 你說 2020 版「修好了」又說「還是有洞」。到底是修了還是沒修?

<details><summary>答案</summary>

**兩件事都是真的，而且要分開講，因為它們是不同的宣稱。**

W03 找到的洞是：2015 版的閘門條件是 `strstr(uri, "htm")`，而 59 個
`/boafrm/form*` 端點的 URI 裡沒有 `htm`，所以**一個都沒被檢查**。

2020 版把條件換成 `(URI 含 ".htm") || (URI 含 ".asp") || (method == POST)`。
所有 handler 都是 POST，所以**全部進閘門了。這個洞是真的修好了。**

沒變的是**判斷方式**：兩版都是拿 `strstr` 掃整條 URI。2015 是「納入條件」太窄，
2020 把納入條件放寬了，結果換成「豁免清單」變成窄的那一端：

```
0040a2cc  move a0,s1              ; a0 = request URI
0040a2d0  jal strstr
0040a2d4  _addiu a1,a1,0x8a0      ; "login"
0040a2d8  bne v0,zero,0x0040a354  ; 含 "login" -> 跳過轉址
```

`strstr` 沒有綁開頭，所以 URI 裡**任何位置**出現 `login` 都算。

我的講法是：**根因沒有變，只是換了個地方冒出來。** 這比「修好了」或「沒修」
都更接近事實，而且是可以驗證的說法。
</details>

### 8.2 🔴 `POST /login/boafrm/formWsc` —— 你實際打過嗎?

<details><summary>答案</summary>

**沒有。這是靜態讀出來的，機器還沒到手，W02 卡在硬體。**

我能講到多細：三個 `strstr` 都不綁位置，而且**讀的是同一個欄位**（`req + 0xf8`）：

1. 閘門 `0x0040a2d8`：`strstr(uri, "login")` → 有就跳過轉址
2. `translate_uri` `0x00403860`：POST 打到非 CGI 路徑，`strstr(uri, "boafrm")` 有就放行
3. `handleForm` `0x0040ee60`：`strstr(uri, "/boafrm/")` 找到後，對後面 8 bytes 做精準比對

中間 `clean_pathname` 會把 `.` 和 `..` 收掉，但這條路徑兩個都沒有。

要證實只要兩個請求：`POST /boafrm/formWsc`（對照組，應該被轉址）和
`POST /login/boafrm/formWsc`（應該進 handler）。兩個都被轉址，就是我讀錯，
那它會以否定結果留在 `notes/auth-flow-2020.md` 裡。

**而且在 W05/W06 跑出來之前，我不會回報給任何人。** 靜態讀三個 `strstr`
不等於漏洞，拿去通報只會浪費別人的時間。
</details>

### 8.3 🔴 十四個 CVE 你說只有三個缺陷。這不是在幫廠商講話嗎?

<details><summary>答案</summary>

正好相反，這對廠商更難看。

- CVE-2025-3987 和 CVE-2025-4462 是**同一行**：
  `sprintf(buf[100], "flash set HW_WLAN0_WSC_PIN %s", localPin); system(buf)`。
  一個講沒過濾，一個講沒長度檢查。同一行，兩個編號。
- CVE-2025-3990/3991/3992/3993 是**同一段三行的尾巴**，複製在 **34 個 handler** 裡。
  有編號的只有四個。

所以真正的意思是：**編號的數量反映的是有人送了幾份 PoC，不是缺陷有幾個。**
而且那一行在 **2015 版裡一字不差** —— 這些不是 2025 年的 bug，是 2015 年的 bug
花了十年才被登記。

我用來說明的方式：「如果我照 CVE 清單修，我會修四個 handler，剩下 29 個一樣有洞。」
</details>

### 8.4 🔴 `lastUrl` 是 100 bytes，你怎麼知道?別跟我說是反編譯器講的。

<details><summary>答案</summary>

不是反編譯器，是 **V2.1.2 的符號表**：

```
$ readelf -sW bin/boa | grep -E 'lastUrl|needReboot'
   421: 0049087c   100 OBJECT  GLOBAL DEFAULT   23 lastUrl
   241: 004908e0     4 OBJECT  GLOBAL DEFAULT   23 needReboot
```

`0x49087c + 100 = 0x4908e0`，剛好就是 `needReboot`。所以不但知道大小，
還知道**溢出去第一個踩到的是誰**：兩個控制旗標，而且 `needReboot = 1` 就寫在
那個 `strcpy` 的上一行。

補充一句可以主動講的：這是 **`.bss` 的資料溢位，不是堆疊溢位**。
沒有 canary 的問題，也沒有 return address 在旁邊。踩到的是相鄰的全域變數。
把它講成「可以蓋 return address 拿 shell」就是吹牛。
</details>

### 8.5 🔴 你說少帶一個參數就能讓 web server 掛掉。憑什麼?

<details><summary>答案</summary>

`req_get_cstream_var` 找不到參數時，回傳的是**呼叫端傳進來的預設值**：

```c
if (-1 < (int)__n) {
    param_3 = malloc(__n + 1);      /* 找到了:配剛好的大小 */
    ...
}
return param_3;                      /* 沒找到:原封不動回傳預設值 */
```

而所有 handler 都是這樣呼叫的：`req_get_cstream_var(req, "submit-url", "")`。
那個 `""` 是 `.rodata` 裡的字面常數（V2.1.2 在 `0x476418`）。

```
LOAD  0x000000 0x00400000 0x00400000 0x77744 0x77744 R E   <- .rodata 在這裡
LOAD  0x078000 0x00488000 0x00488000 0x0368c 0x1ea18 RW
```

`R E`，沒有 W。然後 handler 做 `strcpy(pcVar1, "/status.htm")` —— 往唯讀分頁
寫 12 bytes。boa 是**單一 process** 在迴圈裡處理請求，掛了就沒了。

**這是靜態推論，不是觀測。** 我沒跑過。要推翻它只需要一個請求。
但它同時解釋了一件事：這個型號所有公開 PoC 都帶 `submit-url=`。
如果少帶會 500 或 400，大家不會這麼一致。
</details>

### 8.6 🔴 W01 寫「兩份映像檔都沒有 `/etc/passwd`」。現在你說有。哪一次是錯的?

<details><summary>答案</summary>

**W01 錯了，而且錯得很典型。**

`/etc/passwd` 是一個指向 `/var/passwd` 的 symlink。`/var` 是開機才掛上去的
tmpfs，在**解包出來的映像檔裡當然不存在**，所以 `stat` 回答「不存在」。

W01 把「symlink 指到的東西不存在」讀成「檔案不存在」，然後從這裡推出
「認證檢查一定在某支 binary 裡」，並且用這個理由把後門帳號的問題往後推了
W01、W03、大半個 W04。

真正的內容一直躺在旁邊：

```
$ cat etc/passwd.org            # V2.1.2
root:zhxPr1e7Npazg:0:0:root:/:/bin/sh
onlime_r:$1$01OyWDBw$Hrxb2t.LtmiiJD49OBsCU/:0:0:root:/:/bin/sh

$ strings -a bin/sysconf | grep passwd
cp /etc/passwd.org /var/passwd 2> /dev/null
```

教訓：**在韌體映像檔裡，懸空的 symlink 是常態不是異常。**
`/var` 底下所有東西都是開機才寫的。正確的問題不是「這個路徑存在嗎」，
而是「這個路徑存在嗎；如果不存在，映像檔裡有沒有東西會寫它」。

順帶一提，W01 的**結論**（web 的認證檢查在 binary 裡）其實是對的 ——
它在 MIB `USER_NAME` / `USER_PASSWORD`。對的結論，錯的證據。
這種情況比純粹講錯更危險，因為它不會被自己發現。
</details>

### 8.7 🔴 `onlime_r` 的密碼你是怎麼知道的?你破解了廠商的東西?

<details><summary>答案</summary>

雜湊值在**我自己買的機器的韌體檔案裡**，用 `crypt()` 對二十個常見字串比對：

| 帳號 | 雜湊 | 演算法 | 密碼 |
|---|---|---|---|
| `root` | `zhxPr1e7Npazg` | DES crypt | `123456` |
| `onlime_r` | `$1$01OyWDBw$Hrxb2t.LtmiiJD49OBsCU/` | MD5-crypt | `12345` |

`onlime_r` 那個根本不用破 —— **Pierre Kim 2015 年的公告上就印著同一串雜湊**。
我做的只是確認它一字不差地出現在**廠商在他公告之後才發布的版本**裡。

而 `root` 是 DES crypt：8 個有效字元、56-bit，現在的硬體幾秒鐘。
兩版都是 `123456`，而公告上寫的是 `12345`。廠商的修法是加一位數。
</details>

### 8.8 🟠 `config.dat` 裡的密碼在第幾個 byte?

<details><summary>答案</summary>

**我不知道，而且我不會猜。**

我知道的是格式：`libapmib.so` 寫的檔案是 `COMPCS` 魔術字 + **壓縮過的 TLV 串流**，
內容是 MIB 表的序列化。同族還有 `COMPHS`（硬體設定）、`COMPDS`（預設設定），
對應 `/dev/mtdblock0` 上的三塊區域。

所以 CVE-2019-19823「明文儲存密碼」的意思是：`USER_PASSWORD` 就是一個普通的
MIB 項目，一個普通的 TLV 紀錄，**中間沒有任何雜湊步驟**。這也是為什麼
`formLogin` 可以直接 `strcmp(userpass, cfg_pass)`。

但「第幾個 byte」需要一份真的 `config.dat`，而那需要 W02 的 flash dump
或者一台跑著的機器。壓縮演算法我也還沒認出來。
**證據支持的是「這是 MIB 表的壓縮序列化」，不是「密碼在 offset N」。**
</details>

### 8.9 🔵 `apmib_get(0xb6)` 的 `0xb6` 是什麼?

<details><summary>答案</summary>

`USER_NAME`。`0xb7` 是 `USER_PASSWORD`。

不是猜的 —— `libapmib.so` 裡有一張 413 筆的表，每筆 60 bytes：
big-endian `uint32` 編號，接一個 **32 bytes 內嵌的名字**。

版面是量出來的，不是照網路上的 SDK header 抄的（這個專案在
`dispatch-table.md` 已經被那樣坑過一次）：

```
00c818  00 00 01 ec                                    id
00c81c  41 55 54 48 47 5f 49 50 5f 41 44 44 52 00 ...  "AUTHG_IP_ADDR"
00c854  00 00 01 ed                                    <- 正好 0x3c 之後
00c858  41 55 54 48 47 5f 55 53 45 52 5f 4e 41 4d 45   "AUTHG_USER_NAME"
```

而且這三個編號正好就是 `process_header_end` 在用的 `0x1ec/0x1ed/0x1ee` ——
**兩個獨立來源（binary 的行為 + 另一個檔案的表）對上了**，這才是可以拿去用的。
</details>

### 8.10 ⚪ 你的工具錯了三次，自我檢查三次都說沒問題。那你的結論還能信嗎?

<details><summary>答案（這題要自己主動講）</summary>

**這題我主動講，因為它是這週最有價值的東西。**

`BoaArgTrace` 連續錯三次，三次 `self_check` 都寫 `consistent`：

| 次數 | 症狀 | 原因 |
|---|---|---|
| 1 | 304 個呼叫點只有 1 個被標成有請求參數 | 同一套解析邏輯寫了兩份，走鐘了 |
| 2 | 2015 版 86 個、2020 版 **0** 個 | `accessor:` 拿去跟小寫化的名字比，永遠不相等 |
| 3 | `strcpy` 2015 版 151 個、2020 版 **0** 個 | W03 已經修過的 sstrip PLT 問題，我重寫了一份沒帶上修正 |

抓到它們的**不是自我檢查**：

- 第 1 次：W03 已經**用手讀**出 `formWsc` 有三個參數進 `system()`，工具一個都沒找到。兩個來源不一致。
- 第 2、3 次：把兩版並排比。同一份程式碼相隔五年，不可能 86 → 0。

結論兩句：

> **一個永遠不會觸發的檢查，也永遠不會失敗。**
> `self_check: consistent` 只代表「我想到要檢查的那幾件事沒問題」。

所以我做了兩件事而不是只修 bug：把 PLT 解析抽成 `BoaPlt.java` **只留一份**
（同一個 bug 在同一個專案出現兩次，就不是 bug 是設計問題），
以及讓「給了選項卻沒配對到任何東西」變成錯誤而不是沉默。

至於結論能不能信：**能信的部分是有第二個來源的那些。**
`lastUrl` 是 100 bytes —— 符號表講的。閘門的分支方向 —— 組語講的。
`onlime_r` 的雜湊 —— 檔案裡就有，而且對得上公開公告。
沒有第二來源的，我都標成「照程式碼讀是這樣」並且寫出要怎麼推翻它。
</details>

### 8.11 🟠 `execl` 那六個 handler，你 W03 說參數是使用者控制的。現在呢?

<details><summary>答案</summary>

**W03 猜錯了，而且是我自己推翻的。**

兩版所有 `execl` 呼叫點，argv 都是：

```c
execl(path, "firewall.sh", NULL);      /* 或 ip_qos.sh / radvd.sh / ntp.sh */
```

一個固定的腳本名字加一個 NULL。**沒有任何請求參數進到 argv。**

那使用者輸入去哪了?**進 MIB**,shell 腳本之後自己讀回來。
所以問題還在，只是搬家了 —— 真正該讀的是 `/etc/scripts/*.sh`，
一個 MIB 值被 `firewall.sh` 內插進命令，跟直接注入是同一個 bug，只是晚一個 process。

界線也要講清楚：我的工具解析的是**呼叫當下的參數**，`argv[0]` 是一個裝著路徑的
堆疊 buffer，工具**不會回頭追誰寫進那個 buffer**。所以「沒有請求參數進 argv」
成立的範圍是參數欄位，不包含路徑本身。
</details>

### 8.12 🔴 `formSysCmd` 不在表裡。你 W03 說是「編譯時沒開這個功能」，現在改口?

<details><summary>答案</summary>

**改口，而且新的說法比舊的強，因為它可以被推翻。**

W03 的說法是「SDK 的 `root_form[]` 是按產品組出來的，這台編譯時沒帶這個 handler」。
那是猜的，而且沒有任何東西支持。

日期支持另一個說法。Pierre Kim 的 `2015-totolink-0x02.txt` **點名 N150RT-V2**,
說它有 CVE-2015-9551（`/boafrm/formSysCmd` 未認證 RCE），
而且寫明「until last firmware **`TOTOLINK-N150RT-V2.1.1-B20150708.1548.web`**」。

我手上這份 V2.1.2 是 **2015-08-25** —— 他說最後一個有洞的版本之後。
而在這份裡，handler 從分派表消失了。

所以比較可能的解釋是：**這就是修補本身，被我看到了。**
同一個版本還做了另外兩件事：把 `#skt&` 註解掉（但留著 binary），
以及**把 `onlime_r` 留在 `passwd.org` 裡**。三件事修好一件。

**而且這是可以驗的：** 去抓 V2.1.1-B20150708，挖它的 `root_form[]`。
有 `formSysCmd` → 我說對了；沒有 → 我又錯了，W03 的說法反而比較接近。
這個實驗寫在 `PROGRESS.md` 的 carried-forward 清單裡。
</details>

### 8.13 🟠 你說 2020 版的 401 函式沒有人呼叫。萬一是 Ghidra 沒找到呢?

<details><summary>答案</summary>

這正是我不敢只用一個工具的地方，所以查了兩次。

Ghidra 說 `FUN_0040b850` 的 caller 數是 0。第二個來源是**直接掃原始 bytes**：
MIPS 的 `jal` 是絕對定址，目標編碼進指令裡，跟指令自己的位址無關。

```
jal 0x0040b850  ->  0x0C000000 | (0x0040b850 >> 2)  =  0C 10 2E 14
```

在整個 ELF 裡掃這四個 byte：**0 次**。

而同一支掃描程式，在同一個檔案裡找 `jal 0x0040a4f8` 找到 **1 次**、
`jal 0x00408720` 找到 **1 次** —— 跟 Ghidra 報的數字一樣，而且位置
（file offset `0x8910`）跟 Ghidra 報的呼叫點位址（`0x00408910`）對得上。
**掃描器是校準過的，所以那個 0 是真的。**

意義：這台機器**永遠不會回 401**。沒過認證是被 302 轉去登入頁。
寫 PoC 的時候如果去 assert 401，會對著一台行為完全正常的機器 debug 半天。
</details>

### 8.14 🔵 這週你最不確定的是什麼?

<details><summary>答案</summary>

按不確定程度排：

1. **`POST /login/boafrm/formWsc` 到底會不會進 handler。** 三個 `strstr`
   都讀過、組語層級確認過分支方向，但沒跑過。
2. **少帶 `submit-url` 會不會真的讓 boa 掛掉。** `.rodata` 在 `R E` segment
   是量出來的，回傳預設值的路徑也是讀出來的，但「寫唯讀分頁會 SIGSEGV」
   是作業系統行為，不是我從這份 binary 讀到的。
3. **`0x182` 那個重複的 MIB 編號**（`CUSTOM_PASSTHRU_ENABLED` 和
   `MLD_PROXY_DISABLED`）。我相信它是廠商表裡真的重複 —— `libapmib` 自己就帶
   `"MIB Error: %s detect duplicate id in %s"` 這個字串、還 export 了
   `mibtbl_check` —— 但我沒去讀查表函式確認它到底會回哪一個。
4. **四個 handler 在 2020 版沒顯示 `submit-url` 汙染但還存在**
   （`formDdns`、`formNewSchedule`、`formSysLog`、`formWanTcpipSetup`）。
   是被改寫了，還是我的六跳回溯不夠深?沒查。

前兩個 W05 一個 `curl` 就有答案，後兩個是純靜態、隨時可以做，只是這週沒排進去。
</details>

---

## 9. W02：硬體（Day 1）

> 這一節全部是 **2026-08-14 拆機當天**的題目。
> **到目前為止機器一次都沒有通電** —— 所有答案的來源都只有「晶片外殼上的油墨」。

### 9.1 🔴 公開規格寫這台是 2MB flash。你說 4MB。你憑什麼?

<details><summary>答案</summary>

**兩個答案，而且順序才是重點。**

**事前（W01，硬體還沒到貨）：** `.web` 容器每一段標頭裡有 `burnAddr`（要燒到快閃
記憶體的偏移）和 `len`。把兩份韌體所有段的 `burnAddr + len` 取最大值，得到
**3.57 MiB**。2 MB = 2.00 MiB，**塞不下**。

所以結論不是「規格可能不準」，是「**規格不可能對**」，而且它推出一個可證偽的
預測：實體 flash **至少 4 MB**。這條在硬體到貨前三週就寫進 `PROGRESS.md` 了。

**事後（W02 Day 1）：** `U19` 的絲印是 `cFeon QH32B-104HIP` → EN25QH32B →
**32 Mbit = 4 MiB**。

**這題真正在考的不是我答對了。** 是我**先做出可證偽的預測，再去量**。
反過來（先看晶片、再回頭解釋為什麼合理）完全沒有資訊量 —— 任何結果都能事後解釋。

</details>

### 9.2 🔴 `flashrom` 也說 4096 KiB 啊，那不就兩個來源了?

<details><summary>答案</summary>

**不是。這是這一整題最容易答錯的地方。**

`flashrom` 的晶片資料庫是**用料號當索引**的，而那個料號是我從**同一塊晶片上的
同一行油墨**讀出來，再打進 `grep` 的。

它證明的是：

> 「**如果**這顆是 EN25QH32，那它就是 4096 KiB，而且我讀得動它。」

不是「這顆是 4 MiB」。**兩個來源共用同一個上游，就只是一個來源。**

真正獨立的第二來源是**晶片自己在 SPI 匯流排上回報的 JEDEC ID**（Eon 的廠商碼是
`0x1C`）—— 那是晶片內部暫存器，不經過油墨。要夾上去才有，Day 4 的事。

**這跟 W01 踩過的坑是同一種：** 在 `sstrip` 過的 ELF 上，`readelf` 和 `nm -D`
不是獨立來源，因為它們讀的是同一張（已經被砍掉的）section header。
`nm -D` 和 Ghidra 才是。

</details>

### 9.3 🔴 絲印會不會是假的?這個價位帶打磨重標的料很多。

<details><summary>答案</summary>

**防不了，只能換一條不經過油墨的通道去問同一個問題。**

| 要確認的 | 不經過油墨的來源 |
|---|---|
| flash 型號 / 容量 | **JEDEC ID** —— 晶片內部暫存器 |
| SoC 型號 / 核心 | **bootloader banner + `/proc/cpuinfo`** —— 矽晶片自己說的 |
| RAM 可用容量 | **核心開機時印出來的數字** |
| 電源 IC 功能 | **電表量它的輸出腳** |

注意這四個都**不是「看得更仔細」**，是**換一個物理通道**。用更好的顯微鏡再看一次
油墨，不會增加任何獨立性。

而且重標會自己露餡：如果有人把 16 Mbit 打磨成 32 Mbit,`flashrom` 讀出來的
JEDEC ID 和容量會跟絲印打架 —— 那個矛盾本身就是答案。

**誠實的現況：今天為止，這份筆記裡五顆 IC 的第二來源欄位全部是空的。**

</details>

### 9.4 🟠 板子是 2018 年組的，你分析的兩份韌體是 2015 和 2020。那你到底在分析什麼?

<details><summary>答案</summary>

**這正是 G2 存在的理由，而且我現在還答不出來。** 那是誠實的狀態，不是漏洞。

但不是完全沒資訊。板上的日期碼：

| 料件 | 碼 | 解讀 |
|---|---|---|
| cFeon flash | `1750HKB` | 2017 w50 |
| **Winbond SDRAM** | **`1837H`** | **2018 w37** ← 最新 |
| U&T 磁性元件 | `1818A` / `1818Q` | 2018 w18 |
| LSC 電源 | `181525` | 2018 w15（推測） |
| PCB 廠標 | `18.15` | 2018 |

五顆獨立來源的料件全部落在 2017–2018，**所以板子組裝不早於 2018-09**。

**於是我寫下一個預測：** 這台上面的 build 大概在 2018 年前後，**既不是 2015 的
V2.1.2，也不是 2020 的 V3.4.0**。2025 那批 CVE 點名的是 `3.4.0-B20190525`
（2019-05），時間上就在這塊板子之後不久。

**兩個會打臉的地方，先講在前面：**（a） 前手可能升級過韌體；（b） 產線常常燒的是
幾個月前的舊 image。所以日期碼綁的是**板子**，不是韌體，給的是**下限**。

**為什麼值得先寫下來：** 如果 dump 出來真的是 2018 年的 build，這個專案就從
「兩點前後對照」變成**三點時間軸**，而第三點正好落在 2015 的洞和 2020 的修補
之間 —— 也就是最想知道發生了什麼的那一段。事後才發現，跟事前就預測到，
是完全不同的兩件事。

</details>

### 9.5 🔴 SoC 是 RTL8196**E** 不是 8196**C**。這會不會讓你 W01 的「MIPS-I」結論失效?

<details><summary>答案</summary>

**不會失效，但會改變它的意義 —— 從「限制」變成「選擇」。**

W01 記的 MIPS-I 是從 ELF header 的 `EF_MIPS_ARCH` 讀的。那個欄位描述的是
**編譯器的目標**，不是矽晶片的能力。

8196C 一般記載的核心是 Lexra **RLX4181**,8196E 是 **RLX5281**。Lexra 的舊核心
因為 MIPS 的專利，**拿掉了非對齊存取指令 `LWL` / `LWR` / `SWL` / `SWR`**。

所以如果矽晶片支援、而 binary 裡一個都沒有，那代表 **Realtek SDK 的 toolchain
到 2020 年都還鎖在整個產品線最舊的相容基準上** —— 那才是 ELF header 寫 MIPS-I
的真正原因。

**這是可證偽的：數 `/bin/boa` 裡那四個 mnemonic 出現幾次。**
0 次 → 假說成立；非 0 → 要另找理由。**還沒跑，需要一支 Ghidra 的 mnemonic 直方圖。**

> ⚠️ **陷阱：「W01 用 `qemu-mips-static` 跑起來了」不能拿來當證據。**
> Lexra 是 MIPS 的**子集**，子集編出來的程式在完整的模擬器上本來就跑得動 ——
> 兩種情況下 qemu 都會成功。**一個兩種假設都預測相同結果的實驗，沒有鑑別力。**

</details>

### 9.6 🟠 RAM 晶片是 256 Mbit = 32MB。你為什麼不直接把文件改成 32MB?

<details><summary>答案</summary>

因為**「板上裝了多少」和「系統實際用多少」是兩件事**。

- **裝載量**：32 MiB —— 來源是晶片絲印。
- **可用量**：未知 —— 由 bootloader 的記憶體控制器設定決定，核心開機時會印出來。

兩個數字都要記，而且**分開記**。如果它們不一樣，**那個不一樣本身是發現，
不是誤差** —— 可能是 SDK config 只開了一半，也可能位址線沒全接。

這跟這個專案一路上的同一條紀律：**分清楚「我觀察到什麼」和「我推論出什麼」。**
「晶片是 32MB」是觀察，「這台有 32MB 可用」是推論，而我還沒有做那個推論的證據。

</details>

### 9.7 🔴 你拆機第一個動作是拿 450°C 去燒天線焊點，燒不開。為什麼?

<details><summary>答案</summary>

**是熱容量的問題，不是溫度的問題。**

那個焊點的另一端接的是 **RF 接地銅箔** —— 整片地平面加上底下的過孔陣列。銅的
導熱率約 400 W/m·K，對烙鐵頭來說那就是一片散熱片。熱流進去的速度比流走的速度
慢，焊點大概永遠停在 150–200°C。**顯示的 450 是烙鐵尖端的溫度，不是焊點的溫度。**

一起在害你的：

- **細錐頭接觸面積太小**（約 1 mm²）。傳熱功率正比於接觸面積，刀頭差好幾倍
- **家用烙鐵沒有閉迴路溫控**，感溫在加熱棒不在尖端 —— 一碰大銅面，尖端瞬間掉到
  250°C 以下，而面板還顯示 450
- **450°C 反而更難焊**：助焊劑在你需要它工作之前就**碳化燒光**了
- 同軸/多股線本身也是散熱片

**熔點從來不是問題：** 有鉛 Sn63Pb37 是 **183°C**，無鉛 SAC305 是 **217–220°C**,
兩個都遠低於 450。

**正確做法是反直覺的：先「加錫」，不是先「吸錫」。** 刀頭（2.5–3 mm）→ 塗助焊劑
→ 灌一坨新的**有鉛**錫（把合金熔點拉低，而且形成液態熱橋，傳熱效率跳一個量級）
→ 溫度回到 **350–370°C** → 大銅面從背面熱風預熱 180–200°C。

**而 450°C 已經在燒板子了** —— 焊盤底下的膠 250°C 就開始軟化，撐夠久焊盤會整片
跟著烙鐵起來，而 RF 那段的 50Ω 匹配修不回來。

</details>

### 9.8 🔴 那你最後為什麼沒拆?你不是已經花了時間在上面?

<details><summary>答案</summary>

**因為它不對應 G2 任何一格。** G2 要的是 bootlog、SPI dump、dump 對官方韌體、
標註過的 PCB 照片。天線在不在板上，對這四樣一樣都沒有幫助。

另外兩個理由：

1. 那條線的終點是 **RTL8188ER 的輸出級**。拆掉之後通電 = 讓功率放大器對著開路
   發射。1T1R 的功率不高、風險不戲劇性，**但收益是零 —— 這種賭注不該下**。
2. **這台是 G2 和 G4 的單點故障。** W05 要把 web server 服起來、W06 要在實機上
   重現 CVE，都靠它，而且沒有備品。

**但這一題真正的答案不是技術，是判斷：**

> 任何不可逆的動作，都要先答得出「**這一刀換到哪一個 gate 的哪一格?**」
> 答不出來就不要動。

而我當時答不出來 —— 我問的是「溫度夠不夠高」，而不是「我為什麼要拆」。
**問錯問題比答錯問題貴。**

而且我還差點毀掉一樣交付物：**G2 的第四格是標註過的 PCB 照片，而原廠狀態
只有一次機會拍。**

</details>

### 9.9 🟠 開關那兩根線，剪掉扭在一起變常開不就好了?

<details><summary>答案</summary>

**因為我不知道那兩根線是什麼，而不知道就短接是在賭。**

兩種常見拓撲：

- **串在 DC 電源路徑上**：DC 座 → `J2` pin1 → 上去開關 → 回 `J2` pin2 → 降壓電路。
  短接 = 常開，能動。
- **接到 SoC 的 GPIO**（有 pull-up）：短接的意義取決於極性，可能是「一直被按著」。

從照片看，`J2` 就緊貼著 DC 座，layout 像第一種。**但那是從照片推的，不是量的。**

**量它只要三分鐘**（電源全部拔掉）：

1. 通斷檔量**線那一側**：撥開關，一邊嗶一邊不嗶 → 單純的串聯開關。
2. 量**板那一側**兩根 pin 對地：有一根 0Ω → 接地參考的邏輯開關，不要盲接。
3. 量 DC 座中心腳對 `J2` 的通斷 → 確認是不是串在電源上。

**而且就算量出來是第一種，還是不該剪。** 接下來抓 bootlog 要反覆斷電重開幾十次
（要抓開機瞬間、要試中斷 bootloader），**一個能用手撥的開關是資產，不是障礙** ——
把它換成兩條要用手扭在一起的裸線，是把乾淨的動作換成會抖、會斷續、會短到旁邊的
動作。

</details>

### 9.10 🔵 絲印已經寫 `UART` 了，你為什麼還要用電表量腳位?

<details><summary>答案</summary>

**因為 `UART` 只命名了這一組排針，沒有告訴我組裡四支的順序。**

而且**接錯的代價不對稱**：

- TX / RX 接反 → 沒訊號，重接就好
- **VCC 接到轉接板的輸出 → 可能燒 SoC**

量法：

| 找什麼 | 怎麼量 |
|---|---|
| **GND** | 通斷檔，一探針壓屏蔽罩 / RJ45 金屬框，逐 pin 掃，嗶的那個 |
| **VCC** | 通電後恆定 3.3V 的那根。**永遠不接它** —— 而且這一步同時確認了整條是 3.3V 不是 1.8V |
| **TX** | 開機瞬間電壓會抖、會往下掉的那根（它在送資料） |
| **RX** | 剩下那根 |

**第二來源：邏輯分析儀。** 掛 UART decoder，參數對了會出現**可讀的英文字**，
錯了是亂碼 —— 沒有中間地帶。而且它同時把 baud 量出來（`baud = 1 / 最窄脈衝寬度`），
不用一個一個試。

</details>

### 9.11 🔴 你要把 PCB 照片放上 GitHub。有什麼東西不能放?

<details><summary>答案</summary>

**這塊板子上有兩張會指認出「我這一台」的標籤，而其中一張就在 G2 要交的那張照片上。**

| 位置 | 是什麼 |
|---|---|
| PCB 背面條碼 | 12 個十六進位字元 —— **幾乎確定是這台的 MAC 位址** |
| PCB 正面 QR + 數字標籤 | 機身序號 |

而且同一條規則接下來還會用兩次：

- **bootlog** 會印 MAC，而且照 W04 找到的 `flash set HW_WLAN0_WSC_PIN %s`，
  很可能連 **WPS PIN** 一起印；
- **flash dump 的 config 分割區**裡全部都有 —— 這正是 `.gitignore` 一開始就把
  `dumps/*` 擋在外面的原因之一。

**一條規則，三個地方：**

> 從「我這一台」讀出來的東西一律遮掉，只發表對「**這個型號**」成立的事實。

**而且要在 `git add` 之前決定。** 推上去之後才遮的不叫遮 —— git 有歷史，
改一次 commit 蓋不掉已經 clone 出去的東西。

遮的方式用**塗掉**，不要用模糊（模糊有時候可以反推）、也不要只靠裁切
（原圖如果哪天不小心也上去了，裁切等於沒做）。

</details>

### 9.12 🔴 你為遮蔽工具寫了五個「一定要失敗」的測試，五個都通過了。為什麼那還是壞的?

<details><summary>答案</summary>

**因為它們全部通過的理由是錯的：每一次呼叫都在 `import PIL` 就死了。**

我的檢查只看**離開碼非零**。而當時 `python3` 解析到 `/usr/bin/python3`，那支沒有
Pillow，所以工具一啟動就退出 —— 五個「這個一定要失敗」的測試，全部因為同一個
無關的錯誤而「成功」。

> 我前一次還親手驗過 `python3 -c "import PIL"` 印出 12.3.0。差別是那次用了
> `bash -lc`(login shell),PATH 上有 `~/.venvs/thermal/bin/python3` ——
> **另一個專案的 venv**，剛好裝了 Pillow。非 login shell 就沒有。

**抓到它的是「一個合法的呼叫必須成功」那一行對照組。**
沒有那一行，我會拿著一份 5/5 全綠的報告去遮真正的 MAC。

**兩層修法：**

1. 直指專案自己的 venv，不用裸的 `python3` —— 依賴另一個專案的 venv 是假的可重現性。
2. 每個守衛改成**必須因為自己那條錯誤訊息失敗**，而不是「隨便什麼理由失敗都算」。

**通則：**

> 一個永遠不會觸發的檢查，永遠不會失敗（W04 的 `self_check` 連錯三次都寫
> `consistent`）。
> **而一個因為錯誤理由觸發的檢查更糟 —— 它會給你「已經驗過了」的錯覺。**
>
> 所以任何一組「這些一定要失敗」的測試，旁邊都必須有一個**「這個一定要成功」**。
> 沒有那個對照組，整組測試可以在整個系統壞掉的情況下全綠。

</details>

### 9.13 ⚪ 這一天你最不確定的是什麼?

<details><summary>答案</summary>

按不確定程度排：

1. **那顆 flash 是不是重標的。** 整份 `hardware-inspection.md` 所有結論都建立在
   「油墨上的字是真的」這個假設上，而**到今天為止，五顆 IC 一個獨立來源都還沒有**。
   這是本日最大的單一風險，而且它一次夾具就能結案。
2. **`LSP5526` 是什麼。** 完全沒查到。現在寫的是「從位置推測是降壓穩壓 IC」，
   我沒有把握，也沒打算假裝有。一次電表就能結案。
3. **RTL8196E 的核心到底是不是 RLX5281。** 我是照一般記載說的，沒有第一手來源。
   `/proc/cpuinfo` 一行就結案 —— 而 9.5 那整個假說掛在這件事上。
4. **日期碼的解讀。** `1837H` = 2018 w37 我有把握；`181525` 和 PCB 的 `18.15`
   是推的。但五顆料全部落在 2017–2018，**單一顆讀錯不改變結論** —— 這是刻意
   多抄幾顆的原因。
5. **`J2` 到底是不是串在電源上。** 從 layout 推的，沒量。

**前五項全部都在 Day 2–4 用不超過十分鐘的量測就能結案。**
今天沒做，是因為今天的規則是「不通電」，不是因為做不到。

</details>

---

## 10. W02:Console 與 flash(Day 2–3)

> 機器第一次通電的那一天。

### 10.1 🔴 你說這台跑 2018 的 build。那不過是 BusyBox 的一個時間戳，憑什麼?

<details><summary>答案</summary>

**憑我先去排除了那個時間戳可能沒有意義。**

反證是：「搞不好廠商不重編 BusyBox,V3.4.0 裡那顆也是舊的，那時間戳就什麼都證明不了。」
如果這成立，我的推論整個垮。

去查兩份官方映像：

| | BusyBox 建置 | 映像日期 | 落差 |
|---|---|---|---|
| V2.1.2 | 2015-08-11 | 2015-08-25 | 14 天 |
| V3.4.0 | 2020-10-30 09:55 | 2020-10-30 | **同一天** |

**這家廠商發版時整包重編，所以時間戳確實追蹤建置日期。反證死了。**

而且不只 BusyBox 一個來源 —— **同一次開機印出四個時間戳**：BusyBox `14:56:45`、
`wscd` `06:58`、MiniIGD `06:58`、**`boa` `Jan 10 2018 14:57:54`**。四個binary、
同一天、時間連貫。那是一次完整的建置，不是某個檔案沒更新。

**這題真正在考的是：你有沒有先想「什麼證據會讓我錯」再去找它。**

</details>

### 10.2 🔴 那 W03、W04 那一堆關於 `boa` 的結論，是不是白做了?

<details><summary>答案</summary>

**不是白做，但它們不涵蓋這台機器 —— 而這件事必須主動講，不能等人問。**

W03/W04 讀的是 V2.1.2 和 V3.4.0 的 `/bin/boa`。這台跑的是 2018-01-10 建的第三份。

- `strstr(uri, "htm")` 授權洞 → 關於 V2.1.2
- 59 個 handler 的 `root_form[]` → 關於 V2.1.2
- `lastUrl[100]`、34 個 handler 的 `submit-url` → 關於那兩份
- 2020 版三個未錨定的 `strstr` → 關於 V3.4.0

**那些結論全部正確，而且 repo 從頭到尾都指名了版本號** —— 這就是為什麼它們不需要
被撤回。如果當初寫的是「這個型號有這個洞」，今天就得全部改寫。

**代價是具體的：W05/W06 在這台實機上做的任何動態驗證，測的是第三個二進位。**
在 dump 出來、把這顆 2018 的 `boa` 丟進 Ghidra 之前，「靜態讀到的洞」和
「這台上跑的程式」中間還缺一段。

**所以 flash dump 從「gate 的一格」升級成「整個專案的關鍵路徑」。**

</details>

### 10.3 🔴 開機訊息明明印 `chip name: 8196C`。你憑什麼說是 8196E?

<details><summary>答案</summary>

**因為那個唱反調的來源，在同一段裡就露了餡。**

三個來源說 E：

1. 封裝絲印
2. bootloader banner:`---RealTek(RTL8196E)...`
3. **bootloader 開頭那段組語**：讀 `0xB8000000` 的晶片 ID 暫存器，拿去跟常數
   `0x8196E000` 比對

```
3c 01 b8 00    lui  at, 0xb800
8d ee 00 00    lw   t6, 0(t7)      ← 讀晶片 ID
3c 01 81 96    lui  at, 0x8196     ← 0x8196E000
34 21 e0 00    ori  at, at, 0xe000
15 cf 00 0a    bne  t6, t7, ...    ← 比對
```

**第 3 個最硬：banner 上那個字串不是編譯進去的常數，是從矽晶片讀出來比對的結果。
那是晶片自己說的。**

而說 C 的那一個，**兩行之前才印**：

```
Probing RTL8186 10/100 NIC-kenel stack size order[3]...
chip name: 8196C, chip revid: 0
```

**RTL8186 比兩個候選都老一個世代。** 那支驅動從頭到尾在印**自己程式碼的血緣**，
不是它跑在哪顆晶片上。它的字串不是關於這顆晶片的證據。

**答案不是「三票對一票」。是「那一票的投票人剛剛才說自己在別的地方」。**

</details>

### 10.4 🟠 baud 你說 38400。怎麼不是 19200?

<details><summary>答案</summary>

**因為我量到 26 µs 的脈衝，而 19200 的位元時間是 52.08 µs —— 那會需要半個位元。**

量到的最窄脈衝 **26 µs**;`1/26µs = 38.46 kHz`;38400 的位元時間 26.042 µs,
誤差 0.16%。

**但真正讓它變成量測而不是猜測的，是自洽檢查：** 同一段擷取裡有一個脈衝正好是
**52 µs = 2 × 26**。

- 如果 26 µs 是**一個**位元 → 52 µs 就是連續兩個相同位元。合理。
- 如果 26 µs 是**兩個**位元（即 baud = 19200）→ 那必須存在 13 µs 的脈衝。
  **而不可能有半個位元。**

**19200 正是最容易掉進去的錯誤答案** —— 它的位元時間就是 52.08 µs。
如果我只挑到那個 52 µs 的脈衝就收工，會設成 19200，然後整晚看亂碼。

第三個確認：decoder 設 38400 解出可讀 ASCII。**可讀 vs 亂碼，沒有中間地帶。**

</details>

### 10.5 🔴 你送 Enter 過去，console 明明有回應。為什麼說沒有 shell?

<details><summary>答案</summary>

**因為回顯來自 tty 層，不是來自任何在讀的程式。**

實測：

```
送  : \r \r \r\n  echo MARKER_1234\r
回  : CR LF ×4,然後 "echo MARKER_1234" CR LF
```

每個字元都回來了，而且 CR 被轉成 CR+LF —— **那是 Linux tty 行規程（N_TTY）的
標準行為，只要 echo 開著就會發生，不管有沒有行程 open 那個 tty。**

但是：

- **指令沒有被執行**（沒有 `MARKER_1234` 這一行）
- **沒有提示符**

而且 bootlog 裡從頭到尾沒有 BusyBox 那句
`Please press Enter to activate this console`。

**「console 有回應」感覺很像成功，但它不是。** 這一題考的是能不能分清楚
「訊號有來回」和「另一端有東西在聽」。

</details>

### 10.6 🔴 你說沒夾 SOIC-8 就讀到 flash 了。那算 dump 嗎?

<details><summary>答案</summary>

**現在還不算 —— 我讀的是幾個 64 bytes 的窗口，不是完整映像。要講清楚這個差別。**

路徑是 bootloader 的兩個指令：

```
FLR <RAM位址> <flash位移> <長度>    ← 把 flash 複製進 RAM
DB  <RAM位址> <長度>                ← 把 RAM 印出來
```

**這是一條真正的讀取路徑，而且比夾具安全**（不用夾、沒有匯流排競爭、沒有 5V 風險）。
計畫書只把它列在 Day 6 的「如果兩個都成功了」附加項。

**要變成完整 dump,4 MiB 走 38400 大約 80 分鐘**，可行但慢。
所以規劃是：CH341A 做主路徑，`FLR` 做**獨立的第二條路徑**，兩份比 hash。
**兩條物理上不同的讀取路徑產出同一份雜湊，那比任何單一 dump 都硬。**

**而這條路徑今天已經自我驗證過一次：** 我在第一次 `FLR` 之前先 `DB` 了同一塊 RAM
當對照組；後來讀 `0x060000` 的 `cr6c` 區，payload 跟那份對照組**逐 byte 相同** ——
那是 bootloader 自己載進去的 kernel 開機碼。**兩條不相干的路徑，同一串位元組。**

</details>

### 10.7 🔴 W01 算出來的三個燒錄位址全中。這會不會只是巧合?

<details><summary>答案</summary>

**64 KB 對齊的 flash 上，三個位址同時猜中的機率不是重點 —— 重點是它們不是猜的。**

W01 沒看過這台機器。它解析兩份廠商 `.web` 容器，從每個區段那 16 bytes 標頭裡讀出
`burnAddr` 欄位，產出一張表。那是**推導**，不是猜測，而且推導的對象是一個**沒有
官方文件的私有格式**。

實機讀出來：`w6cg`@`0x010000`、`cr6c`@`0x060000`、SquashFS@`0x180000`。**三比三。**

**而且它預測的是一個它從來沒看過的 build。** 這台跑 2018 的韌體，W01 手上只有
2015 和 2020。如果那個格式是誤讀，第三份映像不會剛好也符合。

順帶三個結構細節，是靜態推導**沒辦法**告訴你、只有實機能講的：

- `w6cg` 和 `cr6c` 的 **16 bytes 標頭是真的燒進 flash 的**
- **rootfs 沒有標頭** —— SquashFS 的 magic 直接在 `0x180000` 上。合理：它要當 MTD
  分割區掛載，前面多 16 bytes 會掛不起來
- `cr6c` 的 `startAddr` 欄位讀出來是 `0x80500000`，**正好是 bootlog 印的
  `Jump to image start=0x80500000`**

</details>

### 10.8 🟠 你電表一開始怎麼量都不對，卡了很久。學到什麼?

<details><summary>答案</summary>

**學到「先用已知量驗證儀器」不是格言，是省時間的操作。**

當時停在 **200mV** 檔量 3.3V，差 16 倍。而它**沒有顯示超量程** —— 它給我一個
會漂的 `0.x`，那個形狀跟一個真實的、有雜訊的低電壓讀數一模一樣。

於是我懷疑板子沒電、懷疑探針、懷疑接線。**全部猜錯，因為我在懷疑未知的那一側，
而問題在已知的那一側。**

**解法只有一步：拿一顆 AA 電池，20V 檔，讀到 1.6V。**

- 讀到了 → 表和檔位都好 → 問題一定在板子
- 讀不到 → 先修表，板子的事全部往後排

**這一步不用碰板子、不用拆線、三十秒。** 而它把「表的問題」和「板的問題」永遠切開。

跟同一週前面兩件事是同一條紀律：`flashrom` 的資料庫不是第二來源（它跟絲印共用
上游）；遮蔽工具的守衛測試 5/5 全過是因為每次呼叫都在 `import PIL` 就死了。
**在你確認工具沒說謊之前，它報的一切都不是資料。**

</details>

### 10.9 🔵 `COMPCS` 在哪?為什麼重要?

<details><summary>答案</summary>

**flash offset `0x00C000`，長度 `0x1D36` = 7,478 bytes。**

Realtek SDK 的設定區在 **`0x010000` 以下**，不是在 flash 尾端：

| 位移 | Magic | 內容 |
|---|---|---|
| `0x006000` | `H601` | 硬體設定 —— MAC、無線校正 |
| `0x008000` | `COMPDS` | **D**efault **S**etting，出廠預設 |
| **`0x00C000`** | **`COMPCS`** | **C**urrent **S**etting ← **這就是 `config.dat`** |

**為什麼重要：W04 有一條「Deliberately not done」寫著**

> 解 COMPCS 壓縮、解析真實的 `config.dat` —— 需要一份真的 `config.dat`，
> 而那要等 W02 的 flash dump。

它就在 `0x00C000`。而 W04 已經把 MIB 表整張解出來了（`0xb6` = `USER_NAME`、
`0xb7` = `USER_PASSWORD`），缺的就是這個 blob。

**而且拿到的是一對，不是一份：** `COMPDS`（出廠）和 `COMPCS`（現行）是同一張表的
兩個版本，長度只差 3 bytes，前 58 個 payload byte 只差**一個 byte**。

**兩份幾乎相同、而且你知道其中一份是「出廠狀態」的壓縮 blob，是攻擊未文件化格式
最好的起手式** —— 遠比對著單一份硬解好。

（順帶：這也說明這台的設定跟出廠預設幾乎沒差別 —— 被重設過，或從沒被真正設定過。）

</details>

### 10.10 🔴 PCB 上那個條碼，你昨天說「幾乎確定是 MAC」，今天說確定。中間差在哪?

<details><summary>答案</summary>

**昨天是從「東西的形狀」推的，今天是從一個無關的來源量到的。**

昨天的依據：12 個十六進位字元、貼在網路裝置的 PCB 上、條碼標籤。**形狀對，但那是
推論。** 筆記當時就是這樣寫的，而且明確寫了「查 OUI 這件事沒有做」。

今天：`0x006000` 的 `H601` 硬體設定區開頭是一串 MAC 位址，**第一個就是那 12 個
字元，逐 byte 相同。** 那個來源跟印標籤那台機器完全沒有關係。

**但真正該注意的是順序：遮蔽是在它還只是推論的時候就做掉的。**

如果當時的做法是「等我確認它真的是 MAC 再決定要不要遮」，那張照片可能已經 push
出去了 —— 而 git 有歷史，推上去之後才遮的不叫遮。

**對這種東西，要照「它看起來是什麼」處理，不是照「它被證明是什麼」處理。**

</details>

### 10.11 ⚪ 這一天你最不確定的是什麼?

<details><summary>答案</summary>

按不確定程度排：

1. **`chipName: UNKNOWN` 到底指什麼。** 我寫「最可能是 SPI flash，因為 2014 年的
   boot ROM 的 flash ID 表裡沒有 EN25QH32B」，而且順著推測那可能就是公開規格寫
   2MB 的原因 —— **但我沒有追出 `chipName` 的來源，那整條是推測。**
2. **flash 容量還是沒有乾淨的第二來源。** JEDEC ID 是 Day 4 唯一沒做到的量測。
   `0x350000` 讀到 `FF` 算旁證（2MB 的部件如果位址繞回，那裡會落在 kernel 區裡、
   不會是 FF），**但「繞回」是我假設的行為，有些部件超範圍就回 FF。**
3. **pin3 = RX 是推論，不是量測。** 其他三支都確定了、是 4-pin 的 `UART` 排針、
   沒有別的可能 —— 但我從來沒驅動過它。
4. **PulseView 打不開分析儀的真正原因。** 我推測是韌體上傳後換 VID/PID、新 ID 沒
   驅動，但我**改用別的軟體就繞過去了，沒有證實**。RUNBOOK §10.20 如實標了。
5. **SoC 核心是 RLX4181 還是 RLX5281。** `/proc/cpuinfo` 一行就結案，而 console
   上沒有 shell 可以跑。W02 的 `LWL`/`LWR` 假說整個掛在這件事上。

**第 1、2、5 項都在 flash dump 之後會有答案。第 3、4 項要另外設計實驗。**

</details>

---

## 11. W02：自動化 flash dump 與工具信任（Day 4）

> 這一天沒有讀到新的韌體知識，全部是**怎麼證明你讀到的東西是真的**。
> 別人問到硬體時，幾乎都會停在這一段。

### 11.1 🔴 你有燒錄器卻不用，是不是其實不會焊?

<details><summary>答案</summary>

**我焊了，而且失敗了，這件事寫在 `LOG.md` 沒有藏。** 但決定不用它跟焊得好不好無關。

先講量測。CH341A 夾具上量到：

| pin | 訊號 | 電壓 |
|---|---|---|
| 8 | VCC | 3.3 V |
| 3 / 7 | WP# / HOLD# | 3.3 V |
| **1 / 6 / 5** | **CS# / CLK / DI** | **5 V** |
| **2** | **DO** | **5 V** |

**判讀不是「有沒有 5V」，是分佈。** 被板子拉到 VCC 軌的那兩支跟著 3.3 V 走，
**被 CH341A 晶片驅動的三支全是 5 V** —— 所以那顆 IC 自己吃 5 V，它每一支輸出
都是 5 V 擺幅。座上 VCC 是 3.3 V 這件事**正是陷阱**，它讓整塊板看起來是安全的。

最難看的是 pin 2 （DO）：那是 flash 的**輸出**腳，被拉到高於它自己的電源 1.7 V。
「反正只是輸入腳，片子撐得住」這個藉口在這條線上不成立 —— 超過 VCC+0.4 V,
輸入端的 ESD 箝位二極體就導通，電流從 5 V 灌進 3.3 V 軌。那是資料手冊
**Absolute Maximum Ratings** 那張表管的範圍，而那張表的標題是「超過此值可能造成
永久損壞」。

然後是決策：**不可替代的是那 4 MiB，不是那支 3 美金的程式器。**

- bootloader 的 `FLR`+`DB` 已經在**這台機器上**跑通過，不是理論路徑；
- 魔改可能再失敗一次，console 不會；
- 就算程式器修好，in-circuit 讀取還有夾具倒灌供電帶不動整塊板的問題。
  走 console 一次閃掉兩個問題。

**燒錄器沒有從計畫裡消失，它降級了** —— 它現在的用途是 dump 的第二來源，
以及 bootloader 死掉時的最後手段。而唯一會弄死 bootloader 的是我自己對
`0x000000` 下 `FLW`，那件事永遠不會做。

</details>

### 11.2 🔴 你的 dump 怎麼證明是對的?計畫書說讀兩次 hash 一樣就好。

<details><summary>答案</summary>

**「讀兩次 hash 一樣」是弱驗收，我沒有採用它當作充分條件。**

同一條路徑的兩次讀，共用它們所有的失效模式 —— 一隻腳沒咬到、一條線被 SoC 拉著、
程式器用 5 V 打它。**每一種都會產生穩定、可重現、格式完全正確的錯答案。**
可重現（repeatable）和正確（correct）是兩件事，而 hash 相同只回答了前者。

我拆成四層，而且沒有一層是「工具說它成功了」：

| 層 | 它能抓到什麼 | 它抓不到什麼 |
|---|---|---|
| **陽性對照** —— 先讀 flash `0x000000`，前四 byte 必須是 `0b f0 00 04`（8/15 另一場 session 記下的已知答案） | 讀到 RAM 舊資料、讀錯位址、`FLR` 沒生效 | 之後才發生的傳輸錯誤 |
| **逐塊解析驗證** —— 位址連續、每行剛好 16 byte、總長相符 | 掉行、掉字元、重試輸出被串接 | **格式正確但內容錯的位元翻轉** |
| **抽驗重讀** —— 隨機 5% 的塊再讀一次比對 | 上一格抓不到的那種 | 系統性的、每次都一樣的錯誤 |
| **結構驗證**（`fwrecon flashdump`）—— 對照 8/15 每一個 offset、W01 從容器推導的燒錄位址、SquashFS superblock | 整體位移、讀到別的 build、讀到別顆片子 | — |

**最強的一項不在表裡：`0x180000` 的 SquashFS 必須解得開。** 1.8 MiB 的 LZMA
是任何序列線都不可能矇混過去的完整性檢查。

**還有一項我沒有，而且我會主動講：真正獨立的第二個儀器。** 8/15 那些窗口走的
也是 `FLR`+`DB`，所以拿它們對帳是**跨場次的可重現性，不是跨儀器的佐證**。
那要等改好的 CH341A。這一格現在是空的，而我寧可它空著也不要假裝它滿了。

</details>

### 11.3 🔴 `FLR` 之後你 `DB` 出來的東西，憑什麼不是 RAM 裡本來就有的?

<details><summary>答案</summary>

**這正是 8/15 差點騙到我的那一格，而它當時是靠對照組擋下來的。**

`FLR` 把 flash 搬進 RAM,`DB` 印 RAM。如果 `FLR` 其實沒生效（例如那句
`(Y)es , (N)o ?` 被吃掉、回了 `Abort!`），`DB` 照樣會印出一份格式完美的
hex dump —— 印的是 RAM 裡上一輪的殘留。**失敗模式不是錯誤訊息，是一份看起來
很正常的資料。**

8/15 的做法：`FLR` 之前先 `DB` 同一塊 RAM 存起來當對照。結果那次特別有意思 ——
對照組跟後來讀到的 `cr6c` payload **逐 byte 相同**，因為那塊 RAM 正是 bootloader
已經載入的 kernel 開機碼。兩條互不相干的路徑得到同一份 bytes，反而是最強的佐證。

**但「內容必須不同」不能當成通則檢查**，上面那個例子就會誤報。所以自動化版本
改用**已知答案的陽性對照**：讀 flash `0x000000`，前四個 byte 必須是
`0b f0 00 04`。這比「有沒有變」強，因為它比對的是一個**外部來源給定的值**，
而不是一個相對關係。

</details>

### 11.4 🟡 你的解析器把裝置吐的每一行都判成不合法，而你的測試套件 10/10 全綠。那套測試有什麼用?

<details><summary>答案</summary>

**當時沒有用，而這是這個專案第七個工具 bug，也是最值得講的一個。**

`DB` 的實際輸出後面有一個 ASCII 欄：

```
80500000: 00 00 00 00 00 00 80 21 40 90 60 00 00 00 00 00     .......!@.`.....
```

我的正則沒有它，所以每一行都不匹配，第一次跑就死在自己的陽性對照上，
訊息是「no data lines at all」。

**根因不是正則寫錯，是我從哪裡抄格式。** 我照 `notes/flash-layout.md` 裡引用的
transcript 寫 —— 而那份引用為了排版把 ASCII 欄修掉了。**筆記是給人看的摘要，
不是規格。**

更難看的是：**守衛套件的合成 transcript 也是照同一份引用寫的。** 所以測試和
被測程式共用同一個錯誤假設，10/10 全綠，驗的是一個裝置根本不會產生的格式。
**測試跟被測程式共用假設時，它不是第二來源，它是同一個來源用兩次。**

而最讓人不舒服的部分是：**逐字的原始格式一直在這個 repo 裡。**
`RUNBOOK.md` §8.7.8 有完整 transcript,ASCII 欄好好地在那裡，console 上線那天
就寫下來了。**沒有東西遺失，是我讀錯了文件** —— `notes/` 是分析，引用會被編輯；
RUNBOOK 是操作記錄，transcript 是逐字的。

修法有三層，而不只是補正則：
1. 正則改成能容忍 ASCII 欄，**而且用「至少兩個空白」當邊界**（bytes 之間只有一個空白）；
2. 保留每行 16 byte 的長度檢查當第二層 —— 萬一正則哪天吞掉 ASCII 欄的一部分，byte 數會不對；
3. 守衛套件的 fixture **改成從真機抓下來的格式**，並加一個對抗案例：
   ASCII 欄的內容故意長得像更多 hex（`ab cd ef 01 23 4`）。

</details>

### 11.5 🟡 抓到 bootloader 之後第一條指令失敗，你怎麼確定不是板子的問題?

<details><summary>答案</summary>

**因為 8/15 那場 session 用同一條指令拿到過完整命令表，而命令表不會自己改。**

徵狀：catch 成功、`<RealTek>` 在手上，然後 `?` 回 `Unknown command !`。
如果只看這一次，合理的結論是「`?` 不是 help」—— 而那是錯的，`?` 就是 help,
§8.7.7 記過。

**兩場 session 對同一台裝置給出相反結果 = 儀器在說話，不是裝置。**

原因是我自己的工具：搶 bootloader 要**連續串流** ESC（中斷窗口只有約一秒），
bootloader 只吃掉一個用來中斷開機，**其餘全部排在它的輸入緩衝區裡**。所以第一條
真正的指令是帶著一串 ESC 前綴送達的。

對策是送一個裸 `\r` 讀到 prompt 再送真的指令（`settle()`）。

**這比看起來嚴重：自動 dump 的第一條指令就是陽性對照。** 一個安靜地沒有執行的
對照，比沒有對照更糟 —— 沒有對照你知道自己沒驗，有一個假的對照你以為驗過了。

</details>

### 11.6 🟡 95 分鐘讀 4 MiB，太慢了。你不能調快嗎?

<details><summary>答案</summary>

**不能，而且我算得出為什麼，這不是「我試過但沒用」。**

`DB` 每 16 個 data byte 要送出 81 個字元：

```
位址 8 + ": " 2 + hex 48 + 空白 5 + ASCII 16 + CRLF 2 = 81
81 / 16 = 5.06 倍膨脹
```

38400 8N1 = 3840 bytes/s ÷ 5.06 = **759 B/s 理論上限**。實測 **723 B/s**,
是理論值的 95%。**線已經吃滿了，瓶頸是物理層，主機端怎麼調都沒用。**

能動的只有三個地方，我都評估過：

| | 效果 | 為什麼沒做 |
|---|---|---|
| 改用 `DW`（印 4-byte word） | 省約 19% 字元 → 約 78 分鐘 | 要另一套解析器和另一組守衛案例。**正確性優先於 19%** |
| 提高 baud | 最大 | **bootloader 固定 38400**，命令集裡沒有改 baud 的指令 |
| 改用 CH341A | 4 MiB 約 2 分鐘 | 見 11.1 |

**而 95 分鐘的機器時間不是我的時間** —— 那段時間我在寫結構驗證器和補文件。
會痛的是「重跑一次」，所以真正該投資的是**掉字元自動重讀**和**拼不完整就不吐檔案**，
不是快 19%。

</details>

### 11.7 ⚪ 這一天你最不確定的是什麼?

<details><summary>答案</summary>

1. **CH341A 魔改為什麼失敗，我沒有隔離。** 三個候選：走線沒真的斷、腳抬起來但
   還碰著焊盤、或者理論不完整（`DO` 那支很可能是獨立上拉到 VBUS，跟晶片供電無關）。
   **一次量測就能分辨 —— 量 CH341A 的 pin 28 本身 —— 而我那天沒量。**
   所以 `LOG.md` 寫的是「原因未隔離」，不是「焊接失敗」。
2. **那塊板現在是「已改、未驗證」狀態。** 下次拿起來之前必須重量，不能假設它是
   5 V 也不能假設是 3.3 V。而且改壞的方向裡有一個比原狀更糟：**如果兩條軌被橋
   起來，座上的 VCC 也會變 5 V**，外觀完全看不出來。
3. **真正獨立的第二個讀取儀器還是沒有。** 見 11.2 最後一段。
4. **CH341A 旁邊那顆三針跳線我還沒量。** 它可能是座上 VCC 選擇、可能是晶片供電
   選擇、也可能是 EPP/UART 模式選擇 —— 如果是第二種，我根本不用焊。
   實驗零風險（座上空的），只是優先序排在後面。

</details>

### 11.8 🔴 你說這台的 build 「抓到廠商修到一半」。你怎麼知道那不只是兩個不相干的版本差異?

<details><summary>答案</summary>

**因為那不是一個差異，是四個互相咬合的差異，而且它們指向同一個時間順序。**

| | 2015 | 2018(這台) | 2020 |
|---|---|---|---|
| `/bin/skt` binary | 在，可執行 | **刪了** | 不在 |
| `rcS` 的 `#skt&` | 註解掉 | **註解還在** | 移除 |
| `onlime_r` uid 0 | 在 | **還在** | 移除 |
| passwd 模板 | `passwd.org` | **byte-identical**,`sha256 e769c562…` | 改名 `passwd_orig` |

**關鍵那一格是第二列。** 如果 2018 只是「另一條產品線」或「隨機的版本差異」，
那行死掉的 `#skt&` 沒有理由**剛好**留在一個 binary 已經被刪掉的系統裡。
它是化石：**它證明 2018 是從 2015 那份程式碼演進來的，而且刪 binary 的人沒有回頭
清啟動腳本。**

第四列把它釘死：`passwd.org` 跟 2015 **逐 byte 相同**。不是「內容相似」，是同一個
檔案。**一個會刪掉後門 binary 的版本，對後門帳號檔連一個 byte 都沒動過。**

反過來說，如果我只有兩版（2015 和 2020），我看到的會是「後門在某個時間點被移除了」，
**中間那個「刪了一半」的狀態根本不存在於任何公開映像裡。**

而 CVE-2015-9550（帳號）和 9551（RCE）是**同一次揭露**。所以這條時間線在講的是：
**兩年半之後，廠商修好了那次揭露的其中一半。**

</details>

### 11.9 🟡 你的 dump 是從 bootloader 讀的。萬一 bootloader 的 `FLR` 本身就是錯的呢?

<details><summary>答案</summary>

**那我目前所有的驗證都看不到，而我把這一格明確留白。**

這是我在 `dump-vs-official.md`、`PROGRESS.md` 和 `dumps/MANIFEST.json` 三個地方
都寫了同一句話的原因：

> 8/15 的窗口走的也是 `FLR`+`DB`，所以跟它們一致是**跨場次的可重現性**，
> 不是跨儀器的佐證。

兩趟完整讀取也一樣 —— 我刻意讓第二趟用不同的 RAM 暫存位址（`0x81800000` vs
`0x81000000`），那能抓到「某塊 RAM 壞了」，**但抓不到「`FLR` 系統性地讀錯」**。

**有一件事不受影響，而且它很硬：`0x180000` 的 SquashFS 解得開。**
如果 `FLR` 系統性地偏移、跳過、或重複資料，1.8 MiB 的 LZMA 就解不出 161 個檔案。
這是一個**不經過任何我寫的程式碼**的完整性檢查。

同理，W01 三週前從廠商容器推導出來的三個燒錄位址，在這份映像裡全部命中 ——
那是一個**完全獨立於讀取路徑**的預測。

**但這些都不能取代「換一個儀器再讀一次」。** 那要等改好的 CH341A，而我不會因為
現在的證據看起來夠多就把那一格填掉。

</details>

---

## 12. W04-2：把結論搬到這台真的在跑的 binary 上

> 這一章有四題是**專案作者自己在當天問出來的**，不是我事後補的。標 👤 的那幾題。
> 一個被自己人問倒的地方，通常也是外人會踩的地方。

### 12.1 🔴 你上週說 `formSysCmd` 的缺席「讀起來像廠商的修補」，還把它寫進 G3 的驗收欄。現在你說它在。你上週在幹嘛?

<details><summary>答案</summary>

**我在用一個合理的推理，對兩個我碰巧拿得到的樣本。推理沒毛病，樣本有。**

W04 的論證是：Pierre Kim 揭露在 2015-07,V2.1.2 出在 2015-08-25，晚於他報告的最後
一個有問題的 build，所以這讀起來像廠商修掉了。

今天的量測：

| | 2015 | **2018** | 2020 |
|---|---|---|---|
| `grep -aoc formSysCmd`(raw binary，不經 Ghidra) | **0** | **1** | **0** |
| 在 `root_form[]` 裡（`BoaFormTable`） | 否 | **entry `0x004838a8` → `0x0044ee2c`** | 否 |

**缺席 → 出現 → 缺席。一個修補不會在兩年半之後自己長回來。**
剩下的解釋就是 W04 明確寫下並排除掉的那一個：**這是一個 build-time 選項**。

而這件事反過來咬公告：CVE-2019-19824 寫 "N150RT through 3.4.0" 受影響。
**下載得到的兩個映像，剛好都是沒有它的那兩個。** 任何人拿公開韌體驗這個 CVE,
都會得到「不受影響」——對這台機器是錯的。

**該學到的不是「我上週錯了」，是「兩個樣本的趨勢線不是趨勢線」。**
這個 repo 有一條「橫著讀，不要直著讀」的規矩，今天證明**兩個點還不夠橫**。

</details>

### 12.2 🔴 你說它「未認證可達」，但 CVE 公告寫的是 authenticated。你憑什麼比公告更嚴重?

<details><summary>答案</summary>

**憑我讀的是這台跑的那個 binary，而公告描述的是一整條產品線。**

閘門在 `process_header_end` @ `0x0040bb1c`，判斷只有兩個 `strstr`：

```
0040be90  jalr t9 -> strstr        ; strstr(uri, ".htm")
0040be9c  bne v0,zero,0x0040bec0   ; 中了 -> 進豁免清單
0040beac  jalr t9 -> strstr        ; strstr(uri, ".asp")
0040beb8  beq v0,zero,0x0040c0a0   ; 兩個都沒中 -> 跳過 send_r_unauthorized
...
0040c088  jalr t9 -> send_r_unauthorized
0040c0a0  jalr t9 -> translate_uri ; 正常流程從這裡繼續
```

`/boafrm/formSysCmd` 兩個子字串都不含。`handleForm` 自己不做任何授權。

**兩個要說清楚的限定：**

1. **`s1` 真的是 URI 嗎?** 是。`0040bb68` 設 `s1 = req + 0x8d4`，而 `handleForm`
   讀的是同一個 `param_1 + 0x8d4`。同一個欄位。
2. **反編譯器在這個函式上出了三個警告**，所以按 repo 的規矩它失去最後發言權，
   上面每個分支都是 `BoaListing` 的指令輸出，反編譯的 C 只在兩者一致處引用。

**最誠實的一句在最後：什麼都還沒送出去。** 這是靜態閱讀，正確講法是
「程式碼讀起來是這樣」。一個 POST 加看一眼 `/tmp/syscmd.log` 就定案，那是 G4。

</details>

### 12.3 🔴 👤 之前 dump 出來的 raw 被刪掉了嗎?我找不到。到底進不進 repo?

<details><summary>答案</summary>

**沒刪。在 `/home/key/fwre-work/dumps/`，兩份都還是 `sha256 a800059a…`。**
從 Windows 走 `\\wsl$\Ubuntu-24.04\home\key\fwre-work\dumps\`。

找不到是因為它**故意不在 `C:` 底下，也故意不在 repo 裡**。理由在
`docs/workspace-layout.md`：這個專案的發現有一部分是檔案系統 metadata
（symlink、權限、device node），放到 `/mnt/c` 會失真。

**進不進 repo：不進——而且今天的政策改變沒有推翻它。**

`dumps/README.md` 當初寫的是「**兩個獨立理由，任一個都足夠**」：

| | 理由 | 今天 |
|---|---|---|
| 1 | 這是廠商韌體，本專案不轉散布 | **還在** |
| 2 | 裡面有這台的 per-unit 機密 | 被「逐欄全開」政策殺掉 |

理由 2 消失，理由 1 沒有 → **dump 一個字都不用改，而且不必重新論證一遍。**

**這題真正的答案是那個寫法。** 當初把兩個理由分開、並標明「任一個都足夠」，
就是為了今天這種時刻——一個理由失效時，答案已經在頁面上了。

有變的是**兩份 UART log 進了 repo**，因為 `MANIFEST.json` 一直記著它們
`contains_unit_identifiers: false`——但我是**重新讀過全文才 add 的**，因為那個
欄位是上一次的結論。順帶學到：`uart-boot.log` 有三個不可列印字元，所以純 `grep`
會說 `binary file matches` **而不告訴你比中什麼**，那個輸出讀起來跟「找到東西了」
一模一樣，實際上相反。要加 `-a`。

</details>

### 12.4 🔴 👤 你說 Softpedia 403、說 `/etc/version` 是意外收穫。你到底下載了什麼?什麼時候搜的?

<details><summary>答案</summary>

**一個檔案都沒下載。** `$FWRE_WORK/firmware/` 還是 2026-08-07 抓的那兩個 `.web`，
repo 的 `firmware/` 零變更。

**Softpedia 403 測了五次**（PowerShell HEAD、`curl` 一般 UA、`curl` Mozilla UA、
`WebFetch` 產品頁、`curl` 完整 Chrome UA 打產品頁），全部 403。
**但這不是新發現**——`firmware/SOURCES.json` 的 `wanted` 欄從 W01 就寫著
Softpedia 擋腳本抓取。我只是確認它還成立。

**`/etc/version` 是 2018 rootfs 裡一個 41-byte 的檔**，在找 `telnetd` 被哪個腳本
啟動時 `ls -la .../etc/` 看到的：`TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002`。

**而這題最重要的部分，是我第一次寫太滿、被問了才改的地方：**

我原本在 `PROGRESS.md` 寫「V2.1.6 is listed on Softpedia」。
**我沒有讀到那個頁面——我讀到的是搜尋引擎索引裡的標題和 URL，頁面本身 403。**
兩者證據強度不同。同理，搜尋摘要說 2.1.6 發布於 2017-05-08，那跟版本字串裡的
`B20171121` 差半年，**我讀不到頁面，所以不引用**。

現在兩份文件都改成「搜尋索引裡有；頁面讀不到；一次瀏覽器下載就能定案」。

**搜尋摘要不是來源。** 這跟「`readelf` 和 `nm -D` 在 `sstrip` 過的 ELF 上不獨立」
是同一條規矩的不同面。

</details>

### 12.5 🔴 你新寫的 CI 閘門，第一次跑在一個你已知有問題的 build 上抓到 0。那你怎麼還敢用它?

<details><summary>答案</summary>

**因為抓到 0 的是那個正對照，而它就是為了這一刻存在的。**

`control:30` 的意思是：**這個閘門在 V2.1.2 上必須至少觸發 30 次，否則判定閘門
自己壞掉，不是那個 build 乾淨。** 第一次跑 0，修完再跑還是 0，兩個不同的 bug：

1. **用名字比對 sink。** 這些 binary 呼叫 libc 走 `sstrip` 過的 PLT,Ghidra 把
   stub 叫成 `FUN_xxxxxxxx`，`strcpy` 一個都沒對上。
   **這是這個專案第三次踩同一個坑**（W03 `BoaSinks`、W04 `BoaArgTrace`、今天）。
2. **字面值解析只檢查 `isConstant()`。** MIPS 的字串位址是 lui/addiu 湊的，
   在 pcode 裡是 `PTRSUB`/`INT_ADD` 而不是常數，所以**一個參數名字都沒讀到**。

**兩個都會以「這個 build 很乾淨」的形式出貨，而且看起來完全正常。**
前兩次這個 bug 都是出貨之後靠橫向比對抓到的；這次在任何數字離開腳本之前就擋下了。

修法是把 `constAddr` 從 `BoaArgTrace` **共用**出來，不是再實作一次——那正是 W04
對 PLT 得到的結論（「重複的解析邏輯本身就是那個 bug」），只是從另一端走回來。

**所以：我敢用它，正是因為它失敗過，而且是在我設計好的地方失敗的。**

</details>

### 12.6 🟠 你解出設定區、拿到明文密碼。怎麼知道解碼器沒解錯，只是解出一堆看起來很像的東西?

<details><summary>答案</summary>

**四個檢查，只有一個是我自己的意見。**

| 檢查 | 結果 |
|---|---|
| `libapmib` 自己的 8-bit payload 檢查碼要等於 0 | ✅ 兩塊都過 |
| 解出來的長度 = header 宣告的 `len + 8` | ✅ 45,226 = 45,218 + 8 |
| TLV 筆數 vs **另一個檔案**（`libapmib.so`）還原的 MIB 表筆數 | ✅ **344 對 344** |
| 有幾個 id 不在那張表裡 | ✅ **0** |

**最硬的是檢查碼，而且它不是我設計的。** 它在 `_apmib_dsconf` @ `0x0001781c`,
資料本身完全看不出來——45,218 個 byte 錯一個就過不了。
**我寫解碼器時不知道它存在，所以它不可能被我調成會過。**

第二硬的是跨檔案那條：flash 裡的 blob 解出 344 筆，而 `libapmib.so` 這個
**完全不同的檔案**還原出 344 筆記錄，兩個工具不共用程式碼。它甚至重現了一個
已知缺陷——`0x182` 同時綁 `CUSTOM_PASSTHRU_ENABLED` 和 `MLD_PROXY_DISABLED`，
所以是 **343 個相異 id、344 筆記錄**。W04 在 2015 版找到過，2020 版沒有。
**2018 版也有。**

還有一個免費的：用 `0x20` 和 `0x00` 兩種 ring 填充值各解一次，結果必須逐 byte
相同——不同就代表有 back-reference 指向從來沒被寫過的視窗空間。相同。

</details>

### 12.7 🔴 那 `root:123456` 呢?你們不是找到 uid 0 的後門帳號?這台不就開箱即 root?

<details><summary>答案</summary>

**不是，而這是整個專案最誘人誇大的一條，所以我把它講小。**

`TELNET_ENABLED = 0`。兩個不共用程式碼的來源：

1. 從 flash `0x00C000` 解出來的設定值；
2. `/bin/sysconf` 自己的判斷：

```c
FUN_00403400() { apmib_get(0xbbb, local_10); return local_10[0]; }  /* TELNET_ENABLED */
/* setinit:  if (FUN_00403400() == 1) system("telnetd & >/dev/null 2>&1"); */
```

**telnetd 有且只有在那個旗標等於 1 時才啟動。**

所以正確講法是：`root:123456` 和 `onlime_r:12345` **在這台上不是入口，是提權鏈的
第二段**——有人得先把 telnet 打開。講成「開箱即 root」會誇大整整一步。

**而諷刺的是，今天找到的那條 RCE 正好就是「先把 telnet 打開」的那隻手。**
那是一條真實的鏈，但它有兩段，我不會把兩段講成一段。

順帶：`SSH_ENABLED = 1`、`SSH_PORT = 22`、`SSH_PASSWORD = xa.zioncom`——出廠預設，
每一台都一樣。**但這個 rootfs 裡根本沒有 SSH daemon**,`dropbear` 只出現在一個
killall 清單裡。一個沒有東西可以啟動的旗標。

</details>

### 12.8 🟠 你數了 142 個 `lwl`，所以這顆 CPU 支援 unaligned load。這推論成立嗎?

<details><summary>答案</summary>

**不完全成立，而這題的價值就在那個「不完全」。**

證據方向是不對稱的，我把它寫進工具的輸出裡而不是留給讀者：

- **有 = 證據。** 編譯器為這個 target 產生了 unaligned 存取，代表工具鏈相信這顆
  核心支援它們。
- **沒有 = 只是相容。** `-mno-unaligned` 之類的旗標在一顆完全支援的核心上會產生
  一模一樣的 0。V3.4.0 是 0，那是關於它的工具鏈的事實，不是關於任何 CPU 的。

**但「有」也還沒到證明：沒有任何證據顯示那 142 個位置裡有一個真的被執行過。**
同一份韌體裡的 busybox 是 **0**，所以「這份韌體都在用」是假的。一個會 trap 的
指令在冷路徑上可以安靜地活很久。

**定案的實驗今天才變得可行：** W02 遺留 #6 想要 `/proc/cpuinfo`，並記著「沒有
shell 可以跑它」。12.1 那條 RCE 正好給了一個。

**這題真正的產出其實是另一個數字：coprocessor 2/3 編碼，三個 build 都是 0。**
Lexra 加的指令住在標準 MIPS 留給 co-processor 2/3 的 opcode 空間，而 Ghidra 的
標準 MIPS 模組**會**把它們解成看起來很合理的東西——那是從 W03 到現在壓在每一條
靜態結論底下、從來沒被點名過的風險。**沒有。風險是真的，它沒有發生，而
「去驗它」才是重點。**

</details>

### 12.9 ⚪ 這一週你最不確定的是什麼?

<details><summary>答案</summary>

**`system()` 呼叫點 158 → 194 → 129。**

這台跑的 build 比兩個公開映像都多，而且是在**更少的函式**裡（764 vs 813）。
`formSysCmd` 只解釋掉一兩個。**其他大約 34 個我解釋不了**，而我沒有為這個數字
寫過預測——預測表裡只有 `strcpy`。

它可能只是幾個 handler 的實作差異，也可能代表這個 build 有一整組我還沒看的
shell 呼叫。**我把它寫進 carried-forward，而不是編一個解釋。**

第二不確定的是 `BoaGate` 的 R2 只在單一函式內追緩衝區，傳給 helper 就追丟。
所以 5 / 6 / 8 是**下限**。真正的數字只會更高，而我不知道高多少。

</details>

### 12.10 🔴 👤 你花了一整天「發現」`formSysCmd`，結果那東西 2024 年就有 CVE 了，而且指名你這台的 build。你在幹嘛?

<details><summary>答案</summary>

**我在重新發現一個已經公開的東西，而且不知道它已經公開。這是文獻回顧的失敗，
我把它寫進 `prior-art.md` 而不是淡化掉。**

CVE-2024-51228（NVD,2024-11-27）的受影響清單裡有：

```
TOTOLINK-CX-N150RT V2.1.6-B20171121.1002
```

**跟這台 `/etc/version` 逐字元相同。**

### 為什麼會漏

`prior-art.md` 的 CVE 清單是 2015（Pierre Kim）、2019–2020（Adamczyk）、2025 三批 ——
**2024 整年空白**。原因看標題就知道：**那份調查是繞著「我已經知道的揭露事件」組織的，
不是繞著產品。** 一份用事件當錨點的調查，只會找到你一開始就知道的那些事件。

而更難看的一點：**W02 在兩週前就從四個 binary 讀到 `2018-01-10`，W04-2 今天早上
從 `/etc/version` 讀到 `V2.1.6-B20171121.1002` —— 沒有人拿它去搜尋。**
那個 CVE 是專案作者貼連結進來才被找到的，不是這個專案自己找到的。

**一個 build 字串就是一個搜尋詞。這個專案手上握著它兩週沒用。**
所以現在改的不是「補一列到表格裡」，是**重新調查的觸發條件**：
從「新的一週開始」改成「**辨識出一個新的 build 字串**」。

### 那今天做的還剩下什麼?

三件，而且都比原本那句「我發現一個沒人知道的洞」小、但硬得多：

1. **獨立推導。** 我是從 binary 讀出來的 —— 分派表、指令層級的閘門分支、
   `translate_uri` 的 POST 白名單 —— 而不是照著 PoC 打一次。對一個
   **重現型專案**來說，這正是它該產出的東西。
2. **這個 handler 不在任何一個下載得到的映像裡**（`grep` 0 / 1 / 0）。
   這一條跟 2024 那個 CVE 無關，而且它推翻了 W04 自己寫進 G3 驗收欄的一句話。
3. **一個可檢查的評分矛盾 —— 這才是真正的貢獻。**

### 那個矛盾

| 來源 | 說法 |
|---|---|
| NVD 的 CVSS 向量 | `AV:A/AC:L/**PR:H**/UI:N/S:U/C:H/I:H/A:H` = **6.8 MEDIUM**。PR：H = 需要高權限 |
| 原始揭露者 [yckuo-sdc](https://github.com/yckuo-sdc/totolink-boa-api-vulnerabilities) 自己的文字 | 「An attacker may inject arbitrary shell commands **without credentials**」 |
| 這個專案，從 binary 讀 | `/boafrm/*` 在這個 build 上完全不經過授權 |

**三個裡面兩個說不用憑證，而那兩個是「揭露者本人」和「獨立讀韌體」。
說要權限的是評分向量。**

如果他們是對的，向量該是 `PR:N`，基準分從 **6.8 MEDIUM 變 8.8 HIGH**。

**而這種錯這個專案已經抓到過兩次：** CVE-2025-3992 和 CVE-2025-3995 指名的端點
在這個韌體上會回 404，因為那些名字是從 PoC 抄的，不是從 binary 讀的。
**一個 CVSS 向量也是同樣抄出來的。**

> ⚠️ **但這一條在 W05/W06 實機證實之前，值零。** 一個沒跑過的評分修正，
> 只是另一個抄來的向量。

</details>

### 12.11 🟠 👤 那個 V2.1.6 你抓下來了，結論是什麼?

<details><summary>答案</summary>

**它不是這台跑的那個 build，而且那個檔案只下載了 40%。**

| | |
|---|---|
| 下載到的 | `TOTOLINK-N150RT-V2.1.6-**B20160516**.1233.web`（zip 內檔名） |
| 這台跑的 | `TOTOLINK-CX-N150RT-V2.1.6-**B20171121**.1002` |

**同一個產品版本號，兩個相差十八個月的 build。** 所以 W02 那句「這個 build 在
任何下載頁上都不存在」**成立**，只是要講得更精確：**版本號是公開的，這個 build 不是。**

而且注意公開版沒有 `CX`，這台有 —— CVE-2024-51228 的六個受影響版本**全部**是 `-CX-`。
`CX` 看起來是一條獨立產品線，不是裝飾。

### 40% 的檔案還能拿來做什麼

`unzip` 直接拒絕（沒有 central directory）。但 **deflate 是串流，前綴照樣解得開** ——
recovered 1,394,888 / 3,453,871 bytes，而 `fwrecon image` 讀得出兩個完整的 section header：

| section | V2.1.2(2015) | **V2.1.6-B20160516** | 這台（B20171121） |
|---|---|---|---|
| `w6cg` @ `0x010000` | 308,866 | **296,804** | 277,012 |
| `cr6c` @ `0x060000` | 985,090 | **986,114** | 987,138 |

**我第一次的答案是：「kernel 三個版本的長度剛好各差 1,024 bytes，一個被改過的
檔不太可能剛好落在那條線上。」那個答案是錯的，而且錯得很有代表性。**

把第四個 build（2020）拿進來算就散了：

```
2.1.2 (2015-08)    985090 =  962*1024 + 2
2.1.6-B20160516    986114 =  963*1024 + 2
unit-2018          987138 =  964*1024 + 2
3.4.0 (2020-10)   1234946 = 1206*1024 + 2
```

**四個全部 ≡ 2 （mod 1024）。** 這個 section 對齊到 1 KiB 網格，所以「每步差
1,024」是三個連號的網格點，是**容器格式的性質**，不是這幾個檔案的性質。
而 2015 和 2018 之間**只有一個網格點**，任何尺寸落在那區間的正常 kernel 都會
由構造保證落在 986,114 —— 被改過的也會。

`w6cg` 那半沒對齊（餘數 642 / 868 / 532），確實夾在前後版本之間，那是真的，
但只是一個約 32 KiB 窗口的排序測試，是弱佐證。

**現在拿得出來的答案是這個：**

| 來源 | 值 | 為什麼跟檔名不同源 |
|---|---|---|
| ZIP header 的 DOS 時間戳 | `2016-05-16 12:34:30` | 檔名的 `B20160516` 是文字，鏡像站可以打；這是打包程式寫的另一個欄位 |
| **壓縮過的 kernel 內部** | `Linux version 2.6.30.9 … #1338 Thu May 12 21:05` | 改檔名改不到。2016-05-12 是星期四，比打包早四天 |
| 同一條 cmdline | `console=ttyS0,38400` | 對得上 W02 在**這台硬體**上量到的 26µs bit time |

**而且天花板要自己講出來：TOTOLINK 不簽章，所以以上全部只是把偽造成本從
「改檔名」提高到「重編 kernel」，不是來源證明。**

**至於「只是前綴」——那句話我也講得太小了。** 三段裡有**兩段是完整的**：
`w6cg` 296,804/296,804、`cr6c` 986,114/986,114（內層 LZMA 解到 `eof`，
3,374,608 bytes）。截斷的只有 rootfs，所以缺的是 `/etc/version` 和 `boa`。
重抓的判準已經先寫死：**CRC-32 要等於 `0xd20c0622`**，
`tools/zipprefix.py` 對不上就 exit 非 0。

</details>

### 12.12 🔴 👤 你的 `LOG.md` 說這題還開著，`PROGRESS.md` 說已經結案。哪一個是真的?

<details><summary>答案</summary>

**`PROGRESS.md` 是真的，而 `LOG.md` 當時沒有被更新 —— 這是我的流程出的錯，
不是兩份文件對同一件事有不同看法。**

經過：那天有一個 commit 標題就叫 **document sync**，同步了 PROGRESS、README、
RUNBOOK、LOG、QA、weekly-results。**然後它後面又落了兩個 commit 的真工作**，
兩個都沒有回頭同步 `LOG.md` 和 `RUNBOOK.md`。結果是 `PROGRESS.md` 已經把
開放問題 #1 劃掉寫 `answered: no`，`LOG.md` 的結尾還停在「如果兩份映像一致…
如果不一致…」。

**病因不是忘記，是把「document sync」當成一週過一次的關卡，而不是每個 commit
之後都要成立的狀態。** `CLAUDE.md` 那條規則（「RUNBOOK、PROGRESS、README board
跟工作在同一個 commit」）存在的理由就是防這個，而它**在規則本身被重寫進
`CLAUDE.md` 的同一週失效**。

`RUNBOOK.md` 更難看：§8.8 和 §8.9 是那個 commit 加進去的，而 §14 變更紀錄
**一列都沒補** —— 也就是說 §13 自我檢查清單最後一項「§14 變更紀錄補了嗎?」
在讓它變成必要的那個 commit 裡被跳過了。

**這件事我沒有偷偷修掉，是寫進 `PROGRESS.md` 的。** 修掉是一個 commit,
習慣不是。

> 對外講法：「我的文件之間出現過矛盾，而且是我自己在做覆核的時候抓到的。
> 我把它當成流程 bug 記下來，因為那個矛盾如果被讀者先抓到，他接下來會開始
> 懷疑我其他每一個日期。」

</details>

### 12.13 🟠 你說那個第三方鏡像的檔案沒被動過。你怎麼知道?

<details><summary>答案</summary>

**我不知道，而且沒有辦法知道 —— 因為 TOTOLINK 不對韌體簽章。** 這是天花板，
先講這句，再講我做了什麼。

雜湊在這裡幫不上忙：雜湊只證明兩個人抓到同一串 byte，不證明那串 byte 出自原廠。
沒有廠商簽章的時候，「這個檔案是真的嗎」在密碼學上無解。

**所以能做的是提高偽造成本，並且說清楚提高到哪裡：**

1. **檔名說 `B20160516`，而 ZIP local file header 的 DOS 時間戳獨立地說
   `2016-05-16 12:34:30`。** 檔名是文字，時間戳是打包程式寫的欄位 —— 兩個對上，
   偽造者就得多改一個地方。
2. **壓縮過的 kernel 裡面有 `Linux version 2.6.30.9 … Thu May 12 21:05`。**
   這個改檔名碰不到，要動得重編 kernel。而 2016-05-12 是星期四，比打包早四天，
   是真實建置流程會產生的時序，不是刻意對齊的數字。
3. **同一條 cmdline 的 `console=ttyS0,38400`，對得上我在自己這台板子上量到的
   26µs bit time。** 這條跨到硬體，不是檔案內部自證。

**我第一次的論證不是這個，而且是錯的**（見 12.11）：我拿三個 build 的 kernel
長度剛好各差 1,024 當證據，結果那是 1 KiB 對齊的網格，不是巧合。

> 對外講法：「沒有廠商簽章的時候，正確答案不是『應該沒問題』，是『我不知道，
> 但我可以說出偽造需要付什麼代價』。而我第一次給的那個代價估錯了 —— 我把
> 檔案格式的對齊當成了巧合，是拿第四個樣本進來算才看出來的。」

</details>

### 12.14 🔴 你之前說 2015 版**沒有** `formSysCmd`。現在你說 2015 出貨了一個 POST 到 `/boafrm/formSysCmd` 的表單。哪一個是真的?

<details><summary>答案</summary>

**兩個都是真的，因為講的是不同的東西 —— 而這正是重點。**

| | 2015 V2.1.2 | 2016 B20160516 | 這台 2018 |
|---|---|---|---|
| 網頁 `syscmd.htm`（出貨的 UI） | **在**，3,835 bytes | **在，逐 byte 相同** | **不在** |
| `boa` 裡的 `formSysCmd` 字串 | **0** | 不知道（rootfs 截斷） | **1** |
| `root_form[]` 分派表 | **不在**（59 筆） | 不知道 | **在**，`0x004838a8` |

**2015 的情況是：表單在，路由不在。** `handleForm` 是對 `root_form[]` 做
`strlen` 再 `memcmp` 的精確比對，沒有前綴規則、沒有第二張表，所以
`POST /boafrm/formSysCmd` 照程式碼讀是走到 `send_r_not_found`。
**廠商把路由拿掉了，但把會打那個路由的頁面留在映像裡。**

**這讓「這是廠商的修補」這個結論更強，不是更弱** —— 但也讓它更難看：
那是**修一半**。而修一半正是這個廠商在同一次揭露上的固定手勢：
`#skt&` 註解掉但 `/bin/skt` 照樣出貨、`onlime_r` 留在 `passwd.org`。
**一次揭露三個洞，三次都修一半。**

**2018 反過來：路由在，頁面不在。** 這個我解釋不了，而且我在 `PROGRESS.md`
開放問題 #11 明講了 —— 三年後有東西把那個路由放回去，我不知道是什麼。

> 對外講法：「我原本只 grep 過執行檔。把廠商真的出貨的網頁打開之後，發現
> 那兩半是反的 —— 而揭露者公告裡那句被當成廢話的括號『even if the GUI is not
> available』，講的就是這件事。」

</details>

### 12.15 🔴 那個 `w6cg` 的格式是你自己猜的。你怎麼知道你 parse 對了?

<details><summary>答案</summary>

**這個格式沒有校驗碼、沒有檔案數、沒有結束標記，所以沒有現成的東西可以對答案。
檢查必須從結構本身生出來。**

每一筆的步長都是 `64 + length`，所以走完整條鏈**要嘛剛好停在最後一個 byte,
要嘛歪掉**；而長度欄位猜錯一個 offset，一兩筆之內就會歪，**而且回不來**。
所以「零 bytes 剩下」不是好看而已，它是這個格式唯一能給的證明。

三份 bundle，全部 `self_check: exact`：1,720,168 / 1,704,011 / 1,417,000 bytes,
一個 byte 不剩。**而且測試裡我把長度欄位搬到 `0x38`（一個很合理的錯猜），
斷言它必須變成 `derailed`** —— 一個不會失敗的檢查什麼都沒證明。

**第二來源：143 這個數字對上了。** `auth-flow-2018.md` 兩週前用臨時方法數出
2018 那份是 143 筆；這支 parser 是在沒有參考那個數字的情況下寫的，跑出來也是
143。**兩個獨立的走法在一個沒有文件的格式上同意。**

**還有一個細節可以拿來反問我自己：長度欄是 big-endian，而 header 裡其他欄位
是 little-endian。** 混合位元序聽起來像是我讀錯了 —— 但如果我讀錯，那三次
`exact` 不可能發生。這是那種「猜錯就會爆給你看」的欄位。

> 對外講法：「格式是逆出來的，所以我沒有把重點放在『我覺得它是對的』，
> 而是放在『如果它是錯的，會怎麼被抓到』。答案是走鏈會歪。然後我寫了一個
> 測試，把欄位故意搬錯，確認它真的會歪。」

</details>

---

## 13. W05 Day 0：登記簿、凍結，以及「你憑什麼說你沒有事後改答案」

> 這一章的題目大多針對**方法**，不針對某個發現。方法比發現耐打，也比較常被問。

### 13.1 🔴 你把 130 個測試的預測先寫好再測。這不就是先射箭再畫靶的反面版本 —— 你會不會為了讓預測成立而挑測試?

<details><summary>答案</summary>

**會，而且這就是為什麼「反證條件」是必填欄而「預測」不是。**

先射箭再畫靶的問題不是「事先有假設」，是**事後才決定什麼算命中**。預先登記解的正是
後者：每一項都必須先寫下*看到什麼我就承認它不成立*。

以 `P3-3`（`formSysCmd` 未認證可達）為例，凍結的那句是：

> 未帶憑證收到 301 到登入頁，或命令沒有執行痕跡 → 「未認證」的讀法錯了，
> NVD 的 `PR:H` 是對的，X-7 那條爭議要撤回。

注意它指名了**哪一份既有結論要跟著改**。寫不出那一句，通常代表這個測試還沒想清楚
要問什麼。128 項裡有 98 項寫得出來，另外 21 項排進去但還沒寫 —— 工具會擋住它們
被記錄結果，而且登記簿會逐 Phase 把還沒寫的列出來。

**至於「挑測試」：所有 128 項都在同一個檔案裡，包含判定不成立的。**
釘死一條也是產出，而且 `refuted` 跟 `confirmed` 在同一張表上。要靠挑選來作弊，
得先把整份登記簿改掉，而那會出現在 diff 裡。

</details>

### 13.2 🔴 凍結雜湊在你自己的 repo 裡，你隨時可以改。這有什麼意義?

<details><summary>答案</summary>

**沒有防篡改的意義，只有「留下痕跡」的意義，而我沒有宣稱它是前者。**

鑰匙在作者手上，這是事實。它保證的是：改一個已經凍結的預測，**必須在同一個 commit
裡同時改掉那個雜湊**，`git diff` 會顯示成兩行刻意的修改。差別是「悄悄改掉」變成
「看得見地改掉」。

比整份雜湊更有用的是**逐項戳記**：每一筆結果都帶著它當時被判定所依據的那段文字的
`case_freeze_sha256`。所以：

- 新增一個項目 → 只有整份雜湊變，既有結果不受影響（這是為什麼戳記要逐項）；
- **改一個已經有結果的項目的反證 → `rtcase check` 直接紅**，訊息會說出舊戳記和新戳記。

「看到答案之後把反證條件寫鬆一點」是唯一一種不留下其他痕跡的作弊法，因為改完之後
整份登記簿讀起來是自洽的。這條檢查就是為它寫的。

**真正的保證來自 git，不來自雜湊。** 雜湊只是讓那個動作在 diff 裡沒地方躲。

</details>

### 13.3 🔴 你砍掉九項，包括反鑑識和降版。這是不是因為你不會做，包裝成「有原則」?

<details><summary>答案</summary>

**降版那一項我有完整寫法、有 bootloader 的 TFTP 路徑、也有 2015 的映像。做得到，不做。**

理由逐項寫在登記簿的「刻意不做」表裡，可以被反駁。分三類：

| 類 | 為什麼不做 |
|---|---|
| 後滲透（60 秒法則、loot、橫向移動、反鑑識、弱化式持久化） | **不產生關於這台的可驗證事實。** 要收的憑證早就從 flash 靜態解出來了；在活機上再收一次不會知道任何新的事，只會多出一份不該存在的副本。反鑑識與弱化式持久化的設計目的是讓一台被入侵的機器讀起來像一台設定很爛的機器 —— 那跟寫 write-up 的目的正好相反 |
| 降版裝回 2015 後門 | 不可逆，而且作用是把一個已知後門重新裝進一台已經沒有它的裝置。它要證明的性質（無韌體簽章、無 anti-rollback）靜態已經成立，回刷不會讓那個結論更真 |
| Evil Twin、廣播式無線 DoS | **輻射範圍及於第三方裝置。** 定向打自有 SSID / 自有 client 的項目留著，而且限制寫在案子上 |

**最能證明這不是包裝的，是留下來的東西：** §11.5 那條「設定值被拼進開機腳本的 shell
命令」留著，因為那是一個漏洞類別。留 finding，砍做法。

</details>

### 13.4 🔴 你說「一份狀態只能有一個擁有者」。那 README 的 gate 板不也在講同一件事嗎?

<details><summary>答案</summary>

**在講，但它只准講引用，不准講內容，而且這個界線寫進 `CLAUDE.md` 了。**

| 檔案 | 擁有 | 不准複述 |
|---|---|---|
| `PROGRESS.md` | gate、週、carried-forward | 單項測試的狀態 |
| `test-cases.toml` | 單項的預測 / 反證 / 結果 / 證據 | gate 的判定 |
| `README.md` | gate 勾選板 + 一行數字 | 上面兩者 |

`test-ledger.md` 是**生成的**，CI 會比對它跟登記簿是否一致 —— 手改它會讓
CI 紅。

會定這條規矩是因為 2026-08-16 真的發生過：`PROGRESS.md` 說某題已答，`LOG.md`
三個檔案外還把同一題當成未答。**那不是忘記，是同一份狀態有兩個擁有者。**
一張 130 列的表放兩份，一個禮拜就散。

</details>

### 13.5 🔴 這個 gate 自己會不會是假的?你怎麼知道 `rtcase check` 綠燈代表什麼?

<details><summary>答案</summary>

**因為有 22 個案例證明它擋得住東西，而且其中一個是必須通過的對照組。**

`tools/test-rtcase.sh`：1 個對照 + 21 個必須被擋下來的案例。而且每一個都檢查
**是不是因為正確的理由被擋** —— 只看 exit code 的話，一個因為無關原因失敗的案例
也會算過。

還有一層：**如果登記簿裡一個反證條件都沒有，`check` 會直接紅**，因為那時候凍結
檢查是在對一個空集合算雜湊，通過等於什麼都沒證明。這是本專案第 12 號工具 bug 的
形狀 —— 一個只在有東西可做時才會啟動的自我檢查，在沒東西可做時回報成功。

而這 22 個案例第一次跑就抓到 `rtcase record` 的一個真 bug：它假設登記簿一定在
repo 裡面，對 repo 外的暫存副本會直接 traceback。

</details>

### 13.6 👤 你回填了 5 筆已經有證據的結果。為什麼不乾脆全部從 0 開始，比較乾淨?

<details><summary>答案</summary>

**因為「乾淨」在這裡等於「假裝什麼都還沒做」，而且回填當場就抓到兩個沒有證據的說法。**

回填 P0-1 / P0-6 / P0-7 / P0-8 / P9-2 的過程中：

- **P0-8 記成 🔶 部分，不是 ✅。** `/bin/*.sh` 把設定值拼進 shell 的普查，在任何
  committed 的檔案裡都不存在 —— `rcS` 審過（`skt-analysis.md`、`credentials.md`），
  但那份普查只活在私有手冊裡。所以整條 MIB 持久化的線目前**沒有可引用的證據**。
- **順手發現「這台沒有 `nc` / `tftp`」從來沒被證明過。** 那份 55 個 binary 的清單
  數的是 ELF,**busybox applet 是 symlink，不會出現在裡面**。這句話現在降級成預測。

兩個都不是「找問題」找到的，是**試著填「證據」那一欄的時候填不出來**才浮出來的。
一張空表不會逼出這種東西。

</details>

### 13.7 🔴 那份紅隊手冊你放在 gitignore 的 `plan/` 裡不公開，是不是心虛?

<details><summary>答案</summary>

**分三塊，而且分法是寫下來可以被反駁的：findings 公開、reproductions 看揭露狀態、
tradecraft 完全不公開。**

- **findings 公開。** `form_formRoute` / `subnet` 進 `system()` 這件事就寫在
  `PROGRESS.md` 開放 #6，帶位址。指出一個缺陷在哪，那就是研究本身。
- **reproductions 看狀態。** 對 2024 就公開的 CVE,`poc/` 是在重現已公開的東西；
  對一個沒回報過的東西，同樣的目錄就是 0-day 食譜。`docs/disclosure.md` 逐項記
  現在是哪一種。
- **tradecraft 不公開。** 沒有任何 gate 要求它，它不產生關於這台的可驗證事實，
  而且 `README.md` 的 scope 明講不做武器化。

會這樣分，是因為原本那兩份原始手冊已經被 commit 進 `study/`（`6068fa3`，5,697 行）。
它還沒 push，拆掉了。**留著的話，敵意讀者三十秒就能把它跟 README 的
"not producing weaponised exploits" 並排** —— 他的結論不會是「作者很壞」，
會是「這個 repo 的自我聲明是裝飾」。

</details>

### 13.8 🔴 你加了一個 G3.75。gate 是你自己定的，加一個新的不就是把及格線畫在球落地的地方?

<details><summary>答案</summary>

**加 gate 只會讓自己更難過關；會被質疑的是改舊 gate，而那件事我刻意沒做。**

G3.5 目前是 4/5，那一格（`FLW` 演練）沒過。有兩個做法：

1. 把它搬進 G3.75，於是 G3.5 變成 4/4 ✅ —— **用改名把一格沒過的變成一個過了的 gate**;
2. 把 G3.75 的三格塞進 G3.5，於是上禮拜「4 of 5」那份回報變成錯的。

**兩個都沒做。** G3.5 維持 4/5,G3.75 的第 1 格是**引用**它而不是複述它，
理由寫在 `PROGRESS.md § Corrections to the plan`。

至於「加一個新 gate」本身：G3.75 五格過兩格，而且過的兩格都是文件工作。
它現在擋住 W05 送出第一個封包 —— 一條把自己擋住的線，不太像是畫在球落地的地方。

</details>

---

## 14. W05：模擬環境、oracle，以及「執行過」和「在矽上執行過」的差別

### 14.1 🔴 你說「模擬跑起來了」，但 `boa` 根本沒服務過一個請求。那叫跑起來嗎?

<details><summary>答案</summary>

**不叫，而且 `notes/emulation-2018.md` 的標題就沒有用那個詞。** 誠實的說法是：
**這台的 userland 在 x86 上執行，而 web server 沒有。**

跑起來的是：`/bin/flash`（讀寫 MIB、解 `w6cg`）、`/bin/busybox`、`/bin/sh`，
全部對著這顆 flash 的逐 byte 副本。跑不起來的是 `boa`，它死在
`libapmib.so+0x27dc` 的一個未對齊半字存取。

**而那個界線正好切在有用的地方。** W05 這一週要問的是「打中的時候看不看得到」，
而那個問題的答案在 sink 這一側 —— `system()` 就是 `/bin/sh -c`，shell 在手上。
`boa` 那一側要回答的是「打不打得中」，那是 Phase 2 的題目，而它**本來就排在真機上**。

所以正確的說法是：**W05 把觀測手段驗完了，沒有驗可達性。** 兩件事分開記，
登記簿裡也是分開的兩組項目。

</details>

### 14.2 🔴 `emulated` 這個證據等級是你自己加的。這不就是給自己開一個比 `static` 好看的欄位?

<details><summary>答案</summary>

**如果它能升級成 ✅ 就是。它不能，而且有三個測試在守這件事。**

原本只有 `static` / `dynamic` 兩格。qemu 裡真的執行了一段程式碼，記 `static`
低估（東西確實跑了、確實改了 flash 副本上的 byte），記 `dynamic` 就是這份登記簿
存在要防的那種灌水 —— 因為 `dynamic` 在這個 repo 裡的定義是**對這台硬體送過封包**。

所以加的是第三格，渲染成 🟪，而 `tools/test-rtcase.sh` 有三個案例分別斷言
`confirmed/dynamic → ✅`、`confirmed/static → 🟥`、`confirmed/emulated → 🟪`，
第三個如果變成 ✅ 就失敗。統計區也是獨立一行（「其中以模擬環境執行收掉（**不是矽上**）」）。

**判準很簡單：一個「給自己好看」的欄位，不會有人特地寫測試去阻止它變成滿分。**

順帶：加這一格的時候發現圖例的渲染有 bug —— 右欄是用左欄的長度去索引的，
**第七個結果標記會被靜靜丟掉**，而那正好是新加的這一個。那是儀器 bug 17。

</details>

### 14.3 🔴 你的 flash 是一個普通檔案。真機有抹除區塊、有損耗、有讀-改-寫。那三個 byte 的結論憑什麼算數?

<details><summary>答案</summary>

**它不算「結論」，它是一個對真機的預測，而且我把它寫成可以被打臉的形狀。**

模擬環境裡量到的是：`flash set HW_WLAN0_WSC_PIN 1` 在 4 MiB 裡改 3 個 byte
（`0x648a`、`0x648b`，加上 `0x006493` 這個 `H601` 區的 8-bit 校驗和），
而校驗和的變化量精確等於 payload 變化量的負值 —— 兩個相距 `0x3EE` 的欄位都成立。

**真機上如果不是這個樣子，那本身就是結果**，而且比一次確認更有價值：
它會告訴我模擬的寫入路徑跟真的那條差在哪裡。

`notes/emulation-2018.md` 的失真表把這一列寫成 **「是，而且是往樂觀的方向」**：
普通檔案的每一次寫入都成功、而且不會重寫別的東西；真機上那是對整個抹除區塊的
讀-改-抹-寫。**這個差異的方向是我先寫下來的，不是被問到才補的。**

</details>

### 14.4 🔴 你花了一整天在模擬，而登記簿 31 項只收掉 6 項。這一天的產出比例合理嗎?

<details><summary>答案</summary>

**不合理的是把它算成「31 項裡的 6 項」。那 31 項有 25 項需要一個網段，
而那個網段當天不存在**（這台筆電沒有內建網路孔，USB 網卡還沒 bind 進 WSL）。
在那個約束下，可做的部分做完了。

但這個問題有一個版本是對的，值得直說：**排程確實排錯了。** 計畫的 Day 1 是
掃描，Day 2 才是模擬；實際跑成相反，理由是 G3.5 #5 擋住了任何送到裝置的東西。
**而反過來跑之後，發現計畫給真機用的 payload 裡有三處是錯的**
（`id` 不存在、`>` 會被 handler 自己的重導向蓋掉、`/var` 可寫的理由引錯了 build），
每一處都是在一個弄壞了也沒代價的地方發現的。

所以我會說的是：「順序反過來是被迫的，但它比原訂的順序好，而我能說出好在哪三處。」

</details>

### 14.5 🔴 廠商的 `flash all` 跟你的 `fwrecon compcs` 有 67 處不同。你憑什麼說你的解碼器是對的?

<details><summary>答案</summary>

**我沒有說它是對的。我說的是「沒有一處是值不同」，而且其中兩條規則是我的錯。**

316 個共同名稱，249 個逐字相同，66 個由四條渲染規則解釋，1 個剩下。
關鍵是那四條規則**是一支腳本在套用的，而且有殘餘就 exit 1** —— 不是我用眼睛
分類完再宣告「都是格式問題」。

四條裡有兩條是 `fwrecon` 該改：全零的 `char[]` 印成 hex 而不是空字串、
4-byte 整數印成點分四段（`QOS_MANUAL_DOWNLINK_SPEED` 印成 `0.1.134.160`，
其實是 `100000`）。那不是「小差異」，是**任何讀我 JSON 的人都會讀錯**。

剩下那一個是 `L2TP_SERVER_IP_ADDR`：我的 MIB 表說 64 bytes，廠商印成 IPv4。
**那個欄位每一個 byte 都是零，所以這些資料沒有能力仲裁誰對。**
筆記裡寫的是「記錄，未解決」，不是挑一個贏家。

</details>

### 14.6 🔴 你說 `boa` 開機就建 `/web/config.dat`，可是它下一秒就當掉了，檔案是 0 bytes。這算什麼證據?

<details><summary>答案</summary>

**證據是那個 `open()` 呼叫，不是那個檔案的內容，而這兩件事回答的是不同的問題。**

W04-2 開放 #8 問的是：「`config.dat` 在這台的 docroot 裡嗎?如果要靠
`formSaveConfig` 生出來，那條鏈就多一步。」`strace` 回答的是**誰**建它、**什麼時候**：

```
lseek(3,49152,SEEK_SET)                     <- 0xC000, COMPCS
read(3,0x490018,7490)
open("/web/config.dat",O_RDWR|O_CREAT|O_TRUNC) = 3
```

**在建立監聽 socket 之前，而且不需要任何請求。** 那一步就把「要先 POST
`formSaveConfig`」這個前提消掉了。

**它沒有回答的是**：檔案裡最後有沒有東西、`boa` 會不會服務一個開機後才建立的檔
（`boa.conf` 有 `DirectoryCache /tmp`）、以及 GET 回來的內容是不是設定。
那三個都寫進 `PROGRESS.md` 開放題，登記簿的 `P10-1` 記的是 **partial**，不是成立。

</details>

### 14.7 🔴 那個 SIGBUS，你怎麼知道不是 qemu 把一條 Lexra 指令解錯了?那不正是這個專案最怕的事嗎?

<details><summary>答案</summary>

**因為我沒有只信 qemu 的反組譯器。** 那條指令是

```
0x27dc:  sh  s7,0(s8)
```

MIPS 的 `sh rt, offset(base)` 編碼是 `0x29<<26 | base<<21 | rt<<16 | offset`，
`s7`=23、`s8`=30，手算得 **`0xa7d70000`**。檔案 offset `0x27dc` 的原始 bytes 是
**`a7 d7 00 00`**，下一條 `sh s7,26(sp)` 手算得 `0xa7b7001a`，實際是 `a7 b7 00 1a`。

**兩個獨立來源：qemu 的反組譯，和一個從編碼規則手算出來的期望值。**
順帶，這個吻合也**確認了函式庫的載入基底**，而不是假設它。

opcode `0x29` 是標準 MIPS I。而 W04-2 的助憶碼普查早就數過這三個 build 的
**coprocessor 2/3 編碼：全部是 0** —— Lexra 的擴充指令就住在那塊 opcode 空間。

剩下的解釋只有一個：`libapmib` 做了一次未對齊的 16-bit 存取，真機的 kernel
（`arch/mips/kernel/unaligned.c`）會幫它修好，`qemu-user` 沒有 guest kernel。
三個 CPU model 都試過，`mips32r6-generic` 連載入都拒絕。

</details>

### 14.8 🔴 `P0-3` 你判通過，但同一份文件裡又說 `FLW` 的行為你還沒搞懂。那到底過了沒有?

<details><summary>答案</summary>

**過了，而且「過了」跟「搞懂了」是兩件事 —— 混在一起才是問題。**

`P0-3` 事先凍結的反證條件是一句話：**「讀回與寫入不一致，或抹除後該區塊不是全 FF
→ 救援路徑不成立。」** 實測：讀回逐 byte 一致（而且讀到一個全新的 RAM 位址），
寫 FF 之後回到全 FF。**兩個條件都滿足。**

未決的是**機制**：Step 6 回到 FF 代表一定有抹除，Step 5 顯示同磁區另一段沒被清掉，
而 bootloader 的完整指令集裡**沒有任何抹除指令**。三條線索指向
「讀-改-抹-寫回整個磁區」，但那是推定。

**事後把 `P0-3` 變難，跟事後把它變鬆一樣不誠實。** 所以它記成通過，
機制那條開成 `PROGRESS.md` 開放 #17，而且我把**作業單自己的設計錯誤**寫在旁邊：
Step 5 的讀回用了上一步已經填過相同內容的 RAM 位址，`RUNBOOK.md` §8.7.8
早就用名字警告過那個坑。

</details>

### 14.9 🔴 你連 `nc` 都沒有，那「這台被打下來會怎樣」不就沒什麼影響力?

<details><summary>答案</summary>

**影響力不在 `nc`，而且沒有 `nc` 這件事本身是量出來的，不是假設的。**

兩個獨立來源：rootfs 裡沒有 `nc` / `netcat` / `tftp` / `curl` / `telnet` 的 ELF;
busybox 自報的 48 個 applet 也沒有 —— **而且那次測試帶了對照組**
（`uptime` 有回應，證明 `applet not found` 是有意義的回答，不是呼叫方式壞掉）。
`/bin/wget` 確實存在，跟登記簿 `P8-15` 事先寫的一樣。

影響力在別的地方：`boa` 以 **root** 跑；`telnetd`、`login`、`chpasswd`
都編進 busybox 了；`root:123456` 還在 `passwd.org` 裡；而 `TELNET_ENABLED`
是**一個 MIB 旗標**，不是一個編譯選項。**未認證命令執行 → 開 telnet → root**
這條鏈中間沒有缺件。

而且還有一條更奇怪的：`/bin/startup.sh` 在「出廠設定與現行設定都無效」的分支裡，
`flash default-sw` 之後緊接著就是 `flash set TELNET_ENABLED 1`。
**這是靜態讀出來的，`flash test-csconf` 判什麼叫「無效」我還沒讀** ——
寫成線索，不寫成結論。

</details>

---

## 15. W05 Phase 3：真機上的 22 項，以及四條被自己的條件反證的預測

### 15.1 🔴 你說 `/config.dat` 跟 flash 一樣，那不就是「檔案就是檔案」?有什麼好講的?

<details><summary>答案</summary>

**講的不是那個檔案，是那兩條讀取路徑不共用任何程式碼。**

- W02 的 7,490 bytes：**bootloader 的 SPI 讀取常式** → `FLR` 搬進 RAM → `DB` 印成
  hex → 走 **UART 38400** → `console-dump.py` 解析。
- 今天的 7,490 bytes：**Linux kernel 的 MTD 驅動** → `libapmib` 讀 `/dev/mtdblock0`
  → `boa` 寫進 docroot → 走 **乙太網路** → `curl`。

`PROGRESS.md` W02 開放 #11 寫的是：「所有東西都走 bootloader 的 `FLR`，
**一個系統性錯的 `FLR` 對它們全部隱形**。」今天那個假設被一條完全不同的路徑檢驗了，
`sha256` 相同。

**範圍要說清楚：是 `0xC000`–`0xD142` 這 7,490 bytes，不是整顆 4 MiB。**
`H601`（`0x6000`）和 kernel 那幾段仍然只有一個儀器讀過。

</details>

### 15.2 🔴 22/31 就叫做完 W05?那 9 項呢?

<details><summary>答案</summary>

**沒有叫做完。`PROGRESS.md` 寫的是 DoD 4/5、登記簿 22/31，而且九項各有理由。**

分三類，而且第一類不是「沒做完」：

1. **`P3-1/2/3`（命令注入）是計畫規定本週不准做的。** W05 §五風險表把
   「忍不住開始做 W06 的 PoC」列為本週機率最高的風險，對策寫著
   「本週不做正式 PoC」。三個目標都定位了、觀測手段都驗過了，**開火是 W06**。
2. **`P9-9`（reset 按鈕）是破壞性的。** 它會用 `COMPDS` 蓋掉 `COMPCS`，
   而今天量到的 4/343 差異就是這台的現況證據。等 W07 那份證據不再需要的時候再測。
3. **`P1-4` / `P3-13` / `P1-12` / `P9-1` / `P9-3` 是時間。** 前兩項要 POST
   （而 POST 會真的執行 handler，要前後各抓快照），後三項要一次冷開機加 console。

**一句話：如果我說「W05 做完了」，`make todo WEEK=W05` 會當場拆穿我。**
那正是那個指令存在的原因。

</details>

### 15.3 🔴 四條預測被反證，聽起來像你的靜態分析不太行?

<details><summary>答案</summary>

**反過來：反證的那四條是這一週唯一有資訊量的部分，而它們反證的東西不一樣大。**

| 被反證的 | 反證掉的是什麼 |
|---|---|
| `P2-2` 豁免字串注入 | **一個被寫進 `PROGRESS.md` 的攻擊假設（X-3）**。十二種變形全部失敗 → 豁免比對有錨定或長度限制，反組譯讀出的「13 個不錨定 `strstr`」在**效果上**不成立 |
| `P2-7` session 模型 | **一個機制的歸因**。「這台沒有 session」是對的，但把它歸因到 `0x004899d8` 那個全域是錯的 —— 那個全域不授權任何東西 |
| `P2-4` `check_host` | 一個未知變成已知，而且方向對攻擊有利（DNS rebinding 前提成立） |
| `P1-3` docroot 覆蓋率 | 一個工具宣稱的邊界。`config.dat` 不在那 143 檔裡，是 `boa` 自己建的 |

**關鍵不是「錯了幾條」，是每一條都被**測試前凍結、雜湊進登記簿**的那句話反證。**
事後才寫的反證條件，只會反證出你當時想看到的東西。

而且要老實：**`auth-flow-2018.md` 的主結論是對的** —— 76 個 `.htm` 裡 69 個被擋、
7 個豁免、兩個不同的 302 目標，全部符合指令層級讀出來的那道門。錯的是從它衍生的
一個攻擊推論，不是那道門本身。

</details>

### 15.4 🔴 `Server: miniupnpd/1.4` 你憑什麼說它在說謊?也許廠商就是裝了 miniupnpd。

<details><summary>答案</summary>

**因為 rootfs 在手上，而裡面沒有那個 binary。**

三個來源：

1. `find` 整個 rootfs：有 `/bin/miniigd`（97,100 bytes），**沒有 `mini_upnpd`、
   沒有 `miniupnpd`、沒有 `upnpd`**。
2. `strings /bin/miniigd` **逐字含有** `Server: miniupnpd/1.4 UPnP/1.4`，
   旁邊就是 `MiniIGD %s (%s).` 和 `/etc/miniigd.conf`。
3. 線上 SSDP 回應的 `Location` 指向 `picsdesc.xml` —— 那是 linux-igd/miniigd
   的檔名，而 `rcS` 有一行 `cp /etc/tmp/pics* /var/linuxigd`。

**所以送出那個 banner 的程式碼，就在 `miniigd` 裡面。**

為什麼要計較：`miniigd` 是 Realtek 的 linux-igd 衍生版，對應 CVE-2014-8361
（在 CISA KEV 上）；`miniupnpd` 是另一個專案、另一組 CVE。
**只讀 banner 的人會查錯一整組 CVE。**

我沒有主張的：我**沒有**測試 CVE-2014-8361。52869 上只做了 `GET` 描述文件，
一個 SOAP action 都沒呼叫。

</details>

### 15.5 🔴 `CX` 那件事聽起來像巧合。一個字串差兩個字母，值得寫進 README?

<details><summary>答案</summary>

**它值得，因為它是一個可檢驗的、關於「別人怎麼找到這台機器」的事實，而且我有它的成本數據。**

| 在哪 | 有沒有 `CX` |
|---|---|
| `/etc/version`（整個 rootfs 唯一一個） | **有** |
| `/bin/boa` 字串表 | 沒有 |
| `/bin/sysconf` | 沒有 |
| **未認證的 `status.htm`（唯一遠端拿得到的）** | **沒有** |
| CVE-2024-51228 的受影響產品字串 | **有** |

**遠端指紋這台裝置，拿到的是沒有 `CX` 的那個；CVE 索引用的是有 `CX` 的那個。**

成本數據就是這個 repo 自己：`CLAUDE.md` 開頭那段寫著這是
「CVE-2024-51228 兩週沒被找到」的原因，而當時的解釋是「要搜版本字串不要搜標籤」。
今天知道了更精確的版本：**連版本字串都有兩個拼法，而網路上看得到的是對不上 CVE 的那個。**

**還沒證明的：** 這是這一台的怪癖，還是這個廠商 build 系統的性質。
CVE-2024-51228 點名六個產品，全都是 `-CX-` build。
如果它們的網頁介面也報不帶 `CX` 的字串，那就從軼事變成發現 —— 寫在開放題 #26。

</details>

### 15.6 🔴 你說「網段上只有兩個 MAC」，但你只聽了 45 秒。一個安靜的第三方呢?

<details><summary>答案</summary>

**對，而且我第一次的證據比這更弱 —— 那 45 秒抓到的是零個封包。**

**零不是證據，除非先證明那條線收得到東西。** 而那一刻它沒有：kernel 自己的介面
計數器是 `RX: 0 packets / TX: 12`。送三個 ARP 有回應之後 `RX` 才變成 3。
所以我重抓了一次，**主動製造已知流量**，得到 16 個封包、剛好兩個 MAC 各 8 個。
**「16 > 0」就是那次擷取的對照組。**

至於一個完全不說話的第三方：**測不到，而登記簿寫的條件本來就是
「`lab.pcap` 出現任何第三個 MAC」** —— 那是一個關於「有沒有人在講話」的條件，
不是關於「有沒有人在」。物理上這是一條網路線直連兩個埠，WAN 空著，
Windows 那一側的位址也確認消失了。**三個獨立的理由，而不是一個 45 秒的擷取。**

</details>

### 15.7 🔴 你自己違反了 G3.75 送出第一個請求，那這道 gate 有什麼用?

<details><summary>答案</summary>

**有用，而且它證明有用的方式就是我被自己記了一筆。**

事實：`GET /` 送出去的時候 G3.75 是 3/5，沒過的是隔離與 IoC 的埠那半。
我在驗證一個剛寫好的路由判斷，**沒有先看板子**。

兩件事是真的，而兩件都不構成理由：

- 狀態在我之前就變了（Windows 那張網卡跟這台做過 DHCP，作者送過 `ping`）；
- 那個請求是所有可能形狀裡最無害的一個（讀一頁，無參數，無 POST）。

**真正的失敗是一個有勾選框的前置條件沒有被讀。** 寫進
`PROGRESS.md § A process failure`，而不是修掉 —— 跟 2026-08-16 那次
document sync 同樣的理由：修是一句話，習慣不是。

**而 gate 本身是有效的：** 它的三個未完成格子，在後續兩個小時內全部被補上了，
順序是隔離 → IoC 埠 → 才開始掃描。如果沒有那道 gate，那個順序不會存在。

</details>

---

## 16. W05 收工：一個被自己推翻兩次的結論，一個被自己弄掉的伺服器

<details>
<summary><b>Q16.1 你早上說閘門的比對「是錨定的」，下午說「是未錨定的」。同一天，同一台機器，同一個人。我為什麼要相信第二個版本?</b></summary>

**因為第二個版本做了第一個版本沒做的事：它預測了還沒被看過的東西，而且說得出
自己會怎麼死。**

第一個版本是這樣得出來的：十二種豁免字串注入全部失敗 → 所以比對一定在某處被
錨定了。**那是從「我的攻擊沒成功」推論「機制不是我讀的那樣」**，而那一步沒有
任何獨立支撐 —— 它只是一個能解釋觀察的故事。

第二個版本先寫下機制，再從機制導出一組**可以打臉它**的預測：

| 預測 | 如果錯了 |
|---|---|
| 出貨的 76 個 `.htm` 裡，剛好 7 個免認證 | 多一個或少一個，模型就死 |
| 那 7 個包含 `wan_status.htm` 和 `Connect_status.htm`，而它們**不在任何一份豁免清單上** | 它們被擋 → 模型死 |
| 不存在的 `/zzqq.htm` → 302 到 `login.htm`；不存在的 `/zzqq_status.htm` → **不是** 302 | 兩個一樣 → 模型死 |
| `/boafrm/formLogin.htm` 會跟其餘 56 個端點**不一樣** | 一樣 → 模型死 |

**全部命中，零誤差。** 而第一個版本的預測能力是零 —— 它只是一句對已發生的事的
評論。

**一個假設不能被「我試了但沒成功」推翻，只能被「它預測了 X，而 X 沒發生」推翻。**

</details>

<details>
<summary><b>Q16.2 那個「未錨定」如果真的成立，為什麼不是一個認證繞過?你是不是在替一個沒打穿的洞找台階?</b></summary>

**不是，而且這個問題的答案比「它不是繞過」更有用。**

繞過需要兩個字串：一個拿去比對豁免，一個拿去開檔。如果它們是**不同的**字串，
未錨定的比對就是一個繞過原語 —— 你裝飾前者、保持後者乾淨。

**這台上它們是同一個字串**，而且是正規化之後的那一份：

```
/password.htm?x=status.htm   302 → login.htm   query 被切掉了,豁免字串不在路徑裡
/password.htm;status.htm     404               分號在路徑裡 → 豁免成立 → 但開不到這個檔
/login.htm/../password.htm   302 → login.htm   正規化在閘門之前,子字串已經沒了
```

第二行是關鍵，而且它**同時證明豁免生效了**（不是 302 而是 404）**和繞過不成立**
（檔案不存在）。

**所以正確的說法是：未錨定的比對在這台上不是繞過原語，是一個比程式碼寫出來的
名單更大的豁免集合。** 實際後果是兩個出貨頁面免認證，而它們不在任何一份
讀 `process_header_end` 的人會寫下的清單上。

</details>

<details>
<summary><b>Q16.3 你說 `P9-1` 被「三個獨立儀器」反證。三個都是你自己寫的腳本讀同一顆 dump，獨立在哪?</b></summary>

**不全是，而且該被質疑的那一個我自己也標出來了。**

| 儀器 | 輸入 | 誰寫的 |
|---|---|---|
| A `loader-unpack.py` | flash `0x0012F0` 的 LZMA 串流 | 我 |
| B 裝置 console 的 `?` | **裝置自己印的** | 廠商 |
| C kernel 的 `.rodata` | flash `0x060010+0x2808` 的**另一段** LZMA 串流 | 我（解壓）/ 廠商（內容） |
| D 開機 log | **裝置自己印的**（以及它**沒**印的） | 廠商 |

A 和 C 都是我寫的解壓程式碼，但它們讀的是 flash 上**兩段不同的壓縮串流**，
而且各自帶了自己的正對照組（A：17 個已知指令必須找到；C：宣告長度必須吻合，
而且 `Linux version` / `swapper` 必須存在）。

**B 和 D 完全不經過我的程式碼。** B 是裝置在序列埠上印出來的 16 條指令，
逐條對得上 A 的字串表 —— 如果 A 的解壓錯了，這一條會立刻爆掉。
D 是「開機 log 裡沒有 `Kernel command line:`」，而 C 解釋了為什麼：
**那個字串不在 image 裡**，所以它永遠印不出來。

**C 和 D 互相解釋，而且是一個能失敗的組合**：如果 C 找到了那個字串而 D 沒印，
就變成 loglevel 的問題，結論要重寫。

</details>

<details>
<summary><b>Q16.4 你把四個測試從 W05 搬到 W06/W07，然後宣布 W05 是 27/27。這不就是移動球門?</b></summary>

**是，而這正是為什麼那個動作現在會留下記錄。**

先說事實：那四項（`P3-1`/`P3-2`/`P3-3` 命令注入、`P9-9` reset 按鈕）的**不做決定
在搬動之前就已經存在**，寫在 `PROGRESS.md § Deliberately not done in W05` 裡，
理由是 W05 計畫 §五自己寫的「本週不做正式 PoC」和「reset 會刪掉別的測試正在用的
證據」。登記簿的 `week` 欄位與那個決定不一致 —— **矛盾的是資料，不是決定**。

但「決定在先」這句話，我說了不算。所以：

- `week` 進了一個新的雜湊 `[schedule].sha256`，跟 `[freeze].sha256` 同一個機制；
- 任何搬動必須同時填 `rescheduled_from` / `reschedule_reason` / `reschedule_date`,
  少一個 `rtcase check` 就紅；
- 六個守衛案例逐一驗證每一種「偷偷搬」都會失敗，外加一個正對照組驗證
  「誠實地搬」會過。

**這不是防篡改** —— 作者手上有鑰匙。它是「改動會出現在 diff 裡」和「不會」的差別。
一個敵意讀者可以打開 `git log`，看到那四行理由是什麼時候寫的、跟結果的時間戳
差多久。

**而如果不搬，唯一的替代方案是永遠說『W05 未完成』，同時明知那四項本週不准做。**
那不是誠實，那是讓收斂指令永遠說謊。

</details>

<details>
<summary><b>Q16.5 你自己把受測裝置的 web server 打掛了兩次，還把出廠預設區覆蓋掉。這不是實驗失敗嗎?</b></summary>

**前者是結果，後者是失誤 —— 而我把它們分開記。**

**web server 掛掉是結果。** `P1-4` 的反證條件在測試之前就寫著：「大量端點回 404
或連線中斷 → **先確認是不是自己把 boa 打掛了**，再下端點不存在的結論。」
它預期了這件事，而我們確認了。而確認的方式本身是有內容的：逐項 `elapsed_ms`
指出 `formPortFw` 佔住 9.65 秒、對照組會重試所以分得出「忙」和「死」、
console 全程零訊息、`ping` 全程正常、20 分鐘後 `boa` 沒有自己回來。

**那不是一次失敗的掃描，那是一個未認證的可用性缺陷的量測。**

**`COMPDS` 被覆蓋是失誤，而且是有結構的那一種。** `P9-9`（reset 按鈕）被延到
W07，理由白紙黑字是「保護 4/343 那份證據」。然後那份證據被 `P1-4` 毀掉了 ——
一個沒有任何警告標籤的測試。

> **風險登記簿的失效模式不是漏掉危險的動作。是把危險寫在響亮的那一個上面，
> 然後安靜的那一個從同一扇門進來。**

代價是可控的，而**代價可控本身是設計出來的**：前後各一份快照，所以差異可以逐欄位
歸因；而掃描前那份與 8/16 的完整 dump 逐 byte 相同，所以「不是開機造成的」是
量出來的。資料在裝置外有兩份副本，還原是 16 KiB 的 `FLW`。

**但「有副本」不等於「已還原」**，而我沒有還原它 —— 那是寫 flash，超出這一場
自己設的上限。所以它是 W06 的第一件事，寫在 `BENCH-LOG.md` 的「下一場從哪裡開始」。

</details>

<details>
<summary><b>Q16.6 「未認證的設定寫入會覆蓋出廠預設區」—— 你怎麼知道不是你的解碼器兩邊都讀錯?</b></summary>

**四個獨立的檢查，而且其中兩個是廠商自己的。**

1. **逐 byte 的比較，不經過解碼器。** `cmp -l` 說 14,068 個 byte 不同，
   並且分區落在 `0x8000-0xC000` 和 `0xC000-0x10000`，
   而 `0x0-0x6000`（bootloader）與 `0x6000-0x8000`（`H601`）**一個 byte 都沒動**。
   如果是解碼器的問題，不會有這種乾淨的區塊邊界。
2. **`libapmib` 自己的 8-bit checksum，三份都過。** 那是廠商的程式碼在判自己的資料。
3. **ring-fill 一致性檢查通過** —— 用兩種不同的 LZSS 視窗初值解碼，結果相同。
4. **方向是可判別的，不是對稱的。** 那四個原本區分兩區的欄位，
   `COMPDS` 全部移到了 `COMPCS` 的值（`0→1`、`0.0.0.0→0.0.1.224`、`0→1`、
   全零→現行 SSID）。**如果是解碼器在亂讀，沒有理由只往一個方向亂。**

**還沒證明的是：是哪一個 handler 做的，以及它是一次寫兩區還是兩次寫。**
那要讀 `libapmib` 的 `Encode` 那一側，而它到今天仍然未讀。

</details>

<details>
<summary><b>Q16.7 你的 `bench-probe` 在最關鍵的一次執行裡什麼都沒寫。那份工具值得信任嗎?</b></summary>

**那一次不值得，而它現在寫得出來了 —— 但你問對了方向，所以我把完整的失效講完。**

那支工具存在的理由，就是防止一個具體的失效模式：一次打錯的 POST 讓 `boa` 死掉，
然後後面 57 個端點全部回「連不上」，看起來跟「端點不存在」一模一樣。

**今天那件事發生了。工具偵測到了。然後 `ProbeError` 在寫檔那一行之前就 return,
59 筆回應連同逐項 `elapsed_ms` 全部消失** —— 而那裡面就有卡住 9.65 秒的那一個。

**偵測一個事件和保存它的記錄，不該是同一條程式路徑。** 現在 journal 和 records
都在 module scope，任何出口都會寫檔，而且守衛套件有一個案例逐一驗證
「中止的執行會寫出一份說明自己為什麼中止的 transcript」。

同一天我還把 `set -o pipefail` + `grep -q` 重新寫進守衛套件裡 ——
而 `PROGRESS.md` **當天早上**才把那個記成儀器 bug 15。兩個正確觸發的拒絕被回報成失敗。

**這一整串的教訓不是「要更小心」。** 是：**一個宣稱能偵測 X 的工具，必須有一個
案例證明它在 X 真的發生時的行為**，而不只是證明它認得出 X。前者今天才被加進去。

</details>

<details>
<summary><b>Q16.8 `P1-12` 你量到 38.76 秒，預測是「小於 40 秒」。餘裕 1.24 秒，而你自己說 t=0 不是通電瞬間。這一項不該判成立吧?</b></summary>

**判定的依據是事先凍結的那句話，不是我事後覺得舒不舒服 —— 而那句話寫的是
「明顯超過 40 秒」。**

38.76 不是明顯超過。所以反證條件不成立，判 `confirmed`。**如果我因為餘裕太薄而
改判，那就是事後調整標準，而這個登記簿存在的全部理由就是不准那樣做。**

**但把數字寫成結論就是誤導，所以判定旁邊寫了三件事：**

- t=0 是第一個 console 字元，**通電到第一個字元的那段沒有量**，所以 38.76 是下界；
- `boa` 印出 `starting server pid=350, port 80` 在 +32.50，第一個 200 在 +38.76 ——
  **中間有 6.26 秒它已經自報啟動但不服務**；
- 這一項存在的用途是當「服務沒回應」判定的基準線，所以**可用的形式是「等 45 秒」**，
  不是「小於 40 秒成立」。

**一個判定成立、而它的可用形式跟預測的數字不同，這件事本身要寫出來。**
否則下一個人會拿 40 秒去掃描，然後把還沒起來的服務讀成關的。

</details>

<details>
<summary><b>Q16.9 `BENCH-LOG.md` 開頭說 per-unit 識別碼不寫進來，而同一份檔案裡有兩個 MAC 位址。你的自我檢查到底有多可靠?</b></summary>

**這一題沒有好答案，而我不打算給一個。**

事實：標頭寫「per-unit 識別碼（MAC、SSID、`config.dat` 內容、射頻校準值）不寫進來」，
而 2026-08-17 上午那一場的 `R1` 段落記了兩個 MAC。

檔案是只追加的，所以那一段不動，矛盾記在最新那一場裡。**兩種可能，而我沒有替作者選：**

- 那條規則是對的 → 上午那一段是違規，要走一次 git 歷史重寫，那是有成本、
  要作者決定的動作；
- `docs/disclosure.md` 的 per-field 決定（自購、已停產、從未部署）涵蓋 MAC
  → 那條規則本身寫得太寬，該由 `docs/disclosure.md` 收斂。

**而這一題真正的答案是第三件事：標頭不該複述那條規則。** 一份狀態一個擁有者 ——
`docs/disclosure.md` 擁有揭露策略，標頭複述它就是第二個擁有者，
而第二個擁有者遲早會跟第一個不一致。**它已經不一致了，而發現它的是一次
搬檔案的路徑檢查，不是任何一次自我檢查。**

</details>

---

## 17. W05 收工第二輪：一份文件的形狀，以及一支檢查器沒有讀的那個檔案

<details>
<summary><b>Q17.1 你的檢查器是為了抓 `AUTOBURN: 0` 那個錯而寫的，結果那個錯還活在 `RUNBOOK.md` 裡。所以它到底抓到了什麼？</b></summary>

**它抓到了它讀的那個檔案裡的那一份。另一份它從來沒看過，而我到 2026-08-17 晚上
才去問「它不讀什麼」。**

事實的順序值得寫清楚，因為它比結論難看：

1. `AUTOBURN: 0`（冒號式）在真機上回 `Unknown command !`；
2. 這件事當天就記成儀器 bug 19，記在 `PROGRESS.md`；
3. `tools/check-runsheet.py` 為此而寫 —— **在那之前沒有任何東西把作業單裡的
   命令當命令讀**；
4. 它讀 `runsheet.md`；
5. **`RUNBOOK.md` §8.12 裡那個冒號式命令一直在，而且它就在記錄了 bug 19
   的同一個 repo 裡。**

**所以這一題的正確答案不是「檢查器有效」，是「檢查範圍的邊界從來沒有被
測量過」。** 那道邊界是我畫的，畫的時候是對的（§8.12 當時宣稱命令已經搬走），
而**宣稱和執行是兩件事** —— §8.12 的開頭寫著「命令搬走了」，然後裡面有 12 個
命令塊，其中 4 個當天就被否證。

一份自我檢查報告成功、而它其實沒有東西可檢查 —— 那是 bug 12 的形狀，
而這一次是同一個形狀換了範圍：**不是「檢查了空集合」，是「集合的定義漏掉一半」。**

**下一個要問的問題不是「這個檢查器對不對」，是「還有哪些檔案裡有沒人讀的命令」。**
目前的答案：`REPRODUCE.md` 有命令塊（未檢查）、`README.md` 有（未檢查）、
`docs/` 有（未檢查）。**那是一個開放題，不是一個已修的 bug。**

</details>

<details>
<summary><b>Q17.2 你不是去檢查 §8.12 的命令，而是禁止它有命令。那不就是把問題掃到地毯下面？寫在散文裡的命令你怎麼辦？</b></summary>

**不是掃到地毯下，是把一整類漂移變成結構上不可能。但你的後半句是對的，而那個
缺口還開著。**

兩個選項，成本不一樣：

| 做法 | 抓得到什麼 | 抓不到什麼 |
|---|---|---|
| 去檢查 §8.12 的命令 | 旗標、目標、路徑錯誤 | **兩份文件對同一步的命令不一致** —— 兩邊都合法，但只有一邊是現在跑得動的 |
| 禁止 §8.12 有命令 | 上面那一整類，以及「舊版本留在另一個檔案」 | **散文裡的命令片段**，例如「先送 `AUTOBURN 0` 再送 `IPCONFIG`」 |

**第二欄才是這次真正發生的失效**：§8.12 的命令沒有「壞掉」，它們是**上一版**。
一支只驗語法的檢查器會對兩份互相矛盾的合法命令都打勾。

而散文裡的片段確實抓不到。**現在靠的是「§8.12 不放 fence」這條規則會讓寫的人
自然把命令留在 runsheet**，而那是社會性約束不是機械性約束。
**要機械化，得比對兩份文件裡出現的同一個指令 token —— 那需要一份指令詞表，
而那份詞表會變成第三個擁有者。** 沒做，理由寫在這裡。

</details>

<details>
<summary><b>Q17.3 你說「站號就是板子必須在的狀態」，但你自己承認 `A3.1` 不需要第 3 站的狀態。那這個不變式是假的。</b></summary>

**不變式的正確寫法是「站號是這一節需要的**最低**狀態」，而我第一版寫成了
「就是狀態」。你抓到的是措辭，但措辭在這裡是有代價的。**

`A3.1`（網段）只需要板子有電 —— 停在 `<RealTek>` 也行，因為那時 Ethernet 已經
初始化（開機 log 印 `---Ethernet init Okay!`）。它排在第 3 站開頭，理由是
**`A3.2` 的輪詢需要位址已經設好**，那是一個順序相依，不是狀態相依。

**兩種可能的修法，我選了第二種：**

| 修法 | 代價 |
|---|---|
| 把 `A3.1` 移到第 2 站尾 | 站的定義變成「最低狀態」，而讀者要自己判斷哪幾節其實可以更早 —— 把判斷推給讀者 |
| 留在第 3 站開頭，並在站的說明裡寫明它不需要這一站 | 編號略微鬆散，但**照著讀一定不會錯**，而「照著讀不會錯」是整個重排的目的 |

**一個永遠成立但需要讀者思考的規則，比一個略鬆但照做就對的規則差。**
那句話寫進第 3 站的說明裡，就在會影響判斷的位置。

</details>

<details>
<summary><b>Q17.4 你搬了 19 節、換了每一個編號，然後說「一行內容都沒掉」。你怎麼知道？</b></summary>

**用一個會失敗的比對，而不是用眼睛。**

搬移是腳本做的，不是手做的 —— 手抄 2,200 行掉東西是無聲的。
驗證的方式是：把搬移前後兩份檔案的**每一行都把 `A<數字>` 換成 `A#`**
（因為編號一定會變），然後做兩個 multiset 的差集。

結果：**只在舊檔出現的 76 行、只在新檔出現的 74 行**，而那 150 行**逐一對得上
預期的變形** —— 18 個 `| | |` 無表頭表格、18 個分隔列、19 個標題、
21 個欄位列出去；19 張新表（各 2 行）、19 個新標題、4 個站區塊、
11 個 `**先決條件**` 列進來。**本文一行都不在那 150 行裡。**

**這個檢查會失敗**：如果我漏搬一節，那一節的每一行都會出現在「只在舊檔」那一欄，
而那一欄我是逐行印出來看的。加上一個獨立的第二來源 —— 檢查器數到
**19 節、4 站、42 個子節、0 個指不到的交叉引用**。

**而它第一次跑出來是錯的**：新編號被當成舊編號又對映了一次，`### A1.1` 變成
`### A1.2.1`。那不是這個比對抓到的，是我看標題清單看到的 —— 所以這個比對
**不能**證明編號正確，只能證明內容沒掉。**兩件事要分開講。**

</details>

<details>
<summary><b>Q17.5 首頁那張目錄把每一節關掉的編號又寫了一遍。你自己的規矩是「一份狀態一個擁有者」。</b></summary>

**是重複，而重複在這個 repo 裡只有一個合法理由：機器讓兩份保持相同。**

編號的擁有者是**節標題**（`（關 P0-2 · P0-5）`），metadata 表格**不再有**
`關掉的項目` 那一列 —— 那一列被拿掉就是為了不要有第二個擁有者。
目錄那一欄是第三次出現，而 `make ci` 對它做三件事：

1. 目錄列出的節，必須剛好是存在的節（少一個、多一個都紅）；
2. 每一節在目錄裡的編號集合，必須**等於**它標題裡的集合；
3. 標題裡的每個編號必須真的在登記簿裡，而登記簿裡每個已執行的項目
   必須至少被一節聲稱。

**沒有第 1、2 條的話，目錄就是第二個擁有者，而它遲早會落後。**
`BENCH-LOG.md` 標頭複述 `docs/disclosure.md` 的規則、然後跟自己檔案裡的
一段矛盾 —— 那就是沒有機器看著的重複長什麼樣。

**判準：一份重複如果有 CI 檢查，它是指標；沒有的話，它是第二個擁有者。**

</details>

<details>
<summary><b>Q17.6 全角標點這件事聽起來像美工。你花時間改 5,000 個逗號，這跟找漏洞有什麼關係？</b></summary>

**沒有關係，而它是這一輪唯一一件作者自己指得出來但講不出原因的事。那件事本身
值得記。**

事實：作者說「新的 runsheet 很奇怪、不直觀，可能是格式問題」。
去量之後，`runsheet.md` 有 **1 個**全角逗號、**470 個**半角逗號，
而被重構掉的舊檔是 **272 對 11**。而且它是**混排** —— 句號是全角 `。`，
逗號是半角 `,`。中日韓排版裡那看起來就是壞的，而它每一行都在扎人，
所以指不出是哪一行。

**但把它當成主因是錯的，而我一開始差點那樣做。** 量完之後真正的問題有三個，
排版只是第三個：

1. **文件順序不是執行順序** —— Part A 讀 `A0`→`A14`，實際跑
   `A0`→`A2`→`A3`→`A5`→`A4`，一個陌生人照著讀會做錯；
2. **同一段程序三套編號**，其中兩套互相不指名；
3. 排版。

**這一題真正的教訓是關於回饋怎麼讀的**：一個「感覺不對」的回饋值得去量，
但**不能照著它的歸因去修**。作者說的是「格式」，量出來的是「順序」。
如果只修了標點，這份文件會變好看，然後繼續把讀者的操作順序帶錯。

</details>

<details>
<summary><b>Q17.7 三套編號你只機械化了兩套之間的橋，第三套（`§8.12.x`）你說「凍結」。那不就是承認你收不乾淨？</b></summary>

**是，而理由不是懶，是 `BENCH-LOG.md` 只能追加。**

`BENCH-LOG.md` 裡有兩場的開工順序是用 `§8.12.x` 記的
（`§8.12.1 → 8.12.2 → §8.9.3 → 8.12.3 → …`）。那是**逐字紀錄**：
它的價值全部來自「當天實際打了什麼、看到什麼」沒有被事後修過。
**重編 `§8.12.x` 會讓那兩行指向不同的東西，而修那兩行就是修證據。**

所以現況是誠實的三套：

| 誰 | 編號 | 動不動 |
|---|---|---|
| `runsheet.md` Part A | `A1.1`–`A4.2` | 重排過，舊新對照在 Part B `B-0` |
| `RUNBOOK.md` §8.12 | `8.12.1`–`8.12.16` | **凍結**，因為 BENCH-LOG 引用它 |
| `BENCH-LOG.md` | 引用上面第二套 | **只追加，不動** |

**能做的是讓橋不會斷**：每一節指名它的 `§8.12.x`，每一個 `§8.12.x` 指名它的節，
一對一，CI 兩端都檢查。**兩套編號還是兩套，但沒有人需要猜對映。**

**而這件事的成本要說出來**：一個讀者第一次進來會看到兩種編號指同一段程序，
那是一次認知負擔，而它換來的是一份沒有被改過的證據檔。**這個交換我認為值得，
但它是一個交換，不是一個乾淨的解。**

</details>

---

## 18. W06：九個 byte、兩條被自己撤回的發現，以及我把散文當成量測的那一次

### Q18.1 你說「一個未認證的 HTTP 請求改了 flash 上九個 byte」。我怎麼知道那九個 byte 不是你自己用 bootloader 寫進去的？

<details><summary>答案</summary>

**你不能只從那份 diff 知道，而這正是為什麼寫入工具的白名單是這個問題的答案。**

`tools/console-write.py` 只能寫兩段：演練用的 `0x3F0000`–`0x400000`，
和設定區 `0x008000`–`0x010000`。**`H601`（`0x6000`–`0x8000`）不在裡面，
而且沒有任何旗標放得寬** —— 那是一個 `grep` 就能驗證的性質，
`tools/test-console-write.sh` 有一個結構性案例讀那個常數本身，
所以將來有人加第三段進去，CI 會紅。

**那九個 byte 全部在 `0x648a`–`0x6493`，也就是 `H601` 裡面。**
我的工具在建構上寫不到那裡。

第二層：那九個 byte 裡有一個是**校驗和**，而它的值跟其餘八個的變化量對得上。
我沒有實作那個校驗和的計算 —— `qemu-env.sh diff` 有一個驗證式，但那是驗證不是產生。
**要偽造這個 diff，我得先實作一個我沒有實作的東西。**

第三層，也是最便宜的：**時間順序在 `BENCH-LOG.md` 裡是逐字的**，
而那個檔案只追加。注入的 `curl` 與前後兩次 `console-dump.py dump` 的順序在那裡。

</details>

### Q18.2 那九個 byte 是 WPS PIN。一個 WPS PIN 有什麼了不起？

<details><summary>答案</summary>

**PIN 本身不了不起，它落在哪一塊才了不起 —— 而我一開始也講錯了。**

`plan/W06` 說 `flash set` 寫的是 `COMPCS`（設定區）。**不是。**
`HW_WLAN0_*` 是硬體 MIB，住在 `H601`。差別是：

| | `COMPCS` | `H601` |
|---|---|---|
| 內容 | 設定 | **這台的 MAC 位址與射頻校準常數** |
| 來源 | 使用者與 handler | **出廠時量出來寫進去的** |
| 廠商映像裡有嗎 | 有等價物 | **沒有** |
| 出廠重置還原嗎 | 會 | **不會** |

所以真正的主張不是「WPS PIN 可以被改」，是
**「一個未認證的 HTTP 請求寫得進這台唯一無法從裝置外部任何來源復原的那一塊」**。

**而我只寫了一個欄位。** 「MAC 也在同一張表裡、所以也寫得進去」是**推論不是量測**，
它是 `PROGRESS.md` 開放 #35，不是這裡的主張。

</details>

### Q18.3 你花一個早上做了一個「白名單讓 `H601` 搆不到」的寫入工具，然後晚上把 `H601` 寫了。那個工具有什麼用？

<details><summary>答案</summary>

**這個問題問得對，而答案是：那個工具做到了它該做的，而它保護的東西不是我以為的那個。**

它保護的是**我的手滑**：打錯位址、燒進一份截斷的檔案、把 `0x8000` 打成 `0x6000`。
那三件事今晚都沒發生，而 `EB` 一行的容量量到 32 只進 17 —— 如果我猜 32，
那份 16 KiB 會有一半是垃圾，而**擋住它的是寫入前的 RAM 回讀**，不是白名單。

它保護不了的是**攻擊者**，因為攻擊者不用我的工具。

**而那才是這一晚真正的發現**：我把「這一塊不可復原」翻譯成了
「我的工具不准碰它」，卻沒有翻譯成「**有沒有別的東西碰得到它**」。
那個問題如果早八個小時問，`plan/W06` 的第 ⑤ 環就會在動手之前被改對。

**一個防護措施的範圍，跟它被寫下來的理由，是兩件事。**

</details>

### Q18.4 你在同一天撤回了自己兩條「本專案獨家」的發現。那你之前那些發現還能信嗎？

<details><summary>答案</summary>

**這個問題應該反過來問：一張只會長不會縮的發現清單，代表沒有人在檢查它。**

兩條各自被不同的東西撤回，而方式不一樣：

- **`D-1`（`formRoute`/`subnet` 到 `system()`）**：被**外部先前技術**先預測，
  再被量測確認。Talos TALOS-2023-1894 讀同一個 SDK 家族的同一個參數，
  找到的是 `sprintf` 進 100-byte 緩衝區，**沒有 `system()`**。
  然後實機打下去零封包，而**同一個 handler 換 `localPin` 有四個封包** ——
  所以不是「打不到」。`BoaGate` 的 R2 規則把 `sprintf` site 誤判成 `system()` site。
- **`D-2`（不帶 `submit-url` 崩潰）**：被**正面證人**撤回。`formNtp` 把
  `submit-url` 原樣回顯進 `Location`，送 800 bytes 回來 799 個 `A` ——
  **值確實抵達了使用它的程式碼**，然後什麼都沒發生。

**信任應該轉移到方法上，不是清單上。** 具體地說：`D-1` 的問題是
**一個工具的結果沒有第二個來源就被寫進了揭露登記簿**，
而這個 repo 的第一條紀律就是不准那樣做。那條紀律當時沒有被套用在自己的 Ghidra script 上。

**現在還沒被檢查的是 R2 的另外四個 site**（`PROGRESS.md` 開放 #36）。
那不是一句安慰，那是一個具體的、可以拿去打我的清單。

</details>

### Q18.5 你說 W05 記錄「`boa` 在模擬下服務不了」是錯的。那 W05 的其他結論呢？

<details><summary>答案</summary>

**那句話不是量測錯，是範圍寫太寬，而兩者的後果不同。**

W05 量到的是真的：`libapmib` 有一個未對齊的半字組儲存，qemu-user 沒有 guest kernel
可以修它。**錯的是把「它在某處 SIGBUS」寫成「它服務不了請求」。**
`-strace` 一跑就看得到位置：

```text
open("/web/config.dat", O_RDWR|O_CREAT|O_TRUNC) = 3
--- SIGBUS si_addr=0x00492b41 ---
```

它死在**產生 `config.dat`**，不是死在服務。擋掉那一個 `open()`，server 就起來了。

**所以要重新檢查的是 W05 所有「因此不可能」形式的結論**，不是它的量測。
這一週已經因此改了兩個：那一條，以及「服務中斷是因為請求數量」
（實際上一個特定 handler 一發就夠）。

**而這件事有一個成本我要說出來**：如果 W05 當時多跑十分鐘的 `-strace`，
W06 的整個 L2 那一層可能在計畫階段就長不一樣。**一句寫太寬的結論，
會讓後面幾週繞開一條其實是通的路。**

</details>

### Q18.6 你把十個項目改期到 W07。那不就是「做不完就改時程」嗎？

<details><summary>答案</summary>

**如果理由是事後寫的、而且沒有人能檢查，那就是。所以這個 repo 讓它不能是。**

改期要三個欄位（`rescheduled_from`、`reschedule_reason`、`reschedule_date`），
少一個 `rtcase check` 就拒收，而且 `[schedule].sha256` 要在同一個 commit 裡重新宣告。

**但今晚證明那還不夠。** 我寫的十個理由裡有四個引用了一句我沒有跑過的話
（「`boa` 在 qemu-user 下服務不了」）。九十分鐘後我跑了，那句話是錯的。
**而更正那四個理由，雜湊一動也不動** —— 因為它只涵蓋 `(id, week)`。

也就是說：**理由可以事後被改寫而不留痕跡**，
「我做不到」可以悄悄變成「我選擇不做」。那跟預測凍結要防的是同一件事，只差一個欄位。

**現在雜湊涵蓋整個改期紀錄**，而 `tools/test-rtcase.sh` 有一個案例證明
「宣告雜湊之後再改寫理由」會被擋下來。

**所以答案是：改期本身不是問題，改期的理由沒有人能查才是。**
而這一次是我自己踩出那個缺口的。

</details>

### Q18.7 「一個請求殺掉 web server」—— 你怎麼知道不是前面幾十個請求累積的？

<details><summary>答案</summary>

**因為有對照組，而且是在乾淨開機之後跑的。**

```text
formNtp  #1  HTTP 302  alive
formNtp  #2  HTTP 302  alive
formNtp  #3  HTTP 302  alive
formSchedule HTTP 000  DEAD    30 秒後仍 DEAD
device ping                    1.6 ms 正常
```

三發**同樣形狀**（只帶 `submit-url`）的 POST 打在另一個 handler 上，全部正常；
第四發打在那一個 handler 上，`curl` **連回應都沒收到**，而且 30 秒後
監聽 socket 還是不在。**裝置本身活著**，所以不是斷線。

第一次觀察到它是那次開機的第 13 個請求 —— **所以第一次觀察不足以宣稱**，
而那正是為什麼要多燒一次開機循環重做。

**沒量的東西我也列出來**：它是崩潰還是卡住（`boa` 不寫 core，這個 kernel 的
`dmesg` 是空的）、哪一種參數形狀觸發、以及 W05 那次服務中斷是不是同一個原因。
第三個是重讀 W05 transcript 的工作，不是 bench 的工作，**混在一起就會讓今晚的
量測不再是關於今晚**。

</details>

### Q18.8 你的 PoC 目錄裡有一個檔案完全沒有請求。那不是留白給自己看的嗎？

<details><summary>答案</summary>

**它是這個 repo 的規則第一次讓我少寫一份我很想寫的東西。**

規則在 `docs/disclosure.md`：**發現可以公開、重現跟著揭露狀態走、tradecraft 完全不發布。**

`poc/01`、`02`、`03` 有完整的請求，因為它們重現的是 2019 與 2024 就公開的東西。
`poc/04` 描述的兩件事 —— 未認證改管理密碼、以及密碼設空之後整台不再檢查認證 ——
**沒有向任何人通報過**。所以一個可以複製貼上的請求不是「重現已公開的工作」，
是一份針對一台已停止支援、而且還在被使用的裝置的配方。

**而那個檔案不是空的**：它寫出發現、寫出判定、指向登記簿的哪一列，
並且寫出**什麼會讓它變成一份真的 PoC**（逐 handler 的 prior-art、通報、90 天時鐘）。

**一個從來沒有讓作者付出代價的揭露政策，沒有被測試過。** 今晚是它的第一次。

</details>

### Q18.9 G4 沒過。那你這一週算成功還是失敗？

<details><summary>答案</summary>

**五條裡過四條，而沒過的那一條比過了更有價值 —— 這句話聽起來像藉口，所以要講清楚它為什麼不是。**

沒過的是 **L2**：任何人 + 下載得到的映像 + 模擬。原因不是做不到，是
**那條鏈的標的 handler（`formSysCmd`）在兩個下載得到的映像裡都不存在**。

而那是兩個**各自正確**的決定撞出來的：
計畫假設 L2 跑 `localPin`（它在 2015 與 2020 完全相同）；
W04-2 把 G4 標的換成 `formSysCmd`，因為那是指名這台 build 的 CVE。
**換標的的時候沒有人回頭問 L2 還成不成立。**

如果我把 G4 判成過，我就得把 L2 的定義改成「在這台自己的 rootfs 上模擬」——
**那就是把門檻挪到球的位置**。這個 repo 有一整章在講那件事為什麼致命。

**而現在那條路是通的**（今晚才證明 `boa` 在 qemu-user 下服務得了），
所以它是 W07 的第一件事，而且不需要裝置。**一個有具體下一步的失敗，
比一個定義被調整過的通過有用。**

</details>

## 19. W07 Day 0–1：G4 收掉的方式、一個公開映像上的命令執行，以及四次無效的量測

### Q19.1 你把 G4 的第三條拆成 3a 跟 3b，然後宣布 3a 過了、3b 不可能。這不就是把門檻挪到球的位置嗎？上一輪你自己才說那樣做是致命的。

<details><summary>答案</summary>

**這個質疑是對的方向，而且我在做之前就先把它問過一次。差別在於「拆」跟「放寬」不是同一件事，判準是：拆完之後，有沒有任何一條原本會失敗的主張變成通過。**

原本的 clause 3：「同一條鏈，在公開映像上重現。」
拆成：
- **3a** 命令注入這個**原語**，在公開映像上重現 —— ✅ 做到了
- **3b** **L1 那一條鏈本身**，在公開映像上重現 —— ❌ 不可能

關鍵在 3b **沒有變成通過，它被判定為結構上不可能並且留在板子上**。
`formSysCmd` 在這台的 `root_form[]` 裡（`0x0044ee2c`），在兩個下載得到的映像裡
都沒有。這不是「我做不到」，是**任何人都做不到**，包括廠商自己 —— 一個指名
了沒有人下載得到的 build 的 CVE，本來就不可能被沒有那台機器的人重現。

**如果我把它留成「待辦」，那才是不誠實**，因為它會暗示再花時間就會好。
它不會。

一個檢驗方法：拆完之後，這個 repo 對外能講的話**變少了還是變多了**？
變多了一條「這個缺陷類別在下載得到的韌體上成立」，
同時**多了一條限制**「這台的那條鏈沒有人能重現」。
放寬門檻只會讓限制消失，而這裡限制被寫進 README 的 gate 板。

</details>

### Q19.2 你的 L2 環境有三段是你自己合成的。那你到底是在測廠商的韌體，還是在測你自己寫的東西？

<details><summary>答案</summary>

**82.9% 來自下載，剩下的每一個 byte 都被列名 —— 而且被合成的那三段，沒有一段參與缺陷本身。**

`reports/mkflash-2.1.2.json` 把每一段標成 `published-image`、`overlay`（帶
來源字串與 sha256）或空白 `0xFF`。CI 會擋下沒有來源字串的 overlay，因為
**一個沒被命名的 overlay 跟一段從實體機器上挖來的 byte 是分不出來的**。

三段合成的是 `H601`（硬體設定）與 `COMPDS`/`COMPCS`（設定），payload 全零。
它們的作用是讓 `apmib_init()` 能起來 —— 不是讓注入成立。注入成立的證據是
`qemu` 自己的 syscall trace 裡的 `execve`，執行的是**廠商 `boa` 二進位**
`sprintf` 出來的字串。合成的區段裡沒有任何東西參與那一行。

而且有一個更硬的檢驗：**廠商自己的 `flash default` 把我合成的 `H601` 蓋掉了**，
用它自己編譯進去的預設值（payload 從全零變成 71 個非零 byte，checksum 仍然平衡）。
所以我的合成塊實際上只是個**鷹架**，讓廠商的程式跑到能寫自己的預設值那一步。

**反過來說，這件事本身就是發現**：公開映像裡沒有 flash 的前 64 KiB，
所以「下載映像丟進 qemu 就能跑」對這個 SDK 是假的，而這是有人量過的，不是傳說。

</details>

### Q19.3 「39 個 handler 一發請求就讓 web server 消失」—— 這是 qemu 的問題還是韌體的問題？你自己說 qemu 會對未對齊存取丟 SIGBUS。

<details><summary>答案</summary>

**現在的答案是「不知道，而工具的欄位名就叫 `died_under_emulation`」。這個質疑我沒有反駁，我把它寫進了報告的必填欄位。**

三件事讓它不只是「qemu 壞掉」：

1. **它會分辨。** 19 個存活，39 個死。如果是 qemu 對這個二進位普遍不耐受，
   不會有這種分佈。對照組也成立：真 handler 200 且存活、假 handler 404。
2. **換掉設定不改變結果。** L2 環境用的是我合成的全零 MIB，unit-2018 環境用的是
   這台真實的 flash。九個在前者死掉的，八個在後者也死掉 —— 所以**不是我的空設定
   造成的**。（唯一的例外是 `formWep`，它在真設定下活著，那一個確實是設定相關。）
3. **實機上有一個對應的觀測。** W06 在真機上量到一發格式良好的未認證 POST
   讓 `boa` 永久消失（`docs/disclosure.md` D-11），但當時說不出是哪一類 handler。

**但這三件事加起來仍然不等於「這 39 個在矽上會死」。** 實機的 MIPS kernel 會在
trap handler 裡修掉未對齊存取，qemu-user 不會，而那個差異正好就在這條路徑上 ——
同一天我還量到廠商自己的 `flash default` 在 qemu 下 SIGBUS、在實機上顯然不會。

所以它是**候選清單**，下一次 bench session 從裡面挑幾個去打實機。
`formWsc` 是第一順位，因為它在兩個 profile 下都死，而 W06 對它開過火卻沒有
記錄伺服器是否存活。

</details>

### Q19.4 同一個量測你跑了四次才對。那我為什麼要相信第四次？

<details><summary>答案</summary>

**因為前三次的錯是被「兩次跑同一個量測結果不一致」抓到的，不是被我覺得數字不對抓到的 —— 而第四次沒有那個症狀。**

前三次分別給 1/58、31/58、18/58。三個都排版整齊、都有對照、都看起來像資料。
**沒有一個數字本身不合理。**

抓到它的線索是：`formSysCmd` 在一次跑裡 `302`、在一小時後的另一次跑裡 `404`。
一個 handler 在不在分派表裡不會隨時間改變，所以至少有一次是錯的。追下去發現
`boa` 會 daemonise、pidfile 存的是啟動器的 pid 而不是持有 socket 的那個，
`stop` 一直在殺一個已經結束的行程並回報成功 —— 一輪掃描累積了 **32 個孤兒**，
而 port 被其中隨機一個持有。

**最難堪的一點**：`serve` 的對照從頭到尾都通過。因為它驗的是
「port 上有東西回應正確」，那是 **port 的性質，不是它自己啟動的那個 process 的性質**。
現在它比對 `/proc/<listener>/root`。

第四次的差別是可檢驗的：39 次重啟、**0 次失敗**、58 個端點全跑完、
`formSysCmd` 這次是 200 而且在後續跑裡穩定。**這個 repo 的第一條規則是
「沒有單一工具的主張」；這次學到它有一個兄弟：沒有單一次執行的主張。**

</details>

### Q19.5 你這一節列了九個儀器 bug，其中六個是你今天自己寫的程式碼裡的。那你今天寫的東西還能信嗎？

<details><summary>答案</summary>

**能信的部分是「被對照抓到過的部分」，而這正是為什麼要數。**

六個新 bug 分佈得很說明問題：
- 兩個（32、33）是**工具讀不到它宣稱讀了的東西**，然後照樣給答案；
- 兩個（34、36）是**守衛本身**壞掉 —— 36 號更難看，它是為了修 34 號寫的，
  結果讓 `serve` 靜默退出，一小時內它比它要修的那個 bug 更糟；
- 一個（35）是**加了第二個 profile 才出現的**：`reset` 清掉的是主機全域的
  SysV IPC，會把另一個 profile 正在跑的 `boa` 弄成死循環；
- 一個（31）是**檢查器被自己的說明文件打敗**。

**如果今天寫了五支新儀器而一個 bug 都沒找到，那才是應該擔心的**，因為這個
repo 前面 27 個 bug 的紀錄說明基準率不是零。真正的問題不是「有沒有 bug」，
而是「有沒有一個對照會在它們身上失敗」。

31 號那個現在有了守衛案例（29 → 30 條），而且我**先看著它失敗、再讓它通過**。
32 號現在是拒絕執行而不是跳過。34 號現在比對 `/proc/<pid>/root`。
35 號現在會拒絕在另一個 profile 還在跑的時候動手。

**沒有守衛案例的是 33 和 36**，那是這一節誠實的缺口，寫在這裡而不是被略過。

</details>

### Q19.6 你說 14 個「孤島端點」，聽起來很唬人。裡面有幾個真的有東西？

<details><summary>答案</summary>

**大概零個，而我在同一段裡就把它講掉了。**

14 個裡面 **13 個只吃 `submit-url`** —— 那是 W06 已經在這台上量過並且反證掉的
類別（`P4-1`、`P4-3`）。一個孤島端點的意思是「這個 handler 沒有選單入口」，
不是「這個 handler 藏著秘密」。

而且真正有意思的那一個 —— `syscmd.htm` 指向一個 V2.1.2 分派表裡不存在的
`formSysCmd` —— **是 W04-2 手工找到的，不是這次的功勞**
（`notes/w6cg-web-ui.md`：「廠商出貨的表單 POST 到一個 404」）。

這次新增的是**機械化與反方向**：兩個 build 加起來有 **10 個頁面 POST 到不存在的
handler**，所以那不是一個奇例而是一個模式。以及 2015 的 UI 就已經帶著一個
2018 才出現的 handler 的頁面。

**把「14 個孤島」講成 14 個發現，是我在寫這一段時最想做而沒有做的事。**

</details>

## 20. W07 Day 2：一個不用密碼的繞過、一支正確而不可達的驗證器，以及一個在我手上消失的檔案

### Q20.1 空使用者名稱加空密碼就進得去 —— 你只在模擬器上打到。憑什麼說這是真的？

<details><summary>答案</summary>

**憑不了，而 note 裡「尚未確立」那一節寫得比發現本身長，就是因為憑不了。**

能說的是這三件事：

1. **機制是讀出來的，不是猜的。** `process_header_end` 整支 1,964 bytes，碰到
   `sp+0x18` 和 `sp+0x38` 的指令只有三個讀取 —— `addiu a1,sp,0x18`、
   `lb v0,0x38(sp)`、`addiu a1,sp,0x38`。沒有 `sw`、沒有 `sb`、沒有 `sh`、
   沒有 `apmib_get`、沒有 `strcpy`。這一句跟模擬器無關。
2. **兩個 profile 都成立**，其中一個是任何人下載得到的 V2.1.2，binary 不同、
   flash 是 `mkflash` 合成的、沒有用到任何 dump。
3. **對照組是硬的**：儲存密碼是 `admin`，當場用原廠 `/bin/flash` 讀回來確認
   非空；`admin:wrong` 回 302，無認證回 302，空使用者帶密碼回 302。所以不是
   「什麼都放行」。

不能說的是**那塊堆疊在矽上也是零**。我寫了一個理由 —— 那是請求路徑上最深的
框架，Linux 給的是清零的堆疊頁 —— 但**那是一個機制故事，不是一次量測**，
而這個 repo 對機制故事的處理方式是把它標成機制故事。

**驗證成本是三個請求、不用斷電、不寫任何東西**，而它排在下一次進站的第一項。
如果它在矽上不成立，那 `D-15` 就從「最嚴重的一列」變成「模擬環境與裝置不一致的
第二個例子」，而後者也是一個值得記的結果。

</details>

### Q20.2 `check_host` 你先說「不存在」、再說「存在而且會回 400」、最後說「不可達」。三個版本，我該信哪一個？

<details><summary>答案</summary>

**信第三個，而前兩個為什麼錯是這一題真正的內容。**

第一版說不存在，是因為我用字串找。`HOST` 這個字串在 `process_option_line`
`0x0040b918`，那裡把值存進 `req+0x60` 之後什麼都不做。**`check_host` 自己一個
字串常數都沒有**，所以字串驅動的搜尋找不到它。

抓到這個錯的不是工具，是 `notes/auth-flow-2018.md` —— W04-2 寫的，它的授權路徑
那一行早就寫著 `check_host` → `apmib_get(0xb6)` → …。**如果我寫下「這台沒有
`check_host`」，我會跟同一個 repo 裡講同一個函式的另一份 note 打架。**

第二版說它會擋，是因為讀完 `check_host` 本體（嚴格的主機名語法檢查）和呼叫端
（`bgtz` 失敗 → `send_r_bad_request`），然後**認定模擬環境上十七個 Host 全過是
測試寫壞了**。它不是。

第三版是對的，而決定它的分支在呼叫的**六個指令之前**：

```
0040bbec  beq v0,zero,0x0040bcd8      ; vhost_root == NULL -> 跳過整個 host 區塊
```

而 `VHostRoot` 在出廠 `boa.conf.bak` 和執行時的 `/var/boa.conf` **都是註解掉的**。

**教訓不是「要讀呼叫端」那種空話，是這句：一支正確而不可達的函式，讀起來跟一支
正確的函式一模一樣。** 兩者的差別不在函式裡。

</details>

### Q20.3 `miniigd` 那條你自己說「幾乎確定是 CVE-2014-8361」。那你到底做了什麼？

<details><summary>答案</summary>

**把一個 2014 年的 KEV 漏洞，定位在一個 2018 年的 build 裡，指到那個 `system()`
的位址。這是驗證，不是發現，而 note 和 `D-16` 兩邊都是這樣寫的。**

具體做了三件別人不一定會做的事：

1. **它是從 `callers:system` 算出來的，不是從字串猜的。** `miniigd` 裡七個
   `system()` 呼叫者全部列在 note 裡，包括那些只跑常數 `iptables` 的。
   一份只列「危險的那一個」的清單，讀者無法判斷你有沒有漏掉別的。
2. **修正了一個會讓整條線消失的錯誤。** 手冊寫的 SOAP 端點是
   `/upnp/control/WANIPConn1`，那是 `miniupnpd` 的；**這支 binary 是
   `/upnp/control/WANIPConnection`**。照手冊探測會拿到乾淨的 404，然後把
   「沒有 UPnP 控制面」寫進紀錄 —— 而 52869 整段時間都開著。
3. **同一條路徑上還有一個沒被 CVE 講到的 `strcpy`**（`0x0040851c`），無界，
   吃的是同一批 SOAP 值。

而最誠實的一句是：**這台上 52869 開著這件事，是 W05 的埠掃描發現的，而當時
沒有任何一條預測提到它。** 我這一週做的是去讀那個埠後面是什麼。

</details>

### Q20.4 `bughunt.md` 十九列，聽起來很多。裡面有幾列是你這一週做出來的？

<details><summary>答案</summary>

**八列，而其中四列的判定欄是問號。**

拆開來看：

| 來源 | 列 |
|---|---|
| 這一週新做 | 4（miniigd）、5（憑證對）、9（`check_host`）、10（open redirect）、11（XSS 類）、12（RFW）、13（映像驗收）、14（dnsspoof） |
| 之前的週次 | 1、2、3、6、7、8、16、17、18、19 |
| 判定是 `?`（機制成立、效果未演示） | 4、11、12、14，加上 15 的 partial |

所以**這一週的八列裡有五列沒有在任何硬體上執行過**。那不是把表灌大，是這一週
刻意不碰硬體的直接後果 —— 而如果我把它們記成 `partial`，`make todo` 會把它們
算成完成，然後欠的活就從清單上消失了。**這正是我沒有那樣做的理由。**

還有一件事：十九列裡**有兩列是本專案自己撤回或反證掉的發現**（18、19），
另外一列（9）是一個看起來存在而其實不存在的防護。一張只會長不會縮的表，
是沒有人在查的表。

</details>

### Q20.5 你說一個檔案在你手上從解開的 rootfs 裡消失了。那你怎麼知道別的東西沒被動過？

<details><summary>答案</summary>

**這一題問到點上了，而正確答案是：我本來不知道，而且這個 repo 沒有任何東西
會告訴我。**

事實是：`bin/miniigd` 被 `ls` 到、被 `strings` 讀過，二十分鐘後 `cp` 說找不到，
而模擬環境裡那份還在。我做的是**重新 `unsquashfs` 一次 `rootfs.squashfs`**，
然後比對三個東西的 SHA-256：新解出來的、環境裡那份、還原後的。三個相同。

所以那一個檔案沒問題。**但「別的東西」我當下答不出來**，而我發現我答不出來的
方式是一個因為別的理由失敗的 `cp` —— 那是運氣。

真正的缺口寫在 `PROGRESS.md` 儀器 bug 39 和開放問題 56：**這個 repo 沒有任何
檢查會確認解開的樹仍然吻合它來自的 SquashFS。** 一棵少了一個檔案的樹，跟一棵
完好的樹，在所有現有檢查眼裡長得一模一樣。而解開的 rootfs 一直被當成證據用，
它其實是衍生資料 —— 證據是 `rootfs.squashfs` 和它背後那份 flash dump。

**我不知道是什麼刪掉它的**，那段期間對那條路徑只有 `strings`、`readelf` 和一次
失敗的 Ghidra 匯入。猜一個原因比寫「不知道」更糟。

</details>

### Q20.6 你說 2020 版把那對憑證緩衝區修掉了。那個 binary 是 `sstrip` 過的，函式沒有名字 —— 你怎麼知道你讀的是同一個函式？

<details><summary>答案</summary>

**靠三件互相獨立的事對上，而且每一件單獨都不夠。**

1. **定位方式是字串，而且是同一個字串。** `FUN_00409fd8` 是用 `host invalid!`
   找到的 —— 2018 版的 `process_header_end` 裡也有這個字串，而它在整個 binary
   裡只出現在授權路徑上。
2. **它的字串集合是同一組，而且順序一樣**：`No logline in process_header_end`、
   `URI contains bogus characters`、`unable to strdup default_vhost/req->header_host`、
   `host invalid!`、然後 `.htm`、`.asp`、豁免清單。第一個字串裡**就寫著函式的
   名字**，那是廠商自己的除錯訊息。
3. **它做同一件事**：`apmib_get(0xb6)` 和 `apmib_get(0xb7)` 進兩個堆疊槽，
   然後用它們比對，然後設 `req->0xb0`。MIB 編號 `0xb6`/`0xb7` 是 W04 從
   `libapmib` 的表獨立還原出來的，跟這次的定位無關。

**而反過來的檢查也做了**：那支函式裡每一個被載進 `a1` 的堆疊位址，不是那兩個
`strcmp` 的參數，就是一個 `apmib_get` 的目的地（`sp+0x24`、`sp+0x20`、
`sp+0x1c`，MIB `0xc5`/`0xaa`/`0xab`，那是下面另一個功能）。**沒有第三個
「只被讀、沒被寫」的槽。** 那句「2020 沒有」如果錯，錯的方式會是我漏看了一個
沒有被載進 `a1` 的存取路徑，而那要用 mnemonic 直方圖去掃，不是用眼睛。

這一條的**份量也要講清楚**：它是靜態的，而且它縮小的是別人（2020 版使用者）的
風險，不是這台的。這台仍然有。

</details>

---

## 21. W07 Day 3：一份公開的原廠原始碼、一個開機十分鐘後就失效的 session，以及我自己造出來的兩個儀器 bug

### Q21.1 你花了四個月讀二進位，然後今天才發現這顆 SDK 的原始碼一直公開在 GitHub 上？

<details><summary>答案</summary>

**對，而且這是今天最該記下來的一件事，不是最該辯解的一件事。**

`docs/disclosure.md` 步驟 2 的規則是「**按 handler 名搜，不要按產品名搜**」——
那條規則本身是 `D-1` 教出來的：按產品搜回來一片空白，按 handler 搜第一頁就是
Cisco Talos。規則是對的，**但它太窄**。它教你怎麼找**公告**，沒教你怎麼找
**原始碼**。

今天真正管用的那一次查詢是**按符號名**搜：`process_header_end`、
`MIB_SUPER_NAME`、`check_auth_flag`。回來的是兩個**不同廠商**的 GPL drop
（Actiontec 的 `WECB-0.16.8.4-GPL.tgz`，以及另一份 rtl819x SDK），
裡面就有 `users/boa/src/request.c` 和 `apmib/apmib.h`。

**為什麼會漏掉：這個專案的整個心智模型是「廠商不給原始碼，所以我讀二進位」。**
那句話對 TOTOLINK 成立，對**這顆 SDK**不成立 —— 它授權給幾十個品牌，
其中有人依 GPL 放出來了。從來沒有人問過這個問題。

規則已經改成步驟 2a：**按符號搜找到原始碼，按 handler 搜找到公告，按產品搜
什麼都找不到。三種都便宜，而且沒有一種可以取代另一種。**

</details>

### Q21.2 你拿別家廠商的原始碼來解釋這台的二進位，憑什麼說那是同一份程式？

<details><summary>答案</summary>

**不能直接說，而且這個限制要跟著每一次引用一起走。** 那不是 TOTOLINK 的
drop，所以它們一致只能證明**這顆 SDK 的血緣**，不能證明 TOTOLINK 做了什麼。

真正撐住這個對應的是**三件互相獨立的事**：

1. **控制流一模一樣。** 原始碼是「四個 `apmib_get` → 先比 SUPER 那對、設
   `auth_flag = 2` → 再比 USER 那對、設 `1`」。這台的指令是
   `apmib_get(0xb6)`、`apmib_get(0xb7)`，然後 `strcmp` 對 `sp+0x18` 設 2、
   `strcmp` 對 `sp+0x58` 設 1 —— **順序、層級、分支形狀全部對上**。
2. **MIB 編號對得上，而且對照表是這台自己的。** `apmib.h` 說 `USER_NAME` 是
   182、`USER_PASSWORD` 是 183。這個專案 W04 從**這台自己的 `libapmib.so`**
   還原出來的表，182 和 183 就是這兩個名字。**那張表在今天之前，從來沒有被
   repo 以外的任何來源驗證過。** 這是雙向的：原始碼佐證了表，表也佐證了原始碼。
3. **少掉的那兩個呼叫是可量的，不是推論的。** 掃指令編碼找 `addiu $a0,$zero,0xb4`
   和 `0xb5`（180/181）—— **三個 build 全部零命中**，而 `0xb6`/`0xb7`
   命中 5–8 處。那個掃描有正對照：如果解碼壞了，182/183 也會是零。

**它不能證明什麼**：不能證明 TOTOLINK 拿的是這個版本、不能證明他們是「刻意」
刪掉那兩行、也不能證明其他廠商的 build 也長這樣。這三件事我一件都沒說。

</details>

### Q21.3 你說 39 個 handler 的死亡是模擬器造成的。那你之前那份報告不就是廢的？

<details><summary>答案</summary>

**那份報告的數字沒錯，錯的是它可以被讀成什麼。而工具自己早就講了。**

`handler-sweep.py` 把欄位命名成 `died_under_emulation`，而且在 JSON 裡帶了一句
「這**不是**關於裝置的主張；`qemu-user` 在 MIPS 核心會修補的地方丟 SIGBUS」。
所以工具是誠實的。**不夠的是誠實。**

今天做的是把那句警告變成一個量測：`gdb-multiarch` 接上 `qemu-mips-static` 的
gdbstub，讓故障當場發生，拿到
`=> 0x2b2c87dc: sh s7,0(s8)`，位置是 `libapmib.so + 0x27d0`，函式是
`mib_write_to_raw` —— TLV 打包器，變長記錄，偏移天生是奇數。

**於是那 39 個的共同點被講清楚了：它們不是脆弱，是「會存設定」。**
19 個「活著」的是參數不夠、提早返回、根本沒走到序列化器。`formSysCmd`
在活著那一組裡，本來看起來像個巧合，現在是必然。

`bughunt.md` 第 16 列因此**撤回**。這是這個專案第三個自己撤回的發現，
而它跟前兩個不一樣的地方是：**它不是靠爭論那句警告撤回的，是靠造一支能分辨
「模擬器的行為」和「韌體的行為」的儀器撤回的。**

**還有一個副產品**：`P8-24` 那個「復原寫入不可觀測」也是同一行造成的。
兩個分開記錄的觀察是同一個 bug。

</details>

### Q21.4 那支 `alignfix` shim 不就是在作弊嗎？你自己改了環境，然後說結果不一樣

<details><summary>答案</summary>

**這是今天最該被問的一題，而答案有三層。**

**第一層：它加的東西，裝置本來就有。** MIPS Linux 核心在 trap handler 裡替
使用者空間補完未對齊存取，這是核心行為不是選項。`qemu-user` 沒有實作那一段。
所以這支 shim 拿掉的是**模擬器對目標的一個偏離**，不是加上目標沒有的能力。

**第二層：它預設關閉，而且會說自己是哪個模式。** 打開它會改變這個環境「是
什麼」。2026-08-18 之前所有模擬量測都是在沒有它的情況下取得的，profile 的
陽性對照也是。一個安靜改掉這件事的旗標，會讓兩個不能並列的東西看起來像同一個。
`tools/test-alignfix.sh` 有一個案例就是在守這件事：**如果未來有人把預設改成
開，CI 會紅。**

**第三層，也是最重要的：它會拒絕，不會猜。** o32 的 `ucontext` 偏移是寫死的，
而寫錯的偏移會產生看起來很合理的垃圾 —— 它會安靜地改壞暫存器，然後程式繼續跑，
產生一堆你無法分辨真假的結果。所以 handler 在動任何暫存器之前檢查兩次：

1. 把復原出來的 `pc` 讀回去，那道指令必須解得出五種可修補形式之一；
2. 用復原出來的暫存器算出的位址，**必須真的沒對齊**。

任一項不過，它就把 `SIG_DFL` 裝回去，讓程序照原本的方式死掉。守衛套件會編一支
**故意寫錯偏移**的版本來證明那條路真的走得到。

**而且它會報帳。** 每次修補都記位址，一次 `formNtp` POST 修 24 次、全部同一個
`pc`、每一個位址都是奇數。一個讀者可以自己確認那些修補全部落在序列化器裡，
而不是落在一個真的 bug 會出現的地方。

</details>

### Q21.5 你今天自己造了兩個儀器 bug。那你的「先讓它失敗一次再相信它」是不是講講而已？

<details><summary>答案</summary>

**兩個都是我造的，兩個都被既有的對照組當場抓到，而第二個花了兩輪掃描才看懂。
兩件事都要講。**

**bug 41：修好崩潰，順手拿掉一個靠崩潰撐著的保證。** 之前每次探測後 handler
都會死，死了就重啟，重啟裡面有 `reset` —— 所以「每次探測都從乾淨的 flash 開始」
**是崩潰的副作用，從來不是刻意設計的性質**。`--alignfix` 打開之後不崩了，
那個保證就沒了，探測 N 讀到的是探測 1..N-1 寫下去的東西。
**抓到它的是 profile 自己的陽性對照**：下一次 `check` 回 `USER_NAME=""`
而不是 `"admin"`。三個值，用廠商自己的 binary 讀回來，一分鐘之內就紅了。

**bug 42：`reset` 還原 flash 和 SysV 段，不還原 `/var`。** handler 開始能寫
之後，其中一個重跑了 `sysconf` 的 `cp -a /etc/boa/boa.conf.bak /var/boa.conf`
那一半，**但沒有補上 `build` 會追加的 `echo 'Port 80' >>`**。runtime 設定檔
變回全部註解掉的上游樣板，`serve` 的 `sed s/^Port .*/` 比對不到，`boa` 綁到
port 0。**而環境自己說它很健康** —— `check` 三個控制全過，因為 flash 真的沒事。
問題不在 flash。

**這一個我花了兩輪掃描才看懂**，而看懂它的方式是把 `boa: starting server
pid=…, port 0` 這一行讀進去 —— 它一直印在 log 裡。

**所以「先讓它失敗一次」有沒有用？有，而且用的方式跟我預期的不一樣。**
它抓到的不是我寫工具時想像的那些失敗，是**修好一個東西之後才長出來的**失敗。
三個 bug（40、41、42）共用一句話：**一個還原只值它那份清單的價值，而那份
清單在有東西開始寫之前，永遠不會有人回頭看。**

</details>

### Q21.6 那個「開機 601 秒後 session 就死掉」的東西，你怎麼確定 `beforeuptime` 真的沒人寫？Ghidra 漏一個參照，跟「沒有參照」長得一模一樣

<details><summary>答案</summary>

**這正是為什麼今天多了一支工具，而不是多了一個結論。**

`BoaXref` 的 `refs:` 用 Ghidra 的參照模型回答，答案是「一次讀、零次寫」。
**那是一個工具的說法。** 所以寫了 `tools/mipsref.py`：它沒有符號表、沒有分析
資料庫、沒有參照模型，只解指令編碼，跟 Ghidra 沒有共用任何東西。

它掃**三種定址**，因為漏掉任何一種都會長得跟「乾淨」一模一樣：

1. `lui r,%hi(a)` 配上帶 `%lo(a)` 的 load/store；
2. **`gp` 相對** —— 而 `gp` 不是跟 Ghidra 要的，是從 ELF 自己的 `PT_DYNAMIC`
   算 `DT_PLTGOT + 0x7ff0`。這台是 `sstrip` 過的，`readelf -S` 什麼都回不出來，
   但 segment 還在，所以這條路走得通；
3. `$zero` 絕對定址。

**而 `--control` 是重點不是選項。** 它要求一個指定的位址**必須**回報至少一次讀
和一次寫。這次用的是 `nowuptime`（`0x004899e0`），它就在 `beforeuptime` 隔壁，
而且我從指令上已經看到它被寫也被讀。控制組回 1 讀 1 寫 → 解碼、`gp`、
file offset 換算三件事都是對的 → `beforeuptime` 的 1 讀 0 寫才有意義。
**解錯任何一件，控制組會回零，工具 exit 2,而不是印一個很有自信的空答案。**

**還有一個誠實的缺口要講**：`beforeuptime` 是 `boa` 的 process-local 全域，
所以理論上不可能被別的程序寫。但**同一套推理**在 `check_auth_flag` 上也講得通，
而那一個我還是去量了 —— 量它只要一個指令。所以這一條列在開放題 62,而不是
寫成「不可能」。

</details>

### Q21.7 你今天沒有關掉任何一項登記簿的案子。那這一場到底算什麼？

<details><summary>答案</summary>

**算一場把三個既有結論改寫掉的桌面工作，而它沒有資格算成「進度」。**

誠實的帳是這樣：

- **改寫**：`D-15` 的機制（未初始化 → 被刪掉的 supervisor 帳號）、
  `bughunt.md` 第 16 列（撤回）、第 13 列（有 CVE，不是我們的）。
- **新增**：`D-18`（IP session），以及開放題 58–62。
- **關掉**：**零。**

**為什麼零：** `P4`/`P5` 那一批的輸入是帶 `--alignfix` 重跑的端點掃描，而它
今天被我自己造的兩個儀器 bug 打斷兩次，收工前沒跑完。把 `P5-3`、`P5-7`、
`P1-9`、`P3-8`…`P3-12` 的靜態半邊先記進去、把 `P4`/`P5` 留到下一場，會讓
同一個下午的工作橫跨兩個 commit，而且會在另一半還沒量之前就把半週的結果寫進
登記簿。

**而進站那 32 項今天完全沒碰，那是刻意的**，理由跟 W07 Day 2 一樣：
今天長出了**三個進站前必須先凍結的新預測**，其中一個（開機 601 秒的視窗）
連作業單的步驟都還不存在。先凍結再進站，不然量到的結果照這個 repo 自己的
規則不可採納。

**這一場最該被質疑的地方，不是「零」，是「三個結論被改寫」。** 一個禮拜之內
被自己改寫三次的結論，代表前面幾次的把關不夠緊 —— 而三次裡有兩次的成因是
同一件事：**環境的限制被寫在每一個受影響的結果旁邊，而不是被環境自己宣告一次。**

</details>
