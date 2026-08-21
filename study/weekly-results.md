# 每週真正拿到的東西

> 這份跟 [`QA.md`](QA.md) 是一對:**QA 是「被問到怎麼答」,這份是「主動要講什麼」。**
>
> 規則三條:
>
> 1. **每一點都要指得回證據** —— commit、note、report,不能只有形容詞。
> 2. **每一點都要說出「它證明了什麼能力」** —— 讀者關心的是方法,不是路由器。
> 3. **每一週都要有「這週沒證明什麼」** —— 這一欄不是謙虛,是**這整個專案唯一真正稀有的東西**。
>    會做逆向的人很多,會說「我這個結論的邊界在哪」的人很少。

---

## 怎麼用這份檔案

- **要向別人講這個專案之前只讀這份。** 每週的「一句話版本」是 30 秒版,「三個點」是被追問時的深度。
- **講的時候一定要帶上限制那一欄。** 「我做了 X」和「我做了 X,而它不能證明 Y,要證明 Y 需要 Z」是兩個層級的候選人。
- **每週收工時回來補一格。** 格式在最後面。

---

## W01 — 偵察與解包(G0 + G1,2026-08-07)

### 一句話

> 「我沒有相信規格書。我從廠商自己的容器格式推導出這台的 flash **至少要 4 MB**,而公開規格寫 2 MB —— 三週後硬體到貨,是 4 MiB。」

### 三個可辯護的點

| 主張 | 證據 | 它證明我會什麼 |
|---|---|---|
| **從二進位推導出一個對物理世界的可否證預測** —— 解析 Realtek 容器的 16-byte header,把每一段的 `burnAddr` 讀出來,發現映像要 3.57 MiB,所以 2 MB 的規格不可能成立 | [`notes/anatomy-n150rt.md`](../notes/anatomy-n150rt.md)、`PROGRESS.md § Corrections` | **能從沒有文件的格式裡建立結構理解**,而且敢把結論寫成「如果我錯了,拆開會看到什麼」 |
| **拿兩個版本而不是一個** —— V2.1.2(2015-08)和 V3.4.0(2020-10),剛好夾住兩次公開揭露 | [`firmware/MANIFEST.json`](../firmware/MANIFEST.json) | **懂得選對資料集**。同樣的工作量,一個版本只能得到「這台有什麼」,兩個版本可以得到「五年之間廠商改了什麼」 |
| **寫了 `fwrecon`** —— 零執行期相依、能解析 `sstrip` 過的 ELF、Realtek 容器、rootfs 攻擊面盤點,58 個測試 | [`tools/fwrecon/`](../tools/fwrecon/) | **工具是寫出來的,不是裝出來的**。而且測試數量是為了讓它「能失敗」,不是為了覆蓋率 |

### 這週沒證明什麼

- **全部是靜態的。** 沒有任何一台裝置被通電。
- 「這台跑的是哪個版本」完全沒有答案 —— 那要等 flash dump(W02 才做到,而答案是**兩個都不是**)。
- 而且這週有一個結論後來被自己推翻:「兩份映像裡都沒有 `/etc/passwd`」是**誤判**,那是一個懸空的符號連結。W04 更正。

---

## W03 — 靜態逆向上半(DoD,2026-08-10)

### 一句話

> 「CVE 公告說的是『`.dat` 檔沒有被限制存取』。我在**指令層級**讀出來的是:授權檢查用 `strstr(uri, "htm")` 決定要不要跑 —— **所以不是 `.dat` 特別,是所有路徑裡不含 `htm` 的東西都不檢查**,包括全部 59 個表單處理器。我找到的是原因,公告寫的是症狀。」

### 三個可辯護的點

| 主張 | 證據 | 它證明我會什麼 |
|---|---|---|
| **把授權漏洞從症狀追到成因**,而且比公告描述的範圍大得多 | [`notes/auth-flow.md`](../notes/auth-flow.md);關鍵兩行組語 `jalr t9 -> strstr` / `beq v0,zero` | **能讀懂控制流,不是只會找字串**。而「範圍比公告大」這句話,只有真的讀過才敢說 |
| **在反編譯器出警告的時候,退回指令層級確認** —— 那個函式 Ghidra 給了三個警告,所以最後的判讀是用 `BoaListing.java` 逐指令看的 | [`ghidra/scripts/BoaListing.java`](../ghidra/scripts/BoaListing.java) | **知道工具什麼時候不能信**。這是初階和中階逆向的分界線 |
| **兩個工具 bug,而且是自己抓到的** —— `import.ps1` 會無聲蓋掉自己的前一次輸出;sink 普查對 `sstrip` 過的 binary 產生假陰性(589 vs **1**) | `PROGRESS.md § Two tooling bugs` | **會懷疑自己的量測**。「2020 版只有 1 個 `strcpy`」這種數字,大部分人會直接寫進報告 |

### 這週沒證明什麼

- 仍然全部是靜態的。
- `formSysCmd` 找不到,當時的解釋是「這個產品編譯時沒有加進去」—— **那是猜測**,W04 用日期把它換成一個更站得住腳的說法。
- `execl` 的參數當時寫成「由請求參數組出來」,W04 發現**每一個都是固定字串**,完全錯。

---

## W04 — CVE 根因定位(G3,2026-08-11)

### 一句話

> 「十四個 2025 年的 CVE,我把它們收斂成**三個缺陷**。其中兩個 CVE 編號指的是**同一行程式碼**,而那行在 2015 年的映像裡一模一樣 —— 比任何一個編號早十年。**CVE 的數量不等於缺陷的數量**,而分辨這件事只能靠真的去讀。」

### 三個可辯護的點

| 主張 | 證據 | 它證明我會什麼 |
|---|---|---|
| **14 個 CVE → 3 個缺陷**,其中 4 個 id 是同一個 copy-paste 慣用法,而那個慣用法出現在 **34 個** handler 裡 —— **有編號的那四個是抽樣,不是全集** | [`notes/submit-url-overflow.md`](../notes/submit-url-overflow.md) | **能看穿漏洞編號的敘事**。廠商和研究者都傾向一個現象一個編號;能收斂它們的人才知道真正要修幾個地方 |
| **緩衝區大小是從符號表讀出來的,不是估的** —— `lastUrl` 是 100 bytes,而緊接在它後面的兩個全域變數是控制旗標 | 同上 | **精確性**。「大概會溢位」和「100 bytes,後面接著 `needReboot`」是兩種可信度 |
| **新工具的三個 bug,沒有一個是它自己的自我檢查抓到的** —— 全部是靠「同一份程式碼隔五年不可能從 86 掉到 0」這個橫向比對抓到的 | `PROGRESS.md § Instrument work` | **知道自我檢查會騙人**。「一個從來不會觸發的檢查,永遠不會失敗」 |

### 這週沒證明什麼

- **全部是靜態的**,而且更嚴重:W02 後來發現這台機器跑的是**第三個 build**,所以 W03/W04 對 `boa` 的每一條結論,講的都是兩個這台裝置從來沒跑過的 binary。
- 2020 版的子字串繞過**從來沒有被執行過**。它是三個 `strstr` 呼叫的讀法,在 W05/W06 實測之前,不會送給任何人。

---

## W02 — 硬體存取(G2,2026-08-16,補做)

### 一句話

> 「我量了那支燒錄器,發現它會拿 5V 打一顆 3.3V 的片子,所以我**沒有用它** —— 改走 bootloader 自己的指令把 4 MiB 讀出來,兩趟,零差異。而那份 dump 讓我看到公開映像看不到的東西:廠商修那個 2015 年的後門,分**三步、跨五年**,而中間那一步只有從自己的矽晶片上才讀得到。」

### 三個可辯護的點

| 主張 | 證據 | 它證明我會什麼 |
|---|---|---|
| **量了工具才決定用不用它。** CH341A 的分佈是:板子拉到 VCC 的兩支跟著 3.3V,**晶片驅動的三支全部 5V** —— 座上 VCC 是 3.3V 這件事正是陷阱。風險留在三美金的板子上,不是唯一一台機器上 | `PROGRESS.md § Day 4`、[`img/13`](../notes/img/13-ch341a-clip-and-adapters.jpg) | **先驗證儀器,再拿它去量未知**。而且**懂得評估不可逆的風險**:不可替代的是那 4 MiB |
| **兩趟完整讀取,不同 RAM 暫存位址,`cmp` 零差異** —— 而且我不拿工具自己報的雜湊當數,是用 `sha256sum` 獨立重算 | `dumps/MANIFEST.json`、[`dump-vs-official.md`](../notes/dump-vs-official.md) §1 | **知道「可重現」和「正確」是兩件事**。同一條路徑讀兩次,共用它們所有的失效模式 |
| **那份 dump 抓到廠商修到一半**:2015 註解掉一行 → **2018 刪掉 binary、uid 0 的後門帳號一個 byte 沒動、那行死掉的呼叫還留在啟動腳本裡當化石** → 2020 才移除帳號 | [`dump-vs-official.md`](../notes/dump-vs-official.md) | **能從三個資料點重建一段時間線**,而且知道「找到一個洞被修好」對另一個洞什麼都沒說 |

### 這週沒證明什麼

- **沒有第二個儀器讀過這顆 flash。** 兩趟 dump 和 8/15 的窗口全部走 bootloader 的 `FLR`,**系統性錯誤對三者都是隱形的**。兩個 hash 相同證明的是傳輸和 SPI 讀取穩定,不是讀得對。
- JEDEC ID 沒讀到,卡在同一件事上。
- **2018 的 `boa` 抽出來了、算了雜湊,但還沒讀。** 在它進 Ghidra 之前,這個 repo 裡每一條關於 `boa` 的結論,講的仍然是兩個這台沒跑過的 binary。

---

## 跨週的那一條線(這是最值錢的一段)

單週的成果會被問「那又怎樣」,**跨週的模式不會**。

### 十個工具 bug,沒有一個是工具自己的自我檢查抓到的

