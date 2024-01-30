#
# Build stage
#
# adding full hash to meet probe requirements
FROM public.ecr.aws/docker/library/maven:3.8.7-amazoncorretto-11@sha256:fa0ca632f2dd44d5c63ed6186ded499abc5734daf3f6fd35e6ddfc0dfb0b8e01 AS build
# adding user to meet probe linting requirements
RUN yum install shadow-utils.x86_64 -y && yum clean all
RUN adduser -r -g root runuser
# maven build fails if the directory is not created upfront
RUN mkdir -p /home/runuser/app/target/classes && chown -R runuser:root /home/runuser && chmod -R 766 /home/runuser
USER runuser
COPY src /home/runuser/app/src
COPY pom.xml /home/runuser/app
RUN mvn -f /home/runuser/app/pom.xml clean package

#
# Package stage
#
# sha256 cannot be found at https://gallery.ecr.aws/amazoncorretto/amazoncorretto
FROM public.ecr.aws/amazoncorretto/amazoncorretto:11@sha256:41c0dd27f942266a952bf4c9fed0735876448a22b5cca6a298800a5607d7ff01
COPY --from=build /home/runuser/app/target/producer-0.0.1-SNAPSHOT.jar /usr/local/lib/dataprocessor-producer.jar
EXPOSE 8080
# adding health check instructions to meet probe requirements
HEALTHCHECK CMD ["curl", "--fail", "http://localhost:8080/healthcheck", "||", "exit 1"]

ENTRYPOINT ["java","-jar","/usr/local/lib/dataprocessor-producer.jar"]
