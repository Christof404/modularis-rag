from .core.database_evaluator import DatabaseEvaluator
import json

# Configuration
DSN = "postgresql://postgres:@localhost:5432/google_nq"
START = 500
END = 5000
STEP = 500
SPLIT = "validation"
CONFIG_PATH = "pipeline_configs/pipeline_config.json"

if __name__ == "__main__":
    # Load configuration from JSON file
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {CONFIG_PATH}")
        exit(1)
    except json.JSONDecodeError:
        print(f"Error: Failed to decode JSON from {CONFIG_PATH}")
        exit(1)

    evaluator = DatabaseEvaluator()
    evaluator.main(dsn=DSN,
                   start_samples=START,
                   end_samples=END,
                   step=STEP,
                   retrieval_pipeline_json=config,
                   split=SPLIT)
