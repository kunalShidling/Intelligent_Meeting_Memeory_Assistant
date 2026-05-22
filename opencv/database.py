"""
Database module for storing and retrieving face embeddings.
Uses MongoDB for persistent storage.
"""

import numpy as np
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure, DuplicateKeyError
from datetime import datetime
from typing import Optional, List, Dict, Tuple
import logging
import config

# Configure logging
logger = logging.getLogger(__name__)


class FaceDatabase:
    """MongoDB database handler for face embeddings."""
    
    def __init__(self, uri: str = config.MONGODB_URI):
        """
        Initialize database connection.
        
        Args:
            uri: MongoDB connection URI
        """
        self.uri = uri
        self.client = None
        self.db = None
        self.collection = None
        self._connected = False
    
    def connect(self) -> bool:
        """
        Connect to MongoDB database.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Import SSL for certificate handling
            import ssl
            import certifi
            
            # Create client with SSL/TLS parameters for MongoDB Atlas
            self.client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=10000,
                tls=True,
                tlsAllowInvalidCertificates=True,  # Bypass SSL verification
                tlsCAFile=certifi.where()  # Use certifi certificates
            )
            
            # Test connection
            self.client.admin.command('ping')
            
            # Get database and collection
            self.db = self.client[config.MONGODB_DATABASE]
            self.collection = self.db[config.MONGODB_COLLECTION]
            self.meetings_collection = None  # Will be initialized in _create_indexes
            
            # Create indexes
            self._create_indexes()
            
            self._connected = True
            logger.info(f"Connected to MongoDB: {config.MONGODB_DATABASE}.{config.MONGODB_COLLECTION}")
            
            return True
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            self._connected = False
            return False
        except Exception as e:
            logger.error(f"Error connecting to database: {e}")
            self._connected = False
            return False
    
    def _create_indexes(self):
        """Create database indexes for efficient querying."""
        try:
            # Create index on name for faster lookups
            self.collection.create_index([("name", ASCENDING)])
            
            # Create meetings collection and indexes
            self.meetings_collection = self.db['meetings']
            self.meetings_collection.create_index([("person_id", ASCENDING)])
            self.meetings_collection.create_index([("participant_ids", ASCENDING)])
            self.meetings_collection.create_index([("participant_names", ASCENDING)])
            self.meetings_collection.create_index([("person_name", ASCENDING)])
            self.meetings_collection.create_index([("timestamp", ASCENDING)])
            
            logger.debug("Database indexes created")
        except Exception as e:
            logger.warning(f"Error creating indexes: {e}")
    
    def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            self._connected = False
            logger.info("Disconnected from MongoDB")
    
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._connected
    
    def _embedding_to_list(self, embedding: np.ndarray) -> List[float]:
        """
        Convert numpy embedding to list for MongoDB storage.
        
        Args:
            embedding: Numpy array embedding
            
        Returns:
            List[float]: Embedding as list with full precision
        """
        # Convert to Python float to preserve precision
        return [float(x) for x in embedding]
    
    def _list_to_embedding(self, embedding_list: List[float]) -> np.ndarray:
        """
        Convert list from MongoDB to numpy embedding.
        
        Args:
            embedding_list: Embedding as list
            
        Returns:
            np.ndarray: Numpy array embedding
        """
        return np.array(embedding_list, dtype=np.float64)
    
    def validate_embedding(self, embedding: np.ndarray) -> bool:
        """
        Validate embedding dimensions.
        
        Args:
            embedding: Embedding to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if embedding is None:
            logger.error("Embedding is None")
            return False
        
        if len(embedding) != config.EMBEDDING_SIZE:
            logger.error(
                f"Invalid embedding size: {len(embedding)}, "
                f"expected {config.EMBEDDING_SIZE}"
            )
            return False
        
        return True
    
    def check_duplicate_embedding(self, embedding: np.ndarray) -> Tuple[bool, Optional[str]]:
        """
        Check if embedding is too similar to existing ones (potential duplicate).
        
        Args:
            embedding: Embedding to check
            
        Returns:
            Tuple[bool, Optional[str]]: (is_duplicate, name_of_duplicate)
        """
        try:
            # Get all embeddings from database
            all_records = self.get_all_embeddings()

            if not all_records:
                return False, None

            # Compare with all stored embeddings using cosine similarity.
            # This avoids initializing FaceNet again, which can exhaust memory.
            norm_query = np.linalg.norm(embedding)
            if norm_query == 0:
                logger.warning("Zero-norm embedding supplied; skipping duplicate check")
                return False, None

            for record in all_records:
                stored_embedding = record['embedding']
                norm_stored = np.linalg.norm(stored_embedding)
                if norm_stored == 0:
                    continue

                similarity = float(np.dot(embedding, stored_embedding) / (norm_query * norm_stored))

                if similarity >= config.DUPLICATE_THRESHOLD:
                    logger.warning(
                        f"Duplicate embedding detected - "
                        f"Similarity: {similarity:.4f} with '{record['name']}'"
                    )
                    return True, record['name']
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error checking duplicate embedding: {e}")
            return False, None
    
    def store_embedding(
        self,
        name: str,
        embedding: np.ndarray,
        check_duplicates: bool = True
    ) -> bool:
        """
        Store face embedding in database.
        
        Args:
            name: Person's name
            embedding: Face embedding vector
            check_duplicates: Whether to check for duplicate embeddings
            
        Returns:
            bool: True if stored successfully, False otherwise
        """
        try:
            if not self.is_connected():
                logger.error("Database not connected")
                return False
            
            # Validate embedding
            if not self.validate_embedding(embedding):
                return False
            
            # Check for duplicates if enabled
            if check_duplicates:
                is_duplicate, duplicate_name = self.check_duplicate_embedding(embedding)
                if is_duplicate:
                    logger.warning(
                        f"Embedding too similar to existing entry: '{duplicate_name}'"
                    )
                    return False
            
            # Prepare document
            document = {
                'name': name,
                'embedding': self._embedding_to_list(embedding),
                'date': datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow(),
                'embedding_size': len(embedding)
            }
            
            # Insert into database
            result = self.collection.insert_one(document)
            
            logger.info(
                f"Stored embedding for '{name}' - "
                f"ID: {result.inserted_id}, Size: {len(embedding)}"
            )
            
            return True
            
        except DuplicateKeyError:
            logger.error(f"Duplicate entry for name: {name}")
            return False
        except Exception as e:
            logger.error(f"Error storing embedding: {e}")
            return False
    
    def get_all_embeddings(self) -> List[Dict]:
        """
        Retrieve all stored embeddings.
        
        Returns:
            List[Dict]: List of records with name and embedding
        """
        try:
            if not self.is_connected():
                logger.error("Database not connected")
                return []
            
            # Query all documents
            cursor = self.collection.find({}, {'name': 1, 'embedding': 1, 'date': 1})
            
            records = []
            for doc in cursor:
                records.append({
                    '_id': doc['_id'],  # Include _id field
                    'name': doc['name'],
                    'embedding': self._list_to_embedding(doc['embedding']),
                    'date': doc.get('date')
                })
            
            logger.debug(f"Retrieved {len(records)} embeddings from database")
            return records
            
        except Exception as e:
            logger.error(f"Error retrieving embeddings: {e}")
            return []
    
    def get_embedding_by_name(self, name: str) -> Optional[np.ndarray]:
        """
        Retrieve embedding for a specific person.
        
        Args:
            name: Person's name
            
        Returns:
            Optional[np.ndarray]: Embedding if found, None otherwise
        """
        try:
            if not self.is_connected():
                logger.error("Database not connected")
                return None
            
            # Query by name
            doc = self.collection.find_one({'name': name})
            
            if doc is None:
                logger.debug(f"No embedding found for name: {name}")
                return None
            
            embedding = self._list_to_embedding(doc['embedding'])
            logger.debug(f"Retrieved embedding for '{name}' - Size: {len(embedding)}")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error retrieving embedding by name: {e}")
            return None
    
    def delete_embedding(self, name: str) -> bool:
        """
        Delete embedding from database.
        
        Args:
            name: Person's name
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            if not self.is_connected():
                logger.error("Database not connected")
                return False
            
            result = self.collection.delete_one({'name': name})
            
            if result.deleted_count > 0:
                logger.info(f"Deleted embedding for: {name}")
                return True
            else:
                logger.warning(f"No embedding found to delete: {name}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting embedding: {e}")
            return False
    
    def count_embeddings(self) -> int:
        """
        Count total number of stored embeddings.
        
        Returns:
            int: Number of embeddings
        """
        try:
            if not self.is_connected():
                logger.error("Database not connected")
                return 0
            
            count = self.collection.count_documents({})
            logger.debug(f"Total embeddings in database: {count}")
            
            return count
            
        except Exception as e:
            logger.error(f"Error counting embeddings: {e}")
            return 0
    
    def clear_all_embeddings(self) -> bool:
        """
        Clear all embeddings from database (use with caution!).
        
        Returns:
            bool: True if cleared successfully, False otherwise
        """
        try:
            if not self.is_connected():
                logger.error("Database not connected")
                return False
            
            result = self.collection.delete_many({})
            logger.warning(f"Cleared {result.deleted_count} embeddings from database")
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing embeddings: {e}")
            return False


    # ==================== Meeting Management Methods ====================
    
    def store_meeting(
        self,
        person_id: str,
        person_name: str,
        transcript: str,
        summary: str,
        audio_path: Optional[str] = None,
        image_path: Optional[str] = None,
        participant_ids: Optional[List[str]] = None,
        participant_names: Optional[List[str]] = None,
        participant_group_key: Optional[str] = None
    ) -> Optional[str]:
        """
        Store a meeting record for a person.
        
        Args:
            person_id: MongoDB ObjectId of the person
            person_name: Name of the person
            transcript: Full transcript of the meeting
            summary: Summary of the meeting
            audio_path: Optional path to audio file
            image_path: Optional path to image file
            
        Returns:
            str: Meeting ID if successful, None otherwise
        """
        try:
            if not self.is_connected():
                logger.error("Database not connected")
                return None
            
            normalized_participant_ids = [str(pid) for pid in participant_ids] if participant_ids else []
            normalized_participant_names = [str(name) for name in participant_names] if participant_names else []

            meeting_doc = {
                'person_id': str(person_id) if person_id else None,
                'person_name': person_name,
                'timestamp': datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow(),
                'transcript': transcript,
                'summary': summary,
                'audio_path': audio_path,
                'image_path': image_path,
                'participant_ids': normalized_participant_ids,
                'participant_names': normalized_participant_names,
                'participant_group_key': participant_group_key
            }
            
            result = self.meetings_collection.insert_one(meeting_doc)
            logger.info(f"Stored meeting for '{person_name}' - ID: {result.inserted_id}")
            
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error storing meeting: {e}")
            return None
    
    def get_last_meeting(self, person_id: str) -> Optional[Dict]:
        """
        Get the most recent meeting for a person.
        
        Args:
            person_id: MongoDB ObjectId of the person
            
        Returns:
            Dict: Meeting record or None
        """
        try:
            if not self.is_connected():
                logger.error("Database not connected")
                return None
            
            meeting = self.meetings_collection.find_one(
                {
                    '$or': [
                        {'person_id': str(person_id)},
                        {'participant_ids': str(person_id)}
                    ]
                },
                sort=[('timestamp', -1)]
            )
            
            return meeting
            
        except Exception as e:
            logger.error(f"Error retrieving last meeting: {e}")
            return None
    
    def get_all_meetings(self, person_id: str) -> List[Dict]:
        """
        Get all meetings for a person, sorted by timestamp (newest first).
        
        Args:
            person_id: MongoDB ObjectId of the person
            
        Returns:
            List[Dict]: List of meeting records
        """
        try:
            if not self.is_connected():
                logger.error("Database not connected")
                return []
            
            meetings = list(self.meetings_collection.find(
                {
                    '$or': [
                        {'person_id': str(person_id)},
                        {'participant_ids': str(person_id)}
                    ]
                }
            ).sort('timestamp', -1))
            
            return meetings
            
        except Exception as e:
            logger.error(f"Error retrieving meetings: {e}")
            return []

    def get_relevant_meetings(
        self,
        participant_ids: Optional[List[str]] = None,
        participant_names: Optional[List[str]] = None,
        limit: int = 25
    ) -> List[Dict]:
        """
        Get meetings ranked by participant overlap and recency.
        """
        try:
            if not self.is_connected():
                logger.error("Database not connected")
                return []

            participant_ids = [str(pid) for pid in (participant_ids or []) if pid]
            participant_names = [str(name) for name in (participant_names or []) if name]

            if not participant_ids and not participant_names:
                return []

            or_clauses = []
            if participant_ids:
                or_clauses.append({'person_id': {'$in': participant_ids}})
                or_clauses.append({'participant_ids': {'$in': participant_ids}})
            if participant_names:
                or_clauses.append({'person_name': {'$in': participant_names}})
                or_clauses.append({'participant_names': {'$in': participant_names}})

            query = {'$or': or_clauses} if or_clauses else {}

            raw_meetings = list(
                self.meetings_collection.find(query)
                .sort('timestamp', -1)
                .limit(max(limit * 5, limit))
            )

            active_ids = set([pid for pid in participant_ids])
            active_names = set([name.lower() for name in participant_names])

            def score_meeting(meeting: Dict) -> int:
                meeting_ids = set([str(pid) for pid in meeting.get('participant_ids', []) if pid])
                if meeting.get('person_id'):
                    meeting_ids.add(str(meeting['person_id']))

                meeting_names = set([str(name).lower() for name in meeting.get('participant_names', []) if name])
                if meeting.get('person_name'):
                    meeting_names.add(str(meeting['person_name']).lower())

                exact_match = False
                if active_ids:
                    exact_match = meeting_ids == active_ids
                elif active_names:
                    exact_match = meeting_names == active_names

                overlap_ids = len(meeting_ids.intersection(active_ids)) if active_ids else 0
                overlap_names = len(meeting_names.intersection(active_names)) if active_names else 0

                score = 0
                if exact_match:
                    score += 100
                score += overlap_ids * 10
                score += overlap_names * 5
                return score

            ranked = []
            for meeting in raw_meetings:
                meeting['_score'] = score_meeting(meeting)
                ranked.append(meeting)

            ranked.sort(
                key=lambda m: (m.get('_score', 0), m.get('timestamp')),
                reverse=True
            )

            return ranked[:limit]

        except Exception as e:
            logger.error(f"Error retrieving relevant meetings: {e}")
            return []
    
    def get_person_by_name(self, name: str) -> Optional[Dict]:
        """
        Get person record by name (includes _id and other fields).
        
        Args:
            name: Person's name
            
        Returns:
            Dict: Person record or None
        """
        try:
            if not self.is_connected():
                logger.error("Database not connected")
                return None
            
            record = self.collection.find_one({'name': name})
            return record
            
        except Exception as e:
            logger.error(f"Error retrieving person by name: {e}")
            return None
    
    def update_person_image(self, person_id: str, image_path: str) -> bool:
        """
        Update the stored image path for a person.
        
        Args:
            person_id: MongoDB ObjectId of the person
            image_path: Path to the image file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            import os
            from bson.objectid import ObjectId
            if not self.is_connected():
                logger.error("Database not connected")
                return False
            
            # Find the existing record to get the old image path
            existing_doc = self.collection.find_one({'_id': ObjectId(person_id)})
            old_image_path = existing_doc.get('image_path') if existing_doc else None

            result = self.collection.update_one(
                {'_id': ObjectId(person_id)},
                {'$set': {'image_path': image_path, 'updated_at': datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()}}
            )
            
            # Delete the old image to avoid storage bloat
            if old_image_path and old_image_path != image_path:
                if os.path.exists(old_image_path):
                    try:
                        os.remove(old_image_path)
                        logger.info(f"Deleted old image for record {person_id}: {old_image_path}")
                    except OSError as e:
                        logger.error(f"Could not delete old image {old_image_path}: {e}")
            
            return result.modified_count > 0
            
        except Exception as e:
            logger.error(f"Error updating person image: {e}")
            return False

    def update_person_embedding_and_image(
        self,
        person_id: str,
        embedding: np.ndarray,
        image_path: str
    ) -> bool:
        """
        Update the embedding and image path for a person to adapt to slight
        changes in their appearance over time.
        """
        try:
            import os
            from bson.objectid import ObjectId
            if not self.is_connected():
                logger.error("Database not connected")
                return False

            # Validate new embedding
            if not self.validate_embedding(embedding):
                return False

            # Find the existing record to get the old image path
            existing_doc = self.collection.find_one({'_id': ObjectId(person_id)})
            old_image_path = existing_doc.get('image_path') if existing_doc else None

            result = self.collection.update_one(
                {'_id': ObjectId(person_id)},
                {'$set': {
                    'embedding': self._embedding_to_list(embedding),
                    'image_path': image_path,
                    'updated_at': datetime.now(datetime.UTC) if hasattr(datetime, 'UTC') else datetime.utcnow()
                }}
            )

            # Delete the old image to save space
            if old_image_path and old_image_path != image_path:
                if os.path.exists(old_image_path):
                    try:
                        os.remove(old_image_path)
                        logger.info(f"Deleted old image for record {person_id}: {old_image_path}")
                    except OSError as e:
                        logger.error(f"Could not delete old image {old_image_path}: {e}")

            return result.modified_count > 0

        except Exception as e:
            logger.error(f"Error updating person embedding and image: {e}")
            return False


