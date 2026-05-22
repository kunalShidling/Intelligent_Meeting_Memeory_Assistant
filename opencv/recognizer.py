"""
Face recognition module using cosine similarity.
Matches face embeddings against stored database.
"""

import numpy as np
from typing import Optional, Tuple, List, Dict
import logging
import config
from database import FaceDatabase

# Configure logging
logger = logging.getLogger(__name__)


class FaceRecognizer:
    """Face recognizer using cosine similarity matching."""
    
    def __init__(self, database: FaceDatabase):
        """
        Initialize face recognizer.
        
        Args:
            database: Connected FaceDatabase instance
        """
        self.database = database
        self._cached_records = None
        self._cache_timestamp = 0
        self._cache_ttl = 60  # Cache embeddings for 60 seconds
        logger.info("Face recognizer initialized")
    
    def _get_all_records(self):
        """Get all records, caching them to avoid reading DB every frame."""
        import time
        current_time = time.time()
        
        if self._cached_records is None or (current_time - self._cache_timestamp) > self._cache_ttl:
            logger.info("Fetching updated embeddings from database to refresh cache...")
            self._cached_records = self.database.get_all_embeddings()
            self._cache_timestamp = current_time
            
        return self._cached_records

    def invalidate_cache(self) -> None:
        self._cached_records = None
        self._cache_timestamp = 0
    
    def compute_cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """
        Compute cosine similarity between two embeddings.
        Handles zero vectors safely.
        
        Args:
            emb1: First embedding (L2-normalized)
            emb2: Second embedding (L2-normalized)
            
        Returns:
            float: Cosine similarity in range [-1, 1]
        """
        try:
            # Check for zero vectors
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            
            if norm1 == 0 or norm2 == 0:
                logger.warning("Zero vector detected in similarity computation")
                return 0.0
            
            # Compute cosine similarity
            # Since embeddings should be L2-normalized, dot product = cosine similarity
            similarity = np.dot(emb1, emb2)
            
            # Clip to valid range
            similarity = np.clip(similarity, -1.0, 1.0)
            
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error computing cosine similarity: {e}")
            return 0.0
    
    def find_best_match(
        self,
        query_embedding: np.ndarray
    ) -> Tuple[Optional[str], float, List[Dict]]:
        """
        Find best matching person in database.
        
        Args:
            query_embedding: Query face embedding
            
        Returns:
            Tuple containing:
                - best_match_name: Name of best match (None if no match)
                - best_similarity: Similarity score of best match
                - all_matches: List of all matches with scores
        """
        try:
            # Get all stored embeddings from cache instead of fetching every frame
            all_records = self._get_all_records()
            
            if not all_records:
                logger.info("No embeddings in database to match against")
                return None, 0.0, []
            
            logger.info(f"Comparing against {len(all_records)} stored embeddings")
            
            # Compute similarities
            matches = []
            best_similarity = -1.0
            best_match_name = None
            
            for record in all_records:
                name = record['name']
                stored_embedding = record['embedding']
                
                # Compute similarity
                similarity = self.compute_cosine_similarity(query_embedding, stored_embedding)
                
                matches.append({
                    'name': name,
                    'similarity': similarity,
                    'date': record.get('date')
                })
                
                logger.debug(f"Similarity with '{name}': {similarity:.4f}")
                
                # Track best match
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match_name = name
            
            # Sort matches by similarity (descending)
            matches.sort(key=lambda x: x['similarity'], reverse=True)
            
            logger.info(
                f"Best match: '{best_match_name}' with similarity: {best_similarity:.4f}"
            )
            
            return best_match_name, best_similarity, matches
            
        except Exception as e:
            logger.error(f"Error finding best match: {e}")
            return None, 0.0, []
    
    def recognize(
        self,
        query_embedding: np.ndarray,
        threshold: float = config.RECOGNITION_THRESHOLD
    ) -> Tuple[bool, Optional[str], float]:
        """
        Recognize person from face embedding.
        
        Args:
            query_embedding: Query face embedding
            threshold: Recognition threshold (default from config)
            
        Returns:
            Tuple containing:
                - recognized: True if person recognized, False otherwise
                - name: Name of recognized person (None if not recognized)
                - confidence: Similarity score
        """
        try:
            logger.info(f"Attempting recognition with threshold: {threshold}")
            
            # Find best match
            best_match_name, best_similarity, all_matches = self.find_best_match(
                query_embedding
            )
            
            # Check if similarity meets threshold
            if best_similarity >= threshold and best_match_name is not None:
                logger.info(
                    f"✓ Person RECOGNIZED: '{best_match_name}' "
                    f"(confidence: {best_similarity:.4f})"
                )
                return True, best_match_name, best_similarity
            else:
                logger.info(
                    f"✗ Person NOT recognized "
                    f"(best match: '{best_match_name}', similarity: {best_similarity:.4f})"
                )
                return False, None, best_similarity
                
        except Exception as e:
            logger.error(f"Error in recognition: {e}")
            return False, None, 0.0
    
    def register_new_person(
        self,
        name: str,
        embedding: np.ndarray
    ) -> bool:
        """
        Register a new person in the database.
        
        Args:
            name: Person's name
            embedding: Face embedding
            
        Returns:
            bool: True if registered successfully, False otherwise
        """
        try:
            logger.info(f"Registering new person: '{name}'")
            
            # Check if name already exists
            existing_embedding = self.database.get_embedding_by_name(name)
            if existing_embedding is not None:
                logger.warning(f"Name '{name}' already exists in database")
                return False
            
            # Store embedding (with duplicate check)
            success = self.database.store_embedding(name, embedding, check_duplicates=True)
            
            if success:
                logger.info(f"✓ Successfully registered: '{name}'")
                # Invalidate cache so it fetches the new person on next recognize
                self._cached_records = None
            else:
                logger.error(f"✗ Failed to register: '{name}'")
            
            return success
            
        except Exception as e:
            logger.error(f"Error registering new person: {e}")
            return False
    
    def recognize_or_register(
        self,
        embedding: np.ndarray,
        ask_for_name_callback=None,
        threshold: float = config.RECOGNITION_THRESHOLD
    ) -> Tuple[str, bool, float]:
        """
        Recognize person or register as new if not found.
        
        Args:
            embedding: Face embedding
            ask_for_name_callback: Function to call to get name for new person
            threshold: Recognition threshold
            
        Returns:
            Tuple containing:
                - name: Person's name (existing or newly registered)
                - is_new: True if newly registered, False if recognized
                - confidence: Similarity score
        """
        try:
            # Attempt recognition
            recognized, name, confidence = self.recognize(embedding, threshold)
            
            if recognized:
                return name, False, confidence
            
            # Person not recognized - register as new (only when callback is provided)
            if ask_for_name_callback is None:
                logger.info("No name callback provided; skipping auto-registration")
                return None, False, 0.0

            logger.info("Person not recognized - proceeding with registration")

            # Get name for new person
            new_name = ask_for_name_callback()
            
            if not new_name:
                logger.error("No name provided for new person")
                return None, False, 0.0
            
            # Validate name
            if not self._validate_name(new_name):
                logger.error(f"Invalid name: '{new_name}'")
                return None, False, 0.0
            
            # Register
            success = self.register_new_person(new_name, embedding)
            
            if success:
                return new_name, True, 1.0
            else:
                return None, False, 0.0
                
        except Exception as e:
            logger.error(f"Error in recognize_or_register: {e}")
            return None, False, 0.0
    
    def _validate_name(self, name: str) -> bool:
        """
        Validate person name.
        
        Args:
            name: Name to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not name:
            return False
        
        if len(name) < config.MIN_NAME_LENGTH:
            logger.error(f"Name too short (min {config.MIN_NAME_LENGTH} chars)")
            return False
        
        if len(name) > config.MAX_NAME_LENGTH:
            logger.error(f"Name too long (max {config.MAX_NAME_LENGTH} chars)")
            return False
        
        # Check for invalid characters
        for char in name:
            if char not in config.ALLOWED_NAME_CHARS:
                logger.error(f"Invalid character in name: '{char}'")
                return False
        
        return True
    
    def get_all_registered_people(self) -> List[str]:
        """
        Get list of all registered people.
        
        Returns:
            List[str]: List of names
        """
        try:
            all_records = self.database.get_all_embeddings()
            names = [record['name'] for record in all_records]
            return sorted(names)
        except Exception as e:
            logger.error(f"Error getting registered people: {e}")
            return []
    
    def print_all_matches(self, matches: List[Dict]):
        """
        Print all matches in a formatted way.
        
        Args:
            matches: List of match dictionaries
        """
        if not matches:
            print("\nNo matches found in database")
            return
        
        print("\n" + "=" * 60)
        print("ALL MATCHES (sorted by similarity):")
        print("=" * 60)
        
        for i, match in enumerate(matches, 1):
            name = match['name']
            similarity = match['similarity']
            status = "✓ MATCH" if similarity >= config.RECOGNITION_THRESHOLD else "✗ NO MATCH"
            
            print(f"{i}. {name:20s} | Similarity: {similarity:.4f} | {status}")
        
        print("=" * 60)


def main():
    """Test face recognizer."""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT
    )
    
    # Connect to database
    db = FaceDatabase()
    if not db.connect():
        print("Failed to connect to database")
        return
    
    # Create recognizer
    recognizer = FaceRecognizer(db)
    
    # Show registered people
    people = recognizer.get_all_registered_people()
    print(f"\nRegistered people: {people}")
    print(f"Total: {len(people)}")
    
    # Test with dummy embedding
    print("\nTesting with random embedding...")
    dummy_embedding = np.random.randn(config.EMBEDDING_SIZE)
    dummy_embedding = dummy_embedding / np.linalg.norm(dummy_embedding)
    
    recognized, name, confidence = recognizer.recognize(dummy_embedding)
    
    if recognized:
        print(f"✓ Recognized: {name} (confidence: {confidence:.4f})")
    else:
        print(f"✗ Not recognized (best match confidence: {confidence:.4f})")
    
    # Disconnect
    db.disconnect()


if __name__ == "__main__":
    main()
