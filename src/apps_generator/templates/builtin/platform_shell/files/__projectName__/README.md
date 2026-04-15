# {{ projectTitle or projectName }}

Platform shell application with Module Federation, OAuth2/OIDC authentication, and multi-tenant organization switching.

## Development

```bash
{{ packageManager }}{% if packageManager == "npm" %} run{% endif %} dev
```

## Build

```bash
{{ packageManager }}{% if packageManager == "npm" %} run{% endif %} build
```

## Configuration

| Variable | Description |
|---|---|
| OIDC Authority | `{{ oidcAuthority }}` |
| OIDC Client ID | `{{ oidcClientId }}` |
| API Base URL | `{{ apiBaseUrl }}` |
| Tenants Endpoint | `{{ tenantsEndpoint }}` |

## Docker

```bash
docker build -f docker/Dockerfile -t {{ projectName }} .
docker run -p 8080:80 {{ projectName }}
```
