# 基于 nanobot 的健身 Agent 开发现状与技术路线说明

## 1. 文档目的

本文档用于系统说明我们当前基于 `nanobot` 已经开发完成的内容、正在运行的技术栈、当前系统所处阶段，以及下一阶段将继续采用的技术路线和实现方法。

和前一版文档相比，这次更新已经把“规则路由”阶段纳入当前现状，而不再只是未来规划。也就是说，这份文档现在描述的是：

- 健身业务基础版已经完成
- 规则路由版已经完成
- LLM 路由尚未接入

因此，这份文档既是当前阶段的开发交接文档，也是下一步进入 LLM 路由前的技术基线说明。

---

## 2. 项目当前定位

当前项目是一个基于 `nanobot` 二次开发的健身训练与饮食协同 Agent。

如果按阶段划分，目前可以拆成三层：

1. 已完成：业务基础版
2. 已完成：规则路由版
3. 未完成：LLM 路由版

因此，当前项目的准确定位应该是：

**一个已经具备完整健身业务闭环，并且已经支持规则驱动自然语言交互的 Fitness Agent 原型。**

这意味着它已经不再只是一个显式命令式 CLI 工具，而是已经具备了初步的 Agent 交互形态。

---

## 3. 我们目前已经开发了什么

### 3.1 已完成的业务闭环

当前已经完成并且代码中已经存在的业务能力包括：

- 用户健身画像建档
- 用户画像局部更新
- 用户画像查询
- 周训练计划生成
- 周训练计划查询
- 每日训练反馈打卡
- 打卡历史查询
- 基于反馈的规则化调整建议生成
- 调整建议查询

这意味着系统已经具备完整最小闭环：

1. 保存用户画像
2. 根据画像生成训练计划
3. 用户按天打卡反馈
4. 系统基于反馈生成调整建议
5. 用户可以回看画像、计划、打卡和建议

### 3.2 已完成的核心数据模型

当前已经实现的核心结构化模型包括：

#### 1. 用户画像 `UserProfile`

当前支持字段包括：

- `user_id`
- `gender`
- `age`
- `height`
- `weight`
- `goal`
- `experience_level`
- `training_days_per_week`
- `session_duration`
- `environment`
- `diet_constraint`
- `current_split`
- `weak_points`
- `injury_notes`
- `created_at`
- `updated_at`

#### 2. 周计划 `WeeklyPlan`

当前支持：

- 计划 ID
- 用户 ID
- 周起始日期
- 目标类型
- 计划版本
- 生成原因
- 每日计划内容
- 生成时间

其中每日内容内部继续拆分为：

- `PlanDay`
- `ExercisePlan`

因此计划本身已经是结构化数据，而不是纯文本拼接。

#### 3. 每日反馈 `DailyFeedback`

当前支持：

- 是否训练
- 已完成动作
- 完成度
- 疲劳等级
- 酸痛描述
- 饮食达标情况
- 额外备注
- 日期和创建时间

#### 4. 调整建议 `AdjustmentSuggestion`

当前支持：

- 建议 ID
- 用户 ID
- 反馈覆盖区间
- 调整类型
- 建议正文
- 触发原因
- 生成时间

### 3.3 已完成的输入归一化

当前系统已经具备一层关键的输入归一化能力，这层能力既服务于 CLI，也服务于规则路由。

#### 1. 目标归一化

例如可以把以下表述归一为标准目标：

- “减脂和增肌”
- “边减脂边增肌”
- “recomp”
- “新手”
- “入门”

归一后的目标包括：

- `瘦肌增肌`
- `减脂保肌`
- `新手入门`
- `增肌`
- `减脂`
- `维持`

#### 2. 训练经验归一化

例如：

- “零基础”
- “刚开始健身”
- “系统健身三个月”
- “练了一年”

归一后映射为：

- `新手`
- `初级`
- `中级`

#### 3. 训练环境归一化

例如：

- “学校”
- “学校健身房”
- “校园”
- “在家”
- “寝室”

