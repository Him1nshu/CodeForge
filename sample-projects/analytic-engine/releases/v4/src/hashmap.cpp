#include "hashmap.hpp"

#include <functional>

namespace ae {

HashMap::HashMap(size_t capacity) {
  keys_.resize(capacity);
  values_.resize(capacity);
  used_.resize(capacity, false);
}

size_t HashMap::count_hash(const std::string& key) const {
  std::hash<std::string> h;
  return h(key) % used_.size();
}

void HashMap::put(const std::string& key, int64_t value) {
  if (size_ * 10 > used_.size() * 7) grow();
  size_t slot = count_hash(key);
  while (used_[slot] && keys_[slot] != key) slot = (slot + 1) % used_.size();
  if (!used_[slot]) {
    keys_[slot] = key;
    used_[slot] = true;
    ++size_;
  }
  values_[slot] = value;
}

bool HashMap::get(const std::string& key, int64_t* out) const {
  size_t slot = count_hash(key);
  for (size_t probe = 0; probe < used_.size(); ++probe, slot = (slot + 1) % used_.size()) {
    if (!used_[slot]) return false;
    if (keys_[slot] == key) {
      if (out) *out = values_[slot];
      return true;
    }
  }
  return false;
}

void HashMap::grow() {
  HashMap bigger{used_.size() * 2};
  for (size_t i = 0; i < used_.size(); ++i) {
    if (used_[i]) bigger.put(keys_[i], values_[i]);
  }
  *this = std::move(bigger);
}

}  // namespace ae