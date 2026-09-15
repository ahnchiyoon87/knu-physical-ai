param(
    [Parameter(Mandatory=$true)][string]$Source,
    [Parameter(Mandatory=$true)][string]$OutputDirectory
)
$ErrorActionPreference = 'Stop'
$resolvedSource = (Resolve-Path -LiteralPath $Source).Path
if (Test-Path -LiteralPath $OutputDirectory) { throw '기존 렌더 폴더는 보존합니다. 새 경로를 지정하세요.' }
if (Get-Process POWERPNT -ErrorAction SilentlyContinue) { throw '열려 있는 PowerPoint를 보존합니다. 렌더를 시작하지 않습니다.' }
$renderDirectory = [IO.Path]::GetFullPath($OutputDirectory)
New-Item -ItemType Directory -Path $renderDirectory | Out-Null
$taskPowerPoint = $null
$taskPresentation = $null
try {
    $taskPowerPoint = New-Object -ComObject PowerPoint.Application
    $taskPresentation = $taskPowerPoint.Presentations.Open($resolvedSource, -1, 0, 0)
    $taskPresentation.Export($renderDirectory, 'PNG', 1600, 900)
    [pscustomobject]@{Source=$resolvedSource;Slides=$taskPresentation.Slides.Count;Output=$renderDirectory} | ConvertTo-Json
}
finally {
    if ($null -ne $taskPresentation) {
        $taskPresentation.Close()
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskPresentation)
    }
    if ($null -ne $taskPowerPoint) {
        $taskPowerPoint.Quit()
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($taskPowerPoint)
    }
}
