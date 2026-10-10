
# Deployment Notes

This is one Git repository, not necessarily one deployed service.

- Deploy `apps/manager-web/` as a frontend.
- Run `services/backend/` as a FastAPI web service.
- Use persistent database storage; PostgreSQL is a good choice for a shared hosted deployment.
- Package `apps/vscode-extension/` as a VSIX.
- Run agents locally or as hosted workers depending on repository and test access needs.
- Configure CORS and environment-specific API URLs.
- Keep secrets in the hosting provider secret manager or environment settings.

