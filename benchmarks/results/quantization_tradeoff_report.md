# FinTrace VLM & Retrieval Quantization Trade-off Report (4-bit vs 8-bit)

**Date:** 2026-11-22T11:37:33Z  
**Target Architecture:** Apple Silicon M-Series Metal (Unified Memory Architecture)  
**Default Policy:** `[RECOMMENDED: 4-BIT INT4]`

## 1. Executive Summary

Adopt 4-bit (int4) quantization as standard default across local Apple Silicon deployments: delivers 43.2% lower unified memory footprint, 52.1% higher throughput, while maintaining 99.1% numeric financial precision within a 0.0095 IoU tolerance.

## 2. Comparative Evaluation Matrix

| Model Family | Quantization | Precision | Weight Size | Peak Memory | 6GB Ceiling Gate | Throughput | Mean IoU | Numeric Precision |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| VLM | `4bit` | int4 | 4.5 GB | 5.35 GB | `[PASS]` | 18.4 t/s | 0.9220 | 99.12% |
| VLM | `8bit` | int8 | 8.2 GB | 9.42 GB | `[FAIL - EXCEEDS]` | 12.1 t/s | 0.9315 | 99.84% |
| RETRIEVAL | `4bit` | int4 | 2.2 GB | 2.85 GB | `[PASS]` | 45.2 t/s | 0.9150 | 98.90% |
| RETRIEVAL | `8bit` | int8 | 3.8 GB | 4.65 GB | `[PASS]` | 32.8 t/s | 0.9280 | 99.50% |

## 3. Detailed Trade-off Analysis

### A. Memory Footprint vs Throughput Dynamics
- **Unified Memory Reduction:** 4-bit saves **43.2%** of peak RAM (5.35 GB vs 9.42 GB).
- **Generation Speedup:** 4-bit delivers **52.1%** faster throughput (18.4 vs 12.1 tokens/sec).
- **Time to First Token (TTFT):** 4-bit responds in **315 ms** vs **485 ms** for 8-bit (-35% latency).

### B. Financial Accuracy & Precision Impact
- **Bounding Box IoU Delta:** 8-bit provides a modest **+0.0095** IoU improvement on high-density financial tables.
- **Numeric Balance Extraction:** 4-bit delivers **99.12%** accuracy on 10-12 digit VND balances; 8-bit achieves **99.84%** (+0.72% difference).
- **Audit Grounding:** Both 4-bit and 8-bit maintain 100% Top-3 retrieval recall across all evaluated BCTC filings.

## 4. Hardware Sizing & Deployment Guidelines

| Apple Silicon Configuration | Recommended Quantization | Rationale |
| :--- | :--- | :--- |
| **16GB Unified Memory (Base M2/M3/M4)** | `4-bit (int4)` | **Mandatory.** 8-bit causes OS memory pressure and swap thrashing. |
| **24GB / 32GB Unified Memory (M-Pro)** | `4-bit (Default)` / `8-bit (High Precision)` | Standard auditing defaults to 4-bit for speed; 8-bit for deep-dive forensic audits. |
| **64GB+ Unified Memory (M-Max / Ultra)** | `8-bit (int8)` | Ample unified memory headroom allows maximum precision without penalty. |
