# HANDOFF G1

> 面向一个完全没有历史上下文的新对话。
> 本文记录 G1 重新打开后的当前真实状态，以及修复后进入 G2 的唯一安全路径。
> 接手者不得仅凭候选分支中的代码、测试或报告宣称项目已经达到 M2/M3/M4。

## 1. 新对话首先要做什么

按以下顺序完整阅读：

1. `AGENTS.md`
2. `HANDOFFG1.md`（本文）
3. `docs/PROJECT_STATE.md`
4. `docs/evidence/g1/` 下的 10 个证据注册表
5. `docs/audits/g1-feature-branch-audit.md`
6. 开始 G2 前阅读 SR-MAPPO Problem 2 技能中的：
   - `references/parameter-and-resource-contract.md`
   - `references/gis-and-event-contract.md`

然后核对 Git 状态、远端哈希和 PR 状态。不要先写代码、合并候选分支、
启动训练或修改论文正文。

## 2. 我们在做什么任务

本仓库是毕业论文第二个问题的唯一权威工作记录。研究问题是：

> 面向道路约束场景，由多架无人机执行喷洒、由一辆移动药液补给车沿道路
> 提供农药补给的空地异构协同系统，并以 SR-MAPPO 作为旗舰算法框架。

最终目标不是“让一段训练代码跑起来”，而是建立一条可复现、可审计、可供
论文盲审追踪的完整证据链：

```text
参数/文献来源
-> 冻结配置和 Git 提交
-> 不可变 run ID 与原始 episode 日志
-> 校验后的长表
-> 配对统计摘要
-> 图表及 artifact manifest
-> 论文陈述
```

最终系统要覆盖：参数注册、离线 GIS 道路模型、物理尺度、药液请求与服务事件、
异构 SR-MAPPO、公平基线、资源激活、试运行、正式作业、封存测试、配对统计、
图表和论文生成。

OSM 只能作为道路约束仿真的输入，绝不能被描述为真实田间部署证据。

## 3. 当前门禁结论

截至 2026-08-20：

- G0：通过并已持久化到 GitHub。
- 修正后的 G1 曾在 `0719483...` 被验收并持久化；本次交接的两名独立审查代理
  又发现四项此前遗漏的 G1 契约阻断，见第 8 节。
- 按“停在第一个失败门禁”的规则，G1 已重新打开，先前的 G2 放行结论被暂停。
- 当前最高成熟度仍为 `M1`，即设计/规范证据。
- 当前门禁：限定范围的 G1.1 合同修复与重新验收。
- 后续门禁：`G2`，确定性模型验证；**现在不能开始 G2 实现**。
- 当前没有任何第二问题正式实验结论。
- 训练、正式实验和封存测试均未获授权。
- 封存测试种子 `30000-30099` 必须继续保持锁定。

当前允许使用的措辞是“设计、定义、提出、建立规范、计划验证”。在 G1.1 修复
重新验收且 G2 真正实现、验证、提交、推送并登记之前，不得把成熟度写成 M2。

## 4. Git、分支与 PR 的精确状态

权威仓库：

`C:/Users/RZX/Documents/ChatGPT/Second`

远端：

`https://github.com/rzx127097-create/Second.git`

交接时本地分支：

`codex/problem2-g0-orchestration`

本次交接审计开始时的本地与远端分支共同 HEAD：

`071948305a074d7de0e6d46f4ac591826cc57f0f`

提交信息：

`docs: finalize corrected g1 persistence`

创建本文前的基线核对结果：工作树干净，本地分支与
`origin/codex/problem2-g0-orchestration` 同步。创建本文后工作树会包含本文和
项目状态更新；接手者必须以本文最后的 GitHub 持久化记录和实际 `git status`
为准，不能继续把 `0719483...` 当作交接文件本身的提交。

交接内容提交：

`ece353583fca5e222c405270c05110660cd416f1`

提交信息：

`docs: add g1 handoff and reopen contract gaps`

该提交已推送；推送后本地 HEAD、upstream 和 `git ls-remote` 三者均为
`ece3535...`。其后的 persistence-record 提交应通过实际 `git log -1` 核对。

