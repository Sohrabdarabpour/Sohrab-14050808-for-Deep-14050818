$content = [IO.File]::ReadAllText("static/css/pages/dashboard/index.css", [System.Text.Encoding]::UTF8)
$old = ".page-dashboard .card-in-progress .deadline-inline-tiles { 
        gap: 8px; 
        top: 0; /* تایل‌ها دقیقاً روی لبه بالایی */
    }"
$new = ".page-dashboard .card-in-progress .deadline-inline-tiles { 
        gap: 8px;
        margin-top: -24px;
        margin-bottom: 8px;
    }"
$content = $content.Replace($old, $new)
[IO.File]::WriteAllText("static/css/pages/dashboard/index.css", $content, [System.Text.Encoding]::UTF8)
Write-Host "Done!"
