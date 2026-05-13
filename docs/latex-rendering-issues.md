# LaTeX 公式渲染问题分析

> 生成日期：2026-05-12 | 分析样本：ROBOT 课件 5 章笔记 | 最后更新：2026-05-13（KaTeX internal 错误修复 + 防御层补全）

## 问题总览

| 类别 | 严重度 | 影响范围 | 检测状态 |
|------|--------|---------|---------|
| `$$` 后空行 | CRITICAL | Ch2-5，54/58 个公式块 (93%) | ✅ 已修复 (Fix 1b) |
| 代码块包裹 | HIGH | Ch2 | ✅ 已修复 (无闭合标签处理) |
| `$$` 前空格 | MEDIUM | Ch2-4，散在 | ✅ 已修复 (Fix 1c) |
| `\begin{...}^T` / `\\^T` / `\;^T` | HIGH | Ch4 (3处) | ✅ 已修复 (Fix 4/5/6) |
| inline `$$...\begin{...}...$$` | HIGH | Ch4 矩阵公式 | ✅ 已修复 (Fix 4) |

## 逐项分析

### 1. `$$` 后空行 — 公式不渲染

**模式**：
```
$$
                    ← 空行（问题所在）
\boldsymbol{T} = \begin{bmatrix}...
```
正确格式：
```
$$
\boldsymbol{T} = \begin{bmatrix}...
```

**根因**：AI 模型在输出 `$$` 后习惯性插入空行再写公式内容。多数 Markdown LaTeX 渲染器（MathJax、KaTeX）将 `$$` 后紧跟空行解释为"空公式块"，其后内容按普通文本处理，矩阵、分数等全部失效。

**统计**：

| 章节 | $$ 总数 | 空行问题 | 比例 |
|------|---------|---------|------|
| Ch1 绪论 | 0 | 0 | — |
| Ch2 数学基础 | 26 | 22 | 85% |
| Ch3 运动学 | 8 | 8 | 100% |
| Ch4 速度静力学 | 16 | 16 | 100% |
| Ch5 动力学 | 8 | 8 | 100% |

**现有修复为何失效 — Fix 4 是罪魁祸首**：

`post_processor.py:fix_latex_format` 按以下顺序处理：

1. **Fix 1**（line 299）：`re.sub(r'\$\$\s+\n', '$$\n', content)` — 通过正则回溯机制**确实能命中** `$$\n\n`，正确移除空行，产生 `$$\n`。
2. **Fix 4**（line 316-320）：`re.sub(r'\$\$\n([^\n$])', r'$$\n\n\1', content)` — 在 Fix 1 之后运行，**将 Fix 1 刚移除的空行重新加回去**。

处理链为：`$$\n\n\boldsymbol{T}` → (Fix 1) → `$$\n\boldsymbol{T}` → (Fix 4) → `$$\n\n\boldsymbol{T}`。Fix 4 是真正的问题所在。

**Fix 4 还会主动破坏正确格式**（Python 验证通过）：即使 AI 生成了正确格式 `$$\n\begin{bmatrix}`（无空行），Fix 4 也会将其破坏为 `$$\n\n\begin{bmatrix}`。即 Fix 4 不仅撤销 Fix 1 的修复，还**破坏所有原本正确的公式块**。

**Fix 4 的根本设计缺陷**：正则 `\$\$\n([^\n$])` 无法区分开闭 `$$`。注释说「公式块后跟普通文字时有空行」，但实际匹配所有 `$$\n` 后紧跟非空内容的行——包括开标签后的 LaTeX 命令。没有合理场景需要在 `$$` 后插入空行（Markdown 段落间距由前文规则处理，不应在公式块内部制造空行）。

**修复方案**：
- Fix 1 保持不变（验证有效）。
- **删除 Fix 4**（无合理用例，且会主动破坏正确格式）。
- 新增 `$$` 后空行移除作为防御层：`re.sub(r'\$\$\n\n+', '$$\n', content)`，在 Fix 1 之后运行。

---

### 2. 代码块包裹 — 整文件不可渲染

**模式**：
```markdown
---
```markdown