远端 `main`：

`2643753855c385253951dfad2c225be0b09b7e00`

未受信任候选分支：

`origin/feature/problem2-code-framework`

候选分支提交：

`52a92c00467fbc3fa6a81e0fcb43469b2f8d1940`

G0/G1 拉取请求：

`https://github.com/rzx127097-create/Second/pull/1`

交接内容推送后 PR #1 状态：`open`、非 draft，目标为 `main`，源提交为
`ece3535...`。GitHub REST API 当时仍在重新计算合并状态，返回
`mergeable=null`、`mergeable_state=unknown`；接手者必须重新查询，不能沿用
推送前针对 `0719483...` 的 `clean` 结果。

### Git 上现在卡在哪里

研究门禁当前卡在第 8 节的四项 G1 合同缺口。PR #1 虽可干净合并，但在 G1.1
修复完成前不要合并这个已知不完整的 G1 版本。限定修复、独立复审和 GitHub
持久化完成后，再重新核对 PR #1 的远端哈希、CI 和 review 状态，并在取得用户
明确合并授权后将更新后的 PR 合并到 `main`，再创建：

`codex/problem2-g2-deterministic-validation`

若新会话尚未取得合并授权，不得擅自修改 `main`。G1.1 应在当前隔离分支上完成；
修复验收后可从新的已推送 G1 HEAD 建立隔离 G2 分支/工作树并记录准确基线。
不要直接在未修复的 `0719483...` 上开始 G2，也不要把旧 `main` 错记成 G1 基线。

## 5. G0 已完成的工作

G0 已完成并验证：

- 将 `Second` 注册为第二问题唯一权威仓库；
- 盘点并保护第一问题仓库中的用户未提交修改；
- 盘点 `D:/Pycharm/Locust_rl`、规划文档和 OSM 输入；
- 记录 OSM 输入 SHA-256；
- 建立项目门禁、证据链、输出根目录和 GitHub 持久化规则；
- 确认 `origin/feature/problem2-code-framework` 只能作为待审计候选输入；
- 将 G0 提交、推送，并在 `docs/PROJECT_STATE.md` 记录验证与哈希。

G0 的详细交接仍保留在 `HANDOFFG0.md`，但后续状态以本文和
`docs/PROJECT_STATE.md` 为准。

## 6. G1 已完成的工作

### 6.1 十个权威 G1 注册表

已建立：

1. `docs/evidence/g1/parameter_registry.yaml`
2. `docs/evidence/g1/literature_source_ledger.yaml`
3. `docs/evidence/g1/experiment_matrix.yaml`
4. `docs/evidence/g1/scenario_seed_manifest.yaml`
5. `docs/evidence/g1/job_identity_contract.yaml`
6. `docs/evidence/g1/raw_episode_schema.yaml`
7. `docs/evidence/g1/validated_long_table_schema.yaml`
8. `docs/evidence/g1/artifact_manifest_schema.yaml`
9. `docs/evidence/g1/sealed_test_lock.yaml`
10. `docs/evidence/g1/output_root_contract.yaml`

这些注册表定义了 21 个规范指标、精确原始/校验长表结构、11 个公平性布尔
约束、种子协议、不可变作业身份、artifact 结构、封存锁和输出根目录。

### 6.2 G1 审计工具与报告

实现并验证：

- `scripts/audit_g1_registries.py`
- `scripts/audit_g1_feature_branch.py`
- `tests/test_g1_registries.py`
- `tests/test_g1_feature_branch_audit.py`
- `outputs/problem2_sr_mappo_v1/g1/registry-audit.json`
- `outputs/problem2_sr_mappo_v1/g1/candidate-branch-audit.json`
- `docs/audits/g1-feature-branch-audit.md`

最终新鲜验证结果：

- `python -m pytest -q` -> `45 passed`
- G1 专项测试 -> `38 passed`
- 注册表审计 -> `status=pass`，10/10 文件、21 个指标、10 个参数、
  5 个来源、0 个错误、1 个 pending-source 警告
- 候选分支审计 -> `status=pass`，210/210 变更路径完整呈现，
  5 个关键 Git blob 被检查，保留 20 个未解决问题
