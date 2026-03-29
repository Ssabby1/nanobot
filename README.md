# Fitness Agent on nanobot

<div align="center">
  <img src="nanobot_logo.png" alt="nanobot" width="220">
  <h1>基于 nanobot 二次开发的 Fitness Agent</h1>
  <p>一个面向训练与饮食场景的垂直智能体原型，支持规则优先、LLM 兜底、多轮补全与可回归评测。</p>
</div>

## 项目定位

这个仓库原本是开源轻量级 Agent 框架 `nanobot`。我在此基础上做了一个面向健身场景的垂直 Agent 子项目，把通用聊天能力收敛成一条更适合真实任务演示的闭环：

1. 理解用户意图
2. 路由到具体 fitness action
3. 在信息不足时做多轮追问补全
4. 调用确定性的业务服务执行
5. 将用户画像、计划、反馈、建议持久化，供后续轮次复用

它不是一个“自由聊天”的健身机器人，而是一个更强调结构化理解、稳定执行和可验证输出的 Agent 工程原型。

## 我做了什么

围绕 Fitness 场景补齐了一条完整业务链路：

- 用户画像创建与更新
- 周训练计划生成与查看
- 日常训练打卡与历史查看
- 基于反馈的调整建议生成
- `nanobot agent -m "..."` 单消息入口接入
- `nanobot fitness route "..."` 垂直路由入口接入
- 规则路由 + LLM 结构化兜底
- 多轮补全、最近用户复用、pending state 续填
- 内置 deterministic eval 与 JSON 报告输出

## 核心亮点

### 1. 规则优先，LLM 只做结构化理解

项目不是把自然语言直接交给模型自由发挥，而是分成两层：

- 规则路由优先命中明显意图，保证低成本和高确定性
- LLM 路由只在规则未命中或表达更模糊时介入
- LLM 输出仍然是结构化字段，如 `action`、`arguments`、`missing_fields`
- 最终执行统一落到 `FitnessService`，避免把业务逻辑散落在 prompt 里

这个设计把“理解”和“执行”解耦，比较适合在面试里展示工程化思路。

### 2. 多轮补全不是报错，而是连续对话

如果用户第一次没有把信息说完整，系统不会直接失败，而是：

- 记录未完成动作到 `workspace/fitness/router_state.json`
- 优先追问最关键的 1 到 2 个字段
- 下一轮只需要补充缺失信息，不用整段重说
- 根据轮次和场景切换追问话术，让第二轮、第三轮更像自然延续

这部分解决的是 Agent 在真实使用里最常见的“信息不完整”问题。

### 3. 不是只会聊天，而是有业务闭环

Fitness 模块不是一个 demo prompt，而是有完整的数据模型和服务层：

- `UserProfile`
- `WeeklyPlan`
- `DailyFeedback`
- `AdjustmentSuggestion`

数据持久化使用 `SQLite`，便于本地演示和回归验证。

### 4. 有内置评测，不靠手点验证

仓库里增加了 fitness 场景的 deterministic eval：

```bash
nanobot fitness eval
```

会自动覆盖典型链路，例如：

- 一次性自然语言建档
- 多轮补全建档
- 最近活跃用户复用
- 建档后生成周计划
- 休息日打卡补全
- 打卡后生成调整建议

并输出 JSON 报告，方便回归检查。

## 架构思路

<p align="center">
  <img src="nanobot_arch.png" alt="nanobot architecture" width="760">
</p>

Fitness 子模块在整体框架中的核心链路可以概括为：

```text
User Message
  -> Rule Router
  -> LLM Router (fallback)
  -> FitnessService
  -> SQLite / Workspace State
  -> Formatted Response
```

对应代码位置：

- `nanobot/fitness/router.py`
- `nanobot/fitness/llm_router.py`
- `nanobot/fitness/service.py`
- `nanobot/fitness/storage.py`
- `nanobot/fitness/eval.py`
- `nanobot/cli/commands.py`

## 技术栈

- Python 3.11
- Typer
- Pydantic v2
- SQLite
- LiteLLM / provider abstraction
- pytest

## 演示方式

### 1. 一句话自然语言建档

```bash
nanobot agent -m "我叫sasa，男，23岁，176cm，140斤，目标减脂，练了五年，每周练4次，每次60分钟，健身房训练，自己做饭"
```

### 2. 多轮补全

```bash
nanobot agent -m "我叫sasa，男，23岁，176cm"
nanobot agent -m "体重140斤"
nanobot agent -m "目标减脂，练了五年，每周练4次，每次60分钟，健身房训练，自己做饭"
```

### 3. 打卡与建议闭环

```bash
nanobot agent -m "我今天练了卧推和深蹲，完成度80%，有点累，饮食还行"
nanobot agent -m "给我生成调整建议"
```

### 4. 垂直路由入口

```bash
nanobot fitness route "给我生成这周训练计划"
```

### 5. 评测

```bash
nanobot fitness eval
```

## 仓库结构

```text
nanobot/
  fitness/
    models.py
    storage.py
    service.py
    router.py
    llm_router.py
    eval.py
  cli/
    commands.py
tests/
  fitness/
  cli/test_fitness_cli.py
docs/
  FITNESS_AGENT_OVERVIEW.md
  FITNESS_PROJECT_SHOWCASE_ZH.md
  FITNESS_TECH_STATUS_AND_ROADMAP_ZH.md
```

## 本地运行

```bash
pip install -e .[dev]
nanobot onboard
nanobot fitness eval
```

如果需要体验 LLM 兜底路由，再按 `nanobot` 原有方式配置 provider 和模型即可。

## 文档补充

- `docs/FITNESS_AGENT_OVERVIEW.md`：英文概览，适合快速说明项目
- `docs/FITNESS_PROJECT_SHOWCASE_ZH.md`：中文展示版材料
- `docs/FITNESS_TECH_STATUS_AND_ROADMAP_ZH.md`：技术现状与演进路线
- `docs/FITNESS_NEXT_THREAD_HANDOFF_ZH.md`：后续整理建议与交接说明

## 声明

这个仓库基于开源项目 `nanobot` 继续开发。README 中重点展示的是我补充实现的 Fitness Agent 子模块及其工程化改造，而不是声称整个基础框架均为我从零搭建。
