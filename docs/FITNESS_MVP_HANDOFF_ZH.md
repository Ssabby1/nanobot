# 健身 Agent MVP 当前状态交接文档

## 1. 项目当前定位

这是一个基于 `nanobot` 二次开发的健身训练与饮食协同 Agent MVP。

当前已经完成的是：

- 用户画像建档
- 用户画像局部更新
- 周训练计划生成
- 每日反馈记录
- 动态调整建议
- 中文/英文双语 CLI 命令
- 一部分自然语言输入归一化
- SQLite 持久化存储

当前还没有完成的是：

- 自然语言对话式 Agent 调度层
- Web 页面
- README 项目包装
- 更完善的自动化测试收尾

所以目前更准确的状态是：

**“业务内核已完成，CLI MVP 已可演示，尚未升级为完整自然语言 Agent 产品。”**

---

## 2. 当前已经实现的能力

### 2.1 用户画像

支持保存以下核心字段：

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

### 2.2 周训练计划生成

当前可根据画像生成一周计划，输出包含：

- 周几训练 / 周几休息
- 每天训练部位
- 动作列表
- 组数和次数
- 注意事项
- 训练日 / 休息日饮食提示

### 2.3 每日反馈记录

支持记录：

- 是否训练
- 完成动作
- 完成度
- 主观疲劳
- 酸痛说明
- 饮食达标情况
- 额外备注

### 2.4 动态调整建议

当前已实现规则：

- 连续两次高疲劳 -> 降量建议
- 出现明显酸痛 -> 动作替换或恢复建议
- 多次未完成计划 -> 简化训练建议
- 饮食连续未达标 -> 饮食替代建议
- 连续多天未训练 -> 低门槛重启建议

---

## 3. 当前命令入口

### 3.1 中文命令

- `nanobot 健身 建档`
- `nanobot 健身 更新画像`
- `nanobot 健身 查看画像`
- `nanobot 健身 生成计划`
- `nanobot 健身 查看计划`
- `nanobot 健身 打卡`
- `nanobot 健身 查看打卡`
- `nanobot 健身 生成建议`
- `nanobot 健身 查看建议`

### 3.2 英文命令

- `nanobot fitness profile-set`
- `nanobot fitness profile-update`
- `nanobot fitness profile-show`
- `nanobot fitness plan-generate`
- `nanobot fitness plan-show`
- `nanobot fitness feedback-add`
- `nanobot fitness feedback-show`
- `nanobot fitness adjustment-generate`
- `nanobot fitness adjustment-show`

---

## 4. 当前支持的输入归一化

已经支持一部分自然语言输入自动映射为系统标准值。

### 4.1 目标 `goal`

支持映射示例：

- `薄肌和减脂` -> `减脂保肌`
- `边减脂边增肌` -> `减脂保肌`
- `薄肌` -> `薄肌增肌`
- `新手` -> `新手入门`

### 4.2 经验 `experience_level`

支持映射示例：

- `系统健身三个月` -> `初级`
- `练了三个月` -> `初级`
- `零基础` -> `新手`
- `练了一年` -> `中级`

### 4.3 场地 `environment`

支持映射示例：

- `学校` -> `校园健身房`
- `学校健身房` -> `校园健身房`
- `在家` -> `家里`
- `寝室` -> `宿舍`

### 4.4 饮食条件 `diet_constraint`

当前标准值：

- `无`
- `食堂为主`
- `外卖为主`
- `自己做饭`
- `忌口`

支持映射示例：

- `学校食堂` -> `食堂为主`
- `外卖` -> `外卖为主`
- `家里吃饭` -> `自己做饭`
- `自己下厨` -> `自己做饭`

### 4.5 数值字段

支持示例：

- `22岁` -> `22`
- `173cm` -> `173`
- `67kg` -> `67`
- `4-5` -> `5`
- `60-90` -> `90`

当前规则：

- 数值范围默认取较大值

### 4.6 打卡字段

支持示例：

- `80%` -> `0.8`
- `80` -> `0.8`
- `有点累` -> `4`
- `很累` -> `5`
- `还行` -> `基本达标`

---

## 5. 主要代码位置

### 5.1 业务模块

- [nanobot/fitness/models.py](/D:/nanobot/nanobot/nanobot/fitness/models.py)
  - 数据模型
  - 输入归一化逻辑

- [nanobot/fitness/storage.py](/D:/nanobot/nanobot/nanobot/fitness/storage.py)
  - SQLite 存储层

- [nanobot/fitness/service.py](/D:/nanobot/nanobot/nanobot/fitness/service.py)
  - 建档
  - 更新画像
  - 生成计划
  - 记录反馈
  - 生成建议
  - 文本格式化输出

