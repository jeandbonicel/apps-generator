FROM eclipse-temurin:{{ javaVersion }}-jdk AS build
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends wget unzip && \
    wget -q https://services.gradle.org/distributions/gradle-8.8-bin.zip -O /tmp/gradle.zip && \
    unzip -q /tmp/gradle.zip -d /opt && \
    ln -s /opt/gradle-8.8/bin/gradle /usr/bin/gradle && \
    rm /tmp/gradle.zip && apt-get clean

COPY build.gradle.kts settings.gradle.kts gradle.properties ./
RUN gradle dependencies --no-daemon || true

COPY src/ src/
RUN gradle bootJar --no-daemon -x test

FROM eclipse-temurin:{{ javaVersion }}-jre
WORKDIR /app
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
COPY --from=build /app/build/libs/*.jar app.jar
RUN chown appuser:appgroup app.jar
USER appuser
EXPOSE {{ gatewayPort }}
HEALTHCHECK --interval=30s --timeout=3s --start-period=30s CMD curl -f http://localhost:{{ gatewayPort }}/actuator/health || exit 1
ENTRYPOINT ["java", "-jar", "app.jar"]
