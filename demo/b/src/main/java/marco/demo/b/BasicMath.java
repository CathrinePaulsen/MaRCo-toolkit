package marco.demo.b;

import marco.demo.c.CoreMath;

public class BasicMath {
    private final CoreMath core = new CoreMath();

    public int plus(int a, int b) {
        return core.add(a, b);
    }

    public int minus(int a, int b) {
        return core.subtract(a, b);
    }
}