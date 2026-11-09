$cfg = Join-Path $PSScriptRoot 'room_config.txt'
$utf8 = New-Object System.Text.UTF8Encoding $false
$text = ''
if (Test-Path $cfg) { $text = [IO.File]::ReadAllText($cfg, [Text.Encoding]::UTF8) }
$cur = ''
if ($text -match '(?m)^prefix=(\S*)') { $cur = $Matches[1] }

$rooms = @('201', '203')
Write-Host ''
Write-Host '=============================================='
Write-Host '   실습실 선택 (학생 PC 이름 앞자리와 같아야 함)'
Write-Host '=============================================='
for ($i = 0; $i -lt $rooms.Count; $i++) {
    $mark = ''
    if ($rooms[$i] -eq $cur) { $mark = '  <- 현재 설정' }
    Write-Host ("  {0}) {1}{2}" -f ($i + 1), $rooms[$i], $mark)
}
Write-Host ''
$ans = Read-Host "번호 선택 (Enter = 현재값 $cur 유지)"
$ans = $ans.Trim()

$sel = $cur
if ($ans -match '^[1-9]$' -and [int]$ans -le $rooms.Count) { $sel = $rooms[[int]$ans - 1] }
elseif ($ans -ne '') { Write-Host '잘못된 입력 - 현재값 유지'; }

if (-not $sel) { $sel = '201' }

if ($text -match '(?m)^prefix=') {
    $text = [regex]::Replace($text, '(?m)^prefix=.*$', "prefix=$sel")
} else {
    $text = "prefix=$sel`r`n" + $text
}
[IO.File]::WriteAllText($cfg, $text, $utf8)
Write-Host ''
Write-Host "선택된 실습실: $sel" -ForegroundColor Green
Write-Host ''
