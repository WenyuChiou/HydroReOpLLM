# README proposal: a guide to the coupling framework

This preserves the earlier layout proposal as design history. The main bilingual
READMEs now implement the generic guide; current examples have their own index.

## Project introduction / 專案介紹

**English:** HydroCNHS with configurable reservoir operations couples
rainfall–runoff modeling, river routing and reservoir release decisions. Users
configure their catchments, river network and reservoir operation modules.
The framework records requested and implemented releases, storage changes,
water balance and audit evidence.

**中文：** 這個框架結合 HydroCNHS 水文產流、河道 routing 與可設定的水庫
放流決策。使用者設定自己的集水區、河網與水庫操作模組，並檢查決策、
實際放流、蓄水、水量平衡及 audit 紀錄。

Place the generic concept figure directly below this introduction.
Keep the English and Chinese pages in the same order.

## Front-page reading order / 首頁閱讀順序

| Step / 步驟 | User task / 使用者工作 | Link destination / 詳細入口 |
|---|---|---|
| 1. Install / 安裝 | Install the package and check the environment / 安裝套件、確認環境 | Installation / 安裝教學 |
| 2. Prepare inputs / 準備資料 | Climate, catchments, river network and reservoirs / 氣象、集水區、河網與水庫資料 | Input formats and units / 格式與單位 |
| 3. Configure / 設定模型 | Hydrology, routing, initial storage and operation units / 水文、routing、初始蓄水與決策單元 | Commented YAML reference / 有註解的 YAML |
| 4. Run / 執行 | Check configuration, run daily simulation, verify outputs / 檢查設定、逐日執行、驗證輸出 | Run commands / 執行指令 |
| 5. Inspect / 查看結果 | Flow, storage, release, balance, audit and trace / 流量、蓄水、放流、平衡與紀錄 | Output reference / 輸出說明 |
| 6. Extend / 擴充 | Change region, network and reservoir count; add a policy / 更換區域、河網、水庫數量或決策模組 | Own-data and multi-reservoir tutorial / 自有資料與多水庫教學 |

## Documentation placement / 文件配置

- **README:** introduction, generic figure, installation and the six-step guide.
  Include short runnable commands once their generic input paths are agreed.
- **Tutorial:** detailed input preparation, complete configuration, execution
  and result inspection. Put concrete case studies in a separate tutorial index.
- **Reference:** YAML fields, units, module interfaces, policy settings,
  physical assumptions, audit rules and trace schema.
- **Developer guide:** extending a decision policy and testing its interface.

首頁保留操作入口。完整設定、模組細節與研究案例放到對應文件，避免新使用者
將個案設定誤認為框架的固定設定。原版 HydroCNHS 的建模、參數與校驗教學
保留連結；水庫操作教學接在同一條模型使用流程上。