| # | 週 | 它長什麼樣 | 誰抓到的 |
|---|---|---|---|
| 1–2 | W03 | 匯入無聲蓋掉前一次;`sstrip` 的 PLT 造成假陰性(589 vs 1) | 橫向比對兩個 build |
| 3–5 | W04 | 參數追蹤器三個 bug,`self_check` 全程說 `consistent` | 同上(86 → 0 不可能) |
| 4–6 | W02 D1 | 守衛套件 5/5 綠燈,而每次呼叫都死在 `import PIL` | 那個「必須成功」的對照案例 |
| 7 | W02 D4 | ESC 塞滿 bootloader 的輸入緩衝區,第一條指令必定失敗 | 跟前一場 session 的結果矛盾 |
| 8 | W02 D4 | 解析器照**筆記裡的引用**寫,少了 ASCII 欄,判掉裝置吐的每一行 | 陽性對照 |
| 9 | W02 D4 | 那個解析器的守衛套件 10/10 全綠 —— 它驗的是裝置不會產生的格式 | 真機第一次跑 |
| 10 | W02 D4 | 監看程式每 10 分鐘安靜失敗一次(寫到 stderr) | 進度一直沒出現 |

**規律:每一個都是「兩個應該一致的東西不一致」抓到的,沒有一個是自我檢查抓到的。**

> 對外講法:「我從這個專案學到最重要的一件事,不是逆向技巧,是**一個不會失敗的檢查等於沒有檢查**。我有十個工具 bug 的紀錄,沒有一個是工具自己發現的 —— 全部是靠交叉比對。所以我現在寫工具的時候,第一件事是想『它錯的時候會長什麼樣』。」

### 三次「預測寫在前面,然後被物理世界驗證」

| 預測 | 何時寫的 | 結果 |
|---|---|---|
| flash ≥ 4 MB(公開規格說 2 MB) | W01,硬體到貨前三週 | ✅ 4 MiB |
| 三個燒錄位址 `0x010000` / `0x060000` / `0x180000` | W01,從廠商容器推導 | ✅ 三個全中,而且中在一個**沒人看過的 build** 上 |
| 板子的日期碼指向 2018 年前後 | W02 Day 1,通電之前 | ✅ 2018-01-10 |

**「先寫下來,再去量」這個順序本身就是可展示的技能** —— 它讓每一個結論都變成可否證的。

---

## W04-2 — 補課週:把結論搬到這台真的在跑的 binary 上(G3.5,2026-08-16)

### 一句話

> 「我花了兩週逆向這台路由器的 web server,然後 W02 把 flash 讀出來,發現**這台跑的
> 是第三個 build,我讀的兩個它從來沒執行過**。這一週是把每一條結論一條一條搬過去,
> 而且第一個小時就有一條被推翻:**有一個命令執行的 handler 只存在於這台跑的那個
> build 裡,兩個下載得到的映像都沒有它。**」

### 三個可辯護的點

| 主張 | 證據 | 它證明我會什麼 |
|---|---|---|
| **`formSysCmd` 在這台的分派表裡,兩個公開映像都沒有** | `grep -aoc` 三個 raw binary:**0 / 1 / 0**;`BoaFormTable` 給出 entry `0x004838a8` → handler `0x0044ee2c`;`BoaGate` 從完全不同的路徑在 `0x0044ef2c` 再抓到一次 | **三個不共用程式碼的來源**。而且我因此收回了自己上一週寫進 gate 驗收欄的一句話 —— 「缺席 → 出現 → 缺席」不可能是修補 |
| **一個已公開 CVE 的官方評分向量,和它自己的揭露者矛盾** | CVE-2024-51228 指名 `TOTOLINK-CX-N150RT V2.1.6-B20171121.1002`(= 這台的 `/etc/version`),NVD 評 `PR:H`/6.8;**原始揭露者寫「without credentials」**,而我從 binary 在指令層級讀出來也是完全不經授權 | 我不是複述公告,是**獨立從韌體推導**出跟公告記錄不一致的東西。三個來源裡兩個對上,而對不上的那個是評分向量 —— 這個專案已經抓到過兩次同類的抄寫錯誤(3992、3995 指名的端點會 404) |
| **`TELNET_ENABLED = 0`,所以 `root:123456` 不是入口** | 設定區解出來是 0;`/bin/sysconf` 的 `FUN_00403400 → apmib_get(0xbbb)` 決定要不要 `system("telnetd &")` | **我會把自己的發現講小。** 這是整個專案最誘人誇大的一條,而正確講法是「提權鏈的第二段」,差整整一步 |

### 這週沒證明什麼

- **我重新發現了一個 2024 年就公開的 CVE,而且不知道它公開過。** CVE-2024-51228 指名這台的 build 字串。`notes/prior-art.md` 的清單是 2015 / 2019 / 2025,**2024 整年空白** —— 因為那份調查是繞著「我已經知道的揭露事件」組織的,不是繞著產品。更難看的是:W02 兩週前就讀到 build 字串了,**沒有人拿它去搜尋**。那個 CVE 是專案作者貼連結進來才被找到的。
- **一個 request 都沒送出去。** 全部是靜態閱讀。那條 RCE 鏈的每一句話都是「程式碼讀起來是 X」,`/tmp/syscmd.log` 沒有人看過,port 沒有人掃過。而那個 `PR:H → PR:N` 的評分修正,**在實機證實之前值零**,否則它只是另一個抄來的向量。
- **G3.5 沒過,五條裡缺第五條。** `FLW` 回復路徑演練需要人和萬用電表,我沒做。**W05 不准開始**,因為 W06 的 PoC 必然寫 flash,而這台的回復路徑從來沒被執行過。
- **`lwl` 的答案是不對稱的,而且我只拿到弱的那一半。** 這台跑的 binary 裡有 142 個 unaligned 指令 —— 但**沒有任何證據顯示其中一個真的被執行過**,同一份韌體裡的 busybox 是 0。「有 = 證明」只在它跑得到的前提下成立,而那個前提還沒驗。
- **公開的 V2.1.6 抓下來了,但只有 40%,所以「這台的 `boa` 跟公開版差在哪」我還是不知道。** 抓到的是 `B20160516`,這台是 `B20171121` —— 同版本號、差十八個月的兩個 build。完整的兩段是 web UI 和 kernel,**截斷的正好是 rootfs**,也就是 `/etc/version`、`boa`、`root_form[]` 住的地方。重抓的判準已經先寫死:CRC-32 要等於 `0xd20c0622`。
- **而我為那個鏡像寫的第一個「沒被動過」的論證是錯的。** 我拿三個 build 的 kernel 長度剛好各差 1,024 bytes 當證據 —— 把第四個 build 拿進來算才發現四個全部 ≡ 2 (mod 1024),那是 1 KiB 對齊的網格,是**容器格式的性質**,不是這幾個檔案的性質。**三個點看起來是趨勢,四個點才看得出那是格線。** 這個專案前面每一次「兩個東西該一致所以我去比」抓到的都是工具在騙我,這次是我自己的論證,而且沒有任何工具會抓到它。
- **`system()` 呼叫點 158 → 194 → 129,多出來的 ~34 個我解釋不了。** `formSysCmd` 只佔一兩個。
- **`BoaGate` 只在單一函式內追緩衝區。** 傳給 helper 就追丟了,所以那些數字是**下限**,不是總數 —— 這一點寫在腳本的註解裡,因為一個會高估的閘門沒有人會繼續跑。

### 補課時追加的一條,而它比上面三條都硬

**廠商實際出貨的網頁,跟 binary 講的是反的。** 這個專案從頭到尾只 grep 過
`boa` 執行檔(`formSysCmd` = 0 / 1 / 0),沒有人打開過那個會 POST 到它的網頁。
`w6cg` 的封裝格式是 W01 列為「解開了但沒 parse」的未打勾項目,擺了兩週。

| | 2015 V2.1.2 | 2016 B20160516 | 這台 2018 |
|---|---|---|---|
| `syscmd.htm`(出貨的頁面) | **在**,3,835 bytes | **在,逐 byte 相同** | **不在** |
| `boa` 的 `root_form[]` 有沒有這條路由 | **沒有** | 不知道(rootfs 截斷) | **有**,`0x004838a8` |

**2015/2016 出貨頁面、沒出貨路由(表單照程式碼讀是打到 404);2018 出貨路由、
沒出貨頁面。** 所以廠商 2015 對 Pierre Kim 的回應是**修一半** ——
跟「`#skt&` 註解掉但 binary 照樣出貨」、「`onlime_r` 留在 `passwd.org`」
同一個手勢,一次揭露三個洞、三次都修一半。而 CVE-2024-51228 揭露者公告裡那句
被當成廢話的括號 *"even if the GUI (`syscmd.htm`) is not available"*,
現在下面有一組量出來的 before/after。

**這條沒證明什麼:**

- **2016 那個 build 的 `boa` 我沒讀到。** rootfs 被截斷,那一格寫「不知道」,
  不是從 2015 推過去的。
- **2018 的移除不是外科手術。** 2015→2018 掉 27 筆、加 26 筆、117 個同名檔有
  60 個內容變了。`syscmd.htm` 是被整包改版帶走的,把它讀成「針對性移除」
  就是在對一次改版讀心。
- **2018 為什麼路由會回來,我完全解釋不了。** 寫在 `PROGRESS.md` 開放問題 #11。
- **而我在這一段差點拿一個 substring 去推翻自己一句正確的結論** —— 用整塊
  grep 在 2018 那份裡「找到」了 `syscmd.htm`,其實是 `language_*.js` 裡的一行
  註解。**檔名出現在某個檔案裡,不等於那個檔案存在。**

### 這一週最該拿出來講的一件事,不是找到的洞

**新寫的 CI 閘門,第一次跑在 V2.1.2 上回報 0 findings** —— 而那個 build 我上一週親手讀出 34 個有問題的 handler。**兩次,兩個不同的原因**,而且兩次都會以「這個 build 很乾淨」的形式出貨:先是用名字比對 sink,但 libc 是走 `sstrip` 過的 PLT(這個專案**第三次**踩同一個坑);修掉之後,字面值解析只檢查 `isConstant()`,而 MIPS 的字串位址是 lui/addiu 湊的,所以一個參數名字都沒讀到。

