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

extra["springCloudVersion"] = "{{ springCloudVersion }}"

dependencies {
    implementation("org.springframework.cloud:spring-cloud-starter-gateway")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
{% if features.oauth2 %}
    implementation("org.springframework.boot:spring-boot-starter-oauth2-resource-server")
{% endif %}
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}

dependencyManagement {
    imports {
        mavenBom("org.springframework.cloud:spring-cloud-dependencies:${property("springCloudVersion")}")
    }
}

tasks.withType<Test> {
    useJUnitPlatform()
}
