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
if (-not $ResourceGroup -and $env:AZURE_RESOURCE_GROUP) { $ResourceGroup = $env:AZURE_RESOURCE_GROUP }
if (-not $Location) {
    if ($env:FOUNDRY_LOCATION) { $Location = $env:FOUNDRY_LOCATION }
    elseif ($env:AZURE_REGION) { $Location = $env:AZURE_REGION }
}
if (-not $ResourceGroup) { $ResourceGroup = "LabVM-RG" }
if (-not $Location) { $Location = "westus" }

$FoundryEndpoint = if ($env:FOUNDRY_ENDPOINT) { $env:FOUNDRY_ENDPOINT.TrimEnd("/") } else { "https://my-ai-service-2364654.services.ai.azure.com" }
$FoundryModel = if ($env:FOUNDRY_MODEL_DEPLOYMENT) { $env:FOUNDRY_MODEL_DEPLOYMENT } else { "gpt-5.4" }
$FoundryAccountName = if ($env:FOUNDRY_ACCOUNT_NAME) { $env:FOUNDRY_ACCOUNT_NAME } else { "my-ai-service-2364654" }

$PizzaApiUrl = if ($env:PIZZA_API_URL) { $env:PIZZA_API_URL.TrimEnd("/") } else { "https://func-pizza-api-ceki46omdafoe.azurewebsites.net" }

function Build-FoundryArgs([string]$agent, [string]$message, [string]$rg, [string]$loc) {
    $args = @("foundry", "agent", "test", "--name", $agent, "--message", $message)
    if ($rg) { $args += @("--resource-group", $rg) }
    if ($loc) { $args += @("--location", $loc) }
    return ,$args
}

function Test-FoundryCliAvailable() {
    $az = Get-Command az -ErrorAction SilentlyContinue
    if (-not $az) { return $false }

    $previous = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & az foundry -h *> $null
    }
    catch {
        # Intentionally ignored.
    }
    finally {
        $ErrorActionPreference = $previous
    }
    return ($LASTEXITCODE -eq 0)
}

function Ensure-AzLogin() {
    try {
        az account show 1>$null 2>$null
    }
    catch {
        throw "Not logged in to Azure CLI. Run: az login"
    }
}

function Get-FoundryApiKey([string]$accountName, [string]$resourceGroup) {
    if ($env:FOUNDRY_API_KEY) { return $env:FOUNDRY_API_KEY }
    if ($env:AZURE_OPENAI_API_KEY) { return $env:AZURE_OPENAI_API_KEY }
    if (-not $resourceGroup) {
        throw "No API key in environment and AZURE_RESOURCE_GROUP is missing. Set FOUNDRY_API_KEY or AZURE_OPENAI_API_KEY."
    }

    $key = az cognitiveservices account keys list --name $accountName --resource-group $resourceGroup --query key1 -o tsv
    if (-not $key) {
        throw "Unable to resolve Foundry API key from Azure."
    }
    return $key.Trim()
}

function Invoke-JsonGet([string]$url, [hashtable]$headers) {
    return Invoke-RestMethod -Method Get -Uri $url -Headers $headers -TimeoutSec 60
}

function Invoke-JsonPost([string]$url, [hashtable]$headers, $bodyObject) {
    $body = $bodyObject | ConvertTo-Json -Depth 20
    return Invoke-RestMethod -Method Post -Uri $url -Headers $headers -Body $body -ContentType "application/json" -TimeoutSec 60
}

function Invoke-PizzaTool([string]$name, [object]$args) {
    if (-not $args) {
        $args = @{}
    }
    elseif ($args -isnot [hashtable]) {
        try {
            $args = ($args | ConvertTo-Json -Depth 20 | ConvertFrom-Json -AsHashtable)
        }
        catch {
            $args = @{}
        }
    }

    try {
        switch ($name) {
            "menu_lookup" {
                return Invoke-JsonGet -url "$PizzaApiUrl/api/menu" -headers @{}
            }
            "allergen_lookup" {
                $itemId = [string]$args.item_id
                if (-not $itemId) { throw "allergen_lookup requires item_id" }
                return Invoke-JsonGet -url "$PizzaApiUrl/api/allergens?item_id=$itemId" -headers @{}
            }
            "price_calc" {
                $payload = @{ order_items = @() }
                if ($args.ContainsKey("order_items")) { $payload.order_items = $args.order_items }
                return Invoke-JsonPost -url "$PizzaApiUrl/api/price" -headers @{} -bodyObject $payload
            }
            "order_submit" {
                $payload = @{}
                foreach ($k in $args.Keys) { $payload[$k] = $args[$k] }
                if (-not $payload.ContainsKey("order_id") -or -not $payload.order_id) {
                    $payload.order_id = [Guid]::NewGuid().ToString()
                }
                return Invoke-JsonPost -url "$PizzaApiUrl/api/orders" -headers @{} -bodyObject $payload
            }
            "order_status" {
                $orderId = [string]$args.order_id
                if (-not $orderId) { throw "order_status requires order_id" }
                return Invoke-JsonGet -url "$PizzaApiUrl/api/orders/$orderId" -headers @{}
            }
            "human_handoff" {
                return Invoke-JsonPost -url "$PizzaApiUrl/api/escalations" -headers @{} -bodyObject $args
            }
            default {
                throw "Unknown tool call: $name"
            }
        }
    }
    catch {
        return @{
            error = "tool_http_error"
            tool = $name
            detail = $_.Exception.Message
        }
    }
}

