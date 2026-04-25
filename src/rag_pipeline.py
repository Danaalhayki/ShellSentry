import os
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Optional

from .logger import setup_logger

logger = setup_logger()


@dataclass
class KnowledgeEntry:
    """One retrievable knowledge item used to ground command generation."""

    category: str
    description: str
    command: str

    def to_document(self) -> str:
        """Text used for embedding and semantic retrieval."""
        return (
            f"Category: {self.category}\n"
            f"Description: {self.description}\n"
            f"Command: {self.command}"
        )


class RagPipeline:
    """
    Retrieval pipeline:
    1) embeds the user query
    2) performs vector search over bash knowledge entries
    3) returns top relevant command examples for LLM grounding
    """

    def __init__(
        self,
        cache_size: int = 128,
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.cache_size = cache_size
        self.embedding_model_name = embedding_model
        self._cache: "OrderedDict[str, List[Dict[str, str]]]" = OrderedDict()
        self._cache_lock = threading.Lock()
        self._index_lock = threading.Lock()

        self._model = None
        self._faiss = None
        self._index = None

        self.knowledge_base: List[KnowledgeEntry] = self._build_knowledge_base()
        self._entry_documents = [entry.to_document() for entry in self.knowledge_base]
        self._initialize_index()

    def _build_knowledge_base(self) -> List[KnowledgeEntry]:
        """Static command knowledge base grouped by required categories."""
        return [
            KnowledgeEntry("Network", "show network interface configuration and IP address", "ifconfig"),
            KnowledgeEntry("Network", "show routing table", "netstat -rn"),
            KnowledgeEntry("Operating System", "show detailed memory information", "cat /proc/meminfo"),
            KnowledgeEntry("Operating System", "show disk usage in human-readable format", "df -h"),
            KnowledgeEntry("Operating System", "list running processes for all users", "ps -a"),
            KnowledgeEntry("Operating System", "show operating system and kernel details", "uname -a"),
            KnowledgeEntry(
                "Logs/SSH",
                "show accepted and failed SSH authentication usernames from auth log",
                "cat /var/log/auth.log | grep -E \"Accepted|Failed\" | cut -d ' ' -f 7,9 | sort | uniq",
            ),
            KnowledgeEntry("Logs/SSH", "show SSH daemon service status", "sudo systemctl status sshd"),
            KnowledgeEntry("Logs/SSH", "restart SSH daemon service", "sudo systemctl restart sshd"),
            KnowledgeEntry("Logs/SSH", "show system user accounts", "cat /etc/passwd"),
            KnowledgeEntry("FTP", "list files in FTP session", "ls"),
            KnowledgeEntry("FTP", "restart FTP service", "sudo service ftp restart"),
            KnowledgeEntry("SQL", "restart MySQL service", "sudo service mysql restart"),
            KnowledgeEntry("SQL", "backup a MySQL database to SQL file", "mysqldump -u root -p dbname > backup.sql"),
            KnowledgeEntry("Crontab", "list scheduled cron jobs", "crontab -l"),
            KnowledgeEntry("Service status", "check SSH service status", "sudo service ssh status"),
            KnowledgeEntry("Service status", "check MySQL service status", "sudo service mysql status"),
            KnowledgeEntry("Service status", "check FTP service status", "sudo service ftp status"),
            KnowledgeEntry("Service status", "check vsftp service status", "sudo service vsftp status"),
            KnowledgeEntry("Service status", "check vsftpd service status", "sudo service vsftpd status"),
            KnowledgeEntry("Service status", "check Apache2 service status", "sudo service apache2 status"),
        ]

    def _initialize_index(self):
        """Load embedding model + FAISS and build vector index once."""
        try:
            from sentence_transformers import SentenceTransformer
            import faiss
        except Exception as e:
            logger.error(
                "RAG dependencies missing. Install sentence-transformers and faiss-cpu. Error: %s",
                str(e),
            )
            return

        try:
            self._model = SentenceTransformer(self.embedding_model_name)
            self._faiss = faiss

            embeddings = self._model.encode(
                self._entry_documents,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            index = self._faiss.IndexFlatIP(embeddings.shape[1])
            index.add(embeddings)
            self._index = index
            logger.info("RAG index initialized with %d entries", len(self.knowledge_base))
        except Exception as e:
            logger.error("Failed to initialize RAG index: %s", str(e), exc_info=True)
            self._index = None

    def _get_cached(self, query: str) -> Optional[List[Dict[str, str]]]:
        with self._cache_lock:
            if query not in self._cache:
                return None
            self._cache.move_to_end(query)
            return self._cache[query]

    def _set_cached(self, query: str, result: List[Dict[str, str]]):
        with self._cache_lock:
            self._cache[query] = result
            self._cache.move_to_end(query)
            while len(self._cache) > self.cache_size:
                self._cache.popitem(last=False)

    def retrieve(self, query: str, top_k: int = 3) -> List[Dict[str, str]]:
        """
        Retrieve top relevant knowledge entries for user query.
        Returns dicts containing category, description, command, and similarity score.
        """
        q = (query or "").strip()
        if not q:
            return []

        cached = self._get_cached(q)
        if cached is not None:
            return cached

        if self._model is None or self._index is None or self._faiss is None:
            logger.warning("RAG retrieval skipped: index or model not initialized")
            return []

        safe_k = max(1, min(top_k, len(self.knowledge_base)))

        try:
            query_embedding = self._model.encode(
                [q],
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
            with self._index_lock:
                scores, indices = self._index.search(query_embedding, safe_k)

            results: List[Dict[str, str]] = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < 0 or idx >= len(self.knowledge_base):
                    continue
                entry = self.knowledge_base[idx]
                results.append(
                    {
                        "category": entry.category,
                        "description": entry.description,
                        "command": entry.command,
                        "score": f"{float(score):.4f}",
                    }
                )

            self._set_cached(q, results)
            return results
        except Exception as e:
            logger.error("RAG retrieve failed: %s", str(e), exc_info=True)
            return []

    def format_for_prompt(self, retrieved_entries: List[Dict[str, str]]) -> str:
        """Render retrieval output as compact grounding context for LLM prompt."""
        if not retrieved_entries:
            return ""
        lines = [
            "Grounding examples from trusted Bash knowledge base:",
        ]
        for i, item in enumerate(retrieved_entries, start=1):
            lines.append(
                f"{i}. [{item['category']}] {item['description']} -> {item['command']}"
            )
        return "\n".join(lines)