前兩次這個 bug 都是**出貨之後**靠橫向比對才抓到的。這一次 `control:30` 在任何數字離開腳本之前就擋下來了。

> 對外講法:「我寫了一道 SAST 閘門,然後**先讓它去跑一個我已經知道有問題的版本**,並且規定它抓不到 30 個就算它自己壞掉。它第一次跑抓到 0 —— 兩次,兩個不同的 bug。如果我沒寫那個正對照,我會拿著一個永遠回報 clean 的工具,而且很有信心。」

### 一句當初寫對的話,今天兌現

`dumps/README.md` 當初把「不 commit raw dump」的理由寫成**兩個獨立的理由,並標明任一個都足夠**。今天揭露政策改變,per-unit 機密那條失效了,「不轉散布廠商韌體」那條沒有 —— 所以 dump 的狀態一個字都不用改,而且**不用重新論證一遍**。

> 對外講法:「我習慣把一個決定的理由拆開寫,並標明哪幾個是獨立的。三個月後其中一個失效的時候,我不用重新想一次,答案已經在頁面上了。」

---

## W05 — 動態分析上半(無 gate,上午段,2026-08-17)

### 一句話

> 「一個未認證的 `GET /config.dat` 拿回 7,490 個 byte,而它的 SHA-256
> **跟我三週前用 bootloader 從 SPI flash `0xC000` 讀出來的那 7,490 個 byte 完全一樣**。
> 那不只是把一個 2019 年的 CVE 在自己的機器上跑通 —— 它同時是**第二個獨立儀器
> 讀到了這顆快閃記憶體**:一邊是 kernel 的 MTD 驅動走乙太網路,一邊是
> bootloader 的 SPI 常式走序列埠,兩條路不共用任何程式碼。
> 那一格在 W02 收工的時候是空的,我把它記成開放題,今天它自己填上了。」

### 三個可辯護的點

| 主張 | 證據 | 它證明我會什麼 |
|---|---|---|
| **一條跨四層、每一環都能單獨指出來的證據鏈** —— HTTP 回應 → flash 位移 `0xC000` → `fwrecon compcs` 解出 `USER_PASSWORD` 明文 → **那組明文直接通過 HTTP Basic 認證**,開啟其餘 68 個被擋頁面。而且它**順手關掉 W02 開放 #11**(「沒有第二個儀器讀過這顆 flash」),因為兩條讀取路徑不共用程式碼 | `sha256 e09cbf84…` 兩邊相同;[`BENCH-LOG.md` R4](../BENCH-LOG.md) | **知道一個「已知漏洞」和一條「自己走完的鏈」差在哪**。CVE-2019-19822 誰都能引用;能指著同一組 bytes 說「這是我用兩個不同儀器分別讀到的」不行 |
| **四條預測被自己事先寫下的條件反證** —— 豁免字串注入十二種全部失敗(`X-3` 不成立)、session 模型根本不存在(不是反組譯指到的那個全域)、`check_host` 不在授權路徑上、docroot 不等於出貨的 143 檔 | [`test-ledger.md`](../test-ledger.md);22/31 已評分,14 成立 / 4 反證 / 4 部分 | **把「我猜對了幾條」變成一個實驗結果**。反證的那四條每一條都指向一個具體的推理缺陷,而且**是被測試前凍結的那句話反證的** —— 事後才寫的條件證明不了任何東西 |
| **兩個「自報身分對不上」的發現,而且兩個都改變別人怎麼找這台機器** —— UPnP daemon 送 `Server: miniupnpd/1.4`,但 rootfs 裡只有 `/bin/miniigd`、**沒有 `mini_upnpd` 這個 binary**,而那個 banner 字串就在 `miniigd` 自己的字串表裡;`/etc/version` 有 `CX`,`boa` 和線上的 `status.htm` 沒有,**而 CVE-2024-51228 索引用的是有 `CX` 的那個** | [`BENCH-LOG.md` R3 / R8](../BENCH-LOG.md);三個來源逐一比對 | **知道識別字串本身就是一個攻擊面/研究面的問題**。第一個換掉整組適用的 CVE;第二個解釋了為什麼這個專案自己花了兩週才找到那個 CVE,而且它可以推廣到任何遠端指紋這個型號的人 |

### 這週沒證明什麼

- **31 項裡 9 項沒做,而其中 3 項是計畫自己規定不准做的。** `P3-1/2/3`(命令注入)
  是 W06 的;`P9-9`(reset 按鈕)是破壞性的,會刪掉今天量到的 4/343 差異;
  其餘四項要 POST 或要冷開機。**每一項的理由都寫在 `PROGRESS.md`,沒有一項是「來不及」。**
- **`formSysCmd` 的可達性沒有測。** W06 目標的三個條件裡,(a) 在這個 build 裡存在、
  (c) 有驗過的 oracle,都成立;**(b) 未認證可達 —— 沒測,因為測它就是打它**,
  而那是 W06。所以「這台可以被未認證命令執行」今天**仍然是讀出來的**。
- **`boa` 連在模擬環境裡都沒服務過一個請求。** 所以 Phase 2 的全部是靠真機做的,
  模擬只驗到 sink 那一側。
- **模擬環境的 `flash set` 寫的是普通檔案。** 真機走 MTD,有抹除區塊。
  那三個 byte 是**對真機的預測**,不是量測。
- **`FLW` 的磁區語意還是未決**,而**證據不夠的原因是我自己的作業單設計錯了**:
  讀回用了上一步已經填過相同內容的 RAM 位址,`RUNBOOK.md` §8.7.8 早就警告過。
- **`status.htm` 的未認證外洩,我沒有查過它是不是已經有人發表過。**
  寫成「未查證」,不寫成「新發現」。
- **有一筆解碼差異解決不了** —— `L2TP_SERVER_IP_ADDR` 我的表說 64 bytes、
  廠商的 binary 印成 IPv4,**而那個欄位全是零,資料沒有能力仲裁**。記錄,未解決。

### 這一週最該拿出來講的一件事,不是模擬跑起來

**我在復原了 `/dev/mtdblock0` 之後,做了一次「乾淨」的量測,結果 diff 裡出現了
一個我從來沒有寫過的欄位。**

原因是 `flash` / `boa` / `sysconf` 把 MIB 表快取在 **System V 共享記憶體**裡,
那段記憶體屬於**主機**核心,活得比 guest 行程久,`cp` 回裝置檔碰不到它。
`strace` 裡那幾行 `ipc(23,…)` 從第一次跑就在,我看過,沒讀懂。

如果沒抓到,結論會是「`flash set` 會重寫整個硬體區塊」—— **跟真正的答案相反**,
而且輸出裡沒有任何一個地方看起來不對。

> 對外講法:「我的模擬環境有一份不在檔案裡的狀態,而我一開始不知道。
> 抓到它的不是任何一個 self-check,是**一次量測的結果多出了一個我沒動過的欄位**。
> 修法不是下次記得清 —— 是把 `reset` 寫成工具的一個子指令,讓它同時清兩邊,
> 然後加一個守衛案例去證明前一個測試的值真的不會活過來。」

### 一件事先寫下來、然後被自己的清單打臉的事

計畫給 oracle 0 的 payload 是 `…;id > /var/web/x.txt;#`,而**這台的 BusyBox
沒有編 `id`**。它的失敗長這樣:

```
/bin/sh: id: not found
-rw-r--r-- 1 root root 0 /var/web/x.txt
```

**重導向把檔案建出來了,該填滿它的指令不存在。** 在真機上那就是一個空的 200,
和「參數被過濾掉了」長得一模一樣。計畫自己把「查 applet 清單」列為前提,
只是沒有人去查。

> 對外講法:「我在模擬環境裡先跑了一次要打真機的 payload,發現它會產生一個
> 跟『沒打中』完全無法區分的結果 —— 因為那台機器上沒有 `id` 這個指令。
> 而且同一個空檔案還有第二個成因:handler 自己尾巴的 `> /tmp/syscmd.log`
> 會蓋掉我的重導向。**兩個不相干的原因,同一個觀測結果**,而我是在一個
> 弄壞了也沒關係的地方發現的。」

### 這一天最短、最好用的一個方法學例子

隔離確認要證明「網段上只有兩台機器」。我抓了 45 秒,**得到零個封包**,
差點寫成「網段乾淨」。

**零不是證據 —— 除非你先證明那條線收得到東西。** 而那一刻它沒有:
kernel 自己的介面計數器是 `RX: 0 packets / TX: 12`。**送得出去、收不回來。**
送三個 ARP 之後有回應,`RX` 變成 3,那 45 秒的沉默才回溯地變成有效證據。

同一天稍早還有一次同樣形狀的:`ping 10.1.1.1` 成功,而 `eth1` 這個介面**不存在**。
兩件事同時為真,因為封包是繞經 Windows 出去的 —— 唯一的破綻是回應的 **TTL 是 63,不是 64**。

> 對外講法:「我有兩次差點把『沒有訊號』讀成『沒有東西』。第一次是一份空的封包擷取,
> 第二次是一個成功的 `ping`。兩次都是靠**一個不共用程式碼的第二來源**發現的 ——
> 一次是 kernel 的介面計數器,一次是回應封包的 TTL。
> 現在那個 TTL 判斷寫進工具了:它自己從 `/proc/net/route` 判定有沒有直連,
> 記進每一份逐字紀錄,而且對需要多播的那一組測試直接拒絕執行。」

---

---

## W05 收工 — 27/27,DoD 5/5(2026-08-17 下午)

### 一句話

> 「一個從 W04-2 就寫在筆記裡的靜態讀法 —— 閘門的十一個豁免字串,每一個都是
> 未錨定的 `strstr` —— 我拿它去預測**沒有人看過的頁面**:出貨的 76 個 `.htm`
> 裡哪七個不用認證。**七個預測、七個命中、六十九個被擋,兩個方向都沒有誤差**,
> 而其中兩個(`wan_status.htm`、`Connect_status.htm`)之所以不用認證,
> 只是因為 `status.htm` 是它們名字的子字串。
> 然後我又拿同一個模型去猜它沒被擬合過的東西,它說 `/boafrm/formLogin.htm`
> 會跟其餘五十六個端點不一樣 —— **裝置回了 404,其餘五十六個回 302。**
> 早上我從『十二種繞過都失敗』推論『所以比對其實是錨定的』,那一步是錯的,
> 而糾正它的不是第十三種繞過,是**問這個機制還應該預測什麼**。」