function Get-ToolSpec() {
    return @(
        @{
            type = "function"
            name = "menu_lookup"
            description = "Get available pizza menu items."
            parameters = @{ type = "object"; properties = @{}; additionalProperties = $false }
        },
        @{
            type = "function"
            name = "allergen_lookup"
            description = "Get allergen details for a menu item id."
            parameters = @{
                type = "object"
                properties = @{ item_id = @{ type = "string" } }
                required = @("item_id")
                additionalProperties = $false
            }
        },
        @{
            type = "function"
            name = "price_calc"
            description = "Calculate order total from order_items."
            parameters = @{
                type = "object"
                properties = @{ order_items = @{ type = "array"; items = @{ type = "object" } } }
                required = @("order_items")
                additionalProperties = $true
            }
        },
        @{
            type = "function"
            name = "order_submit"
            description = "Submit a confirmed order."
            parameters = @{ type = "object"; properties = @{}; additionalProperties = $true }
        },
        @{
            type = "function"
            name = "order_status"
            description = "Get order status by order_id."
            parameters = @{
                type = "object"
                properties = @{ order_id = @{ type = "string" } }
                required = @("order_id")
                additionalProperties = $false
            }
        },
        @{
            type = "function"
            name = "human_handoff"
            description = "Escalate to human support."
            parameters = @{ type = "object"; properties = @{}; additionalProperties = $true }
        }
    )
}

function Get-AssistantText($responseObject) {
    if (-not $responseObject.output) { return "" }
    foreach ($item in $responseObject.output) {
        if ($item.type -eq "message" -and $item.content) {
            foreach ($content in $item.content) {
                if ($content.type -eq "output_text" -and $content.text) {
                    return [string]$content.text
                }
            }
        }
    }
    return ""
}

function Invoke-FoundryResponsesChat([string]$userMessage, [hashtable]$headers) {
    $url = "$FoundryEndpoint/openai/v1/responses"
    $instructions = "You are Crust, a pizza ordering agent. Use tools for menu, pricing, allergens, order submission, and order status. Confirm details before calling order_submit."
    $tools = Get-ToolSpec

    $request = @{
        model = $FoundryModel
        input = $userMessage
        instructions = $instructions
        tools = $tools
        tool_choice = "auto"
    }

    $response = Invoke-JsonPost -url $url -headers $headers -bodyObject $request
    $iterations = 0
    while ($true) {
        $iterations += 1
        if ($iterations -gt 8) {
            throw "Tool-call loop exceeded maximum iterations."
        }

        $toolCalls = @()
        if ($response.output) {
            foreach ($item in $response.output) {
                if ($item.type -eq "function_call") {
                    $toolCalls += $item
                }
            }
        }

        if ($toolCalls.Count -eq 0) {
            $text = Get-AssistantText -responseObject $response
            if (-not $text) { return "(No assistant text returned.)" }
            return $text
        }

        $toolOutputs = @()
        foreach ($call in $toolCalls) {
            $args = @{}
            if ($call.arguments) {
                try {
                    $parsed = $call.arguments | ConvertFrom-Json -AsHashtable
                    if ($parsed) { $args = $parsed }
                }
                catch {
                    $args = @{}
                }
            }

            $result = Invoke-PizzaTool -name $call.name -args $args
            $resultJson = $result | ConvertTo-Json -Depth 20 -Compress
            $toolOutputs += @{
                type = "function_call_output"
                call_id = $call.call_id
                output = $resultJson
            }
        }

        $nextRequest = @{
            model = $FoundryModel
            previous_response_id = $response.id
            input = $toolOutputs
            instructions = $instructions
            tools = $tools
            tool_choice = "auto"
        }
        $response = Invoke-JsonPost -url $url -headers $headers -bodyObject $nextRequest
    }
}

Ensure-AzLogin

if (Test-FoundryCliAvailable) {
    if ($Interactive) {
        Write-Host "Talking to production Foundry agent '$AgentName' via az foundry."
        Write-Host "Type 'exit' to quit."
        while ($true) {
            $inputText = Read-Host "you"
            if (-not $inputText) { continue }
            if ($inputText -ieq "exit") { break }

            $args = Build-FoundryArgs -agent $AgentName -message $inputText -rg $ResourceGroup -loc $Location
            & az @args
            if ($LASTEXITCODE -ne 0) {
                throw "az foundry agent test failed with exit code $LASTEXITCODE"
            }
        }
    }
    else {
        if (-not $Message) { throw "Provide -Message or use -Interactive." }
        $args = Build-FoundryArgs -agent $AgentName -message $Message -rg $ResourceGroup -loc $Location
        & az @args
        if ($LASTEXITCODE -ne 0) {
            throw "az foundry agent test failed with exit code $LASTEXITCODE"
        }
    }
    exit 0
}

Write-Host "az foundry is unavailable here. Using production Foundry Responses API fallback." -ForegroundColor Yellow
$apiKey = Get-FoundryApiKey -accountName $FoundryAccountName -resourceGroup $ResourceGroup
$headers = @{ "api-key" = $apiKey }

if ($Interactive) {
    Write-Host "Talking to production Foundry Responses endpoint '$FoundryEndpoint' with model '$FoundryModel'."
    Write-Host "Type 'exit' to quit."
    while ($true) {
        $inputText = Read-Host "you"
        if (-not $inputText) { continue }
        if ($inputText -ieq "exit") { break }

        $reply = Invoke-FoundryResponsesChat -userMessage $inputText -headers $headers
        Write-Host "crust> $reply"
    }
}
else {
    if (-not $Message) { throw "Provide -Message or use -Interactive." }
    $reply = Invoke-FoundryResponsesChat -userMessage $Message -headers $headers
    Write-Host $reply
}
