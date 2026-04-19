import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from langchain_openai import OpenAIEmbeddings

class PersonaClassifier:
    def __init__(self):
        self.embeddings_model = OpenAIEmbeddings()
        self.centroids = {}
        # Define the Anchors
        self.anchors = {
            "graduate": [
                "admission requirements", "how to apply", "tuition fees", 
                "entrance exams", "open days", "undergraduate programs"
            ],
            "student": [
                "exam schedule", "dormitory registration", "student card", 
                "library hours", "course materials", "scholarship application"
            ],
            "professor": [
                "research grant", "syllabus submission", "faculty meeting", 
                "grading system", "academic publication", "department budget"
            ]
        }

    def initialize_centroids(self):
        """Pre-calculates the group centers once."""
        print("Calculating persona centroids...")
        for label, phrases in self.anchors.items():
            vectors = self.embeddings_model.embed_documents(phrases)
            self.centroids[label] = np.mean(vectors, axis=0)
        print("Persona centroids ready.")

    def determine_persona(self, query: str):
        query_vector = np.array(self.embeddings_model.embed_query(query)).reshape(1, -1)
        
        scores = {}
        for label, centroid in self.centroids.items():
            similarity = cosine_similarity(query_vector, centroid.reshape(1, -1))
            scores[label] = float(similarity[0][0])
        
        best_match = max(scores, key=scores.get)
        # Threshold to avoid random guesses
        if scores[best_match] < 0.70:
            return "unknown"
            
        return best_match