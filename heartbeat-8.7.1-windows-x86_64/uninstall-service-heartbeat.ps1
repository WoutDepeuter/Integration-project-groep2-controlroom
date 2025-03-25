# Delete and stop the service if it already exists.
if (Get-Service heartbeat -ErrorAction SilentlyContinue) {
  Stop-Service heartbeat
  (Get-Service heartbeat).WaitForStatus('Stopped')
  Start-Sleep -s 1
  sc.exe delete heartbeat
}
