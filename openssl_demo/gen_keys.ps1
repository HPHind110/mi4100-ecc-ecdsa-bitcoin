# gen_keys.ps1
# This script generates a secp256k1 keypair using OpenSSL.

Write-Host "--- Checking OpenSSL Version ---"
openssl version

Write-Host "`n--- Generating secp256k1 Private Key (ecc_priv.pem) ---"
# Generate private key for secp256k1 curve
openssl ecparam -name secp256k1 -genkey -noout -out ecc_priv.pem

Write-Host "--- Extracting Public Key (ecc_pub.pem) ---"
# Extract public key from the private key
openssl ec -in ecc_priv.pem -pubout -out ecc_pub.pem

if ((Test-Path ecc_priv.pem) -and (Test-Path ecc_pub.pem)) {
    Write-Host "`nSUCCESS: Keys generated successfully."
    Write-Host "Private Key: ecc_priv.pem"
    Write-Host "Public Key:  ecc_pub.pem"
} else {
    Write-Host "`nFAILURE: Key generation failed."
}
