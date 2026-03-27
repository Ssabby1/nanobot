# 健身 Agent CLI 使用说明

本文档说明当前健身训练与饮食协同 Agent MVP 的命令行用法，包括：

- 每个指令的作用
- 输入格式
- 必填项和可选项
- 输出内容是什么
- 一套推荐测试流程

当前命令支持双语：

- 英文入口：`nanobot fitness ...`
- 中文入口：`nanobot 健身 ...`

建议你平时演示时优先用中文入口，开发和排查问题时保留英文入口也会更稳。

---

## 一、整体流程

完整 MVP 的测试顺序如下：

1. 建档
2. 查看画像
3. 生成计划
4. 查看计划
5. 打卡
6. 查看打卡
7. 生成建议
8. 查看建议

推荐按这个顺序跑，不容易报“缺少前置数据”的错误。

---

## 二、命令总览

### 中文命令

- `nanobot 健身 建档`
- `nanobot 健身 查看画像`
- `nanobot 健身 生成计划`
- `nanobot 健身 查看计划`
- `nanobot 健身 打卡`
- `nanobot 健身 查看打卡`
- `nanobot 健身 生成建议`
- `nanobot 健身 查看建议`

### 对应英文命令

- `nanobot fitness profile-set`
- `nanobot fitness profile-show`
- `nanobot fitness plan-generate`
- `nanobot fitness plan-show`
- `nanobot fitness feedback-add`
- `nanobot fitness feedback-show`
- `nanobot fitness adjustment-generate`
- `nanobot fitness adjustment-show`

---

## 三、详细输入格式

## 1. 建档

命令：

```powershell
nanobot 健身 建档 `
  --user-id demo `
  --gender 男 `
  --age 23 `
  --height 176 `
  --weight 70 `
  --goal 薄肌增肌 `
  --experience-level 初级 `
  --training-days-per-week 4 `
  --session-duration 60 `
  --environment 家里 `
  --diet-constraint 外卖为主 `
  --current-split "上/下肢" `
  --weak-points 肩部 `
  --injury-notes 无
```

作用：

- 创建一个新用户画像
- 如果 `user-id` 已存在，则更新该用户画像

必填参数：

- `--user-id`
  - 用户标识
  - 示例：`demo`
- `--gender`
  - 性别
  - 示例：`男`、`女`
- `--age`
  - 年龄
  - 示例：`23`
- `--height`
  - 身高，单位 cm
  - 示例：`176`
- `--weight`
  - 体重，单位 kg
  - 示例：`70`
- `--goal`
  - 训练目标
  - 推荐使用：`薄肌增肌`、`减脂保肌`、`新手入门`
- `--experience-level`
  - 训练经验
  - 可用值：`新手`、`初级`、`中级`
- `--training-days-per-week`
  - 每周训练天数
  - 示例：`3`、`4`、`5`
- `--session-duration`
  - 单次训练时长，单位分钟
  - 示例：`45`、`60`
- `--environment`
  - 训练场地
  - 可用值：`商业健身房`、`校园健身房`、`宿舍`、`家里`
- `--diet-constraint`
  - 饮食约束
  - 可用值：`无`、`食堂为主`、`外卖为主`、`忌口`

可选参数：

- `--current-split`
  - 当前训练分化
  - 示例：`推拉腿`
- `--weak-points`
  - 薄弱部位
  - 示例：`肩部`、`背部`
- `--injury-notes`
  - 伤病限制
  - 示例：`膝盖不适`

输出内容：

- 显示“建档成功”
- 打印当前用户画像摘要，包括基础信息、训练目标、训练安排、场地饮食、薄弱部位和伤病限制

---

## 2. 查看画像

命令：

```powershell
nanobot 健身 查看画像 --user-id demo
```

作用：

- 查看某个用户当前保存的画像

必填参数：

- `--user-id`

输出内容：

- 用户基础信息
- 目标与经验
- 每周训练安排
- 场地与饮食约束
- 当前分化、薄弱部位、伤病限制

如果没有这个用户：

- 会提示未找到画像

---

## 3. 生成计划

命令：

```powershell
nanobot 健身 生成计划 --user-id demo --week-start 2026-03-25
```

作用：

- 根据用户画像生成一周训练计划

必填参数：

- `--user-id`

可选参数：

- `--week-start`
  - 任意位于目标周内的日期
  - 格式必须是 `YYYY-MM-DD`
  - 示例：`2026-03-25`

说明：

- 系统会自动换算到该周的周一作为计划起始日期

输出内容：

- 用户 ID
- 周起始日期
- 目标类型
- 生成依据
- 每天的安排

每一天会包含：

- 周几
- 训练或休息
- 训练部位
- 动作列表
- 组数和次数
- 注意事项
- 饮食提示

---

## 4. 查看计划

命令：

```powershell
nanobot 健身 查看计划 --user-id demo
```

作用：

- 查看该用户最近一次生成的周计划

必填参数：

- `--user-id`

输出内容：

- 最近一次保存的完整周计划

如果还没生成过计划：

- 会提示未找到计划

---

## 5. 打卡

命令：

