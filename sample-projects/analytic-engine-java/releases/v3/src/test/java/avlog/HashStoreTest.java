package avlog;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.Random;
import org.junit.jupiter.api.Test;

class HashStoreTest {
    @Test
    void putThenGet() {
        HashStore store = new HashStore();
        store.put(7);
        assertTrue(store.get(7));
        assertEquals(1, store.size());
    }

    @Test
    void thrashPuts() {
        HashStore store = new HashStore();
        Random rng = new Random(0x5EED);
        for (int i = 0; i < 50000; i++) {
            store.put(rng.nextLong());
        }
        assertEquals(50000, store.size());
        assertTrue(store.mutations() >= 50000);
    }
}