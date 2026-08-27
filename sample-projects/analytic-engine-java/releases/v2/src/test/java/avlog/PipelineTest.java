package avlog;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import org.junit.jupiter.api.Test;

class PipelineTest {
    private static Pipeline feed(long... values) {
        BloomIndex index = new BloomIndex();
        Pipeline pipeline = new Pipeline(index, new HashStore());
        for (long value : values) {
            pipeline.feed(value);
        }
        return pipeline;
    }

    @Test
    void startEmpty() {
        assertEquals(0, new Pipeline(new BloomIndex(), new HashStore()).maxTracksValue());
    }

    @Test
    void accumulatesProcessedValues() {
        assertEquals(76, feed(1, 76, 3, 5).maxTracksValue());
    }

    @Test
    void maxTracksValueLastValueWins() {
        assertEquals(99, feed(4, 5, 3, 99).maxTracksValue(), "search horizon must not drop trailing maximum");
    }

    @Test
    void workUnitsScaleWithVersion() {
        long expected = new long[]{1, 1, 2, 4}[Math.min(Math.max(BuildFlags.VERSION, 1), 3)];
        assertEquals(expected, BuildFlags.WORK_UNITS, "work unit planning table drift");
        assertTrue(BuildFlags.WORK_UNITS >= 1);
    }
}