- `git diff --check` -> 无错误
- 独立限定范围复审 -> 原始阻断项均已修复，无新的 Critical/Important 问题

### 6.3 G1 最终有效提交链

原始 G1 曾经被错误地认为完成，随后被独立审查重新打开。最终有效修复与
持久化链包括：

- `ebada80` - `fix: harden g1 evidence registration audits`
- `57e3347` - `docs: record g1 final-review remediation`
- `9146600` - `fix: close g1 audit validation gaps`
- `af388c7` - `docs: record g1 fix round 1 evidence`
- `8969e5e` - `docs: accept g1 audit remediation`
- `c274356` - `docs: persist corrected g1 pushed hash`
- `0719483` - `docs: finalize corrected g1 persistence`

`0719483...` 是本次交接审计开始时的 G1 验收 HEAD。不要把早期的“16 passed”
或第一次 G1 persistence 记录当作最终验收结论；也不要忽略本次交接审计在其后
重新打开的 G1.1 阻断。

## 7. 候选代码分支的真实含义

`origin/feature/problem2-code-framework` 包含大量看起来已经完成的代码：

- `src/problem2/road/`、`domain/`、`environment/`、`algorithms/`；
- 配置、测试、训练/评估脚本；
- M3 pilot、formal readiness、road audit 等报告；
- 共 210 个相对 `origin/main` 的变更路径。

但 G1 只对其进行了**只读 Git 对象审计**。审计 `status=pass` 只表示审计器
成功运行且完整呈现了输入，不表示候选实现、测试、报告或成熟度声明被接受。

当前分类：

- 21 个路径可作为设计输入；
- 169 个路径需要独立重新验证；
- 20 个报告/证据路径不能作为当前证据；
- 20 项未解决发现仍保留。

关键冲突包括：

- 12 个工程参数尚未独立验证；
- 候选训练种子 `[0, 1, 2, 3, 4]` 与冻结种子冲突；
- 候选封存种子与 `30000-30099` 不匹配；
- 候选尺度与冻结六尺度协议不匹配；
- 候选 artifact 与 sealed-unlock 实现未被 G1 接受；
- 候选文档/测试含过早 M2/M3/M4 声明；
- 存在 HAPPO、拼写变体和 `AG-SR-MAPPO` 的实质性引用。

因此绝对不要整分支 merge 或整批 cherry-pick。G2 只能逐模块读取候选 Git
blob，先写当前契约下的失败测试，再决定受控复制、重写或拒绝。

## 8. 当前真正未完成或受阻的事项

### 当前阻止进入 G2 的 G1.1 问题

本次交接的事实审查对照实际 YAML、验证器和 SR-MAPPO Problem 2 合同后确认：

1. **服务合同不完整。** `parameter_registry.yaml` 没有登记单次
   `vehicle.service_cap`，也没有登记或明确推导 request safety margin/threshold；
   但 experiment matrix 已要求 `equal_service_cap: true`，G2 状态机也依赖请求
   阈值。必须补充名称、符号、单位、范围、来源、换算、状态和 scope；不得从候选
   分支复制未验证数值。
2. **封存解锁语义不明确。** `sealed_test_lock.yaml` 的 `unlock_count: 1` 无法区分
   “最多允许解锁一次”与“已经解锁一次”。应至少拆成
   `max_unlock_count: 1`、`actual_unlock_count: 0`、`unlocked_at: null`、
   `unlock_commit: null`，并增加 fail-closed 测试。封存集实际上从未访问。
3. **artifact schema 对正式产物仍 fail-open。** 当前允许
   `generator_commit: null`、可缺少 `created_at`，也没有 generator script
   hash/version 和 output hash。`design_only` 可以保留空执行 provenance，但
   `validated`/`locked_summary` 必须条件性要求非空提交、创建时间、生成器 hash/
   version 和输出 SHA-256。
4. **验证集调参规则与实验协议冲突。** `scenario_seed_manifest.yaml` 当前把
   validation 标成 `tuning_allowed: false`，而冻结实验合同要求 validation scenes
   用于 checkpoint 选择和算法调参。必须改成明确且机器可验证的用途，仍禁止
   sealed-test 调参。

