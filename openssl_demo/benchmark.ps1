# benchmark.ps1
# This script benchmarks RSA and ECDSA variants using OpenSSL speed.
# Educational note:
# - `openssl speed ecdsap256` benchmarks NIST P-256 / prime256v1, NOT secp256k1.
# - Direct secp256k1 benchmarking via `openssl speed` is not consistently available
#   across OpenSSL versions/builds, so this script does not claim a secp256k1 speed benchmark.
# - The separate secp256k1 demo lives in gen_keys.ps1 and sign_verify.ps1.

$outputDir = "..\results"
if (!(Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir
}

$outputFile = "$outputDir\openssl_benchmark.txt"

Write-Host "--- Starting OpenSSL Benchmark ---"
Write-Host "Results will be saved to: $outputFile"

# Clear or create the file
"--- OpenSSL Benchmark Results ---" | Out-File -FilePath $outputFile -Encoding ascii
"Date: $(Get-Date)" | Out-File -FilePath $outputFile -Append -Encoding ascii
"OpenSSL Version: $(openssl version)" | Out-File -FilePath $outputFile -Append -Encoding ascii
"Notes:" | Out-File -FilePath $outputFile -Append -Encoding ascii
"- ecdsap256 = ECDSA on NIST P-256 / prime256v1, not secp256k1." | Out-File -FilePath $outputFile -Append -Encoding ascii
"- Direct secp256k1 speed benchmarking may be unavailable in OpenSSL speed, depending on build/version." | Out-File -FilePath $outputFile -Append -Encoding ascii
"- secp256k1 sign/verify demo is handled separately by gen_keys/sign_verify scripts." | Out-File -FilePath $outputFile -Append -Encoding ascii
"- Benchmark results depend on operation type, key size, curve, implementation, and machine." | Out-File -FilePath $outputFile -Append -Encoding ascii

# 1. Benchmark RSA 2048
Write-Host "`nBenchmarking RSA 2048..."
" `n--- RSA 2048 Benchmark ---" | Out-File -FilePath $outputFile -Append -Encoding ascii
openssl speed rsa2048 | Out-File -FilePath $outputFile -Append -Encoding ascii

# 2. Benchmark RSA 3072
Write-Host "Benchmarking RSA 3072..."
" `n--- RSA 3072 Benchmark ---" | Out-File -FilePath $outputFile -Append -Encoding ascii
openssl speed rsa3072 | Out-File -FilePath $outputFile -Append -Encoding ascii

# 3. Benchmark ECDSA P-256 (nistp256 / prime256v1)
Write-Host "Benchmarking ECDSA (NIST P-256 / prime256v1 via ecdsap256)..."
" `n--- ECDSA P-256 (nistp256 / prime256v1) Benchmark ---" | Out-File -FilePath $outputFile -Append -Encoding ascii
openssl speed ecdsap256 | Out-File -FilePath $outputFile -Append -Encoding ascii

# 4. Generic ECDSA speed lines (depends on OpenSSL build/version)
Write-Host "Benchmarking generic ECDSA output reported by OpenSSL speed..."
" `n--- Generic ECDSA speed output (OpenSSL-dependent; curve coverage may vary) ---" | Out-File -FilePath $outputFile -Append -Encoding ascii
openssl speed ecdsa | Out-File -FilePath $outputFile -Append -Encoding ascii
" `n--- Caveat ---" | Out-File -FilePath $outputFile -Append -Encoding ascii
"If OpenSSL speed does not list secp256k1 explicitly, do not interpret these numbers as a direct secp256k1 benchmark." | Out-File -FilePath $outputFile -Append -Encoding ascii

Write-Host "`nBenchmark completed. Please check $outputFile for details."
