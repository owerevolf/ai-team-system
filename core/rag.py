"""
RAG - Retrieval Augmented Generation
Агенты ищут документацию и шаблоны перед генерацией кода
"""

import json
import math
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Document:
    id: str
    title: str
    content: str
    tags: List[str] = field(default_factory=list)
    source: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "tags": self.tags,
            "source": self.source
        }


class SimpleVectorStore:
    """Простая векторная БД на основе TF-IDF"""
    
    def __init__(self):
        self.documents: List[Document] = []
        self.index: Dict[str, Dict[str, float]] = {}
    
    def add(self, doc: Document):
        """Добавление документа"""
        self.documents.append(doc)
        self.index[doc.id] = self._tfidf(doc.content)
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[Document, float]]:
        """Поиск релевантных документов"""
        query_vec = self._tfidf(query)
        
        scores = []
        for doc in self.documents:
            doc_vec = self.index.get(doc.id, {})
            score = self._cosine_similarity(query_vec, doc_vec)
            scores.append((doc, score))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
    
    def _tfidf(self, text: str) -> Dict[str, float]:
        """Простой TF-IDF"""
        words = text.lower().split()
        word_count = {}
        for w in words:
            if len(w) > 2:
                word_count[w] = word_count.get(w, 0) + 1
        
        total = len(words)
        return {w: c / total for w, c in word_count.items()}
    
    def _cosine_similarity(self, vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
        """Косинусное сходство"""
        common_keys = set(vec1.keys()) & set(vec2.keys())
        if not common_keys:
            return 0.0
        
        dot = sum(vec1[k] * vec2[k] for k in common_keys)
        norm1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        norm2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot / (norm1 * norm2)
    
    def save(self, path: Path):
        """Сохранение индекса"""
        data = {
            "documents": [d.to_dict() for d in self.documents],
            "index": self.index
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    
    def load(self, path: Path):
        """Загрузка индекса"""
        if not path.exists():
            return
        
        data = json.loads(path.read_text())
        self.documents = [Document(**d) for d in data["documents"]]
        self.index = data["index"]
    
    def __len__(self):
        return len(self.documents)


class RAGSystem:
    def __init__(self, store_path: Optional[Path] = None):
        if store_path is None:
            store_path = Path.home() / ".ai_team" / "rag_store.json"
        
        self.store_path = store_path
        self.store = SimpleVectorStore()
        self.store.load(store_path)
        
        self._load_templates()
    
    def _load_templates(self):
        """Загрузка шаблонов из templates/"""
        templates_dir = Path(__file__).parent.parent / "templates" / "requirements_examples"
        if not templates_dir.exists():
            return
        
        for template_file in templates_dir.glob("*.md"):
            doc_id = f"template_{template_file.stem}"
            if not any(d.id == doc_id for d in self.store.documents):
                content = template_file.read_text()
                self.store.add(Document(
                    id=doc_id,
                    title=template_file.stem,
                    content=content,
                    tags=["template", "requirements"],
                    source=str(template_file)
                ))
        
        self.store.save(self.store_path)
    
    def search(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Поиск релевантной информации"""
        results = self.store.search(query, top_k)
        
        return [
            {
                "title": doc.title,
                "content": doc.content[:500],
                "score": round(score, 3),
                "tags": doc.tags,
                "source": doc.source
            }
            for doc, score in results
        ]
    
    def get_context(self, query: str, requirements: str) -> str:
        """Получить контекст для генерации"""
        results = self.search(query, top_k=2)
        
        if not results:
            return ""
        
        context = "Релевантные шаблоны и документация:\n\n"
        for i, r in enumerate(results, 1):
            context += f"### {i}. {r['title']} (score: {r['score']})\n"
            context += f"Теги: {', '.join(r['tags'])}\n"
            context += f"```\n{r['content'][:300]}\n```\n\n"
        
        return context
    
    def add_document(self, doc: Document):
        """Добавление документа"""
        self.store.add(doc)
        self.store.save(self.store_path)
    
    def stats(self) -> Dict[str, Any]:
        """Статистика"""
        tags = {}
        for doc in self.store.documents:
            for tag in doc.tags:
                tags[tag] = tags.get(tag, 0) + 1
        
        return {
            "total_documents": len(self.store.documents),
            "tags": tags,
            "store_path": str(self.store_path)
        }
