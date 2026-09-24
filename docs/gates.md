# Gates — the acceptance criteria, copied from the week plans

Every ✅ on the board in [`README.md`](../README.md) is scored against one of the
checklists below. They are **not** written here; they are lifted verbatim out of
the ten week plans by [`tools/extract-gates.py`](../tools/extract-gates.py), and
`make check-gates` fails if this file and those plans have drifted apart.

## Why the plans themselves are not in this repository

They are working documents addressed to the author: day-by-day schedules, time
budgets, stop-losses, and — in `W04` and `W09` — sections that rehearse how to
answer an interview question. `CLAUDE.md`'s house style forbids that register in
a committed file, and publishing the plans to fix a broken link would have
traded a small problem for a larger one. What is a *standard* is here; what is a
*schedule* or a *rehearsal* is not.

## What this page proves, and what it does not

It proves that the text below matches the plan files **as they are now**. It
does **not** date them. `plan/` is untracked, so nothing in it has a history,
and no hash printed here can show that a criterion was not softened after the
fact.

What does date them is in this repository, and it needs no trust:

> **The first commit of `PROGRESS.md` — [`b085444`](../journal/PROGRESS.md),
> 2026-08-07 — already carries the full W01–W10 table with G0–G5 assigned to
> their weeks**, on the day W01 closed and nine days before the hardware
> arrived. Every gate met after that date was met against a standard that commit
> had already fixed. `git log --diff-filter=A -- PROGRESS.md` is the whole check.

Where a plan turned out to be wrong, the correction is in
[`PROGRESS.md § Corrections`](../journal/PROGRESS.md) rather than in a quiet edit
here — `W04-2` and `G3.5` exist only because W02 found the unit runs a build
neither W03 nor W04 had read.

## A note on language

The criteria are reproduced in the language they were written in. A translation
would be a rewrite, and the claim this page exists to support is that nothing was
rewritten. The one-line English gloss under each heading is a **gloss added
here**, not part of the extract.

---

## W01
*Gloss (added here, not part of the extract):* Toolchain green, and the seven structural facts answered from measurement rather than from a spec sheet.

## 三、本週驗收門檻


### G0：環境全綠
- [ ] WSL2：binwalk + sasquatch 有輸出
- [ ] `qemu-mips-static --version` 有輸出
- [ ] `flashrom --version` 有輸出
- [ ] Ghidra 能開
- [ ] PuTTY/picocom 可用

### G1：韌體解剖完成（7 要素）
- [ ] 韌體已解包（binwalk/sasquatch 成功）
- [ ] 能口述 7 要素：**SoC（RTL8196C）、架構（MIPS）、endianness、載入基底位址、SquashFS（LZMA）、/bin/boa、設定檔存法（apmib→config.dat COMPCS 明文）**
- [ ] `notes/anatomy-n150rt.md` 完成
- [ ] `notes/pierre-kim-map.md` 完成
- [ ] `notes/attack-surface.md` v1 完成

> ⚠️ **G1 過不了不准進 W2。**

## W02
*Gloss (added here, not part of the extract):* A boot log and a flash dump off the unit itself, cross-checked against the vendor image.

## 三、本週驗收門檻


### G2：硬體存取
- [ ] 有活 bootlog **或** 已記錄 fallback
- [ ] SPI dump + hash 驗證 **或** 官方韌體主路徑
- [ ] Dump vs 官方比對完成 **或** 理由記錄
- [ ] PCB 標註照片

> ⚠️ **G2 過不了不准進 W3**——但「官方韌體主路徑 + 誠實記錄」也算過。

## W03
*Gloss (added here, not part of the extract):* No formal gate. The dispatch table found, and at least one authentication candidate.

## 三、本週 DoD（非正式 Gate，但必須達標）


