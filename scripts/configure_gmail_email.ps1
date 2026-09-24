param(
    [string]$SenderEmail = "",
    [string]$PublicSiteUrl = "http://localhost:8000"
)

if ([string]::IsNullOrWhiteSpace($SenderEmail)) {
    $SenderEmail = Read-Host "Gmail sender address"
}

$secureAppPassword = Read-Host "Gmail app password" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR(
    $secureAppPassword
)

try {
    $appPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
        $passwordPointer
    )
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
}

if (
    [string]::IsNullOrWhiteSpace($SenderEmail) -or
    [string]::IsNullOrWhiteSpace($appPassword)
) {
    throw "Sender email and Gmail app password are required."
}

[Environment]::SetEnvironmentVariable("EMAIL_HOST", "smtp.gmail.com", "User")
[Environment]::SetEnvironmentVariable("EMAIL_PORT", "587", "User")
[Environment]::SetEnvironmentVariable("EMAIL_HOST_USER", $SenderEmail, "User")
[Environment]::SetEnvironmentVariable("EMAIL_HOST_PASSWORD", $appPassword, "User")
[Environment]::SetEnvironmentVariable("EMAIL_USE_TLS", "true", "User")
[Environment]::SetEnvironmentVariable(
    "DEFAULT_FROM_EMAIL",
    "Savorly <$SenderEmail>",
    "User"
)
[Environment]::SetEnvironmentVariable(
    "PUBLIC_SITE_URL",
    $PublicSiteUrl,
    "User"
)

Write-Host "Gmail SMTP settings saved for the current Windows user."
Write-Host "Restart the terminal, IDE, and Django server before testing."
