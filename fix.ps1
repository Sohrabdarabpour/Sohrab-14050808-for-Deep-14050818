$content = [IO.File]::ReadAllText("static/css/pages/dashboard/index.css", [System.Text.Encoding]::UTF8)
$old = "position: absolute;`n    top: 0; left: 50%;`n    transform: translate(-50%, -50%);`n    display: flex;`n    gap: 12px;`n    align-items: center;`n    z-index: 5;"
$new = "position: relative; /* Changed from absolute to relative flow */`n    top: auto; left: auto;`n    transform: none;`n    display: flex;`n    gap: 10px;`n    align-items: center;`n    justify-content: center;`n    flex-wrap: wrap;`n    margin-top: -28px; /* Slight negative margin to visually connect with icon */`n    margin-bottom: 10px;`n    z-index: 5;`n    padding: 0 12px;"
$content = $content -replace "(\.page-dashboard \.card-in-progress \{)", "`$1`n    /* Ensure relative positioning context for deadline tiles */`n    position: relative;"
$content = $content -replace [regex]::Escape($old), $new
[IO.File]::WriteAllText("static/css/pages/dashboard/index.css", $content, [System.Text.Encoding]::UTF8)
Write-Host "Done!"
