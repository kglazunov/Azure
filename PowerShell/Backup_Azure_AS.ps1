#The backup must be enabled for Analysis Services.
#The Credentials must be created before run this script.
#
#Connection strings
$myCred = Get-AutomationPSCredential -Name 'CHANGEME'
$azureAccountName = $myCred.UserName
$azurePassword = $myCred.Password
$psCred = New-Object System.Management.Automation.PSCredential($azureAccountName, $azurePassword)
$ServerName = "asazure://CHANGEME.asazure.windows.net/CHANGEME"

#Timestamp
$Dt = Get-Date -f yyyyMMddhhmm

#List databases(listing databases through Microsoft.AnalysisServices.Server not working as expected now)
$Databases = @("CHANGEME_DB0", "CHANGEME_DB1", "CHANGEME_DB2")

#Iteration with replacing space in backup file name
foreach ($Database in $Databases)
{
 
 $Database_bkp = $Database -replace ' ','_'
 $BackupFile =  $Database_bkp + "_" + $dt + ".abf"

 Write-Host "Starting to backup $Database to $BackupFile" -ForegroundColor Green
 Backup-ASDatabase -ServicePrincipal -Credential $psCred -Server $ServerName -BackupFile $BackupFile -Name $Database -ApplyCompression -ErrorAction Stop
 Write-Host "$Database has been backed up successfully." -ForegroundColor Green
}
