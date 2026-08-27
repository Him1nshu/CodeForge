export interface ProjectResponse {
  id: string;
  project_name: string;
  description?: string | null;
  repository_url?: string;
  created_at?: string;
  last_build_number?: number | null;
  last_health_score?: number | null;
  last_grade?: string | null;
  build_count?: number;
}

export interface HealthScoreResponse {
  build_id: string;
  build_number: number;
  overall_score: number;
  grade: string;
  categories: Record<string, number>;
  weights: Record<string, number>;
  formula_version: string;
  evidence: Record<string, Record<string, unknown>>;
  calculated_at: string;
}

export interface HealthHistoryPoint {
  build_number: number;
  overall_score: number;
  grade: string;
  created_at: string;
}

export interface TrendItem {
  metric: string;
  build_number: number;
  current_value: number;
  previous_value: number | null;
  change_percent: number | null;
  direction: string;
  significance: string;
}

export interface InsightResponse {
  id: string;
  build_id: string;
  priority: string;
  category: string;
  title: string;
  message: string;
  recommendation: string;
  evidence: Record<string, unknown>;
  created_at: string;
}

export interface MetricBundle {
  build: {
    build_number: number;
    status: string;
    duration_ms: number | null;
    compiler_warnings: number;
    compiler_errors: number;
    commit_hash: string | null;
    branch: string | null;
    created_at: string;
  };
  metrics: { binary_size: number | null; artifact_count: number | null };
  code_metrics: {
    lines_of_code: number | null;
    functions: number | null;
    cyclomatic_complexity_total: number | null;
    avg_function_complexity: number | null;
    max_function_complexity: number | null;
    functions_above_threshold: number | null;
    complexity_threshold: number | null;
    maintainability_index: number | null;
    avg_function_length: number | null;
    top_complex_functions: { file: string; function: string; complexity: number }[];
  } | null;
  tests: {
    total: number;
    passed: number;
    failed: number;
    skipped: number;
    pass_rate: number;
    execution_time_ms: number;
    flaky_tests: string[];
    failures: { name: string; message: string | null }[];
    stability: { name: string; status: string; flaky_score: number; executions: number; passes: number; failures: number; skips: number }[];
    missing: boolean;
  };
  benchmarks: {
    name: string;
    current_mean_ms: number | null;
    previous_mean_ms: number | null;
    change_percent: number | null;
    status: string;
    points: { build_number: number; mean_ms: number }[];
  }[];
  dependencies: { count: number };
  architecture: {
    drift_score: number | null;
    layer_violations: number;
    unexpected_coupling: number;
    module_count: number;
    cyclic_dependencies: number;
    direction_violations: number;
    edge_count: number;
    dependency_graph: { nodes: string[]; edges: { source: string; target: string }[] };
  } | null;
  health: {
    overall_score: number;
    grade: string;
    categories: Record<string, number>;
  } | null;
}

export interface BuildHistoryRow {
  build_id: string;
  build_number: number;
  commit: string | null;
  branch: string | null;
  status: string;
  duration_ms: number | null;
  health_score: number | null;
  tests_passed: number;
  tests_total: number;
  warnings: number;
  issues: number;
  created_at: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}