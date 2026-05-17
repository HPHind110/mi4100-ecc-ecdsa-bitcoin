# benchmark.ps1
# This script benchmarks RSA vs ECDSA using OpenSSL's built-in speed tool.

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

# 1. Benchmark RSA 2048
Write-Host "`nBenchmarking RSA 2048..."
" `n--- RSA 2048 Benchmark ---" | Out-File -FilePath $outputFile -Append -Encoding ascii
openssl speed rsa2048 | Out-File -FilePath $outputFile -Append -Encoding ascii

# 2. Benchmark RSA 3072
Write-Host "Benchmarking RSA 3072..."
" `n--- RSA 3072 Benchmark ---" | Out-File -FilePath $outputFile -Append -Encoding ascii
openssl speed rsa3072 | Out-File -FilePath $outputFile -Append -Encoding ascii

# 3. Benchmark ECDSA (secp256k1)
Write-Host "Benchmarking ECDSA (secp256k1)..."
" `n--- ECDSA secp256k1 Benchmark ---" | Out-File -FilePath $outputFile -Append -Encoding ascii

# Check if ecdsa speed test is available for secp256k1
# Some OpenSSL versions use 'ecdsa' as the algorithm name and then specify curves
# or just allow curve names directly.
openssl speed ecdsap256 | Out-File -FilePath $outputFile -Append -Encoding ascii
" `n--- Trying secp256k1 directly ---" | Out-File -FilePath $outputFile -Append -Encoding ascii
openssl speed ecdsa | Out-File -FilePath $outputFile -Append -Encoding ascii

Write-Host "`nBenchmark completed. Please check $outputFile for details."
