import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class VicsekSimulation {
    private final SimulationConfig config;
    private final List<Particle> particles;
    private final Random random;

    public VicsekSimulation(SimulationConfig config) {
        this.config = config;
        this.random = new Random(config.getSeed());
        this.particles = initializeParticles();
    }

    public List<Particle> getParticles() {
        return particles;
    }

    private List<Particle> initializeParticles() {
        List<Particle> initialParticles = new ArrayList<>(SimulationConfig.N);
        for (int i = 0; i < SimulationConfig.N; i++) {
            double x = random.nextDouble() * SimulationConfig.L;
            double y = random.nextDouble() * SimulationConfig.L;
            double theta = random.nextDouble() * 2.0 * Math.PI;
            initialParticles.add(new Particle(i, x, y, theta));
        }
        return initialParticles;
    }

    public void step() {
        int n = particles.size();
        double[] nextX = new double[n];
        double[] nextY = new double[n];
        double[] nextTheta = new double[n];

        for (int i = 0; i < n; i++) {
            Particle pi = particles.get(i);
            double avgTheta = computeLocalAverageAngle(pi);
            double noise = (random.nextDouble() - 0.5) * config.getEta();
            double theta = normalizeAngle(avgTheta + noise);

            double x = wrapPosition(pi.getX() + SimulationConfig.V0 * Math.cos(theta) * SimulationConfig.DT);
            double y = wrapPosition(pi.getY() + SimulationConfig.V0 * Math.sin(theta) * SimulationConfig.DT);

            nextTheta[i] = theta;
            nextX[i] = x;
            nextY[i] = y;
        }

        for (int i = 0; i < n; i++) {
            particles.get(i).setState(nextX[i], nextY[i], nextTheta[i]);
        }
    }

    private double computeLocalAverageAngle(Particle reference) {
        double sumSin = 0.0;
        double sumCos = 0.0;

        for (Particle other : particles) {
            if (isNeighbor(reference, other)) {
                double theta = other.getTheta();
                sumSin += Math.sin(theta);
                sumCos += Math.cos(theta);
            }
        }

        return Math.atan2(sumSin, sumCos);
    }

    private boolean isNeighbor(Particle a, Particle b) {
        double dx = minimumImageDelta(a.getX() - b.getX());
        double dy = minimumImageDelta(a.getY() - b.getY());
        double distanceSquared = dx * dx + dy * dy;
        return distanceSquared <= SimulationConfig.RADIUS * SimulationConfig.RADIUS;
    }

    private double minimumImageDelta(double delta) {
        double halfBox = SimulationConfig.L / 2.0;
        if (delta > halfBox) {
            return delta - SimulationConfig.L;
        }
        if (delta < -halfBox) {
            return delta + SimulationConfig.L;
        }
        return delta;
    }

    private double wrapPosition(double value) {
        double wrapped = value % SimulationConfig.L;
        if (wrapped < 0.0) {
            wrapped += SimulationConfig.L;
        }
        return wrapped;
    }

    private double normalizeAngle(double angle) {
        double twoPi = 2.0 * Math.PI;
        double normalized = angle % twoPi;
        if (normalized < 0.0) {
            normalized += twoPi;
        }
        return normalized;
    }
}