限定 G1.1 修复必须同时更新 YAML、验证器、负向测试、报告和项目状态，经过独立
复审、主控新鲜验证、提交、推送和 pushed-hash 登记后，才能重新放行 G2。

### 不属于当前 G1.1 阻断但仍须保留

- PR #1 尚未合并；在 G1.1 完成前不要合并旧验收版本。
- 四个外部工程来源记录仍为 pending；它们不阻止未来测试确定性机制，但会阻止
  最终参数冻结和强工程真实性表述。
- 候选分支 20 项发现未解决；它们不阻止未来重建 G2，但阻止直接接受候选实现。

### 仍然完全未完成

- 当前权威 G1 分支没有 `src/problem2/` 和正式 `configs/` 实现树；
- 没有被当前分支接受的道路缓存或 G2 实现；
- 没有通过当前契约验证的服务状态机和资源守恒模型；
- 没有通过 G3 的异构 MARL；
- 没有 G4 资源激活证据；
- 没有第二问题训练、正式原始日志、校验长表、配对统计或锁定图表；
- 没有任何证据支持“移动补给有效”或“SR-MAPPO 最优”。

## 9. 冻结且不可擅自改变的研究合同

### 算法身份

- 公开名称只能是 `SR-MAPPO`。
- 第二问题称为 SR-MAPPO 的空地异构扩展。
- 不实现、不引入、不设置 HAPPO 基线。
- 不改名为 `AG-SR-MAPPO` 或其他公开算法名。

### 资源边界

- 主补给资源仅为农药/药液。
- 电池补给保持 inactive，除非未来有单独激活审计并登记。
- 一辆移动补给车；一辆车同一时间最多服务一架无人机。
- 移动与固定补给比较必须资源量和服务能力匹配。

### 方法族

- `sr_mappo_mobile`
- `sr_mappo_fixed`
- `sr_mappo_astar`
- `mappo_mobile`
- `sr_mappo_two_stage`

### 正式尺度与步数

| Scale | 最大物理决策步 |
|---|---:|
| `g20x20_d2` | 150 |
| `g20x30_d3` | 180 |
| `g20x40_d3` | 220 |
| `g30x30_d3` | 220 |
| `g30x40_d4` | 280 |
| `g30x50_d4` | 350 |

### 种子与阈值

- 训练种子：`42`, `123`, `2024`, `3407`, `7919`
- 验证场景：`20000-20049`
- 封存测试：`30000-30099`
- 主要成功阈值：`reduction_rate >= 0.85`
- 输出根目录：`outputs/problem2_sr_mappo_v1`

## 10. G2 的任务边界

以下内容是 G1.1 重新验收后的 G2 边界。G2 只验证确定性模型，不训练 RL，
不跑 formal jobs，不解锁 sealed test。

G2 应覆盖：

1. GraphML 离线读取和来源哈希；
2. 经纬度到本地米制 CRS 的投影；
3. 道路折线加密、四连通栅格拓扑和连通分量检查；
4. 仅修复可证明的小离散化断口，并记录每条插入连接；
5. `.npz` 缓存和 metadata JSON 的完整 provenance；
6. 物理速度、米制边长和跨步残余距离；
7. request 与 vehicle 的独立状态机；
8. 确定性请求选择、预约、到达、锁定服务、部分补给和完成边界；
9. 冻结并测试事件优先级；
10. 资源守恒、非负约束、终止边界和固定种子事件复现。

### 冻结单位换算和服务时长

G2 设计规范必须在实现前冻结并测试以下换算：

```text
distance_per_step_m = speed_m_per_s * dt_s
spray_per_step_L = flow_L_per_min * dt_s / 60
transfer_per_step_L = transfer_L_per_min * dt_s / 60
service_target_delta_L = min(UAV free capacity,
                             configured service cap per service,
                             vehicle remaining inventory)
service_steps = ceil((setup_s + service_target_delta_L / transfer_L_per_s) / dt_s)
```