### 三個可辯護的點

| 主張 | 證據 | 它證明我會什麼 |
|---|---|---|
| **一個靜態讀法被拿去做出可否證的預測,而且預測命中了它沒看過的資料** —— 76 個出貨頁面全對,外加四個合成路徑、三個「閘門點名但沒出貨」的檔名、以及 `/boafrm/formLogin.htm` 這個第 57 個端點。而**它不是繞過**,理由比「試了沒用」精確:豁免比對和開檔用的是同一個正規化路徑,所以任何裝飾到足以取得豁免的路徑,伺服器都開不到 | [`notes/auth-flow-2018.md`](../notes/auth-flow-2018.md);[`BENCH-LOG.md`](../BENCH-LOG.md) 2026-08-17 下午 | **知道「測試失敗」是關於測試的證據,不是關於機制的證據**。早上那個錯誤是拿一個失敗的利用嘗試去推翻一份正確的反組譯,而分辨這兩件事是這一行最常出錯的地方 |
| **一個開機循環都沒燒就反證掉 `P9-1`,靠的是把 bootloader 從 flash 裡解壓出來** —— 整顆 4 MiB 裡 `grep FLR` 找不到東西,因為指令直譯器是 `0x0012F0` 起的一段 LZMA(17,334 → 56,592)。13 個 cmdline 形狀的針 0 命中,而**同一次掃描被證明找得到 `?` 印的全部 17 個指令**;工具在找不齊時拒絕出報告 | [`tools/loader-unpack.py`](../tools/loader-unpack.py) + `tools/test-loader-unpack.sh` 7 案;[`reports/bootloader-unit-2018.json`](../reports/bootloader-unit-2018.json) | **知道「找不到」什麼時候是證據、什麼時候是自己沒找對地方**。一個宣稱「這裡沒有 X」的報告,如果不能在同一次執行裡證明自己找得到已知存在的東西,那個宣稱值零 |
| **一輪未認證的 POST 把裝置唯一的 web server 弄掉了,而它同時把出廠預設區覆蓋成現行設定** —— 前後各一份 64 KiB 快照,逐欄位歸因:`H601` 未動,`COMPCS` 動 19 欄,`COMPDS` 動 23 欄(同樣那 19 個**加上原本區分兩者的 4 個**,而且每一個都移到 `COMPCS` 的值)。所以在這個 build 上,「恢復原廠設定」還原的是最後被寫進去的那一份 | [`BENCH-LOG.md`](../BENCH-LOG.md) T-14;`config-region-20260817-{1102-pre,post}.bin` | **知道「我改了什麼」和「我能證明是我改的」差在哪**。歸因需要的對照組是免費的:掃描前那份快照與 8/16 的完整 dump 逐 byte 相同,而那期間這台開過機、跑過完整 GET 輪、登入成功過 —— **所以開機和讀取不改設定區,這是量出來的,不是假設的** |

### 這週沒證明什麼

- **`P1-4` 沒跑完,而且是我自己把伺服器打掛的。** 兩輪各送出 34 / 36 個 POST,
  約第 45 個之後 `boa` 停止服務。**那一項判 `partial` 不是因為時間不夠,是因為
  57 個端點的普查在這台機器上一次做不完**,而登記簿事先寫的反證條件就是
  「先確認是不是自己打掛的」—— 確認了,是。
- **那條 DoS 我沒有分類、沒有評估影響、也沒有查前人。** 只記了數字:
  單一請求佔住 4.7–9.7 秒、約 45 個連續請求讓它消失、`ping` 全程正常、
  console 零訊息、20 分鐘後沒有自己回來。**「這是不是一個可發表的缺陷」是 W06/W07 的問題**,
  今天不主張。
- **`P9-3` 判 `partial`,而且我自己寫的成功條件錯了兩半。** 計畫寫「ping 有回應、
  且 MAC 是這台」;實際上 loader 不回 ICMP(TFTP-only 的堆疊沒有義務實作它),
  而且它的 MAC 是從我給的 IP 合成的。**凍結在登記簿裡的那一條沒有要求這些,
  所以判定站得住 —— 但我當天寫的那份計畫是錯的,而這比登記簿對了更值得記。**
- **`tftp put` 沒有測。** 「磚了之後救得回來」這件事,今天只證明到「救援模式進得去、
  網路活著、TFTP 服務會回應」。真正的還原路徑**仍然沒有走過一次**,
  而 W06 要寫 `H601`。
- **`P1-12` 的 38.76 秒是下界,不是量測值。** t=0 是第一個 console 字元,
  不是通電瞬間,而預測的門檻是 40 秒 —— **餘裕 1.24 秒**。
  這一項的用途是當「服務沒回應」判定的基準線,所以可用的結論是「等 45 秒」。
- **`COMPDS` 現在是壞的,而我沒有還原它。** 資料在裝置外有兩份副本,
  還原是 16 KiB 的 `FLW` —— 但那是寫 flash,超出這一場自己設的上限。
  **「有副本」不等於「已還原」**,而下一場的 IoC 預檢會因此報 0 / 343 不是 4 / 343。
- **`P9-9` 被延到 W07 保護的那份證據,被一個沒有警告標籤的測試毀掉了。**
  風險登記簿把危險寫在響亮的那一個動作上,而安靜的那一個從同一扇門進來。
  **這是這一週最該記住的一件事,而它不是一個技術發現。**
- **`BENCH-LOG.md` 的標頭說「per-unit 識別碼不寫進來」,而同一份檔案上午那一段
  寫了兩個 MAC 位址。** 公開的 repo 裡有一個「說不寫卻寫了」的欄位。
  只追加的檔案不能改,所以我把矛盾記下來而不是修掉 —— 但**這是待辦,不是註腳**。

### 這一週最該拿出來講的一件事,不是那個閘門模型

**是我早上寫的那句更正。**

上午十二種豁免字串注入全部失敗,我寫下:「反組譯裡的『未錨定』不等於效果上的
未錨定 —— 比對一定在某個我沒讀到的地方被錨定或被限長了。」

那句話**拿一個失敗的利用嘗試,去推翻一份完全正確的反組譯**。而它讀起來很像
好的懷疑精神:承認自己讀錯了、把矛盾歸因到自己身上、不硬拗。

它錯在方向。正確的動作不是懷疑那份讀法,是**問那個機制還應該預測什麼** ——
而它預測了 `wan_status.htm`、`Connect_status.htm` 和 `/boafrm/formLogin.htm`,
三個當時沒有人看過的東西,裝置三次都同意。

> **一個假設不能被「我試了但沒成功」推翻。** 只能被「它預測了 X,而 X 沒發生」推翻。
> 這兩句話聽起來很接近,而今天它們差了一整個下午。

### 一件事先寫下來、然後被自己的工具打臉的事

`bench-probe` 是為了防止一個具體的失效模式而寫的:一次打錯的 POST 讓 `boa` 死掉,
然後後面 57 個端點全部回「連不上」,看起來跟「端點不存在」一模一樣。

**今天那件事真的發生了 —— 而工具偵測到了它,然後在同一個動作裡把證據銷毀。**
`ProbeError` 在寫檔之前就 `return`,所以 59 筆回應連同逐項 `elapsed_ms`
(那裡面就有那個卡住 9.65 秒的端點)一起消失。

**一個中止的執行,正是最需要它的 transcript 的那一次。**
偵測事件和保存事件不該是同一條程式路徑 —— 而它們是,直到今天。

同一天還把 `set -o pipefail` + `grep -q` 重新寫進守衛套件,
而 `PROGRESS.md` **當天早上**才把那個記成儀器 bug 15。
**知道一個失效模式,和認得出自己正在做它,是兩件事。**

---

## W06 — PoC 重現（G4，四之五，2026-08-17 夜）

### 一句話

> 「一個**未認證**的 HTTP POST 改掉了這台路由器 SPI flash 上**九個指定的 byte**，
> 而那九個 byte 我能一個一個指出來、翻譯成一個有名字的欄位、然後全部放回去 ——
> 最後那份讀取跟這個專案**還沒寫過任何東西之前**那份 dump 逐 byte 相同。
> 而且它們落在**錯的區塊**：不是設定區，是存這台 MAC 與射頻校準的那一塊，
> 出廠重置不還原它。」

### 三個可辯護的點

| 主張 | 證據 | 它證明我會什麼 |
|---|---|---|
| **HTTP 參數 → `system()` → flash 上九個 byte，前後各讀一次、路徑不共用任何程式碼** | 網頁伺服器走乙太網路與 kernel MTD；驗證走 bootloader 的 `FLR`+`DB` 與序列埠。`0x00648a`–`0x006491` 是 ASCII，`0x006493` 是裝置自己重算的 checksum | 把一個網路層的輸入追到非揮發性儲存的**特定位址**，並且用第二條獨立路徑驗證 |
| **未認證的命令執行，而且「未認證」這件事被證明過** | 不帶憑證 → 路由器送出 ICMP echo **request**（方向與對照組相反）；**同一個請求帶憑證，行為完全相同** | 知道「未認證成功」單獨不成立 —— 要排除「其實我不小心帶了什麼」才算 |
| **兩條自己的發現被自己撤回，其中一條是被外部先前技術預測的** | `D-1`：換一個參數打同一個 handler 有四個封包，所以不是「打不到」；而 Talos TALOS-2023-1894 在測試**之前**就說那是 `sprintf` 不是 `system`。`D-2`：`formNtp` 把 800 bytes 原樣回顯，值確實到了，然後什麼都沒發生 | 用**正面證人**反證，而不是用「沒事發生」反證；以及願意把自己的發現往下修 |

### 這週沒證明什麼

