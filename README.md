# ambient-sound-analysis-api
REST API for batch processing HLS streams into WAV and Power Spectral Density (PSD) data for acoustic data visualization and AI training, based on the ambient-sound-analysis repo. Built during the 2025 Microsoft Hackathon.

Proposed subpackages:
- api/ (FastAPI routes + OpenAPI)
- workers/ (Lambda or container jobs for HLS→WAV/PSD)
- lib/ (shared transforms, ffmpeg wrappers, PSD, bandpass utils)
- cli/ (batch jobs for backfills)
- infra/ (Infrastructure as Code for Lambda / Elastic Container Registry (ECR), e.g., Terraform)
