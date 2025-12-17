import sys
import os
import json
import torch
from sentence_transformers import SentenceTransformer, util

# ---------------- CONFIG ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CACHE_DIR = os.path.join(BASE_DIR, "model_cache")
MITRE_FILE = os.path.join(BASE_DIR, "mitre_techniques.json")
SIMILARITY_THRESHOLD = 0.55


os.makedirs(CACHE_DIR, exist_ok=True)

# ---------------- LOAD MODEL ----------------
embedder = SentenceTransformer(
    "ibm-research/CTI-BERT",
    cache_folder=CACHE_DIR
)

# ---------------- LOAD MITRE TECHNIQUES ----------------
with open(MITRE_FILE, "r", encoding="utf-8") as f:
    techniques = json.load(f)

tech_ids = [t["id"] for t in techniques]
tech_names = [t["name"] for t in techniques]
tech_texts = [t["description"] for t in techniques]
tech_tactic_ids = [t.get("tacticId", "Unknown") for t in techniques]
tech_tactic_names = [t.get("tacticName", "Unknown") for t in techniques]

# ---------------- PRECOMPUTE EMBEDDINGS ----------------
tech_embeddings = embedder.encode(
    tech_texts,
    convert_to_tensor=True,
    normalize_embeddings=True
)

# ---------------- PIPELINE ----------------
TOP_K = 3

def run_pipeline(text: str):
    query_emb = embedder.encode(
        text,
        convert_to_tensor=True,
        normalize_embeddings=True
    )

    # Use util.cos_sim which handles shapes correctly (returns 1xN matrix)
    sims = util.cos_sim(query_emb, tech_embeddings)[0]
    
    # Ensure k is not larger than available techniques
    k = min(TOP_K, len(sims))
    top_scores, top_indices = torch.topk(sims, k=k)

    techniques = []

    for score, idx in zip(top_scores, top_indices):
        score = float(score)
        if score >= SIMILARITY_THRESHOLD:
            techniques.append({
                "id": tech_ids[int(idx)],
                "name": tech_names[int(idx)],
                "confidence": round(score, 4),
                "description": tech_texts[int(idx)],
                "tacticId": tech_tactic_ids[int(idx)],
                "tacticName": tech_tactic_names[int(idx)]
            })

    if not techniques:
        return {
            "status": "no_match",
            "techniques": []
        }

    return {
        "status": "ok",
        "techniques": techniques
    }


# ---------------- ENTRY POINT ----------------
if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else ""
    result = run_pipeline(query)
    print(json.dumps(result))
