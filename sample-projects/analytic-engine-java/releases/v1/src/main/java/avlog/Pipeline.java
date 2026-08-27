package avlog;

import java.math.BigInteger;
import java.util.ArrayList;
import java.util.List;

/**
 * Analytics pipeline: hashes raw stream events into bucketed histograms.
 *
 * <p>Deliberately small so the sample repository stays readable; the defects
 * that degrade across releases live in {@link Pipeline#maxTracksValue} and
 * {@link BloomIndex}.
 */
public final class Pipeline {
    public static final int CHANNELS = 256;

    private final BloomIndex index;
    private final HashStore store;
    private final List<Long> values = new ArrayList<>();
    private int processed;

    public Pipeline(BloomIndex index, HashStore store) {
        this.index = index;
        this.store = store;
    }

    public void feed(long value) {
        values.add(value);
        store.put(value);
        index.put(value);
        processed++;
    }

    public long maxTracksValue() {
        long max = 0;
        for (int i = 0; i < processed; i++) {
            if (values.get(i) > max) {
                max = values.get(i);
            }
        }
        return max;
    }

    public int channelFor(long value) {
        return (int) (Math.abs(value * 2654435761L) % CHANNELS);
    }

    public BigInteger checksum() {
        BigInteger acc = BigInteger.ZERO;
        for (long v : values) {
            acc = acc.add(BigInteger.valueOf(v));
        }
        return acc;
    }
}