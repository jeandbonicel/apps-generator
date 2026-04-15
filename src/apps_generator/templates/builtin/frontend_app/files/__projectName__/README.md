# {{ projectTitle or projectName }}

A React micro-frontend (Module Federation remote) built with Vite, TypeScript{% if features.tailwind %}, and Tailwind CSS{% endif %}.

This app can run **standalone** for development or be loaded as a remote module by the platform shell host.

## Getting Started

```bash
{{ packageManager }}{% if packageManager == "npm" %} install{% else %} install{% endif %}

{{ packageManager }}{% if packageManager == "npm" %} run dev{% else %} run dev{% endif %}
```

The dev server starts at [http://localhost:{{ devPort }}](http://localhost:{{ devPort }}).

## Module Federation

This app exposes `{{ exposedModule }}` as a remote entry. The host (platform shell) can load it via:

```
http://localhost:{{ devPort }}/assets/remoteEntry.js
```

## Build

```bash
{{ packageManager }}{% if packageManager == "npm" %} run build{% else %} run build{% endif %}
```

The production build outputs to `dist/`.
{% if features.docker %}

## Docker

```bash
docker build -f docker/Dockerfile -t {{ projectName }} .
docker run -p 8080:80 {{ projectName }}
```
{% endif %}