- **G4 的第三條沒過，而且是我自己的兩個決定撞在一起。** 計畫假設 L2 跑
  `localPin` 那一行（它在 2015 與 2020 完全相同）；W04-2 把 G4 的標的換成
  `formSysCmd`（它是指名這台 build 的 CVE）。**兩個決定各自都對，合起來
  就是：那個 handler 在任何人下載得到的映像裡都不存在。** 沒有人在換標的時
  問過這件事。
- **我把上一週的散文當成量測寫進一個會被雜湊的欄位。** 改期十項的時候我寫
  「`boa` 在 qemu-user 下連一個 GET 都完成不了」——**那句話我沒跑過**，是從
  W05 的 `PROGRESS` 讀來的。九十分鐘後真的去跑，`P0-9` 是 confirmed，四個理由是錯的。
  這個 repo 的第一條證據紀律是「沒有單一工具的主張」，而我做的比那更糟。
- **`H601` 是我在動手之後才知道自己打到的。** 證據早就在 repo 裡 —— W05 的模擬輸出
  同一行既印了 `0x648a` 也印了「H601 checksum」。我花了一個早上蓋一個
  「白名單讓 `H601` 搆不到」的寫入工具，然後用一個未認證的 HTTP 請求把它寫了。
  **我保護的是我的工具，不是那台裝置。**
- **`D-11` 只量了一發。** 一個請求殺掉 web server 是確定的（有三發對照），
  但「它是崩潰還是卡住」「哪一種參數形狀觸發」完全沒量。而且它同時說明
  **W05 把同一件事歸因給了「數量」** —— 那份 transcript 值得重讀，但那是records
  的工作不是 bench 的。
- **`cpu model : 52481` 不是核心名字**，所以從 W02 開到現在的 Lexra 那一題
  還是開著。它現在開著的理由不同了：不是沒人去問，是**這台不報**。
- **沒有向任何人通報。** `D-4`（未認證接管）與 `D-11` 都還沒跑逐 handler 的
  prior-art —— 而今晚那一次搜尋只花一個查詢就撤掉了一個發現。**在通報之後才做
  那個搜尋，順序是反的。**

### 這一週最該拿出來講的一件事，不是那九個 byte

**是一個檢查器的失效模式：對照組分辨不出它要分辨的東西。**

今晚出現三次，穿三件不同的衣服：

1. 掃描的存活對照行被我排版成 `000` 開頭，於是它在統計裡跟「請求失敗」一模一樣；
2. `poc/run.sh` 用「body 是空的」判斷「檔案不存在」，**而這台對不存在的檔案回的是
   302 加一頁 HTML**，body 不是空的 —— 那個對照組永遠會失敗；
3. `P4-3` 的長度階梯打在 `formWlanRedirect`，它在 `root_form[]` 裡、**但不在 43 個
   碰 `lastUrl` 的函式裡** —— 那是那一項自己的反證條件裡「或這條路徑根本沒被走到」
   那一半，而我是誤打誤撞走進去的。

三個都不是「工具壞了」，是**工具在回答一個跟我以為的不一樣的問題**。
而三個都只被同一件事抓到：**去問「如果它是錯的，我會看到什麼」**。
第三個的答案最貴 —— 換一個會把參數回顯進 `Location` 的 handler，
於是「送 800 bytes 回來 799 個 A」把「沒事發生」變成了「值到了，然後沒事發生」。

### 一件事先寫下來、然後被自己的量測打臉的事

`runsheet.md` `A2.6` 是**今天早上**寫的，裡面寫「還原 `COMPDS` 之後應該回到
4 / 343」。晚上實測是 **23**。

23 是對的，錯的是那句話：**差異是兩個區域之間的，而那一節只還原其中一個。**
`4`（本來就不同的）`+ 19`（8/17 那輪 POST 改掉 `COMPCS` 的）。

而那個錯誤買到一個東西：那個 `19` 在 W05 是用**比對兩份快照**算的，這次是用
**在同一份快照裡比對兩個區域**算的 —— 兩條不共用程式碼的計算路徑，同一個數字，
連具名欄位都對得上。**一個寫錯的預期值，換到一次佐證。**

---

## 下一週要填的格式

複製這段:

```markdown
## Wxx — 主題(Gate,日期)

### 一句話
> 「30 秒版本。要有一個具體數字,和一個『所以呢』。」

### 三個可辯護的點
| 主張 | 證據 | 它證明我會什麼 |
|---|---|---|
| | | |

### 這週沒證明什麼
- (至少兩條。如果想不出來,代表這週的自我檢查不夠。)
```

**填寫的時候問自己三個問題:**

1. 這一點,**有沒有人能只靠 Google 就講出來**?能的話就不要寫進去。
2. 這一點的證據,**別人 clone 下來跑得起來嗎**?跑不起來的話,誠實標註為什麼。
3. 「沒證明什麼」那一欄,**有沒有寫出一個會讓我不舒服的東西**?沒有的話,通常是還沒想夠。


## W07, the desk half — 2026-08-18

**The week is not closed.** Thirty of its fifty-eight register rows need the
device and the bench visit has not happened. This entry covers the desk half so
that the claims are written down before the evening changes them.

**The one-line version:** the emulator stopped being a place where things
"looked like" they crashed, and three of this project's own sentences did not
survive that.

### Three defensible claims

**1. A refutation inherits the coverage of whatever produced it.**
`P4-1` predicted that a POST omitting `submit-url` makes the handler `strcpy`
into a read-only page. It was refuted on the device against three handlers, and
the class was written off. Re-run against all 58 with an empty body and controls
that held: **five handlers, all faulting at the same instruction storing to the
same address** — the pooled `""` literal at `0x004725d0`, inside a `PT_LOAD`
mapped `R-X`. 47 handlers carry the idiom and only 5 reach it without
parameters, so three hand-picked ones had roughly one chance in four each — and
the fifth was unreachable that way at all, because it reads `webpage`, not
`submit-url`.
*Evidence:* [`crash-triage-unit-2018.json`](../reports/crash-triage-unit-2018.json),
[`paramfuzz-unit-2018.json`](../reports/paramfuzz-unit-2018.json),
[`absent-parameter-strcpy.md`](../notes/absent-parameter-strcpy.md).
*What it demonstrates:* that a negative result has a coverage, and that writing
the coverage down is the difference between "we tested it" and "we tested three
of forty-seven".

**2. The dispatch table has a second source, and the first thing it produced was
a correction.**
`root_form[]` decides what "the attack surface" means in every week of this
project, and until 2026-08-18 it had one producer. These binaries are `sstrip`'d,
so `readelf -S` returns nothing and no standard tool could cross-read it.
`tools/formtable-scan.py` recovers it from program headers and data shape alone
— **57 of 57 on this unit, same address, zero disagreement with Ghidra** — and
across six builds it shows that `formSysCmd` is absent from 2015, present from
2016, **still present in N300RT V3.4.0 built 2019-03**, and absent from N150RT
V3.4.0 built 2020-10. *"3.4.0 removed it"* is false as stated: the removal is per
product.
*Evidence:* [`formtable-scan-six-builds.json`](../reports/formtable-scan-six-builds.json),
`firmware/SOURCES.json`.
*What it demonstrates:* the repository's own "no claim from a single tool" rule,
applied to the one table it had never been applied to — and a vendor-timeline
statement that only six builds side by side can make.

**3. A checker that only fires after the fact had never been a check.**
The runsheet's coverage rule keys on `executed`, so a row demands a procedure
only once it has a result. Measured: W05 and W06 read as fully covered because
they are finished; **W07 read as fully covered because it had not started** — 58
live rows, 2 claimed, 11 exempted, 47 with neither, and 32 of those scheduled
for a bench visit the same evening. The rule now applies to every live row of a
week the runsheet claims to cover, and Part B being append-only means adding a
week's block is what turns it on.
*Evidence:* `tools/check-runsheet.py`, `runsheet.md` `A1.5`–`A1.9` and
`A3.14`–`A3.24`, `RUNBOOK.md` §8.12.23–§8.12.38.
*What it demonstrates:* back-filling a procedure and following one are different
documents, and only the second can be wrong in time to matter.

### What this half did NOT prove

- **Nothing is on silicon.** Both new findings — the read-only `strcpy` class and
  the `formWsc` `localPin` overflow that gives a fully controlled `$pc` at offset
  509 — are emulated. The kernel does *not* fix up protection faults the way it
  fixes up alignment, so the mechanism transfers by construction; **that is an
  argument, not a measurement.**
- **The `formWsc` overflow has not been reproduced on a public image.** The run
  was attempted and refused (a leftover guest process blocked `reset`). Until it
  succeeds, the most serious memory-safety finding here is bound to a build
  nobody can download — the same limitation that has shadowed this project since
  W02.
- **No prior-art search has run for either.** `localPin` is the parameter
  CVE-2019-19824 names for command injection; whether an overflow on it is
  published is unknown, and assuming either way is exactly how row 13 became a
  correction three days ago.
- **`formtable-scan.py` is validated on one build of six.** The other five have
  no independent reference. The subset relation across builds is suggestive and
  is not proof.
- **Nothing explains why 42 of the 47 handlers return before reaching the tail.**
  The five that do not have nothing in common that has been written down.

## W07, the bench half — 2026-08-18 into 2026-08-19

**One line:** the device was driven for the first time since W06, 21 register
rows closed on silicon and 4 more lifted off emulated evidence — and the single
most serious result was a denial of service this project had inflicted on the
unit itself a day earlier and had recorded as harmless.

**1. An unauthenticated POST from W05 has kept this router off the internet ever
since, and nothing in the project would have noticed.**
W05's sweep of every non-hazardous endpoint with parameters absent changed
`DHCP_MTU_SIZE` from 1500 to 0, in a table whose conclusion was that no field
moved in a dangerous direction. `eth1` therefore comes up with `MTU:0` and
cannot transmit: with the cable in the WAN port, a DHCP server running, across a
full boot and 160 seconds, **zero packets crossed the wire** while `udhcpc -i
eth1` was in `ps` and `WAN_DHCP` read 1. Setting the MTU back by hand and
changing nothing else produced a complete DISCOVER / OFFER / REQUEST / ACK
immediately. It composes: a WAN that is down starts `dnsspoof`, which answers
every name — including one in an invalid TLD — with `10.1.1.1`, the same web
server that carries unauthenticated command injection, the uninitialised
credential pair, and unauthenticated password change.
*Evidence:* `BENCH-LOG.md` `T-62`, `T-63`; `reports/test-results.json` `P8-19`,
`P6-10`; `$FWRE_WORK/dumps/p8-19-wan{2,3}.pcap`.
*What it demonstrates:* a durable, unauthenticated, remote denial of the
device's primary function, found only because a test for something else needed
the WAN to work. **Four bench sessions ran in between and none of them asked
whether the router could still route.**