def main():
    """Test database module."""
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format=config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT
    )
    
    # Create database instance
    db = FaceDatabase()
    
    # Connect
    if not db.connect():
        print("Failed to connect to database")
        print("\nMake sure MongoDB is running:")
        print("  1. Install MongoDB: https://www.mongodb.com/try/download/community")
        print("  2. Start MongoDB service")
        print(f"  3. Ensure it's running on: {config.MONGODB_URI}")
        return
    
    print("Connected to database successfully!")
    
    # Get count
    count = db.count_embeddings()
    print(f"Total embeddings in database: {count}")
    
    # Test with dummy embedding
    dummy_embedding = np.random.randn(config.EMBEDDING_SIZE)
    dummy_embedding = dummy_embedding / np.linalg.norm(dummy_embedding)  # L2 normalize
    
    # Store
    print("\nStoring test embedding...")
    if db.store_embedding("Test User", dummy_embedding):
        print("✓ Embedding stored successfully")
    else:
        print("✗ Failed to store embedding")
    
    # Retrieve
    print("\nRetrieving test embedding...")
    retrieved = db.get_embedding_by_name("Test User")
    if retrieved is not None:
        print("✓ Embedding retrieved successfully")
        print(f"  Shape: {retrieved.shape}")
        print(f"  First 5 values: {retrieved[:5]}")
    else:
        print("✗ Failed to retrieve embedding")
    
    # Cleanup
    print("\nCleaning up test data...")
    db.delete_embedding("Test User")
    
    # Disconnect
    db.disconnect()
    print("\nDatabase test complete!")


if __name__ == "__main__":
    main()
