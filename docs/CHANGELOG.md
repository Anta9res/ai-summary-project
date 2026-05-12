# Changelog

## v1.3.0 — 默认模型切换 + LaTeX 渲染修复 (2026-05-13)

### 默认模型 — kimi-k2.6

- 默认模型从 `qwen-long` (DashScope) 切换为 `kimi-k2.6` (opencode.ai)
- 密钥优先级调整：`OPENCODE_API_KEY` 优先于 `DASHSCOPE_API_KEY`
- 智能回退：未检测到 `OPENCODE_API_KEY` 时自动回退 DashScope (qwen-long)
- 默认 `max_tokens` 提升至 8192（推理模型）

### Bug 修复 — LaTeX 公式渲染

- prompt 添加 LaTeX 格式约束（`$$` 后不空行、不包裹代码块），移除 ````markdown` 模板包裹
- post_processor 删除 Fix 4（破坏正确 LaTeX 格式），新增 `$$` 后空行移除/前空格清理
- 新增 `check_latex_format` 检测规则（`$$` 后空行 error、前空格 warning）
- `remove_code_block_wrapper` 支持无闭合标签场景（max_tokens 截断兜底）
- 新增 9 个测试用例（共 22 个）

## v1.2.0 — 分批合并修复与自动分流 (2026-05-12)

### Bug 修复 — PaddleOCR 分批合并路径错误

- `_merge_batch_results` 读写 `layoutParsingResults` 时 JSON 路径错误：写入 `result.layoutParsingResults` 但读取走 `result.result.layoutParsingResults`（两层嵌套）
- 导致 >100 页 PDF 的分批处理结果中，第 2、3 批（页 101+）的 layout 数据全部丢失
- 修复：改用 `_get_layouts()` 统一读写，写入正确嵌套路径 `result.result.layoutParsingResults`

### 功能 — 单文件自动分流

- 输入目录仅含 1 个 PDF 且 > 5MB 时，自动启用 `--single-file` 模式（无需手动传参）
- 阈值从 10MB 降至 5MB

### Bug 修复 — fileid:// 协议兼容 (2026-05-12)

- `chat_with_file` 中 system_prompt 不再与 `fileid://` 拼接
- system message 仅含 `fileid://`，system_prompt 移入 user message
- 修复 DashScope 因 fileid:// 与 system_prompt 拼接导致无法解析文件的错误

## v1.1.0 — 项目重构与多端点支持 (2026-05-12)

### 阶段一：文件清理与目录重组

- 新建 `scripts/` 目录，迁入 `ppt2pdf.py`、`deploy_production.py`
- `KNOWLEDGE_GRAPH.md` 移至 `docs/knowledge-graph.md`
- 删除 `QUICKSTART.md`（独有内容已合并到 README.md）
- 删除 `PROJECT_STRUCTURE.md`（严重过时，引用不存在的文件）
- 删除 `.cursor/`（IDE 临时文件，已在 .gitignore）
- README.md 更新目录结构、移除 v2.0 引用
- CLAUDE.md 移除 `scripts_backup/` 僵尸引用

### 阶段二：AI 提示词优化

- 移除 v2.0 提示词，仅保留 v3.0
- v3.0 拆分为 system prompt（角色定义）+ user prompt（内容任务）
- 新增 `temperature`、`max_tokens`、`top_p` 可配置参数
- API 密钥环境变量扩展：`DASHSCOPE_API_KEY` / `OPENCODE_API_KEY` / `API_KEY`
- 未知提示词版本回退到 v3.0 并输出警告日志
- 遗留：`use_custom` 自定义提示路径未实现

### 阶段三：多端点/多模型支持

- 新增 `chat_direct` / `process_text_direct`（直接文本注入，用于非 DashScope 端点）
- 自动路由：DashScope → file upload；OpenAI 兼容端点 → direct text
- 推理模型自动 `max_tokens=8192`（kimi-k2.6 等需要更多 token 空间）
- CLI 新增 `--model` / `--endpoint` 参数
- `HTTPS_PROXY` 环境变量代理支持
- 验证 opencode.ai + kimi-k2.6 笔记生成成功

### 使用方式

```bash
# DashScope (qwen-long, 默认)
PYTHONIOENCODING=utf-8 python cli.py --input 课件/ --output output/

# opencode.ai (kimi-k2.6)
PYTHONIOENCODING=utf-8 python cli.py --input 课件/ --output output/ \
  --model kimi-k2.6 --endpoint https://opencode.ai/zen/go/v1
```