归一后映射为：

- `校园健身房`
- `家里`
- `宿舍`
- `商业健身房`

#### 4. 饮食条件归一化

例如：

- “学校食堂”
- “外卖”
- “自己做饭”
- “自己下厨”
- “忌口”

归一后映射为：

- `食堂为主`
- `外卖为主`
- `自己做饭`
- `忌口`
- `无`

#### 5. 数值归一化

当前支持把带单位或范围的输入自动转成标准值，例如：

- `22岁` -> `22`
- `173cm` -> `173`
- `67kg` -> `67`
- `4-5` -> `5`
- `60-90` -> `90`
- `80%` -> `0.8`
- `80` -> `0.8`

#### 6. 主观反馈归一化

例如：

- “有点累” -> `4`
- “很累” -> `5`
- “还行” -> `基本达标`

这部分能力对规则路由至关重要，因为规则层提取出来的自然语言参数最终都需要落到标准字段值上。

### 3.4 已完成的计划生成逻辑

当前周训练计划生成会综合以下维度：

- 训练目标
- 训练经验
- 每周训练天数
- 单次训练时长
- 训练环境
- 薄弱部位
- 伤病限制

当前已经支持：

- 自动分配训练日与休息日
- 根据目标和经验决定训练 focus 序列
- 根据环境决定动作库
- 根据时长决定动作数量
- 根据目标决定组数与次数
- 区分训练日和休息日饮食提示
- 在备注中纳入伤病限制与薄弱部位补强

### 3.5 已完成的规则化调整建议

当前已经实现第一版规则建议引擎，支持以下触发逻辑：

- 连续两次高疲劳 -> 降量建议
- 出现明显酸痛 -> 动作替换或恢复建议
- 多次未完成计划或缺席 -> 简化训练建议
- 连续两次饮食未达标 -> 饮食替代建议
- 连续多天未训练 -> 低门槛重启建议
- 无明显风险信号 -> 维持当前计划建议

当前输出不是单一标签，而是组合型结果，可能同时包含：

- `deload`
- `exercise_swap`
- `simplify`
- `diet`
- `restart`
- `maintain`

### 3.6 已完成的 CLI 业务入口

当前系统已经具备中英双语 CLI 入口。

中文入口包括：

- `nanobot 健身 建档`
- `nanobot 健身 更新画像`
- `nanobot 健身 查看画像`
- `nanobot 健身 生成计划`
- `nanobot 健身 查看计划`
- `nanobot 健身 打卡`
- `nanobot 健身 查看打卡`
- `nanobot 健身 生成建议`
- `nanobot 健身 查看建议`

英文入口包括：

- `nanobot fitness profile-set`
- `nanobot fitness profile-update`
- `nanobot fitness profile-show`
- `nanobot fitness plan-generate`
- `nanobot fitness plan-show`
- `nanobot fitness feedback-add`
- `nanobot fitness feedback-show`
- `nanobot fitness adjustment-generate`
- `nanobot fitness adjustment-show`

### 3.7 已完成的规则路由版本

这是当前版本最关键的新进展。

当前已经实现了规则驱动的自然语言路由层，并且已经完成以下能力：

- 自然语言意图识别
- 自然语言参数抽取
- 缺参提示
- action 到 service 的映射执行
- 用户标识自动提取
- 最近活跃用户记忆
- `agent -m` 入口短路

#### 当前规则路由已支持的动作

当前已支持以下完整动作集：

- `save_profile`
- `update_profile`
- `show_profile`
- `generate_weekly_plan`
- `show_weekly_plan`
- `record_feedback`
- `show_feedback`
- `generate_adjustment`
- `show_adjustment`

这意味着规则路由层已经把健身业务主要闭环全部覆盖完整。

#### 当前已支持的自然语言入口

当前已支持两类自然语言入口：

##### 1. Fitness 专用路由入口

```powershell
nanobot fitness route "我叫sasa，我是男，23岁，176cm，70kg，目标是增肌，初级，每周4次，每次60分钟，在家训练，外卖为主"
```

