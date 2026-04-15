# {{ projectName | title_case }}

{{ projectName | title_case }} - Spring Boot 3 backend with DDD architecture.

## Prerequisites

- Java {{ javaVersion }}
- Gradle 8+
{% if features.database %}
- PostgreSQL 16+
{% endif %}
{% if features.docker %}
- Docker & Docker Compose
{% endif %}

## Getting Started

### Local Development

```bash
# Start dependencies
{% if features.docker %}
docker compose -f docker/docker-compose.yaml up -d db
{% endif %}

# Run the application
./gradlew bootRun
```

The API will be available at `http://localhost:8080`.
{% if features.openapi %}

### API Documentation

Swagger UI is available at `http://localhost:8080/swagger-ui.html` when running locally.
{% endif %}

## Project Structure

```
src/main/java/{{ basePackage | package_to_path }}/
  domain/           # Domain layer (entities, value objects, repositories)
    model/          # Domain models and aggregates
    repository/     # Repository interfaces
    service/        # Domain services
  application/      # Application layer (use cases, commands, queries)
  infrastructure/   # Infrastructure layer
    config/         # Spring configuration
    persistence/    # JPA repositories and adapters
  interfaces/       # Interface layer
    rest/           # REST controllers
      dto/          # Data transfer objects
```

## Testing

```bash
./gradlew test
```
{% if features.docker %}

## Docker

```bash
# Build and run with Docker Compose
docker compose -f docker/docker-compose.yaml up --build
```
{% endif %}
{% if features.kubernetes %}

## Kubernetes Deployment

```bash
# Deploy to dev
kubectl apply -k k8s/overlays/dev/

# Deploy to prod
kubectl apply -k k8s/overlays/prod/
```
{% endif %}
