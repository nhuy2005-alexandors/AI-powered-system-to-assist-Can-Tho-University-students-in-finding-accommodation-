# Isolated catalog789 clone setup. Never prints credentials or raw Docker/SQL errors.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$bootstrapStage = 'preflight'
$repo = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$runtime = 'D:\Dev\Data\NCKH\mobility-catalog-acceptance-20261004-01'
$container = 'nckh-mobility-acceptance-db'
$volume = 'nckh_mobility_acceptance_pgdata'
$project = 'nckh-mobility-acceptance'
$image = 'nckh-student-housing:789-20261002'
$imageId = 'sha256:dcea513d8f8c0bd2b314bfaa672d1bb3a91d100c401afe34f139dcd3c5869bdd'
$catalogSha = 'b859bab1dc66808adc897f8f2b0b858d6aa2aa3954e52fc92c8e816e533b5947'
$zipSha = '25cbfca2a36adf2f93772a5e48db8f6a0a8b48e777de41668d7a4b4ee5911a4a'
$gateSha = 'e08c0ee7478127d6e7d514215b32f2a7463825ec25fb246ee35f2b0ee5eff3fc'
$packageId = 'ccd4bb988a93e6b676d2baa49de70d7e20a9b63c64a836bd673e514c95371d35'
$dockerConfig = Join-Path $repo '.superpowers\sdd\2026-10-05-open-mobility-agent-plan\docker-readonly-config'

