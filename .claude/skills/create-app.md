---
name: create-app
description: Generate a complete multi-tenant app from a description. Orchestrates all appgen templates with sub-agent reasoning for schema design.
---

# Create App — Supervisor Workflow

You are a supervisor agent orchestrating the creation of a complete multi-tenant application using the `appgen` CLI. You have sub-agent roles: Architect, Backend Engineer, Frontend Engineer, and Infra Engineer.

## Input

The user provides a description of the app they want. Examples:
- "A dog grooming platform with dogs, appointments, and grooming services"
- "An e-commerce platform with products, orders, and customers"
- "A project management tool with projects, tasks, and team members"

## Step 1: Architect — Design the Schema

Analyze the user's description and design:

1. **App name** — kebab-case project name (e.g., `dog-grooming`)
2. **Resources** — each becomes a backend service + frontend MFE
3. **Fields per resource** — name, type, constraints
4. **Pages per MFE** — dashboard, list, form, or custom
5. **Auth provider** — clerk (default) or oidc

Present the design to the user for approval before proceeding. Format as:

```
App: dog-grooming
Auth: clerk

Resources:
  1. dog
     - name (string, required, maxLength: 100)
     - breed (string, maxLength: 50)
     - birthDate (date)
     - weightKg (decimal, min: 0)

  2. appointment
     - dogName (string, required)
     - service (string, required)
     - date (datetime, required)
     - notes (text)
     - status (string, required, maxLength: 30)

Pages:
  dog-tracker MFE:
    - dashboard (type: dashboard, resource: dog)
    - list (type: list, resource: dog)
    - new (type: form, resource: dog)

  appointments MFE:
    - list (type: list, resource: appointment)
    - new (type: form, resource: appointment)
```

Ask: "Does this look right? Any changes?"

## Step 2: Backend Engineer — Generate Backend

Once approved, set variables:

```bash
APP_NAME="<app-name>"
WORKSPACE="/tmp/$APP_NAME"
APPGEN="/Users/admin/Documents/Projects/apps-generator/.venv/bin/appgen"
```

Execute in order:

### 2a. Generate infrastructure

```bash
mkdir -p $WORKSPACE

# UI Kit
$APPGEN generate ui-kit -o $WORKSPACE/ui-kit \
  -s projectName=${APP_NAME}-ui --no-interactive --force

# API Client
$APPGEN generate api-client -o $WORKSPACE/api-client \
  -s projectName=${APP_NAME}-client --no-interactive --force

# API Gateway
$APPGEN generate api-gateway -o $WORKSPACE/gateway \
  -s projectName=${APP_NAME}-gateway \
  -s groupId=com.${APP_NAME//-/.} \
  -s basePackage=com.${APP_NAME//-/.}.gateway \
  -s features.oauth2=false \
  --no-interactive --force
```

### 2b. Generate backend services (one per resource group)

For each backend service:
```bash
$APPGEN generate api-domain -o $WORKSPACE/<service-name> \
  -s projectName=<service-name> \
  -s groupId=com.${APP_NAME//-/.} \
  -s basePackage=com.${APP_NAME//-/.}.<domain> \
  -s features.oauth2=false \
  -s 'resources=[<resource-json>]' \
  --gateway $WORKSPACE/gateway \
  --api-client $WORKSPACE/api-client \
  --no-interactive --force
```

### 2c. Generate platform shell

```bash
$APPGEN generate platform-shell -o $WORKSPACE/shell \
  -s projectName=${APP_NAME}-shell \
  -s projectTitle="<App Title>" \
  -s authProvider=clerk \
  -s clerkPublishableKey=pk_test_REPLACE_ME \
  --uikit $WORKSPACE/ui-kit \
  --api-client $WORKSPACE/api-client \
  --no-interactive --force
```

## Step 3: Frontend Engineer — Generate MFEs

For each MFE (with pages linked to resources):

```bash
$APPGEN generate frontend-app -o $WORKSPACE/<mfe-name> \
  -s projectName=<mfe-name> \
  -s projectTitle="<MFE Title>" \
  -s devPort=<port> \
  -s 'pages=[<pages-json>]' \
  --shell $WORKSPACE/shell \
  --uikit $WORKSPACE/ui-kit \
  --api-client $WORKSPACE/api-client \
  --no-interactive --force
```

Port assignment: first MFE gets 5001, second 5002, etc.

## Step 4: Infra Engineer — Build and Wire

### 4a. Build shared libraries

```bash
cd $WORKSPACE/api-client/<client-name> && npm install && npm run build
cd $WORKSPACE/ui-kit/<uikit-name> && npm install && npm run build
```

### 4b. Copy built libs to all consumers

```bash
for consumer in $WORKSPACE/shell/<shell-name> $WORKSPACE/<mfe-name>/<mfe-name> ...; do
  for lib in <client-name> <uikit-name>; do
    src="$WORKSPACE/$([ $lib = <client-name> ] && echo api-client || echo ui-kit)/$lib"
    dest="$consumer/local-deps/$lib"
    [ -d "$dest" ] && cp -r "$src/dist" "$dest/"
  done
done
```

### 4c. Generate docker-compose

```bash
$APPGEN docker-compose $WORKSPACE
```

### 4d. Build and start

```bash
cd $WORKSPACE && docker compose build
docker compose up -d
```

Wait for services to be healthy, then report the URLs to the user.

## Step 5: Report

Print a summary:

```
Your app is running at http://localhost

Services:
  - Shell: http://localhost (port 80)
  - Gateway: http://localhost:8080
  - <service-1>: http://localhost:8081
  - <service-2>: http://localhost:8082
  - PostgreSQL: localhost:5432

MFEs:
  - <mfe-1>: /mfe-1/dashboard, /mfe-1/list, /mfe-1/new
  - <mfe-2>: /mfe-2/list, /mfe-2/new

To create test data:
  curl -X POST http://localhost/api/<resource> \
    -H "Content-Type: application/json" \
    -H "X-Tenant-ID: test-tenant" \
    -d '{"name": "Test", ...}'
```

## Design Guidelines

When designing resources:

- **Naming**: resource names are singular (product, not products). kebab-case for multi-word (grooming-service).
- **Field types**: use `string` for short text, `text` for long text, `decimal` for money/weight, `integer` for counts, `boolean` for flags, `date`/`datetime` for temporal.
- **Required fields**: mark fields that must always be filled. Usually the "name" or primary identifier.
- **Constraints**: use `maxLength` on strings, `min`/`max` on numbers, `unique` on codes/SKUs.
- **One service per domain**: group related resources in one backend (e.g., dog + breed in one service, appointment + service in another).
- **Dashboard page**: always include for the primary resource. Auto-picks first numeric field for chart, first string field for grouping.
- **Port assignment**: MFE ports start at 5001 and increment.

## Error Handling

If any `appgen` command fails:
1. Show the error output
2. Diagnose the issue (missing param, invalid JSON, path not found)
3. Fix and retry

If Docker build fails:
1. Check build logs for compilation errors
2. Most common: missing dependencies, Jinja2 rendering issues
3. Fix the template or generated code and rebuild
