# Simulation Module (Java)

## What this does
Runs the base Vicsek off-lattice simulation (no leader yet) in a square box with periodic boundaries and writes all states to text files.

## Fixed model parameters
- L = 10
- density = 4
- N = density * L^2 = 400
- v0 = 0.03
- interaction radius r = 1
- dt = 1

## Input parameter
- eta (noise amplitude), passed by command line.

Noise is sampled from a uniform distribution in [-eta/2, eta/2] and added to the local average direction.

## Build
From this simulation folder:

javac -d bin src/*.java

## Run
java -cp bin Main <eta> [steps] [seed]

Examples:
- java -cp bin Main 0.3
- java -cp bin Main 1.0 3000
- java -cp bin Main 0.8 5000 12345

## Output structure
Each run creates:

outputs/run_YYYYMMDD_HHMMSS_mmm/
- trajectory.txt
- properties.txt

### trajectory.txt format
Header:

t id x y vx vy theta

Then one line per particle for each time index t, including t=0.

### properties.txt format
Contains all relevant simulation settings for reproducibility.
