# 健身 Agent 输入归一化补充说明

## 饮食条件新增项

当前 `diet-constraint` / `饮食条件` 支持以下标准值：

- `无`
- `食堂为主`
- `外卖为主`
- `自己做饭`
- `忌口`

## 与“自己做饭”相关的自然语言映射

以下输入会自动归一化为 `自己做饭`：

- `自己做饭`
- `自己做`
- `家里吃饭`
- `在家吃饭`
- `家里做饭`
- `自己下厨`

## 示例

下面这些写法现在都可以正常建档：

```powershell
nanobot 健身 建档 --diet-constraint 自己做饭
```

```powershell
nanobot 健身 建档 --diet-constraint 家里吃饭
```

```powershell
nanobot 健身 建档 --diet-constraint 自己下厨
```

系统内部会统一保存为：

```text
自己做饭
```
