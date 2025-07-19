# Security Policy

## Overview
We take the security of the Simplenote MCP Server seriously. This document outlines our policy for reporting, triaging, and resolving security vulnerabilities. If you discover a potential issue, please follow the steps below to help us address it responsibly and efficiently.

---

## Supported Versions
We actively maintain the following major versions:
- **1.x** ─ Supported until 6 months after the release of 2.0
- **2.x (Future)** ─ Active development; latest patch releases will receive fixes

End-of-life (EOL) for a major version will be announced at least 30 days in advance in the CHANGELOG.md and via GitHub releases.

---

## Reporting a Vulnerability
1. **Email Security Team**  
   Send details to security@simplenote-mcp-server.org  
2. **Responsible Disclosure**  
   - Include as much information as possible: steps to reproduce, affected versions, logs, environment details.
   - Encrypt communications using our PGP key (see below).
3. **Acknowledgement**  
   We will respond within 5 business days to confirm receipt and provide an estimated timeline for remediation.

---

## PGP Key
```
-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: OpenPGP.js v4.10.10
Comment: https://openpgpjs.org

mQENBF...
...END PGP PUBLIC KEY BLOCK-----
```
Use this key to encrypt vulnerability reports.

---

## Coordinated Disclosure Process
1. **Initial Triage**  
   We verify the report and assess its severity (CVSS score).
2. **Fix and Review**  
   We develop a patch, write tests, and run security linters (Bandit, CodeQL).
3. **Disclosure**  
   - We will coordinate a disclosure timeline with the reporter.
   - Publish security advisory in GitHub Security Advisories and release notes.
4. **Public Release**  
   - Release patched version tagged and announced.
   - Notify downstream projects and package managers.

---

## Security Release Cadence
- **Critical**: Emergency patch within 48 hours.
- **High**: Patch within 14 days.
- **Medium/Low**: Included in next scheduled minor release.

---

## Security Contact
- **Email**: security@simplenote-mcp-server.org
- **PGP Fingerprint**: ABCD 1234 EF56 7890 ABCD EF01 2345 6789 0ABC DEF1

---

## Acknowledgments
We appreciate the community and security researchers who help keep the project secure. Your contributions are acknowledged in our SECURITY.md history and in GitHub Security Advisories.

Thank you for helping us maintain a secure ecosystem!