**2. The IP-keyed session arm is real, and the static reading of its expiry was
wrong in a way two independent instruments agreed on.**
A POST to `/boafrm/formLogin` makes a gated page return 200 with 5,332 bytes to
the logging-in address carrying no credentials, while a second address on the
same wire gets 302 at every sample. The published reading says the window is
system uptime and shuts permanently at 601 s. Measured against two anchors 706
seconds apart, it shuts at **login + 601** both times — the second window closed
between samples at 1538.1 and 1541.2 against a prediction of 1540.5, and a login
at uptime 939.5 reopened a window the stated mechanism says can never reopen.
So `beforeuptime` has a store that Ghidra's reference model and
`tools/mipsref.py` both missed, with a working control in the same run.
*Evidence:* `BENCH-LOG.md` `T-47`; `reports/test-results.json` `P2-11`;
`tools/session-window.sh`; `$FWRE_WORK/dumps/p2-11-session-window.json`.
*What it demonstrates:* the repository's own two-source rule catching its own
report — and the lead is inside that report already, which renders a
`strcpy`-written global as `writes:false` and was never read as a limitation.

**3. Three results inverted between the first reading and the last, and each
inversion came from a control rather than from more thought.**
An over-long SSDP `ST` drew no reply and looked like a length check; the match
turned out to be a prefix match, and once the ST matched, `wscd` died with
`SIGSEGV ... invalid read from 4187c8bc` — one byte of a live pointer
overwritten, not `41414141`. A SUBSCRIBE `CALLBACK` above 215 bytes returns
`412` with the service alive and looks protected; at 180 it returns 200 and the
service never answers again, so **the guard's threshold sits above the buffer**.
And `boa` counted zero connections under 200 held sockets — because it listens
on a dual-stack IPv6 socket, and the same file had already failed to list port
80 while the server was answering. Counted from `/proc/net/tcp6` it holds 251
and serves throughout, which refutes the Slowloris row through its own second
branch.
*Evidence:* `BENCH-LOG.md` `T-50`, `T-59`, `T-61`; `reports/test-results.json`
`P6-2`, `P6-3`, `P8-16`; `$FWRE_WORK/dumps/w07-console-*.log`.
*What it demonstrates:* every one of the three first readings was defensible and
wrong, and what separated them was a control the register had asked for — a
positive control for the SSDP match, a narrower ladder, and a second way to
count. **Not one of them was resolved by reasoning harder about the first
measurement.**

### What this half did NOT prove

- **`P9-9` was not run, so nothing here is known to survive a factory reset.**
  Every result in this session sits on a configuration that reset is predicted
  to overwrite, and that prediction is itself untested. It was left deliberately
  — pressing it on the dirty machine answers more — but the consequence today is
  that the durability of `DHCP_MTU_SIZE=0` is measured across reboots and **not**
  across a reset.
- **Five rows have no target on this unit, and this project removed four of
  them.** `P6-1`, `P8-7` and `P6-5` are recorded `na` because `UPNP_ENABLED` and
  `ALG_SIP_ENABLED` are 0. That is not evidence about the firmware. Until those
  are written back from the boot loader, nothing is known about whether
  CVE-2014-8361 or CVE-2022-27255 reproduce here.
- **The `wscd` wedge is not shown to be CVE-2021-35393.** One unauthenticated
  SUBSCRIBE removes the whole WPS/UPnP surface until a power cycle, with no
  fault logged, the process still sleeping and both ports still held. A wedge is
  not a memory corruption and calling it one from behaviour would be the exact
  inference the register exists to prevent.
- **The NTP length bug has a behaviour and no root cause.** A 44-byte reply puts
  the clock at `0xFFFFFFFF`, a value not present in the datagram; a correct
  48-byte reply sets the right time. `/bin/ntp_inet` has not been read.
- **`P1-11` has four sources and all four are the device describing itself.**
  The refutation asks for a scan and no over-the-air measurement was taken.
- **Route injection was not delivered.** The device's own DISCOVER requests
  options 33, 121 and 249, so it is inside what it accepts — but the crafted
  lease never reached it, and "it asked for the option" is not "it installs the
  route".
- **`hopeiot.net` was never answered.** The device asks for it within four
  seconds of a WAN lease. What it would have sent is unknown.

## W07, the close-out — 2026-08-19

**One line:** the reset button restored a device this project had damaged, and
it did so from a hard-coded table rather than from the factory-default block —
which mattered, because that block had been overwritten too and nobody had
looked until the afternoon before the button was pressed.

