plugins {
    java
    id("org.springframework.boot") version "{{ springBootVersion }}"
    id("io.spring.dependency-management") version "1.1.5"
}

group = "{{ groupId }}"
version = "0.0.1-SNAPSHOT"

java {
    toolchain {
        languageVersion = JavaLanguageVersion.of({{ javaVersion }})
    }
}

repositories {
    mavenCentral()
}

dependencies {
    // Spring Boot starters
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-validation")
{% if features.database %}
    // Database
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    runtimeOnly("org.postgresql:postgresql")
    implementation("org.liquibase:liquibase-core")
{% endif %}
{% if features.oauth2 %}
    // Security
    implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
{% endif %}
{% if features.openapi %}
    // OpenAPI / Swagger
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:2.5.0")
{% endif %}
    // Testing
    testImplementation("org.springframework.boot:spring-boot-starter-test")
{% if features.oauth2 %}
    testImplementation("org.springframework.security:spring-security-test")
{% endif %}
}

tasks.withType<Test> {
    useJUnitPlatform()
}
