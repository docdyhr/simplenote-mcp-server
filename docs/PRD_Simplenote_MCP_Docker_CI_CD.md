
# 🐳 Simplenote MCP Server – CI/CD Docker Publishing PRD

## 🎯 Goal

Automate the build and publishing process for the `simplenote-mcp-server` Docker image to Docker Hub under the `docdyhr` organization using GitHub Actions. Every push to `main` or a semantic version tag (`vX.Y.Z`) should trigger this pipeline.

---

## 📦 Scope

- GitHub Actions workflow for CI/CD container publishing
- Dockerfile for containerization
- Secure authentication via GitHub secrets
- Tagged image releases (latest + versioned)

---

## 🧱 Features & Requirements

### CI/CD Pipeline

| Feature                        | Description                                           |
|-------------------------------|-------------------------------------------------------|
| Build image                   | On push to `main` or tag (e.g. `v1.0.0`)              |
| Push to Docker Hub            | Automatically tag and push image                     |
| Versioned Tags                | Use `:latest` and optional semver-based tags         |
| Secure Login                  | Uses GitHub Secrets for Docker Hub credentials       |

---

## 🔧 Implementation Details

### Dockerfile

Located in the root of the repository or under `/docker`. Based on Python 3.11 Slim. Exposes port `8000`.

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
CMD ["python", "server.py"]
```

### GitHub Actions Workflow

File: `.github/workflows/docker-publish.yml`

```yaml
name: Publish Docker Image

on:
  push:
    branches: [ main ]
    tags:
      - 'v*.*.*'

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout source
        uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v3
        with:
          username: ${{ secrets.DOCKER_USERNAME }}
          password: ${{ secrets.DOCKER_TOKEN }}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: |
            docdyhr/simplenote-mcp-server:latest
            docdyhr/simplenote-mcp-server:${{ github.ref_name }}
```

---

## 🔐 Secrets Required

| Secret Name     | Description                          |
|-----------------|--------------------------------------|
| `DOCKER_USERNAME` | Docker Hub username (`docdyhr`)     |
| `DOCKER_TOKEN`    | Docker Hub Access Token (RW access) |

To create the token:
- Go to [hub.docker.com → Security](https://hub.docker.com/settings/security)
- Generate a new **Access Token**
- Save the token in GitHub repo → Settings → Secrets → Actions

---

## ✅ Success Criteria

- [ ] Docker image builds correctly from latest source
- [ ] New tags (`v1.0.0`) trigger correct semantic image versions
- [ ] Images appear under [Docker Hub – docdyhr](https://hub.docker.com/repositories/docdyhr)
- [ ] GitHub Actions run reliably and complete without failure

---

## 🛠️ Future Enhancements

- Add multi-architecture builds (`linux/amd64`, `linux/arm64`)
- Add linting/test stage pre-publish
- Automatically update `README.md` with version tags
- Support notifications (e.g., Slack or email)

---
