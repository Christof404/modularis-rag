<p align="center">
  <img src="static/assets/logo.png" alt="Modularis RAG Logo" width="400">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python Version">
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="License">
  <img src="https://img.shields.io/badge/version-0.1.0-orange.svg" alt="Version">
</p>

<p align="center">
  <b>English</b> | <a href="Readme_de.md">Deutsch</a>
</p>

---

**Modularis RAG** is a highly modular framework for the development, optimization, and evaluation of Retrieval-Augmented Generation (RAG) systems. It enables the seamless combination of diverse ingestion and retrieval strategies through declarative JSON configuration, with a special focus on data cleaning and industrial-grade robustness.

---

### 🗺️ Navigation
*   [📦 Installation](#-installation)
*   [⚡ Quick Start](#-quick-start)
*   [⚙️ Ingestion Pipeline](#️-ingestion-pipeline)
*   [🔍 Retrieval Pipeline](#-retrieval-pipeline)
*   [🛠️ Extensibility & Custom Modules](#️-extensibility--custom-modules)
*   [📊 Evaluation](#-evaluation)
*   [📈 Evaluation Dashboard](#-evaluation-dashboard)
*   [🛤️ Roadmap](#️-roadmap)
*   [⚖️ License](#️-license)

---

### 📦 Installation
Modularis RAG requires Python 3.11+ or higher. The easiest way to start the framework is using Docker, as all database extensions (pgvector, pg_search) and models are pre-configured.

#### Option A: Quick Start with Docker (Recommended)
This method starts PostgreSQL (ParadeDB), Ollama, and a ready-to-use Python environment.

1.  **Prerequisites:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine + Compose) and [Ollama](https://ollama.com/) (optional, if used locally).

2.  **Start Containers:**

    ```bash
    docker-compose -f docker/docker-compose.yml up -d
    ```
    *This will automatically pull the `nomic-embed-text-v2-moe` model (may take several minutes).*
3.  **Enter App Container:**

    ```bash
    docker-compose -f docker/docker-compose.yml exec app bash
    ```
4.  **Run Demo (Ingestion of 10 GoogleNQ documents):**

    ```bash
    python -m rag_pipeline.ingestion.main --config docker/docker_pipeline_config.json
    ```
5.  **Run Demo (Retrieval Test):**

    ```bash
    python -m rag_pipeline.retrieval.main --config docker/docker_retrieval_config.json
    ```

#### Option B: Manual Installation
Use this option if you want to do more than just a quick test of the framework.

1.  **System Requirements (PostgreSQL & Ollama):**
    *   **PostgreSQL:** Version 16+ recommended.
    *   **Extensions:** You must install [pgvector](https://github.com/pgvector/pgvector) and [pg_search](https://github.com/paradedb/paradedb) (ParadeDB).
    *   **Ollama:** Install Ollama from [ollama.com](https://ollama.com).

    *   **Linux (Ubuntu/Debian):**
        ```bash
        # PostgreSQL & pgvector
        sudo apt update && sudo apt install postgresql-16 postgresql-16-pgvector
        # pg_search installation (see paradedb.com for details)
        ```
2.  **Clone the repository:**

    ```bash
    git clone https://github.com/Christof404/modularis-rag
    cd modularis-rag
    ```
3.  **Virtual Environment & Dependencies:**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```


---
### ⚡ Quick Start
The most efficient way to create your own pipelines is using the interactive **Pipeline Builder**. 
Example pipeline JSON configurations can also be found here: [https://ragevaluationvisualizer.fly.dev/](https://ragevaluationvisualizer.fly.dev/).

https://github.com/user-attachments/assets/f4ec4c3d-1ae7-4b5a-b02a-9a53a00a0825

<details>
<summary>Example: Baseline Indexing Pipeline</summary>

```json
{
    "source": {
        "component_name": "GoogleNQSource",
        "params": {
            "num_samples": 5000,
            "split": "validation"
        }
    },
    "converter": {
        "component_name": "HTMLToMarkdownConverter",
        "params": {
            "filters": [
                {
                    "component_name": "UniversalHtmlFilter",
                    "params": {
                        "apply_to": "page_content",
                        "css_selector": ".mw-parser-output"
                    }
                }
            ]
        }
    },
    "filters": [],
    "chunkers": [
        {
            "component_name": "HuggingFaceTokenChunker",
            "params": {
                "model_name": "nomic-ai/nomic-embed-text-v2-moe",
                "chunk_size": 500,
                "chunk_overlap": 50,
                "filters": [],
                "extractors": [],
                "target_content_types": null
            }
        }
    ],
    "embedder": {
        "component_name": "OllamaEmbedder",
        "params": {
            "model_name": "nomic-embed-text-v2-moe",
            "model_dimension": 768,
            "batch_size": 64,
            "prefix_prompt": "search_document:"
        }
    },
    "writer": {
        "component_name": "PostgresWriter",
        "params": {
            "dsn": "postgresql://postgres:@localhost:5432/google_nq",
            "table_name": "baseline_b1",
            "vector_dimension": 768
        }
    }
}
```
</details>

<details>
<summary>Example: Base Retrieval Pipeline</summary>

```json
{
    "embedder": {
        "component_name": "OllamaEmbedder",
        "params": {
            "model_name": "nomic-embed-text-v2-moe",
            "model_dimension": 768,
            "max_tokens": 512,
            "batch_size": 64,
            "prefix_prompt": "search_query:"
        }
    },
    "retriever": {
        "component_name": "PostgresVectorRetriever",
        "params": {
            "dsn": "postgresql://postgres:@localhost:5432/google_nq",
            "table_name": "baseline_b1"
        }
    },
    "pre_filters": [],
    "reranker": {
        "component_name": "CrossEncoderReranker",
        "params": {
            "model_name": "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "max_length": 512
        }
    },
    "post_filters": [
        {
            "component_name": "TopKFilter",
            "params": {
                "top_k": 10
            }
        }
    ],
    "context_builder": {
        "component_name": "GroupedContextBuilder",
        "params": {
            "max_chars": 12000
        }
    },
    "formatter": {
        "component_name": "DefaultResponseFormatter",
        "params": {}
    }
}
```
</details>

#### Creating Pipelines
Run the respective `main_builder` script to be guided step-by-step through the configuration.

*   **Create Ingestion Pipeline:**

    ```bash
    python -m rag_pipeline.ingestion.main_builder --config_save_path "pipeline_config.json"
    ```
*   **Create Retrieval Pipeline:**

    ```bash
    python -m rag_pipeline.retrieval.main_builder --config_save_path "pipeline_config.json"
    ```

#### Starting a Pipeline
Start the desired pipeline by specifying the path to the previously generated JSON configuration.

*   **Run Ingestion Pipeline:**

    ```bash
    python -m rag_pipeline.ingestion.main --config "pipeline_config.json"
    ```
*   **Run Retrieval Pipeline:**

    ```bash
    python -m rag_pipeline.retrieval.main --config "pipeline_config.json"
    ```

---

### ⚙️ Ingestion Pipeline
The framework offers two approaches: 
- Declarative usage via JSON (recommended for reproducibility) or
- Direct programmatic integration of the classes.

#### 1. How it works
Clean indexing of data is essential for subsequent retrieval quality. It is crucial to separate data structurally and precisely to minimize context breaks and noise from irrelevant information. Since datasets, especially in corporate environments, vary greatly, the framework does not offer a rigid universal solution, but rather modular building blocks.

#### 2. Configuration of the JSON Schema
By running the `main_builder.py` module, the pipeline can be configured interactively. The structure follows a standardized process but remains maximally flexible due to interchangeable modules.

```bash
python -m rag_pipeline.ingestion.main_builder
```

The terminal assistant guides you through the following indexing workflow:

```mermaid
flowchart TD
    A[Data Source] --> B[Filtering]
    B --> C[Extraction]
    C --> D[Chunking]
    D --> E[Embedding]
    E --> F[Destination]
```

**Best Practice:** Identical input data should flow into the same database. This facilitates the subsequent evaluation of different indexing methods. 
Each strategy (pipeline) receives its own table in the database (e.g., `baseline_b1`), which is automatically created or expanded. Ensure that the database user has the necessary rights to create tables. 
This allows different strategies to be evaluated independently and the most performant solution for the given data to be identified.

#### 3. Video Guide: Pipeline Creation

https://github.com/user-attachments/assets/cff0c3be-987b-4902-b5a7-d6128dffd3c3

#### 4. Programmatic Usage (JSON)
The generated JSON schema can be loaded and executed directly in Python:

```python
from rag_pipeline.ingestion.pipeline import IngestPipeline
from rag_pipeline.core.registry import ComponentRegistry
from rag_pipeline.ingestion.registry import REGISTRY
from rag_pipeline.core.factory import Factory
import json

with open("pipeline_config.json", "r") as f:
    config_dict = json.load(f)
    
registry = ComponentRegistry(REGISTRY)
ingest_factory = Factory(registry)
components_dict = {key: ingest_factory.instantiate_from_config(val) for key, val in config_dict.items()}

pipeline = IngestPipeline(**components_dict)
pipeline.run()
```

#### 5. Execution via CLI

```bash
python -m rag_pipeline.ingestion.main --config "pipeline_config.json"
```

During execution, the performance of each step is measured, the workflow is visualized graphically, and progress is displayed.

```text
╭───────────────────────────────────────────  Pipeline Setup: pipeline_config.json ───────────────────────────────────────────╮
│                                                      Pipeline Workflow                                                      │
│ ┏━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓ │
│ ┃   # ┃ Type           ┃ Component               ┃ Description                                                            ┃ │
│ ┡━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩ │
│ │   1 │ Source         │ GoogleNQSource          │ -                                                                      │ │
│ │   2 │ Converter      │ HTMLToMarkdownConverter │ -                                                                      │ │
│ │   3 │ └── Filter     │ UniversalHtmlFilter     │ Extracts first HTML element matching CSS selector: '.mw-parser-output' │ │
│ │   4 │ Chunker        │ HuggingFaceTokenChunker │ -                                                                      │ │
│ │   5 │ Embedder       │ OllamaEmbedder          │ -                                                                      │ │
│ │   6 │ DatabaseWriter │ PostgresWriter          │ -                                                                      │ │
│ └─────┴────────────────┴─────────────────────────┴────────────────────────────────────────────────────────────────────────┘ │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

Run...
⠇ Processed: 5000 items | Current: Continent | 0.45 doc/s | 3:06:47

==================================================
PIPELINE PERFORMANCE REPORT
==================================================

[Converter]
  HTMLToMarkdownConverter: 1549.37s total | 5000 calls | ~309.87ms/call

[Chunker]
  HuggingFaceTokenChunker: 1602.49s total | 5000 calls | ~320.50ms/call

[Embedder]
  OllamaEmbedder: 6531.90s total | 4998 calls | ~1306.90ms/call

[DatabaseWriter]
  PostgresWriter: 1410.76s total | 4998 calls | ~282.26ms/call

[Pipeline]
  Total_Run: 11207.11s total | 1 calls | ~11207107.73ms/call
==================================================
```

Detailed time measurements allow bottlenecks to be precisely identified. Aborting with **CTRL+C** is possible at any time. 
Current progress is persisted, so processing resumes seamlessly at the next start.

---

### 🔍 Retrieval Pipeline
The Retrieval Pipeline is equally modularly structured to achieve the best performance based on the indexed data. The following example shows a simple vector search. Hybrid approaches (e.g., BM25 combined with vector search) are also possible.

#### 1. Configuration
As with ingestion, the pipeline is configured here via the Builder. This configuration can later also be used by LLM agents to perform targeted searches in vector databases.

#### 2. Creation of the JSON Schema

```bash
python -m rag_pipeline.retrieval.main_builder
```

The terminal assistant guides you step-by-step through the construction of the retrieval pipeline:

```mermaid
flowchart TD
    A[Embedder] --> B[Retriever]
    B --> C[Pre-Filters]
    C --> D[Reranker]
    D --> E[Post-Filters]
    E --> F[Context Builder]
    F --> G[Formatter]
```

#### 3. Video Guide: Retrieval Creation

https://github.com/user-attachments/assets/f2a15289-eb16-4b53-a577-c852810bc0bc

#### 4. Programmatic Usage (JSON)
Integration of the retrieval configuration in Python:

```python
from rag_pipeline.retrieval.pipeline import RetrievalPipeline
from rag_pipeline.core.registry import ComponentRegistry
from rag_pipeline.retrieval.registry import REGISTRY
from rag_pipeline.core.factory import Factory
import json

with open("pipeline_config.json", "r", encoding="utf-8") as f:
    config_dict = json.load(f)
    
registry = ComponentRegistry(REGISTRY)
retrieval_factory = Factory(registry)
components_dict = {key: retrieval_factory.instantiate_from_config(val) for key, val in config_dict.items()}

pipeline = RetrievalPipeline(**components_dict)

query = input("Enter search query: ")
final_response, context_blocks, plain_chunks = pipeline.run(query_text=query, filters_dict={})
print(f"Final response:\n {final_response}")
```

#### 5. Execution via CLI
Starting the retrieval pipeline with integrated performance analysis:

```bash
python -m rag_pipeline.retrieval.main --config "pipeline_config.json"
```

**Example Output:**

```text
Load pipeline setup: pipeline_config.json...
Enter search query: Which company produced the high school musical?

Final response:
 --- GEFUNDENER KONTEXT ---

QUELLE [1]: High School Musical 3: Senior Year
--- QUELLE: High School Musical 3: Senior Year ---
***High School Musical 3: Senior Year*** is a 2008 American [musical film](/wiki/Musical_film "Musical film") and is the third installment in the [*High School Musical* trilogy](/wiki/High_School_Musical_(film_series) "High School Musical (film series)"). Produced and released on October 24, 2008, by [Walt Disney Pictures](/wiki/Walt_Disney_Pictures "Walt Disney Pictures"), the film is a sequel to [Disney Channel Original Movie](/wiki/List_of_Disney_Channel_original_films "List of Disney Channel original films") 2006 television film *[High School Musical](/wiki/High_School_Musical "High School Musical")*. It was the only film in the series to be released theatrically. [Kenny Ortega](/wiki/Kenny_Ortega "Kenny Ortega") returned as director and choreographer, as did all six primary actors.

The sequel follows the main six high school seniors: Troy, Gabriella, Ryan, Sharpay, Chad, and Taylor as they are faced with the challenging prospect of being separated after graduating from high school. Joined by the rest of their East High Wildcat classmates, they stage an elaborate spring musical reflecting their experiences, hopes, and fears about the future.

The film received mixed reviews, though relatively better than the first installment of the series, and, in its first three days of release, *Senior Year* grossed $50 million in North America and an additional $40 million overseas, setting a new record for the largest opening weekend for a musical film.
[...]
--------------------------------------------------

QUELLE [2]: High School Musical 2
--- QUELLE: High School Musical 2 ---
[Pacific Repertory Theatre](/wiki/Pacific_Repertory_Theatre "Pacific Repertory Theatre")'s School of Dramatic Arts *High School Musical* Act 1 Finale.

Like the original *[High School Musical](/wiki/High_School_Musical "High School Musical")*, the sequel has been adapted into two different theatrical productions: a one-act, 70-minute version and a two-act full-length production. This stage production includes the song "Hummuhummunukunukuapua'a" that was left out of the original movie but included in the DVD. Through [Music Theater International](/wiki/Music_Theater_International "Music Theater International"), Disney Theatrical began licensing the theatrical rights in October 2008. MTI had originally recruited 7 schools to serve as tests for the new full-length adaptation, but due to complications with multiple drafts of both the script and the score, all but two schools were forced to drop out of the pilot program.

- On May 18, 2008, Woodlands High School became the first school to produce High School Musical 2.
- From July 17-August 3, 2008, Harrell Theatre, in Collierville, Tennessee, was the first community theatre to perform the production, which featured both a senior cast and a junior cast.
- From January 15 - February 15, 2009, the West Coast premiere production was presented by [Pacific Repertory Theatre](/wiki/Pacific_Repertory_Theatre "Pacific Repertory Theatre")'s School of Dramatic Arts. The production was directed by PacRep founder[Stephen Moorer](/wiki/Stephen_Moorer "Stephen Moorer"), who previously directed the California premiere of the first High School Musical.[[17]](#cite_note-17)
- From 6–18 April 2009, the UK Premiere was performed by StageDaze Theatre Company in [Cardiff](/wiki/Cardiff "Cardiff").[[18]](#cite_note-18)

...
--------------------------------------------------



==================================================
PIPELINE PERFORMANCE REPORT
==================================================

[Embedder]
  OllamaEmbedder: 0.16s total | 1 calls | ~161.11ms/call

[Retriever]
  PostgresVectorRetriever: 0.02s total | 1 calls | ~21.46ms/call

[Reranker]
  CrossEncoderReranker: 0.23s total | 1 calls | ~230.87ms/call

[Filter]
  TopKFilter: 0.00s total | 1 calls | ~0.01ms/call

[ContextBuilder]
  GroupedContextBuilder: 0.00s total | 1 calls | ~0.06ms/call

[Formatter]
  DefaultResponseFormatter: 0.00s total | 1 calls | ~0.01ms/call

[RetrievalPipeline]
  Total_Run: 0.41s total | 1 calls | ~413.78ms/call
==================================================
```

In this example, the response contains the first two chunks found (from originally top-10 results). The correct answer is already contained in the first hit, as the Wikipedia article on "High School Musical" is part of the 5000 indexed documents of the GoogleNQ dataset.

---

### 🛠️ Extensibility & Custom Modules
Modularis RAG is designed to be easily extended. Each component of the pipeline is based on clearly defined interfaces. 
Custom modules can be added by implementing the base classes in `rag_pipeline/ingestion/interfaces.py` or `rag_pipeline/retrieval/interfaces.py`.

#### Example: Custom Ingestion Filter
Suppose you want to create a filter that removes specific keywords from the text:

```python
from rag_pipeline.ingestion.interfaces import BaseFilter
from typing import Optional

class WordBlacklistFilter(BaseFilter):
    def __init__(self, blacklist: list[str], **kwargs):
        super().__init__(**kwargs)
        self.blacklist = blacklist

    def process_text(self, text_content: str) -> Optional[str]:
        for word in self.blacklist:
            text_content = text_content.replace(word, "[REDACTED]")
        return text_content
```

#### Integration into the Framework
To use the new module in the framework (e.g., in the `main_builder`), it simply needs to be registered in the appropriate registry:

1.  **Ingestion:** Add the new class in `rag_pipeline/ingestion/registry.py`.
2.  **Retrieval:** Add the new class in `rag_pipeline/retrieval/registry.py`.

The module will then be immediately available for selection and can be controlled via the JSON configuration.

---

### 📊 Evaluation
The evaluation serves to determine the optimal overall strategy for the given data. It helps in deciding whether computationally intensive chunking methods are worth it compared to simple procedures (e.g., Character Chunking).

#### 1. Procedure
After testing various indexing strategies, multiple tables are usually available. The evaluation module tests the most important parameters efficiently as the number of documents increases. Measured are: **Recall, Hit Rate, MRR**, and **nDCG** (each at @1, @3, @5, and @10).

*   **Hit@K:** Is the correct document contained in the top-K results?
*   **MRR (Mean Reciprocal Rank):** At which position is the first relevant document?
*   **nDCG (Normalized Discounted Cumulative Gain):** Evaluates the quality of the ranking order.
*   **Recall@K:** What proportion of all relevant documents was identified?

#### 2. Base Evaluation (CLI)
The most convenient way to start an evaluation is via the interactive terminal assistant. It guides you through the selection of the dataset, the pipeline configuration, and the metrics to be evaluated.

```bash
python -m evaluation.main
```

**Video Guide: Starting Evaluation**

https://github.com/user-attachments/assets/bd0a26b2-5213-48c0-9a27-08efc924acb2

**Example Output:**

```text
╭─────────────────────────╮
│ RAG Pipeline Evaluation │
╰─────────────────────────╯
? Select evaluation source (dataset): GoogleNQEvaluation
? Select retrieval pipeline config: /home/christof/scratch/tests/rag/src/rag-database/evaluation/pipeline_config.json
? Start num_test_samples: 1000
? End num_test_samples: 5000
? Step size: 1000
? Select metrics to evaluate: done (4 selections)
Loading weights: 100%|███████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 105/105 [00:00<00:00, 4379.06it/s]
BertForSequenceClassification LOAD REPORT from: cross-encoder/ms-marco-MiniLM-L-6-v2
Key                          | Status     | Details
-----------------------------+------------+--------
bert.embeddings.position_ids | UNEXPECTED |        

Notes:
- UNEXPECTED    :can be ignored when loading from different task/architecture; not ok if you expect identical arch.
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
? Use only required docs (limit DB size to match current samples)? No
? Enter value for 'split' [str]: validation

Starting evaluation scaling for GoogleNQEvaluation...
⠋ Overall Evaluation Progress ━━╺━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━   6% 0:41:11
```

#### 3. Batch Evaluation (Script-based)
Alternatively, the evaluation can be started via a script. This is particularly useful for evaluating an entire database at once, rather than just a single table.
Configure the parameters in `evaluation/run_batch_evaluation.py`:

```python
# Configuration
DSN = "postgresql://postgres:@localhost:5432/google_nq"

START = 500
END = 5000
STEP = 500

SPLIT = "validation"
use_only_required_docs = False
CONFIG_PATH = "pipeline_configs/pipeline_config.json"
```

Through `START`, `END`, and `STEP`, it is measured how the retrieval quality scales with a growing corpus. Start the process with:

```bash
python -m evaluation.run_batch_evaluation 
```

#### 4. Results
Results are output in Markdown format, supplemented by visualizations using Matplotlib.

**Example results of the Baseline pipeline:**

```markdown
# Scaling Evaluation Results (Document Level)
| Samples | Recall@1 | Recall@3 | Recall@5 | Recall@10 | Ndcg@1 | Ndcg@3 | Ndcg@5 | Ndcg@10 | Mrr@1 | Mrr@3 | Mrr@5 | Mrr@10 | Hit_Rate@1 | Hit_Rate@3 | Hit_Rate@5 | Hit_Rate@10 | Global Recall |
|---------|----------|----------|----------|-----------|--------|--------|--------|---------|-------|-------|-------|--------|------------|------------|------------|-------------|---------------|
| 500     | 0.634    | 0.762    | 0.784    | 0.792     | 0.634  | 0.711  | 0.720  | 0.723   | 0.634 | 0.693 | 0.698 | 0.699  | 0.634      | 0.762      | 0.784      | 0.792       | 0.792         |
| 1000    | 0.612    | 0.758    | 0.785    | 0.792     | 0.612  | 0.699  | 0.710  | 0.712   | 0.612 | 0.678 | 0.684 | 0.685  | 0.612      | 0.758      | 0.785      | 0.792       | 0.792         |
| 1500    | 0.615    | 0.763    | 0.787    | 0.798     | 0.615  | 0.703  | 0.713  | 0.717   | 0.615 | 0.682 | 0.688 | 0.690  | 0.615      | 0.763      | 0.787      | 0.798       | 0.798         |
| 2000    | 0.617    | 0.767    | 0.792    | 0.802     | 0.617  | 0.706  | 0.717  | 0.720   | 0.617 | 0.685 | 0.691 | 0.692  | 0.617      | 0.767      | 0.792      | 0.802       | 0.802         |
| 2500    | 0.612    | 0.765    | 0.794    | 0.803     | 0.612  | 0.703  | 0.715  | 0.718   | 0.612 | 0.682 | 0.689 | 0.690  | 0.612      | 0.765      | 0.794      | 0.803       | 0.803         |
| 3000    | 0.616    | 0.772    | 0.800    | 0.809     | 0.616  | 0.709  | 0.720  | 0.723   | 0.616 | 0.687 | 0.693 | 0.695  | 0.616      | 0.772      | 0.800      | 0.809       | 0.809         |
| 3500    | 0.623    | 0.777    | 0.805    | 0.814     | 0.623  | 0.715  | 0.726  | 0.729   | 0.623 | 0.693 | 0.699 | 0.701  | 0.623      | 0.777      | 0.805      | 0.814       | 0.814         |
| 4000    | 0.624    | 0.779    | 0.806    | 0.816     | 0.624  | 0.716  | 0.728  | 0.731   | 0.624 | 0.695 | 0.701 | 0.702  | 0.624      | 0.779      | 0.806      | 0.816       | 0.816         |
| 4500    | 0.628    | 0.783    | 0.810    | 0.819     | 0.628  | 0.721  | 0.732  | 0.735   | 0.628 | 0.699 | 0.705 | 0.706  | 0.628      | 0.783      | 0.810      | 0.819       | 0.819         |
| 5000    | 0.630    | 0.781    | 0.807    | 0.817     | 0.630  | 0.720  | 0.731  | 0.734   | 0.630 | 0.699 | 0.705 | 0.706  | 0.630      | 0.781      | 0.807      | 0.817       | 0.817         |


## Sample Retrieval Failures (Error Analysis)
| Question                                                         | Expected IDs (Target)                                                                                                                     | Top Retrieved (Mistake)                              |
|------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------|
| what is the lowest recorded temperature on mount vinson          | https://en.wikipedia.org//w/index.php?title=Vinson_Massif&amp;oldid=836064305                                                             | Philadelphia                                         |
| where did the idea of fortnite come from                         | https://en.wikipedia.org//w/index.php?title=Fortnite&amp;oldid=838517375                                                                  | War of 1812                                          |
| what are the requirements of passing national senior certificate | https://en.wikipedia.org//w/index.php?title=National_Senior_Certificate&amp;oldid=837110357                                               | List of best-selling music artists                   |
| what does hp mean in war and order                               | https://en.wikipedia.org//w/index.php?title=Health_(gaming)&amp;oldid=819315199                                                           | Events leading to the attack on Pearl Harbor         |
| my first love was a castle in the sky                            | https://en.wikipedia.org//w/index.php?title=Sukiyaki_(song)&amp;oldid=838347990                                                           | Windsor Castle                                       |
| what happens to the rbc in acute hemolytic reaction              | https://en.wikipedia.org//w/index.php?title=Acute_hemolytic_transfusion_reaction&amp;oldid=821817747                                      | List of Orange Is the New Black characters           |
| where does the saying like a boss come from                      | https://en.wikipedia.org//w/index.php?title=Like_a_Boss&amp;oldid=816720124                                                               | Knocking on wood                                     |
| who was the first lady nominated member of the rajya sabha       | https://en.wikipedia.org//w/index.php?title=List_of_nominated_members_of_Rajya_Sabha&amp;oldid=818220921                                  | First Lady of the United States                      |
| when was the last time the world series went less than 7 games   | https://en.wikipedia.org//w/index.php?title=Game_seven&amp;oldid=813197908                                                                | World Series                                         |
| who has played for the most nba teams                            | https://en.wikipedia.org//w/index.php?title=List_of_NBA_players_who_have_spent_their_entire_career_with_one_franchise&amp;oldid=806218522 | Golden State Warriors                                |
| bond villain has a good head for numbers                         | https://en.wikipedia.org//w/index.php?title=List_of_James_Bond_villains&amp;oldid=799071896                                               | Law & Order: Special Victims Unit (season 18)        |
| where is the tv show the curse of oak island filmed              | https://en.wikipedia.org//w/index.php?title=The_Curse_of_Oak_Island&amp;oldid=832882458                                                   | I'm a Celebrity...Get Me Out of Here! (UK TV series) |
| where is gall bladder situated in human body                     | https://en.wikipedia.org//w/index.php?title=Gallbladder&amp;oldid=821194740                                                               | Dead Sea                                             |
| youtube phil collins don't lose my number                        | https://en.wikipedia.org//w/index.php?title=Don%27t_Lose_My_Number&amp;oldid=833447176                                                    | List of most-viewed YouTube videos                   |
| how much is john incredible pizza to get in                      | https://en.wikipedia.org//w/index.php?title=John%27s_Incredible_Pizza_Company&amp;oldid=832318419                                         | Ready Player One (film)                              |
| who plays nikki in need for speed carbon                         | https://en.wikipedia.org//w/index.php?title=Emmanuelle_Vaugier&amp;oldid=836763004                                                        | Wizards of Waverly Place (season 4)                  |
| where was the music video what ifs filmed                        | https://en.wikipedia.org//w/index.php?title=What_Ifs&amp;oldid=838232791                                                                  | 3's & 7's                                            |
| horatio spafford story it is well with my soul                   | https://en.wikipedia.org//w/index.php?title=Horatio_Spafford&amp;oldid=834430243                                                          | It's My Party (Lesley Gore song)                     |
| who played in the movie harper valley pta                        | https://en.wikipedia.org//w/index.php?title=Harper_Valley_PTA_(film)&amp;oldid=818590841                                                  | The Dumping Ground (series 5)                        |
| in which sea pearl is found in india                             | https://en.wikipedia.org//w/index.php?title=Pearl&amp;oldid=835416381                                                                     | Indian Ocean                                         |


## Visual Analysis: Metrics Scaling

![scaling_plot_baseline_example.png](static/assets/doc/imgs/scaling_plot_baseline_example.png)

## Pipeline Performance Report (Timings)
```text
==================================================
PIPELINE PERFORMANCE REPORT
==================================================

[Embedder]
  OllamaEmbedder: 887.11s total | 5000 calls | ~177.42ms/call

[Retriever]
  PostgresVectorRetriever: 1082.24s total | 5000 calls | ~216.45ms/call

[Reranker]
  CrossEncoderReranker: 4257.95s total | 5000 calls | ~851.59ms/call

[Filter]
  TopKFilter: 0.06s total | 5000 calls | ~0.01ms/call

[RetrievalPipeline]
  Total_Run: 6228.58s total | 5000 calls | ~1245.72ms/call
==================================================
```

---

### 📈 Evaluation Dashboard
To test the framework and known strategies, a total of 22 indexing pipelines, each with 5000 documents from the GoogleNQ dataset, were imported. 
Each corpus was tested with 12 different retrieval strategies. The resulting 440 independent evaluation results highlight the strengths and weaknesses of the respective approaches. 
The dashboard allows for an efficient comparison of these strategies.

**Link to Dashboard:** [https://ragevaluationvisualizer.fly.dev/](https://ragevaluationvisualizer.fly.dev/)

https://github.com/user-attachments/assets/67890dbd-a00b-41d5-953a-e63bd1a3f94a

---

### 🛤️ Roadmap
The framework is continuously being expanded:
*   **Python Package:** A dedicated Python package (`modularis-rag`) will be released soon to ensure seamless integration and even easier installation.
*   **vLLM Integration:** Support for batch processing for highly efficient LLM-based RAG strategies.
*   **Auto-Tuning:** Automatic search for optimal hyperparameters (chunk size, top-K) based on evaluation metrics.

---

### ⚖️ License
This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

---

### 🌟 Citation
If you use ModularisRag in your research or project, please cite it using the following BibTeX:

```bibtex
@software{haidegger2026modularisrag,
  author = {Haidegger, Christof},
  title = {ModularisRag: A Comprehensive Python Toolkit for Indexing, Retrieval and Retrieval-Augmented Generation},
  year = {2026},
  url = {[https://github.com/Christof404/modularis-rag](https://github.com/Christof404/modularis-rag)},
  version = {0.1.0}
}
```
