import java.util.ArrayList;
import java.util.List;
import java.util.Random;

public class VicsekSimulation {
    private final SimulationConfig config;
    private final List<Particle> particles;
    private final Random random;
    private final int leaderId;

    private Double leaderFixedTheta;
    private Double leaderCircularPhase;

    public VicsekSimulation(SimulationConfig config) {
        this.config = config;
        this.random = new Random(config.getSeed());
        this.particles = initializeParticles();
        this.leaderId = config.getScenario().hasLeader() ? SimulationConfig.LEADER_ID : -1;

        initializeLeaderIfNeeded();
    }

    public List<Particle> getParticles() {
        return particles;
    }

    public int getLeaderId() {
        return leaderId;
    }

    public Double getLeaderFixedTheta() {
        return leaderFixedTheta;
    }

    public Double getLeaderCircularCenterX() {
        return config.getScenario() == SimulationScenario.CIRCULAR_LEADER ? SimulationConfig.CIRCULAR_LEADER_CENTER_X : null;
    }

    public Double getLeaderCircularCenterY() {
        return config.getScenario() == SimulationScenario.CIRCULAR_LEADER ? SimulationConfig.CIRCULAR_LEADER_CENTER_Y : null;
    }

    public Double getLeaderCircularRadius() {
        return config.getScenario() == SimulationScenario.CIRCULAR_LEADER ? SimulationConfig.CIRCULAR_LEADER_RADIUS : null;
    }

    public Double getLeaderCircularOmega() {
        return config.getScenario() == SimulationScenario.CIRCULAR_LEADER ? SimulationConfig.CIRCULAR_LEADER_OMEGA : null;
    }

    private void initializeLeaderIfNeeded() {
        if (!config.getScenario().hasLeader()) {
            return;
        }

        Particle leader = particles.get(leaderId);
        if (config.getScenario() == SimulationScenario.FIXED_LEADER) {
            leaderFixedTheta = random.nextDouble() * 2.0 * Math.PI;
            leader.setState(leader.getX(), leader.getY(), leaderFixedTheta);
            return;
        }

        if (config.getScenario() == SimulationScenario.CIRCULAR_LEADER) {
            leaderCircularPhase = random.nextDouble() * 2.0 * Math.PI;
            double x = wrapPosition(
                    SimulationConfig.CIRCULAR_LEADER_CENTER_X
                            + SimulationConfig.CIRCULAR_LEADER_RADIUS * Math.cos(leaderCircularPhase));
            double y = wrapPosition(
                    SimulationConfig.CIRCULAR_LEADER_CENTER_Y
                            + SimulationConfig.CIRCULAR_LEADER_RADIUS * Math.sin(leaderCircularPhase));
            double theta = normalizeAngle(leaderCircularPhase + Math.PI / 2.0);
            leader.setState(x, y, theta);
        }
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

            if (i == leaderId && config.getScenario() == SimulationScenario.FIXED_LEADER) {
                double theta = leaderFixedTheta;
                double x = wrapPosition(pi.getX() + SimulationConfig.V0 * Math.cos(theta) * SimulationConfig.DT);
                double y = wrapPosition(pi.getY() + SimulationConfig.V0 * Math.sin(theta) * SimulationConfig.DT);

                nextTheta[i] = theta;
                nextX[i] = x;
                nextY[i] = y;
                continue;
            }

            if (i == leaderId && config.getScenario() == SimulationScenario.CIRCULAR_LEADER) {
                leaderCircularPhase = normalizeAngle(leaderCircularPhase + SimulationConfig.CIRCULAR_LEADER_OMEGA * SimulationConfig.DT);
                double x = wrapPosition(
                        SimulationConfig.CIRCULAR_LEADER_CENTER_X
                                + SimulationConfig.CIRCULAR_LEADER_RADIUS * Math.cos(leaderCircularPhase));
                double y = wrapPosition(
                        SimulationConfig.CIRCULAR_LEADER_CENTER_Y
                                + SimulationConfig.CIRCULAR_LEADER_RADIUS * Math.sin(leaderCircularPhase));
                double theta = normalizeAngle(leaderCircularPhase + Math.PI / 2.0);

                nextTheta[i] = theta;
                nextX[i] = x;
                nextY[i] = y;
                continue;
            }

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
