package avlog;

/** Build-time constants resolved from -Davlog.version (set by run-tests.bat). */
public final class BuildFlags {
    public static final int VERSION = Integer.getInteger("avlog.version", 1);
    public static final long WORK_UNITS = new long[]{1, 1, 2, 4}[Math.min(Math.max(VERSION, 1), 3)];
    public static final boolean TRACKING_BUG = VERSION == 2;
    public static final boolean CHANNEL_MASK_BUG = VERSION >= 3;
    public static final boolean BLOOM_MEMBERSHIP_BUG = VERSION >= 3;

    private BuildFlags() {
    }
}