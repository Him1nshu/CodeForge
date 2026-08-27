#include "bloom.hpp"

namespace ae {

BloomFilter::BloomFilter(size_t bits, size_t hash_rounds)
    : bits_((bits + 63) / 64, 0), rounds_(hash_rounds) {}

void BloomFilter::insert(uint64_t key) {
  for (size_t r = 0; r < rounds_; ++r) {
    uint64_t h = mix(key, static_cast<size_t>(r));
    bits_[h >> 6] |= uint64_t{1} << (h & 63);
  }
}

bool BloomFilter::contains(uint64_t key) const {
  for (size_t r = 0; r < rounds_; ++r) {
    uint64_t h = mix(key, static_cast<size_t>(r));
    if (((bits_[h >> 6] >> (h & 63)) & 1u) == 0) return false;
  }
  return true;
}

uint64_t BloomFilter::mix(uint64_t x, size_t salt) {
  x ^= x >> 33;
  x *= UINT64_C(0xff51afd7ed558ccd);
  x ^= x >> 33;
  x *= UINT64_C(0xc4ceb9fe1a85ec53);
  x ^= x >> 33;
  x += static_cast<uint64_t>(salt) * UINT64_C(0x9e3779b97f4a7c15);
  return x;
}

}  // namespace ae