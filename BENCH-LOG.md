# 實機場次紀錄

> **只追加。** 既有段落不修改 —— 一場做完就定版。

## 這份檔案擁有什麼

| 檔案 | 擁有 |
|---|---|
| [`RUNBOOK.md` §8.12](RUNBOOK.md) | **程序** —— 可組合的小節,跨週共用,會被精煉 |
| **本檔** | **每一場實際跑了什麼** —— 計畫(動手前寫的)、紀錄卡、逐字節錄、燒掉了什麼 |
| [`study/test-cases.toml`](study/test-cases.toml) | 單項的預測 / 反證 / 判定 / 證據連結 |
| [`PROGRESS.md`](PROGRESS.md) | gate、週、carried-forward |
| `$FWRE_WORK/dumps/` | 原始 transcript、pcap、JSON。**不進 repo** |

**因為本檔是逐字的,§8.12 可以自由精煉** —— 證據站在這裡,不站在程序文件上。
今天一場就找出四個程序缺陷(`FLW` 的預期回應字樣、寫死的 `eth1`、讀回重用 RAM
位址、繞過測試打在豁免頁上),**每一個都是跑了才知道的**;程序改掉了,而這裡
記的仍然是當時實際打了什麼、實際看到什麼。

**per-unit 識別碼(MAC、SSID、`config.dat` 內容、射頻校準值)不寫進來** ——
跟 W02 把 PCB 條碼塗掉是同一條規則。

**每一場的格式**:計畫 → 紀錄卡 → 實測結果 → 燒掉了什麼 → 下一場從哪裡開始。
**計畫寫在動手之前**,而 append-only + git 讓「寫在前面」這件事可以被 diff 證明。

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
