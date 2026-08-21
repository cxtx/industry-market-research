# 盐焗小调安装说明

“盐焗小调”的技术名称是 `industry-market-research`。安装时必须保留整个仓库目录，不能只复制 `SKILL.md`，因为运行还会用到 `scripts/`、`references/` 等文件。

安装前请确认本机已安装 [Git](https://git-scm.com/downloads)。如果目标目录已经存在，请直接执行本文的“更新”命令，不要重复克隆。

## Codex

### 让 Codex 自动安装（推荐）

把下面这段话复制给 Codex：

```text
使用 $skill-installer，把 https://github.com/cxtx/industry-market-research
安装为用户级 Skill，名称保持 industry-market-research；安装后确认 SKILL.md
及 scripts、references 目录完整，并验证 Skill 可以被识别。
```

### 手动安装

macOS / Linux：

```bash
mkdir -p "$HOME/.agents/skills"
git clone https://github.com/cxtx/industry-market-research.git \
  "$HOME/.agents/skills/industry-market-research"
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force "$HOME/.agents/skills" | Out-Null
git clone https://github.com/cxtx/industry-market-research.git `
  "$HOME/.agents/skills/industry-market-research"
```

安装完成后，在 Codex 中输入：

```text
$industry-market-research 调研中国连锁超市零售业
```

Codex 通常会自动发现新 Skill；如果没有出现，请重新启动 Codex。旧版 Codex 环境可能仍使用 `~/.codex/skills`，新安装建议使用当前的用户级目录 `~/.agents/skills`。

## Claude Code

### 让 Claude Code 自动安装

把下面这段话复制给 Claude Code：

```text
请把 https://github.com/cxtx/industry-market-research 完整克隆到
~/.claude/skills/industry-market-research。不要只复制 SKILL.md；安装后检查
scripts 和 references 目录完整，并验证 /industry-market-research 可以调用。
```

### 手动安装

macOS / Linux：

```bash
mkdir -p "$HOME/.claude/skills"
git clone https://github.com/cxtx/industry-market-research.git \
  "$HOME/.claude/skills/industry-market-research"
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force "$HOME/.claude/skills" | Out-Null
git clone https://github.com/cxtx/industry-market-research.git `
  "$HOME/.claude/skills/industry-market-research"
```

安装完成后，在 Claude Code 中输入：

```text
/industry-market-research 调研中国连锁超市零售业
```

Claude Code 通常会在当前会话中发现新 Skill；如果安装前 `~/.claude/skills` 目录不存在，安装后请重新启动 Claude Code。

## 更新

Codex：

```bash
git -C "$HOME/.agents/skills/industry-market-research" pull --ff-only
```

Claude Code：

```bash
git -C "$HOME/.claude/skills/industry-market-research" pull --ff-only
```

更新后若没有立即生效，重新启动对应应用即可。

## 安装验证

确认以下文件存在：

- Codex：`~/.agents/skills/industry-market-research/SKILL.md`
- Claude Code：`~/.claude/skills/industry-market-research/SKILL.md`

随后用上面的示例命令调用 Skill。能够识别“盐焗小调”并开始确认行业、地域、市场口径，即表示安装成功。
