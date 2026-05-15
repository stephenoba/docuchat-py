from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR

# Collect default metrics (process, platform, gc)
# These are already in the default REGISTRY, so we'll use that as our registry

# Counter: total number of HTTP requests
HTTP_REQUESTS_TOTAL = Counter(
    'docuchat_http_requests_total',
    'Total HTTP requests',
    ['method', 'path', 'status_code']
)

# Histogram: request duration distribution
HTTP_REQUEST_DURATION = Histogram(
    'docuchat_http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'path'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10]
)

# Counter: document processing results
DOCUMENTS_PROCESSED = Counter(
    'docuchat_documents_processed_total',
    'Documents processed by the queue worker',
    ['status']  # 'success' or 'failed'
)

# Gauge: active queue jobs
ACTIVE_QUEUE_JOBS = Gauge(
    'docuchat_active_queue_jobs',
    'Currently active queue jobs',
    ['queue']
)

# Counter: cache hits and misses
CACHE_OPERATIONS = Counter(
    'docuchat_cache_operations_total',
    'Cache operations',
    ['operation', 'result']  # get/set, hit/miss
)

# Export the registry for the /metrics endpoint
METRICS_REGISTRY = REGISTRY
