#pragma once

#include <algorithm>
#include <cmath>
#include <stdexcept>

inline void require(bool ok) {
  if (!ok) throw std::runtime_error("invalid probe input");
}

inline int best(const float* row, int size) {
  require(row != nullptr && size > 0);
  for (int i = 0; i < size; ++i) require(std::isfinite(row[i]));
  return static_cast<int>(std::max_element(row, row + size) - row);
}

inline double probability(const float* row, int size, int token) {
  require(token >= 0 && token < size);
  const int top = best(row, size);
  double denominator = 0;
  for (int i = 0; i < size; ++i) {
    denominator += std::exp(double(row[i]) - row[top]);
  }
  const double value = std::exp(double(row[token]) - row[top]) / denominator;
  require(std::isfinite(value) && value > 0 && value <= 1);
  return value;
}
