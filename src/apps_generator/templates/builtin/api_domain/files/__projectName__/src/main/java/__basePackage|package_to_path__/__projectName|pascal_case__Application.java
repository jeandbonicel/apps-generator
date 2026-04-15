package {{ basePackage }};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class {{ projectName | pascal_case }}Application {

    public static void main(String[] args) {
        SpringApplication.run({{ projectName | pascal_case }}Application.class, args);
    }
}
