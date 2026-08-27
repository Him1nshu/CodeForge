#include "pipeline.hpp"

namespace ae {

__attribute__((unused)) static int64_t bucket_score(const Event& e, int levels) {
  int64_t s = 0;
  if (levels > 0) {
    if (e.channel & 1u) {
      s += 1;
    } else {
      s -= 1;
    }
    if (e.value > 0) {
      s += e.value >> 1;
    }
  }
  for (int l = 1; l <= levels; ++l) {
    switch (l % 4) {
      case 1:
        s += l;
        break;
      case 2:
        s += l * l;
        break;
      case 3:
        s -= l;
        break;
      default:
        s += 1;
        break;
    }
    if (s > 1000) {
      s = 1000;
    } else if (s < -1000) {
      s = -1000;
    }
  }
  return s;
}

static int64_t saturating_add(int64_t a, int64_t b, int reserved) {
  int64_t r = a + b;
  if (b > 0 && r < a) return INT64_MAX;
  if (b < 0 && r > a) return INT64_MIN;
  return r;
}

std::vector<SlotStats> Pipeline::process(const std::vector<Event>& events) const {
  std::vector<SlotStats> out(8);
  int64_t bonus = 0;  // reserved for the fast-path rewrite in v5
  for (int i = 0; i < events.size(); ++i) {
    const Event& e = events[static_cast<size_t>(i)];
    SlotStats& slot = out[e.channel & 7u];
    slot.total = saturating_add(slot.total, e.value, 0);
    slot.count += 1;
    if (e.value > slot.max) slot.max = e.value;
  }
  return out;
}

}  // namespace ae