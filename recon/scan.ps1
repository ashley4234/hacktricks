param(
    [string]$HostFile,    # Host file path (no default)
    [string]$PortFile,    # Port file path (no default)
    [string[]]$h,         # Specify hosts directly (e.g., -h 192.168.1.1,192.168.1.2)
    [string[]]$p,         # Specify ports directly (e.g., -p 22,80,445)
    [switch]$HideClosed,  # Hide closed/filtered ports (show by default)
    [int]$Timeout = 1000, # Connection timeout in milliseconds
    [int]$Interval = 0,   # Basic interval between port scans in milliseconds
    [int]$Jitter = 0,     # Random variation range for interval in milliseconds
    [string]$Outfile      # Output file path (default: result_portscan_YYYYMMDD.txt)
)

# Set output file path
if (-not $Outfile) {
    $dateString = Get-Date -Format "yyyyMMdd"
    $Outfile = "result_portscan_$dateString.txt"
}

# Get target hosts: use arguments if specified, otherwise read from file
if ($h) {
    $Targets = $h
} elseif ($HostFile) {
    # Check if host file exists
    if (-not (Test-Path $HostFile)) {
        Write-Error "Host file not found: $HostFile"
        return
    }
    $Targets = Get-Content $HostFile
} else {
    Write-Error "Please specify target hosts using -h parameter or -HostFile parameter"
    return
}

# Get target ports: use arguments if specified, otherwise read from file, or use default ports
if ($p) {
    # Convert comma-separated string to array (supports both -p "22,80,445" and -p 22,80,445)
    $Ports = $p -split ',' | ForEach-Object { $_.Trim() }
} elseif ($PortFile) {
    if (-not (Test-Path $PortFile)) {
        Write-Error "Port file not found: $PortFile"
        return
    }
    $Ports = Get-Content $PortFile
} else {
    # Default ports
    $Ports = @('21','22','80','135','139','443','445','1433','1521','3306','3389','5432','5900','5985','8000','8080')
    Write-Host "No port specification provided. Using default ports." -ForegroundColor Yellow
}

Write-Host "Starting scan..."
Write-Host "Target source: $(if ($h) { 'Command line arguments' } else { $HostFile })"
Write-Host "Port source: $(if ($p) { 'Command line arguments' } elseif ($PortFile) { $PortFile } else { 'Default ports' })"
Write-Host "Number of target hosts: $($Targets.Count)"
Write-Host "Number of target ports: $($Ports.Count)"
Write-Host "Timeout: $Timeout ms"
Write-Host "Interval: $Interval ms $(if ($Jitter -gt 0) { "(±$Jitter ms jitter)" })"
Write-Host "Output file: $Outfile"
Write-Host "--------------------------------"

# Initialize output content with scan information
$outputContent = @()
$outputContent += "Port Scan Results"
$outputContent += "Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$outputContent += "Target source: $(if ($h) { 'Command line arguments' } else { $HostFile })"
$outputContent += "Port source: $(if ($p) { 'Command line arguments' } elseif ($PortFile) { $PortFile } else { 'Default ports' })"
$outputContent += "Number of target hosts: $($Targets.Count)"
$outputContent += "Number of target ports: $($Ports.Count)"
$outputContent += "Timeout: $Timeout ms"
$outputContent += "Interval: $Interval ms $(if ($Jitter -gt 0) { "(±$Jitter ms jitter)" })"
$outputContent += "================================"
$outputContent += ""

function Test-Port {
    param(
        [string]$ComputerName,
        [int]$Port,
        [int]$Timeout = 1000
    )
    
    $tcpClient = New-Object System.Net.Sockets.TcpClient
    try {
        $asyncResult = $tcpClient.BeginConnect($ComputerName, $Port, $null, $null)
        $wait = $asyncResult.AsyncWaitHandle.WaitOne($Timeout, $false)
        
        if ($wait) {
            try {
                $tcpClient.EndConnect($asyncResult)
                return $true
            }
            catch {
                return $false
            }
        }
        else {
            return $false
        }
    }
    catch {
        return $false
    }
    finally {
        $tcpClient.Close()
    }
}

foreach ($Target in $Targets) {
    Write-Host "Scanning: $Target"
    
    # Store results for each target in an array
    $results = @()
    
    for ($i = 0; $i -lt $Ports.Count; $i++) {
        $Port = $Ports[$i]
        $isOpen = Test-Port -ComputerName $Target -Port $Port -Timeout $Timeout
        
        if ($isOpen) {
            $results += [PSCustomObject]@{
                ComputerName = $Target
                Port         = $Port
                Status       = 'Open'
            }
        }
        else {
            # Show closed/filtered ports by default, hide with HideClosed switch
            if (-not $HideClosed) {
                $results += [PSCustomObject]@{
                    ComputerName = $Target
                    Port         = $Port
                    Status       = 'Closed/Filtered'
                }
            }
        }
        
        # Apply interval and jitter except for the last port
        if ($i -lt ($Ports.Count - 1)) {
            $actualInterval = $Interval
            
            # Add random jitter if specified
            if ($Jitter -gt 0) {
                $randomJitter = Get-Random -Minimum (-$Jitter) -Maximum ($Jitter + 1)
                $actualInterval += $randomJitter
                
                # Ensure interval doesn't become negative
                if ($actualInterval -lt 0) {
                    $actualInterval = 0
                }
            }
            
            # Sleep only if interval is greater than 0
            if ($actualInterval -gt 0) {
                Start-Sleep -Milliseconds $actualInterval
            }
        }
    }
    
    # Output results to console and prepare for file output
    if ($results.Count -gt 0) {
        # Display to console
        $results | Format-Table -AutoSize
        
        # Add to output content for file
        $outputContent += "Target: $Target"
        $outputContent += "$('{0,-15} {1,-6} {2}' -f 'ComputerName', 'Port', 'Status')"
        $outputContent += "$('{0,-15} {1,-6} {2}' -f '------------', '----', '------')"
        foreach ($result in $results) {
            $outputContent += "$('{0,-15} {1,-6} {2}' -f $result.ComputerName, $result.Port, $result.Status)"
        }
        $outputContent += ""
    }
    else {
        Write-Host "  No results to display for $Target" -ForegroundColor Yellow
        $outputContent += "Target: $Target"
        $outputContent += "  No results to display"
        $outputContent += ""
    }
    Write-Host ""  # Empty line to separate targets
}

# Write results to file
try {
    $outputContent += "================================"
    $outputContent += "Scan completed: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    
    $outputContent | Out-File -FilePath $Outfile -Encoding UTF8
    Write-Host "Results saved to: $Outfile" -ForegroundColor Green
} catch {
    Write-Error "Failed to write output file: $($_.Exception.Message)"
}

Write-Host "--------------------------------"
Write-Host "Scan completed."
