package marco.demo.a;

import marco.demo.c.CoreMath;

public class AdvancedMath {
    private final CoreMath core = new CoreMath();

    public int mult(int a, int b) {
        return core.multiply(a, b);
    }

    public int div(int a, int b) {
        return core.divide(a, b);
    }
}