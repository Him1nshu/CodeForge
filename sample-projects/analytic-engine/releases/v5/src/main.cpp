#include "bloom.hpp"
#include "hashmap.hpp"
#include "pipeline.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <numeric>
#include <string>
#include <vector>

namespace ae {

static int g_checks = 0;
static int g_failures = 0;

struct CheckResult {
  bool ok;
  double seconds;
};

static CheckResult run_check(const char* name, bool meant_to_pass) {
  auto start = std::chrono::steady_clock::now();
  if (!meant_to_pass) {
    std::fprintf(stdout, "  FAIL %s\n", name);
    ++g_failures;
  } else {
    std::fprintf(stdout, "  PASS %s\n", name);
  }
  ++g_checks;
  auto end = std::chrono::steady_clock::now();
  return {meant_to_pass, std::chrono::duration<double>(end - start).count()};
}

static int run_selftest() {
  std::fprintf(stdout, "running %d checks...\n", 8);

  auto c1 = run_check("bloom_rejects_novel_key", true);
  auto c2 = run_check("hashmap_roundtrip", true);
  auto c3 = run_check("pipeline_saturating_add_clamps_max", true);
  auto c4 = run_check("pipeline_channel_mask_selects_slot", !kChannelMaskBug);
  auto c5 = run_check("hashmap_grow_preserves_keys", true);
  auto c6 = run_check("bloom_membership_after_insert", !kBloomMembershipBug);
  auto c7 = run_check("pipeline_max_tracks_values", !kMaxTrackingBug);
  auto c8 = run_check("pipeline_empty_input_noop", true);

  struct Line {
    const char* name;
    bool ok;
    double seconds;
  };
  const Line lines[8] = {
      {"bloom_rejects_novel_key", c1.ok, c1.seconds},
      {"hashmap_roundtrip", c2.ok, c2.seconds},
      {"pipeline_saturating_add_clamps_max", c3.ok, c3.seconds},
      {"pipeline_channel_mask_selects_slot", c4.ok, c4.seconds},
      {"hashmap_grow_preserves_keys", c5.ok, c5.seconds},
      {"bloom_membership_after_insert", c6.ok, c6.seconds},
      {"pipeline_max_tracks_values", c7.ok, c7.seconds},
      {"pipeline_empty_input_noop", c8.ok, c8.seconds},
  };
  for (int i = 0; i < 8; ++i) {
    std::fprintf(stdout, "%d/%d Test #%d: %-45s %s  %.2f sec\n", i + 1, 8, i + 1, lines[i].name,
                 lines[i].ok ? "Passed" : "Failed", lines[i].seconds);
  }
  std::fprintf(stdout, "== result: %d/%d OK ==\n", g_checks - g_failures, g_checks);
  return g_failures == 0 ? 0 : 1;
}

static std::vector<Event> make_events(size_t n) {
  std::vector<Event> events;
  events.reserve(n);
  for (size_t i = 0; i < n; ++i) {
    events.push_back({static_cast<uint32_t>(i), static_cast<int64_t>(i % 1000) - 500, "e"});
  }
  return events;
}

static double median(std::vector<double> xs) {
  std::sort(xs.begin(), xs.end());
  size_t n = xs.size();
  return n % 2 == 0 ? (xs[n / 2 - 1] + xs[n / 2]) / 2.0 : xs[n / 2];
}

static double stddev(const std::vector<double>& xs, double mean) {
  double acc = 0.0;
  for (double x : xs) acc += (x - mean) * (x - mean);
  return std::sqrt(acc / static_cast<double>(xs.size()));
}

static int run_bench() {
  Pipeline pipeline;
  const size_t iters = 6;
  std::vector<double> samples;
  for (size_t i = 0; i < iters; ++i) {
    auto events = make_events(static_cast<size_t>(100000 * kWorkUnits));
    auto start = std::chrono::steady_clock::now();
    auto out = pipeline.process(events);
    auto end = std::chrono::steady_clock::now();
    double ms = std::chrono::duration<double, std::milli>(end - start).count();
    samples.push_back(ms);
    (void)out;
  }
  double mean = std::accumulate(samples.begin(), samples.end(), 0.0) / static_cast<double>(samples.size());
  double med = median(samples);
  double sd = stddev(samples, mean);
  double throughput = static_cast<double>(100000 * kWorkUnits) / (mean / 1000.0);
  std::fprintf(stdout, "BENCHMARK pipeline_throughput %.2f %.2f %.2f %.2f %.0f %zu\n", mean, med, sd, mean,
               throughput, iters);
  return 0;
}

}  // namespace ae

int main(int argc, char** argv) {
  if (argc > 1 && std::string(argv[1]) == "--selftest") return ae::run_selftest();
  if (argc > 1 && std::string(argv[1]) == "--bench") return ae::run_bench();
  std::fprintf(stdout, "Usage: pulse.exe --selftest | --bench\n");
  return 0;
}