# embeds vault notes into an in-memory vector index and finds the most semantically
# similar notes to a question; the only module that touches chromadb/sentence-transformers

import chromadb
from sentence_transformers import SentenceTransformer
from second_brain.config import OBSIDIAN_VAULT_PATH, EMBEDDING_MODEL_NAME, VAULT_COLLECTION_NAME
from second_brain.types import NoteMatch
from second_brain.vault.vault_reader import list_note_files, read_note_content, get_note_title

COSINE_SPACE_METADATA = {"hnsw:space": "cosine"}

_embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)


def _build_vault_collection():
    # reads every note in the vault and embeds it into a fresh in-memory chroma collection;
    # uses get_or_create + an explicit clear (rather than create_collection) because chromadb
    # shares its in-process store across client instances with the same default settings, so a
    # second build within one process (e.g. a future long-running MCP server) would otherwise
    # hit "collection already exists" and serve stale entries from the previous build
    chroma_client = chromadb.EphemeralClient()
    vault_collection = chroma_client.get_or_create_collection(VAULT_COLLECTION_NAME, metadata=COSINE_SPACE_METADATA)
    existing_entries = vault_collection.get()
    existing_ids = existing_entries["ids"]

    if len(existing_ids) > 0:
        vault_collection.delete(ids=existing_ids)

    all_note_file_paths = list_note_files(OBSIDIAN_VAULT_PATH)

    note_ids = []
    note_contents = []
    note_metadatas = []

    for file_index in range(len(all_note_file_paths)):
        current_file_path = all_note_file_paths[file_index]
        current_content = read_note_content(current_file_path)
        note_title = get_note_title(current_file_path)

        note_ids.append(current_file_path)
        note_contents.append(current_content)
        note_metadatas.append({"title": note_title})

    if len(note_ids) > 0:
        note_embeddings = _embedding_model.encode(note_contents)
        embeddings_as_lists = note_embeddings.tolist()
        vault_collection.add(
            ids=note_ids,
            embeddings=embeddings_as_lists,
            documents=note_contents,
            metadatas=note_metadatas
        )

    return vault_collection


def search_notes_by_semantic_similarity(question_text, maximum_results):
    # embeds the question and returns the vault notes closest to it in meaning,
    # not just notes that happen to share literal words with the question
    vault_collection = _build_vault_collection()
    note_count = vault_collection.count()

    if note_count == 0:
        return []

    result_count = min(maximum_results, note_count)
    question_embedding = _embedding_model.encode([question_text])
    question_embedding_as_list = question_embedding.tolist()

    query_results = vault_collection.query(
        query_embeddings=question_embedding_as_list,
        n_results=result_count
    )

    matched_ids = query_results["ids"][0]
    matched_documents = query_results["documents"][0]
    matched_metadatas = query_results["metadatas"][0]
    matched_distances = query_results["distances"][0]

    top_matches = []

    for match_index in range(len(matched_ids)):
        current_file_path = matched_ids[match_index]
        current_content = matched_documents[match_index]
        current_title = matched_metadatas[match_index]["title"]
        current_distance = matched_distances[match_index]

        # cosine distance is 0 for an identical match and grows from there;
        # flipping it to a similarity score keeps "higher is more relevant"
        # consistent with the rest of the codebase
        similarity_score = 1.0 - current_distance

        new_match = NoteMatch(
            file_path=current_file_path,
            title=current_title,
            content=current_content,
            match_score=similarity_score
        )
        top_matches.append(new_match)

    return top_matches
