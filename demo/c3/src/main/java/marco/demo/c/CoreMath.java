package marco.demo.c;

public class CoreMath {
    public int add(int a, int b) {
        return a + b;
    }

    public int subtract(int a, int b) {
        return add(a, multiply(-1, b));
    }

    public int multiply(int a, int b) {
        return a * b;
    }

    public int divide(int a, int b) {
        return a / b;
    }
}