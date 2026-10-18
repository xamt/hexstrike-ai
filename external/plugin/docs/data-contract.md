# 渗透测试记录契约

版本 1。插件身份 `pentest-tools`；远端工具服务 `plugin:pentest-tools:scanner`；本地记录服务 `plugin:pentest-tools:records`；HTML 面板 `pentest-workbench`。

## 真实来源与职责

扫描仅由 Agent 调用远端 pentest-tools MCP。记录服务不连接目标、不代理扫描、不执行 Shell。Agent 在工具调用前后保存脱敏的执行记录，发现资产和验证漏洞后保存证据引用。执行状态是 Agent 报告，不是远端进程遥测。页面只读，不发起扫描或修改记录。

## 统一视图

`get_engagement_view({task_id})` 返回 `{success:true,view:{...}}`。每次读取一个完整原子版本，避免进度和报告统计来自不同时点。view 字段如下：

```text
schemaVersion: 1
taskId: string (服务生成UUID)
revision: integer
title: string
status: planned | running | paused | completed
phase: string
plan?: string (最多20000字符的多行纯文本；新任务默认为空，旧快照可缺省)
planSteps?: PlanStep[] (最多100项；新任务默认为空，旧快照可缺省)
preflight?: Preflight (最近一次Agent留存的MCP检查；缺省表示尚未记录)
targets: string[]
scope: string
exclusions: string[]
createdAt: ISO string
updatedAt: ISO string
assetCount: integer
confirmedCount: integer
suspectedCount: integer
runningCount: integer (记录状态running数量，不是活跃进程数)
assets: Asset[]
findings: Finding[]
activities: Activity[]
attackChains: AttackChain[]
report: Report
```

Asset：`id,kind,value,description,evidenceRefs,observedAt` 必填；kind 为 `ip|domain|service|data`；可选 `parentId,port,protocol,service,sensitivity,dataProfile`。端口为 1–65535 整数，service 类型必须有 parentId、port、protocol、service；parentId 引用已有资产，不能自指或成环。`dataProfile` 只适用于 data 资产，包含必填的 `scale`（测得的规模或明确未知）、`categories`（已知类别，可空）、`sampleStatus`（`not_sampled|metadata_only|redacted`）、`exposure`（已验证可见边界）；仅 `redacted` 时填写不超过500字符的 `redactedSample`。旧任务不要求补字段，报告明确显示未记录。data 资产只描述类别/位置/最小脱敏证据，不保存原始敏感记录。间接发现的每个IP和服务单独建资产，汇总数量不替代明细。evidenceRefs 为相对任务目录的证据文件路径数组，不读其内容。

Finding：`id,title,status,severity,assetIds,description,validation,poc,impact,remediation,evidenceRefs` 必填；status 为 `suspected|confirmed|rejected|remediated`；severity 为 `critical|high|medium|low|info`。所有文本允许多行；PoC 是已观察最小复现的脱敏文本，不执行。confirmed 必须提供非空验证、PoC、影响、修复及至少一个证据引用。assetIds 必须引用已保存资产。未验证线索不计入已确认漏洞统计。

Activity：`id,tool,target,status,startedAt,summary,evidenceRefs` 必填；status 为 `running|succeeded|failed|unknown`；可选 `finishedAt`；工具为实际调用的完整名称。先记录running，收到结果后用同ID更新。状态未知不自动标记失败/成功；超过5分钟未更新的running在页面标记“状态待确认”，不伪称仍在执行。此超时只影响展示，不停止远端任务。

AttackChain：`id,title,status,steps,impact,evidenceRefs` 必填；status 为 `hypothesis|partial|verified`；steps 为 `{findingId,description,verified:boolean}[]`。findingId 引用已有漏洞；verified链要求各步骤已验证且关联confirmed/remediated发现，每条链必须有证据。未证实边不可画成已打通。

Report：`summary,keyFindings,coverage,limitations,recommendations`；summary/coverage 为string，其余为string[]。默认均为空。完整报告正文同时包含任务目标、全部资产、漏洞清单及攻击链，来自同一view。摘要为空时显示“报告尚未整理”，不能生成示例结论；任务未完成时为阶段报告，未验证项由suspected发现、unknown/running活动及limitations共同体现。

PlanStep：`id/title/status/summary/evidenceRefs` 必填；status为`pending/running/completed/blocked`，显示为待执行/执行中/已完成/受阻。标题最多160字符，summary最多4000字符；完成或受阻时summary必须非空。最多100项，按ID整行合并、保留顺序，不支持删除。Activity可选`planStepId`必须引用本任务已有步骤或同次写入的新步骤。

Preflight：`status/checkedAt/server/tool/summary` 必填；status为passed/failed，checkedAt为ISO时间，summary为最多4000字符的非空脱敏结果。此记录来自Agent实际通过宿主调用server_health，不是记录服务主动探测或认证的结果。纯计划/离线报告可以没有检查记录；实际测试按技能强制检查。

记录层门槛：有结构化步骤的任务进入running、步骤进入running或关联步骤的活动进入running时，必须已有或同次保存preflight passed，否则PREFLIGHT_REQUIRED且不增加revision。保存failed会原子地将任务置paused、执行中步骤置blocked并记录原因、运行中活动置unknown且不填写完成时间；待执行和已完成步骤保持原状。不取消远端进程。未完成步骤存在时拒绝任务completed。旧版无步骤记录仍可读写；此约束不是远端扫描执行网关。

## 记录工具