##### 2. Agent 单消息入口

```powershell
nanobot agent -m "给我生成这周训练计划"
```

对于明显属于健身业务的输入，系统会优先走本地规则路由，而不是先走大模型。

#### 当前已支持的用户标识自动提取

系统当前已经支持从自然语言中自动提取用户标识，例如：

- “我叫 sasa”
- “我的名字是 sasa”
- “叫我 sasa”

这意味着用户不必再强依赖：

- `--user-id demo`

#### 当前已支持的最近活跃用户记忆

当前规则路由版本会把最近一次成功执行的健身用户记录在：

- `workspace/fitness/router_state.json`

后续当用户继续说：

- “给我看看我的画像”
- “给我生成这周训练计划”
- “看看最近的建议”

如果没有再次显式说出名字，系统会优先沿用最近一次的健身用户。

这使得当前交互已经具备初步多轮连续性，而不再是每句都必须重新声明用户。

### 3.8 已完成的数据持久化

当前继续采用 `SQLite` 作为持久化方案，数据库文件位置为：

- `workspace/fitness/fitness.db`

当前表包括：

- `user_profiles`
- `weekly_plans`
- `daily_feedback`
- `adjustment_suggestions`

当前版本还额外支持：

- profile id 列表查询

用于规则路由在没有明确 `user_id` 时做轻量兜底判断。

### 3.9 已完成的测试基础

当前和本模块直接相关的测试文件包括：

- `tests/fitness/test_service.py`
- `tests/cli/test_fitness_cli.py`

测试覆盖方向包括：

- 基础业务流程
- 规则路由端到端流程
- 缺参提示
- 用户标识自动提取
- 最近活跃用户记忆
- `agent -m` 健身短路

此外，还做了命令级 smoke test，已验证：

1. `agent -m` 建档
2. `agent -m` 查看画像
3. `agent -m` 生成计划
4. `agent -m` 查看计划

---

## 4. 我们目前使用了什么技术栈

### 4.1 语言与运行环境

当前主开发语言仍然是：

- `Python 3.11+`

原因包括：

- nanobot 本体就是 Python 项目
- CLI、规则路由、数据模型、持久化都能快速实现
- 与后续 LLM provider、Agent loop 天然兼容

### 4.2 当前主要技术栈

#### 1. `Typer`

用于：

- CLI 命令定义
- 参数解析
- `fitness route` 命令入口
- `agent -m` 命令入口

#### 2. `Pydantic v2`

用于：

- 数据模型定义
- 参数校验
- 输入归一化
- 结构化参数落库前的最终标准化

#### 3. `SQLite`

用于：

- 用户画像存储
- 周计划存储
- 打卡记录存储
- 调整建议存储

#### 4. `sqlite3`

当前持久化层仍采用 Python 标准库 `sqlite3`，没有引入 ORM。

这样做的原因是：

- 结构足够简单
- 依赖更轻
- 与 MVP 阶段规模匹配

#### 5. `nanobot` 基础设施

当前继续复用 nanobot 的：

- CLI 主命令系统
- 配置加载系统
- workspace 体系
- provider 体系
- agent loop
- session / tools / memory 体系

这让当前规则路由可以自然接入 `agent -m`，而不需要重做整个入口层。

---

## 5. 当前代码结构

当前相关核心代码位置包括：

- `nanobot/fitness/models.py`
- `nanobot/fitness/storage.py`
- `nanobot/fitness/service.py`
- `nanobot/fitness/router.py`
- `nanobot/fitness/__init__.py`
- `nanobot/cli/commands.py`
- `tests/fitness/test_service.py`
- `tests/cli/test_fitness_cli.py`

职责划分如下：

### 5.1 `models.py`

负责：

- 数据模型定义
- 字段类型约束
- 输入归一化

### 5.2 `storage.py`

负责：

- SQLite 表结构
- 画像 / 计划 / 打卡 / 建议的存取
- profile id 列表查询

