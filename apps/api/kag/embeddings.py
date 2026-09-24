"""Embeddings deterministas para la dimension documental.

TF-IDF + LSA entrenado sobre el corpus y guardado en disco. Es local, no cuesta
tokens y da el mismo vector en cada maquina, que es lo que permite que el
comparativo entre RAG puro y KAG sea reproducible.

Si hay Azure OpenAI configurado, `EMBED_BACKEND=aoai` cambia el proveedor sin
tocar el resto: la unica condicion es que la dimension coincida con la columna
`vector(N)` creada en el esquema.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

import numpy as np

VACIAS = {
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas", "y", "o", "en", "a",
    "que", "se", "del", "al", "por", "con", "para", "su", "sus", "lo", "es", "son",
    "no", "sin", "sobre", "como", "mas", "este", "esta", "estos", "estas", "ha", "han",
    "ser", "fue", "entre", "cuando", "donde", "desde", "hasta", "cada", "tambien",
}


def normalizar(texto: str) -> list[str]:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", (texto or "").lower())
        if unicodedata.category(c) != "Mn"
    )
    return [t for t in re.findall(r"[a-z0-9]+", sin_tildes)
            if len(t) > 2 and t not in VACIAS]


class Embebedor:
    """Proyecta texto a un vector unitario de `dimensiones` componentes."""

    def __init__(self, vocabulario: dict[str, int], idf: np.ndarray,
                 proyeccion: np.ndarray):
        self.vocabulario = vocabulario
        self.idf = idf
        self.proyeccion = proyeccion
        self.dimensiones = int(proyeccion.shape[1])

    # ------------------------------------------------------------ entrenamiento

    @classmethod
    def entrenar(cls, textos: list[str], dimensiones: int = 256) -> "Embebedor":
        corpus = [normalizar(t) for t in textos]
        vocabulario: dict[str, int] = {}
        for tokens in corpus:
            for t in tokens:
                vocabulario.setdefault(t, len(vocabulario))

        n_docs, n_terms = len(corpus), len(vocabulario)
        tf = np.zeros((n_docs, n_terms), dtype=np.float64)
        for i, tokens in enumerate(corpus):
            for t in tokens:
                tf[i, vocabulario[t]] += 1.0
        df = (tf > 0).sum(0)
        idf = np.log((1 + n_docs) / (1 + df)) + 1.0
        tfidf = _unitarias(tf * idf)

        # Se descarta la primera componente: captura el "documento promedio" del
        # corpus y, si se deja, todo se parece a todo y la comparacion miente.
        with np.errstate(all="ignore"):
            _, _, vt = np.linalg.svd(tfidf, full_matrices=False)
        k = min(dimensiones, max(1, vt.shape[0] - 1))
        proyeccion = np.ascontiguousarray(vt[1 : k + 1].T)
        return cls(vocabulario, idf, proyeccion)

    # ------------------------------------------------------------ persistencia

    def guardar(self, destino: Path) -> None:
        destino.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(destino, idf=self.idf, proyeccion=self.proyeccion)
        destino.with_suffix(".vocab.json").write_text(
            json.dumps(self.vocabulario, ensure_ascii=False), "utf-8")

    @classmethod
    def cargar(cls, origen: Path) -> "Embebedor":
        datos = np.load(origen)
        vocab = json.loads(origen.with_suffix(".vocab.json").read_text("utf-8"))
        return cls(vocab, datos["idf"], datos["proyeccion"])

    # ------------------------------------------------------------- inferencia

    def vector(self, texto: str) -> np.ndarray:
        v = np.zeros(len(self.vocabulario), dtype=np.float64)
        for t in normalizar(texto):
            idx = self.vocabulario.get(t)
            if idx is not None:
                v[idx] += 1.0
        v *= self.idf
        norma = float(np.linalg.norm(v))
        if norma > 0:
            v /= norma
        with np.errstate(all="ignore"):
            proyectado = v @ self.proyeccion
        return proyectado / max(float(np.linalg.norm(proyectado)), 1e-12)

    def lote(self, textos: list[str]) -> np.ndarray:
        return np.vstack([self.vector(t) for t in textos]) if textos else np.zeros((0, self.dimensiones))


def _unitarias(m: np.ndarray) -> np.ndarray:
    norma = np.linalg.norm(m, axis=1, keepdims=True)
    return m / np.maximum(norma, 1e-12)


def a_literal(v: np.ndarray) -> str:
    """Formato que pgvector acepta como literal: '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{x:.6f}" for x in np.asarray(v, dtype=float).ravel()) + "]"


def es_nulo(v: np.ndarray) -> bool:
    """Vector sin norma: ningun termino de la consulta esta en el vocabulario.

    Hay que detectarlo antes de llegar a la base: la distancia coseno contra un
    vector de ceros es NaN, y NaN se serializa como `null` en JSON, asi que el
    front recibe una similitud vacia sin ninguna explicacion.
    """
    return not np.any(np.asarray(v, dtype=float))