## 第2章 ...
...全部内容...
```

**根因**：AI 模型将整个笔记输出包裹在 ````markdown` 代码块中。**直接根因在 prompt**：`config/prompts.py` 中 `user_prompt`（line 81-135）给出的「内容组织模板」整体用 ````markdown` 包裹，模型据此将实际输出也放入代码块。

`post_processor.py:remove_code_block_wrapper` 通过匹配开闭标签来移除，但 Ch2 的 AI 输出在末尾被截断（内容不完整），缺少闭合 ` ``` `，导致修复逻辑跳过。

**为何只影响 Ch2**：该章内容最长（386行 AI 输出），触发 `max_tokens` 截断，末尾 ` ``` ` 未生成。第 2 次运行时 skip_existing 跳过了此文件，修复后的版本未写回。

**现状**：检测规则 `quality_check:182` 可识别此问题（标记为 error），但修复逻辑要求成对的开闭标签。

**修复方向**：
- **优先**：修改 `user_prompt` 中的模板，不要用 ````markdown` 代码块包裹示例，改为直接 Markdown 结构展示。
- **防御**：`remove_code_block_wrapper` 在无闭合标签时也应移除开标签（行内 ````markdown` 删除 + 末尾孤立的 ` ``` ` 删除）。

---

### 3. `$$` 前空格 — 公式分隔符识别失败

**模式**：` $$\n`（行末空格 + `$$`）

**根因**：AI 模型在段落末尾添加空格后接 `$$`。部分渲染器要求 `$$` 出现在行首或紧跟非空白字符，前置空格可能导致 `$$` 被当作普通文本。

**统计**：Ch2 出现 6 处，Ch3 出现 2 处，Ch4 出现 3 处。

---

### 4. Prompt 层面根因

经深入分析，**prompt 是两大 CRITICAL 问题的根源**：

| 问题 | Prompt 根因 | 位置 |
|------|------------|------|
| 代码块包裹 | `user_prompt` 模板用 ````markdown` 包裹示例结构，模型模仿该行为 | `config/prompts.py:81-135` |
| `$$` 后空行 | system prompt（line 50）仅写 `公式使用 LaTeX 格式（$$公式$$）`，未约束 `$$` 后不得有空行 | `config/prompts.py:50` |
| `$$` 前空格 | 同上，未约束 `$$` 前不得有空格 | `config/prompts.py:50` |

**修复方向**：在 system prompt 中添加明确的 LaTeX 格式约束：

> `$$` 必须紧跟公式内容，不得有空行；`$$` 前后不得有多余空格；不要将输出包裹在 ````markdown` 代码块中。

Prompt 修复是**根本解决方案**，post_processor 修复是**防御层**。二者结合才能覆盖首次生成 + 断点续传场景。

---

### 4. `\begin{...}^T` / `\\^T` / `\;^T` — KaTeX "Got group of unknown type: 'internal'"

**模式**：
```latex
\begin{bmatrix}^Td_x\\^Td_y...    % ^T 紧贴 \begin
T\;^T\Delta                        % ^T 紧贴 \;
```

**根因**：KaTeX 将 `^T` 解释为上标，试图分别附着到 `\begin` 命令、`\\` 换行命令或 `\;` 间距 primitive。这些命令在内部产生非标准 group 类型，KaTeX 无法解析，抛出 `ParseError: KaTeX parse error: Got group of unknown type: 'internal'`。

**受影响范围**：Ch4 笔记第 43 行（`\begin{bmatrix}^T` + `\\^T`）、第 20/116 行（`\;^T`）。

**修复方案**：在命令与 `^`/`_` 之间插入空组 `{}`，让上标/下标附着到 `{}` 而非命令：
```latex
\begin{bmatrix}{}^{T}d_x\\{}^{T}d_y...   % OK
T\;{}^{T}\Delta                           % OK
```

**post_processor 防御层**：
- Fix 4（`_expand_to_display`）：inline `$$...$$` 含 `\begin{...}` 展开为 display math
- Fix 5（`_fix_katex_script_attachment`）：display math 块内修复 `\begin{...}^`、`\\^`、`\;^` 等
- Fix 6：inline `$...$` 中修复 `\;^`、`\,^`、`\:^`、`\!^`（全局替换）