### 5.3 `service.py`

负责：

- 业务编排
- 计划生成
- 打卡记录
- 建议生成
- 结果格式化

### 5.4 `router.py`

负责：

- 规则路由
- 意图识别
- 参数抽取
- 用户标识解析
- 最近活跃用户记忆
- 调用 service 层执行

### 5.5 `commands.py`

负责：

- `fitness route` 入口
- `agent -m` 健身优先短路
- 与原有 CLI / Agent 入口整合

---

## 6. 当前规则路由版本的详细实现方法

这一部分是当前版本的核心技术说明。

### 6.1 规则路由总体思路

当前规则路由遵循：

**自然语言输入 -> 规则识别 -> 提取结构化参数 -> 调用业务服务 -> 输出格式化结果**

它不是开放式自由生成，而是一套确定性业务路由机制。

### 6.2 意图识别方法

当前意图识别主要采用：

- 关键词匹配
- 场景短语匹配
- 规则优先级判断

例如：

- “建档 / 建个档 / 创建档案” -> `save_profile`
- “更新画像 / 修改档案” -> `update_profile`
- “查看画像 / 我的档案” -> `show_profile`
- “生成计划 / 这周怎么练” -> `generate_weekly_plan`
- “查看计划 / 看看计划” -> `show_weekly_plan`
- “打卡 / 我今天练了” -> `record_feedback`
- “查看打卡 / 打卡记录” -> `show_feedback`
- “给我建议 / 怎么调” -> `generate_adjustment`
- “查看建议 / 最近的建议” -> `show_adjustment`

### 6.3 参数提取方法

参数提取当前主要采用：

- 正则表达式
- 固定词表
- 已有归一化函数

#### 1. 用户画像参数提取

可提取：

- 性别
- 年龄
- 身高
- 体重
- 目标
- 训练经验
- 每周训练次数
- 单次训练时长
- 训练环境
- 饮食条件
- 薄弱部位
- 伤病限制
- 当前分化

#### 2. 计划参数提取

可提取：

- 指定日期
- “这周 / 本周 / 下周”这类周语义

#### 3. 打卡参数提取

可提取：

- 日期
- 是否训练
- 动作列表
- 完成度
- 疲劳程度
- 饮食达标情况
- 酸痛描述
- 额外备注

例如：

```text
我今天练了卧推和划船，完成度80%，有点累，饮食还行
```

会提取出：

- `trained_today = True`
- `completed_exercises = ["卧推", "划船"]`
- `completion_rate = 0.8`
- `fatigue_level = 4`
- `diet_adherence = 基本达标`

### 6.4 用户标识解析方法

当前用户标识解析优先级如下：

1. 如果显式传了 `--user-id`
2. 如果文本里出现“我叫 xxx / 我的名字是 xxx / 叫我 xxx”
3. 如果存在最近活跃用户，则优先复用它
4. 如果数据库里只有一个 profile，则自动使用该 profile
5. 最后回落到 `default`

这套逻辑保证了：

- 显式参数优先
- 自然表述优先级高
- 单用户场景使用顺滑
- 多轮连续使用体验更接近真实 Agent

### 6.5 最近活跃用户记忆方法

当前通过：

- `workspace/fitness/router_state.json`

保存：

- `last_user_id`

规则路由每次成功执行后，会自动更新这个文件。之后如果用户继续发健身相关请求而没有重新说出名字，系统会优先沿用最近一次的健身用户。

### 6.6 缺参提示方法

规则路由在关键参数不足时不会直接执行，而是返回：

- 已识别的意图
- 缺失字段列表

例如建档只提供“我是男，23岁”时，会提示还缺：

- 身高
- 体重
- 目标
- 训练经验
- 每周训练天数
- 单次训练时长
- 训练环境
- 饮食条件

### 6.7 action 到 service 的执行映射

规则命中后，统一调用 `FitnessService` 执行，不在路由层重复实现业务逻辑。

映射如下：

