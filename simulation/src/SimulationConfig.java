public class SimulationConfig {
    public static final double L = 10.0;
    public static final double V0 = 0.03;
    public static final double RADIUS = 1.0;
    public static final double DT = 1.0;
    public static final int LEADER_ID = 0;
    public static final double CIRCULAR_LEADER_RADIUS = 5.0;
    public static final double CIRCULAR_LEADER_CENTER_X = L / 2.0;
    public static final double CIRCULAR_LEADER_CENTER_Y = L / 2.0;
    public static final double CIRCULAR_LEADER_OMEGA = V0 / CIRCULAR_LEADER_RADIUS;

    private final double density;
    private final int N;
    private final double eta;
    private final int steps;
    private final long seed;
    private final SimulationScenario scenario;

    public SimulationConfig(double eta, int steps, long seed, double density) {
        this(eta, steps, seed, density, SimulationScenario.STANDARD);
    }

    public SimulationConfig(double eta, int steps, long seed, double density, SimulationScenario scenario) {
        if (eta < 0.0) {
            throw new IllegalArgumentException("eta must be >= 0");
        }
        if (steps < 0) {
            throw new IllegalArgumentException("steps must be >= 0");
        }
        if (scenario == null) {
            throw new IllegalArgumentException("scenario cannot be null");
        }
        this.eta = eta;
        this.steps = steps;
        this.seed = seed;
        this.scenario = scenario;
        this.density = density;
        this.N = (int) Math.round(this.density * L * L);
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

    public double getDensity() { return density; }

    public int getN() { return N; }

    public SimulationScenario getScenario() {
        return scenario;
    }
}
