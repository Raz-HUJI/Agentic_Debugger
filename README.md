# Agentic Debugger CLI (v1.0)

Use this project as a command-line tool named `agent_fix` to scan other projects.

## What this gives you

The `agent_fix` command supports:
- `triage`: analyze only (no judge verdict)
- `fix`: analyze + propose fix + judge against a rubric
- `audit`: same as `fix`, but rubric is required

## Requirements

- Python `3.10` to `3.12` recommended
- PowerShell (Windows)
- `OPENAI_API_KEY`

## One-time project setup

From this repository root:

```powershell
pip install -r requirements.txt
```

Create `.env` in this repository root:

```env
OPENAI_API_KEY=your_openai_key_here
SERPER_API_KEY=optional_serper_key
MODEL_NAME=gpt-4o-mini
```

`OPENAI_API_KEY` is required. `SERPER_API_KEY` is optional.

## Make `agent_fix` a PowerShell command

This adds a persistent `agent_fix` function to your PowerShell profile, so you can run:
`agent_fix triage --target-dir "C:\path\to\project"`

### Automatic setup (recommended)

```powershell
.\install-agent-fix-cli.ps1
```

To install and reload your profile in one step:

```powershell
.\install-agent-fix-cli.ps1 -ReloadProfile
```

If script execution is blocked in your current shell session, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\install-agent-fix-cli.ps1 -ReloadProfile
```

### Verify

```powershell
agent_fix --help
```

### Manual setup (fallback)

```powershell
if (!(Test-Path $PROFILE)) { New-Item -Type File -Path $PROFILE -Force }
@'
function agent_fix {
    & python "C:\path\to\Agentic_Debugger\agent_fix.py" @args
}
'@ | Add-Content $PROFILE
. $PROFILE
```

## Usage examples

### Triage (analysis only)

```powershell
agent_fix triage --target-dir "C:\path\to\SomeOtherProject"
```

With JSON output:

```powershell
agent_fix triage --target-dir "C:\path\to\SomeOtherProject" --output "C:\path\to\triage_result.json"
```

### Fix (default rubric: `rubrics/code_quality_rubric.json`)

```powershell
agent_fix fix --target-dir "C:\path\to\SomeOtherProject"
```

With explicit rubric:

```powershell
agent_fix fix --target-dir "C:\path\to\SomeOtherProject" --rubric "rubrics\security_rubric.json"
```

### Audit (rubric required)

```powershell
agent_fix audit --target-dir "C:\path\to\SomeOtherProject" --rubric "rubrics\performance_rubric.json"
```

## Exit codes

- `0`: success (triage complete, or fix/audit approved)
- `1`: config error (missing env vars)
- `2`: input error (bad path, malformed rubric)
- `3`: unexpected runtime error
- `10`: fix/audit ran but was rejected by the judge

## Available rubrics

- `rubrics/code_quality_rubric.json`
- `rubrics/security_rubric.json`
- `rubrics/performance_rubric.json`
