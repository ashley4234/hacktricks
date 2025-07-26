# PowerShell Port Scanner

A high-performance PowerShell port scanner that uses TcpClient for fast and reliable port scanning with customizable timing controls.

## Features

- **Fast scanning**: Uses System.Net.Sockets.TcpClient for efficient port testing
- **Flexible target specification**: Support both command-line arguments and file-based input
- **Default port list**: Includes common service ports when no ports are specified
- **Timing controls**: Configurable intervals and jitter for stealth scanning
- **Clean output**: Results grouped by target host with formatted tables
- **Closed port visibility**: Show or hide closed/filtered ports

## Usage

### Basic Syntax

```powershell
.\scan.ps1 [parameters]
```

### Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `-h` | string[] | Target hosts (comma-separated) | `-h 192.168.1.1,192.168.1.2` |
| `-p` | string[] | Target ports (comma-separated) | `-p 22,80,443` |
| `-HostFile` | string | Path to host file | `-HostFile hosts.txt` |
| `-PortFile` | string | Path to port file | `-PortFile ports.txt` |
| `-HideClosed` | switch | Hide closed/filtered ports | `-HideClosed` |
| `-Timeout` | int | Connection timeout (ms) | `-Timeout 2000` |
| `-Interval` | int | Delay between port scans (ms) | `-Interval 500` |
| `-Jitter` | int | Random variation for interval (ms) | `-Jitter 200` |

### Default Ports

When no ports are specified via `-p` or `-PortFile`, the scanner uses these default ports:

```
21, 22, 80, 135, 139, 443, 445, 1433, 1521, 3306, 3389, 5432, 5900, 5985, 8000, 8080
```

These include common services:
- **Web**: 80 (HTTP), 443 (HTTPS), 8000, 8080
- **Remote Access**: 22 (SSH), 3389 (RDP), 5900 (VNC), 5985 (WinRM)
- **File Sharing**: 21 (FTP), 445 (SMB)
- **Windows Services**: 135 (RPC), 139 (NetBIOS)
- **Databases**: 1433 (MSSQL), 1521 (Oracle), 3306 (MySQL), 5432 (PostgreSQL)

## Examples

### Basic Scanning

```powershell
# Scan single host with default ports
.\scan.ps1 -h 192.168.1.1

# Scan multiple hosts with specific ports
.\scan.ps1 -h 192.168.1.1,192.168.1.2,192.168.1.3 -p 22,80,443

# Scan with only open ports shown
.\scan.ps1 -h 192.168.1.1 -p 22,80,443 -HideClosed
```

### File-Based Scanning

```powershell
# Use host file with default ports
.\scan.ps1 -HostFile targets.txt

# Use both host and port files
.\scan.ps1 -HostFile targets.txt -PortFile services.txt

# Mix file and arguments
.\scan.ps1 -HostFile targets.txt -p 22,80,443
```

### Stealth Scanning

```powershell
# Add 1 second delay between scans
.\scan.ps1 -h 192.168.1.1 -Interval 1000

# Add random variation (800-1200ms intervals)
.\scan.ps1 -h 192.168.1.1 -Interval 1000 -Jitter 200

# Slow stealth scan with high variation
.\scan.ps1 -h 192.168.1.1 -Interval 5000 -Jitter 2000
```

### Performance Tuning

```powershell
# Fast scan with shorter timeout
.\scan.ps1 -h 192.168.1.1 -Timeout 500

# Very fast scan (no delays, short timeout, hide closed)
.\scan.ps1 -h 192.168.1.1 -Timeout 500 -HideClosed
```

## File Formats

### Host File Format
One host per line:
```
192.168.1.1
192.168.1.2
example.com
10.0.0.1
```

### Port File Format
One port per line:
```
22
80
443
3389
8080
```

## Sample Output

```
Starting scan...
Target source: Command line arguments
Port source: Default ports
Number of target hosts: 1
Number of target ports: 16
Timeout: 1000 ms
Interval: 0 ms
--------------------------------
Scanning: 192.168.1.1

ComputerName Port Status         
------------ ---- ------         
192.168.1.1  21   Closed/Filtered
192.168.1.1  22   Open           
192.168.1.1  80   Open           
192.168.1.1  135  Closed/Filtered
192.168.1.1  139  Closed/Filtered
192.168.1.1  443  Open           
192.168.1.1  445  Closed/Filtered

--------------------------------
Scan completed.
```

## Requirements

- PowerShell 5.1 or later
- Network connectivity to target hosts
- Appropriate firewall permissions

## Error Handling

The script will exit with an error if:
- No target hosts are specified (neither `-h` nor `-HostFile`)
- Specified files don't exist
- Invalid file formats

## Performance Notes

- Uses asynchronous TCP connections for better performance
- TcpClient implementation is faster than Test-NetConnection
- Configurable timeout prevents hanging on unresponsive hosts
- Results are batched per target for cleaner output

## Security Considerations

- Use appropriate intervals and jitter for stealth scanning
- Be aware of network monitoring and IDS systems
- Only scan networks you own or have permission to test
- Consider firewall logs and connection limits

## Troubleshooting

### Common Issues

1. **"No target hosts specified"**: Use `-h` parameter or `-HostFile`
2. **"File not found"**: Check file paths and permissions
3. **All ports show as closed**: Check network connectivity and firewall rules
4. **Slow performance**: Reduce timeout or add `-HideClosed` switch

### Tips

- Start with a small number of hosts and ports for testing
- Use `-HideClosed` for faster scans when only interested in open ports
- Adjust timeout based on network conditions (local: 500ms, remote: 2000ms+)
- Use intervals for rate limiting and stealth