`configured service cap` 必须定义为单次服务可转移总量上限，不能与单步转移率
混用。该参数必须先在 G1.1 注册，不得从候选分支取值。规范还必须冻结：采用整步
`ceil` 后，药液在声明的服务完成边界一次性记账；在此前 servicing 步骤不得提前
入账。非整数服务时长、零/非零 setup time、不同 `dt` 和恰好整除边界都要有测试。

### 冻结状态转换

请求主链必须是：

```text
pending -> reserved -> serving -> completed
```

`cancelled` 只能由设计规范中明确冻结的 terminal/invalid 规则触发。必须逐条列出
合法边、自环和拒绝的非法边；请求原始时间戳必须跨 reservation/service 保留，
completed 请求不得再次预约或服务。

车辆主链必须是：

```text
idle -> transit -> serving -> idle
```

任何 transit 取消/返回 idle 的例外也必须在 transition table 中明确冻结。库存耗尽
是独立资源标志，不是 vehicle mode。

### 冻结单步事件优先级

阶段 1 必须把唯一编号事件序列写入 G2 设计规范，默认合同顺序为：

1. 从状态 `t` 生成 observations 和 action masks；
2. 采样并记录 UAV/vehicle action 及旧 log-probability；
3. 执行合法移动，非法动作只能被 mask/reject 为冻结的 stay 语义；
4. 生成阈值请求；
5. 预约一个当前可服务且未预约的请求；
6. 启动或推进锁定服务；
7. 在声明的完成边界转移资源；
8. 推进害虫、风场和药液场动态；
9. 计算 reward 与 outcome；
10. 应用 termination 并按稳定顺序写出全部事件。

必须明确测试移动到达、请求生成、预约、零 setup 服务、补给完成、喷洒消耗和
episode 终止发生在同一步时的先后关系。G2 负责由确定性状态生成合法动作集合、
服务锁 mask、拒绝非法状态转移，并保证非法动作执行率为零；G3 再负责 masked
probability、保存的旧 mask/log-prob 重放和 PPO 一致性。

### 必须保存的道路缓存 metadata

- 源文件 SHA-256；
- 源/目标 CRS；
- 地理 bbox、投影 bbox 和完整 raster transform；
- grid shape 与 cell resolution；
- 折线加密间距、gap repair 阈值和规范化生成配置 hash；
- topology convention；
- component sizes；
- repair count，以及每次 repair 的原始/栅格端点、米制距离、冻结阈值和原因；
- adjacency checksum；
- 生成代码 Git commit/version；
- 原始 road node/edge 到栅格节点的映射。

## 11. 推荐的 G2 子代理驱动计划

用户在 2026-08-20 本次对话中明确选择“子代理驱动执行”。本文将该选择登记为
后续执行偏好，但它不等于合并 PR、解锁 sealed test 或修改受保护资产的授权。

### 阶段 -1：完成限定 G1.1 修复

1. 使用 `receiving-code-review` 复核第 8 节四项阻断。
2. 使用 TDD 修复注册表、验证器和负向测试；不扩展到 G2 实现。
3. 重新生成 G1 报告，但不得静默覆盖旧证据；先保留旧 hash/提交，再从已提交
   生成器生成带新 provenance 的报告。
4. 进行独立规范审查和代码质量审查。
5. 主控运行完整测试与两个 G1 审计 CLI。
6. 提交、推送并在 `docs/PROJECT_STATE.md` 登记新 G1 HEAD 和验证结果。
7. 只有 G1.1 再次明确放行后，才能执行下面的 G2 阶段。

### 阶段 0：建立干净基线

1. 再次核对更新后的 PR #1、CI/review 状态和远端三个分支哈希。
2. 取得用户明确授权后才可将 PR #1 合并到 `main`；未获授权则保持 `main` 不变，
   以 G1.1 新验收并推送的 HEAD 为准确基线。
3. 若已合并，拉取并验证更新后的 `main`；若未合并，直接验证新 G1 HEAD。
4. 使用 `using-git-worktrees` 建立隔离分支/工作树：
   `codex/problem2-g2-deterministic-validation`。
5. 记录基线提交和工作树状态。

### 阶段 1：先写 G2 规范和执行计划

在任何实现前：

