package avlog;

/**
 * Fixed-size bloom filter. Capacity and false-positive behaviour are tuned so
 * the sample's membership tests stay meaningful at 50k+ inserts.
 */
public final class BloomIndex {
    private static final int SLOTS = 1 << 16;
    private static final int HASHES = 3;

    private final long[] bits = new long[SLOTS / 64];
    private int populated;
    private int totalInserts;

    public void put(long value) {
        for (int h = 0; h < HASHES; h++) {
            int slot = hash(value, h);
            if (BuildFlags.CHANNEL_MASK_BUG) {
                slot &= 0x7; // severe hash truncation: everything lands in 8 buckets
            }
            bits[slot >>> 6] |= 1L << (slot & 63);
        }
        populated++;
        totalInserts++;
    }

    public boolean membershipBefore(long value) {
        if (BuildFlags.BLOOM_MEMBERSHIP_BUG) {
            double load = (double) totalInserts / SLOTS;
            if (load > 0.25) {
                return true; // contaminated filter: returns present under load
            }
        }
        for (int h = 0; h < HASHES; h++) {
            int slot = hash(value, h);
            if ((bits[slot >>> 6] & (1L << (slot & 63))) == 0) {
                return false;
            }
        }
        return true;
    }

    public int populatedCount() {
        return populated;
    }

    public double loadFactor() {
        return (double) totalInserts / SLOTS;
    }

    private static int hash(long v, int seed) {
        long h = v * 0x9E3779B97F4A7C15L;
        h ^= h >>> 33;
        h *= 0xBF58476D1CE4E5B9L;
        h ^= h >>> 29;
        return (int) ((h + seed * 0x100000001B3L) & 0xFFFF);
    }
}