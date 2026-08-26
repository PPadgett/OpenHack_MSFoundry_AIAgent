param(
    [string]$AgentName = "crust",
    [string]$ResourceGroup = "",
    [string]$Location = "",
    [string]$Message = "",
    [switch]$Interactive
)

$ErrorActionPreference = "Stop"

if (-not $AgentName -or $AgentName -eq "crust") {
    if ($env:FOUNDRY_AGENT_NAME) {
        $AgentName = $env:FOUNDRY_AGENT_NAME
    }
}

if (-not $ResourceGroup -and $env:AZURE_RESOURCE_GROUP) {
    $ResourceGroup = $env:AZURE_RESOURCE_GROUP
}

if (-not $Location) {
    if ($env:FOUNDRY_LOCATION) {
        $Location = $env:FOUNDRY_LOCATION
    }
    elseif ($env:AZURE_REGION) {
        $Location = $env:AZURE_REGION
    }
}

function Build-Args([string]$agent, [string]$message, [string]$rg, [string]$loc) {
    $args = @("foundry", "agent", "test", "--name", $agent, "--message", $message)
    if ($rg) {
        $args += @("--resource-group", $rg)
    }
    if ($loc) {
        $args += @("--location", $loc)
    }
    return ,$args
}

function Require-AzCli() {
    $az = Get-Command az -ErrorAction SilentlyContinue
    if (-not $az) {
        throw "Azure CLI (az) not found. Install Azure CLI first."
    }

    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & az foundry -h *> $null
    }
    catch {
        # Intentionally swallowed; availability is verified via LASTEXITCODE below.
    }
    finally {
        $ErrorActionPreference = $previousPreference
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Azure CLI is installed but the 'foundry' command group is unavailable. Install the required extension/tooling, then retry."
    }
}

function Ensure-Login() {
    try {
        az account show 1>$null 2>$null
    }
    catch {
        throw "Not logged in to Azure CLI. Run: az login"
    }
}

Require-AzCli
Ensure-Login

if ($Interactive) {
    Write-Host "Talking to production Foundry agent '$AgentName'."
    Write-Host "Type 'exit' to quit."
    while ($true) {
        $inputText = Read-Host "you"
        if (-not $inputText) {
            continue
        }
        if ($inputText -ieq "exit") {
            break
        }

        $args = Build-Args -agent $AgentName -message $inputText -rg $ResourceGroup -loc $Location
        & az @args
        if ($LASTEXITCODE -ne 0) {
            throw "az foundry agent test failed with exit code $LASTEXITCODE"
        }
    }
}
else {
    if (-not $Message) {
        throw "Provide -Message or use -Interactive."
    }

    $args = Build-Args -agent $AgentName -message $Message -rg $ResourceGroup -loc $Location
    & az @args
    if ($LASTEXITCODE -ne 0) {
        throw "az foundry agent test failed with exit code $LASTEXITCODE"
    }
}
