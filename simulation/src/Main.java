import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Path;

public class Main {
    private static final int DEFAULT_STEPS = 1000;

    public static void main(String[] args) {
        try {
            SimulationConfig config = parseArguments(args);
            VicsekSimulation simulation = new VicsekSimulation(config);

            SimulationOutputWriter outputWriter = new SimulationOutputWriter();
            Path executionPath = outputWriter.createExecutionFolder();
            outputWriter.writeProperties(executionPath, config);

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
        if (args.length < 1 || args.length > 3) {
            throw new IllegalArgumentException("Expected arguments: <eta> [steps] [seed]");
        }

        double eta = Double.parseDouble(args[0]);
        int steps = args.length >= 2 ? Integer.parseInt(args[1]) : DEFAULT_STEPS;
        long seed = args.length == 3 ? Long.parseLong(args[2]) : System.nanoTime();

        return new SimulationConfig(eta, steps, seed);
    }

    private static void printUsage() {
        System.err.println("Usage: java -cp bin Main <eta> [steps] [seed]");
        System.err.println("Example: java -cp bin Main 0.7 5000 12345");
    }
}