**1. The prediction was rewritten before the irreversible test, and the order is
visible in git.**
`P9-9` predicted that reset overwrites `COMPCS` with `COMPDS`. Decoding both
regions of the previous session's snapshot showed they already agreed on 0 of
343 fields, because W05's unauthenticated POST round had written the
factory-default block as well as the live one — 25 of 343 fields off the
2026-08-16 read, `DHCP_MTU_SIZE 1500 → 0` among them. So the original prediction
had already come true and the button could not distinguish "it worked" from "it
did nothing." The replacement followed a chain read out of two binaries:
`/bin/reload` polls `/proc/load_default` and runs `flash default-sw`, and
`/bin/flash`'s own usage separates `default -- write all flash parameters from
hard code` from `reset -- reset current setting to default`. Measured: 7,510
bytes and 20 drifted fields before, **7,490 bytes and 0 drifted fields after,
with a sha256 byte-for-byte identical to the 2026-08-16 flash region**. `H601`
untouched, `eth1` back to `MTU:1500`.
*Evidence:* `test-cases.toml` `P9-9` (`amended`, `amend_reason`, freeze
`ef7ab66d` → `ea8cf733` in commit `b88b932`); `BENCH-LOG.md` `T-69`, `T-70`;
`reports/test-results.json`.
*What it demonstrates:* a prediction changed **before** the measurement, with the
reason and the hash in the same commit, and the commit timestamped before the
button. That is the only form of "I changed my mind" a hostile reader has to
accept.

**2. The step the runsheet called unskippable was a control that could not fail.**
`A3.24` required an `H601` snapshot before and after the reset and said in bold
that it was the one step not to skip. It dumped `0x3F0000`. `H601` is at
`0x006000` — the runsheet's own partition diagram says so, `notes/flash-layout.md`
says so, and the public Realtek `apmib.h` puts `HW_SETTING_OFFSET` at `0x6000`.
On this part `0x3F0000` holds **0 non-`FF` bytes in 4,096**, against 4,093 at
`0x006000`. The comparison was `0xFF` against `0xFF`: it returns UNCHANGED in
every possible world, including the one where the reset wipes the radio
calibration — which is precisely `P9-9`'s refutation condition.
*Evidence:* `RUNBOOK.md` §8.12.38; `runsheet.md` `A3.24`; `BENCH-LOG.md`
correction entry.
*What it demonstrates:* the repository's own rule — *make recovery scripts able
to fail* — applied to a document instead of a script, and the failure found by
reading the address against three sources rather than by running the step.

**3. A global that two instruments called unwritten is written eight bytes from
the line one of them already printed.**
`beforeuptime` is stored at `0x0044f140`, inside `form_formLogin`. Three
blindnesses, each sufficient alone: o32 PIC stores through a GOT-loaded pointer
so no instruction names the address; an address materialised into a register
scored as neither read nor write; and a **GOT slot reported as though it were the
variable** — the committed report called `0x00486270` `authipaddr` with six
reads, when `authipaddr` is at `0x0048fbd8` and all six were address
materialisations. `sstrip` had removed the section headers, so the project had
treated the corpus as symbol-less; `.dynsym` is reachable through `PT_DYNAMIC`
and holds **423 named symbols**. And the scanner's control had been green
throughout, because `nowuptime` happens to be reachable by the addressing form
the scanner could already see.
*Evidence:* `tools/mipsref.py` schema 2; `reports/mipsref-unit-2018-authsession.json`;
`ghidra/scripts/BoaListing.java` over `0x0044f0e0`–`0x0044f190`, where Ghidra's
own annotation reads `-> beforeuptime`.
*What it demonstrates:* **a control proves the path it travels and no other.**
The second control this added failed on its first run — a `jalr` clobbers
caller-saved registers but its delay slot executes first — and catching that is
the whole argument for having it.

### What this week did not prove

- **`H601` was compared decoded, not byte for byte.** `flash allhw` shows the
  MACs and every calibration table intact after the reset, and that is a second
  source, not the authoritative one. The byte comparison needs a boot-loader
  dump, and the serial adapter is what stopped the board booting.
- **`COMPDS` after the reset is unread.** `flash default-sw` restored `COMPCS`
  byte-for-byte; whether it repaired the factory-default block too is unknown,
  and if it did not, then `P0-5`'s IoC baseline has meant something different
  from what this project assumed since W02.
- **Two reads of the same region disagreed and nothing settled it.** The boot
  loader saw `comp_len` 7,501 with a password residue after the string
  terminator; HTTP after boot saw 7,498 without it. Either the boot rewrites
  `COMPCS`, or `/config.dat` is not the byte copy of flash that `A3.6`'s headline
  result claims — and `A3.6` is one of the strongest chains in this repository.
- **The route injection has no attribution.** Options 33, 121 and 249 were sent
  together to guarantee delivery on the single lease available. Both a `/32` and
  a `/16` route were installed, and one of the three also made the device
  announce `32.49.0.49` — four bytes straddling a separator in the option's
  string form. Which option did it is unmeasured, and so is whether it reaches
  anything past three gratuitous ARPs.
- **`eth1.bound`'s unquoted expansions are read, not driven.** Argument injection
  into `sysconf`, not command injection — POSIX `sh` does not re-parse an
  expansion. What `sysconf` does with a shifted argv is the obvious next test and
  it was not run.
- **Which command wedged the device is a hypothesis.** Eight ran; the
  byte-at-a-time read of `/dev/mtdblock0` is the strongest candidate and that is
  all it is. Three power cycles and forty minutes went into a state that turned
  out to be a UART adapter back-feeding through the header.
- **`P5-2` is still not done**, and calling W07 "57 of 58" rather than "nearly
  finished" is the honest form.

## W07, the final desk session — 2026-08-19

**One line:** the row this project had written off as unanswerable was answerable
from evidence already in the repository, and the thing that needed fixing was not
in the firmware — it was six sentences that had outlived their measurement.

**1. Two console lines that name no library were turned into a load base, and
the four bytes that did not match were predicted rather than tolerated.**
`P5-2` had been called "cut in all but name" because a `ret2libc` target seemed
to need an observation channel this device does not offer. `BENCH-LOG.md` already
held two kernel fault messages from 2026-08-18, recorded for other rows.
`boa`'s `epc == 2aafe218` resolves to `strcpy+0x18`, which puts `libuClibc` at
**`0x2aae3000`** and `system` at **`0x2ab08460`**. qemu-user's own `pc` for the
same fault is `0x2b32721c` — `strcpy+0x1c`, four bytes further on. That gap is
the MIPS rule that a fault taken in a **branch delay slot** leaves `EPC` on the
branch, and the two words were read back out of the ELF and decoded to confirm
it: `0x1460fffc` (`bnez v1`) then `0xa0c30000` (`sb v1,0(a2)`), one source
register shared.
*Evidence:* [`notes/mips-ret2libc.md`](../notes/mips-ret2libc.md);
[`reports/libbase-unit-2018.json`](../reports/libbase-unit-2018.json);
`tools/libbase.py` with 27 guard cases.
*What it demonstrates:* **a near-miss with an exact explanation is not a
near-miss.** `0x2aae2ffc` was four bytes off a page boundary and the reflex was
to call it close enough; `mmap` never returns that, and the four bytes had a rule
behind them.

**2. The narrowing that picks `strcpy` is published as a funnel, and so is the
prediction's error bar.**
663 dynamic symbols → 22 admit a page-aligned base → 5 put a *store* at the
`epc` or in a delay slot there → 1 matches qemu-user's instruction pair. Then a
second, independent test: `boa` and `wscd` link different libraries, so if
nothing is randomised their `libc` bases must differ by exactly `libapmib.so`'s
mapped span — `0x25000`, computed from its own program headers. Predicted
`0x2aabe000`; it puts `wscd`'s `epc` at `free+0x12c` and its `ra` at `free+0x58`,
both inside one function, against a fault the kernel called an invalid **read**.
Sweeping all 256 page-aligned bases in the surrounding megabyte, **7** would have
put both addresses in one function — so the landing survived a filter it had
about a **1-in-36** chance of surviving by luck, and that number is in the report
rather than left to the reader to worry about.
*Evidence:* the `narrowing` and `how_easily_it_could_have_held_by_luck` blocks of
the report; `check-reports.py` refuses the file if the funnel does not end at one.
*What it demonstrates:* the difference between a prediction that landed and a
prediction that could not have missed is a number, and publishing it is cheaper
than being asked for it.

**3. A claim's tense outlived its measurement in six committed files, and one of
them was the disclosure register.**
`P1-2` found `52869/tcp` open on 2026-08-16. `P6-1` and `P8-7` found it closed on
2026-08-18, because this project's own W05 unauthenticated POST round had written
`UPNP_ENABLED = 0` and this build ships no UPnP page to undo it. Both were right
when taken. **Neither sentence carried a date**, and the first had been copied
into `docs/disclosure.md` `D-16`, `notes/bughunt.md`, `notes/cve-status.md`,
`notes/attack-surface.md` and `notes/three-unread-binaries.md` three times.
*Evidence:* the six diffs, and `D-16`'s new status line saying it is not
reportable on its network state until a bench visit re-measures it.
*What it demonstrates:* **"one piece of state has exactly one owner" does not
catch this**, because the failure is not duplication — it is tense. And the
second layer is worse than the first: the 2026-08-19 reset probably made those
sentences true again, and a claim that has come back true by accident is
indistinguishable from one that was checked.

### What this session did not prove

- **`P5-2` rests on one boot.** Both fault messages come from station 3, boot 2,
  cycle 3. What is established is per-`execve` determinism, which is what ASLR
  is; what is not established is that a reboot leaves the base alone. Recorded
  `partial` for exactly that reason, and `runsheet.md` `A3.23.0` closes it with
  two `cat`s on the post-reset boot.
- **Nothing has been jumped to.** `system` is computed, not reached. `a0` would
  have to point at a command string, and `P5-1`'s `localPin` frame has not been
  shown to allow that.
- **`TASK_UNMAPPED_BASE` was derived and then withdrawn.** Both processes imply
  `0x2aaa8000`; the MIPS formula gives `0x2aaaa000`. Two pages unaccounted for
  and no reading of this kernel, so only the *difference* between the two bases
  is claimed as predicted.
- **The port state is still unmeasured.** The whole point of finding #3 is that
  nobody has looked since the reset, and this session did not look either — it
  was desk-only. Writing the prediction down is not the same as testing it.
- **Whether "tense" is mechanically checkable is unanswered.** The parity
  divergence got a checker because comparing two lists is mechanical. "Every
  present-tense claim about device state cites a test id and a date" is not, at
  least not without a false-positive surface larger than the problem.

## W07, the closing bench — 2026-08-19

**One line:** the arithmetic done at the desk that morning was confirmed to the
byte by the device that night, and the two things worth more than the arithmetic
were both controls — one that made a hardening flag stop being evidence, and one
that stopped a crash being called an injection.

**1. A predicted address, never observed, printed by the kernel four boots later.**
The morning's desk work put `libuClibc` at `0x2aae3000` in `boa` from a kernel
fault message, and *predicted* `0x2aabe000` in `wscd` purely from
`libapmib.so`'s program headers — the one library the two processes do not share.
`/proc/350/maps` and `/proc/217/maps`, read over a telnet shell opened through
the `formSysCmd` injection: `2aae3000` and `2aabe000`, with `libapmib.so`
occupying exactly `2aabe000 → 2aae3000`. `TASK_UNMAPPED_BASE` came out
`0x2aaa8000`, the number the note had derived and then **deliberately withdrawn**
for disagreeing with the MIPS formula.
*Evidence:* `notes/mips-ret2libc.md` §5; `BENCH-LOG.md` `T-83`;
`reports/libbase-unit-2018.json`.
*What it demonstrates:* the difference between a computation that agrees with its
input and one that predicts an independent measurement. Only the second kind
survives a hostile reader, and the only way to have it is to write the number
down before looking.

**2. A hardening flag that claims a mitigation the kernel does not apply.**
`/proc/sys/kernel/randomize_va_space` reads **2** — full ASLR — on a device whose
library layout is fully determined by its ELF files across two processes and four
boots. The sysctl is generic kernel code; this device does not act on
it, and the kernel source has not been read, so why is open item 86.
*Evidence:* `BENCH-LOG.md` `T-83`; `notes/bughunt.md` row 24.
*What it demonstrates:* **a source is not a measurement.** Reading the flag and
stopping would have closed `P5-2` as refuted without a single address being
looked at, and the write-up would have said "ASLR is on" with a citation.

**3. A control that stopped a crash being reported as command execution.**
Two `AddPortMapping` requests with backtick payloads killed `/bin/miniigd`, and
the natural reading was CVE-2014-8361 crashing rather than executing. The control
refutes it: **twenty-two `A` characters, no shell metacharacter anywhere**, kill
it identically, while `NewInternalClient=10.1.1.1` is answered `200` and the
daemon survives a subsequent read. So the trigger is any value `inet_addr()`
rejects — which is visible in the device's own NAT table as
`DNAT … to:255.255.255.255`, `INADDR_NONE` used as an address. `ps` over telnet
two minutes later shows **no `miniigd` process**, which is a different failure
from `P6-3`'s `wscd` surviving with its listener closed; from outside both are
`connection refused`.
*Evidence:* `BENCH-LOG.md` `T-82`, `T-83`; `docs/disclosure.md` `D-19`;
`notes/three-unread-binaries.md` §2.
*What it demonstrates:* three points define the line and any two of them support
the wrong conclusion. The cost of the third point was one power cycle; the cost
of skipping it would have been a disclosure report naming the wrong CVE.

### What this session did not prove

- **`P8-7`'s second half.** The `MINIUPNPD` chain shows `(0 references)` and
  `ip_forward` is `0`, and **the WAN cable was not connected** — a router with no
  WAN not forwarding says nothing about a router with one. That reading was
  available and stronger and was not taken.
- **`P6-5` was not delivered.** The flag is back to `1` and no SIP helper exists
  anywhere in `/proc/sys/net/netfilter/`, on a kernel with no loadable modules —
  stronger evidence than 2026-08-18's, and still not an answer, because the
  vector is a WAN-side UDP packet and there was one cable.
- **Why `miniigd` dies is unknown.** The unbounded `strcpy` at `0x0044851c` is on
  the path and a 22-byte value is a poor fit for it. Each hypothesis costs a
  power cycle, so the next attempt needs its prediction written first.
- **Open item 79 is not closed by one clean boot.** The board came up with the
  CP2102 attached after the jumpers were reseated, which is what `A2.2`'s
  hypothesis names — one success supports it and cannot prove it, and the failure
  mode last time appeared *between* successful boots.
- **`D-19` has had no prior-art search**, so it is not reportable and has not
  been reported. "Nobody published it" is a claim that needs a search behind it.
- **And the prediction written before the cable was simply wrong.** Open item 76
  was predicted at 20 / 343; the IoC precheck read 4 / 343, `flash default-sw`
  having rewritten both regions. It is left in `BENCH-LOG.md` as written, with the
  refutation firing against it, because a register whose predictions are edited
  after the fact is a register that predicts nothing.

## W08, the interrupt desk session — 2026-08-22

**One line:** the loader's TFTP turned out to be interrupt-driven, the first
version of that reading concluded the exact opposite from observations that were
all individually correct, and the thing that caught it was changing the question
rather than looking harder.

**1. A conclusion reversed by asking a different question.**
Deciding whether the loader ever enables interrupts began as a search for
Realtek's `sti` idiom — `mfc0 $1,$12 / ori $1,1 / mtc0 $1,$12`. None exist.
Seven `cli` sites of the matching shape do. The conclusion written from that was
"the loader runs masked, therefore its TFTP is polled", and it is backwards:
this build writes `ori $1,0x1f / xori $1,0x1e`, which sets bit 0 and clears bits
1 to 4. The instrument now evaluates every `mtc0 $12` in the image with a
four-valued per-bit lattice and reports what bit 0 *is*, not whether the
instruction sequence *looks* like something.
*Evidence:* `reports/bootloader-unit-2018.json` §`interrupt_wiring`;
`notes/loader-interrupts-and-console.md`; `tools/test-loader-unpack.sh` cases
25–27, two of which differ in one bit of one immediate.
*What it demonstrates:* a pattern match answers "is this the shape I expected",
and the question was "what is the value afterwards". The first has a failure
mode no test can cover — you can only think of the shapes you can think of.
**And the error pointed the wrong way**: it would have excluded the correct
cause from the three that survived the bench, with a sentence that sounds
well-founded.

**2. A six-day-old console log that answered a one-day-old question.**
The `Unknown command !` that a clean `EB` line drew on 2026-08-21 was caused by
eight spaces already sitting in the loader's line buffer, behind a `<RealTek>`
that the TFTP completion path had printed **from inside the ethernet interrupt
handler** — `0x80401CD0`, passing a second copy of the prompt string at
`0x8040A894`. The tokeniser stores `argv[0]` before it tests for a space
(`0x80407290` then `0x804072D4`), so `argv[0]` was the empty string.
*Evidence:* `$FWRE_WORK/dumps/w08-a28.log`, unchanged since the night it was
captured; `tools/console-lint.py`, which reproduces the diagnosis and reports an
unexplained rejection as a non-zero exit.
*What it demonstrates:* the reason it took a day is worth more than the answer.
The search for who prints the prompt was a **cross-reference on one address**.
It returned one result, the result was correct, and the inference drawn from it —
*the prompt has one owner* — was false, because the same text is in the image
twice. A cross-reference answers "who uses this address"; the question was "who
prints this text".

**3. A pointer at a rule that does not exist.**
`runsheet.md` `A2.8` ends step 4 with *"see stop condition 5 below"*, and `A2.8`
carries no numbered stop conditions at all — the nearest list is `A2.7`'s, above
rather than below, with four items. `BENCH-LOG.md` then quoted the same number
back as though it were a rule.
*Evidence:* `runsheet.md` `A2.8` 收尾, now five conditions;
`tools/check-runsheet.py` and four cases in `tools/test-check-runsheet.sh`.
*What it demonstrates:* the rule's content was there the whole time; what was
missing was that it was numbered and placed where the pointer points. **A
pointer at a rule that does not exist is worse than no pointer** — the reader
believes something is holding them and nothing is. One of the four new guard
cases passed before the checker's own regular expression was fixed, which is the
same lesson one level down: the case caught the check being empty, not the
document.

### What this session did not prove

- **Nothing was sent to the device.** Every claim is "the code reads as", and
  `P9-17`, `P9-18` and `P9-19` are frozen before the next power-on. The whole
  interrupt story could still be refuted by one `DW B8003000 1`.
- **The `eth0` ISR was not traced to the TFTP handler.** It reaches
  `0x80402040`, which dispatches on EtherType; the rest is a call-graph reading
  with no device observable behind it.
- **`GIMR0`'s bit 8 is not predicted.** Two possible writers, and the call graph
  between them was not chased. Both outcomes are written down with the
  instruction that settles them — deliberately, because a prediction that names
  its own undecided bits survives a hostile reader and a confident wrong number
  does not.
- **Whether the eight spaces were a TAB or eight spacebars is undecidable from
  the record.** Both leave the same echo and the same buffer. The cause of the
  rejection is settled; the keystroke is not.
- **The status census is a straight-line reading over a bounded window**, and it
  can cross a function boundary. It is exact for the `sti` claim, which needs
  four instructions of context; it reports five writes as *undetermined* and
  prints where each one's value came from rather than guessing.
- **The TFTP filename `%s` at `0x804011FC` was read and not chased.** It puts
  attacker-supplied text on the operator's console with no length check beyond a
  42-byte floor on the request. It requires the escape window to have been
  caught, so it crosses no boundary a UART cable has not, and it is a note entry
  rather than a register row — which is a judgement, not a measurement.

## W08, the close — the write-up draft, six cuts, and a control that was designed to fail — 2026-08-22

### 一句話

> I finished the fourteen-chapter draft, **cut six register rows with written
> reasons instead of running them**, and closed the last three at the bench with
> **zero flash writes** — recording all three as `partial`, because each carries
> a clause its own frozen prediction got wrong. W08 closes **8 / 8, 0
> outstanding**. The best result of the night was one the device volunteered:
> **it answered a request that had already timed out**, the instant a twenty-word
> RAM payload re-enabled interrupts.

### 三個可辯護的點

| 主張 | 證據 | 它證明我會什麼 |
|---|---|---|
| **`J`'s network kill is the masked interrupt — at the reception layer, and not at the layer the prediction named.** Two payloads differing in exactly five words: restore the interrupt mask only, and TFTP stays dead on three signals sharing no code; restore the mask *and* the CPU's `IE`, and the loader answers ARP in 0.9 ms on the wire. **It still does not answer TFTP**, so the row is `partial` | `BENCH-LOG.md` `T-99`/`T-100`; `/tmp/w08-c-wire.pcap` (5 frames); `tools/mkramboot.py --irq-restore`, whose simulator refuses a payload that does not return through `ra` | Designing an experiment whose **control is the half predicted to fail**, and then reporting the half that failed. Without B, C is only "I changed something and it got better" |
| **The loader's TFTP stack is up at its compiled-in `192.168.1.6` before `IPCONFIG` is ever typed**, which corrects a sentence this register had recorded. Witnessed twice, the second time by accident: the loader's MAC is `56:aa:a5:5a:7d:e8` there and `56:0a:01:01:01:e8` after `IPCONFIG 10.1.1.1` — so the middle four bytes are written by `IPCONFIG`'s handler, meaning **the stack was serving with a MAC that could not have come from `IPCONFIG`, because `IPCONFIG` had never run** | `BENCH-LOG.md` `T-97`; `dumps/w08-p918-default-ip.json`; `PROGRESS.md` W08 Day 2 | Noticing that a number I was not measuring had changed, and turning it into a second independent witness instead of an aside. The recorded model had the mechanism right and the timing wrong |
| **A console rejection from the previous session was reproduced on command, and an instrument accounted for every rejection in the log including one nobody reported.** TAB expands to exactly eight spaces; the `<RealTek>` after a TFTP completion is painted by the `eth0` ISR and does not clear the line buffer; a command typed after it is rejected while the echo shows no leading space at all | `tools/console-lint.py`: 33 prompts (1 TFTP-printed), 3 rejections, **0 unexplained**, exit 0; it reconstructed the buffer the device actually saw, and flagged `\x1b[A\x1b` at offset `0x198` | Building the checker that reads a verbatim log the way the dispatcher does, rather than trusting the operator's account of it — which in this session was incomplete |

### 這週沒證明什麼

- **No second instrument has read this unit's flash, and now it never will under
  this project.** `P9-5`, `P9-6` and `P9-7` are cut. Every byte-level claim still
  comes through one path: the loader's own `FLR`, over the device's own UART. Two
  reads agreeing proves the transfer is stable, not that it is correct. **The
  JEDEC id has never been read** — `Eon EN25QH32B` rests on the ink on the
  package, and `flashrom` agreeing on 4096 KiB is not a second source because its
  database is keyed on that same name.
- **Open item 97 is not answered, and cutting three rows did not answer it.** The
  part sits at 1.70 V against a 3.3 V supply across three supplies. Whether that
  is the board clamping or resistance in the clip path **was never separated**.
  "We chose not to measure it" and "we found out why" are different sentences and
  the register says the first one.
- **No modified image has ever been written to this device.** `P9-10` is cut as a
  deliberate trade, so `P8-10`'s outbound plain-HTTP upgrade path and `P9-13`'s
  checksum-only acceptance stay **static readings for good** — a supply-chain
  class named and never executed. The chain in chapter 10 ends at a flash byte
  changed by an HTTP request and does not extend to a modified image booting.
- **`fwrecon compcs` still prints "The device itself would reject this blob"**,
  and the only test that would have measured it was `P9-6`. That sentence is now
  a permanent unmeasured claim about device behaviour made by this project's own
  tool. It is kept by decision and listed rather than quietly left.
- **Why the loader's TFTP service stops answering is unknown.** With reception
  restored it replies to ARP and ignores TFTP with the console silent. The
  candidate — a transfer left incomplete by the queued request taken when `IE`
  went high — has two agreeing readings behind it and **no measurement**. It is
  open item 103.
- **`IRR3` carried a prediction with no refutation condition**, and it read zero
  against a predicted 3. It is recorded and **not scored**, because a prediction
  without a written failure condition leaves me holding the power to decide
  afterwards whether it counted. This time the direction happened to be against
  me. That is luck, not method.
- **No wireless test has been run at any point in this project.** Nine rows
  across `P7-*` are cut. For most of them a US$30 adapter is the whole blocker;
  for `P7-3`, `P7-6` and `P7-9` it is not, and buying one should not bring them
  back.
- **The ten-minute read test on the draft has not been run**, and the draft has
  not been edited. W09 is the editing week; W08's DoD was content in all fourteen
  chapters, and that is what was met.