- 用 `brainstorming` 明确 G2 边界与候选代码复用策略；
- 将 G2 设计规范存入 `docs/superpowers/specs/`；
- 用 `writing-plans` 生成逐任务 TDD 计划到 `docs/superpowers/plans/`；
- 每个子任务必须声明输入、输出、允许修改的文件、测试、验收标准、未解决项和
  当前成熟度门禁。

### 阶段 2：按边界派发独立实现代理

推荐依赖 DAG：

```text
道路来源/缓存
-> 投影/拓扑
-> 物理运动
-> 服务事件
-> 资源守恒与跨模块复现
```

接口和文件所有权必须在派发前冻结。资源/复现代理依赖前四层，不是可与其同时
写共享文件的独立任务。推荐拆分：

1. **道路来源与缓存代理**：GraphML 离线读取、hash、CRS/bbox、缓存失效和
   provenance。
2. **投影与拓扑代理**：米制投影、折线加密、四连通图、连通分量、A*/Dijkstra
   一致性和 gap repair ledger。
3. **物理运动代理**：米/秒、`dt`、米制边长、残余行程预算和跨尺度一致性。
4. **服务事件代理**：request/vehicle 状态机、确定性 FIFO+UAV ID tie-break、
   reservation、busy lock、partial refill 和终止边界。
5. **资源与复现代理**：守恒、不为负、固定种子事件序列和属性测试。

有共享接口依赖的任务不能并行写同一文件。先冻结数据类型、函数签名、缓存 schema、
事件 schema 和每个代理的唯一写集，再按依赖顺序派发；只有真正独立且不共享状态
的任务才可并行。

每个实现任务遵循：新代理写失败测试 -> 主控确认 RED -> 最小实现 -> GREEN ->
规范审查代理 -> 代码质量审查代理 -> 修复 -> 小提交。

### 阶段 3：集成与独立总审查

- 集成道路、运动、事件和资源层；
- 运行 G0/G1 回归以及全部 G2 测试；
- 先提交干净的生成器代码、配置和测试；
- 从该生成器提交运行新鲜验证并生成缓存/审计报告，使 provenance 指向这个已存在
  的生成器提交，而不是未提交工作树；
- 派发独立最终审查代理，重点找 fail-open、状态机边界和守恒漏洞；
- 主控在最终证据候选上重新运行全部验证，不接受子代理仅口头声称通过；
- 提交并推送 G2 证据内容提交；
- 在 `docs/PROJECT_STATE.md` 记录内容提交哈希、验证命令和结果，创建并推送单独的
  persistence-record commit；
- 最后核对本地 HEAD、upstream 和 `git ls-remote` 哈希一致；
- 只有上述记录完整，才可宣告 G2 完成或把成熟度提升到 M2。

## 12. G2 最低测试验收清单

至少必须包含并通过：

- 已知节点对的投影与米制距离 sanity check；
- 源 hash、源/目标 CRS、bbox、raster transform、shape、cell resolution、折线
  加密间距、gap 阈值、topology convention、生成配置或代码版本任一变化时缓存失效；
- 抽样节点对 A* 距离与 Dijkstra 一致；
- 四连通约束和连通分量记录正确；
- gap repair 仅发生在冻结阈值内且逐条留痕；
- 距离、喷洒量、转移量和服务步数严格遵守冻结单位换算；
- 非整数服务时长、零/非零 setup time、不同 `dt` 和恰好整除边界正确；
- 不同网格尺度不把“一步”等同为“一格”，残余距离正确累计；
- 单步跨越多条不等长边、预算恰等于边长和长期累计无漂移；
- 六尺度共享物理区域时保持物理速度，路线长度以米输出；
- request/vehicle transition table 每条合法边、自环和非法边均被测试；
- 同步请求按可服务请求 FIFO、同时间按 UAV ID 稳定打破平局；
- 不可达旧请求不会阻塞附近可服务请求；
- terminal/invalid 以外不得取消，请求时间戳保留，completed 请求 exactly once；
- 一车忙碌时多 UAV 到达，不能并发服务；
- 一架 UAV 不会被多车/多次重复预约；
- 部分补给、恰好耗尽、零库存和浮点容差边界；
- 转移量严格等于
  `min(UAV free capacity, service cap, vehicle remaining inventory)`；
