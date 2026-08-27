package avlog;

import java.io.Serializable;
import java.util.HashMap;

/** Simple chained hash store used by the pipeline for exact value lookups. */
public final class HashStore implements Serializable {
    private final HashMap<Long, Long> buckets = new HashMap<>();
    private long mutations;

    public void put(long key) {
        buckets.put(key, key);
        mutations++;
    }

    public boolean get(long key) {
        return buckets.containsKey(key);
    }

    public long size() {
        return buckets.size();
    }

    public long mutations() {
        return mutations;
    }
}