- `open_workbench({})`：只读请求宿主立即打开无任务的HTML实时面板；每次生成新runId，返回pluginId/panelId/runId及panel.open。不创建记录，不查询目标，不要求目标或计划。等待真实任务绑定后才读取面板查询结果。
- `create_engagement({title,targets,scope,exclusions?,plan?,planSteps?})`：创建独立任务目录，revision=1、status=planned，步骤只能为pending；返回task_id、title、revision、task_path（任务目录）、record_path（不可变快照文件）；无扫描。
- `record_progress({task_id,expected_revision,phase?,status?,plan?,planSteps?,preflight?,assets?,findings?,activities?,attackChains?,report?})`：按ID完整行upsert，不支持删除；plan、preflight和report全量替换。验证合并后的引用。修改必须CAS匹配版本；冲突不写入，调用方重新读取后合并，不自动重放扫描。空修改拒绝。
- `get_engagement_view({task_id})`：只读，未知任务返回错误，不伪造空成功。
- `open_engagement({task_id})`：确认任务存在后返回pluginId/panelId/new runId/task_id；先发panel.open，再发context数据事件。不得等待页面查询；不改任务数据。
- `export_report({task_id,expected_revision,format?})`：`format=html` 将该版本完整自包含 HTML 报告保存到任务目录 `reports/report-r<revision>.html`；省略或传 `markdown` 兼容原 `.md` 路径。两种格式均对不可信内容转义，包含资产统计与必需章节；不发网络请求，不更改任务状态，同版本重导出只接受内容相同的文件。

持久数据根目录从显式 `PENTEST_RECORDS_ROOT` 环境变量读取。插件1.0.7映射为 `${DATAAGENT_PROJECT_DIR}/pentest-records`，由宿主展开为工作区内的绝对路径；记录服务不回退到进程cwd。智能体与面板必须解析到同一工作区。升级已有任务时，选择原task_path的父目录，不搬迁、不重建数据。配置变更需要重新加载记录MCP进程，页面刷新不能更新进程环境变量。NOT_FOUND说明记录服务已响应，但当前根目录下找不到该UUID；错误包含任务ID与当前根目录用于对照，不是无漏洞结论。不允许在工具参数中输入任意文件路径；task_id必须UUID。目录权限0700、文件0600；拒绝符号链接和路径逃逸。单个view上限1MiB；记录上限assets500/findings200/activities500/attackChains100；超限报错，不截断伪装完整。保留每次revision快照以追溯，写入原子化、跨进程互斥并有锁定超时；崩溃遗留锁应明确错误，不自动破坏性清理。

插件1.0.5起，create_engagement成功即返回panel.open和context数据事件，不要求plan或planSteps；目标和范围明确后即可打开，再补完整计划。响应保留task_id/title/revision/task_path/record_path，并增加pluginId/panelId/新runId。无计划的新任务phase为“制定测试计划”，首次保存非空计划或步骤后默认变为“计划已记录”；显式phase优先。旧快照不迁移、不推断历史。

1.0.6新增`open_workbench`，用于任务之前显式打开空视图。`activation.autoOpen`不调用工具；必须由技能先调用。MCP结果同时在`_meta`、`structuredContent.dataagentPanelEvents`和单独的工具文本事件行提供同一事件，宿主对同一结果去重；助手不得把普通回复中的JSON当成事件。后续绑定任务时`create_engagement/open_engagement`产生新run，不复用空视图的runId。

record_progress成功保存非空plan仍发打开事件；普通步骤/活动/检查更新、空plan更新、失败请求不发。事件顺序为panel.open、context的data.updated，同一响应使用相同runId；只请求宿主打开，不声明实际加载成功。智能体随后使用宿主read_panel和返回标识检查complete=true、timedOut=false、errors为空及dataSources.view.taskId一致。无需等待资产或漏洞产生；不扫描、不阻塞打开响应等待业务查询。plan纯文本保留换行，全文替换并保留历史；旧schemaVersion=1缺少plan仍可读取。

1.0.4新增步骤和前置检查。仅以planSteps创建计划也自动打开；后续仅更新步骤状态或检查记录不重复打开，实时视图随既有轮询刷新。旧快照不必补字段，不自动将文本拆为步骤或推断健康状态。

## HTML 视图契约

`window.DataAgentPanel` 由宿主注入。state 为 `{mode,document:{data:{runtime:{dataSources,queries}}}}`。
context 数据源的value为 `{taskId,title}`；view 数据源的value为上述view。
唯一查询ID `engagement-view`，固定服务records和工具get_engagement_view，可变参数task_id。autoLoad=false，refreshIntervalSeconds=10。模板在ready收到context后查询一次；新taskId切换时不展示上一个任务的view。宿主负责后续轮询，不在页面追加定时器。快照不查询；已有view时显示冻结内容，否则显示未保存数据。

页面两个主TAB：计划与进度、渗透报告。第一页按 `planSteps` 绘制阶段轨迹，只有 `running` 步骤标为当前阶段；每步保留文字说明，但不重复显示状态列表和计数。旧任务无结构化步骤时显示原文本计划，不推断历史。第一页还显示资产/已确认漏洞/待验证线索/执行中记录计数、由 `status/phase/planSteps/activities` 构成的当前执行卡片，以及 Agent 执行记录；卡片标出最近记录时间与相对年龄，后者不是远端进程心跳。报告页显示资产总数和IP/域名/端口服务/数据资产分项，以及摘要、漏洞统计、关键发现、目标、资产清单、漏洞详情（描述/验证/PoC/影响/等级/修复）、攻击链、未验证项与覆盖限制。面板只读，HTML 导出由 Agent 调用 `export_report` 写入任务目录，不在 iframe 内直接下载。查询失败保留旧值且明确显示错误及旧数据时间。动态内容仅用textContent；不使用innerHTML、外链资源或任意fetch。所有操作键盘可达，支持窄窗和减弱动效。
