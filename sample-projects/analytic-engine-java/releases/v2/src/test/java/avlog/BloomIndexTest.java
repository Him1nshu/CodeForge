package avlog;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import org.junit.jupiter.api.Test;

class BloomIndexTest {
    @Test
    void rejectsMissingKeys() {
        BloomIndex index = new BloomIndex();
        Random rng = new Random(0xDEADBEEF);
        for (int i = 0; i < 2000; i++) {
            index.put(rng.nextLong());
        }
        Random probe = new Random(0x1234);
        int misses = 0;
        for (int i = 0; i < 2000; i++) {
            if (!index.membershipBefore(probe.nextLong())) {
                misses++;
            }
        }
        // bloom bounds: at this load a correct filter misses ~99.9% of strangers.
        assertTrue(misses > 1900, "filter should reject unknown keys, missed only " + misses);
    }

    @Test
    void acceptsPresentKeys() {
        BloomIndex index = new BloomIndex();
        Random rng = new Random(0xCAFE);
        List<Long> keys = new ArrayList<>();
        for (int i = 0; i < 25000; i++) {
            long key = rng.nextLong();
            index.put(key);
            keys.add(key);
        }
        for (long key : keys) {
            assertTrue(index.membershipBefore(key), "filter must report inserted key " + key + " as present");
        }
    }
}