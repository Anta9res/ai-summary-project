# 快速开始指南

## 📦 安装

### 1. 克隆项目

```bash
git clone <repository_url>
cd Fall-Network
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置API密钥

**方式1：使用环境变量（推荐）**

```bash
# Windows (PowerShell)
$env:DASHSCOPE_API_KEY="your_api_key_here"

# Windows (CMD)
set DASHSCOPE_API_KEY=your_api_key_here

# Linux/Mac
export DASHSCOPE_API_KEY="your_api_key_here"
```

**方式2：使用配置文件**

```bash
# 复制配置示例
cp config.yaml.example config.yaml

# 编辑config.yaml，填入API密钥
# model:
#   api_key: "your_api_key_here"
```

## 🚀 基础使用

### 完整流程（推荐）

```bash
python cli.py --input 课件/ --output output/
```

这会自动完成：
1. PDF内容提取
2. AI笔记生成（v3.0应试化版本）
3. 质量检测和格式修复
4. 笔记整合（生成完整笔记和索引）

### 输出结构

```
output/
├── raw_texts/              # PDF提取的原始文本
│   ├── 数据通信与网络-第1讲_提取文本.md
│   └── ...
├── notes/                  # 生成的笔记
│   ├── 第1讲_笔记.md
│   ├── 第2讲_笔记.md
│   ├── ...
│   └── README.md
├── 完整复习笔记.md         # 所有笔记合并
└── 笔记索引.md             # 快速导航索引
```

## 🎯 常用场景

### 1. 首次使用

```bash
# 完整流程生成所有笔记
D:\anaconda3\python.exe cli.py --input 课件/ --output output/
```

### 2. 更新笔记

```bash
# 自动跳过已生成的笔记（断点续传）
D:\anaconda3\python.exe cli.py --input 课件/ --output output/
```

### 3. 重新生成所有笔记

```bash
# 强制重新生成
D:\anaconda3\python.exe cli.py --input 课件/ --output output/ --no-skip
```

### 4. 仅提取PDF文本

```bash
python cli.py --input 课件/ --output output/ --stage parse
```

### 5. 仅生成笔记

```bash
python cli.py --input 课件/ --output output/ --stage generate
```

### 6. 仅整合笔记

```bash
python cli.py --input 课件/ --output output/ --stage integrate
```

## 🔧 高级用法

### 使用v2.0提示词

```bash
python cli.py --input 课件/ --prompt-version v2.0
```

### 自定义配置文件

```bash
python cli.py --input 课件/ --config my_config.yaml
```

### 静默模式（仅显示错误）

```bash
python cli.py --input 课件/ --quiet
```

### 验证配置

```bash
python cli.py --validate-config
```

### 查看帮助

```bash
python cli.py --help
```

## 📊 处理时间估算

| PDF数量 | 预估时间 |
|---------|---------|
| 1-5个   | 2-5分钟 |
| 10个    | 5-10分钟 |
| 19个    | 10-15分钟 |

*注：实际时间取决于PDF大小和网络状况*

## 🎓 v3.0应试化特性

使用v3.0版本（默认）生成的笔记包含：

- ✅ **题型标注**：📝名词解释、📊计算题、✅选择题等
- ✅ **答题要点**：如何组织答案的框架
- ✅ **对比表格**：易混淆概念的清晰对比
- ✅ **计算示例**：公式应用的具体示例
- ✅ **考试重点**：必背概念、必会计算、易混淆点
- ✅ **学术表述**：去除类比口诀，使用规范表述

## 🐛 常见问题

### Q: API调用失败

**检查清单：**
- ✅ API密钥是否正确配置
- ✅ 网络连接是否正常
- ✅ API额度是否充足

**解决方案：**
```bash
# 验证配置
python cli.py --validate-config

# 查看详细日志
# 日志文件在 logs/ 目录
```

### Q: 生成的笔记质量不理想

**调整方法：**
1. 确认使用v3.0版本：`--prompt-version v3.0`
2. 检查质量报告（自动生成）
3. 使用`--no-skip`重新生成

### Q: 进度中断了怎么办

**恢复方法：**
```bash
# 直接重新运行，会自动跳过已完成部分
python cli.py --input 课件/ --output output/
```

### Q: 想同时处理多个学科

**操作方法：**
```bash
# 分别处理，使用不同输出目录
python cli.py --input 课件/Fall-Network/ --output output/Fall-Network/
python cli.py --input 课件/OS/ --output output/OS/
```

## 📚 更多信息

- **完整文档**: 查看 `README.md`
- **项目结构**: 查看 `README.md` 中的"项目结构"章节
- **配置说明**: 查看 `config.yaml.example`
- **故障排查**: 查看 `README.md` 中的"故障排查"章节

## 💡 最佳实践

1. **首次使用**：先用少量PDF测试（3-5个）
2. **断点续传**：保持默认开启，避免重复工作
3. **配置备份**：备份你的`config.yaml`
4. **日志查看**：遇到问题先查看`logs/`目录
5. **质量验证**：生成后检查质量报告

## 🎉 开始使用

```bash
# 就是这么简单！
python cli.py --input 课件/ --output output/
```

祝学习顺利！ 📖✨
