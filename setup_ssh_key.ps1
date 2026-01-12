# Script to copy SSH public key to server
# Password: hero

Write-Host "Setting up SSH key authentication..." -ForegroundColor Cyan
Write-Host ""

$pubkeyPath = "$env:USERPROFILE\.ssh\id_rsa.pub"
$server = "hero@192.168.56.101"

if (Test-Path $pubkeyPath) {
    $pubkey = Get-Content $pubkeyPath
    Write-Host "Public key found!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Copying public key to server..." -ForegroundColor Yellow
    Write-Host "Password: hero" -ForegroundColor Gray
    Write-Host ""
    
    # Copy public key to server
    $pubkey | ssh $server "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && chmod 700 ~/.ssh"
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "Success! SSH key copied to server." -ForegroundColor Green
        Write-Host ""
        Write-Host "Testing connection (should not ask for password)..." -ForegroundColor Yellow
        ssh $server "echo 'SSH key authentication works!'"
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host ""
            Write-Host "========================================" -ForegroundColor Green
            Write-Host "SSH Key Authentication Setup Complete!" -ForegroundColor Green
            Write-Host "========================================" -ForegroundColor Green
        }
    } else {
        Write-Host ""
        Write-Host "Error copying key. Please run manually:" -ForegroundColor Red
        Write-Host "type $pubkeyPath | ssh $server 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys'" -ForegroundColor Yellow
    }
} else {
    Write-Host "Error: Public key not found at $pubkeyPath" -ForegroundColor Red
}

