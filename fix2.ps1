$content = [IO.File]::ReadAllText("static/css/pages/dashboard/index.css", [System.Text.Encoding]::UTF8)
$content = $content -replace "(\.page-dashboard \.stat-card\.card-in-progress \{)", "`$1`n    /* Ensure relative positioning context for deadline tiles */`n    position: relative;"
[IO.File]::WriteAllText("static/css/pages/dashboard/index.css", $content, [System.Text.Encoding]::UTF8)
Write-Host "Done!"
