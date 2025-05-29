package marco.demo.project;

import marco.demo.b.BasicMath;
import marco.demo.a.AdvancedMath;

public class Project {
    public static void main(String[] args) {
        BasicMath basic = new BasicMath();
        AdvancedMath advanced = new AdvancedMath();

        System.out.println("This is a demo project! Performing calculations...");
        System.out.println("Addition (2 + 3): " + basic.plus(2,3));
        System.out.println("Subtraction (5 - 3): " + basic.minus(5, 3));
        System.out.println("Multiplication (2 * 3): " + advanced.mult(2, 3));
        System.out.println("Division (6 / 2): " + advanced.div(6, 2));
    }
}

