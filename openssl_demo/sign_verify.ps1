# sign_verify.ps1
# This script demonstrates signing and verification using OpenSSL.

$messageFile = "message.txt"
$tamperedFile = "message_tampered.txt"
$signatureFile = "sig.bin"
$privKey = "ecc_priv.pem"
$pubKey = "ecc_pub.pem"

# 1. Create message if not exists
Write-Host "--- Creating Message ---"
"Alice pays Bob 1 BTC" | Out-File -FilePath $messageFile -Encoding ascii -NoNewline
Write-Host "Message: $(Get-Content $messageFile)"

# 2. Sign the message
Write-Host "`n--- Signing Message with SHA-256 ---"
openssl dgst -sha256 -sign $privKey -out $signatureFile $messageFile

if (Test-Path $signatureFile) {
    Write-Host "Signature created: $signatureFile"
}

# 3. Verify the signature
Write-Host "`n--- Verifying Signature ---"
openssl dgst -sha256 -verify $pubKey -signature $signatureFile $messageFile

# 4. Tamper with message and verify again
Write-Host "`n--- Tampering with Message ---"
"Alice pays Eve 100 BTC" | Out-File -FilePath $tamperedFile -Encoding ascii -NoNewline
Write-Host "Tampered Message: $(Get-Content $tamperedFile)"

Write-Host "`n--- Verifying Signature against Tampered Message (Expected to FAIL) ---"
openssl dgst -sha256 -verify $pubKey -signature $signatureFile $tamperedFile

Write-Host "`nDemo completed."
