import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from math import log

Document = Tuple[str, str]
Section = Tuple[str, int, str]  # filename, section_id, text

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
    "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "will", "with"
}


class DocuBot:
    def __init__(self, docs_folder="docs", llm_client=None):
        self.docs_folder = Path(docs_folder)
        self.llm_client = llm_client
        self.documents = self.load_documents()
        self.sections = self.build_sections(self.documents)
        self.index = self.build_index(self.sections)
        self.idf = self.compute_idf(self.sections)

    def __repr__(self):
        return f"<DocuBot docs_folder={self.docs_folder} docs={len(self.documents)} sections={len(self.sections)}>"

    # -----------------------------------------------------------
    # Document Loading
    # -----------------------------------------------------------

    def load_documents(self) -> List[Document]:
        docs = []
        if not self.docs_folder.exists():
            raise FileNotFoundError(f"Docs folder not found: {self.docs_folder}")
        for path in sorted(self.docs_folder.glob("*")):
            if path.is_file() and path.suffix.lower() in {".md", ".txt"}:
                text = path.read_text(encoding="utf8")
                filename = path.name
                docs.append((filename, text))
        return docs

    def tokenize(self, text: str) -> List[str]:
        # Clean text: remove punctuation, lowercase
        cleaned = re.sub(r"[^\w\s]", "", text.lower())
        return [word for word in re.findall(r"\b\w+\b", cleaned) if word not in STOP_WORDS]

    def split_into_sections(self, text: str) -> List[str]:
        parts = re.split(r"\n\s*\n", text)
        return [part.strip() for part in parts if part.strip()]

    def build_sections(self, documents: List[Document]) -> List[Section]:
        sections = []
        for filename, text in documents:
            section_texts = self.split_into_sections(text)
            for section_id, section_text in enumerate(section_texts):
                sections.append((filename, section_id, section_text))
        return sections

    # -----------------------------------------------------------
    # Index Construction
    # -----------------------------------------------------------

    def build_index(self, sections: List[Section]) -> Dict[str, Set[Tuple[str, int]]]:
        index = {}
        for filename, section_id, section_text in sections:
            words = set(self.tokenize(section_text))
            for word in words:
                if word not in index:
                    index[word] = set()
                index[word].add((filename, section_id))
        return index

    def compute_idf(self, sections: List[Section]) -> Dict[str, float]:
        N = len(sections)
        df = {}
        for _, _, section_text in sections:
            words = set(self.tokenize(section_text))
            for word in words:
                df[word] = df.get(word, 0) + 1
        idf = {word: log(N / count) for word, count in df.items()}
        return idf

    # -----------------------------------------------------------
    # Scoring and Retrieval
    # -----------------------------------------------------------

    def score_section(self, query: str, section_text: str) -> float:
        query_words = self.tokenize(query)
        section_words = self.tokenize(section_text)
        tf = {}
        for word in section_words:
            tf[word] = tf.get(word, 0) + 1
        score = 0.0
        for word in query_words:
            if word in tf and word in self.idf:
                score += tf[word] * self.idf[word]
        return score

    def has_useful_context(self, scored_results: List[Tuple[float, str, int, str]], min_score: float = 1.0) -> bool:
        if not scored_results:
            return False
        best_score = scored_results[0][0]
        return best_score >= min_score

    def retrieve(self, query: str, top_k: int = 3) -> List[Tuple[str, str]]:
        if not query.strip():
            return []

        query_words = self.tokenize(query)
        candidate_sections = set()
        for word in query_words:
            candidate_sections.update(self.index.get(word, set()))

        scored_results = []
        for filename, section_id, section_text in self.sections:
            if candidate_sections and (filename, section_id) not in candidate_sections:
                continue
            score = self.score_section(query, section_text)
            if score > 0:
                scored_results.append((score, filename, section_id, section_text))

        scored_results.sort(key=lambda x: x[0], reverse=True)

        if not self.has_useful_context(scored_results):
            return []

        results = []
        for score, filename, section_id, section_text in scored_results[:top_k]:
            results.append((f"{filename} (section {section_id})", section_text))

        return results

    # -----------------------------------------------------------
    # Answering Modes
    # -----------------------------------------------------------

    def answer_retrieval_only(self, query: str, top_k: int = 3) -> str:
        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        formatted = []
        for filename, text in snippets:
            formatted.append(f"[{filename}]\n{text}\n")

        return "\n---\n".join(formatted)

    def answer_rag(self, query: str, top_k: int = 3) -> str:
        if self.llm_client is None:
            raise RuntimeError(
                "RAG mode requires an LLM client. Provide a GeminiClient instance."
            )

        snippets = self.retrieve(query, top_k=top_k)

        if not snippets:
            return "I do not know based on these docs."

        return self.llm_client.answer_from_snippets(query, snippets)

    # -----------------------------------------------------------
    # Bonus Helper
    # -----------------------------------------------------------

    def full_corpus_text(self) -> str:
        return "\n\n".join(text for _, text in self.documents)