- 每次 transfer 均满足
  `vehicle decrement == UAV increment == delta`，且 event ID/request ID 对应唯一；
- 服务锁下合法动作集合稳定，非法 masked action 执行率为零；
- 同一步到达/请求/预约/服务/转移/喷洒/终止遵守冻结优先级；
- 最后一个服务步骤恰好结束 episode 的边界；
- 同一固定种子跨独立进程的事件序列、稳定排序和事件摘要逐项一致；
- 初始总药液减喷洒/使用量等于最终总药液，误差在冻结容差内；
- 任何药液量不得为负；
- 冻结 G1 基线提交上的完整测试集不得回归，并记录本次实际 collected/passed 数。

## 13. 已经踩过、绝对不要再踩的坑

### G1 审计与证据坑

1. **验证器 fail-open**：YAML 类型错误、字段缺失或结构错误不能被默认值吞掉。
2. **把审计执行成功当作证据通过**：`candidate audit status=pass` 不等于候选
   代码/成熟度被接受。
3. **错误处理 `git grep` 返回码**：0 是命中，1 是无命中，2 及以上是执行错误，
   必须 fail closed 并保留真实失败命令。
4. **只在个别注册表检查资源边界**：pesticide-only 和 battery-inactive 必须递归
   检查全部注册表中的结构化键。
5. **路径被截断或静默遗漏**：候选审计必须证明 210/210 路径都被呈现，不能用
   输出长度限制隐藏路径。
6. **报告 provenance 陈旧**：生成器代码、生成器提交、脚本 hash、输入 hash 和
   报告必须对应；代码改完后旧报告不能继续使用。
7. **只相信子代理测试摘要**：主控必须在最终提交候选上重新运行测试和审计。
8. **第一次通过就关闭门禁**：G1 的第一次“完成”后来被独立审查推翻；所有重要
   门禁都必须有独立规范审查和代码质量审查。

### G2 模型坑

9. 不要在线静默下载新 OSM；必须离线读取已登记源文件。
10. 不要直接在经纬度上计算速度和距离；必须先投影到米制 CRS。
11. 不要在六个尺度中都定义“一步移动一格”；速度应按米/秒和 `dt` 推进，并
    保留不足一条边的残余距离。
12. 不要只保存 road mask；必须保存 `.npz` 数据、metadata、映射、拓扑校验和。
13. 不要为了连通性随意补路；只能修复冻结阈值内可证明的栅格化断口并逐条记录。
14. 不要让不可达的早期请求永久阻塞可服务请求。
15. 不要允许车辆同时服务多架 UAV，也不要允许同一请求被重复预约。
16. 不要把库存耗尽建模成 vehicle mode；它是独立资源标志。
17. 不要丢弃部分补给，也不要把服务量写成配置常数；必须取三个上限的最小值。
18. 不要让药液出现负数，不要用宽松截断掩盖守恒错误。
19. 不要在环境内部覆盖已经采样的动作；事件锁定必须通过合法状态/动作约束表达。
20. 不要在没有冻结事件顺序时写集成测试，否则同一步请求、到达、转移和终止会
    产生不可复现的边界差异。

### 研究与仓库坑

21. 不要整分支合并/cherry-pick `feature/problem2-code-framework`。
22. 不要接受候选种子 `[0,1,2,3,4]` 或候选尺度覆盖 G1 冻结协议。
23. 不要引入 HAPPO、`happpo` 或 `AG-SR-MAPPO`。
24. 不要启用电池补给；当前只补农药。
25. 不要把第一问题历史数字当成第二问题正式因果证据。
26. 不要把 OSM 仿真输入写成真实部署验证。
27. 不要在 G2 训练、跑 formal、访问 sealed test 或写“显著优于”。
28. 不要修改保护的第一问题仓库、外部 OSM 源文件或既有 Word 文件。
29. 不要把第二问题输出写入 `outputs/sr_mappo_paper_v1`；只能写入冻结根目录。
30. 不要使用宽泛 `git add .`；先检查状态并只提交当前任务文件。
31. 不要 force-push、reset/rewrite 证据历史或覆盖已有报告。