### 5. `$$` 前空格 — 公式分隔符识别失败（已在原 #4 分析）

> 合并入 Fix 1c：`re.sub(r'[ \t]+\$\$', '$$', content)`

---

## 修复路线

### 已完成

| # | 修复项 | 位置 | 状态 |
|---|--------|------|------|
| 1 | Fix 1b: `$$` 后空行移除 `r'^\$\$\n\n+' → '$$\n'` | `post_processor.py:308` | ✅ 已实施 |
| 2 | Fix 1c: `$$` 前空格移除 `r'[ \t]+\$\$' → '$$'` | `post_processor.py:311` | ✅ 已实施 |
| 3 | Fix 4: inline `$$...$$` 含 `\begin{...}` 展开为 display math | `post_processor.py:329` | ✅ 已实施 |
| 4 | Fix 5: display math 中 `\begin{...}^` / `\\^` / `\;^` 插入 `{}` | `post_processor.py:343` | ✅ 已实施 |
| 5 | Fix 6: inline math 中 `\;^` / `\,^` / `\:^` / `\!^` 插入 `{}` | `post_processor.py:358` | ✅ 已实施 |
| 6 | `remove_code_block_wrapper`：无闭合标签时仍移除开标签 | `post_processor.py:121` | ✅ 已实施 |
| 7 | `check_latex_format`：新增 `$$` 后空行检测 + `$$` 前空格检测 + emoji 紧贴检测 | `post_processor.py:360` | ✅ 已实施 |
| 8 | `note_generator`：修复 `system_prompt` 重复参数 bug | `note_generator.py:127` | ✅ 已实施 |

### 短期（prompt 修复）

| # | 修复项 | 位置 | 难度 | 优先级 |
|---|--------|------|------|--------|
| P1 | prompt: 添加 LaTeX 格式约束 + 移除 ````markdown` 模板包裹 | `config/prompts.py:50, 81` | 低 | **最高** |

### 中期（prompt 层面）

| # | 方案 | 说明 |
|---|------|------|
| 9 | few-shot 示例 | 提供正确/错误 LaTeX 格式对比示例 |

### 长期（结构化输出）

| # | 方案 | 说明 |
|---|------|------|
| 10 | 结构化章节输出 | 将公式内容与文本内容分离，模板化渲染 |
| 11 | 引入 LaTeX 校验器 | 生成后自动编译验证公式语法

---

## 现有测试缺口

`tests/test_post_processor.py:56-59` 的 `test_fix_latex_trailing_spaces` 测试：

```python
def test_fix_latex_trailing_spaces(self):
    content = "$$\n\nMiddle content\n$$\n\nNext line\n" + "x" * 600
    fixed = self.pp.fix_latex_format(content)
    assert "$$ \n" not in fixed
```

- 该测试输入不包含实际的 Bug 模式。断言 `"$$ \n" not in fixed` 检查的是 `$$` 后跟空格，但实际 Bug 是 `$$` 后跟**空行**（`\n\n`）。
- **该测试是 no-op**：不验证核心 Bug 是否被修复，也不验证 Fix 4 是否会重新引入问题。
- 需要新增：
  - `test_fix_latex_empty_line_after_opening`：验证 `$$\n\n` 被正确移除
  - `test_fix_latex_no_regression_on_correct`：验证 `$$\n\begin{bmatrix}` 不被 Fix 4 破坏
  - `test_fix_latex_spaces_before_opening`：验证 `$$` 前空格被清理
  - `test_fix_latex_empty_line_detection`：验证检测规则能识别 `$$\n\n` 模式

---

## 影响评估

当前 5 章笔记中，4 章存在公式渲染问题（Ch2-5），涉及 54 个公式块无法正常显示。对于数学密集型课程（机器人学、力学等），这导致核心公式不可读，笔记价值大幅降低。Ch2 的代码块包裹更使整章内容无法渲染。

**推荐执行顺序**：
1. **P1**：修改 prompt（根因修复，防止新生成内容重现问题）
2. **#1-#3**：修复 post_processor（防御层：移除空行 + 删除 Fix 4 + 代码块修复）
3. **#5-#7**：补齐检测规则和测试（防止回归）
