from .evaluation_methods.google_nq_evaluation import GoogleNQEvaluation
from .evaluation_methods.beir_evaluation import BeirEvaluation
from .metrics.recall import Recall
from .metrics.ndcg import NDCG
from .metrics.mrr import MRR
from .metrics.hit import Hit


REGISTRY = {
    "sources": {
        "BeirEvaluation": BeirEvaluation,
        "GoogleNQEvaluation": GoogleNQEvaluation
    },
    "metrics": {
        "Recall": Recall,
        "NDCG": NDCG,
        "MRR": MRR,
        "Hit": Hit
    }
}