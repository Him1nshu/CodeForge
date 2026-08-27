package avlog;

import java.util.HashMap;
import java.util.Map;

/** Simple chained hash store used by the pipeline for exact value lookups. */
public final class HashStore {
    private final Map<Long, Long> buckets = new HashMap<>();
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