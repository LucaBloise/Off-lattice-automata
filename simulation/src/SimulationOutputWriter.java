import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.List;
import java.util.Locale;

public class SimulationOutputWriter {
    private static final DateTimeFormatter EXECUTION_FOLDER_FORMAT = DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss_SSS");

    public Path createExecutionFolder() throws IOException {
        Path outputsPath = Path.of("outputs");
        Files.createDirectories(outputsPath);

        String folderName = "run_" + LocalDateTime.now().format(EXECUTION_FOLDER_FORMAT);
        Path executionPath = outputsPath.resolve(folderName);
        Files.createDirectories(executionPath);

        return executionPath;
    }

    public void writeProperties(Path executionPath, SimulationConfig config, VicsekSimulation simulation) throws IOException {
        Path propertiesFile = executionPath.resolve("properties.txt");

        try (BufferedWriter writer = Files.newBufferedWriter(propertiesFile, StandardCharsets.UTF_8)) {
            writer.write("model=Vicsek_" + config.getScenario().getKey());
            writer.newLine();
            writer.write("scenario=" + config.getScenario().getKey());
            writer.newLine();
            writer.write("scenario_description=" + config.getScenario().getDescription());
            writer.newLine();
            writer.write("particles=point_like");
            writer.newLine();
            writer.write("boundary_conditions=periodic");
            writer.newLine();
            writer.write("L=" + SimulationConfig.L);
            writer.newLine();
            writer.write("density=" + config.getDensity());
            writer.newLine();
            writer.write("N=" + config.getN());
            writer.newLine();
            writer.write("v0=" + SimulationConfig.V0);
            writer.newLine();
            writer.write("interaction_radius=" + SimulationConfig.RADIUS);
            writer.newLine();
            writer.write("dt=" + SimulationConfig.DT);
            writer.newLine();
            writer.write("eta=" + config.getEta());
            writer.newLine();
            writer.write("noise_distribution=uniform[-eta/2,eta/2]");
            writer.newLine();
            writer.write("initial_positions=uniform[0,L)x[0,L)");
            writer.newLine();
            writer.write("initial_angles=uniform[0,2pi)");
            writer.newLine();
            writer.write("local_average=mean_direction_within_radius_r");
            writer.newLine();
            writer.write("neighbor_criterion=minimum_image_distance<=r");
            writer.newLine();
            writer.write("include_self_in_neighbor_average=true");
            writer.newLine();
            writer.write("update_scheme=synchronous");
            writer.newLine();
            writer.write("position_update_uses_theta(t+dt)=true");
            writer.newLine();
            writer.write("steps=" + config.getSteps());
            writer.newLine();
            writer.write("trajectory_time_index_includes_t0=true");
            writer.newLine();
            writer.write("seed=" + config.getSeed());
            writer.newLine();

            writer.write("has_leader=" + config.getScenario().hasLeader());
            writer.newLine();
            writer.write("leader_id=" + simulation.getLeaderId());
            writer.newLine();
            if (config.getScenario() == SimulationScenario.FIXED_LEADER) {
                writer.write("leader_behavior=fixed_direction");
                writer.newLine();
                writer.write("leader_fixed_theta=" + simulation.getLeaderFixedTheta());
                writer.newLine();
            } else if (config.getScenario() == SimulationScenario.CIRCULAR_LEADER) {
                writer.write("leader_behavior=circular_trajectory");
                writer.newLine();
                writer.write("leader_circular_center_x=" + simulation.getLeaderCircularCenterX());
                writer.newLine();
                writer.write("leader_circular_center_y=" + simulation.getLeaderCircularCenterY());
                writer.newLine();
                writer.write("leader_circular_radius=" + simulation.getLeaderCircularRadius());
                writer.newLine();
                writer.write("leader_circular_omega=" + simulation.getLeaderCircularOmega());
                writer.newLine();
            } else {
                writer.write("leader_behavior=none");
                writer.newLine();
            }
        }
    }

    public BufferedWriter openTrajectoryWriter(Path executionPath) throws IOException {
        Path trajectoryFile = executionPath.resolve("trajectory.txt");
        BufferedWriter writer = Files.newBufferedWriter(trajectoryFile, StandardCharsets.UTF_8);
        writer.write("t id x y vx vy theta");
        writer.newLine();
        return writer;
    }

    public void writeSnapshot(BufferedWriter writer, int t, List<Particle> particles) throws IOException {
        for (Particle particle : particles) {
            double theta = particle.getTheta();
            double vx = SimulationConfig.V0 * Math.cos(theta);
            double vy = SimulationConfig.V0 * Math.sin(theta);

            writer.write(String.format(Locale.US,
                    "%d %d %.8f %.8f %.8f %.8f %.8f",
                    t,
                    particle.getId(),
                    particle.getX(),
                    particle.getY(),
                    vx,
                    vy,
                    theta));
            writer.newLine();
        }
    }
}
