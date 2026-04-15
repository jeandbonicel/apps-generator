package {{ basePackage }};

import org.junit.jupiter.api.Test;
import org.springframework.boot.test.context.SpringBootTest;

@SpringBootTest
class {{ projectName | pascal_case }}ApplicationTests {
    @Test
    void contextLoads() {
    }
}
