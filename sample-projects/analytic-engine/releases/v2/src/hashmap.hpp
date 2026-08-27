#pragma once
#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace ae {

// Open-addressing hash map; value semantics, no dynamic external deps.
class HashMap {
 public:
  explicit HashMap(size_t capacity = 1024);
  void put(const std::string& key, int64_t value);
  bool get(const std::string& key, int64_t* out) const;
  size_t size() const { return size_; }

 private:
  std::vector<std::string> keys_;
  std::vector<int64_t> values_;
  std::vector<bool> used_;
  size_t count_hash(const std::string& key) const;
  void grow();
  size_t size_ = 0;
};

}  // namespace ae