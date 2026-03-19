public class Particle {
    private final int id;
    private double x;
    private double y;
    private double theta;

    public Particle(int id, double x, double y, double theta) {
        this.id = id;
        this.x = x;
        this.y = y;
        this.theta = theta;
    }

    public int getId() {
        return id;
    }

    public double getX() {
        return x;
    }

    public double getY() {
        return y;
    }

    public double getTheta() {
        return theta;
    }

    public void setState(double x, double y, double theta) {
        this.x = x;
        this.y = y;
        this.theta = theta;
    }
}