```powershell
nanobot 健身 打卡 `
  --user-id demo `
  --date 2026-03-25 `
  --trained `
  --completed-exercises "俯卧撑,单臂哑铃划船" `
  --completion-rate 0.8 `
  --fatigue-level 4 `
  --soreness-notes "腿部酸痛" `
  --diet-adherence 基本达标 `
  --extra-notes "今天睡眠一般"
```

作用：

- 记录当天训练反馈

必填参数：

- `--user-id`
- `--date`
  - 日期格式：`YYYY-MM-DD`
- `--completion-rate`
  - 完成度
  - 取值范围：`0` 到 `1`
  - 示例：`0.8` 表示 80%
- `--fatigue-level`
  - 主观疲劳等级
  - 取值范围：`1` 到 `5`
- `--diet-adherence`
  - 饮食达标情况
  - 可用值：`达标`、`基本达标`、`未达标`

训练状态参数：

- `--trained`
  - 表示今天有训练
- `--not-trained`
  - 表示今天没训练

二选一，默认是 `--trained`

可选参数：

- `--completed-exercises`
  - 完成的动作，用英文逗号分隔
  - 示例：`"深蹲,卧推,划船"`
- `--soreness-notes`
  - 酸痛情况
- `--extra-notes`
  - 补充说明

输出内容：

- 显示反馈记录已保存
- 显示记录日期和疲劳等级

---

## 6. 查看打卡

命令：

```powershell
nanobot 健身 查看打卡 --user-id demo --limit 7
```

作用：

- 查看最近几条反馈记录

参数：

- `--user-id`
- `--limit`
  - 查看最近多少条
  - 默认值：`7`

输出内容：

- 每条反馈的日期
- 是否训练
- 完成度
- 疲劳等级
- 饮食达标情况
- 完成动作
- 酸痛说明
- 额外备注

---

## 7. 生成建议

命令：

```powershell
nanobot 健身 生成建议 --user-id demo --lookback-days 7
```

作用：

- 根据最近反馈记录生成动态调整建议

参数：

- `--user-id`
- `--lookback-days`
  - 实际上表示“最多读取最近多少条反馈”
  - 默认值：`7`

输出内容：

- 用户 ID
- 反馈区间
- 调整类型
- 触发原因
- 调整建议正文

当前规则包括：

- 连续两次疲劳高，建议降量
- 出现明显酸痛，建议替换动作或恢复
- 多次未完成计划，建议简化训练
- 饮食连续不达标，给出现实饮食替代
- 连续多天未训练，建议低门槛重启

如果还没有任何反馈记录：

- 会提示至少需要一条反馈记录

---

## 8. 查看建议

命令：

```powershell
nanobot 健身 查看建议 --user-id demo
```

作用：

- 查看最近一次生成的调整建议

参数：

- `--user-id`

输出内容：

- 最近一次建议的完整内容

如果还没有生成过建议：

- 会提示未找到建议

---

## 四、推荐测试样例

你可以直接复制这一组命令，从头跑完整闭环。

### 第 1 步：建档

```powershell
nanobot 健身 建档 `
  --user-id demo `
  --gender 男 `
  --age 23 `
  --height 176 `
  --weight 70 `
  --goal 薄肌增肌 `
  --experience-level 初级 `
  --training-days-per-week 4 `
  --session-duration 60 `
  --environment 家里 `
  --diet-constraint 外卖为主
```

### 第 2 步：生成计划

```powershell
nanobot 健身 生成计划 --user-id demo --week-start 2026-03-25
```

### 第 3 步：打卡两次

```powershell
nanobot 健身 打卡 `
  --user-id demo `
  --date 2026-03-24 `
  --trained `
  --completed-exercises "俯卧撑,划船" `
  --completion-rate 0.5 `
  --fatigue-level 4 `
  --soreness-notes "下肢酸痛明显" `
  --diet-adherence 未达标
```

```powershell
nanobot 健身 打卡 `
  --user-id demo `
  --date 2026-03-25 `
  --not-trained `
  --completed-exercises "" `
  --completion-rate 0 `
  --fatigue-level 5 `
  --diet-adherence 未达标 `
  --extra-notes "今天太忙没练"
```

### 第 4 步：生成建议

```powershell
nanobot 健身 生成建议 --user-id demo
```

预期结果：

- 会触发高疲劳建议
- 会触发酸痛建议
- 会触发训练简化建议
- 会触发饮食替代建议

---

## 五、数据保存位置

当前 MVP 使用 SQLite 保存数据。

数据文件位置：

- `当前 workspace/fitness/fitness.db`

如果你想先确认 workspace 路径，可以执行：

```powershell
nanobot status
```

---

## 六、当前版本说明

这版已经完成的是：

- 用户画像建档
- 周训练计划生成
- 每日反馈记录
- 动态调整建议
- 中文输出
- 中文命令别名

这版还没有做的是：

- Web 页面
- LLM 润色计划文本
- 多用户权限体系
- 更细的训练数据库
- 复杂饮食分析

当前更适合用作：

- 本地演示
- 课程项目 MVP
- 简历项目雏形
- 后续继续做 Web 前端的后端基础
