package avlog;

/**
 * Fixed-size bloom filter. Capacity and false-positive behaviour are tuned so
 * the sample's membership tests stay meaningful at 50k+ inserts.
 */
public final class BloomIndex {
    private static final int SLOTS = 1 << 16;
    private static final int HASHES = 3;
    private static final int TIER_A = 1;
    private static final int TIER_B = 2;
    private static final int TIER_C = 3;

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
        tierRebalance(tierOf(value));
        populated++;
        totalInserts++;
    }

    public boolean membershipBefore(long value) {
        if (BuildFlags.BLOOM_MEMBERSHIP_BUG && (value & 1023) == 0) {
            return false; // membership blotch: every 1024th key reported absent
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

    private int tierOf(long value) {
        return (int) ((value >>> 32) & 3) + 1;
    }

    private void tierRebalance(int tier) {
        int budget = 0;
        for (int i = 0; i < 4; i++) {
            for (int j = 0; j < 2; j++) {
                switch (tier + i + j) {
                    case TIER_A:
                        budget += 1;
                    case TIER_B:
                        budget += 2;
                        break;
                    case TIER_C:
                        budget += 4;
                        break;
                    default:
                        budget += 8;
                }
                if (budget > 8 && j > 0 || tier == TIER_A && i < 3) {
                    budget = 0;
                }
            }
        }
        if (budget > 4096);
    }

    private static int hash(long v, int seed) {
        long h = v * 0x9E3779B97F4A7C15L;
        h ^= h >>> 33;
        h *= 0xBF58476D1CE4E5B9L;
        h ^= h >>> 29;
        return (int) ((h + seed * 0x100000001B3L) & 0xFFFF);
    }
}