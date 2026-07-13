# Security Policy

## 🔒 Security Statement

The Simplenote MCP Server project takes security seriously. We are committed to providing a secure platform for note management and maintaining the confidentiality, integrity, and availability of user data.

## 🚨 Reporting Security Vulnerabilities

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report security issues responsibly:

### Primary Contact
- **Email**: docdyhr@me.com
- **Subject**: [SECURITY] Simplenote MCP Server - Vulnerability Report
- **Response Time**: We aim to acknowledge reports within 24 hours

### What to Include
Please include the following information in your report:
- Description of the vulnerability
- Steps to reproduce the issue
- Potential impact assessment
- Suggested mitigation (if known)
- Your contact information for follow-up

### Security Team Response
1. **Acknowledgment** - Within 24 hours
2. **Initial Assessment** - Within 48 hours
3. **Detailed Analysis** - Within 5 business days
4. **Resolution Plan** - Within 10 business days
5. **Security Update** - As soon as safely possible

## 🛡️ Supported Versions

Only the latest released version is actively maintained. This is a solo-maintained open-source project — security fixes land on `main` and are released promptly, but there is no formal backport program for older minor versions.

| Version | Supported          |
| ------- | ------------------ |
| 1.17.x  | ✅ Yes             |
| < 1.17  | ❌ No — please upgrade |

## 📊 Security Monitoring

For detailed information about our automated security monitoring and maintenance procedures, see [Security Monitoring Guide](docs/SECURITY_MONITORING.md).

**Key Features**:
- Automated dependency scanning with Dependabot
- CVE scanning with pip-audit in CI/CD
- Static analysis with Bandit and CodeQL
- Weekly security scans
- 24-hour response time for critical issues

## 🔐 Security Features

### Input Validation & Sanitization
- **Comprehensive Input Validation**: All MCP tool inputs are validated using our security validation system
- **XSS Prevention**: Input sanitization prevents cross-site scripting attacks
- **SQL Injection Prevention**: Parameterized queries and input validation prevent SQL injection
- **Path Traversal Protection**: File path validation prevents directory traversal attacks
- **Command Injection Prevention**: Input filtering blocks command injection attempts

### Rate Limiting & DoS Protection
- **Request Rate Limiting**: 60 requests/minute (burst) and 100 requests per 5-minute window (sustained), enforced per client — source IP for HTTP-transport callers, a fixed identifier for stdio (one local process is genuinely one client there). Both limits share one identity resolution mechanism (`server.py::_resolve_client_id`) so they can't be bypassed independently.
- **Progressive Penalties**: Automatic blocking for repeated violations (1min → 5min → 15min → 1hour, scaling with violation count)
- **Sliding-Window Enforcement**: rolling time-window counters per client identity
- **Write Budget**: mutating tool calls (create/update/delete) are additionally capped per client per rolling window (`SIMPLENOTE_WRITE_BUDGET`, default 20/60s), independent of the general request rate limit, to bound the blast radius of a runaway automated loop
- **Resource Limits**: Memory and processing time limits prevent resource exhaustion

### Authentication & Authorization
- **MCP HTTP transport**: `MCP_TRANSPORT=http` refuses to start on a non-loopback `MCP_HTTP_HOST` unless `MCP_HTTP_AUTH_TOKEN` (a bearer token, checked via constant-time comparison) is configured. Loopback binds remain token-free, matching stdio's local-process trust model. `MCP_HTTP_ALLOWED_HOSTS`/`MCP_HTTP_ALLOWED_ORIGINS` enable DNS-rebinding protection for non-loopback binds. Intended for private-network use (behind a VPN/Tailscale/SSH tunnel) — a static shared token has none of OAuth's revocation/audit/expiry properties, so avoid exposing it directly to the public internet even with a token configured.
- **Credential Protection**: Secure handling of Simplenote credentials (see Data Protection below for the local token cache)

