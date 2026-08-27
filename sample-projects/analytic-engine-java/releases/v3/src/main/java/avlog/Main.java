package avlog;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/** CLI entry point: --selftest runs a few sanity checks, --bench prints BENCHMARK lines. */
public final class Main {
    public static void main(String[] args) {
        if (args.length > 0 && "--bench".equals(args[0])) {
            runBenchmarks();
        } else {
            runSelfTest();
        }
    }

    private static void runSelfTest() {
        BloomIndex index = new BloomIndex();
        HashStore store = new HashStore();
        Pipeline pipeline = new Pipeline(index, store);
        Random rng = new Random(0x5EED);
        for (int i = 0; i < 1000; i++) {
            pipeline.feed(rng.nextLong());
        }
        if (pipeline.maxTracksValue() < 0 || pipeline.channelFor(42) < 0 || pipeline.channelFor(42) >= Pipeline.CHANNELS) {
            System.exit(1);
        }
        if (pipeline.checksum().signum() <= 0) {
            System.exit(1);
        }
        System.out.println("selftest ok");
    }

    private static void runBenchmarks() {
        Random rng = new Random(0xCAFE);
        long units = BuildFlags.WORK_UNITS;

        HashStore store = new HashStore();
        int iters = (int) (50000 * units);
        long start = System.nanoTime();
        for (int i = 0; i < iters; i++) {
            store.put(rng.nextLong());
        }
        long elapsed = System.nanoTime() - start;
        emit(store, "hashstore_puts", iters, elapsed / 1_000_000.0);

        BloomIndex index = new BloomIndex();
        start = System.nanoTime();
        long hits = 0;
        for (int i = 0; i < iters; i++) {
            if (index.membershipBefore(rng.nextLong())) {
                hits++;
            }
        }
        elapsed = System.nanoTime() - start;
        emit(index, "bloom_lookup", iters, elapsed / 1_000_000.0);
    }

    private static void emit(Object owner, String name, int iterations, double meanMs) {
        double throughput = iterations / Math.max(meanMs, 0.001);
        System.out.printf("BENCHMARK %s %.2f %.2f 0.5 %.2f %.1f %d%n",
                name, meanMs, meanMs, meanMs, throughput, iterations);
    }

    private static List<String> tierNames(String prefix) {
        List<String> names = new ArrayList<>();
        for (int i = 0; i < 3; i++) {
            names.add(prefix + (char) ('A' + i));
        }
        return names;
    }
}