function Invoke-PrivateProcess([string]$Executable, [string[]]$Arguments, [string]$InputText = '', [int]$TimeoutSeconds = 20, [string]$WorkingDirectory = $repo) {
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $Executable
    foreach ($argument in $Arguments) { $psi.ArgumentList.Add($argument) }
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.RedirectStandardInput = $true
    $psi.Environment.Clear()
    foreach ($key in @('PATH','SYSTEMROOT','WINDIR','TEMP','TMP','COMSPEC','PATHEXT','ProgramFiles')) {
        $value = [Environment]::GetEnvironmentVariable($key)
        if ($null -ne $value) { $psi.Environment[$key] = $value }
    }
    $psi.Environment['DOCKER_CONFIG'] = $dockerConfig
    $p = [Diagnostics.Process]::Start($psi)
    $out = $p.StandardOutput.ReadToEndAsync()
    $err = $p.StandardError.ReadToEndAsync()
    if ($InputText.Length -gt 0) { $p.StandardInput.Write($InputText) }
    $p.StandardInput.Close()
    if (-not $p.WaitForExit($TimeoutSeconds * 1000)) { $p.Kill($true); $p.WaitForExit(); throw 'operation timeout' }
    $stdout = $out.GetAwaiter().GetResult()
    $null = $err.GetAwaiter().GetResult()
    $exit = $p.ExitCode
    $p.Dispose()
    if ($exit -ne 0) { throw 'operation failed' }
    return $stdout.Trim()
}
function Write-Exclusive([string]$Path, [string]$Value) {
    $bytes = [Text.UTF8Encoding]::new($false).GetBytes($Value)
    $stream = [IO.File]::Open($Path, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
}
function New-PrivateSecret {
    $bytes = [byte[]]::new(32)
    [Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return [Convert]::ToHexString($bytes).ToLowerInvariant()
}
try {
    if ((Get-FileHash -LiteralPath (Join-Path $repo '.codex-gate.json') -Algorithm SHA256).Hash.ToLowerInvariant() -ne $gateSha) { throw 'gate mismatch' }
    if ((Get-FileHash -LiteralPath 'D:\Dev\Data\NCKH\student-housing-docker-20261002-04\catalog\CATALOG.jsonl' -Algorithm SHA256).Hash.ToLowerInvariant() -ne $catalogSha) { throw 'source mismatch' }
    if ((Get-FileHash -LiteralPath 'D:\Dev\Data\NCKH\student-housing-789-Docker-INTERNAL.zip' -Algorithm SHA256).Hash.ToLowerInvariant() -ne $zipSha) { throw 'source mismatch' }
    if (Test-Path -LiteralPath $runtime) { throw 'runtime exists' }
    $ancestor = [IO.DirectoryInfo]::new([IO.Path]::GetDirectoryName($runtime))
    while ($null -ne $ancestor) {
        if (-not $ancestor.Exists -or ($ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw 'invalid runtime ancestor' }
        $ancestor = $ancestor.Parent
    }
    if (-not (Test-Path -LiteralPath $dockerConfig -PathType Container) -or (Get-ChildItem -LiteralPath $dockerConfig -Force | Measure-Object).Count -ne 0) { throw 'Docker config not empty' }
    $docker = (Get-Command docker.exe -CommandType Application | Select-Object -First 1).Source
    $null = Invoke-PrivateProcess $docker @('info','--format','{{.ServerVersion}}')
    $names = @( (Invoke-PrivateProcess $docker @('ps','-a','--format','{{.Names}}')) -split "`n" )
    $volumes = @( (Invoke-PrivateProcess $docker @('volume','ls','--format','{{.Name}}')) -split "`n" )
    if ($names -contains $container -or $volumes -contains $volume) { throw 'target exists' }
    if ((Invoke-PrivateProcess $docker @('image','inspect',$image,'--format','{{.Id}}')) -ne $imageId) { throw 'image mismatch' }
    foreach ($port in @(5455,8032,3032)) {
        $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $port)
        try { $listener.Start() } finally { $listener.Stop() }
    }
    $bootstrapStage = 'private-runtime'
    $null = [IO.Directory]::CreateDirectory($runtime)
    $sid = [Security.Principal.WindowsIdentity]::GetCurrent().User
    $acl = [Security.AccessControl.DirectorySecurity]::new()
    $acl.SetOwner($sid)
    $acl.SetAccessRuleProtection($true, $false)
    $rule = [Security.AccessControl.FileSystemAccessRule]::new($sid, [Security.AccessControl.FileSystemRights]::FullControl,
        [Security.AccessControl.InheritanceFlags]'ContainerInherit,ObjectInherit', [Security.AccessControl.PropagationFlags]::None, [Security.AccessControl.AccessControlType]::Allow)
    $acl.AddAccessRule($rule)
    Set-Acl -LiteralPath $runtime -AclObject $acl
    $actualAcl = Get-Acl -LiteralPath $runtime
    if (-not $actualAcl.AreAccessRulesProtected -or $actualAcl.GetOwner([Security.Principal.SecurityIdentifier]).Value -ne $sid.Value -or $actualAcl.Access.Count -ne 1) { throw 'runtime ACL mismatch' }
    $operation = [Guid]::NewGuid().ToString()
    $ownerPassword = New-PrivateSecret
    $readerPassword = New-PrivateSecret
    Write-Exclusive (Join-Path $runtime 'owner-password') $ownerPassword
    Write-Exclusive (Join-Path $runtime 'reader-password') $readerPassword
    $config = [ordered]@{operation_id=$operation;host='127.0.0.1';port=5455;database='mobility_catalog_acceptance';user='mobility_catalog_reader';password=$readerPassword;container=$container;project=$project;volume=$volume}
    Write-Exclusive (Join-Path $runtime 'runtime-config.json') ($config | ConvertTo-Json -Compress)
    $compose = @"
name: $project
services:
  db:
    image: $image
    pull_policy: never
    container_name: $container
    labels:
      nckh.acceptance.operation: '$operation'
      nckh.acceptance.catalog_sha256: '$catalogSha'
    environment:
      POSTGRES_DB: mobility_catalog_acceptance
      POSTGRES_USER: nckh_handoff
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password
    secrets: [db_password]
    ports: ['127.0.0.1:5455:5432']
    volumes: ['data:/var/lib/postgresql/data']
    healthcheck:
      test: ['CMD', '/opt/handoff/check-ready.sh']
      interval: 5s
      timeout: 3s
      retries: 36
      start_period: 30s
volumes:
  data:
    name: $volume
    labels:
      nckh.acceptance.operation: '$operation'
      nckh.acceptance.catalog_sha256: '$catalogSha'
secrets:
  db_password:
    file: ./owner-password
"@
    Write-Exclusive (Join-Path $runtime 'compose.yaml') $compose
    $bootstrapStage = 'clone-start'
    $null = Invoke-PrivateProcess $docker @('compose','-p',$project,'-f',(Join-Path $runtime 'compose.yaml'),'up','-d','--pull','never','db') '' 60 $runtime
    $deadline = [DateTime]::UtcNow.AddSeconds(180)
    do {
        $health = Invoke-PrivateProcess $docker @('inspect',$container,'--format','{{.State.Health.Status}}')
        if ($health -eq 'healthy') { break }
        if ($health -eq 'unhealthy' -or [DateTime]::UtcNow -ge $deadline) { throw 'clone not healthy' }
        Start-Sleep -Milliseconds 500
    } while ($true)
    $bootstrapStage = 'clone-identity'
    $inspect = (Invoke-PrivateProcess $docker @('container','inspect',$container)) | ConvertFrom-Json
    $observed = @($inspect)[0]
    $binding = @($observed.NetworkSettings.Ports.'5432/tcp')
    $mount = @($observed.Mounts | Where-Object Destination -EQ '/var/lib/postgresql/data')
    $v = @((Invoke-PrivateProcess $docker @('volume','inspect',$volume)) | ConvertFrom-Json)[0]
    if ($observed.Name -ne ('/'+$container) -or $observed.Image -ne $imageId -or
        $observed.Config.Labels.'nckh.acceptance.operation' -ne $operation -or
        $observed.Config.Labels.'nckh.acceptance.catalog_sha256' -ne $catalogSha -or
        $observed.Config.Labels.'com.docker.compose.project' -ne $project -or
        $binding.Count -ne 1 -or $binding[0].HostIp -ne '127.0.0.1' -or $binding[0].HostPort -ne '5455' -or
        $mount.Count -ne 1 -or $mount[0].Type -ne 'volume' -or $mount[0].Name -ne $volume -or $mount[0].RW -ne $true -or
        @($observed.Mounts | Where-Object Type -EQ 'volume').Count -ne 1 -or
        $v.Name -ne $volume -or $v.Labels.'nckh.acceptance.operation' -ne $operation -or
        $v.Labels.'nckh.acceptance.catalog_sha256' -ne $catalogSha -or $v.Labels.'com.docker.compose.project' -ne $project) { throw 'clone identity mismatch' }
    if ((Invoke-PrivateProcess $docker @('exec',$container,'cat','/opt/handoff/package-id')) -ne $packageId) { throw 'package mismatch' }
    $counts = Invoke-PrivateProcess $docker @('exec',$container,'psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','nckh_handoff','-d','mobility_catalog_acceptance','-c',"SELECT current_database() || ':' || (SELECT count(*) FROM public.aggregated_listings) || ':' || (SELECT count(*) FROM public.catalog_handoff_metadata)")
    if ($counts -ne 'mobility_catalog_acceptance:789:789') { throw 'clone data count mismatch' }
    $bootstrapStage = 'reader-setup'
    $sql = @"
BEGIN;
CREATE ROLE mobility_catalog_reader LOGIN PASSWORD '$readerPassword' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOBYPASSRLS;
REVOKE CREATE ON DATABASE mobility_catalog_acceptance FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT CONNECT ON DATABASE mobility_catalog_acceptance TO mobility_catalog_reader;
GRANT USAGE ON SCHEMA public TO mobility_catalog_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mobility_catalog_reader;
ALTER ROLE mobility_catalog_reader SET default_transaction_read_only = on;
COMMIT;
"@
    $null = Invoke-PrivateProcess $docker @('exec','-i',$container,'psql','-X','-q','-v','ON_ERROR_STOP=1','-U','nckh_handoff','-d','mobility_catalog_acceptance') $sql
    Write-Exclusive (Join-Path $runtime 'BOOTSTRAP.json') (@{status='CLONE_READY';operation_id=$operation;image_id=$imageId;catalog_sha256=$catalogSha;database='mobility_catalog_acceptance';port=5455;rows=789} | ConvertTo-Json -Compress)
    $ownerPassword = $readerPassword = $sql = $null
    Write-Output '{"status":"PASS","code":"ISOLATED_CLONE_READY","rows":789,"port":5455}'
    exit 0
} catch {
    Write-Output ('{"status":"FAIL","code":"ISOLATED_CLONE_NOT_READY","stage":"'+$bootstrapStage+'"}')
    exit 1
}
