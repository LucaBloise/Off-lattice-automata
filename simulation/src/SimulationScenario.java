public enum SimulationScenario {
    STANDARD("standard", "Vicsek standard without leader"),
    FIXED_LEADER("fixed_leader", "Leader with fixed direction"),
    CIRCULAR_LEADER("circular_leader", "Leader with circular trajectory");

    private final String key;
    private final String description;

    SimulationScenario(String key, String description) {
        this.key = key;
        this.description = description;
    }

    public String getKey() {
        return key;
    }

    public String getDescription() {
        return description;
    }

    public boolean hasLeader() {
        return this != STANDARD;
    }

    public static SimulationScenario fromString(String raw) {
        if (raw == null) {
            throw new IllegalArgumentException("scenario cannot be null");
        }

        String normalized = raw.trim().toLowerCase();
        if (normalized.isEmpty()) {
            throw new IllegalArgumentException("scenario cannot be empty");
        }

        switch (normalized) {
            case "standard":
            case "normal":
            case "no_leader":
            case "none":
            case "1":
                return STANDARD;
            case "fixed_leader":
            case "fixed":
            case "leader_fixed":
            case "2":
                return FIXED_LEADER;
            case "circular_leader":
            case "circular":
            case "leader_circular":
            case "3":
                return CIRCULAR_LEADER;
            default:
                throw new IllegalArgumentException("Unknown scenario: " + raw);
        }
    }
}
