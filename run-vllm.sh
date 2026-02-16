vllm serve Qwen/Qwen3-4B-Instruct-2507 \
  --enable-auto-tool-choice \
  --tool-call-parser hermes \
  --api-key helloworld123 \
  --host 0.0.0.0 \
  --port 8000 \
  --gpu-memory-utilization 0.95 \
  --tensor-parallel-size 3 \
  --max-model-len 32768