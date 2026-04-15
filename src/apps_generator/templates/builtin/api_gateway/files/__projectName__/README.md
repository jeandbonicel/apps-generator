# {{ projectTitle or projectName }}

API Gateway (BFF) built with Spring Cloud Gateway.

## Running locally

```bash
./gradlew bootRun
```

Gateway runs on port {{ gatewayPort }}.

## Routes

Routes are defined in `src/main/resources/routes.yaml`. New routes are added automatically when generating backend services with `--gateway`:

```bash
appgen generate api-domain -o ./order-service --gateway .
```

## Endpoints

- Gateway: `http://localhost:{{ gatewayPort }}`
- Health: `http://localhost:{{ gatewayPort }}/actuator/health`
- Routes: `http://localhost:{{ gatewayPort }}/actuator/gateway/routes`