### 5.2 CLI 入口

- [nanobot/cli/commands.py](/D:/nanobot/nanobot/nanobot/cli/commands.py)
  - `fitness` / `健身` 命令注册
  - 中文/英文别名

### 5.3 文档

- [plan.md](/D:/nanobot/nanobot/plan.md)
- [docs/FITNESS_CLI_GUIDE_ZH.md](/D:/nanobot/nanobot/docs/FITNESS_CLI_GUIDE_ZH.md)
- [docs/FITNESS_NORMALIZATION_ZH.md](/D:/nanobot/nanobot/docs/FITNESS_NORMALIZATION_ZH.md)

### 5.4 测试

- [tests/fitness/test_service.py](/D:/nanobot/nanobot/tests/fitness/test_service.py)
- [tests/cli/test_fitness_cli.py](/D:/nanobot/nanobot/tests/cli/test_fitness_cli.py)

---

## 6. 如何快速验证当前版本

推荐先跑这条建档命令：

```powershell
nanobot 健身 建档 `
  --user-id sasa `
  --gender 男 `
  --age 22岁 `
  --height 173cm `
  --weight 67kg `
  --goal 薄肌和减脂 `
  --experience-level 系统健身三个月 `
  --training-days-per-week 4-5 `
  --session-duration 60-90 `
  --environment 学校 `
  --diet-constraint 学校食堂
```

然后查看画像：

```powershell
nanobot 健身 查看画像 --user-id sasa
```

然后生成计划：

```powershell
nanobot 健身 生成计划 --user-id sasa
```

然后打卡：

```powershell
nanobot 健身 打卡 `
  --user-id sasa `
  --date 2026-03-26 `
  --trained `
  --completed-exercises "卧推,划船" `
  --completion-rate 80% `
  --fatigue-level 有点累 `
  --diet-adherence 还行 `
  --soreness-notes "手腕有点不舒服"
```

然后生成建议：

```powershell
nanobot 健身 生成建议 --user-id sasa
```

更新画像可以这样做：

```powershell
nanobot 健身 更新画像 `
  --user-id sasa `
  --weight 64kg `
  --session-duration 60-75 `
  --goal 薄肌和增肌 `
  --environment 家里 `
  --diet-constraint 自己做饭
```

英文版局部更新：

```powershell
nanobot fitness profile-update `
  --user-id sasa `
  --training-days-per-week 4-5 `
  --injury-notes 右手轻微TFCC
```

---

## 7. 已知问题 / 当前限制

### 7.1 还不是自然语言 Agent

当前仍然需要显式命令入口，比如：

- `建档`
- `更新画像`
- `生成计划`
- `打卡`

也就是说，虽然底层业务能力已经具备，但还没有实现：

**“用户随便说一句自然语言，系统自动识别意图并调用对应业务函数。”**

这是当前最明显的“还不够 Agent”的地方。

### 7.2 CLI 成功提示部分仍为英文

例如：

- `Profile saved.`
- `Profile updated.`
- `Weekly plan generated.`

功能不受影响，但还没完全本地化。

### 7.3 自动化测试环境不干净

当前本地 `pytest` 在这个 Windows 环境中受到临时目录权限问题影响，手动验证是通的，但自动化测试输出不够干净。

### 7.4 仍有 `.tmp` 临时目录残留风险

由于本地环境权限问题，仓库里可能残留 `.tmp/` 测试目录，属于验证过程产生的噪音，不是业务代码的一部分。

---

## 8. 最建议下一个线程继续做的事情

优先级从高到低建议如下：

### 第一优先级：补自然语言调度层

目标：

- 用户直接输入自然语言
- 系统识别意图
- 自动调用现有业务函数

建议先做规则版，不调用 API：

- “我想建档……” -> `save_profile`
- “帮我生成这周计划” -> `generate_weekly_plan`
- “我今天练了……” -> `record_feedback`
- “给我一点调整建议” -> `generate_adjustment`

这是把项目从“命令行业务工具”升级为“更像 Agent”的关键一步。

### 第二优先级：补 README

目标：

- 把这个项目包装成可放 GitHub、可写简历的二开项目

### 第三优先级：补最小 Web Demo

目标：

- 把 CLI MVP 提升为可截图、可录屏展示的 Web MVP

---

## 9. 一句话交接结论

当前这个项目已经是：

**一个可以写进简历的、基于 nanobot 的健身 Agent 二次开发 CLI MVP。**

下一步最值得做的是：

**补自然语言意图识别与自动路由，让它从“命令式工具”升级为“更像真正 Agent 的交互系统”。**