### Data Protection
- **Sensitive Data Redaction**: `password`/`token`/`secret`/`key` fields are redacted before logging or inclusion in tool-call error output (`security.py`, `middleware.py`). Tool call arguments (note content, search queries) are never logged in full at INFO — only the tool name and argument count; a redacted/truncated form is available at DEBUG for troubleshooting.
- **Secure Transmission**: HTTPS/TLS for all external communications (handled by the underlying `requests`/`urllib3`/`simplenote` client stack)
- **Log Security**: Security events are logged with credential values redacted; log files themselves currently have no special filesystem permissions (tracked for hardening)
- **No encryption at rest from Simplenote itself**: **Simplenote does not encrypt notes at rest on its own servers** — this is a limitation of the underlying service, not this project, and Automattic's own documentation recommends against storing highly sensitive information in Simplenote. Notes are NOT encrypted by default; only notes you explicitly opt into Vault (below) are protected.
- **Vault — opt-in client-side note encryption (shipped)**: `create_note`/`update_note` accept `encrypt=true`, and `encrypt_note`/`decrypt_note` convert existing notes. Encrypted notes are AES-256-GCM ciphertext (via the `cryptography` library) from the moment they leave this server — Simplenote's API, Automattic's infrastructure, and anyone opening the note in the native Simplenote app only ever see the encrypted envelope, never plaintext. Full design, threat model, and explicit limitations: `docs/security/encryption-design.md`.
  - **What Vault protects**: note body content, both in transit to Simplenote and at rest on Simplenote's servers.
  - **What Vault does NOT protect**: the note's title (first line — kept readable so `get_or_create_note`/browsing still work), tags, creation/modification timestamps, or the fact that a note exists at all. It also does not protect against a compromised local machine — the server process itself, and anyone with access to it, can read decrypted content and hold the encryption key.
  - **Key storage**: the Vault master key lives in the OS keychain (via the `keyring` library) or, for headless/container deployments, a file referenced by `SIMPLENOTE_VAULT_KEY_FILE` (`chmod 0600`). It is fetched once per process and cached in memory only — never written to disk in plaintext, never synced to Simplenote. There is no multi-device key sync in the current version: encrypted notes are only decryptable on a machine holding the matching key.
  - **Fail-closed key handling**: a key file/keychain entry that exists but is unreadable, malformed, or the wrong length is never silently replaced with a freshly generated key — doing so would permanently orphan any notes already encrypted with the original. `vault_status` reports the corruption explicitly so it can be resolved deliberately.
