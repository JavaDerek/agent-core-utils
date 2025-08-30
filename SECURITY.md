# Security Policy

## Supported Versions

We support security fixes on the latest minor release of the `main` branch.

## Reporting a Vulnerability

If you discover a security issue, please do not open a public issue. Instead, email:

- derekmferguson@yahoo.co.uk

Please include:
- A description of the issue and potential impact
- Steps to reproduce (proof of concept if available)
- Affected version/commit hash

We will acknowledge receipt within 72 hours and work with you on a coordinated disclosure.

## Handling Secrets

This repository does not include hardcoded credentials. Use environment variables or CI secrets for any keys. Do not commit secrets to the repo.

## CI Secret Scanning

GitHub Actions runs automated secret scanning via Gitleaks on every push and PR. Any detected leak will fail the workflow.
