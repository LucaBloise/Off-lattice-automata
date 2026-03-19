public class SimulationConfig {
    public static final double L = 10.0;
    public static final double DENSITY = 4.0;
    public static final int N = (int) Math.round(DENSITY * L * L);
    public static final double V0 = 0.03;
    public static final double RADIUS = 1.0;
    public static final double DT = 1.0;

    private final double eta;
    private final int steps;
    private final long seed;

    public SimulationConfig(double eta, int steps, long seed) {
        if (eta < 0.0) {
            throw new IllegalArgumentException("eta must be >= 0");
        }
        if (steps < 0) {
            throw new IllegalArgumentException("steps must be >= 0");
        }
        this.eta = eta;
        this.steps = steps;
        this.seed = seed;
    }

    public double getEta() {
        return eta;
    }

    public int getSteps() {
        return steps;
    }

    public long getSeed() {
        return seed;
    }
}