- **Local credential cache**: the Simperium auth token is cached locally at `~/.config/simplenote-mcp/<email>.token`, protected by `chmod 0600` (owner-only). This is a plaintext file, not OS-keychain-backed or encrypted — treat the same as any other locally-cached session token. (This is a different, lower-stakes secret than the Vault master key above — it's a rotatable session token, not the key that data confidentiality depends on.)

### Supply Chain Security
- **Dependency Pinning**: Exact version pinning with SHA256 checksums
- **Vulnerability Scanning**: Automated scanning using OSV and Safety databases
- **SBOM Generation**: Software Bill of Materials for transparency
- **License Compliance**: Automated license compliance checking

## 📋 Security Architecture

### Security Layers
1. **Network Layer**: TLS encryption, secure protocols
2. **Application Layer**: Input validation, rate limiting, authentication
3. **Data Layer**: Secure data handling in transit; Simplenote itself stores notes unencrypted at rest — opt-in client-side encryption (Vault) closes this gap for notes you explicitly mark, see Data Protection above and `docs/security/encryption-design.md`
4. **Monitoring Layer**: Security event logging, anomaly detection

### Security Controls
- **Preventive**: Input validation, authentication, authorization
- **Detective**: Security monitoring, anomaly detection, audit logging
- **Corrective**: Incident response, automatic blocking, rate limiting
- **Recovery**: Backup procedures, disaster recovery planning

## 🔍 Security Testing

### Automated Security Testing
- **Static Analysis**: Bandit security linting on every commit
- **Dependency Scanning**: Automated vulnerability scanning in CI/CD
- **Code Quality**: Comprehensive test coverage with security test cases
- **Container Scanning**: Docker image vulnerability scanning

### Manual Security Testing
- **Code Review**: Security-focused review on every PR touching credential handling, validation, or (once shipped) the Vault encryption module
- **Threat Modeling**: Revisited when the trust boundary changes materially (e.g. the Vault feature — see [ROADMAP.md](ROADMAP.md) and `docs/security/encryption-design.md`)
- This is a solo-maintained open-source project — there is no scheduled third-party audit or penetration-testing program. Responsible disclosures are welcome (see Reporting above) and are the primary source of external security review.

## 📊 Security Monitoring

### Real-Time Monitoring
- **Security Events**: Failed authentication attempts, rate limit violations
- **Anomaly Detection**: Unusual usage patterns, suspicious requests
- **Performance Monitoring**: Resource usage, response time tracking
- **Error Tracking**: Security-related errors and exceptions

### Security Metrics
- **Authentication Failures**: Failed login attempts per hour/day
- **Rate Limit Violations**: Number of clients hitting rate limits
- **Input Validation Failures**: Blocked malicious inputs
- **Vulnerability Exposure**: Open security issues and resolution time

## 🚨 Incident Response

### Incident Classification
- **Critical**: Data breach, system compromise, service unavailability
- **High**: Privilege escalation, authentication bypass
- **Medium**: Information disclosure, denial of service
- **Low**: Security configuration issues, minor vulnerabilities

### Response Timeline
- **Critical**: Immediate response (within 1 hour)
- **High**: Within 4 hours
- **Medium**: Within 24 hours  
- **Low**: Within 72 hours

### Response Process
1. **Detection**: Automated alerts or manual reporting
2. **Assessment**: Severity evaluation and impact analysis
3. **Containment**: Immediate steps to limit damage
4. **Investigation**: Root cause analysis and evidence collection
5. **Resolution**: Implement fixes and verify effectiveness
6. **Communication**: Notify affected users and stakeholders
7. **Documentation**: Post-incident review and lessons learned

## 🔧 Security Configuration

### Environment Variables
```bash
# Credentials
SIMPLENOTE_EMAIL=your-email@example.com
SIMPLENOTE_PASSWORD=your-secure-password
SIMPLENOTE_OFFLINE_MODE=false

# MCP HTTP transport (only relevant if MCP_TRANSPORT=http)
MCP_TRANSPORT=stdio  # or "http"
MCP_HTTP_HOST=127.0.0.1
MCP_HTTP_AUTH_TOKEN=  # required if MCP_HTTP_HOST is non-loopback
MCP_HTTP_ALLOWED_HOSTS=  # comma-separated, enables DNS-rebinding protection
MCP_HTTP_ALLOWED_ORIGINS=  # comma-separated

# Rate limiting / write budget
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=900
RATE_LIMIT_BURST=20
SIMPLENOTE_WRITE_BUDGET=20
SIMPLENOTE_WRITE_BUDGET_WINDOW=60

# Logging
LOG_LEVEL=INFO
```

### Docker Security
```bash
# Run with non-root user
docker run --user mcp:mcp \
  --read-only \
  --tmpfs /tmp \
  --cap-drop ALL \
  --security-opt no-new-privileges \
  simplenote-mcp-server
```

## 📚 Security Best Practices

### For Users
- **Strong Credentials**: Use strong, unique passwords for Simplenote
- **Environment Security**: Secure your environment variables and configuration files
- **Regular Updates**: Keep the MCP server updated to the latest version
- **Network Security**: Use TLS/HTTPS for all communications
- **Monitoring**: Monitor logs for suspicious activity

### For Developers
- **Secure Coding**: Follow secure coding practices and guidelines
- **Input Validation**: Validate and sanitize all inputs
- **Error Handling**: Handle errors securely without information disclosure
- **Dependency Management**: Keep dependencies updated and scan for vulnerabilities
- **Testing**: Include security test cases in all code changes

### For Operators
- **Infrastructure Security**: Secure the deployment environment
- **Access Controls**: Implement proper access controls and monitoring
- **Backup Security**: Secure backups and test recovery procedures
- **Incident Preparedness**: Have incident response procedures ready
- **Regular Audits**: Conduct regular security audits and assessments

## 🔗 Security Resources

### External Resources
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [CWE Top 25](https://cwe.mitre.org/top25/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)
- [Python Security Guidelines](https://python-security.readthedocs.io/)

### Security Tools
- [Bandit](https://bandit.readthedocs.io/) - Python security linter
- [Safety](https://pyup.io/safety/) - Dependency vulnerability scanner
- [OSVIG](https://osv.dev/) - Open source vulnerability database
- [CodeQL](https://codeql.github.com/) - Semantic code analysis

## 📅 Security Review Schedule

### Regular Reviews
- **Every push/PR**: Bandit static analysis + pip-audit CVE scan (`unified-ci.yml`)
- **Weekly**: Scheduled Bandit/dependency security scan (`security.yml`, Monday 03:00 UTC) + Dependabot dependency updates
- **Ad hoc**: Security-impact review for releases that touch credential handling, validation, or the Vault encryption module

### Version-Based Reviews
- **Minor/Major Releases**: Security-relevant changes called out in [CHANGELOG.md](CHANGELOG.md)
- **Patch Releases**: Security-focused testing for critical fixes

## 🏅 Security Acknowledgments

We acknowledge and thank the following individuals and organizations for their contributions to the security of the Simplenote MCP Server:

- Security researchers who responsibly disclose vulnerabilities
- Open source security tools and communities
- The Python security community
- The MCP (Model Context Protocol) security working group

## 📖 Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full, version-by-version history — it is kept current on every release and is the authoritative record. Security-relevant highlights:

- **Unreleased**: Vault — opt-in client-side note encryption (AES-256-GCM), closing the encryption-at-rest gap described above. New tools `encrypt_note`, `decrypt_note`, `vault_status`; `encrypt=true` on `create_note`/`update_note`. `cryptography` and `keyring` promoted to direct dependencies.
- **v1.17.1**: macOS keychain auth hardening (three-step Simperium token resolution), clean `AuthenticationError` instead of leaking raw `TypeError`, log-monitor false-positive-alert fix
- **v1.16.0**: Memory leak in `SecurityValidator.failed_validation_attempts` patched (unbounded growth under sustained load); CodeQL findings resolved
- **v1.12.1**: Memory leak in security event tracking capped; test isolation hardening for auth/security singletons

---

**Last Updated**: 2026-07-13
**Version**: 1.17.1

For questions about this security policy, please contact: docdyhr@me.com
