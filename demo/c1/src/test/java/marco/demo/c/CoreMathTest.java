package marco.demo.c;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class CoreMathTest {

    private final CoreMath coreMath = new CoreMath();

    @Test
    public void testAdd() {
        int result = coreMath.add(2, 3);
        assertEquals(5, result, "2 + 3 should equal 5");
    }

    @Test
    public void testSubtract() {
        int result = coreMath.subtract(5, 3);
        assertEquals(2, result, "5 - 3 should equal 2");
    }
}
