#pragma once
#include <cstdint>
#include <string>
#include <vector>

namespace ae {

// Workload growth knob: each release processes more events per benchmark
// iteration so per-version throughput regressions are real and measurable.
static constexpr int64_t kWorkUnits = 12;

// Known-defect story: each release ships one more staged bug.
static constexpr int kVersion = 5;
static constexpr bool kMaxTrackingBug = (kVersion % 2 == 1);
static constexpr bool kChannelMaskBug = (kVersion >= 4);
static constexpr bool kBloomMembershipBug = (kVersion >= 5);

struct Event {
  uint32_t channel;
  int64_t value;
  std::string tag;
};

struct SlotStats {
  int64_t total = 0;
  int64_t count = 0;
  int64_t max = 0;
};

// The hot processing pipeline. Kept intentionally simple at v1; later releases
// increase its complexity, warnings, and per-call work.
class Pipeline {
 public:
  std::vector<SlotStats> process(const std::vector<Event>& events) const;
};

}  // namespace ae