## 14. 受保护的外部资产

未经用户后续明确授权，不得修改：

- 第一问题仓库：
  `C:/Users/RZX/Desktop/论文/毕业论文/locust-rl-paper`
- 基础项目和 OSM 输入：
  `D:/Pycharm/Locust_rl`
- 第二问题规划证据：
  `C:/Users/RZX/Desktop/论文/小论文/第二个问题/分析`
- 本仓库外的既有 Word 论文文件

第一问题仓库在 G0 时为：

- HEAD `1ca9e5ccc5f77ed775cd2b607dd70d635720accf`
- 13 个与 SR-MAPPO 奖励敏感性相关的预先存在的 modified/untracked 路径

这些修改是用户工作，绝对不能 reset、checkout、revert、覆盖或混入第二问题。
完整清单和 Word 文件 hash 见 `docs/PROJECT_STATE.md`。

只读 OSM hash：

- `jodhpur_drive.graphml`:
  `B3AF36EFBFC87FFF30BD61D204283DC40C5B8C83A80BA0EE09F3DA5EF52A9462`
- `jodhpur_buildings.geojson`:
  `08A81DF6C8FA401014ACD161661072714D9231B2B95173CBE932C86FE57F37DB`
- `jodhpur_green.geojson`:
  `B80F54C7C03EE42B4F8E8A55BFBCFBD4B7A166ED5E3EB97CD443069398CE0647`

## 15. 新会话建议执行的核对命令

```powershell
Get-Content -Raw AGENTS.md
Get-Content -Raw HANDOFFG1.md
Get-Content -Raw docs/PROJECT_STATE.md
git status --short --branch
git rev-parse HEAD
git rev-parse '@{upstream}'
git ls-remote origin refs/heads/main refs/heads/codex/problem2-g0-orchestration refs/heads/feature/problem2-code-framework
python -m pytest -q
$tmpAudit = Join-Path $env:TEMP ("problem2-g1-audit-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $tmpAudit | Out-Null
python scripts/audit_g1_registries.py --root docs/evidence/g1 --report "$tmpAudit/registry-audit.json"
python scripts/audit_g1_feature_branch.py --base origin/main --candidate origin/feature/problem2-code-framework --markdown "$tmpAudit/candidate-branch-audit.md" --json "$tmpAudit/candidate-branch-audit.json"
git diff --check
git status --short
```

上述只读预检把报告写入一次性临时目录，避免刷新时间戳或覆盖仓库内的权威 G1
报告。只有明确进行证据再生成并遵守两阶段 provenance 流程时，才可更新仓库报告。

本机当前没有可直接调用的 `gh` 命令。PR 状态可以通过 GitHub 页面或 GitHub
REST API 核对；不要因为 `gh` 缺失而猜测 PR 已合并。

## 16. G2 完成的定义

只有同时满足以下条件，才能宣告 G2 完成：

1. 所有 G2 确定性组件在权威 G2 分支中实现；
2. 本文第 12 节的测试和所有 G0/G1 回归通过；
3. 道路缓存和每份审计报告都具有可复核 provenance；
4. 独立审查没有未解决的 Critical/Important 问题；
5. 未执行训练、formal jobs 或 sealed-test 访问；
6. 没有修改任何受保护外部资产；
7. G2 代码、测试、配置、报告和文档已提交并推送；
8. `docs/PROJECT_STATE.md` 已记录验证命令、结果和推送提交哈希；
9. 本地 HEAD 与远端 G2 分支哈希一致；
10. 只有上述证据完整后，项目才可提升为 M2 并进入 G3。

## 17. 一句话交接结论

**G1 曾在 `0719483...` 被验收，但本次交接审查确认四项新的 G1 合同阻断，现已
重新打开；下一会话必须先以子代理 + TDD + 双阶段独立审查完成限定 G1.1 修复、
重新验证并持久化，之后才可在新 G1 HEAD 上启动 G2，绝不能直接相信或整合候选
分支的成熟度。**
