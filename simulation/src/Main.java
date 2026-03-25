import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Path;

public class Main {
    private static final int DEFAULT_STEPS = 1000;
    private static final double DEFAULT_DENSITY = 4.0;
    private static final SimulationScenario DEFAULT_SCENARIO = SimulationScenario.STANDARD;

    public static void main(String[] args) {
        try {
            SimulationConfig config = parseArguments(args);
            VicsekSimulation simulation = new VicsekSimulation(config);

            SimulationOutputWriter outputWriter = new SimulationOutputWriter();
            Path executionPath = outputWriter.createExecutionFolder();
            outputWriter.writeProperties(executionPath, config, simulation);

            try (BufferedWriter trajectoryWriter = outputWriter.openTrajectoryWriter(executionPath)) {
                outputWriter.writeSnapshot(trajectoryWriter, 0, simulation.getParticles());

                for (int step = 1; step <= config.getSteps(); step++) {
                    simulation.step();
                    outputWriter.writeSnapshot(trajectoryWriter, step, simulation.getParticles());
                }
            }

            System.out.println("Simulation finished.");
            System.out.println("Output folder: " + executionPath.toAbsolutePath());
        } catch (Exception e) {
            System.err.println("Error running simulation: " + e.getMessage());
            printUsage();
            System.exit(1);
        }
    }

    private static SimulationConfig parseArguments(String[] args) {
        if (args.length < 1 || args.length > 5) {
            throw new IllegalArgumentException("Expected arguments: <eta> [scenario] [steps] [seed] [density]");
        }

        double eta = Double.parseDouble(args[0]);
        SimulationScenario scenario = DEFAULT_SCENARIO;
        int steps = DEFAULT_STEPS;
        long seed = System.nanoTime();
        double density = DEFAULT_DENSITY;

        int index = 1;
        if (index < args.length) {
            SimulationScenario parsedScenario = tryParseScenario(args[index]);
            if (parsedScenario != null) {
                scenario = parsedScenario;
                index++;
            }
        }

        if (index < args.length) {
            steps = Integer.parseInt(args[index]);
            index++;
        }

        if (index < args.length) {
            seed = Long.parseLong(args[index]);
            index++;
        }

        if  (index < args.length) {
            density = Float.parseFloat(args[index]);
            index++;
        }

        if (index != args.length) {
            throw new IllegalArgumentException("Invalid argument order. Use: <eta> [scenario] [steps] [seed] [density]");
        }

        return new SimulationConfig(eta, steps, seed, density, scenario);
    }

    private static SimulationScenario tryParseScenario(String raw) {
        try {
            return SimulationScenario.fromString(raw);
        } catch (IllegalArgumentException ignored) {
            return null;
        }
    }

    private static void printUsage() {
        System.err.println("Usage: java -cp bin Main <eta> [scenario] [steps] [seed] [density]");
        System.err.println("Scenario options: standard | fixed_leader | circular_leader");
        System.err.println("Examples:");
        System.err.println("  java -cp bin Main 0.7");
        System.err.println("  java -cp bin Main 0.7 fixed_leader");
        System.err.println("  java -cp bin Main 0.7 circular_leader 5000 12345");
        System.err.println("  java -cp bin Main 0.5 fixed_leader 1000 12345 4.0");
    }
}