- `save_profile` -> `service.save_profile`
- `update_profile` -> `service.update_profile`
- `show_profile` -> `service.get_profile`
- `generate_weekly_plan` -> `service.generate_weekly_plan`
- `show_weekly_plan` -> `service.get_latest_plan`
- `record_feedback` -> `service.record_feedback`
- `show_feedback` -> `service.list_feedback`
- `generate_adjustment` -> `service.generate_adjustment`
- `show_adjustment` -> `service.get_latest_adjustment`

### 6.8 `fitness route` 入口实现方法

当前在 CLI 层新增了：

- `nanobot fitness route`
- `nanobot 健身 路由`

这个入口的职责是：

1. 接收自然语言
2. 构造规则路由器
3. 调用 `router.handle(...)`
4. 返回最终文本结果

### 6.9 `agent -m` 健身短路方法

当前在 `nanobot agent -m "..."` 的单消息入口前增加了一层健身优先短路逻辑。

流程如下：

1. 先判断输入是否属于健身规则路由范围
2. 如果命中，直接本地执行规则路由
3. 如果不命中，再继续走原有通用 Agent / LLM 流程

这个设计带来的直接好处是：

- 明显的健身场景不依赖模型
- 明显的健身场景不依赖 API key
- 本地响应更快
- 行为更稳定

---

## 7. 当前版本如何验证

### 7.1 测试文件

当前测试主要覆盖在：

- `tests/fitness/test_service.py`
- `tests/cli/test_fitness_cli.py`

当前已覆盖的重点包括：

- 基础业务链路
- 自然语言规则路由链路
- 缺参提示
- 用户标识提取
- 最近活跃用户记忆
- `agent -m` 健身短路

### 7.2 命令级 smoke test

当前已经验证以下真实交互链路可通：

1. `agent -m` 自然语言建档
2. `agent -m` 查看画像
3. `agent -m` 生成计划
4. `agent -m` 查看计划

因此，这一版不只是代码层可运行，也已经在真实命令入口上完成验证。

---

## 8. 当前规则路由版本的边界

虽然规则路由版已经完成，但它仍然是规则系统，不是最终智能路由系统。

当前边界包括：

- 对特别模糊的表达支持还有限
- 多意图混合输入处理仍然有限
- 复杂多轮追问还比较基础
- 没有 LLM 兜底
- 复杂自然语言解释还比较模板化

所以这一版可以定义为：

**规则路由完成版，但不是最终 LLM 路由终版。**

---

## 9. 下一步将会用什么技术栈

下一步进入 LLM 路由阶段后，整体技术栈仍然不会推翻当前实现，而是继续沿用：

- `Python 3.11+`
- `Typer`
- `Pydantic v2`
- `SQLite`
- `nanobot` Agent 基础设施
- `LiteLLM` provider 体系

新增的重点不在于换语言或换数据库，而在于引入：

- LLM 兜底意图识别
- LLM 辅助参数抽取
- LLM 结果润色
- 多轮补全追问

### 9.1 下一步总体原则

下一步仍然坚持：

- 规则优先
- LLM 兜底
- 所有参数继续过 Pydantic 校验
- 所有动作继续映射到现有 service 层

### 9.2 LLM 路由阶段主要职责

LLM 层未来主要负责：

- 处理更模糊、更自由的表达
- 在规则未命中时做意图分类
- 抽取更复杂的结构化参数
- 生成更自然的追问与解释

因此，未来会是：

**规则路由负责确定性，LLM 路由负责弹性理解。**

---

## 10. 一句话总结

当前我们基于 `nanobot` 已经把健身 Agent 从“CLI 基础版”推进到了“规则路由完成版”。

这一版不仅保留了画像、计划、打卡、建议这一整套完整业务能力，还新增了自然语言意图识别、自动参数提取、自动用户标识识别、最近活跃用户记忆，以及 `agent -m` 场景下的健身短路分流能力。

从工程角度看，这一版已经是一个可用、可演示、可继续演进到 LLM 路由阶段的规则驱动健身 Agent 原型。
