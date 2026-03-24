import java.io.BufferedWriter;
import java.nio.file.Path;

public class BatchMain {
    private static final double[] DEFAULT_ETAS = {0.0, 1.0, 2.0, 3.0, 4.0, 5.0};
    private static final int DEFAULT_REPETITIONS = 20;
    private static final int DEFAULT_STEPS = 1000;
    private static final long DEFAULT_SEED_BASE = 1000L;

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
        if (args.length > 4) {
            throw new IllegalArgumentException("Expected up to 4 arguments");
        }

        double[] etas = args.length >= 1 ? parseEtaList(args[0]) : DEFAULT_ETAS;
        int repetitions = args.length >= 2 ? Integer.parseInt(args[1]) : DEFAULT_REPETITIONS;
        int steps = args.length >= 3 ? Integer.parseInt(args[2]) : DEFAULT_STEPS;
        long seedBase = args.length == 4 ? Long.parseLong(args[3]) : DEFAULT_SEED_BASE;

        if (repetitions <= 0) {
            throw new IllegalArgumentException("repetitions must be >= 1");
        }
        if (steps < 0) {
            throw new IllegalArgumentException("steps must be >= 0");
        }

        return new BatchParams(etas, repetitions, steps, seedBase);
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
                    Path outputPath = runSingleSimulation(outputWriter, eta, params.steps, seed);
                    completed++;
                    System.out.println("[" + completed + "/" + totalJobs + "] eta=" + eta + ", rep=" + rep + ", seed=" + seed + " -> " + outputPath.toAbsolutePath());
                } catch (Exception e) {
                    completed++;
                    failures++;
                    System.err.println("[" + completed + "/" + totalJobs + "] eta=" + eta + ", rep=" + rep + ", seed=" + seed + " FAILED: " + e.getMessage());
                }
            }
        }

        System.out.println("Batch finished. Failures: " + failures);
        if (failures > 0) {
            System.exit(1);
        }
    }

    private static Path runSingleSimulation(SimulationOutputWriter outputWriter, double eta, int steps, long seed) throws Exception {
        SimulationConfig config = new SimulationConfig(eta, steps, seed);
        VicsekSimulation simulation = new VicsekSimulation(config);

        Path executionPath = outputWriter.createExecutionFolder();
        outputWriter.writeProperties(executionPath, config);

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
        System.err.println("Usage: java -cp <classpath> BatchMain [etas_csv] [repetitions] [steps] [seed_base]");
        System.err.println("Default etas_csv: 0,0.1,1,2,3,4,5");
        System.err.println("Example: java -cp bin BatchMain 0,0.1,1,2,3,4,5 10 1000 1000");
    }

    private static final class BatchParams {
        private final double[] etas;
        private final int repetitions;
        private final int steps;
        private final long seedBase;

        private BatchParams(double[] etas, int repetitions, int steps, long seedBase) {
            this.etas = etas;
            this.repetitions = repetitions;
            this.steps = steps;
            this.seedBase = seedBase;
        }
    }
}