- [ ] 分派表找到（≥ 10 個 handler 列出）
- [ ] auth 候選函式 ≥ 1 個
- [ ] formSysCmd handler 逆向完成
- [ ] `notes/sink-inventory.md` 建好
- [ ] Ghidra 中 ≥ 5 個函式已重命名

## W04
*Gloss (added here, not part of the extract):* Point at the instruction a CVE lives on, and say why it is wrong.

## 三、G3 驗收門檻


- [ ] CVE-2019-19824（formSysCmd RCE）：指到 system() 那一行 + 為什麼壞
- [ ] CVE-2019-19822（config.dat 洩漏）：指到 boa 為何無 auth 檢查
- [ ] 後門帳號（CVE-2015-9550）：指到硬編碼位置
- [ ] auth-flow.md 完整
- [ ] ≥ 1 個 CVE-2025 根因定位

> ⚠️ **G3 過不了不准進 W5。指不出那一行 = 沒懂。**

## W04-2
*Gloss (added here, not part of the extract):* Three builds read across, the configuration region decoded, and the next target chosen from evidence.

## 四、G3.5 驗收門檻


- [ ] 五（或六）個 build 的 `root_form[]` + sink 普查在 `reports/`，每份帶輸入 SHA-256
- [ ] `notes/auth-flow-2018.md` 完成，關鍵分支在**指令層級**確認
- [ ] `COMPDS` 完整解碼，`TELNET_ENABLED` / `SSH_ENABLED` 有答案 + 第二來源
- [ ] G4 目標從證據選定，且三個分支的推理都寫在 note 裡
- [ ] `FLW` 回復路徑已演練，日期記在 `RUNBOOK.md`

> ⚠️ **G3.5 過不了不准進 W05。**
> 而且這一週有一條額外的驗收標準，它不在上面五條裡：
>
> **「這週有沒有推翻掉自己之前寫的東西？」**
> 一個都沒有 → 高度可疑。五個 build 橫著讀，不可能每一條舊結論都剛好完美轉移。
> 沒有推翻，通常代表**沒有真的去比對，只是把新資料填進舊表格**。

## W05
*Gloss (added here, not part of the extract):* No formal gate. A prediction scorecard completed, and one repeatable dynamic path standing up.

## 四、本週 DoD


- [ ] `notes/prediction-scorecard.md` **在測試之前** commit，測試之後打完分
- [ ] 一條動態路徑站起來（實機必成；qemu / FirmAE 至少記錄失敗原因）
- [ ] `notes/emulation-2018.md` 的「補了什麼 / 失真了嗎」表完成
- [ ] `notes/oracle-design.md` 完成，至少一個 oracle 在模擬環境驗過
- [ ] W06 目標三條件齊備

## W06
*Gloss (added here, not part of the extract):* One chain reproduced end to end, with the evidence layer named at each link.

## 五、G4 驗收門檻


- [ ] 一條完整攻擊鏈在實機成立，**五環各自可指**
- [ ] 至少一環的證據是**帶外的**（ICMP / flash 差異），不是只有 HTTP 回應
- [ ] L2 重現路徑存在（任何人 + 公開映像 + 模擬）
- [ ] 每份 PoC 有驗證範圍區塊，誠實標明哪些版本只有靜態證據
- [ ] `poc/run.sh` 會失敗，而且失敗時說得出是哪一步

> ⚠️ **G4 過不了不准進 W07。**
> 但「過不了」的定義要精確：**在這台上重現不了某個 CVE，不代表 G4 失敗**——
> 如果原因是那個缺陷在這個 build 裡確實不存在，**那是一個發現，而且要拿去更新 W04-2 的三版橫讀表**。

## W07
*Gloss (added here, not part of the extract):* No formal gate. Twelve sinks under verdict, each verdict pointing back at a report.

## 四、本週 DoD


