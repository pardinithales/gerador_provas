# Script para configurar o arquivo .env.local
$content = @"
# Configurações SMTP
SMTP_HOSTNAME=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=gerador_prova
SMTP_PASSWORD=hpai zfmo jnmb pqrz
SMTP_FROM_EMAIL=drthalesneuro@gmail.com
ADMIN_EMAIL=drthalesneuro@gmail.com

# Para Gmail, use uma senha de aplicativo gerada em:
# https://myaccount.google.com/apppasswords
# Não use sua senha normal do Google!
"@

# Certifica-se de usar UTF-8 sem BOM
$Utf8NoBomEncoding = New-Object System.Text.UTF8Encoding $False
[System.IO.File]::WriteAllLines((Resolve-Path ".env.local"), $content, $Utf8NoBomEncoding)

Write-Host "Arquivo .env.local configurado com sucesso!" 