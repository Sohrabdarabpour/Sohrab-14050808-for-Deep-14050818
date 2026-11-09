$content = Get-Content "static/css/pages/dashboard/index.css" -Raw
$old = @"
/* ============================================================
   DEADLINE TILES (تنظیم شده برای عدم تداخل)
   ============================================================ */
.page-dashboard .card-in-progress .deadline-inline-tiles {
    position: absolute;
    top: 0; left: 50%;
    transform: translate(-50%, -50%);
    display: flex;
    gap: 12px;
    align-items: center;
    z-index: 5;
}
"@

$new = @"
/* ============================================================
   DEADLINE TILES (تنظیم شده برای عدم تداخل)
   ============================================================ */
.page-dashboard .card-in-progress {
    /* Ensure relative positioning context for deadline tiles */
    position: relative;
}

.page-dashboard .card-in-progress .deadline-inline-tiles {
    position: relative; /* Changed from absolute to relative flow */
    top: auto; left: auto;
    transform: none;
    display: flex;
    gap: 10px;
    align-items: center;
    justify-content: center;
    flex-wrap: wrap;
    margin-top: -28px; /* Slight negative margin to visually connect with icon */
    margin-bottom: 10px;
    z-index: 5;
    padding: 0 12px;
}
"@

if ($content.Contains($old)) {
    $content = $content.Replace($old, $new)
    Set-Content "static/css/pages/dashboard/index.css" -Value $content -Encoding UTF8
    Write-Host "Done!"
} else {
    Write-Host "Pattern not found!"
    $idx = $content.IndexOf("DEADLINE TILES")
    Write-Host $content.Substring($idx, 400)
}