- [ ] `notes/bughunt.md` ≥ 12 列，每列的判定指得回一份 `reports/`
- [ ] 閘門觸發點扣掉已知 CVE 後的餘集，逐項判定完畢
- [ ] 差分測試台**正對照通過**，分歧點列出
- [ ] 五個 XSS CVE 定位到「參數 → MIB 欄位 → 輸出樣板」
- [ ] 三個沒人讀過的二進位讀完
- [ ] 「相對安全的區域」一節有實質內容

## W08
*Gloss (added here, not part of the extract):* No formal gate. Every chapter carries content, and every claim points at a regenerable artefact.

## 五、本週 DoD


- [ ] 14 章都有內容
- [ ] 每一條主張指得回一個**可重新產生**的產物
- [ ] 圖表用 Mermaid，截圖只用在本質上視覺的東西
- [ ] 第 12 章（工具 bug）和第 14 章（沒證明什麼）**都不是敷衍的**
- [ ] 第 13 章有可跑的閘門，不只是建議清單

## W09
*Gloss (added here, not part of the extract):* Published, legible to a stranger in ten minutes, one full chain, and every claim naming the binary it was measured on.

## 四、G5 驗收門檻


- [ ] writeup 公開，陌生人 10 分鐘看懂
- [ ] 一條完整攻擊鏈：描述 → binary → PoC
- [ ] 工程敘事完整（硬體 + 軟體 + 工具）
- [ ] 法律語句齊備、原始研究者致謝
- [ ] **每一條主張標明測於哪個 binary**
- [ ] 發布前四道過濾全過，特別是**沒有跟揭露政策矛盾的殘留字串**

> ⚠️ **G5 是最終 Gate。通過 = 專案成功。**

## W10
*Gloss (added here, not part of the extract):* No gate. Buffer week.

*This plan states its DoD in the header block above and carries no separate acceptance section.*

---

## Provenance

The SHA-256 of each source, so that a regeneration can be shown to have read the
same bytes. As above: this pins the extract to the source, not the source to a
date.

| week | source file | SHA-256 of the source |
|---|---|---|
| `W01` | `plan/W01_偵察與解包.md` | `29d86bdf235873cdc65019995aaf65cf772ee1e29caf249244b4e74153c0a1f0` |
| `W02` | `plan/W02_硬體存取.md` | `f24755781d09f1d24347b0a8686616a125fed33ca83a21d2b35dabeb69ef325d` |
| `W03` | `plan/W03_Ghidra靜態逆向.md` | `0b05fa608d7e5f2a63a322df510e60322f21c0b6ae8c8572fca2418a2751d213` |
| `W04` | `plan/W04_CVE根因定位.md` | `2193b4cd641fa9a1a86ecb20fdb0dcad333d6de49b090eaa90de323642ea42fc` |
| `W04-2` | `plan/W04-2_補課週.md` | `e71f62187eedf5094cedba6e7c7a0944a3dce4746ed95dff4b7376c8c0e92b54` |
| `W05` | `plan/W05_動態分析.md` | `5e7f52a4981ef5799b558352a171924e208b8fc7f440fcf121ad31efda87df58` |
| `W06` | `plan/W06_PoC重現.md` | `930fdf6c54ca7f505a4f7254d6e93eaf586b005a913caf08b33b28a0cefafcba` |
| `W07` | `plan/W07_BugHunt.md` | `566bc0448a2975c4f097adc451d8b058b7bbb1fe26fb36ff8ee9d3bcffe80b27` |
| `W08` | `plan/W08_Writeup初稿.md` | `4183675917fbc7ac2dd5eb0b25db9de3c49612e20097188eaff8630eb2c4518d` |
| `W09` | `plan/W09_Writeup發布.md` | `22df58e637cde6e77fbd76e044e6b6189359cc41354253de7f15fc0a954c38c5` |
| `W10` | `plan/W10_收斂結案.md` | `410d89c37873c8d0f5637db5d615891eb630f347a2eff8790bdc9404b358a184` |

<!-- Generated by tools/extract-gates.py. Do not edit; edit the plan and regenerate. -->
