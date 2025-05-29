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
    public void testSubtract1() {
        int result = coreMath.add(5, -3);
        assertEquals(2, result, "5 - 3 should equal 2");
    }

    @Test
    public void testSubtract2() {
        int result = coreMath.subtract(5, 3);
        assertEquals(2, result, "5 - 3 should equal 2");
    }

    @Test
    public void testMultiply() {
        int result = coreMath.multiply(2, 3);
        assertEquals(6, result, "2 * 3 should equal 6");
    }

    @Test
    public void testDivide() {
        int result = coreMath.divide(6, 2);
        assertEquals(3, result, "6 / 2 should equal 3");
    }
}
