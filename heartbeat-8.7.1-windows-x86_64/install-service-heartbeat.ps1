# Delete and stop the service if it already exists.
if (Get-Service heartbeat -ErrorAction SilentlyContinue) {
  Stop-Service heartbeat
  (Get-Service heartbeat).WaitForStatus('Stopped')
  Start-Sleep -s 1
  sc.exe delete heartbeat
}

$workdir = Split-Path $MyInvocation.MyCommand.Path

# Create the new service.
New-Service -name heartbeat `
  -displayName Heartbeat `
  -binaryPathName "`"$workdir\heartbeat.exe`" --environment=windows_service -c `"$workdir\heartbeat.yml`" --path.home `"$workdir`" --path.data `"$env:PROGRAMDATA\heartbeat`" --path.logs `"$env:PROGRAMDATA\heartbeat\logs`" -E logging.files.redirect_stderr=true"

# Attempt to set the service to delayed start using sc config.
Try {
  Start-Process -FilePath sc.exe -ArgumentList 'config heartbeat start= delayed-auto'
}
Catch { Write-Host -f red "An error occured setting the service to delayed start." }
