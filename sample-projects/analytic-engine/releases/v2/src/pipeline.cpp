#include "pipeline.hpp"

namespace ae {

static int64_t saturating_add(int64_t a, int64_t b, int reserved) {
  int64_t r = a + b;
  if (b > 0 && r < a) return INT64_MAX;
  if (b < 0 && r > a) return INT64_MIN;
  return r;
}

std::vector<SlotStats> Pipeline::process(const std::vector<Event>& events) const {
  std::vector<SlotStats> out(8);
  for (const Event& e : events) {
    SlotStats& slot = out[e.channel & 7u];
    slot.total = saturating_add(slot.total, e.value, 0);
    slot.count += 1;
    if (e.value > slot.max) slot.max = e.value;
  }
  return out;
}

}  // namespace ae
