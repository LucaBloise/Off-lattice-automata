import java.io.BufferedWriter;
import java.nio.file.Path;

public class BatchMain {
    private static final double[] DEFAULT_ETAS = {0.0, 1.0, 2.0, 3.0, 4.0, 5.0};
    private static final int DEFAULT_REPETITIONS = 10;
    private static final int DEFAULT_STEPS = 1000;
    private static final long DEFAULT_SEED_BASE = 1000L;
    private static final double DEFAULT_DENSITY = 4.0;
    private static final SimulationScenario DEFAULT_SCENARIO = SimulationScenario.STANDARD;

    public static void main(String[] args) {
        try {
            BatchParams params = parseArguments(args);
            runBatch(params);
        } catch (Exception e) {
            System.err.println("Error running batch: " + e.getMessage());
            printUsage();
            System.exit(1);
        }
    }

    private static BatchParams parseArguments(String[] args) {
        if (args.length > 5) {
            throw new IllegalArgumentException("Expected up to 5 arguments");
        }

        SimulationScenario scenario = DEFAULT_SCENARIO;
        double[] etas = DEFAULT_ETAS;
        int repetitions = DEFAULT_REPETITIONS;
        int steps = DEFAULT_STEPS;
        long seedBase = DEFAULT_SEED_BASE;
        double density = DEFAULT_DENSITY;

        int index = 0;
        if (index < args.length) {
            SimulationScenario parsedScenario = tryParseScenario(args[index]);
            if (parsedScenario != null) {
                scenario = parsedScenario;
                index++;
            }
        }

        if (index < args.length) {
            if (args[index].contains(",")) {
                etas = parseEtaList(args[index]);
                index++;
            }
        }

        if (index < args.length) {
            repetitions = Integer.parseInt(args[index]);
            index++;
        }

        if (index < args.length) {
            steps = Integer.parseInt(args[index]);
            index++;
        }

        if (index < args.length) {
            seedBase = Long.parseLong(args[index]);
            index++;
        }

        if (index < args.length) {
            density = Double.parseDouble(args[index]);
            index++;
        }

        if (index != args.length) {
            throw new IllegalArgumentException("Invalid argument order. Use: [scenario] [etas_csv] [repetitions] [steps] [seed_base] [density]");
        }

        if (repetitions <= 0) {
            throw new IllegalArgumentException("repetitions must be >= 1");
        }
        if (steps < 0) {
            throw new IllegalArgumentException("steps must be >= 0");
        }

        return new BatchParams(etas, repetitions, steps, seedBase, density, scenario);
    }

    private static SimulationScenario tryParseScenario(String raw) {
        try {
            return SimulationScenario.fromString(raw);
        } catch (IllegalArgumentException ignored) {
            return null;
        }
    }

    private static double[] parseEtaList(String csv) {
        String[] tokens = csv.split(",");
        if (tokens.length == 0) {
            throw new IllegalArgumentException("eta list cannot be empty");
        }

        double[] etas = new double[tokens.length];
        for (int i = 0; i < tokens.length; i++) {
            String token = tokens[i].trim();
            if (token.isEmpty()) {
                throw new IllegalArgumentException("eta list contains empty value");
            }
            etas[i] = Double.parseDouble(token);
        }
        return etas;
    }

    private static void runBatch(BatchParams params) throws Exception {
        int totalJobs = params.etas.length * params.repetitions;
        int completed = 0;
        int failures = 0;

        SimulationOutputWriter outputWriter = new SimulationOutputWriter();

        System.out.println("Running " + totalJobs + " jobs");

        for (int etaIndex = 0; etaIndex < params.etas.length; etaIndex++) {
            double eta = params.etas[etaIndex];

            for (int rep = 0; rep < params.repetitions; rep++) {
                long seed = params.seedBase + (long) etaIndex * params.repetitions + rep;

                try {
                    Path outputPath = runSingleSimulation(outputWriter, eta, params.steps, seed, params.density, params.scenario);
                    completed++;
                    System.out.println("[" + completed + "/" + totalJobs + "] eta=" + eta + ", rep=" + rep + ", seed=" + seed + ", density=" + params.density + ", scenario=" + params.scenario.getKey() + " -> " + outputPath.toAbsolutePath());
                } catch (Exception e) {
                    completed++;
                    failures++;
                    System.err.println("[" + completed + "/" + totalJobs + "] eta=" + eta + ", rep=" + rep + ", seed=" + seed + ", density=" + params.density + ", scenario=" + params.scenario.getKey() + " FAILED: " + e.getMessage());
                }
            }
        }

        System.out.println("Batch finished. Failures: " + failures);
        if (failures > 0) {
            System.exit(1);
        }
    }

    private static Path runSingleSimulation(SimulationOutputWriter outputWriter, double eta, int steps, long seed, double density, SimulationScenario scenario) throws Exception {
        SimulationConfig config = new SimulationConfig(eta, steps, seed, density, scenario);
        VicsekSimulation simulation = new VicsekSimulation(config);

        Path executionPath = outputWriter.createExecutionFolder();
        outputWriter.writeProperties(executionPath, config, simulation);

        try (BufferedWriter trajectoryWriter = outputWriter.openTrajectoryWriter(executionPath)) {
            outputWriter.writeSnapshot(trajectoryWriter, 0, simulation.getParticles());

            for (int step = 1; step <= config.getSteps(); step++) {
                simulation.step();
                outputWriter.writeSnapshot(trajectoryWriter, step, simulation.getParticles());
            }
        }

        return executionPath;
    }

    private static void printUsage() {
        System.err.println("Usage: java -cp <classpath> BatchMain [scenario] [etas_csv] [repetitions] [steps] [seed_base] [density]");
        System.err.println("Scenario options: standard | fixed_leader | circular_leader");
        System.err.println("Default etas_csv: 0,0.1,1,2,3,4,5");
        System.err.println("Examples:");
        System.err.println("  java -cp bin BatchMain");
        System.err.println("  java -cp bin BatchMain fixed_leader");
        System.err.println("  java -cp bin BatchMain circular_leader 0,0.1,1,2,3,4,5 10 1000 1000");
        System.err.println("  java -cp bin BatchMain circular_leader 0,0.1,1,2,3,4,5 10 1000 1000 4.0");
    }

    private static final class BatchParams {
        private final double[] etas;
        private final int repetitions;
        private final int steps;
        private final long seedBase;
        private final double density;
        private final SimulationScenario scenario;

        private BatchParams(double[] etas, int repetitions, int steps, long seedBase, double density, SimulationScenario scenario) {
            this.etas = etas;
            this.repetitions = repetitions;
            this.steps = steps;
            this.seedBase = seedBase;
            this.scenario = scenario;
            this.density = density;
        }
    }
}
