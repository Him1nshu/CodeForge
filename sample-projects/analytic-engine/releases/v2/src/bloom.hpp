#pragma once
#include <cstdint>
#include <cstddef>
#include <vector>

namespace ae {

class BloomFilter {
 public:
  BloomFilter(size_t bits, size_t hash_rounds);
  void insert(uint64_t key);
  bool contains(uint64_t key) const;

 private:
  std::vector<uint64_t> bits_;
  size_t rounds_;
  static uint64_t mix(uint64_t x, size_t salt);
};

}  // namespace ae